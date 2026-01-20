#!/usr/bin/env python3
# ~/bin/excel2csv.py

import sys
import pandas as pd
from pathlib import Path

def excel_to_text(excel_path):
    """将Excel文件转换为可读文本用于对比"""
    try:
        # 读取Excel文件
        excel_path = Path(excel_path)
        
        # 读取所有工作表
        excel_file = pd.ExcelFile(excel_path)
        
        output_lines = []
        
        for sheet_name in excel_file.sheet_names:
            df = pd.read_excel(excel_file, sheet_name=sheet_name, header=None)
            
            # 添加工作表标题
            output_lines.append(f"=== Sheet: {sheet_name} ===")
            
            # 转换为文本表示
            for i, row in df.iterrows():
                # 每行最多显示10个单元格，避免太长
                row_str = " | ".join([str(cell)[:50] for cell in row[:10]])
                output_lines.append(f"Row {i:3d}: {row_str}")
            
            output_lines.append("")  # 空行分隔
        
        return "\n".join(output_lines)
        
    except Exception as e:
        return f"[Excel文件读取错误: {str(e)}]"

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("用法: excel2csv.py <excel文件路径>")
        sys.exit(1)
    
    print(excel_to_text(sys.argv[1]))