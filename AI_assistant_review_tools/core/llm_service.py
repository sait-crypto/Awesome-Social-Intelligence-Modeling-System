"""LLM服务：DeepSeek API调用和LLM搜索功能"""
import os
import requests
import json
import re


class LLMService:
    """LLM服务类"""

    def __init__(self, api_key=None, api_url=None):
        """初始化LLM服务"""
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        self.api_url = api_url or "https://api.deepseek.com/v1/chat/completions"
        self.token_usage = 0

    def call_deepseek_api(self, messages, max_tokens=1000, temperature=0.3):
        """调用DeepSeek API"""
        if not self.api_key:
            return "API call failed: DEEPSEEK_API_KEY is not configured", 0

        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}'
        }

        data = {
            'model': 'deepseek-chat',
            'messages': messages,
            'max_tokens': max_tokens,
            'temperature': temperature,
            'stream': False
        }

        # attempt the request with simple retry/backoff in case of transient network issues or occasional hiccups
        max_attempts = 3
        backoff = 2
        tokens_used = 0
        for attempt in range(1, max_attempts + 1):
            try:
                response = requests.post(self.api_url, headers=headers, json=data, timeout=60)
                response.raise_for_status()
                result = response.json()

                if 'usage' in result and 'total_tokens' in result['usage']:
                    tokens_used = result['usage']['total_tokens']
                    self.token_usage += tokens_used

                if 'choices' in result and len(result['choices']) > 0:
                    return result['choices'][0]['message']['content'].strip(), tokens_used
                else:
                    return None, tokens_used

            except requests.exceptions.Timeout:
                # log and retry if there are remaining attempts
                print(f"DeepSeek API请求超时 (attempt {attempt}/{max_attempts})")
                if attempt == max_attempts:
                    return "API调用失败: 请求超时", 0
            except requests.exceptions.RequestException as e:
                # network error or bad response; break if unrecoverable
                print(f"DeepSeek API请求失败 (attempt {attempt}/{max_attempts}): {e}")
                if attempt == max_attempts:
                    return f"API调用失败: {str(e)}", 0
            except Exception as e:
                print(f"处理DeepSeek API响应时出错: {e}")
                return f"API调用异常: {str(e)}", 0

            # exponential backoff before next try
            import time
            time.sleep(backoff)
            backoff *= 2

        # should not reach here, but return failure for safety
        return "API调用失败: 重试后仍失败", 0

    def generate_tldr_summary(self, title, abstract, keywords="", primary_area="", soft_limit=300):
        """生成TLDR摘要"""
        # 构建包含关键词和领域的提示词
        context_info = ""
        if keywords:
            context_info += f"关键词: {keywords}\n"
        if primary_area:
            context_info += f"主要领域: {primary_area}\n"
        # 摘要截断添加标识，保证LLM感知
        truncated_abstract = abstract[:1000]
        if len(abstract) > 1000:
            truncated_abstract += "..."

        prompt = f"""请为以下学术论文生成一个简洁的TLDR总结（不超过{soft_limit}字），然后将其翻译成中文：
标题：{title}
{context_info}摘要：{truncated_abstract}
请按照以下格式输出：
英文总结：[英文TLDR总结]
中文翻译：[中文TLDR翻译]"""

        messages = [
            {"role": "system", "content": "你是一个专业的学术论文总结助手。"},
            {"role": "user", "content": prompt}
        ]

        summary, tokens_used = self.call_deepseek_api(messages)

        if not summary or summary.startswith("API调用失败") or summary.startswith("API调用异常"):
            return None, tokens_used
        english_summary = ""
        chinese_translation = ""

        # 增强解析逻辑：如果包含特定分隔符，则分割；否则视为整体是中文翻译或英文总结
        if "英文总结：" in summary and "中文翻译：" in summary:
            parts = summary.split("中文翻译：")
            if len(parts) == 2:
                english_part = parts[0].replace("英文总结：", "").strip()
                chinese_part = parts[1].strip()
                english_summary = english_part
                chinese_translation = chinese_part
        elif "中文翻译：" in summary:
            # 只有中文翻译部分
            chinese_translation = summary.replace("中文翻译：", "").strip()
            english_summary = "（未提供英文总结）"
        else:
            # 假设LLM直接输出了内容，默认放入中文显示，避免空白
            chinese_translation = summary
            english_summary = ""

        return {'english': english_summary, 'chinese': chinese_translation, 'tokens': tokens_used}, tokens_used

    def llm_search_papers_two_stage(self, search_query, papers, config, callback=None):
        """两阶段LLM搜索：先用标题初筛，再用TLDR和摘要精筛"""
        # 修正：config取值增加get默认值，避免KeyError
        default_threshold = 0.4
        default_pre_ratio = 0.7
        default_soft_limit = 500
        default_hard_limit = 1000
        preliminary_threshold = config.get('llm_relevance_threshold', default_threshold) * config.get('preliminary_threshold_ratio', default_pre_ratio)
        final_threshold = config.get('llm_relevance_threshold', default_threshold)
        soft_limit = config.get('llm_search_tldr_abstract_soft_limit', default_soft_limit)
        hard_limit = config.get('llm_search_tldr_abstract_hard_limit', default_hard_limit)
        effective_limit = min(soft_limit, hard_limit)

        print(f"\n=== 开始两阶段LLM搜索 ===")
        print(f"初步阈值: {preliminary_threshold:.2f}, 最终阈值: {final_threshold:.2f}")

        # 第一阶段：使用标题进行初步筛选
        print("\n--- 第一阶段：标题初筛 ---")
        preliminary_results = self.llm_search_papers_single_stage(
            search_query,
            papers,
            include_tldr_abstract=False,
            custom_threshold=preliminary_threshold,
            config=config,
            callback=callback
        )

        if not preliminary_results:
            print("初步筛选未找到相关论文")
            return []

        preliminary_papers = [res['paper'] for res in preliminary_results]
        print(f"第一阶段找到 {len(preliminary_papers)} 篇论文，进入第二阶段")

        # 第二阶段：对初筛结果使用TLDR和摘要进行精细筛选
        print("\n--- 第二阶段：TLDR和摘要精筛 ---")

        # 修正1：先截断初筛论文列表，再生成信息，从源头避免索引错位
        truncated_papers = preliminary_papers[:effective_limit]
        papers_info = []
        for i, paper in enumerate(truncated_papers):
            title = paper.get('title', '')
            tldr = paper.get('tldr', '')
            abstract = paper.get('abstract', '')
            keywords = paper.get('keywords', '')
            primary_area = paper.get('primary_area', '')
            # 修正2：摘要截断添加标识，保证LLM感知
            truncated_abs = abstract[:1000]
            if len(abstract) > 1000:
                truncated_abs += "..."

            info = f"{i+1}. {title}"
            if tldr:
                info += f"\n   TLDR: {tldr}"
            if truncated_abs:
                info += f"\n   摘要: {truncated_abs}"
            if keywords:
                info += f"\n   关键词: {keywords}"
            if primary_area:
                info += f"\n   主要领域: {primary_area}"

            papers_info.append(info)
        papers_text = "\n".join(papers_info)

        prompt = f"""请根据用户的需求，基于【研究领域、核心方法、研究问题】判断以下论文各自与搜索需求的语义匹配度，按以下标准打分：
0.8-1：高度相关（核心内容完全匹配）；0.5-0.8：中度相关（领域/方法匹配）；0.0-0.5：低度相关。
严格按 序号,分数 格式输出，仅输出数字，无多余字符、空格、备注。
用户需求：{search_query}
论文信息：
{papers_text}
请按照以下格式输出：
相关论文序号,分数
例如：
1,0.85
3,0.72
5,0.68
如果没有相关论文，请输出"无"。
请确保只输出序号和分数（分数从0到1），不要输出其他任何内容。"""

        messages = [
            {"role": "system", "content": "你是一个专业的论文搜索助手，能够准确理解用户的搜索需求并为每篇论文评估相关性分数。请放宽搜索条件，只要论文与用户需求有相关性就包含在内。"},
            {"role": "user", "content": prompt}
        ]

        response, tokens_used = self.call_deepseek_api(messages, max_tokens=1000, temperature=0.1)
        if callback:
            callback(tokens_used)
        if not response or response.startswith("API调用失败"):
            print("第二阶段LLM API调用失败，未找到相关论文")
            return []

        scored_papers = []
        response_str = response.strip().lower()
        if response_str != "无":
            try:
                lines = response_str.split('\n')
                lines = [line.strip() for line in lines if line.strip()]
                for line in lines:
                    parts = line.split(',')
                    if len(parts) == 2:
                        try:
                            index = int(parts[0].strip()) - 1
                            score = min(max(float(parts[1].strip()), 0.0), 1.0)
                            # 修正3：索引仅匹配截断后的列表，杜绝越界
                            if 0 <= index < len(truncated_papers) and 0 <= score <= 1:
                                scored_papers.append({
                                    'paper': truncated_papers[index],
                                    'score': score
                                })
                        except ValueError:
                            continue
            except Exception as e:
                print(f"解析LLM第二阶段响应时出错: {e}")
                return []
        else:
            # 修正4：无结果时添加日志，保证日志输出统一
            print("第二阶段LLM筛选未找到相关论文")

        # 筛选
        final_results = [p for p in scored_papers if p['score'] >= final_threshold]
        print(f"\n=== 两阶段搜索完成，找到 {len(final_results)} 篇论文 ===")
        return final_results

    def llm_search_papers_single_stage(self, search_query, papers, include_tldr_abstract,
                                       custom_threshold=None, config=None, callback=None):
        """单阶段LLM搜索"""
        # 修正1：统一config容错逻辑，所有取值增加get默认值，避免KeyError
        default_threshold = 0.4
        default_soft_title = 2000
        default_hard_title = 4000
        default_soft_tldr = 500
        default_hard_tldr = 1000
        if config is None:
            relevance_threshold = custom_threshold or default_threshold
            soft_limit = default_soft_title if not include_tldr_abstract else default_soft_tldr
            hard_limit = default_hard_title if not include_tldr_abstract else default_hard_tldr
        else:
            relevance_threshold = custom_threshold or config.get('llm_relevance_threshold', default_threshold)
            soft_limit = config.get('llm_search_tldr_abstract_soft_limit', default_soft_tldr) if include_tldr_abstract else config.get('llm_search_soft_limit', default_soft_title)
            hard_limit = config.get('llm_search_tldr_abstract_hard_limit', default_hard_tldr) if include_tldr_abstract else config.get('llm_search_hard_limit', default_hard_title)

        effective_limit = min(soft_limit, hard_limit)
        # 修正2：先截断原始论文列表，再生成信息，从源头避免索引错位
        truncated_papers = papers[:effective_limit]

        papers_info = []
        for i, paper in enumerate(truncated_papers):
            title = paper.get('title', '')
            info = f"{i+1}. {title}"

            if include_tldr_abstract:
                tldr = paper.get('tldr', '')
                abstract = paper.get('abstract', '')
                keywords = paper.get('keywords', '')
                primary_area = paper.get('primary_area', '')
                # 修正3：摘要截断添加标识，保证LLM感知
                truncated_abs = abstract[:800]
                if len(abstract) > 800:
                    truncated_abs += "..."

                if tldr:
                    info += f"\n   TLDR: {tldr}"
                if truncated_abs:
                    info += f"\n   摘要: {truncated_abs}"
                if keywords:
                    info += f"\n   关键词: {keywords}"
                if primary_area:
                    info += f"\n   主要领域: {primary_area}"

            papers_info.append(info)

        papers_text = "\n".join(papers_info)

        prompt = f"""请根据用户的需求基于【研究领域、核心方法、研究问题】判断以下论文各自与搜索需求的语义匹配度，按以下标准打分：
0.8-1：高度相关（核心内容完全匹配）；0.5-0.8：中度相关（领域/方法匹配）；0.0-0.5：低度相关。
严格按 序号,分数 格式输出，仅输出数字，无多余字符、空格、备注。

用户需求：{search_query}
论文标题列表：
{papers_text}
请仔细分析每个论文标题与用户需求的相关性，请按照以下格式输出：
相关论文序号,分数
例如：
1,0.85
3,0.72
5,0.68
如果没有相关论文，请输出"无"。
请确保只输出序号和分数（分数从0到1），不要输出其他任何内容。"""

        messages = [
            {"role": "system", "content": "你是一个专业的论文搜索助手，能够准确理解用户的搜索需求并筛选相关论文。请仔细分析论文标题与用户需求的相关性。请放宽搜索条件，只要论文与用户需求有相关性就包含在内。"},
            {"role": "user", "content": prompt}
        ]

        response, tokens_used = self.call_deepseek_api(messages, max_tokens=2000, temperature=0.1)
        if callback:
            callback(tokens_used)

        if not response or response.startswith("API调用失败"):
            print("单阶段LLM API调用失败，未找到相关论文")
            return []

        scored_papers = []
        response_str = response.strip().lower()
        if response_str != "无":
            try:
                lines = response_str.split('\n')
                lines = [line.strip() for line in lines if line.strip()]

                for line in lines:
                    parts = line.split(',')
                    if len(parts) == 2:
                        try:
                            index = int(parts[0].strip()) - 1
                            score = min(max(float(parts[1].strip()), 0.0), 1.0)
                            # 修正4：索引仅匹配截断后的列表，杜绝越界和匹配错误
                            if 0 <= index < len(truncated_papers) and 0 <= score <= 1:
                                scored_papers.append({
                                    'paper': truncated_papers[index],
                                    'score': score
                                })
                        except ValueError:
                            # 捕获数值转换错误，继续解析下一行
                            continue
            except Exception as e:
                print(f"解析LLM单阶段响应时出错: {e}")
                return []
        else:
            # 修正5：无结果时添加日志，保证日志输出统一
            print("单阶段LLM筛选未找到相关论文")

        # 按分数排序并筛选
        filtered_results = [p for p in scored_papers if p['score'] >= relevance_threshold]
        filtered_results.sort(key=lambda x: x['score'], reverse=True)
        return filtered_results

    def llm_search_papers(self, search_query, papers, config, callback=None):
        """LLM搜索论文（根据配置决定使用单阶段或两阶段）"""
        include_tldr_abstract = config.get('llm_include_tldr_abstract', False)

        if include_tldr_abstract:
            return self.llm_search_papers_two_stage(search_query, papers, config, callback)
        else:
            # 修正：透传custom_threshold参数，保证参数功能可用
            return self.llm_search_papers_single_stage(
                search_query,
                papers,
                include_tldr_abstract=False,
                custom_threshold=None,
                config=config,
                callback=callback
            )

    def check_paper_relevance(self, search_query, paper, callback=None):
        """检查单篇论文的相关性"""
        # 修正1：添加callback参数，补全token回调覆盖
        title = paper.get('title', '')
        abstract = paper.get('abstract', '')
        tldr = paper.get('tldr', '')
        keywords = paper.get('keywords', '')
        primary_area = paper.get('primary_area', '')
        # 修正2：摘要截断添加标识，保证LLM感知
        truncated_abs = abstract[:500]
        if len(abstract) > 500:
            truncated_abs += "..."

        paper_info = f"标题: {title}\n"
        if truncated_abs:
            paper_info += f"摘要: {truncated_abs}\n"
        if tldr:
            paper_info += f"TLDR: {tldr}\n"
        if keywords:
            paper_info += f"关键词: {keywords}\n"
        if primary_area:
            paper_info += f"主要领域: {primary_area}\n"

        prompt = f"""请判断以下论文是否符合搜索条件，并给出相关性分数（0-1）和一个极简的理由（小于27字）。
搜索条件：{search_query}
论文信息：
{paper_info}
请按照以下格式输出：
分数: [0-1之间的数字]
理由：[小于27字的简短理由]
例如:
分数: 0.43
理由: 研究仇恨语言检测，属于仇恨检测子领域
请确保只输出分数和理由，不要输出其他任何内容。"""

        messages = [
            {"role": "system", "content": "你是一个专业的论文搜索助手，能够准确判断论文与搜索条件的符合程度/相关性。"},
            {"role": "user", "content": prompt}
        ]

        response, tokens_used = self.call_deepseek_api(messages, max_tokens=100, temperature=0.1)
        # 修正3：触发token回调，补全统计
        if callback:
            callback(tokens_used)

        # 修正4：统一返回值默认值，避免TypeError
        score = 0.0
        judgment = ""
        reason = "未解析到理由"

        if response and not response.startswith("API调用失败") and not response.startswith("API调用异常"):
            try:
                lines = response.strip().split('\n')
                for line in lines:
                    line_strip = line.strip()
                    if line_strip.startswith('分数:'):
                        score_str = line_strip.replace('分数:', '').strip()
                        # 修正5：增强分数解析的异常捕获
                        score = float(score_str) if score_str.replace('.', '').isdigit() else 0.0
                        score = min(max(score, 0.0), 1.0)
                    elif line_strip.startswith('理由:'):
                        reason = line_strip.replace('理由:', '').strip()[:27]  # 强制限制理由长度

                judgment = "已分析"
            except Exception as e:
                print(f"解析单篇论文相关性响应时出错: {e}")
                judgment = "解析失败"
                score = 0.0
        else:
            judgment = "API错误"
            score = 0.0

        return score, judgment, reason, tokens_used
