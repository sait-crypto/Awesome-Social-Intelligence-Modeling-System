# 分类变更列表 (CATEGORIES_CHANGE_LIST) 使用指南

## 概述

`CATEGORIES_CHANGE_LIST` 是一个自动化的类别变更处理机制，用于管理分类标识的演变。当分类的 `unique_name` 发生变更时，无需手动修改所有历史数据，系统会自动应用变更规则将旧标识转换为新标识。

## 核心目标

- **自动化处理**：避免手动修改所有包含旧分类标识的数据
- **数据一致性**：确保所有论文数据在系统中保持一致的分类标识
- **透明转换**：用户无感知，系统自动应用变更
- **可追溯**：记录分类变更历史，便于审计和回溯

## 实现机制

### 1. CATEGORIES_CHANGE_LIST 定义

位置：`config/categories_config.py`

```python
CATEGORIES_CHANGE_LIST = [
    {
        "old_unique_name": "旧分类标识",
        "new_unique_name": "新分类标识",
    },
    # ... 更多变更规则 ...
]
```

### 2. 配置集成

`CATEGORIES_CHANGE_LIST` 被集成到 `CATEGORIES_CONFIG` 字典中：

```python
CATEGORIES_CONFIG = {
    "config_version": "2.0",
    "last_updated": "2026-01-14",
    "categories": [...],
    "categories_change_list": CATEGORIES_CHANGE_LIST,  # <- 变更列表
}
```

### 3. 获取变更列表

通过 `ConfigLoader` 获取：

```python
from src.core.config_loader import get_config_instance

config = get_config_instance()
change_list = config.get_categories_change_list()
# change_list = [{"old_unique_name": "...", "new_unique_name": "..."}, ...]
```

### 4. 自动应用逻辑

核心规范化函数：`UpdateFileUtils.normalize_category_value()`

```python
def normalize_category_value(self, raw_val, config_instance) -> str:
    # 步骤 1：应用变更规则
    categories_change_list = config_instance.get_categories_change_list()
    for change_rule in categories_change_list:
        old_unique_name = change_rule.get('old_unique_name', '').strip()
        new_unique_name = change_rule.get('new_unique_name', '').strip()
        if old_unique_name and new_unique_name and val == old_unique_name:
            # 找到匹配的变更规则，应用转换
            print(f"应用分类变更规则：'{old_unique_name}' -> '{new_unique_name}'")
            val = new_unique_name
            break
    
    # 步骤 2：进行常规的分类查询和验证
    category = config_instance.get_category_by_name_or_unique_name(val)
    if category:
        return category.get('unique_name', '')
    
    return val
```

## 应用点

变更规则会在以下场景自动应用：

### 1. 文件 I/O 操作
- **读取 Excel 文件**：`UpdateFileUtils.read_excel_file()` 后的规范化
- **读取 JSON 文件**：`UpdateFileUtils.read_json_file()` 后的规范化
- **写入文件**：保存前自动应用变更

### 2. GUI 交互
- **submit_gui 保存论文**：`submit_gui.save_all_papers()` 调用 `normalize_category_value()`
- **论文提交**：自动转换为最新的分类标识

### 3. 数据库操作
- **加载论文**：从数据库加载时应用变更
- **保存论文**：保存前应用变更确保一致性

### 4. 数据转换
- **DataFrame 规范化**：`normalize_dataframe_columns()` 应用规则
- **Paper 对象**：创建或更新时自动规范化

## 使用示例

### 示例 1：简单的分类重命名

**场景**：需要将 "Sentiment Analysis" 重命名为 "Sentiment Understanding"

**步骤**：

1. 在 `config/categories_config.py` 中修改分类定义：

```python
{
    "unique_name": "Sentiment Understanding",  # 改为新名称
    "order": 2,
    "name": "Sentiment Understanding",
    "primary_category": "Perception and Classification",
    "enabled": True,
}
```

2. 在 `CATEGORIES_CHANGE_LIST` 中添加变更记录：

```python
CATEGORIES_CHANGE_LIST = [
    {
        "old_unique_name": "Sentiment Analysis",
        "new_unique_name": "Sentiment Understanding",
    },
]
```

3. **系统会自动**：
   - 所有包含 "Sentiment Analysis" 的 Excel 论文在加载时转换为 "Sentiment Understanding"
   - 所有包含 "Sentiment Analysis" 的 JSON 论文在加载时转换为 "Sentiment Understanding"
   - submit_gui 中的论文保存时自动转换
   - 数据库中的论文在查询时自动转换

### 示例 2：批量分类重构

**场景**：大规模分类结构调整，涉及多个分类重命名

