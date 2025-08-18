from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from werkzeug.utils import secure_filename
import os
from datetime import datetime
from backend.database import DatabaseManager

theme_backgrounds_bp = Blueprint('admin_theme_backgrounds', __name__, url_prefix='/admin/theme-backgrounds')

def login_required(f):
    def decorated_function(*args, **kwargs):
        from flask import session
        if 'admin_user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

@theme_backgrounds_bp.route('/')
@login_required
def theme_backgrounds():
    """主题背景图管理页面"""
    try:
        # 获取所有主题
        themes = []
        theme_dir = 'static/themes'
        if os.path.exists(theme_dir):
            for file in os.listdir(theme_dir):
                if file.endswith('.css'):
                    theme_name = file.replace('.css', '')
                    themes.append(theme_name)
        
        # 从数据库获取背景图
        backgrounds = DatabaseManager.get_theme_backgrounds()
        
    except Exception as e:
        print(f"获取主题背景图数据失败: {e}")
        themes = []
        backgrounds = []
    
    return render_template('admin/theme_backgrounds.html', 
                         themes=themes, 
                         backgrounds=backgrounds)

@theme_backgrounds_bp.route('/upload', methods=['POST'])
@login_required
def upload_theme_background():
    """上传主题背景图"""
    try:
        theme_name = request.form.get('theme_name')
        background_name = request.form.get('background_name')
        
        if not theme_name or not background_name:
            return jsonify({'success': False, 'message': '请填写完整信息'})
        
        if 'file' not in request.files:
            return jsonify({'success': False, 'message': '请选择图片文件'})
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'message': '请选择图片文件'})
        
        # 检查文件类型
        allowed_extensions = {'.png', '.jpg', '.jpeg', '.webp'}
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in allowed_extensions:
            return jsonify({'success': False, 'message': '只支持 PNG、JPG、JPEG、WEBP 格式'})
        
        # 生成文件名
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_name = secure_filename(background_name)
        filename = f"theme_bg_{timestamp}_{safe_name}{file_ext}"
        
        # 保存文件到 uploads/themes_bgs
        bg_dir = 'uploads/themes_bgs'
        os.makedirs(bg_dir, exist_ok=True)
        file_path = os.path.join(bg_dir, filename)
        file.save(file_path)
        
        # 获取文件大小
        file_size = os.path.getsize(file_path)
        
        # 保存到数据库
        DatabaseManager.add_theme_background(
            theme_name=theme_name,
            background_name=background_name,
            file_path=f'/uploads/themes_bgs/{filename}',
            file_size=file_size
        )
        
        return jsonify({
            'success': True,
            'message': f'主题背景图上传成功！',
            'filename': filename
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'上传失败: {str(e)}'})

@theme_backgrounds_bp.route('/get')
@login_required
def get_theme_background():
    """获取单个主题背景图信息"""
    try:
        bg_id = request.args.get('id', type=int)
        if not bg_id:
            return jsonify({'success': False, 'message': '缺少背景图ID'})
        
        background = DatabaseManager.get_theme_background_by_id(bg_id)
        if background:
            return jsonify({'success': True, 'data': background})
        else:
            return jsonify({'success': False, 'message': '背景图不存在'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'获取失败: {str(e)}'})

