"""
用户认证和权限管理模块
处理用户登录、权限验证和会话管理
"""
import hashlib
import secrets
import json
from datetime import datetime, timedelta
from functools import wraps
from flask import session, request, jsonify, redirect, url_for
from .database import DatabaseManager

class AuthManager:
    """认证管理器"""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """密码哈希"""
        salt = secrets.token_hex(16)
        password_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        return f"{salt}:{password_hash.hex()}"
    
    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        """验证密码"""
        try:
            salt, stored_hash = password_hash.split(':')
            password_hash_check = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
            return stored_hash == password_hash_check.hex()
        except:
            return False
    
    @staticmethod
    def create_user(username: str, password: str, is_admin: bool = False, permissions: dict = None) -> int:
        """创建用户"""
        if permissions is None:
            permissions = {}
        
        password_hash = AuthManager.hash_password(password)
        permissions_json = json.dumps(permissions)
        
        query = '''
            INSERT INTO users (username, password_hash, is_admin, permissions)
            VALUES (?, ?, ?, ?)
        '''
        return DatabaseManager.execute_insert(query, (username, password_hash, is_admin, permissions_json))
    
    @staticmethod
    def authenticate_user(username: str, password: str) -> dict:
        """用户认证"""
        query = "SELECT * FROM users WHERE username = ? AND is_active = 1"
        users = DatabaseManager.execute_query(query, (username,))
        
        if not users:
            return None
        
        user = users[0]
        if AuthManager.verify_password(password, user['password_hash']):
            # 更新最后登录时间
            update_query = "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?"
            DatabaseManager.execute_update(update_query, (user['id'],))
            
            return {
                'id': user['id'],
                'username': user['username'],
                'is_admin': user['is_admin'],
                'permissions': json.loads(user['permissions']) if user['permissions'] else {}
            }
        
        return None
    
    @staticmethod
    def get_user_by_id(user_id: int) -> dict:
        """根据ID获取用户信息"""
        query = "SELECT * FROM users WHERE id = ? AND is_active = 1"
        users = DatabaseManager.execute_query(query, (user_id,))
        
        if users:
            user = users[0]
            return {
                'id': user['id'],
                'username': user['username'],
                'is_admin': user['is_admin'],
                'permissions': json.loads(user['permissions']) if user['permissions'] else {}
            }
        
        return None
    
    @staticmethod
    def update_user_permissions(user_id: int, permissions: dict) -> int:
        """更新用户权限"""
        permissions_json = json.dumps(permissions)
        query = "UPDATE users SET permissions = ? WHERE id = ?"
        return DatabaseManager.execute_update(query, (permissions_json, user_id))
    
    @staticmethod
    def get_all_users() -> list:
        """获取所有用户列表"""
        query = '''
            SELECT id, username, is_admin, permissions, created_time, last_login, is_active
            FROM users ORDER BY created_time DESC
        '''
        users = DatabaseManager.execute_query(query)
        
        for user in users:
            user['permissions'] = json.loads(user['permissions']) if user['permissions'] else {}
        
        return users

