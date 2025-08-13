"""
独立的Flask后台管理应用
运行在7860端口，替代Gradio后台管理界面
"""
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash, send_from_directory
from werkzeug.utils import secure_filename
import os
import shutil
from datetime import datetime, timedelta
from PIL import Image
from backend.database import DatabaseManager, init_database
from backend.auth import AuthManager, AccessCodeManager
from backend.models import Pattern, Product, ProductCategory, AccessCode, ThemeTemplate

# 创建独立的Flask应用
app = Flask(__name__)
app.secret_key = 'admin-backend-secret-key-change-in-production'

# 配置session以避免与前台冲突
app.config['SESSION_COOKIE_NAME'] = 'admin_session'
app.config['SESSION_COOKIE_PATH'] = '/'
app.config['SESSION_COOKIE_DOMAIN'] = None
app.config['SESSION_COOKIE_SECURE'] = False
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# 配置上传文件夹
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# 确保上传目录存在
os.makedirs(os.path.join(UPLOAD_FOLDER, 'patterns'), exist_ok=True)
os.makedirs(os.path.join(UPLOAD_FOLDER, 'products'), exist_ok=True)
os.makedirs(os.path.join(UPLOAD_FOLDER, 'depth_maps'), exist_ok=True)

# 初始化数据库
init_database()

# 登录检查装饰器
def login_required(f):
    def decorated_function(*args, **kwargs):
        if 'admin_user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

def admin_required(f):
    def decorated_function(*args, **kwargs):
        if 'admin_user_id' not in session:
            return redirect(url_for('login'))
        # 这里可以添加额外的管理员权限检查
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

# 主页和登录路由
@app.route('/')
def index():
    """后台管理首页"""
    if 'admin_user_id' not in session:
        return redirect(url_for('login'))
    
    # 获取统计数据
    try:
        patterns = DatabaseManager.get_patterns() or []
        products = DatabaseManager.get_products() or []
        categories = DatabaseManager.get_categories() or []
        access_codes = DatabaseManager.get_access_codes() or []
        users = DatabaseManager.get_users() or []
        
        stats = {
            'patterns_count': len(patterns),
            'products_count': len(products),
            'categories_count': len(categories),
            'access_codes_count': len(access_codes),
            'users_count': len(users)
        }
    except Exception as e:
        print(f"获取统计数据失败: {e}")
        stats = {
            'patterns_count': 0,
            'products_count': 0,
            'categories_count': 0,
            'access_codes_count': 0,
            'users_count': 0
        }
    
    return render_template('admin/dashboard.html', stats=stats)

