"""
通用工具函数
"""
import urllib.parse
import shutil
import os
import re
import json
import hashlib
import uuid
from typing import List, Dict, Any, Optional,Tuple
from datetime import datetime
from pathlib import Path



def validate_url(url: str) -> bool:
    """验证URL格式"""
    if not url:
        return False
    
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z0-9-]{2,}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    
    return bool(re.match(url_pattern, url))


def clean_doi(doi: str, conflict_marker: str = None) -> str:
    """清理DOI，移除URL部分和冲突标记"""
    if not doi:
        return ""
    
    # 如果提供了冲突标记，先移除
    if conflict_marker:
        doi = doi.replace(conflict_marker, "").strip()
    
    doi = doi.strip()
    
    # 移除常见的URL前缀
    prefixes = ['https://doi.org/', 'http://doi.org/', 
                'https://dx.doi.org/', 'http://dx.doi.org/',
                'doi:', 'DOI:']
    
    for prefix in prefixes:
        if doi.lower().startswith(prefix.lower()):
            doi = doi[len(prefix):]
            break
    #进一步，清除doi/字串及前面的内容
    match = re.search(r"doi/(.*)", doi, flags=re.IGNORECASE)
    doi = match.group(1) if match else doi
    return doi


def validate_doi(doi: str, check_format: bool = True, conflict_marker: str = None) -> Tuple[bool, str]:
    """验证DOI格式，返回(是否有效, 清理后的DOI)"""
    if not doi:
        return (False, "")
    
    # 清理DOI
    cleaned_doi = clean_doi(doi, conflict_marker)
    
    if not cleaned_doi:
        return (False, "")
    
    # 如果不需要格式验证，直接返回
    if not check_format:
        return (True, cleaned_doi)
    
    # DOI正则表达式
    doi_pattern = re.compile(r'^10\.\d{4,9}/[-._;()/:A-Z0-9]+$', re.IGNORECASE)
    
    if bool(re.match(doi_pattern, cleaned_doi)):
        return (True, cleaned_doi)
    else:
        return (False, cleaned_doi)


def format_authors(authors: str, max_length: int = 150) -> str:
    """格式化作者列表"""
    if not authors:
        return ""
    
    authors = str(authors)
    # 清理多余空格和换行
    authors = ' '.join(authors.split())
    
    # 如果作者列表太长，截断
    if len(authors) > max_length:
        # 尝试在逗号处截断
        parts = authors.split(',')
        truncated = parts[0]
        
        for i in range(1, len(parts)):
            if len(truncated + ', ' + parts[i]) <= max_length - 3:  # 为"..."留空间
                truncated += ', ' + parts[i]
            else:
                truncated += ', ...'
                break
        
        return truncated
    
    return authors


def validate_authors(authors: str, max_length: int = 150) -> Tuple[bool, str]:
    """验证作者格式，返回(是否有效, 格式化后的作者)"""
    if not authors:
        return (False, "")
    
    formatted = format_authors(authors, max_length)
    return (len(formatted) > 0, formatted)


def normalize_pipeline_image(path: str, figure_dir: str = "figures") -> str:
    """
    规范化pipeline图片路径
    输入可以是：1) 文件名 2) 相对路径 3) 绝对路径
    输出：相对于项目根的路径，如 "figures/image.png"
    """
    if not path or not str(path).strip():
        return ""
    
    path_s = str(path).strip()
    
    # 统一使用正斜杠
    path_s = path_s.replace('\\', '/')
    figure_dir = figure_dir.replace('\\', '/').rstrip('/')
    # 如果 figure_dir 是绝对路径（来自 setting.config），取其 basename 以保证返回值为相对路径（例如 "figures"）
    if os.path.isabs(figure_dir):
        figure_dir = os.path.basename(figure_dir)
    
    # 如果是绝对路径，提取文件名并放到相对的 figure_dir 下
    if os.path.isabs(path_s):
        filename = os.path.basename(path_s)
        return f"{figure_dir}/{filename}"
    
    # 如果已经是相对路径且以figure_dir开头，直接返回
    if path_s.startswith(figure_dir + '/'):
        return path_s
    
    # 如果只是文件名（不包含路径分隔符），添加figure_dir前缀
    if '/' not in path_s and '\\' not in path_s:
        return f"{figure_dir}/{path_s}"
    
    # 其他情况：提取文件名并放到figure_dir下
    filename = os.path.basename(path_s)
    return f"{figure_dir}/{filename}"


