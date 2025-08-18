from flask import Blueprint, render_template, request, jsonify, redirect, url_for
import os
import shutil
from datetime import datetime
from backend.database import DatabaseManager

settings_bp = Blueprint('admin_settings', __name__, url_prefix='/admin/settings')

def admin_required(f):
    def decorated_function(*args, **kwargs):
        from flask import session
        if 'admin_user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

@settings_bp.route('/')
@admin_required
def settings():
    """系统设置页面"""
    try:
        # 获取系统统计信息
        patterns_count = len(DatabaseManager.get_patterns() or [])
        products_count = len(DatabaseManager.get_products() or [])
        categories_count = len(DatabaseManager.get_categories() or [])
        access_codes_count = len(DatabaseManager.get_access_codes() or [])
        users_count = len(DatabaseManager.get_users() or [])
        
        # 获取数据库文件大小
        db_path = 'database.db'
        db_size = os.path.getsize(db_path) if os.path.exists(db_path) else 0
        db_size_mb = round(db_size / (1024 * 1024), 2)
        
        # 获取上传文件夹大小
        upload_size = 0
        if os.path.exists('uploads'):
            for dirpath, dirnames, filenames in os.walk('uploads'):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    upload_size += os.path.getsize(filepath)
        upload_size_mb = round(upload_size / (1024 * 1024), 2)
        
        system_info = {
            'patterns_count': patterns_count,
            'products_count': products_count,
            'categories_count': categories_count,
            'access_codes_count': access_codes_count,
            'users_count': users_count,
            'db_size_mb': db_size_mb,
            'upload_size_mb': upload_size_mb,
            'total_size_mb': round(db_size_mb + upload_size_mb, 2)
        }
        
    except Exception as e:
        print(f"获取系统信息失败: {e}")
        system_info = {
            'patterns_count': 0,
            'products_count': 0,
            'categories_count': 0,
            'access_codes_count': 0,
            'users_count': 0,
            'db_size_mb': 0,
            'upload_size_mb': 0,
            'total_size_mb': 0
        }
    
    return render_template('admin/settings.html', system_info=system_info)

@settings_bp.route('/backup-database', methods=['POST'])
@admin_required
def backup_database():
    """备份数据库"""
    try:
        # 创建备份目录
        backup_dir = 'backups'
        os.makedirs(backup_dir, exist_ok=True)
        
        # 生成备份文件名
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f'database_backup_{timestamp}.db'
        backup_path = os.path.join(backup_dir, backup_filename)
        
        # 复制数据库文件
        if os.path.exists('database.db'):
            shutil.copy2('database.db', backup_path)
            return jsonify({
                'success': True,
                'message': f'数据库备份成功！备份文件：{backup_filename}'
            })
        else:
            return jsonify({'success': False, 'message': '数据库文件不存在'})
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'备份失败: {str(e)}'})

@settings_bp.route('/clear-uploads', methods=['POST'])
@admin_required
def clear_uploads():
    """清理上传文件"""
    try:
        deleted_count = 0
        upload_dirs = ['uploads/patterns', 'uploads/products', 'uploads/depth_maps']
        
        for upload_dir in upload_dirs:
            if os.path.exists(upload_dir):
                for filename in os.listdir(upload_dir):
                    file_path = os.path.join(upload_dir, filename)
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                        deleted_count += 1
        
        return jsonify({
            'success': True,
            'message': f'已清理 {deleted_count} 个上传文件'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'清理失败: {str(e)}'})

@settings_bp.route('/reset-database', methods=['POST'])
@admin_required
def reset_database():
    """重置数据库"""
    try:
        # 先备份当前数据库
        backup_dir = 'backups'
        os.makedirs(backup_dir, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f'database_before_reset_{timestamp}.db'
        backup_path = os.path.join(backup_dir, backup_filename)
        
        if os.path.exists('database.db'):
            shutil.copy2('database.db', backup_path)
        
        # 清空所有表的数据（保留表结构）
        tables = ['patterns', 'products', 'product_categories', 'access_codes']
        for table in tables:
            DatabaseManager.execute_update(f"DELETE FROM {table}")
        
        return jsonify({
            'success': True,
            'message': f'数据库重置成功！原数据已备份为：{backup_filename}'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'重置失败: {str(e)}'})