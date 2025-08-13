#!/usr/bin/env python3
"""
主题管理Web界面
基于Flask的简单主题管理界面
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for
import os
import sys
sys.path.append('.')

from backend.database import init_database
from backend.theme_manager import ThemeManager

app = Flask(__name__)
app.secret_key = 'theme_admin_secret_key'

# 初始化数据库和主题管理器
init_database()
theme_manager = ThemeManager()

@app.route('/')
def index():
    """主题管理首页"""
    themes = theme_manager.get_available_themes()
    current_theme = theme_manager.get_current_theme()
    
    return f"""
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>主题管理系统</title>
        <style>
            body {{
                font-family: 'Microsoft YaHei', sans-serif;
                margin: 0;
                padding: 20px;
                background-color: #f5f5f5;
            }}
            .container {{
                max-width: 1200px;
                margin: 0 auto;
                background: white;
                padding: 30px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }}
            h1 {{
                color: #333;
                text-align: center;
                margin-bottom: 30px;
            }}
            .current-theme {{
                background: #e3f2fd;
                padding: 15px;
                border-radius: 8px;
                margin-bottom: 30px;
                text-align: center;
            }}
            .theme-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }}
            .theme-card {{
                border: 2px solid #ddd;
                border-radius: 10px;
                padding: 20px;
                text-align: center;
                transition: all 0.3s ease;
            }}
            .theme-card:hover {{
                border-color: #1976d2;
                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            }}
            .theme-card.active {{
                border-color: #4caf50;
                background-color: #f1f8e9;
            }}
            .theme-name {{
                font-size: 1.2em;
                font-weight: bold;
                margin-bottom: 10px;
                color: #333;
            }}
            .theme-description {{
                color: #666;
                margin-bottom: 15px;
                line-height: 1.4;
            }}
            .theme-colors {{
                display: flex;
                justify-content: center;
                gap: 10px;
                margin-bottom: 15px;
            }}
            .color-box {{
                width: 30px;
                height: 30px;
                border-radius: 50%;
                border: 2px solid #fff;
                box-shadow: 0 2px 4px rgba(0,0,0,0.2);
            }}
            .theme-decorations {{
                font-size: 1.5em;
                margin-bottom: 15px;
            }}
            .btn {{
                background: #1976d2;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                cursor: pointer;
                font-size: 14px;
                transition: background 0.3s ease;
            }}
            .btn:hover {{
                background: #1565c0;
            }}
            .btn.active {{
                background: #4caf50;
            }}
            .btn:disabled {{
                background: #ccc;
                cursor: not-allowed;
            }}
            .actions {{
                text-align: center;
                margin-top: 30px;
            }}
            .status {{
                margin-top: 20px;
                padding: 10px;
                border-radius: 5px;
                text-align: center;
            }}
            .status.success {{
                background: #d4edda;
                color: #155724;
                border: 1px solid #c3e6cb;
            }}
            .status.error {{
                background: #f8d7da;
                color: #721c24;
                border: 1px solid #f5c6cb;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎨 主题管理系统</h1>
            
            <div class="current-theme">
                <h3>当前激活主题: <span style="color: #1976d2;">{current_theme}</span></h3>
            </div>
            
            <div class="theme-grid">
                {''.join([f'''
                <div class="theme-card {'active' if theme['id'] == current_theme else ''}">
                    <div class="theme-name">{theme['name']}</div>
                    <div class="theme-description">{theme['description']}</div>
                    <div class="theme-colors">
                        <div class="color-box" style="background-color: {theme['primary_color']}" title="主色调"></div>
                        <div class="color-box" style="background-color: {theme['secondary_color']}" title="辅助色"></div>
                        <div class="color-box" style="background-color: {theme['accent_color']}" title="强调色"></div>
                    </div>
                    <div class="theme-decorations">{''.join(theme['decorations'])}</div>
                    <button class="btn {'active' if theme['id'] == current_theme else ''}" 
                            onclick="setTheme('{theme['id']}')"
                            {'disabled' if theme['id'] == current_theme else ''}>
                        {'当前主题' if theme['id'] == current_theme else '切换主题'}
                    </button>
                </div>
                ''' for theme in themes])}
            </div>
            
            <div class="actions">
                <button class="btn" onclick="refreshPage()">🔄 刷新页面</button>
                <button class="btn" onclick="showCreateForm()">➕ 创建自定义主题</button>
            </div>
            
            <div id="status"></div>
        </div>
        
        <script>
            function setTheme(themeId) {{
                fetch('/set_theme', {{
                    method: 'POST',
                    headers: {{
                        'Content-Type': 'application/json',
                    }},
                    body: JSON.stringify({{theme_id: themeId}})
                }})
                .then(response => response.json())
                .then(data => {{
                    if (data.success) {{
                        showStatus('主题切换成功！', 'success');
                        setTimeout(() => location.reload(), 1000);
                    }} else {{
                        showStatus('主题切换失败: ' + data.message, 'error');
                    }}
                }})
                .catch(error => {{
                    showStatus('请求失败: ' + error, 'error');
                }});
            }}
            
            function refreshPage() {{
                location.reload();
            }}
            
            function showCreateForm() {{
                alert('自定义主题创建功能开发中...');
            }}
            
            function showStatus(message, type) {{
                const statusDiv = document.getElementById('status');
                statusDiv.innerHTML = message;
                statusDiv.className = 'status ' + type;
                setTimeout(() => {{
                    statusDiv.innerHTML = '';
                    statusDiv.className = '';
                }}, 3000);
            }}
        </script>
    </body>
    </html>
    """

@app.route('/set_theme', methods=['POST'])
def set_theme():
    """设置主题"""
    try:
        data = request.get_json()
        theme_id = data.get('theme_id')
        
        if not theme_id:
            return jsonify({'success': False, 'message': '主题ID不能为空'})
        
        success = theme_manager.set_active_theme(theme_id)
        
        if success:
            return jsonify({'success': True, 'message': '主题设置成功'})
        else:
            return jsonify({'success': False, 'message': '主题设置失败'})
    
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/themes')
def api_themes():
    """获取主题列表API"""
    try:
        themes = theme_manager.get_available_themes()
        current_theme = theme_manager.get_current_theme()
        
        return jsonify({
            'success': True,
            'themes': themes,
            'current_theme': current_theme
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/theme/<theme_id>')
def api_theme_config(theme_id):
    """获取特定主题配置API"""
    try:
        config = theme_manager.get_theme_config(theme_id)
        css_path = theme_manager.get_theme_css_path(theme_id)
        
        return jsonify({
            'success': True,
            'config': config,
            'css_path': css_path
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

if __name__ == '__main__':
    print("启动主题管理系统...")
    print("访问地址: http://localhost:5001")
    app.run(debug=True, port=5001, host='0.0.0.0')