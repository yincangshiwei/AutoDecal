from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from werkzeug.utils import secure_filename
import os
from datetime import datetime
from PIL import Image
from backend.database import DatabaseManager

products_bp = Blueprint('admin_products', __name__, url_prefix='/admin/products')

def login_required(f):
    def decorated_function(*args, **kwargs):
        from flask import session
        if 'admin_user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

@products_bp.route('/')
@login_required
def products():
    """产品管理页面"""
    try:
        products = DatabaseManager.get_products() or []
        categories = DatabaseManager.get_categories() or []
    except Exception as e:
        print(f"获取产品数据失败: {e}")
        products = []
        categories = []
    return render_template('admin/products.html', products=products, categories=categories)

@products_bp.route('/add', methods=['POST'])
@login_required
def add_product():
    """添加产品"""
    try:
        name = request.form.get('name')
        category_id = request.form.get('category_id', type=int)
        
        if not name or not category_id:
            return jsonify({'success': False, 'message': '请填写完整的产品信息'})
        
        if 'image' not in request.files or 'depth_map' not in request.files:
            return jsonify({'success': False, 'message': '请上传产品图和深度图'})
        
        product_file = request.files['image']
        depth_file = request.files['depth_map']
        
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
        query = '''
            INSERT INTO products (title, category_id, product_image, depth_image, product_image_path, depth_image_path, image_width, image_height, upload_time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        '''
        product_id = DatabaseManager.execute_insert(query, (
            name, category_id, product_filename, depth_filename, product_filename, depth_filename, width, height, datetime.now()
        ))
        
        return jsonify({
            'success': True,
            'message': f'产品"{name}"添加成功！',
            'product_id': product_id
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'添加失败: {str(e)}'})

@products_bp.route('/get')
@login_required
def get_product():
    """获取单个产品信息"""
    try:
        product_id = request.args.get('id', type=int)
        if not product_id:
            return jsonify({'success': False, 'message': '缺少产品ID'})
        
        query = "SELECT *, title as name FROM products WHERE id = ?"
        results = DatabaseManager.execute_query(query, (product_id,))
        
        if results:
            product = dict(results[0])
            return jsonify({'success': True, 'data': product})
        else:
            return jsonify({'success': False, 'message': '产品不存在'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'获取失败: {str(e)}'})

@products_bp.route('/update', methods=['POST'])
@login_required
def update_product():
    """更新产品"""
    try:
        product_id = request.form.get('id', type=int)
        name = request.form.get('name')
        category_id = request.form.get('category_id', type=int)
        
        if not product_id or not name or not category_id:
            return jsonify({'success': False, 'message': '缺少必要参数'})
        
        # 构建更新字段和参数
        update_fields = ["title = ?", "category_id = ?"]
        params = [name, category_id]
        
        # 处理产品图片上传
        if 'image' in request.files and request.files['image'].filename != '':
            product_file = request.files['image']
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            product_filename = f"product_{timestamp}_{secure_filename(product_file.filename)}"
            product_path = os.path.join('uploads', 'products', product_filename)
            
            os.makedirs(os.path.dirname(product_path), exist_ok=True)
            product_file.save(product_path)
            
            # 获取图片尺寸
            with Image.open(product_path) as img:
                width, height = img.size
            
            update_fields.extend([
                "product_image = ?", 
                "product_image_path = ?",
                "image_width = ?",
                "image_height = ?"
            ])
            params.extend([product_filename, product_filename, width, height])
        
        # 处理深度图上传
        if 'depth_map' in request.files and request.files['depth_map'].filename != '':
            depth_file = request.files['depth_map']
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            depth_filename = f"depth_{timestamp}_{secure_filename(depth_file.filename)}"
            depth_path = os.path.join('uploads', 'depth_maps', depth_filename)
            
            os.makedirs(os.path.dirname(depth_path), exist_ok=True)
            depth_file.save(depth_path)
            
            update_fields.extend([
                "depth_image = ?",
                "depth_image_path = ?"
            ])
            params.extend([depth_filename, depth_filename])
        
        # 添加产品ID到参数末尾
        params.append(product_id)
        
        # 构建完整的更新查询
        query = f"UPDATE products SET {', '.join(update_fields)} WHERE id = ?"
        
        result = DatabaseManager.execute_update(query, tuple(params))
        
        if result > 0:
            return jsonify({'success': True, 'message': '产品更新成功！'})
        else:
            return jsonify({'success': False, 'message': '产品不存在或更新失败'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'更新失败: {str(e)}'})

@products_bp.route('/delete', methods=['POST'])
@login_required
def delete_product():
    """删除产品"""
    try:
        data = request.get_json()
        product_id = data.get('id')
        
        if not product_id:
            return jsonify({'success': False, 'message': '缺少产品ID'})
        
        # 获取文件路径并删除文件
        query = "SELECT product_image_path, depth_image_path FROM products WHERE id = ?"
        results = DatabaseManager.execute_query(query, (product_id,))
        
        if results:
            product = results[0]
            image_path = os.path.join('uploads', 'products', product['product_image_path'])
            depth_path = os.path.join('uploads', 'depth_maps', product['depth_image_path'])
            
            if os.path.exists(image_path):
                os.remove(image_path)
            if os.path.exists(depth_path):
                os.remove(depth_path)
        
        # 删除数据库记录
        query = "DELETE FROM products WHERE id = ?"
        result = DatabaseManager.execute_update(query, (product_id,))
        
        if result > 0:
            return jsonify({'success': True, 'message': '产品删除成功！'})
        else:
            return jsonify({'success': False, 'message': '产品不存在或已删除'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'删除失败: {str(e)}'})

@products_bp.route('/clear', methods=['POST'])
@login_required
def clear_products():
    """清空所有产品"""
    try:
        # 获取所有产品文件路径
        query = "SELECT product_image_path, depth_image_path FROM products"
        results = DatabaseManager.execute_query(query)
        
        # 删除文件
        for row in results:
            image_path = os.path.join('uploads', 'products', row['product_image_path'])
            depth_path = os.path.join('uploads', 'depth_maps', row['depth_image_path'])
            
            if os.path.exists(image_path):
                os.remove(image_path)
            if os.path.exists(depth_path):
                os.remove(depth_path)
        
        # 清空数据库记录
        query = "DELETE FROM products"
        result = DatabaseManager.execute_update(query)
        
        return jsonify({'success': True, 'message': f'已清空所有产品，共 {result} 个'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'清空失败: {str(e)}'})