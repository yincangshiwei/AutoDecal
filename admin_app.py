"""
独立的Flask后台管理应用
运行在7860端口，替代Gradio后台管理界面
"""
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash, send_from_directory
import os
from datetime import datetime
from backend.database import DatabaseManager, init_database
from backend.auth import AuthManager
from routes.admin import register_admin_blueprints

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

# 注册所有管理员蓝图
register_admin_blueprints(app)

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
                INSERT INTO users (username, password_hash, is_admin, is_active, created_time)
                VALUES (?, ?, 1, 1, ?)
            '''
            DatabaseManager.execute_insert(query, ('admin', password_hash, datetime.now()))
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
    print("   2. 支持印花图案、产品、分类、授权码、用户管理")
    print("   3. 适合展会展台展示使用")
    print("=" * 60)
    
    # 启动Flask后台管理应用
    app.run(host='0.0.0.0', port=7860, debug=True, use_reloader=False)