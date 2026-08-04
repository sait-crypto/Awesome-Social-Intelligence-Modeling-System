"""Social Intelligence Modeling 分类配置。

约定：
- ``unique_name`` 是持久化标识；改名或合并时必须在
  ``CATEGORIES_CHANGE_LIST`` 中提供旧值到当前值的直接映射。
- ``predecessor_category`` 引用父分类的 ``unique_name``，根分类为 ``None``。
- ``order`` 仅控制同级显示顺序，允许跨分支重复。
- ``Uncategorized`` 与 ``Other`` 是工程兜底分类，不属于论文 Figure 2 的学术分类。
"""


# 历史分类必须直接映射到当前启用分类；normalize_category_value 只应用一次映射。
CATEGORIES_CHANGE_LIST = [
    # 早期通用分类。
    {"old_unique_name": "Base Techniques", "new_unique_name": "Other"},
    {"old_unique_name": "Ethics and Safety", "new_unique_name": "Other"},
    {"old_unique_name": "Social Media Security", "new_unique_name": "Other"},

    # Perception 的改名、删除与合并。
    {"old_unique_name": "Perception and Classification", "new_unique_name": "Perception"},
    {"old_unique_name": "Controversy Analysis", "new_unique_name": "Discourse and Pragmatic Analysis"},
    {"old_unique_name": "Micro-Level Pragmatic Expressions", "new_unique_name": "Discourse and Pragmatic Analysis"},
    {"old_unique_name": "Macro-Level Discourse Analysis", "new_unique_name": "Discourse and Pragmatic Analysis"},
    {"old_unique_name": "Sarcasm Detection", "new_unique_name": "Discourse and Pragmatic Analysis"},
    {"old_unique_name": "Humor Recognition", "new_unique_name": "Discourse and Pragmatic Analysis"},
    {"old_unique_name": "Euphemism Recognition", "new_unique_name": "Discourse and Pragmatic Analysis"},
    {"old_unique_name": "Metaphor Recognition", "new_unique_name": "Discourse and Pragmatic Analysis"},
    {"old_unique_name": "Bragging Detection", "new_unique_name": "Discourse and Pragmatic Analysis"},
    {"old_unique_name": "Malicious Bot Detection", "new_unique_name": "Malicious User Detection"},

    # Understanding 的合并与历史别名。
    {"old_unique_name": "User Behavior Prediction", "new_unique_name": "User Profiling"},
    {"old_unique_name": "User Participation Prediction", "new_unique_name": "User Profiling"},
    {"old_unique_name": "Social Psychological Phenomena Analysis", "new_unique_name": "User-Level Understanding"},
    {"old_unique_name": "Dynamic Community Analysis", "new_unique_name": "Community Detection and Analysis"},
    {"old_unique_name": "Community Detection", "new_unique_name": "Community Detection and Analysis"},
    {"old_unique_name": "Multimodal Analysis", "new_unique_name": "Meme and Multimodal Understanding"},

    # Generation 的改名、删除与合并。
    {"old_unique_name": "Generation and Intervention", "new_unique_name": "Generation"},
    {"old_unique_name": "Hashtag and Caption Generation", "new_unique_name": "Social Content Generation"},
    {"old_unique_name": "Humorous and Creative Content Generation", "new_unique_name": "Social Content Generation"},
    {"old_unique_name": "Humor Generation", "new_unique_name": "Social Content Generation"},
    {"old_unique_name": "Story Generation", "new_unique_name": "Social Content Generation"},
    {"old_unique_name": "Dialogue and Conversational Systems", "new_unique_name": "Socially-Aware Dialogue Generation"},
    {"old_unique_name": "Social Impact and Intervention", "new_unique_name": "Social Intervention"},
    {"old_unique_name": "Rumor Refutation Generation", "new_unique_name": "Evidence-Grounded Rumor Refutation"},
    {"old_unique_name": "Text Detoxification and Moderation", "new_unique_name": "Content Moderation and Detoxification"},

    # Simulation 根分类与旧五维分类迁移到论文采用的三维体系。
    {"old_unique_name": "Simulation and Deduction", "new_unique_name": "Simulation"},
    {"old_unique_name": "Social Simulation", "new_unique_name": "Simulation"},
    {"old_unique_name": "Micro Social Simulation", "new_unique_name": "Micro-Level Social Simulation"},
    {"old_unique_name": "Macro Social Simulation", "new_unique_name": "Macro-Level Social Simulation"},
    {"old_unique_name": "Static Social Simulation", "new_unique_name": "Simulation"},
    {"old_unique_name": "Dynamic Social Simulation", "new_unique_name": "Simulation"},
    {"old_unique_name": "Mechanistic-Model-Based Social Simulation", "new_unique_name": "Mechanistic Models"},
    {"old_unique_name": "Empirical-and-Statistical-Model-Based Social Simulation", "new_unique_name": "Graph-Based Models"},
    {"old_unique_name": "Agent-Based Social Simulation", "new_unique_name": "LLM-Empowered Agent-Based Modeling"},
    {"old_unique_name": "Other-Based Social Simulation", "new_unique_name": "Modeling Method"},
    {"old_unique_name": "Individual-Oriented Social Simulation", "new_unique_name": "Individual-Oriented Simulation"},
    {"old_unique_name": "Group-Oriented Social Simulation", "new_unique_name": "Group-Oriented Simulation"},
    {"old_unique_name": "Social Simulation for Military", "new_unique_name": "Application Domain"},
    {"old_unique_name": "Social Simulation for Economy", "new_unique_name": "Economy and Politics"},
    {"old_unique_name": "Social Simulation for Education", "new_unique_name": "Application Domain"},
    {"old_unique_name": "Social Simulation for Games", "new_unique_name": "Psychology, Games, and Narrative"},
    {"old_unique_name": "Social Simulation for Embodied Intelligence", "new_unique_name": "Embodied Intelligence"},
    {"old_unique_name": "Social Simulation for Politics", "new_unique_name": "Economy and Politics"},
    {"old_unique_name": "Social Simulation for Psychology", "new_unique_name": "Psychology, Games, and Narrative"},
    {"old_unique_name": "Social Simulation for Sociology", "new_unique_name": "Sociology and Social Media"},
    {"old_unique_name": "Social Simulation for Social Media", "new_unique_name": "Sociology and Social Media"},
    {"old_unique_name": "Social Simulation for Other Fields", "new_unique_name": "Application Domain"},
    {"old_unique_name": "Social Value and Bias for Social Simulation", "new_unique_name": "Simulation"},
    {"old_unique_name": "Town/Community Simulation", "new_unique_name": "Simulation"},
]


