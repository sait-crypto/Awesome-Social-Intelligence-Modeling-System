import json
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import re
import threading
import time
import os
import webbrowser
from collections import OrderedDict
import pickle
import statistics

from utils.file_utils import ConfigManager, SessionManager
from core.llm_service import LLMService
from core.translation import TranslationService

class PaperReviewBrowser:
    def __init__(self, root):
        self.root = root
        self.root.title("论文审稿数据浏览器 - DeepSeek集成版")
        self.root.geometry("1400x900")
        
        # 基础路径配置
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.default_save_dir = os.path.join(self.base_dir, "saves")
        self.default_source_dir = os.path.join(self.base_dir, "sources")
        self.ensure_directories()

        # 文件路径
        self.config_file_path = "config.ini"
        self.session_file_path = "session.pkl"
        self.cache_file_path = "cache.pkl"
        
        # 绑定事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.bind('<KeyPress>', self.on_key_press)
        
        # 加载配置与服务
        self.config = ConfigManager.load_config(self.config_file_path)
        self.llm_service = LLMService()
        self.translation_service = TranslationService(self.config, self.llm_service)
        
        # 数据变量
        self.json_file_path = ""
        self.sorted_data = []      # 数据库中所有论文 (Base Universe)
        self.filtered_data = []    # 当前展示列表 (Final View)
        self.all_tracks = []
        self.track_vars = {}
        self.track_popup = None
        self.current_paper = None
        
        # 搜索状态
        self.llm_search_active = False          # 是否正在进行网络请求
        self.llm_search_results_active = False  # 是否处于展示AI结果的状态
        self.ai_search_results = []             # 存储AI搜索选出的论文子集 (AI Universe)
        
        self.rating_scale_dragging = False
        self.llm_progress = None
        self.llm_progress_window = None
        
        # 加载会话
        self.session_data = SessionManager.load_session(self.session_file_path)
        
        # 初始化界面变量 (默认值)
        self.llm_translate_title_var = tk.BooleanVar(value=False)
        self.search_var = tk.StringVar()
        self.keywords_area_var = tk.StringVar()
        self.rating_var = tk.DoubleVar(value=0.0)
        self.show_adopted_only_var = tk.BooleanVar(value=False)
        self.show_excluded_var = tk.BooleanVar(value=True)
        self.show_notes_only_var = tk.BooleanVar(value=False)
        self.llm_search_var = tk.StringVar()
        self.include_tldr_abstract_var = tk.BooleanVar(value=False)
        self.relevance_threshold_var = tk.DoubleVar(value=0.5) 
        
        # 加载缓存
        self.load_cache()
        
        # 创建界面
        self.create_widgets()
        
        # 初始化逻辑
        self.root.after(200, self.initialize_database)
        
        if hasattr(self, 'result_label'):
            self.result_label.config(text="请选择数据库文件开始使用")

    def ensure_directories(self):
        """确保默认目录存在"""
        for path in [self.default_save_dir, self.default_source_dir]:
            if not os.path.exists(path):
                os.makedirs(path)

    def initialize_database(self):
        """初始化数据库选择"""
        last_session_path = self.config.get('last_session_path', '')
        if last_session_path and os.path.exists(last_session_path):
            try:
                with open(last_session_path, 'rb') as f:
                    session_data = pickle.load(f)
                db_path = session_data.get('database_path', '')
                if db_path and os.path.exists(db_path):
                    self.load_database(db_path, last_session_path)
                    self.restore_ui_state_if_confirmed()
                    return
                else:
                    self.session_file_path = last_session_path
                    messagebox.showwarning("警告", f"存档文件中记录的数据库文件不存在: {db_path}")
            except Exception as e:
                print(f"加载上次存档失败: {e}")
        
        if hasattr(self, 'status_label'):
            self.status_label.config(text="数据库: 未选择 | 存档: 未选择")

    def restore_ui_state_if_confirmed(self):
        """询问用户是否恢复上次的界面状态"""
        saved_ui = self.session_data.get('ui_state', {})
        if not saved_ui:
            return

        if messagebox.askyesno("恢复工作区", "检测到上次保存的界面配置（AI搜索状态、筛选条件等），是否恢复？"):
            try:
                # 1. 恢复基础筛选控件值
                self.search_var.set(saved_ui.get('search_text', ''))
                self.keywords_area_var.set(saved_ui.get('keywords_area_text', ''))
                self.rating_var.set(saved_ui.get('min_rating', 0.0))
                self.rating_label.config(text=f"{self.rating_var.get():.1f}")
                
                self.show_adopted_only_var.set(saved_ui.get('show_adopted_only', False))
                self.show_excluded_var.set(saved_ui.get('show_excluded', False))
                self.show_notes_only_var.set(saved_ui.get('show_notes_only', False))
                
                self.llm_search_var.set(saved_ui.get('llm_search_text', ''))
                if not self.llm_search_var.get():
                     self.llm_search_entry.insert(0, "例如: 找出所有有关语言-视觉模型的论文")
                     self.llm_search_entry.config(foreground="gray")
                else:
                     self.llm_search_entry.config(foreground="black")

                self.include_tldr_abstract_var.set(saved_ui.get('include_tldr_abstract', False))
                self.relevance_threshold_var.set(saved_ui.get('relevance_threshold', 0.6))
                self.relevance_threshold_label.config(text=f"{self.relevance_threshold_var.get():.2f}")
                self.llm_translate_title_var.set(saved_ui.get('llm_translate_title', False))
                
                # 2. 恢复Track筛选
                saved_tracks = saved_ui.get('selected_tracks_list', None)
                if saved_tracks is not None and self.track_vars:
                    self.select_all_var.set(False)
                    for t, v in self.track_vars.items():
                        v.set(t in saved_tracks)
                    if all(self.track_vars[t].get() for t in self.track_vars):
                        self.select_all_var.set(True)

                # 恢复类别筛选
                saved_statuses = saved_ui.get('selected_statuses_list', None)
                if saved_statuses is not None and hasattr(self, 'status_vars') and self.status_vars:
                    self.select_all_status_var.set(False)
                    for s, v in self.status_vars.items():
                        v.set(s in saved_statuses)
                    if all(self.status_vars[s].get() for s in self.status_vars):
                        self.select_all_status_var.set(True)

                # 3. 恢复AI搜索状态 (关键步骤)
                self.llm_search_results_active = saved_ui.get('llm_search_results_active', False)
                ai_ids = saved_ui.get('ai_search_results_ids', [])
                
                if self.llm_search_results_active and ai_ids:
                    # 将ID重新映射回当前加载的 paper 对象
                    id_map = {str(p.get('id')): p for p in self.sorted_data}
                    self.ai_search_results = []
                    for pid in ai_ids:
                        if str(pid) in id_map:
                            self.ai_search_results.append(id_map[str(pid)])
                    
                    if self.ai_search_results:
                        self.undo_llm_search_button.config(state=tk.NORMAL)
                        if hasattr(self, 'result_label'):
                            self.result_label.config(text=f"已恢复AI搜索状态，基准论文数: {len(self.ai_search_results)}")
                    else:
                        # 如果ID没对上，重置状态
                        self.llm_search_results_active = False
                        self.ai_search_results = []
                        self.undo_llm_search_button.config(state=tk.DISABLED)

                # 4. 触发搜索以应用所有状态
                self.on_search() 
            except Exception as e:
                print(f"恢复界面状态失败: {e}")

    def save_session_immediate(self):
        """保存会话状态（包括UI状态和AI搜索结果）"""
        if self.session_file_path and os.path.exists(os.path.dirname(self.session_file_path)):
            try:
                self.session_data['database_path'] = self.json_file_path
                
                # --- 保存当前UI状态 ---
                ui_state = {
                    'search_text': self.search_var.get(),
                    'keywords_area_text': self.keywords_area_var.get(),
                    'min_rating': self.rating_var.get(),
                    'show_adopted_only': self.show_adopted_only_var.get(),
                    'show_excluded': self.show_excluded_var.get(),
                    'show_notes_only': self.show_notes_only_var.get(),
                    'llm_search_text': self.llm_search_var.get(),
                    'include_tldr_abstract': self.include_tldr_abstract_var.get(),
                    'relevance_threshold': self.relevance_threshold_var.get(),
                    'llm_translate_title': self.llm_translate_title_var.get(),
                    # 保存AI搜索状态
                    'llm_search_results_active': self.llm_search_results_active,
                    # 只保存ID以减小体积且保持数据引用一致性
                    'ai_search_results_ids': [p.get('id') for p in self.ai_search_results] if self.llm_search_results_active else []
                }
                # 保存Track状态
                if self.track_vars:
                    ui_state['selected_tracks_list'] = [t for t, v in self.track_vars.items() if v.get()]
                # 保存类别筛选状态
                if hasattr(self, 'status_vars') and self.status_vars:
                    ui_state['selected_statuses_list'] = [s for s, v in self.status_vars.items() if v.get()]
                
                self.session_data['ui_state'] = ui_state
                # -------------------

                SessionManager.save_session(self.session_data, self.session_file_path)
                if hasattr(self, 'status_label'):
                    db_name = os.path.basename(self.json_file_path) if self.json_file_path else "未选择"
                    session_name = os.path.basename(self.session_file_path)
                    self.status_label.config(text=f"数据库: {db_name} | 存档: {session_name} (已保存)")
            except Exception as e:
                print(f"自动保存失败: {e}")

    # ... (create_new_archive, load_archive, load_database, load_cache, save_cache, on_closing 保持不变) ...
    # 为了节省篇幅，此处省略未修改的加载/保存文件代码，请保持原样 ...

    def create_new_archive(self):
        """创建新存档"""
        db_path = filedialog.askopenfilename(
            title="选择论文数据库文件",
            initialdir=self.default_source_dir,
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if not db_path: return
        
        base_name = os.path.splitext(os.path.basename(db_path))[0]
        session_path = filedialog.asksaveasfilename(
            title="保存存档文件",
            initialdir=self.default_save_dir,
            defaultextension=".sav",
            filetypes=[("Save files", "*.sav"), ("All files", "*.*")],
            initialfile=f"{base_name}.sav"
        )
        
        if session_path:
            new_session = SessionManager.get_default_session()
            new_session['database_path'] = db_path
            try:
                SessionManager.save_session(new_session, session_path)
                self.session_data = new_session
                self.load_database(db_path, session_path)
            except Exception as e:
                messagebox.showerror("错误", f"创建存档文件失败: {e}")

    def load_archive(self):
        """读取存档文件"""
        session_path = filedialog.askopenfilename(
            title="选择存档文件",
            initialdir=self.default_save_dir,
            filetypes=[("Save files", "*.sav"), ("All files", "*.*")]
        )
        if not session_path: return

        try:
            with open(session_path, 'rb') as f:
                session_data = pickle.load(f)
            db_path = session_data.get('database_path', '')
            
            if db_path and os.path.exists(db_path):
                self.load_database(db_path, session_path)
                self.restore_ui_state_if_confirmed()
            else:
                messagebox.showerror("错误", f"数据库文件不存在: {db_path}\n请重新选择")
                db_path = filedialog.askopenfilename(
                    title="选择数据库文件",
                    initialdir=self.default_source_dir,
                    filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
                )
                if db_path:
                    session_data['database_path'] = db_path
                    with open(session_path, 'wb') as f:
                        pickle.dump(session_data, f)
                    self.load_database(db_path, session_path)
                    self.restore_ui_state_if_confirmed()
        except Exception as e:
            messagebox.showerror("错误", f"读取存档文件失败: {e}")

    def load_database(self, json_file_path, session_file_path):
        """加载数据库及预处理"""
        self.json_file_path = json_file_path
        self.session_file_path = session_file_path
        
        self.config['last_session_path'] = session_file_path
        ConfigManager.save_config(self.config, self.config_file_path)
        
        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                raw_data = json.load(f)
        except Exception as e:
            messagebox.showerror("错误", f"加载数据失败: {e}")
            raw_data = []
        
        valid_papers = []
        tracks_set = set()
        statuses_set = set()
        
        for paper in raw_data:
            # 不再在加载时排除任何 status（包括 Withdraw/Reject），全部纳入展示与筛选
            pass
            
            tracks_set.add(paper.get('track', '') or '')
            statuses_set.add(paper.get('status', '') or '')
            
            # 统一评分逻辑
            rating_val = 0.0
            rating_avg = paper.get('rating_avg')
            found_numeric = False

            if rating_avg is not None:
                if isinstance(rating_avg, list) and rating_avg:
                    rating_val = float(rating_avg[0])
                    found_numeric = True
                elif isinstance(rating_avg, (int, float)):
                    rating_val = float(rating_avg)
                    found_numeric = True

            if not found_numeric:
                for field in ['rating', 'recommendation']:
                    val_str = str(paper.get(field, ''))
                    if val_str and any(c.isdigit() for c in val_str):
                        try:
                            scores = [float(s) for s in re.split(r'[;,\s]+', val_str) if s.strip().replace('.','',1).isdigit()]
                            if scores:
                                rating_val = statistics.mean(scores)
                                found_numeric = True
                                break
                        except:
                            pass

            # 如果没有任何数字评分且类别为 Desk Reject/Reject/Withdraw，则视作 0 分并标记为有数值（以便被最低评分筛选）
            status_val = (paper.get('status') or '').strip().lower()
            if not found_numeric and status_val in ('desk reject', 'reject', 'withdraw'):
                rating_val = 0.0
                has_numeric = True
            else:
                has_numeric = found_numeric

            # 当没有数值评分且不是拒绝类时，保持 _calculated_rating 为 None，并标记为无数值（免疫最低评分筛选）
            paper['_has_numeric_rating'] = bool(has_numeric)
            paper['_calculated_rating'] = float(rating_val) if has_numeric else None

            # 排序键: 若有数值评分且>0按评分降序，否则按(0, id)
            sort_key = (-rating_val, paper.get('id', '')) if has_numeric and rating_val > 0 else (0, paper.get('id', ''))
            paper['_sort_key'] = sort_key
            valid_papers.append(paper)
        
        self.sorted_data = sorted(valid_papers, key=lambda x: x['_sort_key'])
        self.all_tracks = sorted(list(tracks_set))
        self.all_statuses = sorted(list(statuses_set))
        
        self.session_data = SessionManager.load_session(self.session_file_path)
        self.session_data['database_path'] = json_file_path
        
        self.initialize_track_selection()
        
        self.filtered_data = self.sorted_data.copy()
        self.display_papers()
        
        if hasattr(self, 'status_label'):
            self.status_label.config(text=f"数据库: {os.path.basename(self.json_file_path)} | 存档: {os.path.basename(self.session_file_path)}")
        if hasattr(self, 'result_label'):
            self.result_label.config(text=f"已加载 {len(self.sorted_data)} 篇论文")
        if hasattr(self, 'total_papers_label'):
            self.total_papers_label.config(text=f"论文总数: {len(self.sorted_data)}")

    def load_cache(self):
        """统一加载缓存"""
        self.translation_cache = OrderedDict()
        self.summary_cache = OrderedDict()
        self.abstract_translation_cache = OrderedDict()
        self.title_translation_cache = OrderedDict()
        self.relevance_cache = OrderedDict()
        self.global_cache_order = OrderedDict()
        
        try:
            if os.path.exists(self.cache_file_path):
                with open(self.cache_file_path, 'rb') as f:
                    cache_data = pickle.load(f)
                    self.translation_cache = cache_data.get('translation_cache', OrderedDict())
                    self.summary_cache = cache_data.get('summary_cache', OrderedDict())
                    self.abstract_translation_cache = cache_data.get('abstract_translation_cache', OrderedDict())
                    self.title_translation_cache = cache_data.get('title_translation_cache', OrderedDict())
                    self.relevance_cache = cache_data.get('relevance_cache', OrderedDict())
                    self.llm_service.token_usage = cache_data.get('deepseek_token_usage', 0)
                    
                    order_list = cache_data.get('cache_order', None)
                    if order_list is not None:
                        for cache_name, key in order_list:
                            dict_ref = getattr(self, f"{cache_name}_cache", None)
                            if dict_ref is not None and key in dict_ref:
                                self.global_cache_order[(cache_name, key)] = dict_ref
                    else:
                        for cache_name, dict_ref in (
                                ('translation', self.translation_cache),
                                ('summary', self.summary_cache),
                                ('abstract_translation', self.abstract_translation_cache),
                                ('title_translation', self.title_translation_cache),
                                ('relevance', self.relevance_cache)):
                            for k in dict_ref.keys():
                                self.global_cache_order[(cache_name, k)] = dict_ref
                    
                    while len(self.global_cache_order) > self.config.get('max_cache_size', 0):
                        (old_name, old_key), old_dict = self.global_cache_order.popitem(last=False)
                        old_dict.pop(old_key, None)
                print("缓存已加载")
        except Exception as e:
            print(f"加载缓存异常: {e}，使用新缓存")

    def save_cache(self):
        """保存缓存"""
        cache_data = {
            'translation_cache': self.translation_cache,
            'summary_cache': self.summary_cache,
            'abstract_translation_cache': self.abstract_translation_cache,
            'title_translation_cache': self.title_translation_cache,
            'relevance_cache': self.relevance_cache,
            'deepseek_token_usage': self.llm_service.token_usage,
            'cache_order': list(self.global_cache_order.keys())
        }
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                with open(self.cache_file_path, 'wb') as f:
                    pickle.dump(cache_data, f)
                return
            except PermissionError:
                time.sleep(0.5)
            except Exception as e:
                print(f"保存缓存失败: {e}")
                break

    def on_closing(self):
        try:
            ConfigManager.save_config(self.config, self.config_file_path)
            self.save_session_immediate() 
            self.save_cache()
        except Exception as e:
            messagebox.showerror("错误", f"退出保存失败: {e}")
        self.root.destroy()

    # --- 功能函数 (部分省略，保持不变) ---
    def restore_tree_focus(self):
        try:
            if hasattr(self, 'paper_tree') and self.paper_tree.winfo_exists():
                self.paper_tree.focus_set()
                sels = self.paper_tree.selection()
                if sels: self.paper_tree.focus(sels[0])
        except Exception: pass

    def is_paper_adopted(self, pid): return pid in self.session_data['adopted_papers']
    def is_paper_excluded(self, pid): return pid in self.session_data['excluded_papers']
    
    def toggle_paper_adopted(self, pid):
        s = self.session_data['adopted_papers']
        s.remove(pid) if pid in s else s.add(pid)
        self.save_session_immediate()

    def toggle_paper_excluded(self, pid):
        s = self.session_data['excluded_papers']
        s.remove(pid) if pid in s else s.add(pid)
        self.save_session_immediate()

    def create_widgets(self):
        # 菜单
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        f_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="文件", menu=f_menu)
        f_menu.add_command(label="新建存档", command=self.create_new_archive)
        f_menu.add_command(label="打开存档", command=self.load_archive)
        f_menu.add_separator()
        f_menu.add_command(label="退出", command=self.on_closing)

        h_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="帮助", menu=h_menu)
        h_menu.add_command(label="快捷键", command=self.show_shortcuts)
        
        # 主布局
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 顶部控制栏
        top_frame = ttk.Frame(main_frame)
        top_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 存档区域
        arc_frame = ttk.Frame(top_frame)
        arc_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(arc_frame, text="打开存档", command=self.load_archive).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(arc_frame, text="新建存档", command=self.create_new_archive).pack(side=tk.LEFT, padx=(0, 10))
        self.status_label = ttk.Label(arc_frame, text="数据库: 未选择 | 存档: 未选择", relief=tk.SUNKEN)
        self.status_label.pack(side=tk.LEFT, padx=(0, 10))
        
        # 配置区域
        cfg_frame = ttk.Frame(top_frame)
        cfg_frame.pack(side=tk.RIGHT)
        ttk.Button(cfg_frame, text="配置", command=self.show_config_dialog).pack(side=tk.LEFT, padx=(0, 10))
        
        cache_count = sum(len(c) for c in [self.translation_cache, self.summary_cache, self.abstract_translation_cache, self.title_translation_cache, self.relevance_cache])
        self.cache_status_label = ttk.Label(cfg_frame, text=f"缓存: {cache_count}/{self.config['max_cache_size']}")
        self.cache_status_label.pack(side=tk.LEFT, padx=(0, 10))
        self.token_label = ttk.Label(cfg_frame, text=f"Token使用: {self.llm_service.token_usage}")
        self.token_label.pack(side=tk.LEFT)
        
        # 搜索栏
        ctrl_frame = ttk.Frame(main_frame)
        ctrl_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 第一行搜索
        r1 = ttk.Frame(ctrl_frame)
        r1.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(r1, text="搜索:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.search_entry = ttk.Entry(r1, textvariable=self.search_var, width=30)
        self.search_entry.grid(row=0, column=1, padx=(0, 10))
        self.search_entry.bind('<Return>', self.on_search)
        
        ttk.Label(r1, text="Track/领域/关键词:").grid(row=0, column=2, sticky=tk.W, padx=(0, 5))
        self.keywords_area_entry = ttk.Entry(r1, textvariable=self.keywords_area_var, width=20)
        self.keywords_area_entry.grid(row=0, column=3, padx=(0, 10))
        self.keywords_area_entry.bind('<Return>', self.on_search)

        self.search_button = ttk.Button(r1, text="搜索", command=self.on_search)
        self.search_button.grid(row=0, column=4, padx=(0, 10))

        self.clear_search_button = ttk.Button(r1, text="清除搜索", command=self.clear_search)
        self.clear_search_button.grid(row=0, column=5, padx=(0, 10))
        
        self.track_button = ttk.Button(r1, text="Track筛选 ▼", command=self.show_track_filter_popup)
        self.track_button.grid(row=0, column=6, padx=(0, 10))
        
        self.status_button = ttk.Button(r1, text="类别筛选 ▼", command=self.show_status_filter_popup)
        self.status_button.grid(row=0, column=7, padx=(0, 10))
        
        ttk.Checkbutton(r1, text="只显示已采用", variable=self.show_adopted_only_var, command=self.on_search).grid(row=0, column=8, padx=(0, 10))
        
        ttk.Checkbutton(r1, text="显示已排除", variable=self.show_excluded_var, command=self.on_search).grid(row=0, column=9, padx=(0, 10))
        
        ttk.Checkbutton(r1, text="只显示有笔记", variable=self.show_notes_only_var, command=self.on_search).grid(row=0, column=10, padx=(0, 10))
        
        ttk.Label(r1, text="最低评分:").grid(row=0, column=11, sticky=tk.W, padx=(0, 5))
        self.rating_scale = ttk.Scale(r1, from_=0, to=10, variable=self.rating_var, command=self.on_rating_scale_drag)
        self.rating_scale.grid(row=0, column=12, sticky=tk.EW, padx=(0, 10))
        self.rating_scale.bind('<ButtonRelease-1>', self.on_rating_scale_release)
        self.rating_label = ttk.Label(r1, text=f"{self.rating_var.get():.1f}")
        self.rating_label.grid(row=0, column=13, padx=(0, 10))
        r1.columnconfigure(12, weight=1)

        # 第二行搜索 (LLM)
        r2 = ttk.Frame(ctrl_frame)
        r2.pack(fill=tk.X, pady=(5, 0))
        
        ttk.Label(r2, text="AI搜索:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.llm_search_entry = ttk.Entry(r2, textvariable=self.llm_search_var, width=80)
        self.llm_search_entry.grid(row=0, column=1, padx=(0, 10))
        self.llm_search_entry.bind('<Return>', self.on_llm_search)
        if not self.llm_search_var.get():
            self.llm_search_entry.insert(0, "例如: 找出所有有关语言-视觉模型的论文")
            self.llm_search_entry.config(foreground="gray")
        self.llm_search_entry.bind('<FocusIn>', self.on_llm_search_focusin)
        self.llm_search_entry.bind('<FocusOut>', self.on_llm_search_focusout)
        
        self.llm_search_button = ttk.Button(r2, text="AI搜索", command=self.on_llm_search)
        self.llm_search_button.grid(row=0, column=2, padx=(0, 10))
        self.undo_llm_search_button = ttk.Button(r2, text="退回AI搜索", command=self.undo_llm_search, state=tk.DISABLED)
        self.undo_llm_search_button.grid(row=0, column=3, padx=(0, 10))
        
        ttk.Checkbutton(r2, text="提示词中加入TLDR和摘要", variable=self.include_tldr_abstract_var).grid(row=0, column=4, padx=(0, 10))
        
        ttk.Label(r2, text="相关性阈值:").grid(row=0, column=5, sticky=tk.W, padx=(0, 5))
        self.relevance_scale = ttk.Scale(r2, from_=0, to=1, variable=self.relevance_threshold_var, command=self.on_relevance_threshold_change)
        self.relevance_scale.grid(row=0, column=6, sticky=tk.EW, padx=(0, 10))
        self.relevance_threshold_label = ttk.Label(r2, text=f"{self.relevance_threshold_var.get():.2f}")
        self.relevance_threshold_label.grid(row=0, column=7, padx=(0, 10))
        r2.columnconfigure(6, weight=1)
        
        # 内容区域
        self.content_pane = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        self.content_pane.pack(fill=tk.BOTH, expand=True)
        
        # 列表
        list_frame = ttk.Frame(self.content_pane)
        self.content_pane.add(list_frame, weight=1)
        
        lt_frame = ttk.Frame(list_frame)
        lt_frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(lt_frame, text="论文列表", font=('Arial', 12, 'bold')).pack(side=tk.LEFT)
        self.total_papers_label = ttk.Label(lt_frame, text="当前论文计数: 0")
        self.total_papers_label.pack(side=tk.LEFT, padx=(10, 0))
        
        lc_frame = ttk.Frame(list_frame)
        lc_frame.pack(fill=tk.BOTH, expand=True)
        
        self.paper_tree = ttk.Treeview(lc_frame, columns=('status', 'rating', 'paper_status', 'track', 'title'), show='headings', height=25)
        self.paper_tree.heading('status', text='状态')
        self.paper_tree.heading('rating', text='评分')
        self.paper_tree.heading('paper_status', text='类别')
        self.paper_tree.heading('track', text='Track')
        self.paper_tree.heading('title', text='标题')
        
        self.paper_tree.column('status', width=38, stretch=False)
        self.paper_tree.column('rating', width=40, stretch=False)
        self.paper_tree.column('paper_status', width=50, stretch=False)
        self.paper_tree.column('track', width=100, stretch=False)
        self.paper_tree.column('title', width=400, stretch=True)
        
        sb = ttk.Scrollbar(lc_frame, orient=tk.VERTICAL, command=self.paper_tree.yview)
        self.paper_tree.configure(yscrollcommand=sb.set)
        self.paper_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.paper_tree.bind('<<TreeviewSelect>>', self.on_paper_select)
        
        # 详情
        detail_frame = ttk.Frame(self.content_pane)
        self.content_pane.add(detail_frame, weight=2)
        
        ttk.Label(detail_frame, text="论文详情", font=('Arial', 12, 'bold')).pack(anchor=tk.W, pady=(0, 5))
        
        note_frame = ttk.Frame(detail_frame)
        note_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(note_frame, text="用户笔记:", font=('Arial', 10, 'bold')).pack(anchor=tk.W)
        self.note_text = scrolledtext.ScrolledText(note_frame, wrap=tk.WORD, font=('Arial', 10), height=4)
        self.note_text.pack(fill=tk.X, expand=False)
        self.note_text.bind('<KeyRelease>', self.on_note_change)
        
        self.detail_text = scrolledtext.ScrolledText(detail_frame, wrap=tk.WORD, font=('Arial', 10), width=80, height=25)
        self.detail_text.pack(fill=tk.BOTH, expand=True)
        self.detail_text.config(state=tk.DISABLED)
        
        # 详情底部按钮
        btn_frame = ttk.Frame(detail_frame)
        btn_frame.pack(fill=tk.X, pady=(5, 0))
        
        l_btn_frame = ttk.Frame(btn_frame)
        l_btn_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.adopted_var = tk.BooleanVar()
        ttk.Checkbutton(l_btn_frame, text="采用", variable=self.adopted_var, command=self.on_adopted_toggle).pack(side=tk.LEFT, padx=(0, 10))
        
        self.excluded_var = tk.BooleanVar()
        ttk.Checkbutton(l_btn_frame, text="排除", variable=self.excluded_var, command=self.on_excluded_toggle).pack(side=tk.LEFT, padx=(0, 10))
        
        self.generate_tldr_button = ttk.Button(l_btn_frame, text="AI生成TLDR", command=self.on_generate_tldr, state=tk.DISABLED)
        self.generate_tldr_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.translate_abstract_button = ttk.Button(l_btn_frame, text="AI翻译摘要", command=self.on_translate_abstract, state=tk.DISABLED)
        self.translate_abstract_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.complete_translation_button = ttk.Button(l_btn_frame, text="完成普通翻译", command=self.on_complete_translation, state=tk.DISABLED)
        self.complete_translation_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.regenerate_translation_button = ttk.Button(l_btn_frame, text="重新生成普通翻译", command=self.on_regenerate_translation, state=tk.DISABLED)
        self.regenerate_translation_button.pack(side=tk.LEFT, padx=(0, 10))

        ttk.Checkbutton(l_btn_frame, text="AI翻译标题", variable=self.llm_translate_title_var, command=self.on_llm_translate_title_change).pack(side=tk.LEFT, padx=(0, 10))
        
        self.check_llm_search_button = ttk.Button(l_btn_frame, text="AI搜索符合性检测", command=self.on_check_llm_search)
        self.check_llm_search_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.llm_search_result_label = ttk.Label(l_btn_frame, text="")
        self.llm_search_result_label.pack(side=tk.LEFT, padx=(0, 10))
        
        # 样式配置 (部分省略)
        for tag, kwargs in {
            'bold': {'font': ('Arial', 10, 'bold')},
            'translation': {'foreground': 'blue'},
            'translating': {'foreground': 'orange'},
            'error': {'foreground': 'red'},
            'highlight': {'background': 'yellow'},
            'rating_high': {'foreground': 'green'},
            'rating_medium': {'foreground': 'orange'},
            'rating_low': {'foreground': 'red'},
            'link': {'foreground': 'blue', 'underline': True},
            'summary': {'foreground': 'purple'},
            'llm_translation': {'foreground': 'darkgreen'},
            'partial_translation': {'foreground': 'gray'},
            'title_translation': {'foreground': 'darkblue'},
            'author_male': {'foreground': 'blue'},
            'author_female': {'foreground': 'red'},
            'author_unknown': {'foreground': 'gray'}
        }.items():
            self.detail_text.tag_configure(tag, **kwargs)
            
        self.detail_text.tag_bind('link', '<Button-1>', self.on_link_click)
        
        # 底部栏
        stat_frame = ttk.Frame(main_frame)
        stat_frame.pack(fill=tk.X, pady=(10, 0))
        self.result_label = ttk.Label(stat_frame, text="", relief=tk.SUNKEN, anchor=tk.W)
        self.result_label.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=2)
        
        self.restore_ui_layout()

    # ... (快捷键、详情页操作等，保持不变) ...
    def on_paper_up(self):
        if not self.filtered_data or not self.paper_tree.selection(): return
        item = self.paper_tree.selection()[0]
        prev_item = self.paper_tree.prev(item)
        if prev_item:
            self.paper_tree.selection_set(prev_item)
            self.paper_tree.focus(prev_item)
            self.paper_tree.see(prev_item)
            self.on_paper_select(None)

    def on_paper_down(self):
        if not self.filtered_data or not self.paper_tree.selection(): return
        item = self.paper_tree.selection()[0]
        next_item = self.paper_tree.next(item)
        if next_item:
            self.paper_tree.selection_set(next_item)
            self.paper_tree.focus(next_item)
            self.paper_tree.see(next_item)
            self.on_paper_select(None)

    def on_open_paper_link(self, event=None):
        if not self.current_paper:
            messagebox.showinfo("提示", "请先选中一篇论文")
            return
        link = self.current_paper.get('site', '')
        if link: webbrowser.open_new_tab(link)
        else: messagebox.showinfo("提示", "该论文没有可用链接")

    def show_shortcuts(self):
        msg = ("A: 切换采用\nE: 切换排除\nC: 复制论文标题到剪贴板\nD: AI搜索符合性检测\nG: 打开链接\nS/Space/⬇: 下一论文\nW/Shift+Space/⬆: 上一论文\nT: AI翻译摘要\nY: 完成普通翻译")
        messagebox.showinfo("快捷键", msg)

    def on_key_press(self, event):
        focus = self.root.focus_get()
        if focus and focus.winfo_class() in ('Entry', 'TEntry', 'Text', 'ScrolledText'): return
        
        key = (event.keysym or '').lower()
        is_shift_pressed = (event.state & 0x0001) != 0

        if key == 'a': self.on_adopted_toggle()
        elif key == 'e': self.on_excluded_toggle()
        elif key == 'd': self.on_check_llm_search()
        elif key == 'g': self.on_open_paper_link()
        elif key == 'w' or (key == 'space' and  is_shift_pressed): self.on_paper_up()
        elif key == 's' or (key == 'space' and not is_shift_pressed): self.on_paper_down()
        elif key == 't': self.on_translate_abstract()
        elif key == 'y': self.on_complete_translation()
        elif key == 'c': self.on_copy_title()

    def confirm_regenerate(self, operation_name, paper_title):
        return messagebox.askyesno(
            "确认重新生成",
            f"论文 '{paper_title[:50]}...'\n已经进行过{operation_name}操作。\n确定要消耗Token重新生成吗？"
        )

    def on_copy_title(self):
        if not self.current_paper:
            messagebox.showinfo("提示", "请先选中一篇论文")
            return
        title = self.current_paper.get('title', '')
        if title:
            try:
                self.root.clipboard_clear()
                self.root.clipboard_append(title)
                if hasattr(self, 'result_label'):
                    self.result_label.config(text=f"论文标题已复制到剪贴板: {title}")
                else:
                    messagebox.showinfo("复制成功", "论文标题已复制到剪贴板")
            except Exception as e:
                messagebox.showerror("复制失败", f"无法复制到剪贴板: {e}")
        else:
            messagebox.showwarning("提示", "当前论文没有标题可复制")

    def on_generate_tldr(self):
        if self.current_paper:
            title = self.current_paper.get('title', '')
            cache_key = f"summary:{title}"
            
            if cache_key in self.summary_cache:
                if not self.confirm_regenerate("TLDR总结", title):
                    return
            
            self.generate_tldr_button.config(state=tk.DISABLED, text="生成中...")
            self.start_summary_thread(self.current_paper, self.update_summary_in_ui)
        try:
            self.restore_tree_focus()
        except Exception: pass

    def on_translate_abstract(self):
        if self.current_paper:
            title = self.current_paper.get('title', '')
            cache_key = f"abstract_translation:{title}"
            
            if cache_key in self.abstract_translation_cache:
                if not self.confirm_regenerate("摘要翻译", title):
                    return
            
            self.translate_abstract_button.config(state=tk.DISABLED, text="翻译中...")
            self.start_abstract_translation_thread(self.current_paper, self.update_abstract_translation_in_ui)
        try:
            self.restore_tree_focus()
        except Exception: pass

    def on_check_llm_search(self):
        if not self.current_paper:
            messagebox.showwarning("警告", "请先选择一篇论文")
            return
        
        llm_search_text = self.llm_search_var.get().strip()
        if not llm_search_text or llm_search_text.startswith("例如"):
            messagebox.showwarning("警告", "请先设置AI搜索条件")
            return

        self.check_llm_search_button.config(state=tk.DISABLED, text="检测中...")
        self.llm_search_result_label.config(text="检测中...", foreground="black")
        
        self.start_llm_search_check_thread(self.current_paper, llm_search_text)
        self.restore_tree_focus()

    def start_llm_search_check_thread(self, paper, search_query):
        def check_llm_search():
            score, judgment, reason, tokens_used = self.llm_service.check_paper_relevance(search_query, paper)
            self.root.after(0, self.update_llm_search_check_result, paper, search_query, score, judgment, reason, tokens_used)
        
        thread = threading.Thread(target=check_llm_search)
        thread.daemon = True
        thread.start()

    def update_llm_search_check_result(self, paper, search_query, score, judgment, reason, tokens_used):
        if score is not None:
            cache_key = f"relevance:{paper.get('id')}"
            result_data = {
                'score': score,
                'judgment': judgment,
                'reason': reason,
                'tokens': tokens_used,
                'query': search_query
            }
            self.add_to_cache(self.relevance_cache, cache_key, result_data)

        if self.current_paper and self.current_paper.get('id') == paper.get('id'):
            self.check_llm_search_button.config(state=tk.NORMAL, text="AI搜索符合性检测")
            
            if score is None:
                self.llm_search_result_label.config(text="检测失败", foreground='red')
            else:
                threshold = self.relevance_threshold_var.get()
                result_text = f"{score:.2f} - {judgment}: {reason}"
                fg_color = 'green' if score >= threshold else 'red'
                self.llm_search_result_label.config(text=result_text, foreground=fg_color)
                self.result_label.config(text=f"检测完成: 分数 {score:.2f}, 使用 {tokens_used} tokens")

    def on_llm_translate_title_change(self):
        self.session_data['llm_translate_title'] = self.llm_translate_title_var.get()
        self.save_session_immediate()
        if self.current_paper and self.llm_translate_title_var.get():
            self.start_title_translation_thread(self.current_paper, self.update_title_translation_in_ui)

    def on_adopted_toggle(self):
        if self.current_paper:
            self.toggle_paper_adopted(self.current_paper.get('id'))
            self.display_papers()
        self.root.after(50, self.restore_tree_focus)

    def on_excluded_toggle(self):
        if self.current_paper:
            self.toggle_paper_excluded(self.current_paper.get('id'))
            self.display_papers()
        self.root.after(50, self.restore_tree_focus)

    def restore_ui_layout(self):
        if 'ui_layout' in self.config:
            layout = self.config['ui_layout']
            if 'pane_position' in layout:
                try: self.content_pane.sashpos(0, int(layout['pane_position']))
                except: pass
            if 'window_width' in layout and 'window_height' in layout:
                self.root.geometry(f"{layout['window_width']}x{layout['window_height']}")

    def on_link_click(self, event):
        try:
            idx = self.detail_text.index(f"@{event.x},{event.y}")
            ranges = self.detail_text.tag_ranges('link')
            for i in range(0, len(ranges), 2):
                if self.detail_text.compare(ranges[i], "<=", idx) and self.detail_text.compare(idx, "<", ranges[i+1]):
                    url = self.detail_text.get(ranges[i], ranges[i+1]).strip()
                    if url: webbrowser.open(url)
                    break
        except Exception: pass

    def on_note_change(self, event=None):
        if self.current_paper:
            self.set_paper_note(self.current_paper.get('id'), self.note_text.get(1.0, tk.END).strip())

    def get_paper_note(self, pid): return self.session_data['paper_notes'].get(pid, "")
    def set_paper_note(self, pid, note):
        self.session_data['paper_notes'][pid] = note
        self.save_session_immediate()

    def on_rating_scale_drag(self, event=None):
        self.rating_label.config(text=f"{self.rating_var.get():.1f}")
        self.rating_scale_dragging = True

    def on_rating_scale_release(self, event=None):
        if self.rating_scale_dragging:
            self.rating_scale_dragging = False
            self.on_search()
            self.save_session_immediate()

    def on_relevance_threshold_change(self, event=None):
        self.relevance_threshold_label.config(text=f"{self.relevance_threshold_var.get():.2f}")
        self.config['llm_relevance_threshold'] = self.relevance_threshold_var.get()
        self.save_session_immediate()

    # --- 核心搜索逻辑修改 ---

    def text_search(self, text, pattern, mode="general"):
        if not text or not pattern: return False
        t, p = str(text).lower(), str(pattern).lower()
        if mode == "general": return p in t
        elif mode == "keywords":
            t_words = set(re.split(r'[;,\s]+', t))
            p_words = set(re.split(r'[;,\s]+', p))
            return bool(t_words & p_words)
        return False

    def on_search(self, event=None):
        """执行搜索：根据当前状态选择数据源，并应用所有筛选条件"""
        if self.llm_search_active or not self.json_file_path: return
        
        # 1. 确定数据源 (Universe)
        # 如果处于AI结果状态，数据源是AI筛选结果；否则是整个数据库
        if self.llm_search_results_active:
            source_data = self.ai_search_results
            self.result_label.config(text=f"AI搜索结果: {len(source_data)}篇 (在此范围内筛选)")
        else:
            source_data = self.sorted_data
            if hasattr(self, 'result_label'): # 防止初始化时标签不存在
                self.result_label.config(text=f"数据库总数: {len(source_data)}篇")

        # 2. 获取当前筛选条件
        stext = self.search_var.get().strip()
        ktext = self.keywords_area_var.get().strip()
        min_r = self.rating_var.get()
        show_a = self.show_adopted_only_var.get()
        show_e = self.show_excluded_var.get()
        show_n = self.show_notes_only_var.get()
        
        sel_tracks = None
        if self.track_vars:
            sel_tracks = {t for t, v in self.track_vars.items() if v.get()}
            self.session_data.setdefault('search_state', {})['selected_tracks'] = list(sel_tracks)
            self.save_session_immediate()

        sel_statuses = None
        if hasattr(self, 'status_vars') and self.status_vars:
            sel_statuses = {s for s, v in self.status_vars.items() if v.get()}
            self.session_data.setdefault('search_state', {})['selected_statuses'] = list(sel_statuses)
            self.save_session_immediate()
        
        # 3. 执行过滤
        self.filtered_data = []
        for p in source_data:
            has_numeric = p.get('_has_numeric_rating', False)
            rating = p.get('_calculated_rating') if has_numeric else None
            # 仅对有数值评分（或被强制为0的拒绝类）应用最低评分筛选；无数值且非拒绝类则免疫
            if has_numeric:
                if rating is None: continue
                if rating < min_r: continue
            
            pid = p.get('id', '')
            if show_a and (not pid or not self.is_paper_adopted(pid)): continue
            if not show_e and (pid and self.is_paper_excluded(pid)): continue
            if show_n and not self.get_paper_note(pid).strip(): continue
            
            if sel_tracks is not None and p.get('track', '') not in sel_tracks: continue
            if sel_statuses is not None and p.get('status', '') not in sel_statuses: continue
            
            if stext:
                if not any(self.text_search(p.get(f, ''), stext) for f in ['title', 'abstract', 'tldr']): continue
            if ktext:
                if not any(self.text_search(p.get(f, ''), ktext) for f in ['keywords', 'primary_area', 'track']): continue
            





            
            self.filtered_data.append(p)
        
        self.display_papers()
        
        # 更新状态栏提示
        prefix = "AI结果筛选: " if self.llm_search_results_active else "筛选结果: "
        self.result_label.config(text=f"{prefix}找到 {len(self.filtered_data)} 篇论文")

    def on_llm_search(self, event=None):
        """开始AI搜索"""
        if not self.json_file_path: return
        query = self.llm_search_var.get().strip()
        if not query or query.startswith("例如"): 
            messagebox.showwarning("提示", "请输入搜索内容")
            return
            
        if not messagebox.askyesno("确认LLM搜索", "确定要消耗Token基于当前列表进行搜索吗？"): return
        
        # 记录当前用于AI搜索的输入列表（即当前屏幕上显示的列表）
        input_papers = self.filtered_data.copy()
        if not input_papers:
            messagebox.showinfo("提示", "当前列表为空，无法进行AI搜索")
            return

        self.llm_search_active = True
        self.disable_filter_controls()
        self.show_llm_progress_window()
        
        def run_search():
            # 这里的输入是 input_papers (当前筛选结果)
            res = self.llm_service.llm_search_papers(query, input_papers, self.config)
            
            # 搜索完成，更新状态
            if res:
                self.ai_search_results = [r['paper'] for r in res]
                self.llm_search_results_active = True
            else:
                # 搜索失败或无结果，保持原有状态，不进入AI结果模式
                self.ai_search_results = []
                self.llm_search_results_active = False # 或者保持之前的状态? 这里的逻辑是如果搜不到，就别切模式
            
            self.llm_search_active = False
            
            # 回到主线程更新UI
            self.root.after(0, self.finish_llm_search)

        threading.Thread(target=run_search, daemon=True).start()

    def finish_llm_search(self):
        """AI搜索结束后的UI处理"""
        self.hide_llm_progress_window()
        self.enable_filter_controls()
        
        if self.llm_search_results_active:
            self.undo_llm_search_button.config(state=tk.NORMAL)
            # 搜索完成后，触发一次 on_search，此时 Universe 变为 ai_search_results
            # 由于刚搜完通常不需要额外过滤，所以这里的 on_search 会显示所有 AI 结果
            self.on_search() 
        else:
            messagebox.showinfo("AI搜索", "未找到符合条件的论文")

    def undo_llm_search(self):
        """退回AI搜索，恢复全量数据库视图"""
        if not self.llm_search_results_active:
            return
        
        # 重置状态
        self.llm_search_results_active = False
        self.ai_search_results = []
        self.undo_llm_search_button.config(state=tk.DISABLED)
        
        # 重新触发搜索，此时 Universe 变回 sorted_data (全量)
        # 会自动应用当前界面上保留的筛选条件 (Rating, Keywords等)
        self.on_search()
        self.save_session_immediate()

    def clear_search(self):
        if self.llm_search_active: return
        self.search_var.set("")
        self.keywords_area_var.set("")
        self.show_notes_only_var.set(False)
        if hasattr(self, 'track_vars'):
            self.select_all_var.set(True)
            for var in self.track_vars.values(): var.set(True)
        self.on_search()

    def on_complete_translation(self):
        """触发完成所有普通翻译（包括摘要和TLDR）"""
        if self.current_paper:
            self.complete_translation_button.config(state=tk.DISABLED, text="翻译中...")
            self.start_complete_translation_thread(self.current_paper, self.update_complete_translation_in_ui)
        self.restore_tree_focus()

    def on_regenerate_translation(self):
        if self.current_paper:
            title = self.current_paper.get('title', '')
            if messagebox.askyesno("确认重新生成", f"确定要重新生成 '{title[:20]}...' 的普通翻译吗？"):
                self.regenerate_translation_button.config(state=tk.DISABLED, text="重新生成中...")
                self.start_regenerate_translation_thread(self.current_paper, self.update_regenerate_translation_in_ui)
        self.restore_tree_focus()


    def enable_search_controls(self):
        """(旧方法兼容) 重新启用搜索控件"""
        self.enable_filter_controls()

    def disable_filter_controls(self):
        """禁用所有筛选控件"""
        # 搜索输入框和按钮
        for w in [self.search_entry, self.keywords_area_entry, self.search_button, 
                  self.clear_search_button, self.track_button, self.llm_search_button, 
                  self.undo_llm_search_button, self.rating_scale, getattr(self, 'relevance_scale', None), getattr(self, 'llm_search_entry', None)]:
            try:
                if w is not None:
                    w.config(state=tk.DISABLED)
            except Exception:
                pass
        
        # 递归禁用复选框
        def disable_checkbuttons(widget):
            for child in widget.winfo_children():
                if isinstance(child, ttk.Checkbutton):
                    child.config(state=tk.DISABLED)
                elif isinstance(child, (ttk.Frame, tk.Frame, ttk.LabelFrame)):
                    disable_checkbuttons(child)
        
        # 从主控区域开始禁用
        # 假设所有控制都在 self.root 的顶部区域，直接遍历整个 root 可能会有点慢但比较稳
        # 这里为了精准，遍历包含控制按钮的 top_frame 或 ctrl_frame
        # 由于布局层级较深，直接禁用 root 下的 Checkbutton 可能更简单，或者只针对 ctrl_frame
        disable_checkbuttons(self.root) 

    def enable_filter_controls(self):
        """启用所有筛选控件"""
        for w in [self.search_entry, self.keywords_area_entry, self.search_button, 
                  self.clear_search_button, self.track_button, self.llm_search_button, getattr(self, 'llm_search_entry', None)]:
            try:
                if w is not None:
                    w.config(state=tk.NORMAL)
            except Exception:
                pass
        
        if self.llm_search_results_active:
             self.undo_llm_search_button.config(state=tk.NORMAL)
        else:
             self.undo_llm_search_button.config(state=tk.DISABLED)
             
        self.rating_scale.config(state=tk.NORMAL)
        try:
            if hasattr(self, 'relevance_scale') and self.relevance_scale is not None:
                self.relevance_scale.config(state=tk.NORMAL)
        except Exception:
            pass
        
        def enable_checkbuttons(widget):
            for child in widget.winfo_children():
                if isinstance(child, ttk.Checkbutton):
                    child.config(state=tk.NORMAL)
                elif isinstance(child, (ttk.Frame, tk.Frame, ttk.LabelFrame)):
                    enable_checkbuttons(child)
        
        enable_checkbuttons(self.root)

    def on_llm_search_focusin(self, event):
        if self.llm_search_entry.get().startswith("例如"):
            self.llm_search_entry.delete(0, tk.END)
            self.llm_search_entry.config(foreground="black")

    def on_llm_search_focusout(self, event):
        if not self.llm_search_entry.get():
            self.llm_search_entry.insert(0, "例如: 找出所有有关语言-视觉模型的论文")
            self.llm_search_entry.config(foreground="gray")

    def show_llm_progress_window(self):
        """显示AI搜索进度条弹窗"""
        if self.llm_progress_window and self.llm_progress_window.winfo_exists():
            return
        
        self.llm_progress_window = tk.Toplevel(self.root)
        self.llm_progress_window.title("AI搜索进行中...")
        self.llm_progress_window.geometry("400x120")
        self.llm_progress_window.resizable(False, False)
        # 设置为模态窗口
        self.llm_progress_window.transient(self.root)
        self.llm_progress_window.grab_set()
        
        frame = ttk.Frame(self.llm_progress_window)
        frame.pack(expand=True, fill=tk.BOTH, padx=20, pady=20)
        
        ttk.Label(frame, text="AI正在分析论文，请稍候...", font=('Arial', 10)).pack(pady=(0, 10))
        self.llm_progress = ttk.Progressbar(frame, mode='indeterminate', length=350)
        self.llm_progress.pack(pady=5)
        self.llm_progress.start()
        
        # 居中显示
        self.llm_progress_window.update_idletasks()
        try:
            x = self.root.winfo_x() + (self.root.winfo_width() // 2) - (self.llm_progress_window.winfo_width() // 2)
            y = self.root.winfo_y() + (self.root.winfo_height() // 2) - (self.llm_progress_window.winfo_height() // 2)
            self.llm_progress_window.geometry(f"+{x}+{y}")
        except: pass

    def hide_llm_progress_window(self):
        """隐藏AI搜索进度条弹窗"""
        if self.llm_progress_window:
            try:
                if self.llm_progress: self.llm_progress.stop()
                self.llm_progress_window.grab_release()
                self.llm_progress_window.destroy()
            except: pass
            self.llm_progress_window = None
            self.llm_progress = None

    def display_papers(self):
        cur_id = self.current_paper.get('id') if self.current_paper else None
        for i in self.paper_tree.get_children(): self.paper_tree.delete(i)
        
        id_map = {}
        for p in self.filtered_data:
            has_numeric = p.get('_has_numeric_rating', False)
            rating = p.get('_calculated_rating') if has_numeric else None
            status = ("✅" if self.is_paper_adopted(p.get('id')) else "") + ("✖" if self.is_paper_excluded(p.get('id')) else "")

            rating_display = f"{rating:.1f}" if (has_numeric and rating is not None) else "无"
            item = self.paper_tree.insert('', 'end', values=(
                status,
                rating_display,
                p.get('status', '') or p.get('track', ''),
                p.get('track', ''),
                p.get('title', '无标题')
            ))
            if p.get('id'): id_map[str(p.get('id'))] = item
            
        if cur_id and str(cur_id) in id_map:
            self.paper_tree.selection_set(id_map[str(cur_id)])
            self.paper_tree.see(id_map[str(cur_id)])
            
        if hasattr(self, 'total_papers_label'):
            self.total_papers_label.config(text=f"当前论文计数: {len(self.filtered_data)}")

    def on_paper_select(self, event):
        sel = self.paper_tree.selection()
        if not sel: return
        idx = self.paper_tree.index(sel[0])
        if idx < len(self.filtered_data):
            self.current_paper = self.filtered_data[idx]
            self.display_paper_details(self.current_paper)
            self.start_translation_thread(self.current_paper, self.update_translation_in_ui)
            if self.llm_translate_title_var.get():
                self.start_title_translation_thread(self.current_paper, self.update_title_translation_in_ui)
            
            for b in [self.generate_tldr_button, self.translate_abstract_button, self.regenerate_translation_button]:
                b.config(state=tk.NORMAL)
            self.complete_translation_button.config(state=tk.DISABLED, text="完成普通翻译")

    def display_paper_details(self, paper):
        """显示论文详情，优先使用缓存瞬间渲染"""
        self.detail_text.config(state=tk.NORMAL)
        self.detail_text.delete(1.0, tk.END)
        
        pid = paper.get('id', '')
        self.note_text.delete(1.0, tk.END)
        self.note_text.insert(1.0, self.get_paper_note(pid))
        self.adopted_var.set(self.is_paper_adopted(pid))
        self.excluded_var.set(self.is_paper_excluded(pid))
        
        # 恢复AI检测按钮状态
        self.check_llm_search_button.config(state=tk.NORMAL, text="AI搜索符合性检测")
        self.llm_search_result_label.config(text="")
        
        # 显示之前的AI检测结果
        relevance_key = f"relevance:{pid}"
        if relevance_key in self.relevance_cache:
            res = self.relevance_cache[relevance_key]
            thresh = self.relevance_threshold_var.get()
            score = res.get('score', 0)
            color = 'green' if score >= thresh else 'red'
            self.llm_search_result_label.config(text=f"{score:.2f} - {res.get('judgment')}: {res.get('reason')}", foreground=color)
        
        # --- 渲染文本内容 ---
        self.detail_text.insert(tk.END, "原文标题: ", 'bold')
        self.detail_text.insert(tk.END, f"{paper.get('title','')}\n")
        
        # 标题翻译 (读取缓存)
        self.detail_text.insert(tk.END, "中文翻译: ", 'bold')
        cached_title = self.translation_cache.get(f"标题:{paper.get('title','')}")
        self.detail_text.insert(tk.END, f"{cached_title}\n" if cached_title else "翻译中...\n", 'translation' if cached_title else 'translating')
        
        # LLM标题翻译 (读取缓存)
        self.detail_text.insert(tk.END, "LLM翻译: ", 'bold')
        llm_t = self.title_translation_cache.get(f"title_llm:{paper.get('title','')}")
        self.detail_text.insert(tk.END, f"{llm_t['translation']}\n" if llm_t else "等待请求...\n", 'title_translation' if llm_t else 'translating')
        self.detail_text.insert(tk.END, "\n")
        
        # 链接
        if paper.get('site'): self.detail_text.insert(tk.END, f"原文链接: {paper.get('site')}\n", 'link')
        if paper.get('pdf'): self.detail_text.insert(tk.END, f"PDF链接: {paper.get('pdf')}\n", 'link')
        self.detail_text.insert(tk.END, "\n")
        
        # 作者信息处理
        authors = [a.strip() for a in paper.get('author', '').split(';') if a.strip()]
        homepages = [h.strip() for h in paper.get('homepage', '').split(';')]
        genders = [g.strip() for g in paper.get('gender', '').split(';')]
        
        if authors:
            self.detail_text.insert(tk.END, "作者: ", 'bold')
            for i, auth in enumerate(authors):
                if i > 0: self.detail_text.insert(tk.END, "; ")
                tag = 'author_unknown'
                if i < len(genders):
                    g = genders[i].upper()
                    if g == 'M': tag = 'author_male'
                    elif g == 'F': tag = 'author_female'
                
                start = self.detail_text.index(tk.END)
                self.detail_text.insert(tk.END, auth, tag)
                if i < len(homepages) and homepages[i]:
                    self.detail_text.tag_add(f"alink_{i}", start, self.detail_text.index(tk.END))
                    self.detail_text.tag_config(f"alink_{i}", underline=True)
                    self.detail_text.tag_bind(f"alink_{i}", "<Button-1>", lambda e, u=homepages[i]: webbrowser.open(u))
            self.detail_text.insert(tk.END, "\n\n")

        # 评分
        self.detail_text.insert(tk.END, "评分信息\n", 'bold')
        has_numeric = paper.get('_has_numeric_rating', False)
        rv = paper.get('_calculated_rating') if has_numeric else None
        if has_numeric and rv is not None:
            tag = 'rating_high' if rv >= 4 else ('rating_low' if rv <= 2 and rv > 0 else 'rating_medium')
            self.detail_text.insert(tk.END, f"综合评分: {rv:.2f}\n", tag)
        else:
            self.detail_text.insert(tk.END, "综合评分: 无\n", 'rating_medium')
        for f in ['rating', 'confidence', 'recommendation']:
            if paper.get(f): self.detail_text.insert(tk.END, f"{f.title()}: {paper.get(f)}\n")
        self.detail_text.insert(tk.END, "\n")
        
        # TLDR & AI总结
        title = paper.get('title', '')
        tldr = paper.get('tldr', '')
        self.detail_text.insert(tk.END, "TLDR\n", 'bold')
        
        sum_key = f"summary:{title}"
        if sum_key in self.summary_cache:
            if tldr: self.detail_text.insert(tk.END, f"{tldr}\n\n")
            res = self.summary_cache[sum_key]
            self.detail_text.insert(tk.END, f"AI总结 (消耗 {res['tokens']} tokens):\n", 'bold')
            self.detail_text.insert(tk.END, f"英文: {res['english']}\n", 'summary')
            self.detail_text.insert(tk.END, f"中文: {res['chinese']}\n", 'summary')
        elif tldr:
            self.detail_text.insert(tk.END, f"{tldr}\n")
        else:
            self.detail_text.insert(tk.END, "暂无TLDR，点击下方按钮生成AI总结\n")
        self.detail_text.insert(tk.END, "\n")
        
        # 摘要及普通翻译 (读取缓存)
        abstract = paper.get('abstract', '')
        if abstract:
            self.detail_text.insert(tk.END, "摘要\n", 'bold')
            self.detail_text.insert(tk.END, f"{abstract}\n\n")
            
            # --- 立即显示缓存中的摘要翻译 ---
            abs_cache_key = f"摘要:{abstract}"
            if abs_cache_key in self.translation_cache:
                trans_text = self.translation_cache[abs_cache_key]
                tag = 'partial_translation' if "......（未翻译完全" in trans_text else 'translation'
                self.detail_text.insert(tk.END, f"摘要翻译: {trans_text}\n", tag)
                
                # 如果是部分翻译，立刻启用完成按钮
                if tag == 'partial_translation':
                    self.complete_translation_button.config(state=tk.NORMAL, text="完成普通翻译")
                else:
                    self.complete_translation_button.config(state=tk.DISABLED, text="完成普通翻译")
            # -----------------------------

            # LLM 摘要翻译 (读取缓存)
            abs_key = f"abstract_translation:{title}"
            if abs_key in self.abstract_translation_cache:
                res = self.abstract_translation_cache[abs_key]
                self.detail_text.insert(tk.END, f"\nLLM摘要翻译 (消耗 {res['tokens']} tokens):\n", 'bold')
                self.detail_text.insert(tk.END, f"{res['translation']}\n", 'llm_translation')
            self.detail_text.insert(tk.END, "\n")
            
        for f, l in [('keywords', '关键词'), ('primary_area', '主要领域'), ('track', 'Track')]:
            if paper.get(f):
                self.detail_text.insert(tk.END, f"{l}\n", 'bold')
                self.detail_text.insert(tk.END, f"{paper.get(f)}\n\n")
        
        self.highlight_search_terms()
        self.detail_text.config(state=tk.DISABLED)

    def highlight_search_terms(self):
        try:
            self.detail_text.tag_remove('highlight', '1.0', tk.END)
            terms = []
            if hasattr(self, 'search_var'): terms += [t for t in re.split(r'[;,\s]+', self.search_var.get().strip()) if len(t) >= 2]
            if hasattr(self, 'keywords_area_var'): terms += [t for t in re.split(r'[;,\s]+', self.keywords_area_var.get().strip()) if len(t) >= 2]
            
            for term in terms:
                start = '1.0'
                while True:
                    pos = self.detail_text.search(term, start, stopindex=tk.END, nocase=True)
                    if not pos: break
                    end = f"{pos}+{len(term)}c"
                    self.detail_text.tag_add('highlight', pos, end)
                    start = end
        except Exception: pass

    def show_config_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("参数配置")
        dialog.geometry("500x700")
        
        canvas = tk.Canvas(dialog)
        sb = ttk.Scrollbar(dialog, orient="vertical", command=canvas.yview)
        frame = ttk.Frame(canvas)
        
        frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=frame, anchor="nw")
        canvas.configure(yscrollcommand=sb.set)
        canvas.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        
        def _on_mousewheel(event): canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        dialog.bind("<Destroy>", lambda e: canvas.unbind_all("<MouseWheel>"))
        
        vars_map = {}
        
        def add_entry(label, key, note=""):
            ttk.Label(frame, text=label).pack(anchor=tk.W, pady=(10, 5))
            v = tk.StringVar(value=str(self.config.get(key, 0)))
            vars_map[key] = v
            ttk.Entry(frame, textvariable=v, width=10).pack(anchor=tk.W)
            if note: ttk.Label(frame, text=note, foreground='gray').pack(anchor=tk.W)

        add_entry("AI生成TLDR长度限制:", 'llm_tldr_soft_limit', "单位：字")
        ttk.Label(frame, text=f"TLDR硬限制: {self.config['llm_tldr_hard_limit']}").pack(anchor=tk.W)
        
        add_entry("AI搜索软限制:", 'llm_search_soft_limit', "单位：篇")
        add_entry("包含TLDR/摘要的AI搜索软限制:", 'llm_search_tldr_abstract_soft_limit', "单位：篇")
        add_entry("初步搜索阈值比例:", 'preliminary_threshold_ratio', "0-1之间")
        add_entry("AI摘要翻译长度限制:", 'abstract_translation_limit', "单位：字")
        add_entry("最大缓存项数:", 'max_cache_size', "单位：项")
        
        # 清除缓存按钮
        def _clear_cache():
            if messagebox.askyesno("确认清除缓存", "清空缓存将删除所有已生成的翻译/摘要等条目，之后需要重新生成。是否继续？"):
                for c in (self.translation_cache, self.summary_cache,
                          self.abstract_translation_cache, self.title_translation_cache,
                          self.relevance_cache):
                    c.clear()
                if hasattr(self, 'global_cache_order'):
                    self.global_cache_order.clear()
                self.save_cache()
                self.update_cache_status()
                messagebox.showinfo("完成", "缓存已清空")
        ttk.Button(frame, text="清除缓存", command=_clear_cache).pack(anchor=tk.W, pady=(10,5))
        
        ttk.Label(frame, text="翻译服务优先级:", font=('Arial', 10, 'bold')).pack(anchor=tk.W, pady=(20, 5))
        s_frame = ttk.Frame(frame)
        s_frame.pack(fill=tk.X)
        service_vars = {}
        for s in ['mymemory', 'google', 'baidu', 'youdao', 'libre', 'tencent']:
            v = tk.BooleanVar(value=s in self.config.get('translation_services', []))
            service_vars[s] = v
            ttk.Checkbutton(s_frame, text=s, variable=v).pack(side=tk.LEFT, padx=(0, 10))
            
        def save():
            try:
                for k, v in vars_map.items():
                    val = float(v.get()) if '.' in v.get() else int(v.get())
                    self.config[k] = val
                
                self.config['translation_services'] = [k for k, v in service_vars.items() if v.get()]
                ConfigManager.save_config(self.config, self.config_file_path)
                messagebox.showinfo("成功", "配置已保存")
                self.update_cache_status()
                dialog.destroy()
            except ValueError:
                messagebox.showerror("错误", "请输入有效的数字")
                
        ttk.Button(frame, text="保存", command=save).pack(pady=20)

    def initialize_track_selection(self):
        self.track_vars = {}
        saved = self.session_data.get('search_state', {}).get('selected_tracks')
        for t in self.all_tracks:
            self.track_vars[t] = tk.BooleanVar(value=(saved is None or t in saved))
        self.select_all_var = tk.BooleanVar(value=True)

        # 初始化类别筛选 (状态)
        self.status_vars = {}
        saved_status = self.session_data.get('search_state', {}).get('selected_statuses')
        for s in getattr(self, 'all_statuses', []):
            s_lower = (s or '').strip().lower()
            if saved_status is None:
                # 默认不勾选 Desk Reject、Reject 和 Withdraw
                default_selected = s_lower not in ('desk reject', 'reject', 'withdraw')
            else:
                default_selected = s in saved_status
            self.status_vars[s] = tk.BooleanVar(value=default_selected)
        self.select_all_status_var = tk.BooleanVar(value=all(v.get() for v in self.status_vars.values()) if self.status_vars else True)

    def show_track_filter_popup(self):
        if self.track_popup and self.track_popup.winfo_exists():
            self.track_popup.destroy()
            return

        self.track_popup = tk.Toplevel(self.root)
        self.track_popup.overrideredirect(True)
        self.track_popup.attributes('-topmost', True)
        
        x = self.track_button.winfo_rootx()
        y = self.track_button.winfo_rooty() + self.track_button.winfo_height()
        self.track_popup.geometry(f"250x400+{x}+{y}")
        
        mf = ttk.Frame(self.track_popup, relief="solid", borderwidth=1)
        mf.pack(fill=tk.BOTH, expand=True)
        
        cf = ttk.Frame(mf)
        cf.pack(fill=tk.X, padx=5, pady=5)
        
        def toggle_all():
            v = self.select_all_var.get()
            for var in self.track_vars.values(): var.set(v)
            self.on_search()
            
        ttk.Checkbutton(cf, text="(全选)", variable=self.select_all_var, command=toggle_all).pack(side=tk.LEFT)
        ttk.Button(cf, text="关闭", command=self.track_popup.destroy, width=6).pack(side=tk.RIGHT)
        ttk.Separator(mf, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=5)
        
        cv = tk.Canvas(mf, highlightthickness=0)
        sb = ttk.Scrollbar(mf, orient="vertical", command=cv.yview)
        sf = ttk.Frame(cv)
        
        sf.bind("<Configure>", lambda e: cv.configure(scrollregion=cv.bbox("all")))
        cv.create_window((0, 0), window=sf, anchor="nw")
        cv.configure(yscrollcommand=sb.set)
        cv.pack(side="left", fill="both", expand=True, padx=5)
        sb.pack(side="right", fill="y")
        
        def _mw(event): cv.yview_scroll(int(-1*(event.delta/120)), "units")
        cv.bind_all("<MouseWheel>", _mw)
        self.track_popup.bind("<Destroy>", lambda e: cv.unbind_all("<MouseWheel>"))
        
        for t in self.all_tracks:
            ttk.Checkbutton(sf, text=t or "(无Track)", variable=self.track_vars[t], command=self.on_search).pack(anchor=tk.W, pady=2)

    def show_status_filter_popup(self):
        if self.track_popup and self.track_popup.winfo_exists():
            # if track popup open, close it to avoid overlap
            pass

        if hasattr(self, 'status_popup') and self.status_popup and self.status_popup.winfo_exists():
            self.status_popup.destroy()
            return

        self.status_popup = tk.Toplevel(self.root)
        self.status_popup.overrideredirect(True)
        self.status_popup.attributes('-topmost', True)

        x = self.status_button.winfo_rootx()
        y = self.status_button.winfo_rooty() + self.status_button.winfo_height()
        self.status_popup.geometry(f"250x300+{x}+{y}")

        mf = ttk.Frame(self.status_popup, relief="solid", borderwidth=1)
        mf.pack(fill=tk.BOTH, expand=True)

        cf = ttk.Frame(mf)
        cf.pack(fill=tk.X, padx=5, pady=5)

        def toggle_all_status():
            v = self.select_all_status_var.get()
            for var in self.status_vars.values(): var.set(v)
            self.on_search()

        ttk.Checkbutton(cf, text="(全选)", variable=self.select_all_status_var, command=toggle_all_status).pack(side=tk.LEFT)
        ttk.Button(cf, text="关闭", command=self.status_popup.destroy, width=6).pack(side=tk.RIGHT)
        ttk.Separator(mf, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=5)

        cv = tk.Canvas(mf, highlightthickness=0)
        sb = ttk.Scrollbar(mf, orient="vertical", command=cv.yview)
        sf = ttk.Frame(cv)

        sf.bind("<Configure>", lambda e: cv.configure(scrollregion=cv.bbox("all")))
        cv.create_window((0, 0), window=sf, anchor="nw")
        cv.configure(yscrollcommand=sb.set)
        cv.pack(side="left", fill="both", expand=True, padx=5)
        sb.pack(side="right", fill="y")

        def _mw(event): cv.yview_scroll(int(-1*(event.delta/120)), "units")
        cv.bind_all("<MouseWheel>", _mw)
        self.status_popup.bind("<Destroy>", lambda e: cv.unbind_all("<MouseWheel>"))

        for s in getattr(self, 'all_statuses', []):
            ttk.Checkbutton(sf, text=s or "(无类别)", variable=self.status_vars[s], command=self.on_search).pack(anchor=tk.W, pady=2)

    def add_to_cache(self, cache_dict, key, value):
        """Add item and maintain global FIFO order across all caches."""
        cache_name = self._get_cache_name(cache_dict)
        if key in cache_dict:
            del cache_dict[key]
            if cache_name is not None:
                self.global_cache_order.pop((cache_name, key), None)

        cache_dict[key] = value
        if cache_name is not None:
            self.global_cache_order[(cache_name, key)] = cache_dict

        max_size = self.config.get('max_cache_size', 0)
        while len(self.global_cache_order) > max_size:
            (old_name, old_key), old_dict = self.global_cache_order.popitem(last=False)
            old_dict.pop(old_key, None)

        self.update_cache_status()
        self.save_cache()

    def update_cache_status(self):
        total = len(self.global_cache_order) if hasattr(self, 'global_cache_order') else \
                sum(len(c) for c in [self.translation_cache, self.summary_cache, self.abstract_translation_cache, self.title_translation_cache, self.relevance_cache])
        self.cache_status_label.config(text=f"缓存: {total}/{self.config['max_cache_size']}")

    def _get_cache_name(self, cache_dict):
        if cache_dict is self.translation_cache: return 'translation'
        if cache_dict is self.summary_cache: return 'summary'
        if cache_dict is self.abstract_translation_cache: return 'abstract_translation'
        if cache_dict is self.title_translation_cache: return 'title_translation'
        if cache_dict is self.relevance_cache: return 'relevance'
        return None

    def start_translation_thread(self, paper, callback):
        def translate():
            title = paper.get('title', '')
            abstract = paper.get('abstract', '')
            tldr = paper.get('tldr', '')
            
            title_key = f"标题:{title}"
            if title_key in self.translation_cache:
                t_title = self.translation_cache[title_key]
            else:
                t_title = self.translation_service.translate_text_online_single(title, "标题")
            
            t_tldr = ""
            abs_key = f"摘要:{abstract}"
            t_abs = ""
            more = False
            
            if abs_key in self.translation_cache:
                t_abs = self.translation_cache[abs_key]
                if "......（未翻译完全" in t_abs:
                    more = True
            elif abstract:
                partial = abstract[:500]
                t_abs = self.translation_service.translate_text_online_single(partial, "摘要")
                if len(abstract) > 500:
                    t_abs += "......（未翻译完全，可点击下方按钮完成全部翻译）"
                    more = True
            
            self.root.after(0, callback, paper, t_title, t_tldr, t_abs, more)
        threading.Thread(target=translate, daemon=True).start()

    def start_regenerate_translation_thread(self, paper, callback):
        def regenerate():
            for key in [f"标题:{paper.get('title')}", f"摘要:{paper.get('abstract')}"]:
                if key in self.translation_cache: del self.translation_cache[key]
            self.start_translation_thread(paper, callback)
        threading.Thread(target=regenerate, daemon=True).start()

    def start_summary_thread(self, paper, callback):
        def run():
            res, _ = self.llm_service.generate_tldr_summary(paper.get('title', ''), paper.get('abstract', ''))
            self.root.after(0, callback, paper, res)
        threading.Thread(target=run, daemon=True).start()

    def start_abstract_translation_thread(self, paper, callback):
        def run():
            res, tokens = self.translation_service.translate_abstract_with_llm(paper.get('title', ''), paper.get('abstract', ''))
            result = {'translation': res, 'tokens': tokens} if res else None
            self.root.after(0, callback, paper, result)
        threading.Thread(target=run, daemon=True).start()

    def start_complete_translation_thread(self, paper, callback):
        def run():
            abs_text = self.translation_service.translate_text_online_batch(paper.get('abstract', ''), "摘要")
            tldr_text = ""
            if paper.get('tldr'):
                 tldr_text = self.translation_service.translate_text_online_single(paper.get('tldr'), "TLDR")
            self.root.after(0, callback, paper, abs_text, tldr_text)
        threading.Thread(target=run, daemon=True).start()

    def start_title_translation_thread(self, paper, callback):
        def run():
            res, tokens = self.translation_service.translate_title_with_llm(paper.get('title', ''))
            result = {'translation': res, 'tokens': tokens} if res else None
            self.root.after(0, callback, paper, result)
        threading.Thread(target=run, daemon=True).start()

    def update_complete_translation_in_ui(self, paper, abs_text, tldr_text):
        if abs_text: self.add_to_cache(self.translation_cache, f"摘要:{paper.get('abstract')}", abs_text)
        
        if self.current_paper and self.current_paper['id'] == paper['id']:
            self.detail_text.config(state=tk.NORMAL)
            
            if abs_text:
                start = self.detail_text.search("摘要翻译:", "1.0", tk.END)
                if start:
                    end = self.detail_text.search("\n\n", start, tk.END) or self.detail_text.search("\n", f"{start}+1c", tk.END)
                    if end:
                        self.detail_text.delete(start, end)
                        self.detail_text.insert(start, f"摘要翻译: {abs_text}\n\n", 'translation')
            
            if tldr_text:
                tldr_start = self.detail_text.search("TLDR\n", "1.0", tk.END)
                if tldr_start:
                    pos = self.detail_text.search("\n", f"{tldr_start}+1l", tk.END)
                    if pos:
                        trans_start = self.detail_text.search("TLDR翻译:", pos, tk.END)
                        if trans_start and self.detail_text.compare(trans_start, "<", self.detail_text.search("摘要\n", pos, tk.END) or tk.END):
                            line_end = self.detail_text.search("\n", trans_start, tk.END)
                            self.detail_text.delete(trans_start, line_end)
                            self.detail_text.insert(trans_start, f"TLDR翻译: {tldr_text}", 'translation')
                        else:
                            self.detail_text.insert(f"{pos}+1c", f"TLDR翻译: {tldr_text}\n", 'translation')

            self.complete_translation_button.config(state=tk.NORMAL, text="完成普通翻译")
            self.detail_text.config(state=tk.DISABLED)

    def update_translation_in_ui(self, paper, t_title, t_tldr, t_abs, more):
        if t_title: self.add_to_cache(self.translation_cache, f"标题:{paper.get('title')}", t_title)
        if t_abs: self.add_to_cache(self.translation_cache, f"摘要:{paper.get('abstract')}", t_abs)
        
        if not self.current_paper or self.current_paper['id'] != paper['id']: return
        
        self.detail_text.config(state=tk.NORMAL)
        start = self.detail_text.search("中文翻译:", "1.0", tk.END)
        if start:
            end = self.detail_text.search("\n", start, tk.END)
            self.detail_text.delete(start, end)
            self.detail_text.insert(start, f"中文翻译: {t_title}", 'translation')
        
        if t_abs:
            abs_anchor = self.detail_text.search("摘要翻译:", "1.0", tk.END)
            tag = 'partial_translation' if more else 'translation'
            if abs_anchor:
                end = self.detail_text.search("\n", abs_anchor, tk.END)
                self.detail_text.delete(abs_anchor, end)
                self.detail_text.insert(abs_anchor, f"摘要翻译: {t_abs}\n", tag)
            else:
                abs_header = self.detail_text.search("摘要\n", "1.0", tk.END)
                if abs_header:
                    next_section = self.detail_text.search("关键词\n", abs_header, tk.END) or \
                                   self.detail_text.search("主要领域\n", abs_header, tk.END) or \
                                   self.detail_text.search("Track\n", abs_header, tk.END) or tk.END
                    if next_section != tk.END:
                        self.detail_text.insert(next_section, f"摘要翻译: {t_abs}\n\n", tag)
                    else:
                        self.detail_text.insert(tk.END, f"摘要翻译: {t_abs}\n\n", tag)

        if more: self.complete_translation_button.config(state=tk.NORMAL, text="完成普通翻译")
        self.detail_text.config(state=tk.DISABLED)

    def update_regenerate_translation_in_ui(self, paper, *args):
        self.update_translation_in_ui(paper, *args)
        self.regenerate_translation_button.config(state=tk.NORMAL, text="重新生成普通翻译")

    def update_summary_in_ui(self, paper, res):
        if res: self.add_to_cache(self.summary_cache, f"summary:{paper.get('title')}", res)
        if self.current_paper and self.current_paper['id'] == paper['id']:
            self.detail_text.config(state=tk.NORMAL)
            if res:
                start = self.detail_text.search("TLDR\n", "1.0", tk.END)
                if start:
                    no_tldr = self.detail_text.search("暂无TLDR", start, tk.END)
                    if no_tldr: self.detail_text.delete(no_tldr, self.detail_text.search("\n", no_tldr, tk.END))
                    pos = self.detail_text.search("\n\n", start, tk.END) or self.detail_text.search("\n", f"{start}+1c", tk.END)
                    if pos:
                        txt = f"\nAI总结 (消耗 {res['tokens']} tokens):\n英文: {res['english']}\n中文: {res['chinese']}\n"
                        self.detail_text.insert(pos, txt, 'summary')
            self.generate_tldr_button.config(state=tk.NORMAL, text="LLM生成TLDR")
            self.detail_text.config(state=tk.DISABLED)

    def update_abstract_translation_in_ui(self, paper, res):
        if res: self.add_to_cache(self.abstract_translation_cache, f"abstract_translation:{paper.get('title')}", res)
        if self.current_paper and self.current_paper['id'] == paper['id']:
            self.detail_text.config(state=tk.NORMAL)
            if res:
                start = self.detail_text.search("摘要\n", "1.0", tk.END)
                if start:
                    end = self.detail_text.search("关键词\n", start, tk.END) or \
                          self.detail_text.search("主要领域\n", start, tk.END) or \
                          self.detail_text.search("Track\n", start, tk.END) or tk.END
                    if not self.detail_text.search("LLM摘要翻译", start, tk.END):
                        if end != tk.END:
                            self.detail_text.insert(end, f"\nLLM摘要翻译 (消耗 {res['tokens']} tokens):\n", 'bold')
                            self.detail_text.insert(f"{end}+1l", f"{res['translation']}\n\n", 'llm_translation')
                        else:
                            self.detail_text.insert(tk.END, f"\nLLM摘要翻译 (消耗 {res['tokens']} tokens):\n", 'bold')
                            self.detail_text.insert(tk.END, f"{res['translation']}\n\n", 'llm_translation')
            self.translate_abstract_button.config(state=tk.NORMAL, text="LLM翻译摘要")
            self.detail_text.config(state=tk.DISABLED)

    def update_title_translation_in_ui(self, paper, res):
        if res: self.add_to_cache(self.title_translation_cache, f"title_llm:{paper.get('title')}", res)
        if self.current_paper and self.current_paper['id'] == paper['id']:
            self.detail_text.config(state=tk.NORMAL)
            start = self.detail_text.search("LLM翻译:", "1.0", tk.END)
            if start:
                end = self.detail_text.search("\n", start, tk.END)
                self.detail_text.delete(start, end)
                if res: self.detail_text.insert(start, f"LLM翻译: {res['translation']}", 'title_translation')
            self.detail_text.config(state=tk.DISABLED)

if __name__ == "__main__":
    root = tk.Tk()
    app = PaperReviewBrowser(root)
    root.mainloop()