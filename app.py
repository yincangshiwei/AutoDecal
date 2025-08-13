"""
产品印花平台主应用入口
支持前台印花设计和后台管理功能
"""
from flask import Flask, render_template, request, jsonify, send_from_directory, session, redirect, url_for
import os
import threading
from backend.gradio_admin import create_admin_interface
from backend.database import init_database
from frontend.api import create_api_blueprint
from backend.auth import init_auth

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-in-production'

# 配置上传文件夹
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# 确保上传目录存在
os.makedirs(os.path.join(UPLOAD_FOLDER, 'patterns'), exist_ok=True)
os.makedirs(os.path.join(UPLOAD_FOLDER, 'products'), exist_ok=True)
os.makedirs(os.path.join(UPLOAD_FOLDER, 'depth_maps'), exist_ok=True)

# 初始化数据库
init_database()

# 初始化认证系统
init_auth(app)

# 注册API蓝图
api_bp = create_api_blueprint()
app.register_blueprint(api_bp, url_prefix='/api')

# Flask后台管理已移至独立应用 admin_app.py (运行在7860端口)

@app.route('/')
def home():
    """首页 - 直接跳转到印花编辑器"""
    # 检查是否已通过授权码验证
    if 'access_code_validated' not in session:
        return redirect(url_for('access_code_login', redirect_to='pattern_editor'))
    return redirect(url_for('pattern_editor'))

@app.route('/design')
def design():
    """完整设计界面"""
    return render_template('index.html')

@app.route('/pattern-editor')
def pattern_editor():
    """印花图案贴合编辑器页面"""
    # 检查是否已通过授权码验证
    if 'access_code_validated' not in session:
        return redirect(url_for('access_code_login', redirect_to='pattern_editor'))
    return render_template('pattern_editor.html')

@app.route('/access-login')
def access_code_login():
    """授权码登录页面"""
    redirect_to = request.args.get('redirect_to', 'pattern_editor')
    return render_template('access_login.html', redirect_to=redirect_to)

@app.route('/verify-access-code', methods=['POST'])
def verify_access_code():
    """验证授权码"""
    from backend.auth import AccessCodeManager
    from backend.database import DatabaseManager
    
    access_code = request.form.get('access_code', '').strip()
    redirect_to = request.form.get('redirect_to', 'pattern_editor')
    
    if not access_code:
        return jsonify({'success': False, 'message': '请输入授权码'})
    
    # 直接查询数据库验证授权码
    try:
        query = '''
            SELECT * FROM access_codes 
            WHERE code = ? AND is_active = 1 
            AND (start_date IS NULL OR start_date <= datetime('now'))
            AND (end_date IS NULL OR end_date >= datetime('now'))
        '''
        results = DatabaseManager.execute_query(query, (access_code,))
        
        if results:
            # 更新使用次数
            DatabaseManager.execute_update(
                "UPDATE access_codes SET usage_count = usage_count + 1 WHERE code = ?", 
                (access_code,)
            )
            
            session['access_code_validated'] = True
            session['access_code'] = access_code
            return jsonify({'success': True, 'redirect_url': url_for(redirect_to)})
        else:
            return jsonify({'success': False, 'message': '授权码无效或已过期'})
            
    except Exception as e:
        print(f"授权码验证错误: {e}")
        return jsonify({'success': False, 'message': '验证失败，请重试'})

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    """提供上传文件的访问"""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# Gradio后台管理已移至独立应用 admin_app.py (运行在7860端口)
# 不再在主应用中启动后台管理界面

def initialize_default_data():
    """初始化默认数据"""
    from backend.auth import AuthManager, AccessCodeManager
    from backend.database import DatabaseManager
    from datetime import datetime, timedelta
    
    # 检查并创建默认管理员账户
    try:
        existing_admin = DatabaseManager.execute_query("SELECT * FROM users WHERE username = 'admin'")
        if not existing_admin:
            # 创建默认管理员账户
            AuthManager.create_user(
                username='admin',
                password='admin123',
                is_admin=True,
                permissions={'all': True}
            )
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
                INSERT INTO access_codes (code, description, start_date, end_date, is_active)
                VALUES (?, ?, NULL, NULL, 1)
            '''
            DatabaseManager.execute_insert(query, ('TEST2024', '永久测试授权码'))
            print("✓ 创建永久测试授权码: TEST2024")
        
        return "TEST2024"
    except Exception as e:
        print(f"✗ 初始化授权码失败: {e}")
        return "TEST2024"

if __name__ == '__main__':
    # 初始化默认数据
    temp_access_code = initialize_default_data()
    
    print("=" * 60)
    print("🎨 产品印花平台前台启动成功！")
    print("=" * 60)
    print("📱 前台界面: http://localhost:5000")
    print("⚙️  后台管理: 请单独运行 python admin_app.py (端口7860)")
    print("-" * 60)
    print("🎫 前台访问授权码:")
    print(f"   授权码: {temp_access_code}")
    
    # 启动Flask前台应用
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