class AccessCodeManager:
    """访问授权码管理器"""
    
    @staticmethod
    def generate_access_code(length: int = 8) -> str:
        """生成访问授权码"""
        return secrets.token_urlsafe(length)[:length].upper()
    
    @staticmethod
    def create_access_code(description: str, start_date: datetime, end_date: datetime) -> dict:
        """创建访问授权码"""
        code = AccessCodeManager.generate_access_code()
        
        query = '''
            INSERT INTO access_codes (code, description, start_date, end_date)
            VALUES (?, ?, ?, ?)
        '''
        
        code_id = DatabaseManager.execute_insert(query, (code, description, start_date, end_date))
        
        return {
            'id': code_id,
            'code': code,
            'description': description,
            'start_date': start_date,
            'end_date': end_date
        }
    
    @staticmethod
    def validate_access_code(code: str) -> bool:
        """验证访问授权码"""
        query = '''
            SELECT * FROM access_codes 
            WHERE code = ? AND is_active = 1 
            AND (start_date IS NULL OR start_date <= CURRENT_TIMESTAMP)
            AND (end_date IS NULL OR end_date >= CURRENT_TIMESTAMP)
        '''
        
        codes = DatabaseManager.execute_query(query, (code,))
        
        if codes:
            # 增加使用次数
            update_query = "UPDATE access_codes SET usage_count = usage_count + 1 WHERE code = ?"
            DatabaseManager.execute_update(update_query, (code,))
            return True
        
        return False
    
    @staticmethod
    def get_access_codes() -> list:
        """获取所有访问授权码"""
        query = '''
            SELECT * FROM access_codes 
            ORDER BY created_time DESC
        '''
        return DatabaseManager.execute_query(query)
    
    @staticmethod
    def update_access_code(code_id: int, description: str, start_date: datetime, end_date: datetime) -> int:
        """更新访问授权码"""
        query = '''
            UPDATE access_codes 
            SET description = ?, start_date = ?, end_date = ?
            WHERE id = ?
        '''
        return DatabaseManager.execute_update(query, (description, start_date, end_date, code_id))
    
    @staticmethod
    def delete_access_code(code_id: int) -> int:
        """删除访问授权码"""
        query = "UPDATE access_codes SET is_active = 0 WHERE id = ?"
        return DatabaseManager.execute_update(query, (code_id,))

def login_required(f):
    """登录验证装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': '需要登录'}), 401
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """管理员权限验证装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': '需要登录'}), 401
        
        user = AuthManager.get_user_by_id(session['user_id'])
        if not user or not user['is_admin']:
            return jsonify({'error': '需要管理员权限'}), 403
        
        return f(*args, **kwargs)
    return decorated_function

def permission_required(permission: str):
    """特定权限验证装饰器"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                return jsonify({'error': '需要登录'}), 401
            
            user = AuthManager.get_user_by_id(session['user_id'])
            if not user:
                return jsonify({'error': '用户不存在'}), 401
            
            # 管理员拥有所有权限
            if user['is_admin']:
                return f(*args, **kwargs)
            
            # 检查特定权限
            permissions = user.get('permissions', {})
            if permissions.get('all') or permissions.get(permission):
                return f(*args, **kwargs)
            
            return jsonify({'error': f'需要 {permission} 权限'}), 403
        
        return decorated_function
    return decorator

def access_code_required(f):
    """访问授权码验证装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 检查会话中是否有有效的访问授权码
        if 'access_code_validated' in session and session.get('access_code_validated'):
            return f(*args, **kwargs)
        
        # 检查请求中的访问授权码
        access_code = request.args.get('access_code') or request.form.get('access_code')
        
        if access_code and AccessCodeManager.validate_access_code(access_code):
            session['access_code_validated'] = True
            session['access_code'] = access_code
            return f(*args, **kwargs)
        
        return jsonify({
            'success': False,
            'error': '需要有效的访问授权码',
            'message': '请先通过授权码验证'
        }), 403
    
    return decorated_function

def init_auth(app):
    """初始化认证系统"""
    app.secret_key = app.config.get('SECRET_KEY', 'your-secret-key-change-in-production')
    
    # 创建默认管理员账户（如果不存在）
    try:
        query = "SELECT COUNT(*) as count FROM users WHERE username = 'admin'"
        result = DatabaseManager.execute_query(query)
        
        if result[0]['count'] == 0:
            # 创建默认管理员账户，密码为 admin123
            AuthManager.create_user(
                username='admin',
                password='admin123',
                is_admin=True,
                permissions={'all': True}
            )
            print("默认管理员账户已创建: admin / admin123")
    
    except Exception as e:
        print(f"初始化认证系统时出错: {e}")

# 权限配置
PERMISSIONS = {
    'pattern_manage': '印花图案管理',
    'product_manage': '产品管理',
    'category_manage': '分类管理',
    'access_code_manage': '授权码管理',
    'user_manage': '用户管理',
    'theme_manage': '主题管理'
}

def get_permission_list():
    """获取权限列表"""
    return PERMISSIONS