def validate_pipeline_image(path: str, figure_dir: str = "figures") -> Tuple[bool, str]:
    """
    验证 pipeline 图片（支持多图），返回 (是否有效, 规范化后的路径或多图以";"连接的字符串)
    - 允许使用分隔符 `;` 或中文 `；` 输入多张图片
    - 最多允许 3 张图片；超过则返回 False
    - 每张图片使用 `normalize_pipeline_image` 规范化并验证扩展名与位于 figure_dir 下
    """
    if not path or not str(path).strip():
        return (True, "")  # 允许为空

    path_s = str(path).strip()

    # 支持多分隔符：; 或 中文 ；
    parts = [p.strip() for p in re.split(r'[;；]', path_s) if p.strip()]

    if not parts:
        return (True, "")

    # 限制最多 3 张图片
    if len(parts) > 3:
        # 仍返回规范化的前3项以便提示，但判定为无效
        normalized_parts = [normalize_pipeline_image(p, figure_dir) for p in parts[:3]]
        return (False, ";".join(normalized_parts))

    normalized_parts = []
    valid_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg'}

    # 规范化 figure_dir 用于比较
    fig_dir_norm = figure_dir.replace('\\', '/').rstrip('/')
    if os.path.isabs(fig_dir_norm):
        fig_dir_norm = os.path.basename(fig_dir_norm)

    for p in parts:
        normalized = normalize_pipeline_image(p, figure_dir)
        ext = os.path.splitext(normalized)[1].lower()
        if ext not in valid_extensions:
            return (False, normalized)
        if not normalized.startswith(fig_dir_norm + '/'):
            return (False, normalized)
        normalized_parts.append(normalized)

    # 以分号分隔返回规范化后的路径
    return (True, ";".join(normalized_parts))

def validate_date(date_str: Any) -> Tuple[bool, str]:
    """
    验证并规范化日期格式
    流程：
    1. 转换为字符串并去除空白
    2. 尝试清洗（去除时分秒，统一分隔符）
    3. 验证是否符合格式，支持日缺省和日月份缺省
    
    返回: (是否有效, 规范化后的日期字符串)
    """
    if date_str is None:
        return (True, "")
        
    # 1. 转字符串并去除首尾空格
    s_val = str(date_str).strip()
    if not s_val:
        return (True, "")

    # 捕获原始值，防止后续split空格时截断非标准日期（如 "Oct 27, 2025"）
    original_val = s_val

    # Zotero 在中文界面中可能导出“四月 17, 2026”形式的日期。
    # 必须在按空格去除时间部分之前处理，否则月份会被单独截出。
    chinese_months = (
        "一月", "二月", "三月", "四月", "五月", "六月",
        "七月", "八月", "九月", "十月", "十一月", "十二月",
    )
    localized_match = re.fullmatch(
        r"(十一月|十二月|一月|二月|三月|四月|五月|六月|七月|八月|九月|十月)\s+(\d{1,2})\s*,\s*(\d{4})",
        s_val,
    )
    if localized_match:
        month_text, day_text, year_text = localized_match.groups()
        month = chinese_months.index(month_text) + 1
        try:
            datetime(int(year_text), month, int(day_text))
        except ValueError:
            return (False, original_val)
        return (True, f"{year_text}-{month:02d}-{int(day_text):02d}")

    # 2. 去除时间部分
    if ' ' in s_val:
        s_val = s_val.split(' ')[0]
    
    try:
        final_str = ""
        
        # 3. 统一分隔符：将 / 和 . 替换为 -
        s_val = re.sub(r'[/\.]', '-', s_val)
        
        # 4. 处理纯数字格式
        if s_val.isdigit():
            if len(s_val) == 4:   # YYYY -> YYYY
                final_str = s_val
            elif len(s_val) == 6: # YYYYMM -> YYYY-MM
                final_str = f"{s_val[:4]}-{s_val[4:]}"
            elif len(s_val) == 8: # YYYYMMDD -> YYYY-MM-DD
                final_str = f"{s_val[:4]}-{s_val[4:6]}-{s_val[6:]}"
            else:
                return (False, original_val)
        
        # 5. 处理带分隔符的格式
        else:
            parts = s_val.split('-')
            # 过滤空串
            parts = [p for p in parts if p]
            
            if not parts:
                return (False, original_val)
            
            year = parts[0]
            if len(year) != 4 or not year.isdigit():
                return (False, original_val)

            if len(parts) == 1:   # YYYY
                final_str = year
            elif len(parts) == 2: # YYYY-MM
                month = int(parts[1])
                if not (1 <= month <= 12): return (False, original_val)
                final_str = f"{year}-{month:02d}"
            elif len(parts) >= 3: # YYYY-MM-DD
                month = int(parts[1])
                day = int(parts[2])
                # 利用 datetime 验证日期的合法性
                try:
                    datetime(int(year), month, day)
                except ValueError:
                    return (False, original_val)
                final_str = f"{year}-{month:02d}-{day:02d}"
            else:
                return (False, original_val)

        return (True, final_str)

    except (ValueError, IndexError):
        return (False, original_val)


