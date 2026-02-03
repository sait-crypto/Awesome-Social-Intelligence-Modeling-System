"""
提交系统的业务逻辑层
处理数据管理、文件读写、Git操作和Zotero集成
"""
import os
import sys
import threading
import subprocess
import time
from typing import Dict, List, Any, Optional, Tuple
import shutil
import configparser
import json

# 保持与原文件一致的路径处理
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.config_loader import get_config_instance
from src.core.database_model import Paper, is_same_identity
from src.core.update_file_utils import get_update_file_utils
from src.process_zotero_meta import ZoteroProcessor
from src.utils import clean_doi

# 锚定根目录
BASE_DIR = str(get_config_instance().project_root)

class SubmitLogic:
    """提交系统的业务逻辑控制器"""

    def __init__(self):
        # 加载配置
        self.config = get_config_instance()
        self.settings = get_config_instance().settings
        self.update_utils = get_update_file_utils()
        self.zotero_processor = ZoteroProcessor()
        
        # 论文数据列表
        self.papers: List[Paper] = []
        
        # 路径配置
        self.update_json_path = os.path.join(BASE_DIR, self.settings['paths']['update_json'])
        self.update_excel_path = os.path.join(BASE_DIR, self.settings['paths']['update_excel'])
        
        self.conflict_marker = self.settings['database']['conflict_marker']
        self.PLACEHOLDER = "to be filled in"


        self.figure_dir = self.settings['paths'].get('figure_dir', 'assets/figures/')
        self.paper_dir = self.settings['paths'].get('paper_dir', 'assets/papers/')
        # 确保目录存在
        os.makedirs(os.path.join(BASE_DIR, self.figure_dir), exist_ok=True)
        os.makedirs(os.path.join(BASE_DIR, self.paper_dir), exist_ok=True)

        # PR配置
        try:
            ui_cfg = self.settings.get('ui', {}) or {}
            enable_pr_val = ui_cfg.get('enable_pr', 'true')
            self.pr_enabled = str(enable_pr_val).strip().lower() in ('1', 'true', 'yes', 'on')
        except Exception:
            self.pr_enabled = True

        if '--no-pr' in sys.argv or os.environ.get('NO_PR', '').lower() in ('1', 'true'):
            self.pr_enabled = False

    def load_existing_updates(self) -> int:
        """加载默认更新文件中的论文"""
        count = 0
        if os.path.exists(self.update_json_path):
            try:
                loaded_papers = self.update_utils.load_papers_from_json(self.update_json_path, skip_invalid=False)
                self.papers.extend(loaded_papers)
                count = len(self.papers)
            except Exception as e:
                raise Exception(f"加载更新文件失败: {e}")
        return count

    def create_new_paper(self) -> Paper:
        """创建一个新的占位符论文并添加到列表"""
        placeholder_data = {
            'title': self.PLACEHOLDER,
            'authors': self.PLACEHOLDER,
            'category': '',
            'doi': '',
            'paper_url': '',
            'project_url': '',
            'conference': '',
            'contributor': '',
            'notes': '',
            'status': ''
        }
        try:
            placeholder = Paper.from_dict(placeholder_data)
        except Exception:
            placeholder = Paper.from_dict({'title': self.PLACEHOLDER})
            
        self.papers.append(placeholder)
        return placeholder

    def delete_paper(self, index: int) -> bool:
        """删除指定索引的论文"""
        if 0 <= index < len(self.papers):
            del self.papers[index]
            return True
        return False

    def clear_papers(self):
        """清空所有论文"""
        self.papers = []

    def validate_papers_for_save(self) -> List[Tuple[int, str, List[str]]]:
        """验证所有论文，返回无效论文列表 (index, title, errors)"""
        invalid_papers = []
        for i, paper in enumerate(self.papers):
             valid, errors, _ = paper.validate_paper_fields(
                self.config,
                check_required=True,
                check_non_empty=True,
                no_normalize=False
            )
             if not valid:
                 invalid_papers.append((i+1, paper.title[:50], errors[:2]))
        return invalid_papers

    def check_save_conflicts(self, target_path: str) -> Tuple[List[Paper], bool]:
        """检查保存时的冲突，返回(合并后的列表, 是否有冲突)"""
        existing_papers = []
        if os.path.exists(target_path):
            existing_papers = self.update_utils.load_papers_from_json(target_path, skip_invalid=False)
        
        merged_papers = list(existing_papers)
        existing_map = {}
        for p in existing_papers:
            key = p.get_key()
            existing_map[key] = p

        has_conflict = False
        
        # 预处理当前论文并检查冲突
        for paper in self.papers:
            paper.doi = clean_doi(paper.doi, self.conflict_marker) if paper.doi else ""
            paper.category = self.update_utils.normalize_category_value(paper.category, self.config)
            
            key = paper.get_key()
            if key in existing_map:
                has_conflict = True
                # 这里我们不合并，只标记冲突，具体合并逻辑在 perform_save 中根据用户选择处理
            else:
                pass # 这里只是预检查
                
        return merged_papers, has_conflict

    def perform_save(self, target_path: str, overwrite_duplicates: bool = False) -> List[Paper]:
        """执行保存操作"""
        existing_papers = []
        if os.path.exists(target_path):
            existing_papers = self.update_utils.load_papers_from_json(target_path, skip_invalid=False)
        
        merged_papers = list(existing_papers)
        existing_map = {}
        for idx, p in enumerate(existing_papers):
            key = p.get_key()
            existing_map[key] = idx

        for paper in self.papers:
            # 再次确保规范化
            paper.doi = clean_doi(paper.doi, self.conflict_marker) if paper.doi else ""
            paper.category = self.update_utils.normalize_category_value(paper.category, self.config)
            
            key = paper.get_key()
            if key in existing_map:
                if overwrite_duplicates:
                    idx = existing_map[key]
                    merged_papers[idx] = paper
            else:
                merged_papers.append(paper)

        self.update_utils.save_papers_to_json(target_path, merged_papers, skip_invalid=False)
        return merged_papers

    def load_from_template(self, filepath: str) -> int:
        """从模板文件加载论文，替换当前列表"""
        new_papers = []
        if filepath.endswith('.json'):
            data = self.update_utils.read_json_file(filepath)
            if data and 'papers' in data:
                for paper_data in data['papers']:
                    new_papers.append(Paper.from_dict(paper_data))
        elif filepath.endswith('.xlsx'):
            import pandas as pd
            df = pd.read_excel(filepath, engine='openpyxl')
            new_papers = self.update_utils.excel_to_paper(df, only_non_system=True)
        
        self.papers = new_papers
        return len(self.papers)

    # ================= Zotero 逻辑 =================

    def process_zotero_json(self, json_str: str) -> List[Paper]:
        """处理Zotero JSON字符串"""
        return self.zotero_processor.process_meta_data(json_str)

    def add_zotero_papers(self, papers: List[Paper]) -> int:
        """批量添加Zotero论文"""
        self.papers.extend(papers)
        return len(papers)

    def get_zotero_fill_updates(self, source_paper: Paper, target_index: int) -> Tuple[List[str], List[Tuple[str, Any]]]:
        """
        计算Zotero填充的更新内容
        返回: (冲突字段列表, 待更新字段列表[(field, val)])
        """
        if not (0 <= target_index < len(self.papers)):
            return [], []
            
        target_paper = self.papers[target_index]
        conflicts = []
        fields_to_update = []
        
        system_fields = [t["variable"] for t in self.config.get_system_tags()]
        
        for field in source_paper.__dataclass_fields__:
            if field in ['invalid_fields', 'is_placeholder'] or field in system_fields:
                continue
            
            val = getattr(source_paper, field)
            if val:
                target_val = getattr(target_paper, field)
                fields_to_update.append((field, val))
                # 冲突检测
                if target_val and str(target_val).strip() and str(target_val).strip() != self.PLACEHOLDER:
                    conflicts.append(field)
                    
        return conflicts, fields_to_update

    def apply_paper_updates(self, index: int, updates: List[Tuple[str, Any]], overwrite: bool):
        """应用更新到指定论文"""
        if not (0 <= index < len(self.papers)):
            return 0
            
        target_paper = self.papers[index]
        updated_count = 0
        
        for field, val in updates:
            target_val = getattr(target_paper, field)
            if overwrite or (not target_val or not str(target_val).strip()):
                setattr(target_paper, field, val)
                updated_count += 1
        return updated_count

    # ================= PR 提交逻辑 =================

    def has_update_files(self) -> bool:
        """检查是否存在更新文件"""
        return os.path.exists(self.update_json_path)

    def execute_pr_submission(self, status_callback, result_callback, error_callback):
        """执行PR提交的线程函数"""
        def run():
            try:
                # 检查 Git
                try:
                    subprocess.run(["git", "--version"], check=True, capture_output=True)
                except (subprocess.CalledProcessError, FileNotFoundError):
                    raise Exception("Git未安装！")
                
                # 获取当前分支
                result = subprocess.run(["git", "branch", "--show-current"], 
                                       capture_output=True, text=True, cwd=BASE_DIR)
                current_branch = result.stdout.strip()
                original_branch = current_branch
                created_new_branch = False
                
                # 分支处理
                if current_branch == "main":
                    branch_name = f"paper-submission-{int(time.time())}"
                    try:
                        subprocess.run(["git", "checkout", "-b", branch_name], 
                                      check=True, capture_output=True, text=True, cwd=BASE_DIR)
                        created_new_branch = True
                        status_callback(f"已创建并切换到新分支: {branch_name}")
                    except subprocess.CalledProcessError as e:
                        raise Exception(f"创建分支失败: {e.stderr}")
                else:
                    branch_name = current_branch
                
                # 添加文件
                have_files = False
                try:
                    if os.path.exists(self.update_json_path):
                        have_files = True
                        subprocess.run(["git", "add", self.update_json_path], 
                                     check=True, capture_output=True, cwd=BASE_DIR)
                    if os.path.exists(self.update_excel_path):
                        have_files = True
                        subprocess.run(["git", "add", self.update_excel_path], 
                                     check=True, capture_output=True, cwd=BASE_DIR)
                    
                    if not have_files:
                        raise Exception("没有找到可提交的更新文件！")
                        
                    # 提交
                    subprocess.run(["git", "commit", "-m", f"Add {len(self.papers)} papers via GUI"], 
                                   check=True, capture_output=True, cwd=BASE_DIR)
                    status_callback("已提交更改到本地仓库")
                except subprocess.CalledProcessError as e:
                    raise Exception(f"提交更改失败: {e.stderr}")
                
                # 推送
                try:
                    subprocess.run(["git", "push", "origin", branch_name], 
                                 check=True, capture_output=True, text=True, cwd=BASE_DIR)
                    status_callback(f"已推送到远程分支: {branch_name}")
                except subprocess.CalledProcessError as e:
                    raise Exception(f"推送失败: {e.stderr}")
                
                # 创建 PR
                pr_url = None
                try:
                    pr_title = f"论文提交: {len(self.papers)} 篇新论文"
                    pr_body = f"通过GUI提交了 {len(self.papers)} 篇论文。"
                    
                    try:
                        subprocess.run(["gh", "--version"], check=True, capture_output=True)
                        use_gh = True
                    except: use_gh = False

                    if use_gh:
                        res = subprocess.run(
                            ["gh", "pr", "create", "--base", "main", "--head", branch_name,
                             "--title", pr_title, "--body", pr_body],
                            capture_output=True, text=True, cwd=BASE_DIR
                        )
                        if res.returncode == 0:
                            pr_url = res.stdout.strip()
                        else:
                            # 即使GH失败，推送已完成，由用户手动创建
                            raise Exception(f"GitHub CLI创建PR失败: {res.stderr}")
                    else:
                        # 抛出特定异常以触发手动指引
                        raise Exception("GitHub CLI not installed")

                except Exception as e:
                    if "GitHub CLI" in str(e):
                        result_callback(None, branch_name, manual_guide=True)
                    else:
                        result_callback(None, branch_name, manual_guide=False)
                    # 此时不应抛出异常终止，因为推送已成功
                else:
                    result_callback(pr_url, branch_name, manual_guide=False)

                # 切回原分支
                if created_new_branch:
                    subprocess.run(["git", "checkout", original_branch], check=True, capture_output=True, text=True, cwd=BASE_DIR)

            except Exception as e:
                error_callback(str(e))
                
        threading.Thread(target=run, daemon=True).start()



    def import_file_asset(self, src_path: str, asset_type: str) -> str:
        """
        导入文件资源到项目目录
        asset_type: 'figure' or 'paper'
        返回: 相对路径字符串
        """
        if not src_path or not os.path.exists(src_path):
            return ""
        
        dest_dir = self.figure_dir if asset_type == 'figure' else self.paper_dir
        abs_dest_dir = os.path.join(BASE_DIR, dest_dir)
        
        filename = os.path.basename(src_path)
        # 简单避免重名覆盖
        if os.path.exists(os.path.join(abs_dest_dir, filename)):
            name, ext = os.path.splitext(filename)
            filename = f"{name}_{int(time.time())}{ext}"
            
        dest_path = os.path.join(abs_dest_dir, filename)
        try:
            shutil.copy2(src_path, dest_path)
            # 返回相对路径（使用正斜杠）
            rel_path = os.path.join(dest_dir, filename).replace('\\', '/')
            return rel_path
        except Exception as e:
            print(f"Copy file failed: {e}")
            return ""

    def save_ai_config(self, profiles: List[Dict], active_profile: str, enable_ai: bool):
        """保存AI配置到 config.ini"""
        config = configparser.ConfigParser()
        user_path = os.path.join(self.config.config_path, 'config.ini')
        if os.path.exists(user_path):
            config.read(user_path, encoding='utf-8')
        
        if 'ai' not in config:
            config['ai'] = {}
            
        config['ai']['enable_ai_generation'] = str(enable_ai).lower()
        config['ai']['active_profile'] = active_profile
        config['ai']['profiles_json'] = json.dumps(profiles) # 使用JSON存储列表
        
        with open(user_path, 'w', encoding='utf-8') as f:
            config.write(f)
        
        # 重新加载
        self.config = get_config_instance() # Reload

    def perform_save(self, target_path: str, conflict_mode: str = 'ask') -> List[Paper]:
        """
        执行保存
        conflict_mode: 'ask', 'overwrite_all', 'skip_all'
        """
        existing_papers = []
        if os.path.exists(target_path):
            existing_papers = self.update_utils.load_papers_from_json(target_path, skip_invalid=False)
        
        merged_papers = list(existing_papers)
        existing_map = {p.get_key(): idx for idx, p in enumerate(existing_papers)}

        for paper in self.papers:
            # 规范化
            paper.doi = clean_doi(paper.doi, self.conflict_marker) if paper.doi else ""
            paper.category = self.update_utils.normalize_category_value(paper.category, self.config)
            
            key = paper.get_key()
            if key in existing_map:
                if conflict_mode == 'overwrite_all':
                    idx = existing_map[key]
                    merged_papers[idx] = paper
                elif conflict_mode == 'skip_all':
                    continue
                # 'ask' 模式应在 GUI 层处理，Logic 层假设调用时已确定策略
            else:
                merged_papers.append(paper)

        self.update_utils.save_papers_to_json(target_path, merged_papers, skip_invalid=False)
        return merged_papers