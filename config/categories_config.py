"""
分类配置文件

重要说明：
1. unique_name字段是分类的唯一标识符，不可重复，用于内部存储和系统处理
2. order字段决定分类在Excel和README中的显示顺序，必须唯一
3. enabled=false的分类会被系统忽略，相关论文不会出现在该分类下
4. primary_category字段用于表示二级分类所属的一级分类，一级分类的primary_category应为None。
   注意：`primary_category` 应使用父类的 `unique_name` 字符串进行引用，**不要使用 `order` 作为标识**。order 仅用于显示排序，可随时修改。
5. name字段用于README中的显示，可与其他分类重复。系统支持按name查询分类但会输出警告（建议使用unique_name）
6. 请勿随意修改已有分类的unique_name和order，以免影响已有数据

类别标识规则：
- name 和 unique_name 都可用于表示一个分类，但建议统一使用 unique_name
- 使用 name 进行查询时，系统会返回第一个匹配的分类，并输出 DeprecationWarning
- 内部存储始终使用 unique_name 作为标识（在paper_database、submit_gui、更新文件等处）
- 仅在 README 生成时使用 name 作为显示名称
"""

# =========================================类别变更列表=========================================
"""
因为分类需要频繁调整和优化，且已有论文数据需要保持一致性，因此需要一个自动化的类别变更处理机制
CATEGORIES_CHANGE_LIST用于自动处理类变更，
如果发生了：
    1.论文分类集体变更
    2.分类unique_name变更
建议在此列表中添加变更记录项，交由系统自动处理，将旧 unique_name 替换为新 unique_name，而非手动处理
(变更逻辑在normalize_category_value() 函数中)

列表元素格式：
    {
        "old_unique_name": "旧unique_name",   # 旧的唯一标识符（被替换）
        "new_unique_name": "新unique_name",   # 新的唯一标识符（替换目标）
    }

所有相关文件（更新文件Excel/JSON、database等）进行修改时会自动应用这些变更
"""

CATEGORIES_CHANGE_LIST = [
    # 在这里添加分类变更记录
    # 格式示例：
    # {
    #     "old_unique_name": "Base Techniques",
    #     "new_unique_name": "Hate Speech Analysis",
    # },
        {
        "old_unique_name": "Social Content Generation",   # 旧的唯一标识符（被替换）
        "new_unique_name": "Comment Generation",   # 新的唯一标识符（替换目标）
    }
]

# =========================================分类配置=========================================
CATEGORIES_CONFIG = {
    "config_version": "2.0",
    "last_updated": "2026-01-14",
    
    # 分类列表，按order排序
    "categories": [

        # ============一级分类===============
        {
            "unique_name": "Uncategorized",
            "order": 0,                     # 排序顺序，0为第一个
            "name": "Uncategorized",  # 显示名称
            "primary_category": None,# 所属一级分类，None表示本身为一级分类
            "enabled": True,                # 是否启用该分类
        },
        {
            "unique_name": "Base Techniques",
            "order": 99,                     # 排序顺序，0为第一个
            "name": "Base Techniques",  # 显示名称
            "primary_category": None,# None表示本身为1级分类
            "enabled": True,                # 是否启用该分类
        },
        {
            "unique_name": "Perception and Classification",
            "order": 100,                     # 排序顺序，0为第一个
            "name": "Perception and Classification",  # 显示名称
            "primary_category": None,# None表示本身为1级分类
            "enabled": True,                # 是否启用该分类
        },
        {
            "unique_name": "Understanding",
            "order": 101,                     # 排序顺序，0为第一个
            "name": "Understanding",  # 显示名称
            "primary_category": None,# None表示本身为1级分类
            "enabled": True,                # 是否启用该分类
        },
        {
            "unique_name": "Generation",
            "order": 102,                     # 排序顺序，0为第一个
            "name": "Generation",  # 显示名称
            "primary_category": None,# None表示本身为1级分类
            "enabled": True,                # 是否启用该分类
        },
        {
            "unique_name": "Simulation and Deduction",
            "order": 103,                     # 排序顺序，0为第一个
            "name": "Simulation and Deduction",  # 显示名称
            "primary_category": None,# None表示本身为1级分类
            "enabled": True,                # 是否启用该分类
        },
        {
            "unique_name": "Social Media Security",
            "order": 104,                     # 排序顺序，0为第一个
            "name": "Social Media Security",  # 显示名称
            "primary_category": None,# None表示本身为1级分类
            "enabled": True,                # 是否启用该分类
        },
        {
            "unique_name": "Other",
            "order": 200,
            "name": "Other",
            "primary_category": None,# None表示本身为1级分类
            "enabled": True,
        },
        
        # ============二级分类===============
        {
            "unique_name": "Hate Speech Analysis",
            "order": 1,                     
            "name": "Hate Speech Analysis",  # 显示名称
            "primary_category": "Perception and Classification",# 所属一级分类，使用一级分类的 `unique_name` 表示
            "enabled": True,                # 是否启用该分类
        },
        {
            "unique_name": "Sentiment Analysis",
            "order": 2,
            "name": "Sentiment Analysis",
            "primary_category": "Perception and Classification",
            "enabled": True,
        },
        {
            "unique_name": "Misinformation Analysis",
            "order": 3,
            "name": "Misinformation Analysis",
            "primary_category": "Perception and Classification",
            "enabled": True,
        },
        {
            "unique_name": "Multimodal Analysis",
            "order": 4,
            "name": "Meme Analysis",
            "primary_category": "Perception and Classification",
            "enabled": True,
        },
        {
            "unique_name": "Steganography Detection",
            "order": 5,
            "name": "Steganography Detection",
            "primary_category": "Perception and Classification",
            "enabled": True,
        },
        {
            "unique_name": "Event Extraction",
            "order": 6,
            "name": "Event Extraction",
            "primary_category": "Perception and Classification",
            "enabled": True,
        },
        {
            "unique_name": "Topic Modeling",
            "order": 7,
            "name": "Topic Modeling",
            "primary_category": "Understanding",
            "enabled": True,
        },
        {
            "unique_name": "User Opinion Mining",
            "order": 8,
            "name": "User Opinion Mining",
            "primary_category": "Perception and Classification",
            "enabled": True,
        },
        {
            "unique_name": "User Profiling",
            "order": 9,
            "name": "User Profiling",
            "primary_category": "Understanding",
            "enabled": True,
        },
        {
            "unique_name": "User Behavior Prediction",
            "order": 10,
            "name": "User Behavior Prediction",
            "primary_category": "Perception and Classification",
            "enabled": True,
        },
        {
            "unique_name": "Comment Generation",
            "order": 11,
            "name": "Comment Generation",
            "primary_category": "Generation",
            "enabled": True,
        },
        {
            "unique_name": "Information Diffusion Analysis",
            "order": 12,
            "name": "Information Diffusion Analysis",
            "primary_category": "Simulation and Deduction",
            "enabled": True,
        },
        {
            "unique_name": "Macrosocial Phenomena Analysis",
            "order": 13,
            "name": "Macrosocial Phenomena Analysis",
            "primary_category": "Simulation and Deduction",
            "enabled": True,
        },
        {
            "unique_name": "Social Simulation",
            "order": 14,
            "name": "Social Simulation",
            "primary_category": "Simulation and Deduction",
            "enabled": True,
        },
        {
            "unique_name": "Malicious Bot Detection",
            "order": 15,
            "name": "Malicious Bot Detection",
            "primary_category": "Perception and Classification",
            "enabled": True,
        },
        {
            "unique_name": "Community Detection",
            "order": 16,
            "name": "Community Detection",
            "primary_category": "Perception and Classification",
            "enabled": True,
        },
        {
            "unique_name": "Dynamic Community Analysis",
            "order": 17,
            "name": "Dynamic Community Analysis",
            "primary_category": "Simulation and Deduction",
            "enabled": True,
        },
        {
            "unique_name": "Social Psychological Phenomena Analysis",
            "order": 18,
            "name": "Social Psychological Phenomena Analysis",
            "primary_category": "Understanding",
            "enabled": True,
        },

    ],
    
    # ============= 分类变更列表 =============
    # 用于自动处理旧 unique_name 向新 unique_name 的转换
    # 当分类的 unique_name 发生变更时，在此列表中添加映射关系
    # normalize_category_value 会自动应用这些变更规则
    "categories_change_list": CATEGORIES_CHANGE_LIST,
}


