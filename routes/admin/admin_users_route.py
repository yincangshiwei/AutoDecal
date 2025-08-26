from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from datetime import datetime
from backend.database import DatabaseManager
from backend.auth import AuthManager

users_bp = Blueprint('admin_users', __name__, url_prefix='/admin/users')

def admin_required(f):
    def decorated_function(*args, **kwargs):
        from flask import session
        if 'admin_user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

@users_bp.route('/')
@admin_required
def users():
    """用户管理页面"""
    try:
        # 获取用户列表（包含角色信息）
        users = DatabaseManager.get_users_with_roles()
        # 获取所有角色列表
        roles = DatabaseManager.get_roles()
    except Exception as e:
        print(f"获取用户数据失败: {e}")
        users = []
        roles = []
    return render_template('admin/users.html', users=users, roles=roles)

@users_bp.route('/add', methods=['POST'])
@admin_required
def add_user():
    """添加用户"""
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        role_id = data.get('role_id')
        
        if not username or not password:
            return jsonify({'success': False, 'message': '请填写完整的用户信息'})
        
        # 检查用户名是否已存在
        existing_user = DatabaseManager.get_user_by_username(username)
        if existing_user:
            return jsonify({'success': False, 'message': '用户名已存在'})
        
        # 加密密码
        password_hash = AuthManager.hash_password(password)
        
        # 检查是否为管理员角色
        is_admin = 0
        if role_id:
            role = DatabaseManager.get_role_by_id(role_id)
            if role and role['name'] == '管理员':
                is_admin = 1
        
        query = '''
            INSERT INTO users (username, password_hash, role_id, is_admin, is_active, created_time)
            VALUES (?, ?, ?, ?, 1, ?)
        '''
        user_id = DatabaseManager.execute_insert(query, (
            username, password_hash, role_id, is_admin, datetime.now()
        ))
        
        return jsonify({
            'success': True,
            'message': f'用户"{username}"添加成功！',
            'user_id': user_id
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'添加失败: {str(e)}'})

@users_bp.route('/get')
@admin_required
def get_user():
    """获取单个用户信息"""
    try:
        user_id = request.args.get('id', type=int)
        if not user_id:
            return jsonify({'success': False, 'message': '缺少用户ID'})
        
        query = "SELECT * FROM users WHERE id = ?"
        results = DatabaseManager.execute_query(query, (user_id,))
        
        if results:
            user = dict(results[0])
            # 不返回密码哈希
            user.pop('password_hash', None)
            return jsonify({'success': True, 'data': user})
        else:
            return jsonify({'success': False, 'message': '用户不存在'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'获取失败: {str(e)}'})

@users_bp.route('/update', methods=['POST'])
@admin_required
def update_user():
    """更新用户"""
    try:
        data = request.get_json()
        user_id = data.get('id')
        username = data.get('username')
        password = data.get('password')
        role_id = data.get('role_id')
        is_active = data.get('is_active', True)
        
        if not user_id:
            return jsonify({'success': False, 'message': '缺少用户ID'})
        
        # 获取当前用户信息
        current_user = DatabaseManager.execute_query("SELECT * FROM users WHERE id = ?", (user_id,))
        if not current_user:
            return jsonify({'success': False, 'message': '用户不存在'})
        
        current_user = current_user[0]
        
        # 检查是否为admin用户，admin用户有特殊保护
        if current_user['username'] == 'admin':
            # admin用户不能修改用户名，不能禁用，不能删除角色
            if username != 'admin':
                return jsonify({'success': False, 'message': 'admin用户名不能修改'})
            if not is_active:
                return jsonify({'success': False, 'message': 'admin用户不能禁用'})
            # admin用户必须保持管理员角色
            admin_role = DatabaseManager.execute_query("SELECT * FROM roles WHERE name = '管理员' AND is_active = 1")
            if admin_role:
                role_id = admin_role[0]['id']
        
        # 检查用户名是否已被其他用户使用
        if username and username != current_user['username']:
            existing_user = DatabaseManager.get_user_by_username(username)
            if existing_user:
                return jsonify({'success': False, 'message': '用户名已存在'})
        
        # 检查是否为管理员角色
        is_admin = 0
        if role_id:
            role = DatabaseManager.get_role_by_id(role_id)
            if role and role['name'] == '管理员':
                is_admin = 1
        
        # 构建更新查询
        updates = []
        params = []
        
        if username:
            updates.append("username = ?")
            params.append(username)
        
        if password:
            updates.append("password_hash = ?")
            params.append(AuthManager.hash_password(password))
        
        if role_id is not None:
            updates.append("role_id = ?")
            params.append(role_id)
            updates.append("is_admin = ?")
            params.append(is_admin)
        
        updates.append("is_active = ?")
        params.append(is_active)
        
        params.append(user_id)
        
        query = f"UPDATE users SET {', '.join(updates)} WHERE id = ?"
        result = DatabaseManager.execute_update(query, tuple(params))
        
        if result > 0:
            return jsonify({'success': True, 'message': '用户更新成功！'})
        else:
            return jsonify({'success': False, 'message': '更新失败'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'更新失败: {str(e)}'})

@users_bp.route('/delete', methods=['POST'])
@admin_required
def delete_user():
    """删除用户"""
    try:
        data = request.get_json()
        user_id = data.get('id')
        
        if not user_id:
            return jsonify({'success': False, 'message': '缺少用户ID'})
        
        # 检查是否为admin用户
        user = DatabaseManager.execute_query("SELECT * FROM users WHERE id = ?", (user_id,))
        if not user:
            return jsonify({'success': False, 'message': '用户不存在'})
        
        if user[0]['username'] == 'admin':
            return jsonify({'success': False, 'message': 'admin用户不能删除'})
        
        query = "DELETE FROM users WHERE id = ?"
        result = DatabaseManager.execute_update(query, (user_id,))
        
        if result > 0:
            return jsonify({'success': True, 'message': '用户删除成功！'})
        else:
            return jsonify({'success': False, 'message': '用户不存在或已删除'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'删除失败: {str(e)}'})

@users_bp.route('/toggle-status', methods=['POST'])
@admin_required
def toggle_user_status():
    """切换用户状态"""
    try:
        data = request.get_json()
        user_id = data.get('id')
        is_active = data.get('is_active')
        
        if not user_id or is_active is None:
            return jsonify({'success': False, 'message': '缺少必要参数'})
        
        # 检查是否为admin用户
        user = DatabaseManager.execute_query("SELECT * FROM users WHERE id = ?", (user_id,))
        if not user:
            return jsonify({'success': False, 'message': '用户不存在'})
        
        if user[0]['username'] == 'admin' and not is_active:
            return jsonify({'success': False, 'message': 'admin用户不能禁用'})
        
        query = "UPDATE users SET is_active = ? WHERE id = ?"
        result = DatabaseManager.execute_update(query, (is_active, user_id))
        
        if result > 0:
            action = '启用' if is_active else '禁用'
            return jsonify({'success': True, 'message': f'用户{action}成功！'})
        else:
            return jsonify({'success': False, 'message': '用户不存在或操作失败'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'操作失败: {str(e)}'})
