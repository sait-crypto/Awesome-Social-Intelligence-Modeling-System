"""
项目入口1：从核心数据库生成README论文表格部分
"""
import os
import sys
import re
import json
import hashlib
from typing import Dict, List, Tuple
from urllib.parse import quote

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.database_manager import DatabaseManager
from src.core.database_model import Paper
from src.core.config_loader import get_config_instance
from src.core.update_file_utils import get_update_file_utils
from src.utils import truncate_text, format_authors, create_hyperlink, escape_markdown, escape_markdown_base

class ReadmeGenerator:
    """README生成器"""
    
    def __init__(self):
        self.config = get_config_instance()
        self.settings = self.config.settings
        self.db_manager = DatabaseManager()
        self.update_utils = get_update_file_utils()
        self.project_root = str(self.config.project_root)
        self.assets_dir = self.settings['paths'].get('assets_dir', 'assets/').replace('\\', '/').rstrip('/')
        self.legacy_figure_dir = self.settings['paths'].get('figure_dir', 'figures/').replace('\\', '/').rstrip('/')
        self.complete_list_database_path = self.settings['paths'].get(
            'complete_list_database',
            os.path.join(self.project_root, 'paper_database_complete_list.csv'),
        )
        self.complete_list_output_path = self.settings['paths'].get(
            'complete_list_output',
            os.path.join(self.project_root, 'COMPLETE_LIST.md'),
        )
        self.paper_metadata_path = self.settings['paths'].get(
            'paper_metadata',
            os.path.join(self.project_root, 'config', 'paper_metadata.json'),
        )
        self._current_display_papers: List[Paper] = []
        self._rendered_paper_anchors: Dict[Tuple[str, str], str] = {}
        
        self.max_title_length = int(self.settings['readme'].get('max_title_length', 100))
        self.max_authors_length = int(self.settings['readme'].get('max_authors_length', 150))
        self.max_analogy_summary_length = self._read_length_setting('max_analogy_summary_length', 240)
        self.summary_field_limits = {
            'summary_motivation': self._read_length_setting('max_summary_motivation_length', 240),
            'summary_innovation': self._read_length_setting('max_summary_innovation_length', 240),
            'summary_method': self._read_length_setting('max_summary_method_length', 240),
            'summary_conclusion': self._read_length_setting('max_summary_conclusion_length', 240),
            'summary_limitation': self._read_length_setting('max_summary_limitation_length', 240),
        }
        self.max_notes_length = self._read_length_setting('max_notes_length', 400)
        self.translation_separator = self.settings['database'].get('translation_separator', '[翻译]')
        
        # ===== 恢复：配置项兼容逻辑 =====
        # 兼容配置项为 bool 或 str 的情况；确保得到布尔值
        truncate_val = self.settings['readme'].get('truncate_translation', 'true')
        try:
            self.is_truncate_translation = str(truncate_val).lower() == 'true'
        except Exception:
            self.is_truncate_translation = bool(truncate_val)
        
        # 兼容配置项为 bool 或 str 的情况；确保得到布尔值
        markdown_val = self.settings['readme'].get('enable_markdown', 'false')
        try:
            self.enable_markdown = str(markdown_val).lower() == 'true'
        except Exception:
            self.enable_markdown = bool(markdown_val)

    def _read_length_setting(self, name: str, default: int) -> int:
        """Read a non-negative README character limit; zero means unlimited."""
        try:
            return max(0, int(self.settings['readme'].get(name, default)))
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _truncate_field(text: str, max_length: int) -> str:
        value = str(text or '')
        if max_length <= 0 or len(value) <= max_length:
            return value
        if max_length == 1:
            return '…'
        return value[:max_length - 1].rstrip() + '…'

    def _load_paper_metadata(self) -> Tuple[bool, Dict[str, str]]:
        """Load the single source of truth for README paper information."""
        try:
            with open(self.paper_metadata_path, 'r', encoding='utf-8') as f:
                raw = json.load(f)
            if not isinstance(raw, dict):
                raise ValueError('paper metadata must be a JSON object')
        except Exception as e:
            print(f'Failed to load paper metadata {self.paper_metadata_path}: {e}')
            return False, {}

        defaults = {
            'paper_title': 'TODO: Paper Title',
            'authors': 'TODO: Authors',
            'affiliations': 'TODO: Affiliations',
            'venue': 'TODO',
            'year': 'TODO',
            'arxiv_id': '',
            'paper_url': '',
            'bibtex_type': 'misc',
            'bibtex_key': 'todo_social_intelligence',
            'bibtex_author': 'TODO: Authors',
            'bibtex_note': 'Paper metadata to be announced',
            'repository_url': '',
        }
        return True, {key: str(raw.get(key, value) or '').strip() for key, value in defaults.items()}

    @staticmethod
    def _single_line(value: str) -> str:
        return re.sub(r'\s+', ' ', str(value or '')).strip()

    def _generate_paper_intro_content(self, metadata: Dict[str, str]) -> str:
        title = self._single_line(metadata.get('paper_title')) or 'TODO: Paper Title'
        paper_url = self._single_line(metadata.get('paper_url'))
        title_display = f'[{title}]({paper_url})' if paper_url else title
        authors = metadata.get('authors') or 'TODO: Authors'
        affiliations = metadata.get('affiliations') or 'TODO: Affiliations'
        venue = self._single_line(metadata.get('venue')) or 'TODO'
        year = self._single_line(metadata.get('year')) or 'TODO'
        return (
            'This repository accompanies our paper:\n\n'
            f'> **{title_display}** \\\n'
            f'> {authors} \\\n'
            f'> {affiliations} \\\n'
            f'> **Venue:** {venue} &nbsp;|&nbsp; **Year:** {year}\n\n'
            '> 🌟 If this resource helps your research, please star the repository and cite our paper.'
        )

    def _generate_paper_badges_content(self, metadata: Dict[str, str]) -> str:
        arxiv_id = self._single_line(metadata.get('arxiv_id'))
        arxiv_id = re.sub(r'^(?:arXiv:|https?://arxiv\.org/(?:abs|pdf)/)', '', arxiv_id, flags=re.I)
        arxiv_id = arxiv_id.removesuffix('.pdf').strip('/')
        badge_value = quote(arxiv_id or 'TBD', safe='.')
        paper_url = self._single_line(metadata.get('paper_url'))
        arxiv_url = paper_url or (f'https://arxiv.org/abs/{arxiv_id}' if arxiv_id else 'https://arxiv.org/')
        return (
            '![PRs Welcome](https://img.shields.io/badge/PRs-Welcome-blue) '
            f'[![arXiv](https://img.shields.io/badge/arXiv-{badge_value}-009688.svg)]({arxiv_url})'
        )

    def _generate_citation_content(self, metadata: Dict[str, str]) -> str:
        entry_type = re.sub(r'[^A-Za-z]', '', metadata.get('bibtex_type', 'misc')) or 'misc'
        entry_key = re.sub(r'[^A-Za-z0-9:_-]', '_', metadata.get('bibtex_key', 'todo_social_intelligence'))
        title = self._single_line(metadata.get('paper_title')) or 'TODO: Paper Title'
        author = self._single_line(metadata.get('bibtex_author') or metadata.get('authors')) or 'TODO: Authors'
        venue = self._single_line(metadata.get('venue')) or 'TODO'
        year = self._single_line(metadata.get('year')) or 'TODO'
        note = self._single_line(metadata.get('bibtex_note'))
        url = self._single_line(metadata.get('paper_url') or metadata.get('repository_url'))

        fields = [
            ('title', title),
            ('author', author),
            ('howpublished', venue),
            ('year', year),
        ]
        if note:
            fields.append(('note', note))
        if url:
            fields.append(('url', url))

        bibtex_lines = [f'@{entry_type}{{{entry_key},']
        for index, (name, value) in enumerate(fields):
            comma = ',' if index < len(fields) - 1 else ''
            bibtex_lines.append(f'  {name:<12} = {{{value}}}{comma}')
        bibtex_lines.append('}')
        return '## Citation\n\n```bibtex\n' + '\n'.join(bibtex_lines) + '\n```'

    @staticmethod
    def _replace_managed_block(content: str, start_marker: str, end_marker: str, body: str) -> Tuple[bool, str]:
        start_index = content.find(start_marker)
        end_index = content.find(end_marker, start_index + len(start_marker))
        if start_index == -1 or end_index == -1:
            return False, content
        body_start = start_index + len(start_marker)
        replacement = '\n' + body.strip() + '\n'
        return True, content[:body_start] + replacement + content[end_index:]

    def _render_paper_metadata_blocks(self, content: str) -> Tuple[bool, str]:
        success, metadata = self._load_paper_metadata()
        if not success:
            return False, content

        blocks = [
            ('<!-- PAPER_BADGES_START -->', '<!-- PAPER_BADGES_END -->', self._generate_paper_badges_content(metadata)),
            ('<!-- PAPER_INTRO_START -->', '<!-- PAPER_INTRO_END -->', self._generate_paper_intro_content(metadata)),
            ('<!-- PAPER_CITATION_TOP_START -->', '<!-- PAPER_CITATION_TOP_END -->', self._generate_citation_content(metadata)),
            ('<!-- PAPER_CITATION_BOTTOM_START -->', '<!-- PAPER_CITATION_BOTTOM_END -->', self._generate_citation_content(metadata)),
        ]
        for start_marker, end_marker, body in blocks:
            replaced, content = self._replace_managed_block(content, start_marker, end_marker, body)
            if not replaced:
                print(f'Missing README managed block: {start_marker} ... {end_marker}')
                return False, content
        return True, content

    def _load_display_papers(self) -> Tuple[bool, List[Paper]]:
        """加载并预处理用于 README 展示的论文列表"""
        success, papers = self.db_manager.load_database()
        if not success:
            return False, []

        display_papers = []
        for paper in papers:
            if not paper.show_in_readme or paper.conflict_marker:
                continue
            # Apply category aliases/migrations in memory so README generation is
            # compatible with older database values without rewriting the database.
            paper.category = self.update_utils.normalize_category_value(paper.category, self.config)
            if self.is_truncate_translation:
                self._truncate_translation_in_paper(paper)
            display_papers.append(paper)
        return True, display_papers

    def _load_complete_list_papers(self) -> Tuple[bool, List[Paper]]:
        """Load the independent database used only for COMPLETE_LIST.md.

        This read-only path deliberately bypasses UpdateProcessor and AIGenerator.
        Entries hidden from the detailed README and conflict variants are included
        because this file is an exhaustive view of its source database. Only rows
        without a title are omitted because they cannot form a useful list item.
        """
        success, papers = self.update_utils.read_data(self.complete_list_database_path)
        if not success:
            return False, []

        complete_papers = [paper for paper in papers if str(paper.title or '').strip()]
        complete_papers.sort(key=lambda p: str(p.title or '').casefold())
        complete_papers.sort(
            key=lambda p: (str(p.date or ''), str(p.submission_time or '')),
            reverse=True,
        )
        return True, complete_papers

    @staticmethod
    def _sanitize_complete_list_cell(value: str) -> str:
        return (
            str(value or '')
            .strip()
            .replace('\\', '\\\\')
            .replace('|', '\\|')
            .replace('\r\n', '<br>')
            .replace('\r', '<br>')
            .replace('\n', '<br>')
        )

    def _generate_complete_list_row(self, paper: Paper) -> str:
        title = (
            str(paper.title or '')
            .strip()
            .replace('\r\n', ' ')
            .replace('\r', ' ')
            .replace('\n', ' ')
        )
        title_cell = create_hyperlink(title, str(paper.paper_url or '').strip()).replace('|', '\\|')
        venue = self._sanitize_complete_list_cell(paper.conference) or '—'

        links = []
        seen_urls = set()

        def append_link(label: str, url: str):
            normalized = str(url or '').strip()
            if not normalized or normalized in seen_urls:
                return
            seen_urls.add(normalized)
            links.append(f'[{label}]({normalized.replace(" ", "%20")})')

        append_link('Paper', paper.paper_url)
        append_link('Project', paper.project_url)
        if paper.doi:
            append_link('DOI', f'https://doi.org/{paper.doi}')

        links_cell = ' · '.join(links) if links else '—'
        return f'| {title_cell} | {venue} | {links_cell} |\n'

    def generate_complete_list_content(self) -> str:
        """Generate the compact list from its independent Paper database."""
        success, papers = self._load_complete_list_papers()
        if not success:
            return ''

        rows = ''.join(self._generate_complete_list_row(paper) for paper in papers)
        return (
            '# Complete Paper List\n\n'
            '<!-- This file is generated by src/convert.py. Do not edit it manually. -->\n\n'
            f'This compact index contains {len(papers)} papers. '
            'For categorized summaries and detailed review fields, return to the '
            '[main README](./README.md).\n\n'
            '| Title | Venue | Links |\n'
            '|:--|:--:|:--:|\n'
            f'{rows}'
        )

    def update_complete_list_file(self) -> bool:
        """Write COMPLETE_LIST.md without modifying the independent database."""
        content = self.generate_complete_list_content()
        if not content:
            print(f'Unable to generate complete list from: {self.complete_list_database_path}')
            return False

        try:
            output_dir = os.path.dirname(self.complete_list_output_path)
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
            with open(self.complete_list_output_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f'Complete list updated: {self.complete_list_output_path}')
            return True
        except Exception as e:
            print(f'Failed to write complete list: {e}')
            return False

    def generate_readme_tables(self) -> str:
        """生成README的论文表格部分"""
        success, display_papers = self._load_display_papers()
        self._current_display_papers = display_papers
        if not success:
            print("加载数据库失败，无法生成README表格")
            return ""

        papers_by_category = self._group_papers_by_category(display_papers)
        # Render a multi-category paper in full only at its first category.
        # Later categories keep a compact table row linking to that entry.
        self._rendered_paper_anchors = {}

        markdown_output = ""
        roots, children_map = self._build_category_tree()

        def render_category(cat, depth: int = 0) -> str:
            category_name = cat.get('name', cat.get('unique_name'))
            category_key = cat.get('unique_name')
            category_count, _ = self._get_category_paper_count_and_anchor(category_key, display_papers)
            if category_count == 0:
                return ""

            heading_level = min(6, 3 + depth)
            heading_prefix = "| " if depth == 0 else ""
            section = f"\n{'#' * heading_level} {heading_prefix}{category_name} ({category_count} papers)\n\n"

            category_papers = papers_by_category.get(category_key, [])
            if category_papers:
                section += self._generate_category_table(category_papers)

            for child in children_map.get(category_key, []):
                section += render_category(child, depth + 1)

            return section

        for root in roots:
            markdown_output += render_category(root)

        return markdown_output

    def _truncate_translation_in_paper(self, paper: Paper):
        """对 Paper 对象中的所有字符串字段执行翻译截断"""
        sep = self.translation_separator
        for field in paper.__dataclass_fields__:
            val = getattr(paper, field)
            if isinstance(val, str) and sep in val:
                setattr(paper, field, val.split(sep)[0].rstrip())

    def _group_papers_by_category(self, papers: List[Paper]) -> Dict[str, List[Paper]]:
        grouped = {}
        for p in papers:
            # 支持多分类
            raw = p.category or ""
            parts = [x.strip() for x in str(raw).split('|') if x.strip()]
            if not parts:
                grouped.setdefault("Uncategorized", []).append(p)
            else:
                for cat in parts:
                    grouped.setdefault(cat, []).append(p)
        
        # 排序：按提交时间倒序
        for k in grouped:
            grouped[k].sort(key=lambda x: x.submission_time or "", reverse=True)
            
        return grouped

    def _generate_category_table(self, papers: List[Paper]) -> str:
        if not papers: return ""
        header = "| Title & Info | Analogy Summary | Pipeline | Summary |\n"
        sep = "|:--| :---: | :----: | :---: |\n"
        rows = "".join(self._generate_paper_or_reference_row(p) for p in papers)
        return header + sep + rows

    @staticmethod
    def _paper_identity(paper: Paper) -> Tuple[str, str]:
        return paper.get_key()

    def _paper_anchor(self, paper: Paper) -> str:
        identity = '\0'.join(self._paper_identity(paper))
        if not identity.strip('\0'):
            identity = str(paper.uid or paper.citation_key or paper.title or '')
        digest = hashlib.sha1(identity.encode('utf-8')).hexdigest()[:12]
        return f'paper-entry-{digest}'

    def _generate_paper_or_reference_row(self, paper: Paper) -> str:
        identity = self._paper_identity(paper)
        anchor = self._rendered_paper_anchors.get(identity)
        if anchor:
            title = self._sanitize_field(truncate_text(paper.title, self.max_title_length))
            return f'|[↪ {title}](#{anchor}) <sub>Full entry</sub>||||\n'

        anchor = self._paper_anchor(paper)
        self._rendered_paper_anchors[identity] = anchor
        return self._generate_paper_row(paper, anchor)

    def _generate_paper_row(self, paper: Paper, anchor: str = '') -> str:
        col1 = self._generate_title_authors_cell(paper)
        if anchor:
            col1 = f'<a id="{anchor}"></a>{col1}'
        col2 = self._generate_analogy_cell(paper)
        col3 = self._generate_pipeline_cell(paper)
        col4 = self._generate_summary_cell(paper)
        if col4:
            col4 = f" <div style=\"line-height: 1.05;font-size: 0.8em\"> {col4}</div>"
        return f"|{col1}|{col2}|{col3}|{col4}|\n"

    def _generate_analogy_cell(self, paper: Paper) -> str:
        if not paper.analogy_summary:
            return ""
        value = self._truncate_field(paper.analogy_summary, self.max_analogy_summary_length)
        return self._sanitize_field(value)

    def _generate_title_authors_cell(self, paper: Paper) -> str:
        if not paper.title:
            return "Authors (to fill)"

        title = truncate_text(paper.title, self.max_title_length)
        title = self._sanitize_field(title)
        authors = self._sanitize_field(format_authors(paper.authors, self.max_authors_length))
        if self.enable_markdown:
            authors = authors.replace('*', '\\' + '*')

        date = paper.date if paper.date else ""

        conference_badge = ""
        if paper.conference:
            conference_encoded = quote(paper.conference, safe='').replace('-', '--')
            conference_badge = f" [![Publish](https://img.shields.io/badge/Conference-{conference_encoded}-blue)]()"

        project_badge = ""
        if paper.project_url:
            if 'github.com' in paper.project_url:
                match = re.search(r'github\.com/([^/]+/[^/]+)', paper.project_url)
                if match:
                    repo_path = match.group(1)
                    project_badge = f'[![Star](https://img.shields.io/github/stars/{repo_path}.svg?style=social&label=Star)](https://github.com/{repo_path})'
                else:
                    project_badge = f'[![Project](https://img.shields.io/badge/Project-View-blue)]({paper.project_url})'
            else:
                project_badge = f'[![Project](https://img.shields.io/badge/Project-View-blue)]({paper.project_url})'

        badges = ""
        if project_badge or conference_badge:
            badges = f"{project_badge}{conference_badge}<br>"

        title_with_link = create_hyperlink(title, paper.paper_url)

        multi_line = ""
        try:
            raw_cat = paper.category or ""
            parts = [p.strip() for p in str(raw_cat).split('|') if p.strip()]
            if len(parts) > 1:
                links = []
                for uname in parts:
                    display = self.config.get_category_field(uname, 'name') or uname
                    _, anchor = self._get_category_paper_count_and_anchor(uname, self._current_display_papers)
                    links.append(f"[{display}](#{anchor})")
                links_str = ", ".join(links)
                multi_line = f" <br> <span style=\"color:cyan\">[multi-category：{links_str}]</span>"
        except Exception:
            multi_line = ""

        return f"{badges}{title_with_link} <br> {authors} <br> {date}{multi_line}"

    def _generate_pipeline_cell(self, paper: Paper) -> str:
        """生成Pipeline图单元格（支持最多3张图片，显示在同一格内）"""
        if not paper.pipeline_image:
            return ""

        parts = [p.strip() for p in str(paper.pipeline_image).split('|') if p.strip()]
        if not parts:
            return ""

        existing_imgs = []
        for raw_path in parts[:3]:
            normalized = raw_path.replace('\\', '/')
            full_path = normalized if os.path.isabs(normalized) else os.path.join(self.project_root, normalized)
            if os.path.exists(full_path):
                if os.path.isabs(normalized):
                    try:
                        rel_path = os.path.relpath(full_path, self.project_root).replace('\\', '/')
                    except Exception:
                        rel_path = normalized
                    existing_imgs.append(rel_path)
                else:
                    existing_imgs.append(normalized)
            else:
                print(f"警告: pipeline图片不存在: {raw_path}")

        if not existing_imgs:
            return ""

        n = len(existing_imgs)
        if n == 1:
            return f'<img width="1200" alt="pipeline" src="{existing_imgs[0]}">' 
        else:
            imgs_html = ''.join([f'<img width="1000" style="display:block;margin:6px auto" alt="pipeline" src="{p}">' for p in existing_imgs])
            return f'<div style="display:flex;flex-direction:column;gap:6px;align-items:center">{imgs_html}</div>'

    def _generate_summary_cell(self, paper: Paper) -> str:
        # 复用原有逻辑
        fields = []
        tags_map = {
            'summary_motivation': 'motivation',
            'summary_innovation': 'innovation',
            'summary_method': 'method',
            'summary_conclusion': 'conclusion',
            'summary_limitation': 'limitation'
        }
        
        for k, name in tags_map.items():
            val = getattr(paper, k, "")
            if val:
                disp = self.config.get_tag_field(k, 'display_name') or name
                disp = str(disp).replace('\r', '').replace('\n', '')
                val = self._truncate_field(val, self.summary_field_limits.get(k, 0))
                fields.append(f"**[{disp}]** {self._sanitize_field(val)}")
        
        full_html = "<br>".join(fields)
        
        notes_html = ""
        if paper.notes:
            notes = self._truncate_field(paper.notes, self.max_notes_length)
            notes_html = f'<details><summary>**[notes]**</summary><div style="margin-top:6px">{self._sanitize_field(notes)}</div></details>'
            
        if not full_html and not notes_html: return ""
        
        if full_html:
            blk = f'<details><summary>**[summary]**</summary><div style="margin-top:6px">{full_html}</div></details>'
            if notes_html: return blk + '<div style="margin-top:6px">' + notes_html + '</div>'
            return blk
        return notes_html

    def _sanitize_field(self, text: str) -> str:
        if not text: return ""
        s = str(text).strip().replace('\r\n', '\n').replace('\r', '\n')
        if not self.enable_markdown:
            s = escape_markdown(s)
        else:
            s = escape_markdown_base(s)
        return s.replace('\n', '<br>')

    def _slug(self, name: str) -> str:
        s = str(name or "").strip()
        s = re.sub(r'[^A-Za-z0-9\s\-]', '', s)
        return re.sub(r'\s+', '-', s)

    def _build_category_tree(self):
        cats = [c for c in self.config.get_active_categories() if c.get('enabled', True)]
        children_map = {}
        roots = []

        for category in cats:
            predecessor = category.get('predecessor_category')
            if predecessor:
                children_map.setdefault(predecessor, []).append(category)
            else:
                roots.append(category)

        roots.sort(key=lambda x: x.get('order', 0))
        for key in children_map:
            children_map[key].sort(key=lambda x: x.get('order', 0))

        return roots, children_map

    def _get_category_paper_count_and_anchor(self, unique_name: str, all_papers: List[Paper]) -> Tuple[int, str]:
        cat_config = self.config.get_category_by_unique_name(unique_name)
        if not cat_config:
            return 0, ""

        _, children_map = self._build_category_tree()
        target_cats = set()
        stack = [unique_name]
        while stack:
            current = stack.pop()
            if current in target_cats:
                continue
            target_cats.add(current)
            for child in children_map.get(current, []):
                stack.append(child['unique_name'])

        count = 0
        for p in all_papers:
            p_cats = set([x.strip() for x in str(p.category or "").split('|')])
            p_cats.discard("")
            if not p_cats:
                p_cats.add("Uncategorized")
            if not p_cats.isdisjoint(target_cats):
                count += 1

        prefix = "|-" if cat_config.get('predecessor_category') is None else ""
        raw_anchor = f"{prefix}{cat_config.get('name', unique_name)} {count} papers"
        return count, self._slug(raw_anchor)

    def _generate_quick_links(self) -> str:
        """根据 categories 配置递归生成 Quick Links 列表（插入到表格前）"""
        success, display_papers = self._load_display_papers()
        if success:
            self._current_display_papers = display_papers
        roots, children_map = self._build_category_tree()
        if not roots:
            return ""

        lines = ["### Quick Links", ""]

        def append_link(category, depth: int = 0):
            name = category.get('name', category.get('unique_name'))
            try:
                category_key = category.get('unique_name')
                category_count, anchor = self._get_category_paper_count_and_anchor(category_key, display_papers)
            except Exception:
                category_count = 0
                anchor = ""

            indent = "  " * (depth + 1)
            lines.append(f"{indent}- [{name}](#{anchor}) ({category_count} papers)")

            for child in children_map.get(category.get('unique_name'), []):
                append_link(child, depth + 1)

        for root in roots:
            append_link(root)

        return "\n".join(lines)

    def update_readme_file(self) -> bool:
        """Update README.md and the independently generated complete list."""
        readme_path = os.path.join(self.config.project_root, 'README.md')

        if not os.path.exists(readme_path):
            print(f"README文件不存在: {readme_path}")
            return False

        try:
            with open(readme_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            print(f"读取README文件失败: {e}")
            return False

        metadata_success, content = self._render_paper_metadata_blocks(content)
        if not metadata_success:
            return False

        new_tables = self.generate_readme_tables()
        tables_intro = self._generate_quick_links()

        start_marker = "## Selected paper list"
        end_marker = "=====List End====="

        start_index = content.find(start_marker)
        end_index = content.find(end_marker)

        if start_index == -1 or end_index == -1:
            print("无法找到README中的标记部分")
            return False

        try:
            success, valid_papers = self._load_display_papers()
            if not success:
                valid_papers = []
            self._current_display_papers = valid_papers
            unique_keys = set()
            for p in valid_papers:
                unique_keys.add(p.get_key())
            total_unique = len(unique_keys)
        except Exception:
            total_unique = 0

        before_tables = content[:start_index + len(start_marker)] + f" ({total_unique} papers)"
        after_tables = content[end_index:]

        if tables_intro:
            new_content = before_tables + "\n" + tables_intro + "\n\n" + new_tables + "\n" + after_tables
        else:
            new_content = before_tables +  "\n" + new_tables + "\n" + after_tables

        try:
            with open(readme_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"README文件已更新: {readme_path}")
            return self.update_complete_list_file()
        except Exception as e:
            print(f"写入README文件失败: {e}")
            return False

def main():
    """主函数"""
    print("开始生成README论文表格...")

    generator = ReadmeGenerator()

    tables = generator.generate_readme_tables()
    print("论文表格生成完成")

    # 更新README文件
    success = generator.update_readme_file()

    if success:
        print("README文件更新成功")
    else:
        print("README文件更新失败")
        print("\n生成的表格内容：")
        print(tables)


if __name__ == "__main__":
    main()
