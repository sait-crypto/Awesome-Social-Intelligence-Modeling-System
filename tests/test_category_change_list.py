#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
类别变更列表的测试和演示脚本

演示如何使用 CATEGORIES_CHANGE_LIST 实现自动化的类别变更处理：
1. 测试空的变更列表（当前状态）
2. 演示添加变更记录的方式
3. 验证 normalize_category_value 的变更应用逻辑
"""
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.core.config_loader import get_config_instance
from src.core.update_file_utils import UpdateFileUtils
from config.categories_config import CATEGORIES_CHANGE_LIST, CATEGORIES_CONFIG

def test_empty_change_list():
    """测试空的变更列表"""
    print("\n" + "="*60)
    print("测试 1: 空的 CATEGORIES_CHANGE_LIST")
    print("="*60)
    
    print(f"当前 CATEGORIES_CHANGE_LIST 内容: {CATEGORIES_CHANGE_LIST}")
    print(f"CATEGORIES_CONFIG 中的 categories_change_list: {CATEGORIES_CONFIG.get('categories_change_list')}")
    
    config = get_config_instance()
    change_list = config.get_categories_change_list()
    print(f"通过 config.get_categories_change_list() 获取: {change_list}")
    
    if not change_list:
        print("✅ 变更列表为空，这是正常的初始状态")
    else:
        print(f"⚠️ 变更列表非空: {change_list}")


def test_normalize_without_change():
    """测试在无变更规则下的 normalize_category_value 行为"""
    print("\n" + "="*60)
    print("测试 2: 无变更规则下的规范化")
    print("="*60)
    
    config = get_config_instance()
    utils = UpdateFileUtils()
    
    # 测试用例
    test_cases = [
        ("Perception and Classification", "应该返回该unique_name"),
        ("Sentiment Analysis", "应该返回该unique_name"),
        ("Unknown Category", "应该返回原值"),
        (None, "应该返回空字符串"),
        ("", "应该返回空字符串"),
    ]
    
    for test_val, description in test_cases:
        result = utils.normalize_category_value(test_val, config)
        print(f"  输入: {test_val!r:30} -> 结果: {result!r:30} ({description})")


def test_demonstrate_change_usage():
    """演示如何使用变更列表"""
    print("\n" + "="*60)
    print("测试 3: 演示变更列表的使用方式")
    print("="*60)
    
    print("\n📝 示例：如果要将 'Sentiment Analysis' 重命名为 'Sentiment Understanding'")
    print("   1. 在 categories_config.py 中修改分类定义:")
    print("      - unique_name 从 'Sentiment Analysis' 改为 'Sentiment Understanding'")
    print("\n   2. 在 CATEGORIES_CHANGE_LIST 中添加变更记录:")
    print("      {")
    print("          'old_unique_name': 'Sentiment Analysis',")
    print("          'new_unique_name': 'Sentiment Understanding',")
    print("      }")
    print("\n   3. 之后所有对旧 unique_name 的数据都会自动转换:")
    print("      - 更新 Excel 文件时自动转换")
    print("      - 更新 JSON 文件时自动转换")
    print("      - 从数据库加载论文时自动转换")
    print("      - submit_gui 保存论文时自动转换")


def test_demonstrate_change_application():
    """演示变更的应用（需要手动编辑 CATEGORIES_CHANGE_LIST）"""
    print("\n" + "="*60)
    print("测试 4: 模拟变更应用（如果有变更规则的话）")
    print("="*60)
    
    # 创建一个模拟的变更列表用于演示
    mock_change_list = [
        {
            "old_unique_name": "Test Old Name",
            "new_unique_name": "Test New Name",
        },
    ]
    
    print(f"\n模拟变更列表: {mock_change_list}")
    print("\n如果使用上述变更列表，normalize_category_value 会：")
    print("  1. 检测输入值是否匹配任何 old_unique_name")
    print("  2. 如果匹配，自动转换为对应的 new_unique_name")
    print("  3. 输出日志：应用分类变更规则：'Test Old Name' -> 'Test New Name'")
    print("\n这确保了所有包含旧 unique_name 的数据都能无缝升级到新标识。")


def list_all_categories():
    """列出所有当前的分类"""
    print("\n" + "="*60)
    print("当前所有分类列表")
    print("="*60)
    
    config = get_config_instance()
    categories = config.get_active_categories()
    
    print("\n一级分类:")
    for cat in categories:
        if cat.get('primary_category') is None:
            print(f"  {cat.get('unique_name'):40} (order: {cat.get('order'):3})")
    
    print("\n二级分类:")
    for cat in categories:
        if cat.get('primary_category') is not None:
            parent = cat.get('primary_category', 'N/A')
            print(f"  {cat.get('unique_name'):40} -> {parent}")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("类别变更列表 - 测试和演示脚本")
    print("="*60)
    
    test_empty_change_list()
    test_normalize_without_change()
    test_demonstrate_change_usage()
    test_demonstrate_change_application()
    list_all_categories()
    
    print("\n" + "="*60)
    print("✅ 所有测试完成")
    print("="*60)
    print("\n💡 总结:")
    print("  - CATEGORIES_CHANGE_LIST 现在已集成到配置系统中")
    print("  - normalize_category_value() 会自动应用变更规则")
    print("  - 添加新的变更规则只需编辑 CATEGORIES_CHANGE_LIST")
    print("  - 所有数据处理都会自动应用这些规则")
