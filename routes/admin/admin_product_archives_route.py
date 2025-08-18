from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from datetime import datetime
from backend.database import DatabaseManager

product_archives_bp = Blueprint('admin_product_archives', __name__, url_prefix='/admin/product_archives')

def login_required(f):
    def decorated_function(*args, **kwargs):
        from flask import session
        if 'admin_user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

@product_archives_bp.route('/')
@login_required
def product_archives():
    """产品效果归档管理页面"""
    try:
        archives = DatabaseManager.get_product_archives()
    except Exception as e:
        print(f"获取产品效果归档数据失败: {e}")
        archives = []
    return render_template('admin/product_archives.html', archives=archives)

@product_archives_bp.route('/add', methods=['POST'])
@login_required
def add_product_archive():
    """添加产品效果归档"""
    try:
        data = request.get_json()
        access_code = data.get('access_code', '')
        original_product_image = data.get('original_product_image', '')
        original_depth_image = data.get('original_depth_image', '')
        effect_image = data.get('effect_image', '')
        effect_category = data.get('effect_category', '')
        registration_info = data.get('registration_info', '')
        follow_up_person = data.get('follow_up_person', '')
        
        if not all([access_code, original_product_image, original_depth_image, effect_image, effect_category]):
            return jsonify({'success': False, 'message': '请填写完整的归档信息'})
        
        # 这里应该处理文件上传，暂时使用占位符路径
        original_product_path = f"uploads/archives/original_product_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        original_depth_path = f"uploads/archives/original_depth_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        effect_image_path = f"uploads/archives/effect_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        
        archive_id = DatabaseManager.add_product_archive(
            access_code, original_product_image, original_depth_image, effect_image,
            effect_category, registration_info, follow_up_person,
            original_product_path, original_depth_path, effect_image_path
        )
        
        return jsonify({
            'success': True,
            'message': '产品效果归档添加成功！',
            'archive_id': archive_id
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'添加失败: {str(e)}'})

@product_archives_bp.route('/get')
@login_required
def get_product_archive():
    """获取单个产品效果归档信息"""
    try:
        archive_id = request.args.get('id', type=int)
        if not archive_id:
            return jsonify({'success': False, 'message': '缺少归档ID'})
        
        archive = DatabaseManager.get_product_archive_by_id(archive_id)
        
        if archive:
            return jsonify({'success': True, 'data': archive})
        else:
            return jsonify({'success': False, 'message': '归档不存在'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'获取失败: {str(e)}'})

@product_archives_bp.route('/delete', methods=['POST'])
@login_required
def delete_product_archive():
    """删除产品效果归档"""
    try:
        data = request.get_json()
        archive_id = data.get('id')
        
        if not archive_id:
            return jsonify({'success': False, 'message': '缺少归档ID'})
        
        result = DatabaseManager.delete_product_archive(archive_id)
        
        if result > 0:
            return jsonify({'success': True, 'message': '产品效果归档删除成功！'})
        else:
            return jsonify({'success': False, 'message': '归档不存在或已删除'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'删除失败: {str(e)}'})

def allowed_file(filename):
    """检查文件扩展名是否允许"""
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS