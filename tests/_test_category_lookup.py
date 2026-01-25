#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
验证类别查询和规范化逻辑的脚本
"""
import sys
import os
import warnings

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'))

from src.core.config_loader import get_config_instance
from src.core.update_file_utils import get_update_file_utils

def test_category_lookup():
    """测试按 name 或 unique_name 查询分类"""
    print("=" * 70)
    print("测试：按 name 或 unique_name 查询分类")
    print("=" * 70)
    
    config = get_config_instance()
    
    # 测试 1: 按 unique_name 查询（应无警告）
    print("\n1. 按 unique_name 查询（预期：无警告）")
    print("-" * 70)
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        result = config.get_category_by_name_or_unique_name("Hate Speech Analysis")
        if result:
            print(f"✓ 查询成功: {result['unique_name']} (name={result['name']})")
            if w:
                print(f"⚠ 收到 {len(w)} 个警告（不应该有）")
            else:
                print("✓ 无警告（符合预期）")
        else:
            print("✗ 查询失败")
    
    # 测试 2: 按 name 查询（应有警告）
    print("\n2. 按 name 查询（预期：有 DeprecationWarning）")
    print("-" * 70)
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        result = config.get_category_by_name_or_unique_name("Hate Speech Analysis")
        if result:
            print(f"✓ 查询成功: {result['unique_name']} (name={result['name']})")
            if w:
                print(f"✓ 收到警告（符合预期）: {w[0].message}")
            else:
                print("⚠ 无警告（不符合预期）")
        else:
            print("✗ 查询失败")
    
    # 测试 3: 查询不存在的分类（应返回 None）
    print("\n3. 查询不存在的分类（预期：返回 None）")
    print("-" * 70)
    result = config.get_category_by_name_or_unique_name("NonExistentCategory")
    if result is None:
        print("✓ 返回 None（符合预期）")
    else:
        print(f"✗ 返回了非 None 值: {result}")


def test_category_normalization():
    """测试类别规范化（name -> unique_name）"""
    print("\n" + "=" * 70)
    print("测试：类别规范化")
    print("=" * 70)
    
    config = get_config_instance()
    update_utils = get_update_file_utils()
    
    test_cases = [
        ("Hate Speech Analysis", "Hate Speech Analysis", "按 unique_name 查询应返回 unique_name"),
        ("Sentiment Analysis", "Sentiment Analysis", "按 unique_name 查询应返回 unique_name"),
        ("", "", "空字符串应返回空字符串"),
        (None, "", "None 应返回空字符串"),
        ("NonExistent", "NonExistent", "不存在的分类应返回原值"),
    ]
    
    print("\n")
    for i, (input_val, expected, description) in enumerate(test_cases, 1):
        print(f"{i}. {description}")
        print(f"   输入: {input_val!r}")
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = update_utils.normalize_category_value(input_val, config)
            print(f"   输出: {result!r}")
            print(f"   预期: {expected!r}")
            if result == expected:
                print("   ✓ 通过")
            else:
                print("   ✗ 失败")
            if w:
                print(f"   ⚠ 警告: {w[0].message}")
        print()


def test_all_categories():
    """列出所有分类及其 unique_name"""
    print("\n" + "=" * 70)
    print("所有启用分类列表")
    print("=" * 70)
    
    config = get_config_instance()
    categories = config.get_active_categories()
    
    print(f"\n总共 {len(categories)} 个启用分类：\n")
    print(f"{'Order':<5} {'Unique Name':<40} {'Name':<40} {'Primary':<40}")
    print("-" * 130)
    
    for cat in sorted(categories, key=lambda x: x.get('order', 0)):
        order = cat.get('order', '?')
        unique_name = cat.get('unique_name', '')[:39]
        name = cat.get('name', '')[:39]
        primary = cat.get('primary_category', 'None')
        if primary is None:
            primary = '[一级分类]'
        
        print(f"{order:<5} {unique_name:<40} {name:<40} {primary:<40}")


if __name__ == "__main__":
    test_category_lookup()
    test_category_normalization()
    test_all_categories()
    
    print("\n" + "=" * 70)
    print("验证完成")
    print("=" * 70)
