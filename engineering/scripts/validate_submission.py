"""
验证提交脚本（CSV/JSON）
功能：
1. 验证 submit_template.csv 和 submit_template.json 中的论文格式 (validate_paper_fields)
2. 验证论文是否为实质性新增（对比 origin/main 分支的模版内容，排除完全未修改的占位符）
3. 验证 figures/assets 目录下所有文件的格式
"""
import os
import sys
import subprocess
import tempfile
from pathlib import Path
from typing import List

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.config_loader import get_config_instance
from src.core.update_file_utils import get_update_file_utils
from src.core.database_model import Paper, is_duplicate_paper

def get_original_content(abs_path: str, temp_path: str, project_root: str) -> bool:
    """
    获取 origin/main 分支的文件内容并保存到临时路径
    """
    try:
        rel_path = Path(abs_path).resolve().relative_to(Path(project_root).resolve()).as_posix()
        # 使用 git show 获取 main 分支的文件内容
        # 注意：在 GitHub Actions checkout 时 fetch-depth: 0 才能获取 origin/main
        cmd = ["git", "show", f"origin/main:{rel_path}"]
        with open(temp_path, "wb") as f:
            subprocess.check_call(cmd, stdout=f, stderr=subprocess.DEVNULL)
        return True
    except ValueError:
        print(f"Warning: Path is outside project root: {abs_path}")
        return False
    except subprocess.CalledProcessError:
        print(f"Info: Original file {abs_path} not found in main branch (New file?).")
        return False
    except Exception as e:
        print(f"Warning: Failed to fetch original file {abs_path}: {e}")
        return False

def validate_papers(papers: List[Paper], original_papers: List[Paper], source_name: str) -> int:
    """
    验证论文列表
    返回: 有效且非重复的论文数量
    """
    config = get_config_instance()
    valid_count = 0

    print(f"\n--- Validating {source_name} ({len(papers)} items) ---")

    for i, paper in enumerate(papers):
        paper_idx = i + 1
        
        # 1. 字段验证 (使用 no_normalize=False 因为不会)
        is_valid, errors, _ = paper.validate_paper_fields(
            config, 
            check_required=True, 
            check_non_empty=True, 
            no_normalize=False 
        )

        if not is_valid:
            print(f"❌ [Item {paper_idx}] Validation Failed: {paper.title[:30]}...")
            for err in errors:
                print(f"   - {err}")
            continue

        # 2. 实质变更检测 (与原始模版对比)
        # complete_compare=True 表示全字段严格对比
        is_dup, _ = is_duplicate_paper(original_papers, paper, complete_compare=True)
        
        if is_dup:
            # 这是一个完全未修改的模版条目（或者是已存在的条目）
            print(f"⚠️ [Item {paper_idx}] Ignored (Unchanged/Duplicate from template): {paper.title[:30]}...")
            continue

        # 通过所有检查
        print(f"✅ [Item {paper_idx}] Valid New Submission: {paper.title[:30]}...")
        valid_count += 1

    return valid_count

def validate_figures(figure_dir: str, allowed_exts=None):
    """
    验证图片目录下的文件格式
    """
    print(f"\n--- Validating Figures in {figure_dir} ---")
    if not os.path.exists(figure_dir):
        print(f"Info: {figure_dir} does not exist, skipping.")
        return

    valid_exts = allowed_exts or {'.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp'}
    has_error = False

    for root, dirs, files in os.walk(figure_dir):
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext not in valid_exts:
                print(f"❌ Invalid file format: {os.path.join(root, file)}")
                has_error = True
    
    if has_error:
        print("Error: Invalid files found in figures directory.")
        sys.exit(1)
    else:
        print("Figures directory check passed.")

def main():
    config_loader = get_config_instance()
    utils = get_update_file_utils()
    settings = config_loader.settings
    project_root = str(config_loader.project_root)

    # 获取路径配置
    update_csv_path = settings['paths'].get('update_csv')
    update_json_path = settings['paths']['update_json']
    figure_dir = settings['paths']['figure_dir']
    assets_dir = settings['paths'].get('assets_dir')

    total_valid_submissions = 0

    # 创建临时目录用于存放原始模版
    with tempfile.TemporaryDirectory() as temp_dir:
        # ==================== 1. 验证 CSV ====================
        if update_csv_path and os.path.exists(update_csv_path):
            # 加载当前提交的 CSV
            try:
                success, current_csv_papers = utils.load_papers_from_csv(update_csv_path)
                if not success:
                    print("Error loading current CSV: parser returned failed status")
                    sys.exit(1)
            except Exception as e:
                print(f"Error loading current CSV: {e}")
                sys.exit(1)

            # 获取原始 CSV
            temp_csv_path = os.path.join(temp_dir, "original.csv")
            original_csv_papers = []
            if get_original_content(update_csv_path, temp_csv_path, project_root):
                try:
                    success, original_csv_papers = utils.load_papers_from_csv(temp_csv_path)
                    if not success:
                        original_csv_papers = []
                except Exception:
                    pass # 原始文件可能损坏或为空，视为无基准

            # 执行验证
            total_valid_submissions += validate_papers(
                current_csv_papers,
                original_csv_papers,
                "CSV Template"
            )
            

        # ==================== 2. 验证 JSON ====================
        if os.path.exists(update_json_path):
            # 加载当前提交的 JSON
            try:
                success, current_json_papers = utils.load_papers_from_json(update_json_path)
                if not success:
                    print("Error loading current JSON: parser returned failed status")
                    sys.exit(1)
            except Exception as e:
                print(f"Error loading current JSON: {e}")
                sys.exit(1)

            # 获取原始 JSON
            temp_json_path = os.path.join(temp_dir, "original.json")
            original_json_papers = []
            if get_original_content(update_json_path, temp_json_path, project_root):
                try:
                    success, original_json_papers = utils.load_papers_from_json(temp_json_path)
                    if not success:
                        original_json_papers = []
                except Exception:
                    pass

            # 执行验证
            total_valid_submissions += validate_papers(
                current_json_papers, 
                original_json_papers, 
                "JSON Template"
            )

    # ==================== 3. 验证图片/资源 ====================
    validate_figures(figure_dir)
    if assets_dir and assets_dir != figure_dir:
        validate_figures(
            assets_dir,
            {'.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.pdf'},
        )

    # ==================== 4. 最终判定 ====================
    print("-" * 50)
    if total_valid_submissions > 0:
        print(f"🎉 Validation Success! Found {total_valid_submissions} valid new paper(s).")
        sys.exit(0)
    else:
        print("❌ Validation Failed: No valid new papers found.")
        print("Possible reasons:")
        print("1. All entries failed format validation (check required fields).")
        print("2. All entries are identical to the repository template (did you fill them in?).")
        sys.exit(1)

if __name__ == "__main__":
    main()
