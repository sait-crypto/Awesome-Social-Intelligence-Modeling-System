#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试分类变更列表实际应用的演示脚本

这个脚本演示如何：
1. 临时添加一个变更规则
2. 查看 normalize_category_value 如何应用这个规则
3. 验证变更的生效
"""
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.core.config_loader import get_config_instance
from src.core.update_file_utils import UpdateFileUtils


def test_with_change_rule():
    """测试添加了变更规则的情况"""
    print("\n" + "="*60)
    print("测试：应用分类变更规则")
    print("="*60)
    
    config = get_config_instance()
    utils = UpdateFileUtils()
    
    # 模拟在配置中添加一个变更规则
    print("\n📝 模拟场景：重命名分类 'Sentiment Analysis' -> 'Sentiment Understanding'")
    print("\n步骤 1: 创建临时配置副本并添加变更规则")
    
    # 创建一个临时的模拟类别配置
    test_config_snapshot = {
        'categories_change_list': [
            {
                'old_unique_name': 'Sentiment Analysis',
                'new_unique_name': 'Sentiment Understanding',
            }
        ]
    }
    
    print(f"临时变更规则: {test_config_snapshot['categories_change_list']}")
    
    # 创建一个模拟的配置对象用于测试
    class MockConfig:
        def __init__(self, real_config, change_list):
            self._real_config = real_config
            self._change_list = change_list
        
        def get_categories_change_list(self):
            return self._change_list
        
        def get_category_by_name_or_unique_name(self, identifier):
            return self._real_config.get_category_by_name_or_unique_name(identifier)
    
    mock_config = MockConfig(config, test_config_snapshot['categories_change_list'])
    
    print("\n步骤 2: 测试规范化旧的 unique_name")
    print("   处理包含旧分类标识的数据时...")
    
    # 模拟需要转换的数据
    test_data = [
        'Sentiment Analysis',  # 旧值，应该被转换
        'Sentiment Understanding',  # 新值，应该保持不变
        'Perception and Classification',  # 其他分类，不受影响
    ]
    
    print("\n结果:")
    for old_value in test_data:
        result = utils.normalize_category_value(old_value, mock_config)
        status = "✅ 转换" if old_value == 'Sentiment Analysis' else "✓ 保持"
        print(f"  {status} '{old_value:30}' -> '{result}'")
    
    print("\n步骤 3: 实际应用场景")
    print("   这个变更规则会自动应用在:")
    print("   - 从 Excel 文件加载论文时")
    print("   - 从 JSON 文件加载论文时")
    print("   - submit_gui 保存论文时")
    print("   - 更新文件时")
    print("\n   所有包含 'Sentiment Analysis' 的论文都会自动转换为使用 'Sentiment Understanding'")


def test_multiple_changes():
    """测试多个变更规则"""
    print("\n" + "="*60)
    print("测试：多个并发的变更规则")
    print("="*60)
    
    utils = UpdateFileUtils()
    
    # 模拟多个变更规则
    multiple_changes = [
        {
            'old_unique_name': 'Sentiment Analysis',
            'new_unique_name': 'Sentiment Understanding',
        },
        {
            'old_unique_name': 'Topic Modeling',
            'new_unique_name': 'Topic Mining',
        },
        {
            'old_unique_name': 'Community Detection',
            'new_unique_name': 'Community Structure Analysis',
        },
    ]
    
    print(f"\n配置了 {len(multiple_changes)} 个变更规则:")
    for i, change in enumerate(multiple_changes, 1):
        print(f"  {i}. '{change['old_unique_name']}' -> '{change['new_unique_name']}'")
    
    print("\n当处理数据时，normalize_category_value 会按顺序检查每个规则:")
    print("  1. 检查是否匹配第一个 old_unique_name")
    print("  2. 如果匹配，立即应用转换")
    print("  3. 如果不匹配，检查下一个规则")
    print("  4. 如果没有任何规则匹配，进行常规的分类查询")
    
    # 模拟数据处理
    test_papers = [
        'Sentiment Analysis',
        'Topic Modeling',
        'Community Detection',
        'Other Category',
    ]
    
    print("\n💾 模拟处理包含旧分类的论文数据:")
    for paper_category in test_papers:
        # 手动演示变更逻辑
        transformed = paper_category
        for change in multiple_changes:
            if paper_category == change['old_unique_name']:
                transformed = change['new_unique_name']
                break
        
        if transformed != paper_category:
            print(f"  ✅ '{paper_category:30}' -> '{transformed}'")
        else:
            print(f"  ✓  '{paper_category:30}' (无变更)")


def show_implementation_details():
    """展示实现细节"""
    print("\n" + "="*60)
    print("实现细节：变更规则是如何工作的")
    print("="*60)
    
    print("\n🔧 核心逻辑在 normalize_category_value() 中：")
    print("""
    def normalize_category_value(self, raw_val, config_instance):
        # ... 初始化代码 ...
        
        # 第一步：应用变更规则
        categories_change_list = config_instance.get_categories_change_list()
        for change_rule in categories_change_list:
            old_unique_name = change_rule.get('old_unique_name', '').strip()
            new_unique_name = change_rule.get('new_unique_name', '').strip()
            if old_unique_name and new_unique_name and val == old_unique_name:
                print(f"应用分类变更规则：'{old_unique_name}' -> '{new_unique_name}'")
                val = new_unique_name  # 应用转换
                break
        
        # 第二步：进行常规的分类查询和验证
        category = config_instance.get_category_by_name_or_unique_name(val)
        if category:
            return category.get('unique_name', '')
        
        return val
    """)
    
    print("\n📊 流程图：")
    print("""
    输入 (raw_val)
         ↓
    初始化和清理
         ↓
    检查变更规则列表
    ├─ 找到匹配 → 应用转换 → 输出日志
    └─ 无匹配 → 继续
         ↓
    通过 get_category_by_name_or_unique_name 查询
    ├─ 找到分类 → 返回 unique_name
    └─ 未找到 → 返回原值
         ↓
    输出 (unique_name 或原值)
    """)


if __name__ == "__main__":
    print("\n" + "="*60)
    print("分类变更规则 - 实际应用演示")
    print("="*60)
    
    test_with_change_rule()
    test_multiple_changes()
    show_implementation_details()
    
    print("\n" + "="*60)
    print("✅ 演示完成")
    print("="*60)
    print("\n💡 要点回顾：")
    print("  1. CATEGORIES_CHANGE_LIST 允许你定义分类的变更映射")
    print("  2. normalize_category_value() 自动应用这些变更")
    print("  3. 变更是透明的 - 所有系统都会自动获得最新的分类标识")
    print("  4. 这使得重命名分类不需要手动修改所有数据")
    print("\n🚀 使用方式：")
    print("  1. 在 CATEGORIES_CONFIG 中修改分类的 unique_name")
    print("  2. 在 CATEGORIES_CHANGE_LIST 中添加映射规则")
    print("  3. 系统会自动处理所有旧数据的转换")
