"""
权限管理模块
处理用户权限检查和角色权限验证
"""
import json
from flask import session
from backend.database import DatabaseManager

class PermissionManager:
    """权限管理器"""
    
    @staticmethod
    def get_user_permissions():
        """获取当前用户的权限"""
        if 'admin_user_id' not in session:
            return {}
        
        user_id = session['admin_user_id']
        role_id = session.get('user_role_id')
        is_admin = session.get('is_admin', False)
        
        # 如果是超级管理员，拥有所有权限
        if is_admin and session.get('admin_username') == 'admin':
            return {
                'menus': {
                    'patterns': True,
                    'products': True,
                    'categories': True,
                    'access_codes': True,
                    'access_logs': True,
                    'users': True,
                    'roles': True,
                    'theme_backgrounds': True,
                    'product_archives': True,
                    'settings': True
                },
                'actions': {
                    'create': True,
                    'edit': True,
                    'delete': True,
                    'export': True,
                    'import': True
                }
            }
        
        # 根据角色获取权限
        if role_id:
            role = DatabaseManager.get_role_by_id(role_id)
            if role and role['permissions']:
                try:
                    return json.loads(role['permissions'])
                except:
                    pass
        
        # 默认无权限
        return {
            'menus': {},
            'actions': {}
        }
    
    @staticmethod
    def has_menu_permission(menu_name):
        """检查是否有菜单权限"""
        permissions = PermissionManager.get_user_permissions()
        return permissions.get('menus', {}).get(menu_name, False)
    
    @staticmethod
    def has_action_permission(action_name):
        """检查是否有操作权限"""
        permissions = PermissionManager.get_user_permissions()
        return permissions.get('actions', {}).get(action_name, False)
    
    @staticmethod
    def get_accessible_menus():
        """获取用户可访问的菜单列表"""
        permissions = PermissionManager.get_user_permissions()
        menus = permissions.get('menus', {})
        return [menu for menu, allowed in menus.items() if allowed]
    
    @staticmethod
    def get_allowed_actions():
        """获取用户允许的操作列表"""
        permissions = PermissionManager.get_user_permissions()
        actions = permissions.get('actions', {})
        return [action for action, allowed in actions.items() if allowed]