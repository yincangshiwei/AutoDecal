"""
管理员方法扩展
包含授权码管理和用户管理的具体实现
"""
import os
import secrets
import string
from datetime import datetime
from .database import DatabaseManager
from .auth import AuthManager

class AdminMethodsExtension:
    """管理员方法扩展类"""
    
    def __init__(self, admin_instance):
        self.admin = admin_instance
    
    # 授权码管理方法
    def get_access_codes_list(self):
        """获取授权码列表"""
        if not self.admin.check_permission('access_code_manage'):
            return "权限不足"
        
        codes = DatabaseManager.execute_query("""
            SELECT id, code, description, start_date, end_date, is_active, created_time, usage_count
            FROM access_codes ORDER BY created_time DESC
        """)
        
        if not codes:
            return "暂无授权码"
        
        result = "授权码列表:\n"
        for code in codes:
            status = "有效" if code['is_active'] else "已禁用"
            start_date = code['start_date'] or "无限制"
            end_date = code['end_date'] or "无限制"
            result += f"ID: {code['id']}, 授权码: {code['code']}, 描述: {code['description']}\n"
            result += f"  有效期: {start_date} ~ {end_date}, 使用次数: {code['usage_count']}, 状态: {status}\n\n"
        
        return result
    
    def create_access_code(self, description: str, start_date: str, end_date: str):
        """创建授权码"""
        if not self.admin.check_permission('access_code_manage'):
            return "权限不足"
        
        if not description:
            return "请填写授权码描述"
        
        try:
            # 生成随机授权码
            code = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(12))
            
            # 处理日期
            start_dt = None
            end_dt = None
            
            if start_date:
                start_dt = datetime.strptime(start_date, '%Y-%m-%d %H:%M:%S')
            if end_date:
                end_dt = datetime.strptime(end_date, '%Y-%m-%d %H:%M:%S')
            
            # 插入数据库
            query = """
                INSERT INTO access_codes (code, description, start_date, end_date, created_time)
                VALUES (?, ?, ?, ?, ?)
            """
            code_id = DatabaseManager.execute_insert(query, (
                code, description, start_dt, end_dt, datetime.now()
            ))
            
            return f"授权码创建成功！\n授权码: {code}\nID: {code_id}"
        
        except ValueError as e:
            return f"日期格式错误，请使用 YYYY-MM-DD HH:MM:SS 格式"
        except Exception as e:
            return f"创建失败: {str(e)}"
    
    def update_access_code(self, code_id: int, description: str, start_date: str, end_date: str):
        """更新授权码"""
        if not self.admin.check_permission('access_code_manage'):
            return "权限不足"
        
        if not code_id:
            return "请输入授权码ID"
        
        try:
            # 处理日期
            start_dt = None
            end_dt = None
            
            if start_date:
                start_dt = datetime.strptime(start_date, '%Y-%m-%d %H:%M:%S')
            if end_date:
                end_dt = datetime.strptime(end_date, '%Y-%m-%d %H:%M:%S')
            
            # 更新数据库
            query = """
                UPDATE access_codes 
                SET description = ?, start_date = ?, end_date = ?
                WHERE id = ?
            """
            result = DatabaseManager.execute_update(query, (description, start_dt, end_dt, code_id))
            
            if result > 0:
                return f"授权码更新成功！"
            else:
                return "授权码不存在"
        
        except ValueError as e:
            return f"日期格式错误，请使用 YYYY-MM-DD HH:MM:SS 格式"
        except Exception as e:
            return f"更新失败: {str(e)}"
    
    def delete_access_code(self, code_id: int):
        """删除授权码"""
        if not self.admin.check_permission('access_code_manage'):
            return "权限不足"
        
        if not code_id:
            return "请输入授权码ID"
        
        try:
            result = DatabaseManager.execute_update("UPDATE access_codes SET is_active = 0 WHERE id = ?", (code_id,))
            if result > 0:
                return f"授权码删除成功！"
            else:
                return "授权码不存在"
        except Exception as e:
            return f"删除失败: {str(e)}"
    
    # 用户管理方法
    def get_users_list(self):
        """获取用户列表"""
        if not self.admin.check_permission('user_manage'):
            return "权限不足"
        
        users = DatabaseManager.execute_query("""
            SELECT id, username, is_admin, permissions, created_time
            FROM users ORDER BY created_time DESC
        """)
        
        if not users:
            return "暂无用户"
        
        result = "用户列表:\n"
        for user in users:
            role = "超级管理员" if user['is_admin'] else "普通用户"
            permissions = user['permissions'] or "无特殊权限"
            result += f"ID: {user['id']}, 用户名: {user['username']}, 角色: {role}\n"
            result += f"  权限: {permissions}, 创建时间: {user['created_time']}\n\n"
        
        return result
    
    def create_user(self, username: str, password: str, is_admin: bool = False):
        """创建用户"""
        if not self.admin.check_permission('user_manage'):
            return "权限不足"
        
        if not username or not password:
            return "请填写用户名和密码"
        
        try:
            # 检查用户名是否已存在
            existing = DatabaseManager.execute_query("SELECT id FROM users WHERE username = ?", (username,))
            if existing:
                return "用户名已存在"
            
            # 创建用户
            user_id = AuthManager.create_user(username, password, is_admin)
            role = "超级管理员" if is_admin else "普通用户"
            
            return f"用户创建成功！\n用户名: {username}\n角色: {role}\nID: {user_id}"
        
        except Exception as e:
            return f"创建失败: {str(e)}"
    
    def update_user_permissions(self, user_id: int, pattern_manage: bool, product_manage: bool, 
                               category_manage: bool, access_code_manage: bool, 
                               user_manage: bool, theme_manage: bool):
        """更新用户权限"""
        if not self.admin.check_permission('user_manage'):
            return "权限不足"
        
        if not user_id:
            return "请输入用户ID"
        
        try:
            # 构建权限字符串
            permissions = []
            if pattern_manage:
                permissions.append('pattern_manage')
            if product_manage:
                permissions.append('product_manage')
            if category_manage:
                permissions.append('category_manage')
            if access_code_manage:
                permissions.append('access_code_manage')
            if user_manage:
                permissions.append('user_manage')
            if theme_manage:
                permissions.append('theme_manage')
            
            permissions_str = ','.join(permissions)
            
            # 更新数据库
            result = DatabaseManager.execute_update(
                "UPDATE users SET permissions = ? WHERE id = ?", 
                (permissions_str, user_id)
            )
            
            if result > 0:
                return f"用户权限更新成功！\n权限: {permissions_str or '无特殊权限'}"
            else:
                return "用户不存在"
        
        except Exception as e:
            return f"更新失败: {str(e)}"