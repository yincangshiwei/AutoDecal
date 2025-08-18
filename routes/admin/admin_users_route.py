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
        query = "SELECT * FROM users ORDER BY created_time DESC"
        results = DatabaseManager.execute_query(query)
        users = [dict(row) for row in results] if results else []
    except Exception as e:
        print(f"获取用户数据失败: {e}")
        users = []
    return render_template('admin/users.html', users=users)

@users_bp.route('/add', methods=['POST'])
@admin_required
def add_user():
    """添加用户"""
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        role = data.get('role', 'user')
        
        if not username or not password:
            return jsonify({'success': False, 'message': '请填写完整的用户信息'})
        
        # 加密密码
        password_hash = AuthManager.hash_password(password)
        is_admin = 1 if role == 'admin' else 0
        
        query = '''
            INSERT INTO users (username, password_hash, is_admin, is_active, created_time)
            VALUES (?, ?, ?, 1, ?)
        '''
        user_id = DatabaseManager.execute_insert(query, (
            username, password_hash, is_admin, datetime.now()
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
        role = data.get('role')
        is_active = data.get('is_active', True)
        
        if not user_id or not username:
            return jsonify({'success': False, 'message': '缺少必要参数'})
        
        is_admin = 1 if role == 'admin' else 0
        
        if password:
            # 更新密码
            password_hash = AuthManager.hash_password(password)
            query = '''
                UPDATE users 
                SET username = ?, password_hash = ?, is_admin = ?, is_active = ?
                WHERE id = ?
            '''
            result = DatabaseManager.execute_update(query, (
                username, password_hash, is_admin, is_active, user_id
            ))
        else:
            # 不更新密码
            query = '''
                UPDATE users 
                SET username = ?, is_admin = ?, is_active = ?
                WHERE id = ?
            '''
            result = DatabaseManager.execute_update(query, (
                username, is_admin, is_active, user_id
            ))
        
        if result > 0:
            return jsonify({'success': True, 'message': '用户更新成功！'})
        else:
            return jsonify({'success': False, 'message': '用户不存在或更新失败'})
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
        
        query = "UPDATE users SET is_active = ? WHERE id = ?"
        result = DatabaseManager.execute_update(query, (is_active, user_id))
        
        if result > 0:
            action = '启用' if is_active else '禁用'
            return jsonify({'success': True, 'message': f'用户{action}成功！'})
        else:
            return jsonify({'success': False, 'message': '用户不存在或操作失败'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'操作失败: {str(e)}'})