def validate_invalid_fields(invalid_fields: str, allowed_variables=None) -> Tuple[bool, str]:
    """
    验证 invalid_fields 字段
    invalid_fields 是以 | 分隔的 tag variable 列表（JSON中可对应为字符串数组）
    
    流程：
    1. 如果为空，返回有效
    2. 按 | 分割
    3. 验证每个部分是否是合法变量名
    4. 若提供 allowed_variables，则每项必须在允许集合中
    4. 返回验证结果和错误信息
    
    参数:
        invalid_fields: | 分隔的字段 variable 列表
        allowed_variables: 可选，允许的字段 variable 集合/列表
    
    返回: (是否有效, 错误信息)
    """
    if not invalid_fields or str(invalid_fields).strip() == "":
        return (True, "")
    
    if isinstance(invalid_fields, list):
        parts = [str(p).strip() for p in invalid_fields if str(p).strip()]
    else:
        invalid_fields_str = str(invalid_fields).strip()
        parts = [p.strip() for p in invalid_fields_str.split('|') if p.strip()]
    
    if not parts:
        return (True, "")

    allowed_set = None
    if allowed_variables is not None:
        allowed_set = {str(v).strip() for v in allowed_variables if str(v).strip()}

    var_pattern = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')

    # 验证每个部分是否都是合法变量名
    for part in parts:
        if not var_pattern.match(part):
            return (False, f"invalid_fields 中含有非法字段名: '{part}'（应为合法 variable）")
        if allowed_set is not None and part not in allowed_set:
            return (False, f"invalid_fields 中字段不存在于当前 tag 配置: '{part}'")
    
    return (True, "")

    
def extract_doi_from_url(url: str) -> Optional[str]:
    """从URL中提取DOI"""
    if not url:
        return None
    
    # 匹配DOI URL
    doi_patterns = [
        r'doi\.org/(10\.\d{4,9}/[-._;()/:A-Z0-9]+)',
        r'dx\.doi\.org/(10\.\d{4,9}/[-._;()/:A-Z0-9]+)',
        r'doi:(10\.\d{4,9}/[-._;()/:A-Z0-9]+)'
    ]
    
    for pattern in doi_patterns:
        match = re.search(pattern, url, re.IGNORECASE)
        if match:
            return match.group(1)
    
    return None


def ensure_directory(path: str) -> bool:
    """确保目录存在，如果不存在则创建"""
    try:
        Path(path).mkdir(parents=True, exist_ok=True)
        return True
    except Exception as e:
        print(f"创建目录失败 {path}: {e}")
        return False




def truncate_text(text: str, max_length: int, ellipsis: str = "...") -> str:
    """截断文本，保留最大长度"""
    if not text:
        return ""
    
    if len(str(text)) <= max_length:
        return text
    
    return text[:max_length - len(ellipsis)] + ellipsis