@theme_backgrounds_bp.route('/update', methods=['POST'])
@login_required
def update_theme_background():
    """更新主题背景图"""
    try:
        # 支持表单数据和文件上传
        if request.content_type and 'multipart/form-data' in request.content_type:
            bg_id = request.form.get('id')
            background_name = request.form.get('background_name')
            theme_name = request.form.get('theme_name')
            file = request.files.get('file')
        else:
            data = request.get_json()
            bg_id = data.get('id')
            background_name = data.get('background_name')
            theme_name = data.get('theme_name')
            file = None
        
        if not bg_id:
            return jsonify({'success': False, 'message': '缺少背景图ID'})
        
        # 获取原始记录
        original_bg = DatabaseManager.get_theme_background_by_id(int(bg_id))
        if not original_bg:
            return jsonify({'success': False, 'message': '背景图不存在'})
        
        # 处理文件上传
        new_file_path = None
        new_file_size = None
        
        if file and file.filename:
            # 检查文件类型
            allowed_extensions = {'.png', '.jpg', '.jpeg', '.webp'}
            file_ext = os.path.splitext(file.filename)[1].lower()
            if file_ext not in allowed_extensions:
                return jsonify({'success': False, 'message': '只支持 PNG、JPG、JPEG、WEBP 格式'})
            
            # 删除旧文件
            old_file_path = original_bg['file_path'].replace('/uploads/', 'uploads/')
            if os.path.exists(old_file_path):
                os.remove(old_file_path)
            
            # 保存新文件
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            safe_name = secure_filename(background_name or original_bg['background_name'])
            filename = f"theme_bg_{timestamp}_{safe_name}{file_ext}"
            
            bg_dir = 'uploads/themes_bgs'
            os.makedirs(bg_dir, exist_ok=True)
            file_path = os.path.join(bg_dir, filename)
            file.save(file_path)
            
            new_file_path = f'/uploads/themes_bgs/{filename}'
            new_file_size = os.path.getsize(file_path)
        
        # 更新数据库
        result = DatabaseManager.update_theme_background(
            bg_id=int(bg_id),
            background_name=background_name,
            theme_name=theme_name,
            file_path=new_file_path,
            file_size=new_file_size
        )
        
        if result > 0:
            return jsonify({'success': True, 'message': '背景图更新成功！'})
        else:
            return jsonify({'success': False, 'message': '背景图不存在或更新失败'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'更新失败: {str(e)}'})

@theme_backgrounds_bp.route('/delete', methods=['POST'])
@login_required
def delete_theme_background():
    """删除主题背景图"""
    try:
        data = request.get_json()
        bg_id = data.get('id')
        
        if not bg_id:
            return jsonify({'success': False, 'message': '缺少背景图ID'})
        
        # 获取文件路径
        background = DatabaseManager.get_theme_background_by_id(bg_id)
        if background:
            # 删除物理文件
            file_path = background['file_path'].replace('/uploads/', 'uploads/')
            if os.path.exists(file_path):
                os.remove(file_path)
        
        # 从数据库删除记录
        result = DatabaseManager.delete_theme_background(bg_id)
        
        if result > 0:
            return jsonify({'success': True, 'message': '背景图删除成功！'})
        else:
            return jsonify({'success': False, 'message': '背景图不存在或已删除'})
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'删除失败: {str(e)}'})

@theme_backgrounds_bp.route('/clear-all', methods=['POST'])
@login_required
def clear_all_theme_backgrounds():
    """清空所有主题背景图"""
    try:
        # 获取所有背景图
        backgrounds = DatabaseManager.get_theme_backgrounds()
        
        # 删除物理文件
        for bg in backgrounds:
            file_path = bg['file_path'].replace('/uploads/', 'uploads/')
            if os.path.exists(file_path):
                os.remove(file_path)
        
        # 从数据库删除所有记录
        query = "DELETE FROM theme_backgrounds"
        deleted_count = DatabaseManager.execute_update(query)
        
        return jsonify({
            'success': True,
            'message': f'已清空所有背景图，共删除 {deleted_count} 张'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'清空失败: {str(e)}'})

@theme_backgrounds_bp.route('/clear-theme', methods=['POST'])
@login_required
def clear_theme_backgrounds():
    """清空指定主题的所有背景图"""
    try:
        data = request.get_json()
        theme_name = data.get('theme_name')
        
        if not theme_name:
            return jsonify({'success': False, 'message': '缺少主题名称'})
        
        # 获取该主题的所有背景图
        backgrounds = DatabaseManager.get_theme_backgrounds(theme_name)
        
        # 删除物理文件
        for bg in backgrounds:
            file_path = bg['file_path'].replace('/uploads/', 'uploads/')
            if os.path.exists(file_path):
                os.remove(file_path)
        
        # 从数据库删除记录
        deleted_count = DatabaseManager.clear_theme_backgrounds(theme_name)
        
        return jsonify({
            'success': True,
            'message': f'已清空主题 "{theme_name}" 的 {deleted_count} 张背景图'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'清空失败: {str(e)}'})