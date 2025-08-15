"""
Flask后台管理界面
替代Gradio的稳定后台管理系统
"""
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, flash
from werkzeug.utils import secure_filename
import os
import shutil
from datetime import datetime, timedelta
from PIL import Image
from .database import DatabaseManager
from .auth import AuthManager, AccessCodeManager, login_required, admin_required
from .models import Pattern, Product, ProductCategory, AccessCode

# 创建后台管理蓝图
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/')
def index():
    """后台管理首页"""
    if 'admin_user_id' not in session:
        return redirect(url_for('admin.login'))
    
    # 获取统计数据
    stats = {
        'patterns_count': len(DatabaseManager.get_patterns()),
        'products_count': len(DatabaseManager.get_products()),
        'categories_count': len(DatabaseManager.get_categories()),
        'access_codes_count': len(DatabaseManager.get_access_codes()),
        'users_count': len(DatabaseManager.get_users())
    }
    
    return render_template('admin/dashboard.html', stats=stats)

@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    """管理员登录"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = AuthManager.authenticate_user(username, password)
        if user and user['is_admin']:
            session['admin_user_id'] = user['id']
            session['admin_username'] = user['username']
            flash('登录成功！', 'success')
            return redirect(url_for('admin.index'))
        else:
            flash('用户名或密码错误，或您没有管理员权限', 'error')
    
    return render_template('admin/login.html')

@admin_bp.route('/logout')
def logout():
    """管理员登出"""
    session.pop('admin_user_id', None)
    session.pop('admin_username', None)
    flash('已退出登录', 'info')
    return redirect(url_for('admin.login'))

# 印花图案管理
@admin_bp.route('/patterns')
@login_required
def patterns():
    """印花图案管理页面"""
    patterns = DatabaseManager.get_patterns(active_only=False)
    return render_template('admin/patterns.html', patterns=patterns)

@admin_bp.route('/patterns/add', methods=['POST'])
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
        
        # 保存文件
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"pattern_{timestamp}_{filename}"
        
        upload_path = os.path.join('uploads', 'patterns')
        os.makedirs(upload_path, exist_ok=True)
        file_path = os.path.join(upload_path, filename)
        file.save(file_path)
        
        # 获取图片信息
        with Image.open(file_path) as img:
            width, height = img.size
        
        file_size = os.path.getsize(file_path)
        
        # 创建图案记录
        pattern = Pattern(
            name=name,
            filename=filename,
            file_path=file_path,
            file_size=file_size,
            image_width=width,
            image_height=height
        )
        
        pattern_id = DatabaseManager.add_pattern(pattern)
        
        return jsonify({
            'success': True, 
            'message': f'印花图案"{name}"添加成功！',
            'pattern_id': pattern_id
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'添加失败: {str(e)}'})

@admin_bp.route('/patterns/get')
@login_required
def get_pattern():
    """获取单个印花图案信息"""
    try:
        pattern_id = request.args.get('id', type=int)
        if not pattern_id:
            return jsonify({'success': False, 'message': '缺少图案ID'})
        
        pattern = DatabaseManager.get_pattern_by_id(pattern_id)
        if pattern:
            return jsonify({'success': True, 'data': pattern})
        else:
            return jsonify({'success': False, 'message': '图案不存在'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'获取失败: {str(e)}'})

@admin_bp.route('/patterns/update', methods=['POST'])
@login_required
def update_pattern():
    """更新印花图案"""
    try:
        pattern_id = request.form.get('id', type=int)
        name = request.form.get('name')
        
        if not pattern_id or not name:
            return jsonify({'success': False, 'message': '缺少必要参数'})
        
        result = DatabaseManager.update_pattern(pattern_id, name=name)
        if result > 0:
            return jsonify({'success': True, 'message': '印花图案更新成功！'})
        else:
            return jsonify({'success': False, 'message': '图案不存在或更新失败'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'更新失败: {str(e)}'})

@admin_bp.route('/patterns/delete', methods=['POST'])
@login_required
def delete_pattern():
    """删除印花图案"""
    try:
        data = request.get_json()
        pattern_id = data.get('id')
        
        if not pattern_id:
            return jsonify({'success': False, 'message': '缺少图案ID'})
        
        result = DatabaseManager.delete_pattern(pattern_id)
        if result > 0:
            return jsonify({'success': True, 'message': '印花图案删除成功！'})
        else:
            return jsonify({'success': False, 'message': '图案不存在或已删除'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'删除失败: {str(e)}'})

@admin_bp.route('/patterns/clear', methods=['POST'])
@login_required
def clear_patterns():
    """清空所有印花图案"""
    try:
        result = DatabaseManager.clear_patterns()
        return jsonify({'success': True, 'message': f'已清空所有印花图案，共 {result} 个'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'清空失败: {str(e)}'})

# 产品管理
@admin_bp.route('/products')
@login_required
def products():
    """产品管理页面"""
    products = DatabaseManager.get_products()
    categories = DatabaseManager.get_categories()
    return render_template('admin/products.html', products=products, categories=categories)

@admin_bp.route('/products/add', methods=['POST'])
@login_required
def add_product():
    """添加产品"""
    try:
        title = request.form.get('title')
        category_id = request.form.get('category_id', type=int)
        
        if not title or not category_id:
            return jsonify({'success': False, 'message': '请填写完整的产品信息'})
        
        if 'product_image' not in request.files or 'depth_image' not in request.files:
            return jsonify({'success': False, 'message': '请上传产品图和深度图'})
        
        product_file = request.files['product_image']
        depth_file = request.files['depth_image']
        
        if product_file.filename == '' or depth_file.filename == '':
            return jsonify({'success': False, 'message': '请上传产品图和深度图'})
        
        # 保存产品图
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        product_filename = f"product_{timestamp}_{secure_filename(product_file.filename)}"
        depth_filename = f"depth_{timestamp}_{secure_filename(depth_file.filename)}"
        
        product_path = os.path.join('uploads', 'products', product_filename)
        depth_path = os.path.join('uploads', 'depth_maps', depth_filename)
        
        os.makedirs(os.path.dirname(product_path), exist_ok=True)
        os.makedirs(os.path.dirname(depth_path), exist_ok=True)
        
        product_file.save(product_path)
        depth_file.save(depth_path)
        
        # 获取图片尺寸
        with Image.open(product_path) as img:
            width, height = img.size
        
        # 创建产品记录
        product = Product(
            title=title,
            category_id=category_id,
            product_image=product_filename,
            depth_image=depth_filename,
            product_image_path=product_path,
            depth_image_path=depth_path,
            image_width=width,
            image_height=height
        )
        
        product_id = DatabaseManager.add_product(product)
        
        return jsonify({
            'success': True,
            'message': f'产品"{title}"添加成功！',
            'product_id': product_id
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'添加失败: {str(e)}'})

@admin_bp.route('/products/get')
@login_required
def get_product():
    """获取单个产品信息"""
    try:
        product_id = request.args.get('id', type=int)
        if not product_id:
            return jsonify({'success': False, 'message': '缺少产品ID'})
        
        products = DatabaseManager.get_products()
        product = next((p for p in products if p['id'] == product_id), None)
        
        if product:
            return jsonify({'success': True, 'data': product})
        else:
            return jsonify({'success': False, 'message': '产品不存在'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'获取失败: {str(e)}'})

@admin_bp.route('/products/update', methods=['POST'])
@login_required
def update_product():
    """更新产品"""
    try:
        product_id = request.form.get('id', type=int)
        title = request.form.get('title')
        category_id = request.form.get('category_id', type=int)
        
        if not product_id or not title or not category_id:
            return jsonify({'success': False, 'message': '缺少必要参数'})
        
        result = DatabaseManager.update_product(product_id, title=title, category_id=category_id)
        if result > 0:
            return jsonify({'success': True, 'message': '产品更新成功！'})
        else:
            return jsonify({'success': False, 'message': '产品不存在或更新失败'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'更新失败: {str(e)}'})

@admin_bp.route('/products/delete', methods=['POST'])
@login_required
def delete_product():
    """删除产品"""
    try:
        data = request.get_json()
        product_id = data.get('id')
        
        if not product_id:
            return jsonify({'success': False, 'message': '缺少产品ID'})
        
        result = DatabaseManager.delete_product(product_id)
        if result > 0:
            return jsonify({'success': True, 'message': '产品删除成功！'})
        else:
            return jsonify({'success': False, 'message': '产品不存在或已删除'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'删除失败: {str(e)}'})

@admin_bp.route('/products/clear', methods=['POST'])
@login_required
def clear_products():
    """清空所有产品"""
    try:
        result = DatabaseManager.clear_products()
        return jsonify({'success': True, 'message': f'已清空所有产品，共 {result} 个'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'清空失败: {str(e)}'})

# 分类管理
@admin_bp.route('/categories')
@login_required
def categories():
    """分类管理页面"""
    categories = DatabaseManager.get_categories(active_only=False)
    return render_template('admin/categories.html', categories=categories)

@admin_bp.route('/categories/add', methods=['POST'])
@login_required
def add_category():
    """添加分类"""
    try:
        name = request.form.get('name')
        is_default = request.form.get('is_default') == 'on'
        
        if not name:
            return jsonify({'success': False, 'message': '请输入分类名称'})
        
        category_id = DatabaseManager.add_category(name, is_default)
        
        return jsonify({
            'success': True,
            'message': f'分类"{name}"添加成功！',
            'category_id': category_id
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'添加失败: {str(e)}'})

# 授权码管理
@admin_bp.route('/access-codes')
@login_required
def access_codes():
    """授权码管理页面"""
    codes = DatabaseManager.get_access_codes(active_only=False)
    return render_template('admin/access_codes.html', codes=codes)

@admin_bp.route('/access-codes/add', methods=['POST'])
@login_required
def add_access_code():
    """添加授权码"""
    try:
        description = request.form.get('description', '手动创建的授权码')
        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')
        
        start_date = None
        end_date = None
        
        if start_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        
        if end_date_str:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
        
        code_info = AccessCodeManager.create_access_code(description, start_date, end_date)
        
        return jsonify({
            'success': True,
            'message': f'授权码"{code_info["code"]}"创建成功！',
            'code': code_info['code']
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'创建失败: {str(e)}'})

@admin_bp.route('/access-codes/delete/<int:code_id>', methods=['POST'])
@login_required
def delete_access_code(code_id):
    """删除授权码"""
    try:
        result = AccessCodeManager.delete_access_code(code_id)
        if result > 0:
            return jsonify({'success': True, 'message': '授权码删除成功！'})
        else:
            return jsonify({'success': False, 'message': '授权码不存在或已删除'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'删除失败: {str(e)}'})

# 用户管理
@admin_bp.route('/users')
@admin_required
def users():
    """用户管理页面"""
    users = DatabaseManager.get_users(active_only=False)
    return render_template('admin/users.html', users=users)

# 系统设置
@admin_bp.route('/settings')
@admin_required
def settings():
    """系统设置页面"""
    return render_template('admin/settings.html')