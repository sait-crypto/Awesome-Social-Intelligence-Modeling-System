# CATEGORIES_CHANGE_LIST - 快速参考

## 📌 基本概念

将分类从 `old_unique_name` 自动转换为 `new_unique_name`。

## 🔧 快速使用

### 添加一个变更规则

编辑 `config/categories_config.py`：

```python
CATEGORIES_CHANGE_LIST = [
    {
        "old_unique_name": "旧名称",
        "new_unique_name": "新名称",
    },
]
```

### 就这么简单！

系统会自动：
- ✅ 转换所有旧数据
- ✅ 应用于 Excel 和 JSON 文件
- ✅ 应用于 submit_gui
- ✅ 应用于数据库加载

## 💡 常见场景

### 场景 1：简单重命名
```python
{
    "old_unique_name": "Sentiment Analysis",
    "new_unique_name": "Sentiment Understanding",
}
```

### 场景 2：分类合并
```python
{
    "old_unique_name": "Topic A",
    "new_unique_name": "Topic Combined",
},
{
    "old_unique_name": "Topic B",
    "new_unique_name": "Topic Combined",
}
```

### 场景 3：大规模重构
```python
CATEGORIES_CHANGE_LIST = [
    {"old_unique_name": "A", "new_unique_name": "A_new"},
    {"old_unique_name": "B", "new_unique_name": "B_new"},
    {"old_unique_name": "C", "new_unique_name": "C_new"},
]
```

## 🎯 工作原理

```
输入值 (如："Sentiment Analysis")
    ↓
检查 CATEGORIES_CHANGE_LIST
    ├─ 找到匹配？ → 转换为新值
    └─ 无匹配？ → 继续
    ↓
进行常规分类查询
    ↓
输出规范化值 (如："Sentiment Understanding")
```

## 📊 查看日志

当规则被应用时，会输出：
```
应用分类变更规则：'Sentiment Analysis' -> 'Sentiment Understanding'
```

## ✅ 验证实现

```bash
# 快速验证
python scripts/verify_implementation.py

# 完整测试
python scripts/integration_test_changes.py
```

## 📚 更多信息

- 完整指南：[CATEGORIES_CHANGE_LIST_GUIDE.md](CATEGORIES_CHANGE_LIST_GUIDE.md)
- 实现总结：[IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)
- 测试脚本：`scripts/test_category_change_list.py`
- 演示脚本：`scripts/demo_category_changes.py`

## ⚠️ 注意

1. **顺序很重要**：按列表顺序检查，第一个匹配立即应用
2. **避免冲突**：不要为同一个 old_unique_name 创建多个规则
3. **保留历史**：处理后保留规则用于审计
4. **备份数据**：大规模变更前备份数据文件

## 🚀 快速开始

1. 找到需要变更的分类名称
2. 在 CATEGORIES_CONFIG 中更新定义
3. 在 CATEGORIES_CHANGE_LIST 中添加规则
4. 完成！系统自动处理

## 💬 示例

**需求**：将 "Sentiment Analysis" 改为 "Sentiment Understanding"

**步骤**：

编辑 `config/categories_config.py`：

```python
# 1. 修改分类定义
{
    "unique_name": "Sentiment Understanding",  # ← 改这里
    "order": 2,
    "name": "Sentiment Understanding",
    "predecessor_category": "Content-Level Perception",
    "enabled": True,
}

# 2. 添加变更规则
CATEGORIES_CHANGE_LIST = [
    {
        "old_unique_name": "Sentiment Analysis",
        "new_unique_name": "Sentiment Understanding",
    },
]
```

**结果**：✅ 所有旧数据自动转换

---

**最后更新**：2026-01-15
**状态**：✅ 完全实现并测试通过
