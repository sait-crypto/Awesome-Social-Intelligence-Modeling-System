# GUI 多分类功能实现说明

## 概述
已完整实现 `submit_gui.py` 中的多分类支持功能。用户可以在 GUI 中为一篇论文添加多个分类，分类之间通过 `;`（英文分号）分隔。

## 核心设计

### 1. 数据存储格式
- **内部存储**：`paper.category` 字段存储为分号分隔的字符串，例如：`NLP;CV;DL`
- **GUI 显示**：每个分类在独立的一行显示，每行包含一个下拉框

### 2. GUI 布局

#### 第一行（初始行）
- 按钮文本：`+`（加号）
- 下拉框：选择第一个分类
- 功能：点击 `+` 按钮，添加下一行

#### 后续行
- 按钮文本：`-`（减号）
- 下拉框：选择额外分类
- 功能：点击 `-` 按钮，删除该行

### 3. 限制条件
- **最多分类数**：`min(max_categories_per_paper, 6)`
  - `max_categories_per_paper` 在 `config.ini` 中配置（默认值 4）
  - GUI 层限制为最多 6 行，防止界面过大
- **每行**：可选，可以留空

## 实现细节

### 关键方法

#### `_gui_add_category_row(value_display: str = "")`
**功能**：添加一行分类输入
- 如果这是第一行，按钮为 `+`，点击时添加新行
- 如果是后续行，按钮为 `-`，点击时删除该行
- 每次添加新行后，原有第一行的按钮会从 `+` 改为 `-`

**参数**：
- `value_display`（可选）：显示名称，会自动在下拉框中选中

**闭包处理**：
使用闭包 `make_button_callback()` 确保每个按钮回调正确引用对应的行框架

#### `_gui_clear_category_rows()`
**功能**：清除所有分类行
- 销毁所有行的 frame 组件
- 清空 `self.category_rows` 列表

#### `_gui_get_category_values() -> List[str]`
**功能**：从所有行中收集分类值（unique_name 列表）
- 遍历 `self.category_rows` 中的所有行
- 从下拉框获取显示名称 (display_name)
- 通过 `self.category_mapping` 转换为 unique_name
- 跳过空值
- 返回 unique_name 列表

#### `load_paper_to_form(paper)`
**功能**：将论文数据加载到表单
- 特殊处理 `category` 字段：
  1. 将 `paper.category` 字符串（`;` 分隔）拆分为 unique_name 列表
  2. 清除所有现有行
  3. 为每个 unique_name 创建一行：
     - 通过反向映射 `category_reverse_mapping` 获取显示名称
     - 调用 `_gui_add_category_row(display_name)` 创建行

#### `get_paper_from_form() -> Optional[Paper]`
**功能**：从表单获取论文数据
- 特殊处理 `category` 字段：
  1. 调用 `_gui_get_category_values()` 获取所有行的 unique_name 列表
  2. 用 `;` 连接成字符串
  3. 存储到 `paper_data['category']`
- 其他字段正常处理

#### `clear_form()`
**功能**：清空表单
- 清除 category 行：`_gui_clear_category_rows()`
- 添加初始空行：`_gui_add_category_row('')`

### 数据映射

```
category_mapping (display_name -> unique_name)
┌─────────────────────┬──────────────────────┐
│ Display Name        │ Unique Name          │
├─────────────────────┼──────────────────────┤
│ 自然语言处理        │ NLP                  │
│ 计算机视觉          │ CV                   │
│ 深度学习            │ DL                   │
└─────────────────────┴──────────────────────┘

category_reverse_mapping (unique_name -> display_name)
┌──────────────────────┬─────────────────────┐
│ Unique Name          │ Display Name        │
├──────────────────────┼─────────────────────┤
│ NLP                  │ 自然语言处理        │
│ CV                   │ 计算机视觉          │
│ DL                   │ 深度学习            │
└──────────────────────┴─────────────────────┘
```

## 工作流示例

