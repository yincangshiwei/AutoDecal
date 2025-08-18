from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from datetime import datetime
from backend.database import DatabaseManager

access_codes_bp = Blueprint('admin_access_codes', __name__, url_prefix='/admin/access-codes')

def login_required(f):
    def decorated_function(*args, **kwargs):
        from flask import session
        if 'admin_user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

@access_codes_bp.route('/')
@login_required
def access_codes():
    """授权码管理页面"""
    try:
        query = "SELECT * FROM access_codes ORDER BY created_time DESC"
        results = DatabaseManager.execute_query(query)
        access_codes = []
        
        if results:
            for row in results:
                code = dict(row)
                
                # 处理expires_at字段
                expires_at = code.get('expires_at')
                if expires_at:
                    if isinstance(expires_at, str):
                        try:
                            code['expires_at'] = datetime.fromisoformat(expires_at.replace('T', ' '))
                        except ValueError:
                            code['expires_at'] = None
                
                # 处理created_time字段
                created_time = code.get('created_time')
                if created_time and isinstance(created_time, str):
                    try:
                        code['created_time'] = datetime.fromisoformat(created_time.replace('T', ' '))
                    except ValueError:
                        pass
                
                # 设置状态
                if code.get('expires_at') and isinstance(code['expires_at'], datetime) and code['expires_at'] < datetime.now():
                    code['status'] = 'expired'
                elif code.get('is_active', 1):
                    code['status'] = 'active'
                else:
                    code['status'] = 'inactive'
                
                access_codes.append(code)
    except Exception as e:
        print(f"获取授权码数据失败: {e}")
        access_codes = []
    return render_template('admin/access_codes.html', access_codes=access_codes)

@access_codes_bp.route('/add', methods=['POST'])
@login_required
def add_access_code():
    """添加授权码"""
    try:
        data = request.get_json()
        code = data.get('code')
        description = data.get('description', '')
        expires_at = data.get('expires_at')
        max_uses = data.get('max_uses')
        
        if not code:
            return jsonify({'success': False, 'message': '请输入授权码'})
        
        # 处理过期时间
        expires_datetime = None
        if expires_at:
            expires_datetime = datetime.fromisoformat(expires_at.replace('T', ' '))
        
        # 处理最大使用次数
        max_uses_value = None
        if max_uses:
            max_uses_value = int(max_uses)
        
        query = '''
            INSERT INTO access_codes (code, description, expires_at, max_uses, is_active, created_time)
            VALUES (?, ?, ?, ?, 1, ?)
        '''
        code_id = DatabaseManager.execute_insert(query, (
            code, description, expires_datetime, max_uses_value, datetime.now()
        ))
        
        return jsonify({
            'success': True,
            'message': f'授权码"{code}"添加成功！',
            'code_id': code_id
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'添加失败: {str(e)}'})

@access_codes_bp.route('/get')
@login_required
def get_access_code():
    """获取单个授权码信息"""
    try:
        code_id = request.args.get('id', type=int)
        if not code_id:
            return jsonify({'success': False, 'message': '缺少授权码ID'})
        
        query = "SELECT * FROM access_codes WHERE id = ?"
        results = DatabaseManager.execute_query(query, (code_id,))
        
        if results:
            code = dict(results[0])
            return jsonify({'success': True, 'data': code})
        else:
            return jsonify({'success': False, 'message': '授权码不存在'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'获取失败: {str(e)}'})

@access_codes_bp.route('/update', methods=['POST'])
@login_required
def update_access_code():
    """更新授权码"""
    try:
        data = request.get_json()
        code_id = data.get('id')
        code = data.get('code')
        description = data.get('description', '')
        expires_at = data.get('expires_at')
        max_uses = data.get('max_uses')
        
        if not code_id or not code:
            return jsonify({'success': False, 'message': '缺少必要参数'})
        
        # 处理过期时间
        expires_datetime = None
        if expires_at:
            expires_datetime = datetime.fromisoformat(expires_at.replace('T', ' '))
        
        # 处理最大使用次数
        max_uses_value = None
        if max_uses:
            max_uses_value = int(max_uses)
        
        query = '''
            UPDATE access_codes 
            SET code = ?, description = ?, expires_at = ?, max_uses = ?
            WHERE id = ?
        '''
        result = DatabaseManager.execute_update(query, (
            code, description, expires_datetime, max_uses_value, code_id
        ))
        
        if result > 0:
            return jsonify({'success': True, 'message': '授权码更新成功！'})
        else:
            return jsonify({'success': False, 'message': '授权码不存在或更新失败'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'更新失败: {str(e)}'})

@access_codes_bp.route('/delete', methods=['POST'])
@login_required
def delete_access_code():
    """删除授权码"""
    try:
        data = request.get_json()
        code_id = data.get('id')
        
        if not code_id:
            return jsonify({'success': False, 'message': '缺少授权码ID'})
        
        query = "DELETE FROM access_codes WHERE id = ?"
        result = DatabaseManager.execute_update(query, (code_id,))
        
        if result > 0:
            return jsonify({'success': True, 'message': '授权码删除成功！'})
        else:
            return jsonify({'success': False, 'message': '授权码不存在或已删除'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'删除失败: {str(e)}'})

@access_codes_bp.route('/toggle-status', methods=['POST'])
@login_required
def toggle_access_code_status():
    """切换授权码状态"""
    try:
        data = request.get_json()
        code_id = data.get('id')
        status = data.get('status')
        
        if not code_id or status is None:
            return jsonify({'success': False, 'message': '缺少必要参数'})
        
        query = "UPDATE access_codes SET is_active = ? WHERE id = ?"
        is_active_value = 1 if status == 'active' else 0
        result = DatabaseManager.execute_update(query, (is_active_value, code_id))
        
        if result > 0:
            action = '启用' if status == 'active' else '禁用'
            return jsonify({'success': True, 'message': f'授权码{action}成功！'})
        else:
            return jsonify({'success': False, 'message': '授权码不存在或操作失败'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'操作失败: {str(e)}'})