from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from werkzeug.utils import secure_filename
import os
from datetime import datetime
from PIL import Image
from backend.database import DatabaseManager

patterns_bp = Blueprint('admin_patterns', __name__, url_prefix='/admin/patterns')

def login_required(f):
    def decorated_function(*args, **kwargs):
        from flask import session
        if 'admin_user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

@patterns_bp.route('/')
@login_required
def patterns():
    """印花图案管理页面"""
    try:
        patterns = DatabaseManager.get_patterns() or []
    except Exception as e:
        print(f"获取印花图案失败: {e}")
        patterns = []
    return render_template('admin/patterns.html', patterns=patterns)

@patterns_bp.route('/add', methods=['POST'])
@login_required
def add_pattern():
    """添加印花图案"""
    try:
        name = request.form.get('name')
        if not name:
            return jsonify({'success': False, 'message': '请输入图案名称'})
        
        if 'file' not in request.files:
            return jsonify({'success': False, 'message': '请选择图片文件'})
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'message': '请选择图片文件'})
        
        # 检查重名
        existing_pattern = DatabaseManager.execute_query("SELECT id FROM patterns WHERE name = ?", (name,))
        if existing_pattern:
            return jsonify({'success': False, 'message': f'图案名称"{name}"已存在，请使用其他名称'})
        
        # 保存文件
        original_filename = file.filename
        file_ext = os.path.splitext(original_filename)[1].lower()
        safe_name = secure_filename(os.path.splitext(original_filename)[0])
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"pattern_{timestamp}_{safe_name}{file_ext}"
        
        upload_path = os.path.join('uploads', 'patterns')
        os.makedirs(upload_path, exist_ok=True)
        file_path = os.path.join(upload_path, filename)
        file.save(file_path)
        
        # 获取图片信息
        with Image.open(file_path) as img:
            width, height = img.size
        
        file_size = os.path.getsize(file_path)
        
        # 创建图案记录
        query = '''
            INSERT INTO patterns (name, filename, file_path, file_size, image_width, image_height, upload_time)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        '''
        pattern_id = DatabaseManager.execute_insert(query, (
            name, filename, file_path, file_size, width, height, datetime.now()
        ))
        
        return jsonify({
            'success': True, 
            'message': f'印花图案"{name}"添加成功！',
            'pattern_id': pattern_id
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'添加失败: {str(e)}'})

@patterns_bp.route('/batch-upload', methods=['POST'])
@login_required
def batch_upload_patterns():
    """批量上传印花图案"""
    try:
        if 'files' not in request.files:
            return jsonify({'success': False, 'message': '请选择图片文件'})
        
        files = request.files.getlist('files')
        if not files or all(f.filename == '' for f in files):
            return jsonify({'success': False, 'message': '请选择图片文件'})
        
        results = []
        success_count = 0
        error_count = 0
        
        for file in files:
            if file.filename == '':
                continue
                
            try:
                # 使用文件名作为图案名称（去掉扩展名）
                original_filename = file.filename
                pattern_name = os.path.splitext(original_filename)[0]
                file_ext = os.path.splitext(original_filename)[1].lower()
                
                # 检查重名
                existing_pattern = DatabaseManager.execute_query("SELECT id FROM patterns WHERE name = ?", (pattern_name,))
                if existing_pattern:
                    results.append({
                        'filename': original_filename,
                        'status': 'duplicate',
                        'message': f'图案名称"{pattern_name}"已存在'
                    })
                    continue
                
                # 保存文件
                safe_name = secure_filename(os.path.splitext(original_filename)[0])
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
                filename = f"pattern_{timestamp}_{safe_name}{file_ext}"
                
                upload_path = os.path.join('uploads', 'patterns')
                os.makedirs(upload_path, exist_ok=True)
                file_path = os.path.join(upload_path, filename)
                file.save(file_path)
                
                # 获取图片信息
                with Image.open(file_path) as img:
                    width, height = img.size
                
                file_size = os.path.getsize(file_path)
                
                # 创建图案记录
                query = '''
                    INSERT INTO patterns (name, filename, file_path, file_size, image_width, image_height, upload_time)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                '''
                pattern_id = DatabaseManager.execute_insert(query, (
                    pattern_name, filename, file_path, file_size, width, height, datetime.now()
                ))
                
                results.append({
                    'filename': original_filename,
                    'status': 'success',
                    'message': f'上传成功',
                    'pattern_id': pattern_id
                })
                success_count += 1
                
            except Exception as e:
                results.append({
                    'filename': file.filename,
                    'status': 'error',
                    'message': f'上传失败: {str(e)}'
                })
                error_count += 1
        
        return jsonify({
            'success': True,
            'message': f'批量上传完成！成功: {success_count} 个，失败: {error_count} 个',
            'results': results,
            'success_count': success_count,
            'error_count': error_count
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'批量上传失败: {str(e)}'})

