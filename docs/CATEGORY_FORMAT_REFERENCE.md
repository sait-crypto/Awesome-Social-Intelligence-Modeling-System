# 分类提取功能 - 快速参考

## 格式说明

分类以**分号分隔的字符串**形式存储在Paper对象的`category`字段中。

## 示例

### Zotero标签格式
```
tag: "cat Social Media Security"
tag: "cat Humor Generation;Sentiment Analysis"
```

### 提取后的格式
```python
paper.category = "Social Media Security;Humor Generation;Sentiment Analysis"
```

### 在代码中使用
```python
# 获取分类字符串
category_str = paper.category  
# "Social Media Security;Humor Generation;Sentiment Analysis"

# 转换为列表
categories = category_str.split(";") if category_str else []
# ["Social Media Security", "Humor Generation", "Sentiment Analysis"]

# 获取分类数量
count = len(categories)
# 3

# 遍历分类
for cat in categories:
    print(cat)
# Social Media Security
# Humor Generation
# Sentiment Analysis
```

## 特性

- ✅ 字符串类型：`str`
- ✅ 分隔符：分号（`;`）无空格
- ✅ 空分类：空字符串（`""`）
- ✅ 自动去重：重复分类只保留一次
- ✅ GUI兼容：通过`split(";")`可转换为列表

## 在Zotero中标记

1. 使用前缀 `cat ` （不区分大小写）
2. 单个标签可包含多个分类（用`;`分隔）
3. 示例：
   - `cat Social Media Security`
   - `cat Humor Generation;Sentiment Analysis`
   - `CAT Misinformation Analysis` （大写也可以）

## 验证

运行测试：
```bash
python test_category_format_validation.py
```
