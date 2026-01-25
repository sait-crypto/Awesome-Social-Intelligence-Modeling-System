"""Test if coloring code runs"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.core.database_manager import DatabaseManager

def test_save():
    """Test saving database to trigger coloring code"""
    
    db = DatabaseManager()
    
    # Load database
    df = db.load_database()
    papers = db.update_utils.excel_to_paper(df, only_non_system=False, skip_invalid=False)
    
    print(f"论文数: {len(papers)}")
    print(f"保存数据库...")
    
    # Save back
    excel_data = db.update_utils.paper_to_excel(papers, only_non_system=False, skip_invalid=False)
    db.save_database(excel_data, password="")
    
    print(f"保存完成")

if __name__ == "__main__":
    test_save()
