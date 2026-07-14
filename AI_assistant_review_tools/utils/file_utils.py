"""文件操作工具：配置和会话管理"""
import json
import pickle
import os
import time
import configparser
from tkinter import messagebox


class ConfigManager:
    """配置管理器"""
    
    @staticmethod
    def get_default_config():
        """获取默认配置"""
        return {
            'llm_tldr_soft_limit': 300,
            'llm_tldr_hard_limit': 500,
            'llm_search_hard_limit': 3000,
            'llm_search_soft_limit': 1500,
            'abstract_translation_limit': 2500,
            'online_translation_limit': 500,
            'max_cache_size': 500,
            'llm_include_tldr_abstract': False,
            'llm_relevance_threshold': 0.4,
            'llm_search_tldr_abstract_hard_limit': 1000,
            'llm_search_tldr_abstract_soft_limit': 500,
            'preliminary_threshold_ratio': 0.6,
            'last_session_path': '',
            'ui_layout': {
                'pane_position': 400,
                'window_width': 1400,
                'window_height': 900
            },
            'translation_services': ['mymemory', 'google', 'baidu', 'youdao', 'libre', 'tencent'],
            'translation_service_params': {
                'mymemory': {
                    'email': '2182712226@qq.com',
                    'key': 'f23aa66e19b601cff7cf'
                },
                'baidu': {
                    'appid': '',
                    'key': ''
                },
                'youdao': {
                    'appKey': '',
                    'key': ''
                },
                'tencent': {
                    'secretId': '',
                    'secretKey': ''
                }
            }
        }
    
    @staticmethod
    def load_config(config_file_path="config.ini"):
        """加载配置文件（优先使用 config.ini）"""
        default_config = ConfigManager.get_default_config()
        
        # 确保默认目录存在
        base_dir = os.path.dirname(os.path.abspath(__file__))
        if not os.path.exists("./saves"):
            os.makedirs("./saves", exist_ok=True)
        if not os.path.exists("./sources"):
            os.makedirs("./sources", exist_ok=True)

        # 优先尝试加载 config.ini
        ini_file_path = "config.ini"
        try:
            if os.path.exists(ini_file_path):
                config = ConfigManager.load_config_from_ini(ini_file_path, default_config)
                return config
        except Exception as e:
            print(f"加载 config.ini 失败: {e}，尝试加载 config.json")
        
        # 如果 config.ini 不存在或加载失败，尝试从 config.json 加载（向后兼容）
        json_file_path = config_file_path if config_file_path.endswith('.json') else "config.json"
        try:
            if os.path.exists(json_file_path):
                with open(json_file_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    # 确保所有必要的配置项都存在
                    for key, value in default_config.items():
                        if key not in config:
                            config[key] = value
                    return config
        except Exception as e:
            print(f"加载 config.json 失败: {e}")
        
        return default_config
    
    @staticmethod
    def load_config_from_ini(ini_file_path, default_config):
        """从 INI 文件加载配置"""
        config_parser = configparser.ConfigParser()
        config_parser.read(ini_file_path, encoding='utf-8')
        
        config = default_config.copy()
        
        # 加载 LLM 配置
        if config_parser.has_section('LLM'):
            config['llm_tldr_soft_limit'] = config_parser.getint('LLM', 'llm_tldr_soft_limit', fallback=default_config['llm_tldr_soft_limit'])
            config['llm_tldr_hard_limit'] = config_parser.getint('LLM', 'llm_tldr_hard_limit', fallback=default_config['llm_tldr_hard_limit'])
            config['llm_search_hard_limit'] = config_parser.getint('LLM', 'llm_search_hard_limit', fallback=default_config['llm_search_hard_limit'])
            config['llm_search_soft_limit'] = config_parser.getint('LLM', 'llm_search_soft_limit', fallback=default_config['llm_search_soft_limit'])
            config['llm_search_tldr_abstract_hard_limit'] = config_parser.getint('LLM', 'llm_search_tldr_abstract_hard_limit', fallback=default_config['llm_search_tldr_abstract_hard_limit'])
            config['llm_search_tldr_abstract_soft_limit'] = config_parser.getint('LLM', 'llm_search_tldr_abstract_soft_limit', fallback=default_config['llm_search_tldr_abstract_soft_limit'])
            config['llm_relevance_threshold'] = config_parser.getfloat('LLM', 'llm_relevance_threshold', fallback=default_config['llm_relevance_threshold'])
            config['llm_include_tldr_abstract'] = config_parser.getboolean('LLM', 'llm_include_tldr_abstract', fallback=default_config['llm_include_tldr_abstract'])
        
        # 加载翻译配置
        if config_parser.has_section('Translation'):
            config['abstract_translation_limit'] = config_parser.getint('Translation', 'abstract_translation_limit', fallback=default_config['abstract_translation_limit'])
            config['online_translation_limit'] = config_parser.getint('Translation', 'online_translation_limit', fallback=default_config['online_translation_limit'])
            
            # 解析翻译服务列表
            services_str = config_parser.get('Translation', 'translation_services', fallback='')
            config['translation_services'] = [s.strip() for s in services_str.split(',')] if services_str else default_config['translation_services']
        
        # 加载翻译服务参数
        config['translation_service_params'] = default_config['translation_service_params'].copy()
        
        if config_parser.has_section('Translation.MyMemory'):
            config['translation_service_params']['mymemory'] = {
                'email': config_parser.get('Translation.MyMemory', 'email', fallback=''),
                'key': config_parser.get('Translation.MyMemory', 'key', fallback='')
            }
        
        if config_parser.has_section('Translation.Baidu'):
            config['translation_service_params']['baidu'] = {
                'appid': config_parser.get('Translation.Baidu', 'appid', fallback=''),
                'key': config_parser.get('Translation.Baidu', 'key', fallback='')
            }
        
        if config_parser.has_section('Translation.Youdao'):
            config['translation_service_params']['youdao'] = {
                'appKey': config_parser.get('Translation.Youdao', 'appKey', fallback=''),
                'key': config_parser.get('Translation.Youdao', 'key', fallback='')
            }
        
        if config_parser.has_section('Translation.Tencent'):
            config['translation_service_params']['tencent'] = {
                'secretId': config_parser.get('Translation.Tencent', 'secretId', fallback=''),
                'secretKey': config_parser.get('Translation.Tencent', 'secretKey', fallback='')
            }
        
        # 加载缓存配置
        if config_parser.has_section('Cache'):
            config['max_cache_size'] = config_parser.getint('Cache', 'max_cache_size', fallback=default_config['max_cache_size'])
        
        # 加载搜索配置
        if config_parser.has_section('Search'):
            config['preliminary_threshold_ratio'] = config_parser.getfloat('Search', 'preliminary_threshold_ratio', fallback=default_config['preliminary_threshold_ratio'])
        
        # 加载会话配置
        if config_parser.has_section('Session'):
            config['last_session_path'] = config_parser.get('Session', 'last_session_path', fallback='')
        
        # 加载 UI 配置
        ui_layout = default_config['ui_layout'].copy()
        if config_parser.has_section('UI'):
            ui_layout['pane_position'] = config_parser.getint('UI', 'pane_position', fallback=default_config['ui_layout']['pane_position'])
            ui_layout['window_width'] = config_parser.getint('UI', 'window_width', fallback=default_config['ui_layout']['window_width'])
            ui_layout['window_height'] = config_parser.getint('UI', 'window_height', fallback=default_config['ui_layout']['window_height'])
        config['ui_layout'] = ui_layout
        
        return config
    
    @staticmethod
    def save_config(config, config_file_path="config.ini", max_retries=3):
        """保存配置文件到 INI 格式"""
        retry_delay = 1
        
        for attempt in range(max_retries):
            try:
                # 保存为 INI 格式
                config_parser = configparser.ConfigParser()
                
                # LLM 配置
                config_parser['LLM'] = {
                    'llm_tldr_soft_limit': str(config.get('llm_tldr_soft_limit', 300)),
                    'llm_tldr_hard_limit': str(config.get('llm_tldr_hard_limit', 500)),
                    'llm_search_hard_limit': str(config.get('llm_search_hard_limit', 3000)),
                    'llm_search_soft_limit': str(config.get('llm_search_soft_limit', 1500)),
                    'llm_search_tldr_abstract_hard_limit': str(config.get('llm_search_tldr_abstract_hard_limit', 1000)),
                    'llm_search_tldr_abstract_soft_limit': str(config.get('llm_search_tldr_abstract_soft_limit', 500)),
                    'llm_relevance_threshold': str(config.get('llm_relevance_threshold', 0.4)),
                    'llm_include_tldr_abstract': str(config.get('llm_include_tldr_abstract', False))
                }
                
                # 翻译配置
                config_parser['Translation'] = {
                    'abstract_translation_limit': str(config.get('abstract_translation_limit', 2500)),
                    'online_translation_limit': str(config.get('online_translation_limit', 500)),
                    'translation_services': ', '.join(config.get('translation_services', ['mymemory', 'google']))
                }
                
                # 翻译服务参数
                translation_params = config.get('translation_service_params', {})
                if 'mymemory' in translation_params:
                    config_parser['Translation.MyMemory'] = translation_params['mymemory']
                if 'baidu' in translation_params:
                    config_parser['Translation.Baidu'] = translation_params['baidu']
                if 'youdao' in translation_params:
                    config_parser['Translation.Youdao'] = translation_params['youdao']
                if 'tencent' in translation_params:
                    config_parser['Translation.Tencent'] = translation_params['tencent']
                
                # 缓存配置
                config_parser['Cache'] = {
                    'max_cache_size': str(config.get('max_cache_size', 500))
                }
                
                # 搜索配置
                config_parser['Search'] = {
                    'preliminary_threshold_ratio': str(config.get('preliminary_threshold_ratio', 0.6))
                }
                
                # 会话配置
                config_parser['Session'] = {
                    'last_session_path': config.get('last_session_path', '')
                }
                
                # UI 配置
                ui_layout = config.get('ui_layout', {})
                config_parser['UI'] = {
                    'pane_position': str(ui_layout.get('pane_position', 400)),
                    'window_width': str(ui_layout.get('window_width', 1400)),
                    'window_height': str(ui_layout.get('window_height', 900))
                }
                
                with open(config_file_path, 'w', encoding='utf-8') as f:
                    config_parser.write(f)
                return True
            except PermissionError as e:
                print(f"保存配置文件失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                else:
                    break
            except Exception as e:
                print(f"保存配置文件失败: {e}")
                break
        return False

class SessionManager:
    """会话管理器"""
    
    @staticmethod
    def get_default_session():
        """获取默认会话数据"""
        return {
            'adopted_papers': set(),
            'excluded_papers': set(),
            'paper_notes': {},
            'search_state': {
                'search_text': '',
                'keywords_area_text': '',
                'min_rating': 0.0,
                'show_adopted_only': False,
                'show_excluded': False,
                'llm_search_text': '',
                'include_tldr_abstract': False,
                'relevance_threshold': 0.5
            },
            'llm_translate_title': False
        }
    
    @staticmethod
    def load_session(session_file_path):
        """加载会话状态"""
        try:
            with open(session_file_path, 'rb') as f:
                session_data = pickle.load(f)
                
                # 确保所有必要的键都存在
                default_session = SessionManager.get_default_session()
                for key, value in default_session.items():
                    if key not in session_data:
                        session_data[key] = value
                
                # 确保 search_state 中的所有键都存在
                if 'search_state' in session_data:
                    for key, value in default_session['search_state'].items():
                        if key not in session_data['search_state']:
                            session_data['search_state'][key] = value
                
                return session_data
        except FileNotFoundError:
            return SessionManager.get_default_session()
        except Exception as e:
            print(f"加载会话状态失败: {e}，创建新会话")
            return SessionManager.get_default_session()
    
    @staticmethod
    def save_session(session_data, session_file_path, max_retries=3):
        """保存会话状态"""
        retry_delay = 0.5
        
        # 确保保存目录存在
        save_dir = os.path.dirname(session_file_path)
        if save_dir and not os.path.exists(save_dir):
            try:
                os.makedirs(save_dir, exist_ok=True)
            except:
                pass

        for attempt in range(max_retries):
            try:
                with open(session_file_path, 'wb') as f:
                    pickle.dump(session_data, f)
                return True
            except PermissionError as e:
                print(f"保存会话失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
            except Exception as e:
                print(f"保存会话状态失败: {e}")
                break
        return False