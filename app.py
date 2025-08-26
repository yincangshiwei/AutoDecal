"""
产品印花平台主应用入口
支持前台印花设计和后台管理功能
"""
from flask import Flask, render_template, request, jsonify, send_from_directory, session, redirect, url_for
import os
import threading
import subprocess
import time
import requests
from backend.database import init_database
from frontend.api import create_api_blueprint
from backend.auth import init_auth

app = Flask(__name__)
app.secret_key = 'frontend-secret-key-change-in-production'

# 配置session以避免与后台管理冲突
app.config['SESSION_COOKIE_NAME'] = 'frontend_session'
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
os.makedirs(os.path.join(UPLOAD_FOLDER, 'archives'), exist_ok=True)

# 初始化数据库
init_database()

# 初始化认证系统
init_auth(app)

# 注册API蓝图
try:
    api_bp = create_api_blueprint()
    app.register_blueprint(api_bp, url_prefix='/api')
    print("✓ API蓝图注册成功")
except Exception as e:
    print(f"✗ API蓝图注册失败: {e}")
    import traceback
    traceback.print_exc()

# 添加中间件来跳过ngrok警告页面
@app.after_request
def add_ngrok_skip_header(response):
    """添加ngrok跳过浏览器警告的头部"""
    # 为所有响应添加跳过ngrok警告的头部
    response.headers['ngrok-skip-browser-warning'] = 'true'
    response.headers['X-Custom-User-Agent'] = 'AutoDecal-App/1.0'
    
    # 如果是HTML响应，注入JavaScript自动跳转脚本
    if response.content_type and 'text/html' in response.content_type:
        bypass_script = '''
        <script>
        // 自动跳过ngrok警告页面
        (function() {
            if (window.location.hostname.includes('ngrok') && document.title.includes('ngrok')) {
                const visitButton = document.querySelector('button[onclick*="visit"]') || 
                                  document.querySelector('a[href*="visit"]') ||
                                  document.querySelector('.visit-site');
                if (visitButton) {
                    visitButton.click();
                }
            }
        })();
        </script>
        '''
        
        # 将脚本注入到HTML中
        if hasattr(response, 'data'):
            html_content = response.get_data(as_text=True)
            if '</head>' in html_content:
                html_content = html_content.replace('</head>', bypass_script + '</head>')
                response.set_data(html_content)
    
    return response

# 添加中间件来更新用户活动时间和检查会话状态
@app.before_request
def update_user_activity():
    """更新用户活动时间并检查会话状态"""
    if 'session_id' in session and 'access_code_validated' in session:
        from backend.database import DatabaseManager
        try:
            # 检查会话是否仍然有效（未被强制退出）
            query = "SELECT is_active FROM access_logs WHERE session_id = ?"
            results = DatabaseManager.execute_query(query, (session['session_id'],))
            
            if not results or not results[0]['is_active']:
                # 会话已被强制退出，清除本地会话
                session.clear()
                # 如果是API请求，返回JSON错误
                if request.path.startswith('/api/'):
                    return jsonify({
                        'success': False,
                        'error': '会话已失效',
                        'message': '您的会话已被管理员强制退出，请重新登录',
                        'redirect': '/access-login'
                    }), 401
                # 如果是页面请求，重定向到登录页面
                elif request.path not in ['/access-login', '/verify-access-code', '/']:
                    return redirect(url_for('access_code_login'))
            else:
                # 会话有效，更新活动时间
                DatabaseManager.update_access_log_activity(session['session_id'])
        except Exception as e:
            print(f"检查会话状态失败: {e}")

# 添加登出路由
@app.route('/logout')
def logout():
    """用户登出"""
    if 'session_id' in session:
        from backend.database import DatabaseManager
        try:
            DatabaseManager.logout_access_log(session['session_id'])
        except Exception as e:
            print(f"记录登出时间失败: {e}")
    
    # 清除会话
    session.clear()
    return redirect(url_for('access_code_login'))

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
    import uuid
    import user_agents
    
    access_code = request.form.get('access_code', '').strip()
    redirect_to = request.form.get('redirect_to', 'pattern_editor')
    
    if not access_code:
        return jsonify({'success': False, 'message': '请输入授权码'})
    
    # 直接查询数据库验证授权码
    try:
        query = '''
            SELECT * FROM access_codes 
            WHERE code = ? AND is_active = 1 
            AND (expires_at IS NULL OR expires_at >= datetime('now'))
            AND (max_uses IS NULL OR used_count < max_uses)
        '''
        results = DatabaseManager.execute_query(query, (access_code,))
        
        if results:
            # 更新使用次数
            DatabaseManager.execute_update(
                "UPDATE access_codes SET used_count = used_count + 1 WHERE code = ?", 
                (access_code,)
            )
            
            # 生成会话ID
            session_id = str(uuid.uuid4())
            
            # 获取用户信息
            ip_address = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR', ''))
            user_agent = request.headers.get('User-Agent', '')
            ua = user_agents.parse(user_agent)
            
            browser = f"{ua.browser.family} {ua.browser.version_string}" if ua.browser.family else "Unknown"
            operating_system = f"{ua.os.family} {ua.os.version_string}" if ua.os.family else "Unknown"
            
            # 简单的地理位置信息（这里可以集成IP地理位置API）
            location = "未知地区"  # 可以后续集成IP地理位置服务
            
            # 记录访问日志
            DatabaseManager.add_access_log(
                session_id=session_id,
                access_code=access_code,
                ip_address=ip_address,
                location=location,
                browser=browser,
                operating_system=operating_system
            )
            
            # 设置会话信息
            session['access_code_validated'] = True
            session['access_code'] = access_code
            session['session_id'] = session_id
            
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