# 验证函数
def validate_categories_config():
    """
    验证分类配置的有效性
    
    返回: (是否有效, 错误信息列表)
    """
    errors = []
    
    # 检查unique_name唯一性
    unique_names = {}
    for category in CATEGORIES_CONFIG["categories"]:
        unique_name = category.get("unique_name")
        if unique_name is None:
            errors.append(f"分类缺少unique_name字段: {category}")
            continue
            
        if unique_name in unique_names:
            errors.append(f"unique_name {unique_name} 重复")
        else:
            unique_names[unique_name] = True
    
    # 检查order唯一性，并建立order->category映射
    orders = {}
    categories_by_order = {}
    for category in CATEGORIES_CONFIG["categories"]:
        order = category.get("order")
        if order is None:
            errors.append(f"分类 {category.get('unique_name')} 缺少order字段")
            continue
            
        if order in orders:
            errors.append(f"order {order} 重复: {orders[order]} 和 {category['unique_name']}")
        else:
            orders[order] = category["unique_name"]
            categories_by_order[order] = category
    
    # 检查 primary_category 合法性：
    # - 一级分类（primary_category 为 None）应为 None
    # - 二级分类（primary_category 非 None）必须引用存在的一级分类（用 unique_name 表示），且被引用的分类的 primary_category 必须为 None
    # 为便于查找，建立 unique_name -> category 映射
    categories_by_unique = {c.get('unique_name'): c for c in CATEGORIES_CONFIG['categories']}
    for category in CATEGORIES_CONFIG["categories"]:
        pc = category.get("primary_category", None)
        if pc is None:
            continue
        # 如果 primary_category 非 None，则应为字符串并且存在于 categories_by_unique
        if not isinstance(pc, str):
            errors.append(f"分类 {category.get('unique_name')} 的 primary_category 应为父分类的 unique_name(str)，当前为 {pc!r}")
            continue
        if pc not in categories_by_unique:
            errors.append(f"分类 {category.get('unique_name')} 的 primary_category '{pc}' 不存在")
            continue
        parent = categories_by_unique[pc]
        if parent.get('primary_category') is not None:
            errors.append(f"分类 {category.get('unique_name')} 的 primary_category '{pc}' 指向的不是一级分类 ({parent.get('unique_name')})")

    # 检查name不为空
    for category in CATEGORIES_CONFIG["categories"]:
        name = category.get("name", "").strip()
        if not name:
            errors.append(f"分类 {category.get('unique_name')} 的name不能为空")
    
    return len(errors) == 0, errors

# 配置验证
if __name__ == "__main__":
    is_valid, error_list = validate_categories_config()
    if is_valid:
        print("✅ 分类配置验证通过")
    else:
        print("❌ 分类配置验证失败:")
        for error in error_list:
            print(f"   - {error}")
        exit(1)