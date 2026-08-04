# 从Zotero Meta数据提取分类功能说明

## 功能概述

系统现在支持从Zotero的Meta数据中自动提取论文分类信息。当从Zotero导入论文时，会自动识别tags字段中的分类标记，并填充到论文对象的category字段中。

**分类格式**：提取的分类以分号分隔的字符串形式存储，例如：`"Social Media Security;Humor Generation;Sentiment Analysis"`

## 使用方法

### 1. 在Zotero中标记分类

在Zotero中为论文条目添加标签（tags），使用以下格式：

```
cat <unique_name>
```

其中：
- `cat` 是分类标记前缀（不区分大小写，可以是 cat、Cat、CAT）
- 后面跟一个空格
- `<unique_name>` 是分类的唯一标识符（参考 `config/categories_config.py`）

### 2. 多个分类的表示方法

#### 方法一：使用多个标签
```
标签1: cat Social Media Security
标签2: cat Humor Generation
标签3: cat Sentiment Analysis
```

#### 方法二：在一个标签中用分号分隔
```
标签: cat Humor Generation;Frontier Applications;Sentiment Analysis
```

#### 方法三：混合使用
```
标签1: cat Social Media Security
标签2: cat Humor Generation;Frontier Applications
```

### 3. 从Zotero导入到系统

使用项目提供的Zotero插件 "One-Click Copy Metadata"：
1. 右键点击Zotero条目
2. 选择 "Copy Meta to JSON Format"
3. 在GUI界面点击 "📋 从Zotero Meta填充表单" 或 "📑 从Zotero新建论文"
4. 粘贴复制的Meta数据

系统会自动：
- 提取所有以 "cat " 开头的标签
- 解析分号分隔的多个分类
- 去除重复的分类
- 填充到论文的category字段

## 示例

### Zotero Meta JSON 格式
```json
{
  "title": "Example Paper on Social Media Analysis",
  "DOI": "10.1234/example.2024",
  "date": "2024-01-01",
  "creators": [
    {"creatorType": "author", "firstName": "John", "lastName": "Doe"}
  ],
  "tags": [
    {"tag": "cat Social Media Security"},
    {"tag": "cat Humor Generation;Frontier Applications"},
    {"tag": "machine learning"},
    {"tag": "nlp"}
  ]
}
```

### 提取结果
从上述JSON中会提取出以下分类字符串：
```
"Hate Speech Analysis;Misinformation Analysis;Frontier Applications"
```

即分类以**分号分隔的字符串**形式存储在Paper对象的category字段中。

注意：
- "machine learning" 和 "nlp" 不会被提取（因为没有 "cat " 前缀）
- 重复的分类会自动去重
- 分类之间用分号（`;`）连接，不含空格

## 可用分类列表

请参考 `config/categories_config.py` 中的分类配置。当前主要分类包括：

### 一级分类
- Perception
- Understanding
- Generation
- Simulation
- Other

### 二级分类（示例）
- Content-Level Perception
- User-Level Perception
- Structural and Discourse Modeling
- Network and Propagation Understanding
- User-Level Understanding
- Social Content Generation
- Socially-Aware Dialogue Generation
- Social Intervention
- Modeling Method
- Simulation Scale
  - Micro-Level Social Simulation
    - Individual-Oriented Simulation
    - Group-Oriented Simulation
  - Macro-Level Social Simulation
    - Macro Social Alignment
    - Macro Social Phenomena Analysis
- Application Domain
等...

完整列表请查看配置文件。

## 注意事项

1. **分类名称匹配**：tags中的分类名称应使用 `unique_name`（如 "Social Media Security"），而非显示名称
2. **大小写敏感**：分类名称本身是大小写敏感的，必须与配置文件中的 `unique_name` 完全匹配
3. **前缀不区分大小写**："cat"、"Cat"、"CAT" 都可以识别
4. **分隔符**：多个分类用分号（;）分隔，会自动处理前后空格
5. **去重**：重复的分类会自动去除，保留第一次出现的顺序

## 测试

项目包含完整的测试用例：
- `test_category_extraction.py` - 基本功能测试
- `test_category_edge_cases.py` - 边界情况测试

运行测试：
```bash
python test_category_extraction.py
python test_category_edge_cases.py
```

## 技术实现

实现位置：`src/process_zotero_meta.py`

核心方法：
- `_extract_categories_from_tags()` - 从tags数组中提取分类
- `_map_item_to_paper()` - 将Zotero条目映射为Paper对象（包含分类提取）

提取逻辑：
1. 遍历tags数组中的每个标签对象
2. 检查tag字段是否以 "cat "开头（不区分大小写）
3. 移除 "cat " 前缀，提取分类部分
4. 按分号分隔多个分类
5. 去重并保持顺序
6. 将分类列表转换为分号分隔的字符串
7. 返回字符串格式的分类（如 "分类1;分类2;分类3"）