@patterns_bp.route('/get-existing-names')
@login_required
def get_existing_pattern_names():
    """获取现有图案名称列表"""
    try:
        query = "SELECT name FROM patterns"
        results = DatabaseManager.execute_query(query)
        names = [row['name'] for row in results] if results else []
        return jsonify({'success': True, 'names': names})
    except Exception as e:
        return jsonify({'success': False, 'message': f'获取失败: {str(e)}'})

@patterns_bp.route('/get')
@login_required
def get_pattern():
    """获取单个印花图案信息"""
    try:
        pattern_id = request.args.get('id', type=int)
        if not pattern_id:
            return jsonify({'success': False, 'message': '缺少图案ID'})
        
        query = "SELECT * FROM patterns WHERE id = ?"
        results = DatabaseManager.execute_query(query, (pattern_id,))
        
        if results:
            pattern = dict(results[0])
            return jsonify({'success': True, 'data': pattern})
        else:
            return jsonify({'success': False, 'message': '图案不存在'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'获取失败: {str(e)}'})

@patterns_bp.route('/update', methods=['POST'])
@login_required
def update_pattern():
    """更新印花图案"""
    try:
        pattern_id = request.form.get('id', type=int)
        name = request.form.get('name')
        
        if not pattern_id or not name:
            return jsonify({'success': False, 'message': '缺少必要参数'})
        
        # 构建更新字段和参数
        update_fields = ["name = ?"]
        params = [name]
        
        # 处理文件上传
        if 'file' in request.files and request.files['file'].filename != '':
            file = request.files['file']
            
            # 获取原文件信息用于删除
            query = "SELECT filename, file_path FROM patterns WHERE id = ?"
            old_pattern = DatabaseManager.execute_query(query, (pattern_id,))
            
            # 保存新文件
            original_filename = file.filename
            file_ext = os.path.splitext(original_filename)[1].lower()
            safe_name = secure_filename(os.path.splitext(original_filename)[0])
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"pattern_{timestamp}_{safe_name}{file_ext}"
            
            upload_path = os.path.join('uploads', 'patterns')
            os.makedirs(upload_path, exist_ok=True)
            file_path = os.path.join(upload_path, filename)
            file.save(file_path)
            
            # 获取新图片信息
            with Image.open(file_path) as img:
                width, height = img.size
            
            file_size = os.path.getsize(file_path)
            
            # 删除旧文件
            if old_pattern:
                old_file_path = old_pattern[0]['file_path']
                if os.path.exists(old_file_path):
                    os.remove(old_file_path)
            
            # 添加文件相关字段到更新列表
            update_fields.extend([
                "filename = ?",
                "file_path = ?", 
                "file_size = ?",
                "image_width = ?",
                "image_height = ?"
            ])
            params.extend([filename, file_path, file_size, width, height])
        
        # 添加pattern_id到参数末尾
        params.append(pattern_id)
        
        # 构建完整的更新查询
        query = f"UPDATE patterns SET {', '.join(update_fields)} WHERE id = ?"
        
        result = DatabaseManager.execute_update(query, tuple(params))
        
        if result > 0:
            return jsonify({'success': True, 'message': '印花图案更新成功！'})
        else:
            return jsonify({'success': False, 'message': '图案不存在或更新失败'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'更新失败: {str(e)}'})

@patterns_bp.route('/delete', methods=['POST'])
@login_required
def delete_pattern():
    """删除印花图案"""
    try:
        data = request.get_json()
        pattern_id = data.get('id')
        
        if not pattern_id:
            return jsonify({'success': False, 'message': '缺少图案ID'})
        
        # 获取文件路径并删除文件
        query = "SELECT file_path FROM patterns WHERE id = ?"
        results = DatabaseManager.execute_query(query, (pattern_id,))
        
        if results:
            file_path = results[0]['file_path']
            if os.path.exists(file_path):
                os.remove(file_path)
        
        # 删除数据库记录
        query = "DELETE FROM patterns WHERE id = ?"
        result = DatabaseManager.execute_update(query, (pattern_id,))
        
        if result > 0:
            return jsonify({'success': True, 'message': '印花图案删除成功！'})
        else:
            return jsonify({'success': False, 'message': '图案不存在或已删除'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'删除失败: {str(e)}'})

@patterns_bp.route('/clear', methods=['POST'])
@login_required
def clear_patterns():
    """清空所有印花图案"""
    try:
        # 获取所有图案文件路径
        query = "SELECT file_path FROM patterns"
        results = DatabaseManager.execute_query(query)
        
        # 删除文件
        for row in results:
            file_path = row['file_path']
            if os.path.exists(file_path):
                os.remove(file_path)
        
        # 清空数据库记录
        query = "DELETE FROM patterns"
        result = DatabaseManager.execute_update(query)
        
        return jsonify({'success': True, 'message': f'已清空所有印花图案，共 {result} 个'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'清空失败: {str(e)}'})