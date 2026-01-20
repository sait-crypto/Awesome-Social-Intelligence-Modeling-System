## invalid_fields 字段验证说明

### 概述
`invalid_fields` 是一个系统字段，用于记录论文中哪些字段存在验证问题。该字段的值应该是由逗号或中文逗号分隔的字段order列表。

### 验证规则
`invalid_fields` 字段的验证应包括以下规则：

1. **允许为空**：空字符串、None 或仅包含空格的字符串都是有效的
2. **分隔符**：支持使用英文逗号 `,` 或中文逗号 `，` 作为分隔符
3. **每个数字必须是非负整数（≥ 0）**：
   - ✓ 有效：`"0"`, `"1"`, `"0,1,2"`, `"1，2，3"`
   - ✗ 无效：`"-1"`, `"1.5"`, `"abc"`, `"1,2,-3,4"`
4. **支持带空格的格式**：分隔符两侧的空格会被自动清理
   - ✓ 有效：`"1, 2, 3"`, `"1 ， 2 ， 3"`

### 实现细节

#### 验证函数
在 `src/utils.py` 中添加了 `validate_invalid_fields()` 函数：

```python
def validate_invalid_fields(invalid_fields: str) -> Tuple[bool, str]:
    """
    验证 invalid_fields 字段
    返回: (是否有效, 错误信息)
    """
```

该函数会：
1. 处理空值（返回有效）
2. 按逗号分割字符串
3. 过滤空字符串部分
4. 验证每个部分是否都是非负整数

#### 集成到验证流程
在 `src/core/database_model.py` 的 `Paper.validate_paper_fields()` 方法中集成了验证：
- 当 `invalid_fields` 不为空时，调用验证函数
- 如果验证失败，将错误信息添加到验证错误列表中
- 同时将 `invalid_fields` 本身标记为无效字段

### 测试用例

所有测试用例都位于 `test_invalid_fields_validation.py` 和 `test_paper_invalid_fields_integration.py`

运行测试：
```bash
python test_invalid_fields_validation.py          # 单元测试
python test_paper_invalid_fields_integration.py   # 集成测试
```

### 使用场景

1. **导入数据时的验证**：当从 JSON 或 Excel 导入论文数据时，验证 `invalid_fields` 的格式
2. **数据库保存前验证**：防止无效的 `invalid_fields` 值被保存到数据库
3. **用户输入验证**：在 GUI 中编辑论文时，验证用户输入的 `invalid_fields`

### 错误信息示例

当验证失败时，会显示具体的错误信息：
- `"invalid_fields 中含有非整数值: 'abc'（应该是非负整数）"`
- `"invalid_fields 中含有非整数值: '1.5'（应该是非负整数）"`
- `"invalid_fields 中含有负数: -1（应该是非负整数）"`
