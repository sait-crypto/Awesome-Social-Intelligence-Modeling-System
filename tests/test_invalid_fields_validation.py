#!/usr/bin/env python3
"""
测试 invalid_fields 字段验证功能
"""
import sys
sys.path.insert(0, '.')

from src.utils import validate_invalid_fields

def test_cases():
    """测试各种情况"""
    test_data = [
        # (输入, 期望有效, 描述)
        ("", True, "空字符串应该有效"),
        ("   ", True, "只有空格应该有效"),
        (None, True, "None 应该有效"),
        ("0", True, "单个 0 应该有效"),
        ("1", True, "单个数字应该有效"),
        ("0,1,2", True, "逗号分隔的数字应该有效"),
        ("0，1，2", True, "中文逗号分隔的数字应该有效"),
        ("1,2, 3 , 4", True, "带空格的逗号分隔数字应该有效"),
        ("1，2， 3 ， 4", True, "带空格的中文逗号分隔数字应该有效"),
        ("1,2,3,4,5", True, "多个数字应该有效"),
        ("-1", False, "负数应该无效"),
        ("1,2,-3,4", False, "包含负数应该无效"),
        ("1,abc,3", False, "包含非数字应该无效"),
        ("1.5", False, "浮点数应该无效"),
        ("1,2.5,3", False, "包含浮点数应该无效"),
        ("1, 2, abc", False, "包含字母应该无效"),
        ("1,", True, "末尾逗号应该有效（会被过滤）"),
        (",1,2", True, "开头逗号应该有效（会被过滤）"),
        ("1,,2", True, "中间空逗号应该有效（会被过滤）"),
        ("0,0,0", True, "重复的 0 应该有效"),
        ("10,20,30", True, "两位数应该有效"),
        ("100,200,300", True, "三位数应该有效"),
    ]
    
    print("=" * 70)
    print("测试 validate_invalid_fields 函数")
    print("=" * 70)
    
    passed = 0
    failed = 0
    
    for input_val, expected_valid, description in test_data:
        valid, error = validate_invalid_fields(input_val)
        
        status = "✓ PASS" if valid == expected_valid else "✗ FAIL"
        if valid == expected_valid:
            passed += 1
        else:
            failed += 1
        
        print(f"\n{status}")
        print(f"  输入: {repr(input_val)}")
        print(f"  描述: {description}")
        print(f"  期望有效: {expected_valid}")
        print(f"  实际有效: {valid}")
        if error:
            print(f"  错误信息: {error}")
    
    print("\n" + "=" * 70)
    print(f"测试结果: 通过 {passed}/{len(test_data)}, 失败 {failed}/{len(test_data)}")
    print("=" * 70)
    
    return failed == 0


if __name__ == "__main__":
    success = test_cases()
    sys.exit(0 if success else 1)
