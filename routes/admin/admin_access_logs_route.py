from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from backend.database import DatabaseManager

access_logs_bp = Blueprint('admin_access_logs', __name__, url_prefix='/admin/access-logs')

def login_required(f):
    def decorated_function(*args, **kwargs):
        from flask import session
        if 'admin_user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

@access_logs_bp.route('/')
@login_required
def access_logs():
    """授权码访问记录管理页面"""
    try:
        access_logs = DatabaseManager.get_access_logs() or []
    except Exception as e:
        print(f"获取访问记录失败: {e}")
        access_logs = []
    return render_template('admin/access_logs.html', access_logs=access_logs)

@access_logs_bp.route('/force-logout', methods=['POST'])
@login_required
def force_logout_access():
    """强制登出指定的访问记录"""
    try:
        data = request.get_json()
        log_id = data.get('id')
        
        if not log_id:
            return jsonify({'success': False, 'message': '缺少访问记录ID'})
        
        result = DatabaseManager.force_logout_access_log(log_id)
        
        if result > 0:
            return jsonify({'success': True, 'message': '强制登出成功！'})
        else:
            return jsonify({'success': False, 'message': '访问记录不存在或已登出'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'操作失败: {str(e)}'})

@access_logs_bp.route('/get-by-code')
@login_required
def get_access_logs_by_code():
    """根据授权码获取访问记录"""
    try:
        access_code = request.args.get('code')
        if not access_code:
            return jsonify({'success': False, 'message': '缺少授权码参数'})
        
        logs = DatabaseManager.get_access_logs(access_code=access_code)
        return jsonify({'success': True, 'data': logs})
    except Exception as e:
        return jsonify({'success': False, 'message': f'获取失败: {str(e)}'})

@access_logs_bp.route('/clear-offline', methods=['POST'])
@login_required
def clear_offline_access_logs():
    """清空已离线的访问记录"""
    try:
        # 删除状态为已离线的访问记录（is_active = 0 表示已离线）
        query = "DELETE FROM access_logs WHERE is_active = 0"
        result = DatabaseManager.execute_update(query)
        
        return jsonify({
            'success': True,
            'message': f'已清空 {result} 条离线访问记录'
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'清空失败: {str(e)}'})