@app.route('/login', methods=['GET', 'POST'])
def login():
    """管理员登录"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        try:
            # 验证管理员账户
            query = "SELECT * FROM users WHERE username = ? AND is_admin = 1"
            results = DatabaseManager.execute_query(query, (username,))
            
            if results:
                user = results[0]
                # 验证密码
                if AuthManager.verify_password(password, user['password_hash']):
                    session['admin_user_id'] = user['id']
                    session['admin_username'] = user['username']
                    flash('登录成功！', 'success')
                    return redirect(url_for('index'))
                else:
                    flash('用户名或密码错误', 'error')
            else:
                flash('用户名或密码错误，或您没有管理员权限', 'error')
        except Exception as e:
            print(f"登录验证失败: {e}")
            flash('登录失败，请重试', 'error')
    
    return render_template('admin/login.html')

@app.route('/logout')
def logout():
    """管理员登出"""
    session.pop('admin_user_id', None)
    session.pop('admin_username', None)
    flash('已退出登录', 'info')
    return redirect(url_for('login'))

# 印花图案管理
@app.route('/patterns')
@login_required
def patterns():
    """印花图案管理页面"""
    try:
        patterns = DatabaseManager.get_patterns() or []
    except Exception as e:
        print(f"获取印花图案失败: {e}")
        patterns = []
    return render_template('admin/patterns.html', patterns=patterns)

@app.route('/patterns/add', methods=['POST'])
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

@app.route('/patterns/get')
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

@app.route('/patterns/update', methods=['POST'])
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
            filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"pattern_{timestamp}_{filename}"
            
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

@app.route('/patterns/delete', methods=['POST'])
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

@app.route('/patterns/clear', methods=['POST'])
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

# 产品管理
@app.route('/products')
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

@app.route('/products/add', methods=['POST'])
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
        
        # 创建产品记录 - 使用正确的数据库字段名
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

@app.route('/products/get')
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

@app.route('/products/update', methods=['POST'])
@login_required
def update_product():
    """更新产品"""
    try:
        # 支持表单数据和文件上传
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

@app.route('/products/delete', methods=['POST'])
@login_required
def delete_product():
    """删除产品"""
    try:
        data = request.get_json()
        product_id = data.get('id')
        
        if not product_id:
            return jsonify({'success': False, 'message': '缺少产品ID'})
        
        # 获取文件路径并删除文件 - 使用正确的字段名
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

@app.route('/products/clear', methods=['POST'])
@login_required
def clear_products():
    """清空所有产品"""
    try:
        # 获取所有产品文件路径
        query = "SELECT image_path, depth_map_path FROM products"
        results = DatabaseManager.execute_query(query)
        
        # 删除文件
        for row in results:
            image_path = os.path.join('uploads', 'products', row['image_path'])
            depth_path = os.path.join('uploads', 'depth_maps', row['depth_map_path'])
            
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

# 分类管理
@app.route('/categories')
@login_required
def categories():
    """分类管理页面"""
    try:
        categories = DatabaseManager.get_categories() or []
    except Exception as e:
        print(f"获取分类数据失败: {e}")
        categories = []
    return render_template('admin/categories.html', categories=categories)

@app.route('/categories/add', methods=['POST'])
@login_required
def add_category():
    """添加分类"""
    try:
        data = request.get_json()
        name = data.get('name')
        
        if not name:
            return jsonify({'success': False, 'message': '请输入分类名称'})
        
        query = '''
            INSERT INTO product_categories (name, created_time)
            VALUES (?, ?)
        '''
        category_id = DatabaseManager.execute_insert(query, (name, datetime.now()))
        
        return jsonify({
            'success': True,
            'message': f'分类"{name}"添加成功！',
            'category_id': category_id
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'添加失败: {str(e)}'})

@app.route('/categories/get')
@login_required
def get_category():
    """获取单个分类信息"""
    try:
        category_id = request.args.get('id', type=int)
        if not category_id:
            return jsonify({'success': False, 'message': '缺少分类ID'})
        
        query = "SELECT * FROM product_categories WHERE id = ?"
        results = DatabaseManager.execute_query(query, (category_id,))
        
        if results:
            category = dict(results[0])
            return jsonify({'success': True, 'data': category})
        else:
            return jsonify({'success': False, 'message': '分类不存在'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'获取失败: {str(e)}'})

@app.route('/categories/update', methods=['POST'])
@login_required
def update_category():
    """更新分类"""
    try:
        data = request.get_json()
        category_id = data.get('id')
        name = data.get('name')
        
        if not category_id or not name:
            return jsonify({'success': False, 'message': '缺少必要参数'})
        
        query = "UPDATE product_categories SET name = ? WHERE id = ?"
        result = DatabaseManager.execute_update(query, (name, category_id))
        
        if result > 0:
            return jsonify({'success': True, 'message': '分类更新成功！'})
        else:
            return jsonify({'success': False, 'message': '分类不存在或更新失败'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'更新失败: {str(e)}'})

@app.route('/categories/delete', methods=['POST'])
@login_required
def delete_category():
    """删除分类"""
    try:
        data = request.get_json()
        category_id = data.get('id')
        
        if not category_id:
            return jsonify({'success': False, 'message': '缺少分类ID'})
        
        # 删除数据库记录
        query = "DELETE FROM product_categories WHERE id = ?"
        result = DatabaseManager.execute_update(query, (category_id,))
        
        if result > 0:
            return jsonify({'success': True, 'message': '分类删除成功！'})
        else:
            return jsonify({'success': False, 'message': '分类不存在或已删除'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'删除失败: {str(e)}'})

# 授权码管理
@app.route('/access-codes')
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
                    # 如果已经是datetime对象，保持不变
                
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

@app.route('/access-codes/add', methods=['POST'])
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

@app.route('/access-codes/get')
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

@app.route('/access-codes/update', methods=['POST'])
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

@app.route('/access-codes/delete', methods=['POST'])
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

@app.route('/access-codes/toggle-status', methods=['POST'])
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

# 用户管理
@app.route('/users')
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

@app.route('/users/add', methods=['POST'])
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

@app.route('/users/get')
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

@app.route('/users/update', methods=['POST'])
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

@app.route('/users/delete', methods=['POST'])
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

@app.route('/users/toggle-status', methods=['POST'])
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

# 主题管理
@app.route('/themes')
@login_required
def themes():
    """主题管理页面"""
    try:
        query = "SELECT * FROM themes ORDER BY created_time DESC"
        results = DatabaseManager.execute_query(query)
        themes = [dict(row) for row in results] if results else []
    except Exception as e:
        print(f"获取主题数据失败: {e}")
        themes = []
    return render_template('admin/themes.html', themes=themes)

@app.route('/themes/add', methods=['POST'])
@login_required
def add_theme():
    """添加主题"""
    try:
        data = request.get_json()
        name = data.get('name')
        season = data.get('season', '')
        description = data.get('description', '')
        primary_color = data.get('primary_color', '#007bff')
        secondary_color = data.get('secondary_color', '#6c757d')
        accent_color = data.get('accent_color', '#28a745')
        is_active = data.get('is_active', True)
        
        if not name:
            return jsonify({'success': False, 'message': '请输入主题名称'})
        
        query = '''
            INSERT INTO themes (name, season, description, primary_color, secondary_color, accent_color, is_active, created_time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        '''
        theme_id = DatabaseManager.execute_insert(query, (
            name, season, description, primary_color, secondary_color, accent_color, is_active, datetime.now()
        ))
        
        return jsonify({
            'success': True,
            'message': f'主题"{name}"添加成功！',
            'theme_id': theme_id
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'添加失败: {str(e)}'})

@app.route('/themes/get')
@login_required
def get_theme():
    """获取单个主题信息"""
    try:
        theme_id = request.args.get('id', type=int)
        if not theme_id:
            return jsonify({'success': False, 'message': '缺少主题ID'})
        
        query = "SELECT * FROM themes WHERE id = ?"
        results = DatabaseManager.execute_query(query, (theme_id,))
        
        if results:
            theme = dict(results[0])
            return jsonify({'success': True, 'data': theme})
        else:
            return jsonify({'success': False, 'message': '主题不存在'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'获取失败: {str(e)}'})

@app.route('/themes/update', methods=['POST'])
@login_required
def update_theme():
    """更新主题"""
    try:
        data = request.get_json()
        theme_id = data.get('id')
        name = data.get('name')
        season = data.get('season', '')
        description = data.get('description', '')
        primary_color = data.get('primary_color')
        secondary_color = data.get('secondary_color')
        accent_color = data.get('accent_color')
        is_active = data.get('is_active', True)
        
        if not theme_id or not name:
            return jsonify({'success': False, 'message': '缺少必要参数'})
        
        query = '''
            UPDATE themes 
            SET name = ?, season = ?, description = ?, primary_color = ?, secondary_color = ?, accent_color = ?, is_active = ?
            WHERE id = ?
        '''
        result = DatabaseManager.execute_update(query, (
            name, season, description, primary_color, secondary_color, accent_color, is_active, theme_id
        ))
        
        if result > 0:
            return jsonify({'success': True, 'message': '主题更新成功！'})
        else:
            return jsonify({'success': False, 'message': '主题不存在或更新失败'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'更新失败: {str(e)}'})

@app.route('/themes/delete', methods=['POST'])
@login_required
def delete_theme():
    """删除主题"""
    try:
        data = request.get_json()
        theme_id = data.get('id')
        
        if not theme_id:
            return jsonify({'success': False, 'message': '缺少主题ID'})
        
        query = "DELETE FROM themes WHERE id = ?"
        result = DatabaseManager.execute_update(query, (theme_id,))
        
        if result > 0:
            return jsonify({'success': True, 'message': '主题删除成功！'})
        else:
            return jsonify({'success': False, 'message': '主题不存在或已删除'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'删除失败: {str(e)}'})

@app.route('/themes/toggle-status', methods=['POST'])
@login_required
def toggle_theme_status():
    """切换主题状态"""
    try:
        data = request.get_json()
        theme_id = data.get('id')
        is_active = data.get('is_active')
        
        if not theme_id or is_active is None:
            return jsonify({'success': False, 'message': '缺少必要参数'})
        
        query = "UPDATE themes SET is_active = ? WHERE id = ?"
        result = DatabaseManager.execute_update(query, (is_active, theme_id))
        
        if result > 0:
            action = '启用' if is_active else '禁用'
            return jsonify({'success': True, 'message': f'主题{action}成功！'})
        else:
            return jsonify({'success': False, 'message': '主题不存在或操作失败'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'操作失败: {str(e)}'})

# 系统设置
@app.route('/settings')
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

@app.route('/settings/backup-database', methods=['POST'])
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

@app.route('/settings/clear-uploads', methods=['POST'])
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

@app.route('/settings/reset-database', methods=['POST'])
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
        tables = ['patterns', 'products', 'product_categories', 'access_codes', 'theme_templates']
        for table in tables:
            DatabaseManager.execute_update(f"DELETE FROM {table}")
        
        # 重新初始化默认数据
        initialize_default_data()
        
        return jsonify({
            'success': True,
            'message': f'数据库重置成功！原数据已备份为：{backup_filename}'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'重置失败: {str(e)}'})

# 静态文件服务
@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    """提供上传文件的访问"""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/static/<path:filename>')
def static_files(filename):
    """提供静态文件访问"""
    return send_from_directory('static', filename)

def initialize_default_data():
    """初始化默认数据"""
    # 检查并创建默认管理员账户
    try:
        existing_admin = DatabaseManager.execute_query("SELECT * FROM users WHERE username = 'admin'")
        if not existing_admin:
            # 创建默认管理员账户
            password_hash = AuthManager.hash_password('admin123')
            query = '''
                INSERT INTO users (username, email, password_hash, is_admin, is_active, created_time)
                VALUES (?, ?, ?, 1, 1, ?)
            '''
            DatabaseManager.execute_insert(query, ('admin', 'admin@example.com', password_hash, datetime.now()))
            print("✓ 默认管理员账户已创建")
        else:
            # 更新现有管理员密码为正确的哈希值
            password_hash = AuthManager.hash_password('admin123')
            DatabaseManager.execute_update(
                "UPDATE users SET password_hash = ? WHERE username = 'admin'",
                (password_hash,)
            )
            print("✓ 管理员账户密码已更新")
    except Exception as e:
        print(f"✗ 初始化管理员账户失败: {e}")
    
    # 确保有可用的授权码
    try:
        # 检查是否已有TEST2024授权码
        existing_codes = DatabaseManager.execute_query(
            "SELECT * FROM access_codes WHERE code = 'TEST2024' AND is_active = 1"
        )
        
        if not existing_codes:
            # 创建TEST2024授权码
            query = '''
                INSERT INTO access_codes (code, description, is_active, created_time)
                VALUES (?, ?, 1, ?)
            '''
            DatabaseManager.execute_insert(query, ('TEST2024', '永久测试授权码', datetime.now()))
            print("✓ 创建永久测试授权码: TEST2024")
        
        return "TEST2024"
    except Exception as e:
        print(f"✗ 初始化授权码失败: {e}")
        return "TEST2024"

if __name__ == '__main__':
    # 初始化默认数据
    temp_access_code = initialize_default_data()
    
    print("=" * 60)
    print("🎨 产品印花平台后台管理系统启动成功！")
    print("=" * 60)
    print("⚙️  后台管理: http://localhost:7860")
    print("-" * 60)
    print("🔐 后台管理登录信息:")
    print(f"   账号: admin")
    print(f"   密码: admin123")
    print("-" * 60)
    print("🎫 前台访问授权码:")
    print(f"   授权码: {temp_access_code}")
    print("=" * 60)
    print("💡 使用说明:")
    print("   1. 访问后台管理界面进行图案和产品管理")
    print("   2. 支持印花图案、产品、分类、授权码、用户、主题管理")
    print("   3. 适合展会展台展示使用")
    print("=" * 60)
    
    # 启动Flask后台管理应用
    app.run(host='0.0.0.0', port=7860, debug=True, use_reloader=False)