def _category(unique_name, order, predecessor_category, description, *, name=None):
    """构造结构一致的分类记录，减少配置字段漂移。"""
    return {
        "unique_name": unique_name,
        "order": order,
        "name": name or unique_name,
        "predecessor_category": predecessor_category,
        "enabled": True,
        "description": description,
    }


CATEGORIES_CONFIG = {
    "config_version": "3.1",
    "last_updated": "2026-07-27",
    "categories": [
        # 工程兜底根分类。
        _category("Uncategorized", 0, None, "[一级分类] - 未分类"),

        # Figure 2 的四个认知层级。
        _category("Perception", 100, None, "[一级分类] - 感知：识别社会信号与状态"),
        _category("Understanding", 101, None, "[一级分类] - 理解：建模社会结构、关系与行为模式"),
        _category("Generation", 102, None, "[一级分类] - 生成：产生具有社会意义的内容、对话与干预"),
        _category("Simulation", 103, None, "[一级分类] - 仿真：重建动态社会过程并探索可能未来"),
        _category("Other", 200, None, "[一级分类] - 其他"),

        # Perception -------------------------------------------------------
        _category("Content-Level Perception", 10, "Perception", "[二级分类]（Perception）- 内容级感知"),
        _category("Hate Speech Analysis", 10, "Content-Level Perception", "[三级分类]（Content-Level Perception）- 仇恨言论分析"),
        _category("Misinformation Analysis", 20, "Content-Level Perception", "[三级分类]（Content-Level Perception）- 虚假信息分析"),
        _category("Machine-Generated Content Detection", 30, "Content-Level Perception", "[三级分类]（Content-Level Perception）- 机器生成内容检测"),
        _category("Sentiment Analysis", 40, "Content-Level Perception", "[三级分类]（Content-Level Perception）- 情感分析"),
        _category("Discourse and Pragmatic Analysis", 50, "Content-Level Perception", "[三级分类]（Content-Level Perception）- 语篇与语用分析"),
        _category("User-Level Perception", 20, "Perception", "[二级分类]（Perception）- 用户级感知"),
        _category("User Stance Detection", 10, "User-Level Perception", "[三级分类]（User-Level Perception）- 用户立场检测"),
        _category("Malicious User Detection", 20, "User-Level Perception", "[三级分类]（User-Level Perception）- 恶意与异常用户检测"),

        # Understanding ----------------------------------------------------
        _category("Structural and Discourse Modeling", 10, "Understanding", "[二级分类]（Understanding）- 结构与语篇建模"),
        _category("Event Extraction", 10, "Structural and Discourse Modeling", "[三级分类]（Structural and Discourse Modeling）- 事件抽取"),
        _category("Topic Modeling", 20, "Structural and Discourse Modeling", "[三级分类]（Structural and Discourse Modeling）- 主题建模"),
        _category("Network and Propagation Understanding", 20, "Understanding", "[二级分类]（Understanding）- 网络与传播理解"),
        _category("Meme and Multimodal Understanding", 10, "Network and Propagation Understanding", "[三级分类]（Network and Propagation Understanding）- 模因与多模态理解"),
        _category("Social Popularity Prediction", 20, "Network and Propagation Understanding", "[三级分类]（Network and Propagation Understanding）- 社交流行度预测"),
        _category("Information Diffusion Analysis", 30, "Network and Propagation Understanding", "[三级分类]（Network and Propagation Understanding）- 信息扩散分析"),
        _category("User-Level Understanding", 30, "Understanding", "[二级分类]（Understanding）- 用户与社区层级理解"),
        _category("User Profiling", 10, "User-Level Understanding", "[三级分类]（User-Level Understanding）- 用户画像"),
        _category("Community Detection and Analysis", 20, "User-Level Understanding", "[三级分类]（User-Level Understanding）- 社区检测与分析"),

        # Generation -------------------------------------------------------
        _category("Social Content Generation", 10, "Generation", "[二级分类]（Generation）- 社交内容生成"),
        _category("Comment Generation", 10, "Social Content Generation", "[三级分类]（Social Content Generation）- 评论生成"),
        _category("Social Summarization", 20, "Social Content Generation", "[三级分类]（Social Content Generation）- 社交摘要生成"),
        _category("Socially-Aware Dialogue Generation", 20, "Generation", "[二级分类]（Generation）- 社会感知对话生成"),
        _category("Personalized Dialogue Generation", 10, "Socially-Aware Dialogue Generation", "[三级分类]（Socially-Aware Dialogue Generation）- 个性化对话生成"),
        _category("Empathetic Dialogue Generation", 20, "Socially-Aware Dialogue Generation", "[三级分类]（Socially-Aware Dialogue Generation）- 同理心对话生成"),
        _category("Strategic and Persuasive Dialogue Generation", 30, "Socially-Aware Dialogue Generation", "[三级分类]（Socially-Aware Dialogue Generation）- 策略性与说服性对话生成"),
        _category("Social Intervention", 30, "Generation", "[二级分类]（Generation）- 社会干预"),
        _category("Misinformation Generation", 10, "Social Intervention", "[三级分类]（Social Intervention）- 虚假信息生成"),
        _category("Counter-Hate Speech Generation", 20, "Social Intervention", "[三级分类]（Social Intervention）- 反仇恨言论生成"),
        _category("Evidence-Grounded Rumor Refutation", 30, "Social Intervention", "[三级分类]（Social Intervention）- 基于证据的谣言反驳"),
        _category("Content Moderation and Detoxification", 40, "Social Intervention", "[三级分类]（Social Intervention）- 内容审核与净化"),

        # Simulation：严格采用方法、规模、应用领域三个正交维度。----------
        _category("Modeling Method", 10, "Simulation", "[二维度]（Simulation）- 建模方法"),
        _category("Mechanistic Models", 10, "Modeling Method", "[三维度值]（Modeling Method）- 基于显式方程、规则或过程动力学的机制模型"),
        _category("Graph-Based Models", 20, "Modeling Method", "[三维度值]（Modeling Method）- 显式表示拓扑与多尺度社会结构的图模型"),
        _category("LLM-Empowered Agent-Based Modeling", 30, "Modeling Method", "[三维度值]（Modeling Method）- 由大语言模型赋能的智能体建模"),
        _category("Simulation Scale", 20, "Simulation", "[二维度]（Simulation）- 仿真规模"),
        _category("Micro-Level Social Simulation", 10, "Simulation Scale", "[三维度值]（Simulation Scale）- 个体与群体交互层面的微观社会仿真"),
        _category("Individual-Oriented Simulation", 10, "Micro-Level Social Simulation", "[四级分类]（Micro-Level Social Simulation）- 单个社会智能体的角色、认知、行为与交互模式仿真"),
        _category("Group-Oriented Simulation", 20, "Micro-Level Social Simulation", "[四级分类]（Micro-Level Social Simulation）- 多智能体集体推理、决策、心理、偏差与合作演化仿真"),
        _category("Macro-Level Social Simulation", 20, "Simulation Scale", "[三维度值]（Simulation Scale）- 总体状态、涌现现象与长期演化的宏观社会仿真"),
        _category("Macro Social Alignment", 10, "Macro-Level Social Simulation", "[四级分类]（Macro-Level Social Simulation）- 对真实人口分布、态度、互动与结构模式的宏观对齐"),
        _category("Macro Social Phenomena Analysis", 20, "Macro-Level Social Simulation", "[四级分类]（Macro-Level Social Simulation）- 信息扩散、极化、集体行动与干预效果等宏观社会现象分析"),
        _category("Application Domain", 30, "Simulation", "[二维度]（Simulation）- 应用领域"),
        _category("Sociology and Social Media", 10, "Application Domain", "[三维度值]（Application Domain）- 社会学、计算社会科学与社交媒体"),
        _category("Economy and Politics", 20, "Application Domain", "[三维度值]（Application Domain）- 经济与政治制度中的策略行为"),
        _category("Psychology, Games, and Narrative", 30, "Application Domain", "[三维度值]（Application Domain）- 心理、游戏与叙事场景"),
        _category("Embodied Intelligence", 40, "Application Domain", "[三维度值]（Application Domain）- 具身智能与未来应用领域"),
    ],
    "categories_change_list": CATEGORIES_CHANGE_LIST,
}