def get_ngrok_public_url():
    """获取ngrok公网链接"""
    try:
        response = requests.get('http://localhost:4040/api/tunnels', timeout=5)
        if response.status_code == 200:
            data = response.json()
            tunnels = data.get('tunnels', [])
            
            # 打印调试信息
            print(f"调试: 找到 {len(tunnels)} 个隧道")
            for i, tunnel in enumerate(tunnels):
                print(f"调试: 隧道 {i+1} - 协议: {tunnel.get('proto')}, URL: {tunnel.get('public_url')}")
            
            # 优先返回HTTP，避免HTTPS的警告页面
            for tunnel in tunnels:
                if tunnel.get('proto') == 'http':
                    return tunnel.get('public_url')
            
            # 如果没有HTTP，再返回HTTPS
            for tunnel in tunnels:
                if tunnel.get('proto') == 'https':
                    return tunnel.get('public_url')
                    
            # 如果都没找到，返回第一个可用的
            if tunnels:
                return tunnels[0].get('public_url')
                
        return None
    except Exception as e:
        print(f"调试: 获取ngrok链接时出错: {e}")
        return None

def setup_ngrok_tunnel(port=5000):
    """设置ngrok隧道并获取公网链接"""
    try:
        # 检查ngrok是否已安装
        result = subprocess.run(['ngrok', 'version'], capture_output=True, text=True)
        if result.returncode != 0:
            print("⚠️  ngrok未安装，无法创建外部链接")
            print("   请访问 https://ngrok.com/ 下载并安装ngrok")
            return None
        
        print("🌐 正在启动ngrok隧道...")
        print("   这可能需要几秒钟时间...")
        
        # 启动ngrok隧道（后台运行）- 同时生成HTTP和HTTPS隧道
        ngrok_cmd = ['ngrok', 'http', str(port), '--host-header=rewrite']
        print(f"调试: 执行命令: {' '.join(ngrok_cmd)}")
        
        ngrok_process = subprocess.Popen(
            ngrok_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # 给ngrok一些时间启动
        time.sleep(8)
        
        # 检查ngrok进程是否正常运行
        if ngrok_process.poll() is not None:
            stdout, stderr = ngrok_process.communicate()
            print(f"调试: ngrok进程异常退出")
            print(f"调试: stdout: {stdout}")
            print(f"调试: stderr: {stderr}")
            return None
        else:
            print("调试: ngrok进程正在运行")
        
        # 尝试获取公网链接
        public_url = None
        max_attempts = 10
        for attempt in range(max_attempts):
            public_url = get_ngrok_public_url()
            if public_url:
                break
            time.sleep(1)
        
        print("=" * 60)
        print("🌍 ngrok隧道已启动！")
        print("=" * 60)
        print(f"🏠 本地访问: http://localhost:{port}")
        
        if public_url:
            print(f"🔗 公网链接: {public_url}")
            print("   可以直接分享此链接给其他人访问")
            print("   ✓ 已同时生成HTTP和HTTPS隧道:")
            print("     - --scheme=http,https (同时支持两种协议)")
            print("     - --host-header=rewrite (重写主机头)")
            print("     - HTTP响应头: ngrok-skip-browser-warning")
            print("     - JavaScript自动跳转脚本")
            print("   💡 提示: HTTP链接无警告页面，HTTPS链接更安全")
        else:
            print("🔗 公网链接: 获取失败，请访问 http://localhost:4040 查看")
            print("   或在新终端运行: curl http://localhost:4040/api/tunnels")
        
        print("=" * 60)
        
        return public_url, ngrok_process
            
    except FileNotFoundError:
        print("⚠️  ngrok未找到，请确保已安装并添加到PATH")
        print("   下载地址: https://ngrok.com/download")
        return None
    except Exception as e:
        print(f"⚠️  启动ngrok失败: {e}")
        return None

def start_flask_with_share(share=False, port=5000):
    """启动Flask应用，支持外部分享"""
    ngrok_process = None
    public_url = None
    
    if share:
        result = setup_ngrok_tunnel(port)
        if result:
            public_url, ngrok_process = result
            
            # 如果成功获取到公网链接，启动定时检查线程
            if public_url and ngrok_process:
                def monitor_ngrok():
                    """监控ngrok状态并更新公网链接"""
                    current_public_url = public_url
                    while ngrok_process and ngrok_process.poll() is None:
                        time.sleep(30)  # 每30秒检查一次
                        new_url = get_ngrok_public_url()
                        if new_url and new_url != current_public_url:
                            print(f"\n🔄 公网链接已更新: {new_url}")
                            current_public_url = new_url
                
                # 启动监控线程
                monitor_thread = threading.Thread(target=monitor_ngrok, daemon=True)
                monitor_thread.start()
    
    try:
        # 启动Flask应用
        app.run(host='0.0.0.0', port=port, debug=True, use_reloader=False)
    except KeyboardInterrupt:
        print("\n🛑 正在关闭服务器...")
    finally:
        # 清理ngrok进程
        if ngrok_process:
            print("🔄 正在关闭外部链接...")
            ngrok_process.terminate()
            ngrok_process.wait()
            print("✅ 外部链接已关闭")

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
    print("-" * 60)
    
    # 检查是否启用外部分享
    import sys
    share_enabled = '--share' in sys.argv or '-s' in sys.argv
    
    if share_enabled:
        print("🌐 外部分享模式已启用")
        print("   正在创建公网访问链接...")
    
    # 启动Flask前台应用（支持外部分享）
    start_flask_with_share(share=share_enabled, port=5000)
