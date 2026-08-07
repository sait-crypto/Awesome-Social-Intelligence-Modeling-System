"""
配置文件加载器
"""
import os
import re
import configparser
from typing import Dict, List, Any, Optional
import sys
import json
from pathlib import Path


# 将项目根目录添加到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

# 导入配置文件
from config import tag_config, categories_config


class ConfigLoader:
    """配置加载器，读取所有配置文件"""
    INLINE_COMMENT_PREFIXES = ('//', ';', '#')  # 配置文件注释前缀，为健壮性，除#外，也支持 //和; 作为行注释前缀
    USER_PROMPTS_FILE = 'user_prompts.json'
    DOTENV_FILE = '.env'
    API_KEY_ENV = 'AI_API_KEY'
    API_KEYS_ENV = 'AI_API_KEYS'
    def __init__(self):
        if getattr(sys, 'frozen', False):
            # A packaged entry remains anchored to the repository containing the executable.
            self.project_root = Path(sys.executable).resolve().parent
        else:
            # 以模块位置上溯两级作为项目根（保证以项目根为基准解析所有相对路径）
            # src/core -> src -> root (2 levels up from src, so 3 levels from here)
            self.project_root = Path(__file__).resolve().parents[3]
        # Packaged and Python entry points share the repository configuration.
        self.config_path = (self.project_root / 'engineering' / 'config').resolve()

        # 读取配置（_load_settings 会使用 self.project_root 来解析相对路径）
        self.settings = self._load_settings()
        self.tags_config = self._load_tags_config()
        self.categories_config = self._load_categories_config()

        # 便于其他模块直接使用绝对路径
        self.paths = self.settings.get('paths', {})
        
        # API keys come only from process environment variables or the local .env file.
        self.api_keys = self._load_global_api_keys()
    
    def _load_settings(self) -> Dict[str, Any]:
        """加载config.ini文件，优先加载默认配置，再覆盖用户配置"""
        # 为健壮性，除#外，也支持 //和; 作为注释
        config = configparser.ConfigParser(inline_comment_prefixes=self.INLINE_COMMENT_PREFIXES)
        
        default_path = (self.config_path / 'config_default.ini').resolve()
        user_path = (self.config_path / 'config.ini').resolve()

        # 1. 读取默认配置
        if default_path.exists():
            config.read(str(default_path), encoding='utf-8')

        # 2. 读取用户配置（覆盖默认）
        if user_path.exists():
            config.read(str(user_path), encoding='utf-8')

        settings: Dict[str, Any] = {}
        for section in config.sections():
            settings[section] = dict(config.items(section))

        # 处理 paths：统一使用 self.project_root 作为相对路径基准，并规范化为绝对路径字符串
        if 'paths' in settings:
            paths = settings['paths'] or {}
            normalized: Dict[str, Any] = {}
            # 保证有默认项
            paths.setdefault('update_json', 'submit_template.json')
            
            # 特殊处理 extra_update_file 列表
            extra_files_list = []
            
            for k, v in paths.items():
                if not v:
                    normalized[k] = None
                    continue
                
                # 处理 extra_update_file (逗号分割的列表)
                if k == 'extra_update_file':
                    raw_paths = [p.strip() for p in v.split(',') if p.strip()]
                    for raw_p in raw_paths:
                        p_obj = Path(raw_p)
                        try:
                            if not p_obj.is_absolute():
                                abs_path = str((self.project_root / p_obj).resolve())
                            else:
                                abs_path = str(p_obj.resolve())
                            extra_files_list.append(abs_path)
                        except Exception:
                            extra_files_list.append(str(raw_p))
                    # 保存原始字符串
                    normalized[k] = v
                    continue

                # 处理普通路径
                p = Path(v)
                try:
                    if not p.is_absolute():
                        normalized[k] = str((self.project_root / p).resolve())
                    else:
                        normalized[k] = str(p.resolve())
                except Exception:
                    # 回退到原始字符串（避免抛出）
                    normalized[k] = str(p)
            
            settings['paths'] = normalized
            # 将解析后的额外文件列表单独存入
            settings['paths']['extra_update_files_list'] = extra_files_list

        # 处理 AI 配置的 Profiles JSON 解析
        if 'ai' in settings:
            settings['ai']['profiles'] = self._process_ai_profiles(settings['ai'])

        return settings

    def get_local_env_path(self) -> Path:
        """Return the repository-local dotenv path used by desktop tools."""
        return (self.project_root / self.DOTENV_FILE).resolve()

    def _load_dotenv_values(self) -> Dict[str, str]:
        """Read the local .env without overriding the process environment."""
        env_path = self.get_local_env_path()
        if not env_path.is_file():
            return {}

        values: Dict[str, str] = {}
        try:
            for raw_line in env_path.read_text(encoding='utf-8-sig').splitlines():
                line = raw_line.strip()
                if not line or line.startswith('#'):
                    continue
                if line.startswith('export '):
                    line = line[7:].lstrip()
                if '=' not in line:
                    continue
                name, value = line.split('=', 1)
                name = name.strip()
                if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', name):
                    continue
                value = value.strip()
                if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
                    value = value[1:-1]
                values[name] = value
        except OSError as exc:
            print(f"Unable to read local .env: {exc}")
        return values

    @staticmethod
    def _split_api_keys(raw_value: str) -> List[str]:
        raw_value = raw_value or ''
        if ',' in raw_value:
            # Empty comma-separated slots are significant: profile index N uses key N.
            return [part.strip() for part in raw_value.split(',')]
        return [part.strip() for part in raw_value.splitlines() if part.strip()]

    def _load_global_api_keys(self) -> List[str]:
        """Load API keys exclusively from environment variables or root .env."""
        process_value = (
            os.environ.get(self.API_KEYS_ENV, '').strip()
            or os.environ.get(self.API_KEY_ENV, '').strip()
        )
        if process_value:
            return self._split_api_keys(process_value)

        local_values = self._load_dotenv_values()
        multi_value = str(local_values.get(self.API_KEYS_ENV, '')).strip()
        single_value = str(local_values.get(self.API_KEY_ENV, '')).strip()
        return self._split_api_keys(multi_value or single_value)

    def get_local_api_keys(self) -> List[str]:
        """Return keys stored in root .env, excluding process-only secrets."""
        local_values = self._load_dotenv_values()
        return self._split_api_keys(
            local_values.get(self.API_KEYS_ENV, '') or local_values.get(self.API_KEY_ENV, '')
        )

    def save_local_api_keys(self, keys: List[str]) -> None:
        """Persist the desktop profile key list in the ignored root .env file."""
        env_path = self.get_local_env_path()
        env_path.parent.mkdir(parents=True, exist_ok=True)
        existing_lines = []
        if env_path.is_file():
            existing_lines = env_path.read_text(encoding='utf-8-sig').splitlines()

        replacement = f"{self.API_KEYS_ENV}={','.join(str(key).strip() for key in keys)}"
        output_lines: List[str] = []
        replaced = False
        for line in existing_lines:
            match = re.match(r'^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=', line)
            if match and match.group(1) == self.API_KEYS_ENV:
                if not replaced:
                    output_lines.append(replacement)
                    replaced = True
                continue
            output_lines.append(line)
        if not replaced:
            if output_lines and output_lines[-1].strip():
                output_lines.append('')
            output_lines.append(replacement)

        temporary_path = env_path.with_name(f'{env_path.name}.tmp')
        temporary_path.write_text('\n'.join(output_lines).rstrip() + '\n', encoding='utf-8')
        os.replace(temporary_path, env_path)
        self.api_keys = self._load_global_api_keys()

    @staticmethod
    def _upgrade_deepseek_profile(profile: Dict[str, Any]) -> Dict[str, Any]:
        """Upgrade retired DeepSeek aliases while preserving their old mode."""
        upgraded = dict(profile)
        # Secrets are no longer part of profile/config data.
        upgraded.pop('api_key_source', None)
        if str(upgraded.get('provider', '')).strip().lower() != 'deepseek':
            return upgraded

        legacy_model = str(upgraded.get('model', '')).strip()
        legacy_modes = {
            'deepseek-chat': ('deepseek-v4-pro', 'disabled'),
            'deepseek-reasoner': ('deepseek-v4-flash', 'enabled'),
            'deepseek-coder': ('deepseek-v4-pro', 'disabled'),
        }
        if legacy_model in legacy_modes:
            model, thinking_type = legacy_modes[legacy_model]
            upgraded['model'] = model
            upgraded.setdefault('thinking', {'type': thinking_type})

        if upgraded.get('model') in {'deepseek-v4-pro', 'deepseek-v4-flash'}:
            upgraded.setdefault('thinking', {'type': 'enabled'})
            thinking = upgraded.get('thinking')
            if isinstance(thinking, str):
                upgraded['thinking'] = {'type': thinking}
            upgraded.setdefault('reasoning_effort', 'high')
            upgraded['api_url'] = upgraded.get('api_url') or 'https://api.deepseek.com/v1/chat/completions'
        return upgraded

    def _process_ai_profiles(self, ai_settings: Dict[str, Any]) -> List[Dict]:
        """处理AI Profiles：解析JSON"""
        raw_profiles = ai_settings.get('profiles_json', '[]')
        profiles = []
        try:
            profiles = json.loads(raw_profiles)
        except Exception:
            profiles = []
        
        if not isinstance(profiles, list):
            profiles = []

        # 转换为字典以便去重/查找
        profiles_dict = {
            p.get('name'): self._upgrade_deepseek_profile(p)
            for p in profiles
            if isinstance(p, dict) and 'name' in p
        }

        # 确保有默认
        if not profiles_dict:
            profiles_dict['default_deepseek'] = {
                "name": "default_deepseek",
                "provider": "deepseek",
                "api_url": "https://api.deepseek.com/v1/chat/completions",
                "model": "deepseek-v4-pro",
                "thinking": {"type": "disabled"},
                "reasoning_effort": "high",
            }
        
        return list(profiles_dict.values())

    def resolve_api_key(self, profile_index: int = 0) -> Optional[str]:
        """Resolve a profile key from environment-backed key storage."""
        if self.api_keys:
            if 0 <= profile_index < len(self.api_keys):
                return self.api_keys[profile_index]
            return self.api_keys[0]  # Fallback to the first key for single-secret CI.
        
        return None

    def save_ai_settings(self, enable_ai: bool, active_profile_name: str, profiles_list: List[Dict]):
        """保存 AI 设置到 config.ini"""
        config = configparser.ConfigParser()
        user_path = self.config_path / 'config.ini'
        
        if user_path.exists():
            config.read(str(user_path), encoding='utf-8')
        
        if 'ai' not in config:
            config['ai'] = {}
            
        config['ai']['enable_ai_generation'] = str(enable_ai).lower()
        config['ai']['active_profile'] = active_profile_name
        sanitized_profiles = []
        for profile in profiles_list:
            sanitized = dict(profile)
            sanitized.pop('api_key_source', None)
            sanitized_profiles.append(sanitized)
        config['ai']['profiles_json'] = json.dumps(sanitized_profiles)
        
        # 清理旧字段
        for old_key in ['key_path', 'deepseek_api_key_path', 'api_key_github_secret_name']:
            if old_key in config['ai']:
                del config['ai'][old_key]
        
        with open(user_path, 'w', encoding='utf-8') as f:
            config.write(f)
        
        # 刷新
        self.settings = self._load_settings()
        self.api_keys = self._load_global_api_keys()

    def get_ai_provider_defaults(self, provider: str) -> Dict[str, str]:
        """获取 Provider 的默认值"""
        # (此处由 AIGenerator.get_provider_defaults 实现，保持空实现避免循环)
        return {} 

    def _default_user_prompts_payload(self) -> Dict[str, Any]:
        """默认用户 Prompt 配置。"""
        return {
            'vibe_papers': [],
            'writing_paper_context': '',
            'other_user_prompt': ''
        }

    def get_user_prompts_file_path(self) -> Path:
        """用户 Prompt 配置文件路径。"""
        return (self.config_path / self.USER_PROMPTS_FILE).resolve()

    def load_user_prompts(self) -> Dict[str, Any]:
        """读取用户 Prompt 配置；缺失或损坏时返回默认值。"""
        default_payload = self._default_user_prompts_payload()
        file_path = self.get_user_prompts_file_path()
        if not file_path.exists():
            return dict(default_payload)

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                payload = json.load(f)
        except Exception:
            return dict(default_payload)

        if not isinstance(payload, dict):
            return dict(default_payload)

        vibe_raw = payload.get('vibe_papers', [])
        if isinstance(vibe_raw, list):
            vibe_papers = [str(item).strip() for item in vibe_raw if str(item).strip()]
        else:
            vibe_papers = []

        return {
            'vibe_papers': vibe_papers,
            'writing_paper_context': str(payload.get('writing_paper_context', '') or '').strip(),
            'other_user_prompt': str(payload.get('other_user_prompt', '') or '').strip(),
        }

    def save_user_prompts(self, prompts_payload: Dict[str, Any]) -> None:
        """保存用户 Prompt 配置到 config 目录下 JSON 文件。"""
        payload = self._default_user_prompts_payload()
        payload.update(prompts_payload or {})

        vibe_raw = payload.get('vibe_papers', [])
        if isinstance(vibe_raw, list):
            vibe_papers = [str(item).strip() for item in vibe_raw if str(item).strip()]
        else:
            vibe_papers = []

        normalized = {
            'vibe_papers': vibe_papers,
            'writing_paper_context': str(payload.get('writing_paper_context', '') or '').strip(),
            'other_user_prompt': str(payload.get('other_user_prompt', '') or '').strip(),
        }

        file_path = self.get_user_prompts_file_path()
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(normalized, f, ensure_ascii=False, indent=2)
    
    def _load_tags_config(self) -> Dict[str, Any]:
        """加载标签配置"""
        # 直接从tag_config模块导入配置
        return tag_config.TAGS_CONFIG
    
    def _load_categories_config(self) -> Dict[str, Any]:
        """加载分类配置"""
        # 直接从categories_config模块导入配置
        return categories_config.CATEGORIES_CONFIG
    
    def _localized_record(self, record: Dict[str, Any], language: Optional[str]) -> Dict[str, Any]:
        if not language:
            return record
        language = 'zh' if str(language).lower().startswith('zh') else 'en'
        localized = dict(record)
        for field_name in ('name', 'display_name', 'description'):
            localized_value = record.get(f'{field_name}_{language}')
            if localized_value not in (None, ''):
                localized[field_name] = localized_value
        return localized

    def get_active_tags(self, language: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取所有启用的标签（包括immutable标签）"""
        active_tags = []
        for tag in self.tags_config.get('tags', []):
            if tag.get('immutable', False) or tag.get('enabled', False):
                active_tags.append(self._localized_record(tag, language))
        return active_tags
    
    def get_active_categories(self, language: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取所有启用的分类"""
        # 返回按 order 排序的启用分类。当 order 值重复时，保持配置中出现的原始顺序。
        raw = self.categories_config.get('categories', []) or []
        active_categories = []
        for idx, category in enumerate(raw):
            if category.get('enabled', True):
                # 附加原始索引，便于稳定排序时作为次级键
                cat = self._localized_record(category, language)
                cat['_original_index'] = idx
                active_categories.append(cat)

        # 使用 tuple(key_order, original_index) 进行排序，保证当 order 相同时保持原始出现顺序
        active_categories.sort(key=lambda c: (c.get('order', 0), c.get('_original_index', 0)))

        # 在返回前移除内部使用的临时字段
        for c in active_categories:
            if '_original_index' in c:
                del c['_original_index']

        return active_categories
    
    def get_tag_by_variable(self, variable: str) -> Optional[Dict[str, Any]]:
        """根据变量名获取标签配置"""
        for tag in self.tags_config.get('tags', []):
            if tag.get('variable') == variable:
                return tag
        return None
    def get_tag_field(self, variable: str,field_name:str) -> str:
        """根据变量名和tag域名获取具体tag的具体字段值"""
        for tag in self.tags_config.get('tags', []):
            if tag.get('variable') == variable:
                return tag.get(field_name,"")

        return ''
    
    def get_category_by_unique_name(self, unique_name: str) -> Optional[Dict[str, Any]]:
        """根据唯一标识名获取分类配置"""
        for category in self.categories_config.get('categories', []):
            if category.get('unique_name') == unique_name:
                return category
        return None
    
    def get_categories_change_list(self) -> List[Dict[str, str]]:
        """获取分类变更列表"""
        return self.categories_config.get('categories_change_list', [])
    
    def get_category_by_name_or_unique_name(self, identifier: str) -> Optional[Dict[str, Any]]:
        """根据 unique_name 或 name 获取分类配置 (忽略大小写)"""
        if not identifier: return None
        identifier_lower = identifier.lower()
        
        # 首先按 unique_name 匹配
        for category in self.categories_config.get('categories', []):
            if category.get('unique_name', '').lower() == identifier_lower:
                return category
        
        # 如果按 unique_name 未找到，则按 name 匹配
        for category in self.categories_config.get('categories', []):
            if category.get('name', '').lower() == identifier_lower:
                return category
        
        return None
    
    def get_category_field(self, unique_name: str,field_name:str) -> str:
        """根据唯一标识名和category域名获取具体category的具体字段值"""
        for category in self.categories_config.get('categories', []):
            if category.get('unique_name') == unique_name:
                return category.get(field_name,"")

        return ''
    def get_required_tags(self) -> List[Dict[str, Any]]:
        """获取所有必填标签"""
        required_tags = []
        for tag in self.get_active_tags():
            if tag.get('required', False):
                required_tags.append(tag)
        return required_tags
    
    def get_non_system_tags(self) -> List[Dict[str, Any]]:
        """获取所有非系统字段标签（system_var=False）,不包括禁用的tag！"""
        non_system_tags = []
        for tag in self.get_active_tags():
            # 从配置中读取system_var字段，默认为False
            if not tag.get('system_var', False):
                non_system_tags.append(tag)
        return non_system_tags
    def get_system_tags(self) -> List[Dict[str, Any]]:
        """获取所有系统字段标签（system_var=True）"""
        system_tags = []
        for tag in self.get_active_tags():
            # 从配置中读取system_var字段，默认为False
            if tag.get('system_var', False):
                system_tags.append(tag)
        return system_tags
    
    def validate_value(self, tag: Dict[str, Any], value: Any) -> bool:
        """验证值是否符合标签的验证规则"""
        if value is None or value == "":
            return not tag.get('required', False)
        
        validation_pattern = tag.get('validation')
        
        try:
            t = tag.get('type')
            if t == 'string':
                if validation_pattern:
                    return bool(re.match(validation_pattern, str(value)))
                return True
            elif t == 'bool':
                return str(value).lower() in ['true', 'false', 'yes', 'no', '1', '0']
            elif t == 'enum':
                return True
            else:
                return True
        except Exception:
            return False


# 创建全局配置加载器单例
_config_instance = None
def get_config_instance():
    """获取全局配置加载器单例"""
    global _config_instance
    _config_instance = ConfigLoader() if _config_instance is None else _config_instance
    return _config_instance