def validate_categories_config():
    """验证分类唯一性、层级完整性与迁移规则。"""
    errors = []
    categories = CATEGORIES_CONFIG["categories"]
    categories_by_unique = {}

    for category in categories:
        unique_name = category.get("unique_name")
        if not isinstance(unique_name, str) or not unique_name.strip():
            errors.append(f"分类缺少有效 unique_name: {category}")
            continue
        if unique_name in categories_by_unique:
            errors.append(f"unique_name {unique_name} 重复")
        categories_by_unique[unique_name] = category

        if not isinstance(category.get("order"), (int, float)):
            errors.append(f"分类 {unique_name} 的 order 必须是数字")
        if not str(category.get("name", "")).strip():
            errors.append(f"分类 {unique_name} 的 name 不能为空")

    for unique_name, category in categories_by_unique.items():
        predecessor = category.get("predecessor_category")
        if predecessor is None:
            continue
        if not isinstance(predecessor, str) or predecessor not in categories_by_unique:
            errors.append(f"分类 {unique_name} 的父分类不存在: {predecessor!r}")
        elif predecessor == unique_name:
            errors.append(f"分类 {unique_name} 的父分类不能指向自己")

    for unique_name, category in categories_by_unique.items():
        seen = {unique_name}
        predecessor = category.get("predecessor_category")
        while predecessor is not None:
            if predecessor in seen:
                errors.append(f"分类 {unique_name} 的 predecessor_category 存在循环引用")
                break
            seen.add(predecessor)
            parent = categories_by_unique.get(predecessor)
            if parent is None:
                break
            predecessor = parent.get("predecessor_category")

    active_names = {
        name.casefold()
        for name, category in categories_by_unique.items()
        if category.get("enabled", True)
    }
    seen_old_names = set()
    for rule in CATEGORIES_CONFIG.get("categories_change_list", []):
        old_name = str(rule.get("old_unique_name", "") or "").strip()
        new_name = str(rule.get("new_unique_name", "") or "").strip()
        old_key = old_name.casefold()
        if not old_name or not new_name:
            errors.append(f"分类变更规则不完整: {rule}")
            continue
        if old_key in seen_old_names:
            errors.append(f"分类变更规则重复定义旧分类: {old_name}")
        seen_old_names.add(old_key)
        if old_key in active_names:
            errors.append(f"分类变更规则的旧分类仍处于启用状态: {old_name}")
        target = categories_by_unique.get(new_name)
        if target is None:
            errors.append(f"分类变更规则 {old_name} 的目标不存在: {new_name}")
        elif not target.get("enabled", True):
            errors.append(f"分类变更规则 {old_name} 的目标未启用: {new_name}")

    return len(errors) == 0, errors


if __name__ == "__main__":
    is_valid, error_list = validate_categories_config()
    if is_valid:
        print("[OK] 分类配置验证通过")
    else:
        print("[ERROR] 分类配置验证失败:")
        for error in error_list:
            print(f"   - {error}")
        raise SystemExit(1)
