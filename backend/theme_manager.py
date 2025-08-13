"""
主题管理模块
负责主题的切换、管理和配置
"""
import os
import json
from typing import Dict, List, Optional
from .database import DatabaseManager

class ThemeManager:
    """主题管理器"""
    
    def __init__(self):
        self.themes_dir = 'static/themes'
        self.default_theme = 'default'
        
        # 预定义主题配置
        self.theme_configs = {
            'default': {
                'name': '默认主题',
                'description': '简洁现代的默认主题，适合各种场景',
                'css_file': 'default.css',
                'preview_image': 'default_preview.jpg',
                'primary_color': '#1976D2',
                'secondary_color': '#424242',
                'accent_color': '#FF9800',
                'decorations': ['⚡', '🎨', '✨'],
                'season': 'all'
            },
            'christmas': {
                'name': '圣诞主题',
                'description': '红绿配色的圣诞节主题，营造温馨节日氛围',
                'css_file': 'christmas.css',
                'preview_image': 'christmas_preview.jpg',
                'primary_color': '#C62828',
                'secondary_color': '#2E7D32',
                'accent_color': '#FFD700',
                'decorations': ['🎄', '🔔', '⭐'],
                'season': 'winter'
            },
            'easter': {
                'name': '复活节主题',
                'description': '紫橙配色的复活节主题，展现春天活力',
                'css_file': 'easter.css',
                'preview_image': 'easter_preview.jpg',
                'primary_color': '#7B1FA2',
                'secondary_color': '#388E3C',
                'accent_color': '#FF6F00',
                'decorations': ['🐰', '🥚', '🌸'],
                'season': 'spring'
            }
        }
    
    def get_available_themes(self) -> List[Dict]:
        """获取可用主题列表"""
        themes = []
        for theme_id, config in self.theme_configs.items():
            css_path = os.path.join(self.themes_dir, config['css_file'])
            if os.path.exists(css_path):
                theme_info = {
                    'id': theme_id,
                    'name': config['name'],
                    'description': config['description'],
                    'css_file': config['css_file'],
                    'primary_color': config['primary_color'],
                    'secondary_color': config['secondary_color'],
                    'accent_color': config['accent_color'],
                    'decorations': config['decorations'],
                    'season': config['season'],
                    'is_active': self.is_theme_active(theme_id)
                }
                themes.append(theme_info)
        return themes
    
    def get_current_theme(self) -> Optional[str]:
        """获取当前激活的主题"""
        try:
            result = DatabaseManager.execute_query(
                "SELECT name FROM theme_templates WHERE is_default = 1 AND is_active = 1 LIMIT 1"
            )
            if result:
                return result[0]['name']
            return self.default_theme
        except Exception:
            return self.default_theme
    
    def set_active_theme(self, theme_id: str) -> bool:
        """设置激活主题"""
        if theme_id not in self.theme_configs:
            return False
        
        try:
            # 先取消所有主题的默认状态
            DatabaseManager.execute_update("UPDATE theme_templates SET is_default = 0")
            
            # 检查主题是否已存在
            existing = DatabaseManager.execute_query(
                "SELECT id FROM theme_templates WHERE name = ?", (theme_id,)
            )
            
            if existing:
                # 更新现有主题为默认主题
                DatabaseManager.execute_update(
                    "UPDATE theme_templates SET is_default = 1 WHERE name = ?", 
                    (theme_id,)
                )
            else:
                # 插入新主题记录
                config = self.theme_configs[theme_id]
                DatabaseManager.execute_update(
                    """INSERT INTO theme_templates (name, display_name, css_file, primary_color, secondary_color, is_default, is_active) 
                       VALUES (?, ?, ?, ?, ?, 1, 1)""",
                    (theme_id, config['name'], config['css_file'], config['primary_color'], config['secondary_color'])
                )
            
            return True
        except Exception as e:
            print(f"设置主题失败: {e}")
            return False
    
    def is_theme_active(self, theme_id: str) -> bool:
        """检查主题是否激活"""
        try:
            result = DatabaseManager.execute_query(
                "SELECT is_default FROM theme_templates WHERE name = ?", (theme_id,)
            )
            return result and result[0]['is_default'] == 1
        except Exception:
            return theme_id == self.default_theme
    
    def get_theme_css_path(self, theme_id: str = None) -> str:
        """获取主题CSS文件路径"""
        if not theme_id:
            theme_id = self.get_current_theme()
        
        if theme_id in self.theme_configs:
            return f"/static/themes/{self.theme_configs[theme_id]['css_file']}"
        
        return f"/static/themes/{self.theme_configs[self.default_theme]['css_file']}"
    
    def get_theme_config(self, theme_id: str = None) -> Dict:
        """获取主题配置"""
        if not theme_id:
            theme_id = self.get_current_theme()
        
        return self.theme_configs.get(theme_id, self.theme_configs[self.default_theme])
    
    def create_custom_theme(self, theme_id: str, name: str, css_content: str, config: Dict) -> bool:
        """创建自定义主题"""
        try:
            # 保存CSS文件
            css_filename = f"{theme_id}.css"
            css_path = os.path.join(self.themes_dir, css_filename)
            
            os.makedirs(self.themes_dir, exist_ok=True)
            with open(css_path, 'w', encoding='utf-8') as f:
                f.write(css_content)
            
            # 保存主题配置
            self.theme_configs[theme_id] = {
                'name': name,
                'css_file': css_filename,
                'is_custom': True,
                **config
            }
            
            # 保存到数据库
            DatabaseManager.execute_update(
                """INSERT OR REPLACE INTO theme_templates (name, display_name, css_file, primary_color, secondary_color, is_default, is_active) 
                   VALUES (?, ?, ?, ?, ?, 0, 1)""",
                (theme_id, name, css_filename, config.get('primary_color', '#1976D2'), config.get('secondary_color', '#424242'))
            )
            
            return True
        except Exception as e:
            print(f"创建自定义主题失败: {e}")
            return False
    
    def delete_custom_theme(self, theme_id: str) -> bool:
        """删除自定义主题"""
        if theme_id in ['christmas', 'easter', 'default']:  # 不能删除预设主题
            return False
        
        try:
            # 删除CSS文件
            if theme_id in self.theme_configs:
                css_file = self.theme_configs[theme_id]['css_file']
                css_path = os.path.join(self.themes_dir, css_file)
                if os.path.exists(css_path):
                    os.remove(css_path)
                
                # 从配置中移除
                del self.theme_configs[theme_id]
            
            # 从数据库中删除
            DatabaseManager.execute_update(
                "DELETE FROM theme_templates WHERE name = ?", (theme_id,)
            )
            
            # 如果删除的是当前激活主题，切换到默认主题
            if self.get_current_theme() == theme_id:
                self.set_active_theme(self.default_theme)
            
            return True
        except Exception as e:
            print(f"删除自定义主题失败: {e}")
            return False
    
    def export_theme(self, theme_id: str) -> Optional[Dict]:
        """导出主题配置"""
        if theme_id not in self.theme_configs:
            return None
        
        try:
            config = self.theme_configs[theme_id].copy()
            css_path = os.path.join(self.themes_dir, config['css_file'])
            
            if os.path.exists(css_path):
                with open(css_path, 'r', encoding='utf-8') as f:
                    config['css_content'] = f.read()
            
            return {
                'theme_id': theme_id,
                'export_time': DatabaseManager.get_current_time(),
                'config': config
            }
        except Exception as e:
            print(f"导出主题失败: {e}")
            return None
    
    def import_theme(self, theme_data: Dict) -> bool:
        """导入主题配置"""
        try:
            theme_id = theme_data['theme_id']
            config = theme_data['config']
            css_content = config.pop('css_content', '')
            
            return self.create_custom_theme(theme_id, config['name'], css_content, config)
        except Exception as e:
            print(f"导入主题失败: {e}")
            return False

# 全局主题管理器实例
theme_manager = ThemeManager()