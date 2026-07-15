# 数据规范化方法中的数据保护机制

## 概述

为了保护数据库中已存在的论文数据，即使验证失败也不丢失，我们在四个数据规范化方法中添加了 `skip_invalid` 参数。

## 受影响的方法

以下四个方法在 `src/core/update_file_utils.py` 中：

1. **`json_to_paper()`** - 从JSON转换为Paper对象
2. **`excel_to_paper()`** - 从Excel转换为Paper对象  
3. **`paper_to_json()`** - 从Paper对象转换为JSON
4. **`paper_to_excel()`** - 从Paper对象转换为Excel

## 参数说明

### `skip_invalid: bool = False`

- **默认值**: `False`（不跳过）
- **默认行为**：保留所有论文，即使验证失败或包含 `invalid_fields`
- **使用场景**：
  - **False**: 用于处理数据库中现有的论文数据，确保数据不会因验证失败而丢失
  - **True**: 用于处理用户提交的新论文（如更新文件），可以过滤掉不规范的论文

## 详细说明

### json_to_paper() 和 excel_to_paper()

当验证失败时：
- **skip_invalid=False**（默认）：
  ```
  警告: 保留验证失败的论文: 论文标题...
  → 论文被保留并返回
  ```
- **skip_invalid=True**：
  ```
  警告: 跳过验证失败的论文: 论文标题...
  → 论文被跳过（不返回）
  ```

### paper_to_json() 和 paper_to_excel()

当论文包含 `invalid_fields` 时：
- **skip_invalid=False**（默认）：
  ```
  警告: 保留包含invalid_fields的论文: 论文标题...
  → 论文被保留并转换
  ```
- **skip_invalid=True**：
  ```
  警告: 跳过包含invalid_fields的论文: 论文标题...
  → 论文被跳过（不转换）
  ```

## 使用示例

### 处理数据库现有数据（保护模式）

```python
from src.core.update_file_utils import get_update_file_utils

utils = get_update_file_utils()

# 从Excel加载论文 - 保留所有论文
papers = utils.excel_to_paper(df, skip_invalid=False)  # 默认行为

# 转换回Excel - 保留所有论文
new_df = utils.paper_to_excel(papers, skip_invalid=False)  # 默认行为
```

### 处理用户提交的新论文（严格模式）

```python
from src.core.update_file_utils import get_update_file_utils

utils = get_update_file_utils()

# 从JSON加载用户提交的论文 - 过滤不规范的论文
papers = utils.json_to_paper(json_data, skip_invalid=True)

# 转换为JSON - 只输出规范的论文
clean_data = utils.paper_to_json(papers, skip_invalid=True)
```

## 重要提示

⚠️ **数据库安全**：在处理核心数据库（`paper_database.xlsx`）时，**始终使用默认值** `skip_invalid=False`，以确保数据不会因验证失败而丢失。

✅ **最佳实践**：
- 数据库操作：使用 `skip_invalid=False`（默认）
- 用户提交处理：使用 `skip_invalid=True`（严格验证）
- 数据清理：使用 `skip_invalid=True`（仅保留规范数据）

## 验证失败的情况

论文会因以下原因验证失败或标记为 `invalid_fields`：

1. **DOI格式无效**
2. **作者格式不规范**
3. **URL格式无效**
4. **日期格式不符合 YYYY-MM-DD**
5. **必填字段为空**
6. **分类无效**
7. **字段类型不匹配**
8. **其他验证规则不符**

这些不规范的论文会在 Excel 中显示为红色单元格（`invalid_fields` 列），便于用户识别和手动修正。
