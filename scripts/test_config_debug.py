"""Debug why invalid_fields coloring is not applied"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.core.database_manager import DatabaseManager
from src.core.config_loader import get_config_instance

def test_config_and_columns():
    """Test config and column detection"""
    
    db = DatabaseManager()
    config = get_config_instance()
    
    # Load database
    df = db.load_database()
    papers = db.update_utils.excel_to_paper(df, only_non_system=False, skip_invalid=False)
    
    print(f"=== 配置和列信息 ===")
    
    # Check conflict_row_name
    conflict_row_name = config.get_tag_field("conflict_marker", "table_name")
    print(f"conflict_marker 列名: {conflict_row_name}")
    print(f"conflict_marker 在 df.columns 中: {conflict_row_name in df.columns}")
    
    # Check invalid_row_name
    invalid_row_name = config.get_tag_field("invalid_fields", "table_name")
    print(f"invalid_fields 列名: {invalid_row_name}")
    print(f"invalid_fields 在 df.columns 中: {invalid_row_name in df.columns}")
    
    # Show all columns
    print(f"\nDataframe 中的所有列 ({len(df.columns)} 列):")
    for i, col in enumerate(df.columns):
        print(f"  {i}: {col}")
    
    # Check if condition would pass
    print(f"\n=== 条件检查 ===")
    print(f"conflict_row_name in df.columns: {conflict_row_name in df.columns}")
    if conflict_row_name in df.columns:
        print("✓ 条件满足，着色代码会执行")
    else:
        print("✗ 条件不满足，着色代码不会执行")

if __name__ == "__main__":
    test_config_and_columns()