### 1. 添加新论文
```
用户点击 [+论文]
↓
表单清空，显示初始 category 行（带 + 按钮）
↓
用户在第一行选择 "自然语言处理"
↓
用户点击 + 按钮
↓
新增第二行（带 - 按钮），第一行的 + 改为 -
↓
用户在第二行选择 "计算机视觉"
↓
用户点击第二行的 - 删除该行
↓
恢复为一行，第一行按钮恢复为 +
```

### 2. 加载现有论文
```
数据库中论文的 category: "NLP;CV;DL"
↓
load_paper_to_form() 被调用
↓
分割字符串: ["NLP", "CV", "DL"]
↓
反向映射获取显示名称:
  - NLP → "自然语言处理"
  - CV → "计算机视觉"  
  - DL → "深度学习"
↓
为每个分类创建行
↓
第一行按钮: +
第二、三行按钮: -
```

### 3. 保存论文
```
用户编辑完成，点击 [保存]
↓
get_paper_from_form() 被调用
↓
_gui_get_category_values() 收集所有行
↓
从下拉框读取显示名称:
  - Row 1: "自然语言处理"
  - Row 2: "计算机视觉"
  - Row 3: "深度学习"
↓
正向映射转换为 unique_name:
  - "自然语言处理" → NLP
  - "计算机视觉" → CV
  - "深度学习" → DL
↓
合并为字符串: "NLP;CV;DL"
↓
创建 Paper 对象并保存
```

## 配置参数

### config.ini
```ini
[database]
max_categories_per_paper = 4  # 一篇论文最多分类数
```

### categories_config.py
```python
# 活跃分类列表（每个分类包含 name、unique_name、enabled 等字段）
ACTIVE_CATEGORIES = [
    {'name': '自然语言处理', 'unique_name': 'NLP', 'enabled': True},
    {'name': '计算机视觉', 'unique_name': 'CV', 'enabled': True},
    ...
]
```

## 测试验证

已通过以下测试：

1. **基础多分类数据处理**
   - ✓ Paper 对象正确存储多分类字符串
   - ✓ 字符串正确分割为部分列表

2. **分类规范化**
   - ✓ 英文分号、中文分号都能正确处理
   - ✓ 空格被正确去除
   - ✓ 重复分类被正确去重

3. **论文验证**
   - ✓ 多分类论文通过验证
   - ✓ 无效分类被正确检测

4. **GUI 映射**
   - ✓ 正向映射（display_name → unique_name）正确
   - ✓ 反向映射（unique_name → display_name）正确

5. **值收集逻辑**
   - ✓ 从多行正确收集所有非空值
   - ✓ 正确转换为 unique_name
   - ✓ 正确用 `;` 连接

## 注意事项

1. **按钮管理**
   - 第一行的按钮始终与其他行不同
   - 添加新行时，原有行的按钮会自动更新
   - 删除行时，确保至少保留一行

2. **闭包陷阱**
   - 每个行的按钮回调使用 `make_button_callback()` 闭包
   - 确保每个按钮正确引用对应的行框架
   - 防止变量捕获错误

3. **映射初始化**
   - `category_mapping` 和 `category_reverse_mapping` 在 `create_form_fields()` 中初始化
   - 这两个映射在整个 GUI 生命周期内保持一致

4. **空值处理**
   - 可以有空行（用户未选择任何分类）
   - 收集值时会自动跳过空行
   - 保存时如果所有行都是空，`category` 字段会是空字符串

## 文件修改

修改的文件：
- `src/submit_gui.py`
  - `_gui_add_category_row()`：完全重写
  - `_gui_clear_category_rows()`：完全重写
  - `_gui_get_category_values()`：新增
  - `load_paper_to_form()`：大幅修改，category 部分完全重写
  - `get_paper_from_form()`：大幅修改，category 部分完全重写
  - `clear_form()`：已正确处理 category 清空

## 后续使用

用户现在可以：
1. 在 GUI 中为论文添加多个分类
2. 通过点击按钮动态添加/删除分类行
3. 保存和加载多分类论文
4. README 生成时，多分类论文会出现在相应的多个分类章节中
