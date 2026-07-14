"""翻译服务：在线翻译和LLM翻译功能"""
import requests
import urllib.parse
from ratelimit import limits, sleep_and_retry


class TranslationService:
    """翻译服务类"""
    
    MINUTE = 60
    
    def __init__(self, config, llm_service):
        """初始化翻译服务"""
        self.config = config
        self.llm_service = llm_service
    
    def translate_abstract_with_llm(self, title, abstract, tldr="", keywords="", primary_area=""):
        """使用LLM翻译摘要"""
        abstract_limit = self.config.get('abstract_translation_limit', 2500)
        
        # 构建包含标题、TLDR、关键词和领域的提示词
        context_info = f"标题：{title}\n"
        if tldr and tldr.strip():
            context_info += f"TLDR：{tldr}\n"
        if keywords:
            context_info += f"关键词：{keywords}\n"
        if primary_area:
            context_info += f"主要领域：{primary_area}\n"
        
        prompt = f"""请将以下学术论文摘要翻译成中文，结合标题、TLDR、关键词和领域信息以确保翻译准确性：

{context_info}
摘要：{abstract[:abstract_limit]}

请提供准确、专业的翻译："""
        
        messages = [
            {"role": "system", "content": "你是一个专业的学术翻译助手，能够结合论文标题、TLDR、关键词和领域信息进行准确的摘要翻译。"},
            {"role": "user", "content": prompt}
        ]
        
        translation, tokens_used = self.llm_service.call_deepseek_api(messages)
        return translation, tokens_used
    
    def translate_title_with_llm(self, title, abstract="", tldr="", keywords="", primary_area=""):
        """使用LLM翻译标题"""
        # 构建包含摘要、TLDR、关键词和领域的提示词
        context_info = ""
        if abstract and abstract.strip():
            context_info += f"摘要：{abstract[:500]}\n"
        if tldr and tldr.strip():
            context_info += f"TLDR：{tldr}\n"
        if keywords:
            context_info += f"关键词：{keywords}\n"
        if primary_area:
            context_info += f"主要领域：{primary_area}\n"
        
        if context_info:
            prompt = f"""请将以下学术论文标题翻译成中文，结合摘要、TLDR、关键词和领域信息以确保翻译的准确性：

{context_info}
标题：{title}

请提供专业、准确的翻译："""
        else:
            prompt = f"请将以下学术论文标题翻译成中文，保持专业性和准确性：\n\n{title}"
        
        messages = [
            {"role": "system", "content": "你是一个专业的学术翻译助手，能够结合论文摘要、TLDR、关键词和领域信息进行准确的标题翻译。"},
            {"role": "user", "content": prompt}
        ]
        
        translation, tokens_used = self.llm_service.call_deepseek_api(messages, max_tokens=200, temperature=0.1)
        return translation, tokens_used
    
    def is_translation_failed(self, translation):
        """检查翻译是否失败"""
        if not translation or not translation.strip():
            return True
        
        fail_indicators = [
            "翻译失败",
            "fail", "error", "sorry", "quota", "exceeded", "limit",
            "invalid", "unauthorized", "timeout", "无法翻译", "请求失败",
            "api", "key", "expired", "over", "usage", "超出", "超过"
        ]
        
        translation_lower = translation.lower()
        if any(indicator in translation_lower for indicator in fail_indicators):
            return True
            
        if len(translation) < 3:
            return True
            
        return False
    
    @sleep_and_retry
    @limits(calls=30, period=MINUTE)
    def translate_text_online_single(self, text, text_type="标题"):
        """在线翻译单个文本（带限流）"""
        return self._translate_text_online_single_impl(text, text_type)
    
    def translate_text_online_batch(self, text, text_type="标题"):
        """分批翻译长文本"""
        if not text:
            return ""
            
        limit = self.config['online_translation_limit']
        if len(text) <= limit:
            return self.translate_text_online_single(text, text_type)
        
        try:
            segments = []
            start = 0
            while start < len(text):
                end = start + limit
                if end < len(text):
                    sentence_end = text.rfind('.', start, end)
                    if sentence_end != -1 and sentence_end > start:
                        end = sentence_end + 1
                    else:
                        word_end = text.rfind(' ', start, end)
                        if word_end != -1 and word_end > start:
                            end = word_end + 1
                
                segment = text[start:end].strip()
                if segment:
                    segments.append(segment)
                start = end
            
            translated_segments = []
            for i, segment in enumerate(segments):
                print(f"翻译第 {i+1}/{len(segments)} 段...")
                translated_segment = self.translate_text_online_single(segment, f"{text_type}_分段{i+1}")
                if self.is_translation_failed(translated_segment):
                    print(f"第 {i+1} 段翻译失败")
                    continue
                translated_segments.append(translated_segment)
            
            if translated_segments:
                full_translation = " ".join(translated_segments)
                return full_translation
            else:
                return "所有分段翻译均失败"
            
        except Exception as e:
            print(f"分批翻译失败: {e}")
            return self.translate_text_online_single(text[:limit], text_type)

    def _translate_text_online_single_impl(self, text, text_type="标题"):
        """在线翻译单个文本的实际实现"""
        services = self.config.get('translation_services', ['mymemory', 'google'])
        
        for service in services:
            try:
                # print(f"尝试使用 {service} 翻译服务...") # Reduce spam
                translated = self._call_translation_service(service, text, text_type)
                
                if translated and not self.is_translation_failed(translated):
                    # print(f"{service} 翻译成功")
                    return translated
                else:
                    # print(f"{service} 翻译失败: {translated}")
                    pass
                    
            except Exception as e:
                print(f"{service} 翻译服务异常: {e}")
                continue
        
        return "所有翻译服务均失败"
    
    def _call_translation_service(self, service, text, text_type):
        """调用具体的翻译服务"""
        if len(text) > self.config['online_translation_limit'] and text_type != "标题":
            text = text[:self.config['online_translation_limit']] + "..."
        
        if service == 'mymemory':
            return self._translate_mymemory(text)
        elif service == 'google':
            return self._translate_google(text)
        elif service == 'baidu':
            return self._translate_baidu(text)
        elif service == 'youdao':
            return self._translate_youdao(text)
        elif service == 'libre':
            return self._translate_libre(text)
        elif service == 'tencent':
            return self._translate_tencent(text)
        else:
            return f"未知翻译服务: {service}"
    
    def _translate_mymemory(self, text):
        """MyMemory翻译服务"""
        try:
            params = self.config.get('translation_service_params', {}).get('mymemory', {})
            email = params.get('email', '2182712226@qq.com')
            key = params.get('key', 'f23aa66e19b601cff7cf')
            
            url = f"https://api.mymemory.translated.net/get?q={urllib.parse.quote(text)}&langpair=en|zh&key={key}&de={email}"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                translated = data['responseData']['translatedText']
                return translated
            else:
                return f"翻译API调用失败，状态码: {response.status_code}"
        except Exception as e:
            return f"翻译异常: {str(e)}"
    
    def _translate_google(self, text):
        """Google翻译服务"""
        try:
            url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl=zh&dt=t&q={urllib.parse.quote(text)}"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0 and data[0]:
                    translated = ''.join([item[0] for item in data[0] if item[0]])
                    return translated
            return "Google翻译失败"
        except Exception as e:
            return f"Google翻译异常: {str(e)}"
    
    def _translate_baidu(self, text):
        """百度翻译服务"""
        try:
            params = self.config.get('translation_service_params', {}).get('baidu', {})
            appid = params.get('appid', '')
            key = params.get('key', '')
            
            if not appid or not key:
                return "百度翻译未配置"
                
            import hashlib
            import random
            
            salt = random.randint(32768, 65536)
            sign = hashlib.md5((appid + text + str(salt) + key).encode()).hexdigest()
            
            url = "https://fanyi-api.baidu.com/api/trans/vip/translate"
            data = {
                'q': text,
                'from': 'en',
                'to': 'zh',
                'appid': appid,
                'salt': salt,
                'sign': sign
            }
            
            response = requests.post(url, data=data, timeout=10)
            if response.status_code == 200:
                result = response.json()
                if 'trans_result' in result:
                    translated = ' '.join([item['dst'] for item in result['trans_result']])
                    return translated
            return "百度翻译失败"
        except Exception as e:
            return f"百度翻译异常: {str(e)}"
    
    def _translate_youdao(self, text):
        """有道翻译服务"""
        try:
            params = self.config.get('translation_service_params', {}).get('youdao', {})
            appKey = params.get('appKey', '')
            key = params.get('key', '')
            
            if not appKey or not key:
                return "有道翻译未配置"
                
            import hashlib
            import time
            import uuid
            
            salt = str(uuid.uuid1())
            curtime = str(int(time.time()))
            sign_str = appKey + text + salt + curtime + key
            sign = hashlib.sha256(sign_str.encode()).hexdigest()
            
            url = "https://openapi.youdao.com/api"
            data = {
                'q': text,
                'from': 'en',
                'to': 'zh-CHS',
                'appKey': appKey,
                'salt': salt,
                'sign': sign,
                'signType': 'v3',
                'curtime': curtime
            }
            
            response = requests.post(url, data=data, timeout=10)
            if response.status_code == 200:
                result = response.json()
                if result.get('errorCode') == '0' and 'translation' in result:
                    translated = ' '.join(result['translation'])
                    return translated
            return "有道翻译失败"
        except Exception as e:
            return f"有道翻译异常: {str(e)}"
    
    def _translate_libre(self, text):
        """LibreTranslate翻译服务"""
        try:
            url = "https://libretranslate.com/translate"
            data = {
                'q': text,
                'source': 'en',
                'target': 'zh',
                'format': 'text'
            }
            
            response = requests.post(url, json=data, timeout=10)
            if response.status_code == 200:
                result = response.json()
                if 'translatedText' in result:
                    return result['translatedText']
            return "Libre翻译失败"
        except Exception as e:
            return f"Libre翻译异常: {str(e)}"
    
    def _translate_tencent(self, text):
        """腾讯云翻译服务"""
        try:
            params = self.config.get('translation_service_params', {}).get('tencent', {})
            secretId = params.get('secretId', '')
            secretKey = params.get('secretKey', '')
            
            if not secretId or not secretKey:
                return "腾讯云翻译未配置"
                
            try:
                from tencentcloud.common import credential
                from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
                from tencentcloud.tmt.v20180321 import tmt_client, models
                
                cred = credential.Credential(secretId, secretKey)
                client = tmt_client.TmtClient(cred, "ap-shanghai")
                
                req = models.TextTranslateRequest()
                req.SourceText = text
                req.Source = "en"
                req.Target = "zh"
                req.ProjectId = 0
                
                resp = client.TextTranslate(req)
                return resp.TargetText
                
            except ImportError:
                return "腾讯云SDK未安装"
            except Exception as e:
                return f"腾讯云翻译失败: {e}"
                
        except Exception as e:
            return f"腾讯云翻译异常: {str(e)}"