def get_current_timestamp() -> str:
    """获取当前时间戳"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def generate_paper_uid(title: str, doi: str, length: int = 8) -> str:
    """
    根据论文的 title 和 doi 生成一个稳定的短 UID（默认 8 字符十六进制）
    如果 title 和 doi 都为空，则回退为短 UUID
    """
    t = (title or "").strip()
    d = (doi or "").strip()
    key = f"{t}|{d}"
    if not t and not d:
        return str(uuid.uuid4())[:length]
    h = hashlib.sha1(key.encode('utf-8')).hexdigest()
    return h[:length]


def compare_papers(paper1: Dict, paper2: Dict, key_fields: List[str] = None) -> List[str]:
    """比较两篇论文的差异，返回差异字段列表"""
    if key_fields is None:
        key_fields = ['doi', 'title', 'authors']
    
    differences = []
    
    for field in key_fields:
        val1 = paper1.get(field, "")
        val2 = paper2.get(field, "")
        
        if str(val1).strip().lower() != str(val2).strip().lower():
            differences.append(field)
    
    return differences


def merge_paper_data(existing: Dict, new: Dict, prefer_new: bool = True) -> Dict:
    """合并两篇论文的数据"""
    result = existing.copy()
    
    for key, new_value in new.items():
        existing_value = existing.get(key, "")
        
        if not existing_value or (prefer_new and new_value):
            result[key] = new_value
    
    return result


def _escape_md_text(text: str) -> str:
    """对 Markdown 链接文本做基础转义（中括号/反斜杠/换行）"""
    if text is None:
        return ""
    s = str(text)
    s = s.replace("\\", "\\\\")
    s = s.replace("\n", " ")
    s = s.replace("]", "\\]")
    s = s.replace("[", "\\[")
    return s

def create_hyperlink(text: str, url: str) -> str:
    """
    生成 Markdown 风格超链接： [text](url)
    - 当 url 为空或 None 时仅返回文本
    - 对显示文本做基础转义以避免破坏 Markdown
    """
    if not url:
        return _escape_md_text(text)
    # 保证 URL 中的空格等被安全编码，但保留常见 URL 字符
    try:
        parsed = urllib.parse.urlsplit(url)
        if not parsed.scheme:
            # 若缺少 scheme，假定为 https
            url = "https://" + url
        # 只对 URL 的路径/查询部分做 quote，保留 :// 和主机
        url = urllib.parse.urlunsplit(parsed._replace(path=urllib.parse.quote(parsed.path, safe="/"), query=urllib.parse.quote_plus(parsed.query, safe="=&")) )
    except Exception:
        url = url.replace(" ", "%20")
    return f"[{_escape_md_text(text)}]({url})"


def escape_markdown(text: str) -> str:
    """转义Markdown特殊字符"""

    if not text:
        return ""
    text = str(text)
    # 需要转义的Markdown字符
    special_chars = ['\\', '`', '*', '_', '{', '}', '[', ']', '(', ')', '#', '+', '-', '.', '!']
    
    for char in special_chars:
        text = text.replace(char, '\\' + char)
    
    return text
def escape_markdown_base(text: str) -> str:
    """只转义容易引起问题的Markdown字符：反斜杠、方括号、圆括号"""
    if not text:
        return ""
    text = str(text)
    special_chars = ['\\', '[', ']', '(', ')']
    
    for char in special_chars:
        text = text.replace(char, '\\' + char)
    
    return text

def sanitize_filename(filename: str) -> str:
    """清理文件名，移除非法字符"""
    # 移除非法字符
    illegal_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
    for char in illegal_chars:
        filename = filename.replace(char, '_')
    
    # 移除开头和结尾的空格和点
    filename = filename.strip('. ')
    
    # 限制长度
    if len(filename) > 255:
        name, ext = os.path.splitext(filename)
        filename = name[:255 - len(ext)] + ext
    
    return filename





def figure_exists_in_repo(figure_path: str, project_root: str = None) -> bool:
    """
    检查图片是否存在于仓库中
    - figure_path: 规范化后的图片路径
    - project_root: 项目根目录，如果为None则使用当前工作目录
    """
    if not figure_path:
        return False
    
    if project_root is None:
        from src.core.config_loader import get_config_instance
        project_root = str(get_config_instance().project_root)
    
    # 构建完整路径
    full_path = os.path.join(project_root, figure_path)
    
    # 检查文件是否存在
    return os.path.isfile(full_path)


def backup_file(filepath: str, backup_dir: str) -> Optional[str]:
    """
    统一备份文件/文件夹函数（兼容文件和文件夹）
    逻辑：
    - 文件：原文件名(无后缀) + "__backup_" + timestamp + 后缀
      例如：data.xlsx -> data__backup_20250101_120000.xlsx
    - 文件夹：原文件夹名 + "__backup_" + timestamp
      例如：figures -> figures__backup_20250101_120000
    
    参数:
        filepath: 源文件/文件夹路径
        backup_dir: 备份目录路径
    
    返回:
        备份路径（文件/文件夹），失败则返回 None
    """
    # 检查源路径是否存在
    if not os.path.exists(filepath):
        print(f"❌ [备份失败] 路径不存在: {filepath}")
        return None

    try:
        # 确保备份根目录存在
        ensure_directory(backup_dir)
        
        # 解析源路径的基础名称（文件名/文件夹名）
        base_name = os.path.basename(filepath)
        # 生成时间戳
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 区分处理：文件 vs 文件夹
        if os.path.isfile(filepath):
            # 处理文件：拆分后缀
            name, ext = os.path.splitext(base_name)
            backup_name = f"{name}__backup_{timestamp}{ext}"
            backup_path = os.path.join(backup_dir, backup_name)
            # 复制文件（保留元数据）
            shutil.copy2(filepath, backup_path)
        elif os.path.isdir(filepath):
            # 处理文件夹：无后缀，直接拼接
            backup_name = f"{base_name}__backup_{timestamp}"
            backup_path = os.path.join(backup_dir, backup_name)
            # 递归复制文件夹（处理目标已存在的情况）
            if os.path.exists(backup_path):
                # 若备份文件夹已存在，追加随机后缀避免冲突（可选逻辑）
                backup_path += f"_{os.urandom(4).hex()}"
            shutil.copytree(filepath, backup_path)
        else:
            print(f"❌ [备份失败] 既不是文件也不是文件夹: {filepath}")
            return None
        
        print(f"📦 [备份成功] {base_name} 已备份至: {backup_path}")
        return backup_path

    except Exception as e:
        print(f"❌ [备份失败] {filepath} 备份出错: {str(e)}")
        return None