```python
CATEGORIES_CHANGE_LIST = [
    {
        "old_unique_name": "Sentiment Analysis",
        "new_unique_name": "Sentiment Understanding",
    },
    {
        "old_unique_name": "Topic Modeling",
        "new_unique_name": "Topic Mining",
    },
    {
        "old_unique_name": "Community Detection",
        "new_unique_name": "Community Structure Analysis",
    },
]
```

系统会按顺序检查每个规则，逐个应用匹配的变更。

### 示例 3：分类合并

**场景**：需要将两个小分类合并为一个

```python
CATEGORIES_CHANGE_LIST = [
    {
        "old_unique_name": "Small Category 1",
        "new_unique_name": "Merged Category",
    },
    {
        "old_unique_name": "Small Category 2",
        "new_unique_name": "Merged Category",
    },
]
```

两个旧分类的论文都会自动转换为使用合并后的分类。

## 工作流程

### 分类变更的完整工作流

```
1. 识别需要变更的分类
   ↓
2. 在 CATEGORIES_CONFIG 中修改分类定义
   ├─ 修改 unique_name（如果重命名）
   ├─ 修改 order（如果调整顺序）
   └─ 修改其他字段（如需要）
   ↓
3. 在 CATEGORIES_CHANGE_LIST 中添加映射规则
   ├─ old_unique_name: 旧的标识符
   └─ new_unique_name: 新的标识符
   ↓
4. 系统自动应用变更
   ├─ 文件 I/O 时自动转换
   ├─ 数据加载时自动转换
   └─ 数据保存时自动转换
   ↓
5. 验证数据一致性
   ├─ 查看 Excel/JSON 文件
   ├─ 查看数据库记录
   └─ 确认转换成功
```

## 注意事项

### ✅ 最佳实践

1. **及时记录**：分类变更后立即在 CATEGORIES_CHANGE_LIST 中添加记录
2. **保留历史**：不要删除已处理的变更规则，保留为历史记录
3. **备份数据**：在进行大规模变更前，备份所有数据文件
4. **验证结果**：变更后验证所有受影响的数据是否正确转换
5. **测试脚本**：使用提供的测试脚本验证变更规则的正确性

### ⚠️ 常见问题

**Q：能否删除已处理的变更规则？**
A：可以，但建议保留作为历史记录。删除前确保所有旧数据已转换完毕。

**Q：变更规则的顺序重要吗？**
A：顺序重要。系统按列表顺序检查规则，一旦找到匹配立即应用，然后停止检查。

**Q：如果有多个规则匹配同一个值怎么办？**
A：系统只应用第一个匹配的规则。应避免在列表中创建冲突的规则。

**Q：如何验证变更是否成功应用？**
A：
- 查看日志输出：`应用分类变更规则：'...' -> '...'`
- 检查 Excel/JSON 文件中的分类值
- 运行测试脚本：`python scripts/test_category_change_list.py`

**Q：变更后旧的 unique_name 还能使用吗？**
A：取决于 CATEGORIES_CONFIG 中的定义。如果旧 unique_name 已被删除，则无法查询。但在变更列表中保留映射可以持续转换旧数据。

## 相关文件

| 文件 | 作用 |
|------|------|
| `config/categories_config.py` | 定义 CATEGORIES_CHANGE_LIST 和 CATEGORIES_CONFIG |
| `src/core/config_loader.py` | 提供 `get_categories_change_list()` 方法 |
| `src/core/update_file_utils.py` | 在 `normalize_category_value()` 中应用变更 |
| `src/submit_gui.py` | 保存论文时调用规范化函数 |
| `scripts/test_category_change_list.py` | 测试脚本 |
| `scripts/demo_category_changes.py` | 演示脚本 |

## 调试和监控

### 启用详细日志

当应用变更规则时，系统会输出：
```
应用分类变更规则：'Sentiment Analysis' -> 'Sentiment Understanding'
```

### 运行测试脚本

```bash
python scripts/test_category_change_list.py
```

输出包括：
- 当前 CATEGORIES_CHANGE_LIST 内容
- 规范化测试结果
- 所有可用分类列表

### 运行演示脚本

```bash
python scripts/demo_category_changes.py
```

演示包括：
- 应用单个变更规则
- 应用多个并发规则
- 实现细节和流程图

## 总结

CATEGORIES_CHANGE_LIST 提供了一个优雅的方案来处理分类的演变：

- ✅ **自动化**：无需手动修改数据
- ✅ **一致性**：所有系统组件同步应用变更
- ✅ **可维护**：清晰的配置，易于追踪
- ✅ **可扩展**：支持批量变更和复杂场景
- ✅ **可回溯**：保留变更历史记录

通过合理使用这个机制，可以在保证数据完整性的前提下，灵活地调整分类结构。
