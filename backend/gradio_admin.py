"""
Gradio后台管理界面
使用Gradio构建的管理界面，包含所有后台管理功能
"""
import gradio as gr
import os
import shutil
from datetime import datetime
from PIL import Image
from .database import DatabaseManager
from .auth import AuthManager, AccessCodeManager, get_permission_list
from .models import Pattern, Product, ProductCategory

class GradioAdmin:
    """Gradio管理界面类"""
    
    def __init__(self):
        self.current_user = None
        self.upload_folder = 'uploads'
    
    def authenticate(self, username: str, password: str):
        """用户认证"""
        user = AuthManager.authenticate_user(username, password)
        if user:
            self.current_user = user
            return f"登录成功！欢迎 {user['username']}"
        else:
            return "用户名或密码错误"
    
    def logout(self):
        """用户登出"""
        self.current_user = None
        return "已退出登录"
    
    def check_permission(self, permission: str) -> bool:
        """检查权限"""
        if not self.current_user:
            return False
        
        if self.current_user['is_admin']:
            return True
        
        permissions = self.current_user.get('permissions', {})
        return permissions.get('all') or permissions.get(permission)
    
    # 印花图案管理
    def get_patterns_list(self):
        """获取印花图案列表"""
        if not self.check_permission('pattern_manage'):
            return "权限不足"
        
        try:
            patterns = DatabaseManager.get_patterns(active_only=False)
            if not patterns:
                return "暂无印花图案"
            
            result = "印花图案列表:\n"
            for pattern in patterns:
                status = "正常" if pattern['is_active'] else "已删除"
                result += f"ID: {pattern['id']}, 名称: {pattern['name']}, 文件: {pattern['filename']}, 状态: {status}\n"
            
            return result
        except Exception as e:
            return f"获取列表失败: {str(e)}"
    
    def add_pattern(self, name: str, image_file):
        """添加印花图案"""
        if not self.check_permission('pattern_manage'):
            return "权限不足"
        
        if not name or not image_file:
            return "请填写图案名称并上传图片"
        
        try:
            # 保存上传的图片
            filename = f"pattern_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{image_file.name}"
            file_path = os.path.join(self.upload_folder, 'patterns', filename)
            
            # 确保目录存在
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # 复制文件
            shutil.copy(image_file.name, file_path)
            
            # 获取图片尺寸
            with Image.open(file_path) as img:
                width, height = img.size
            
            # 获取文件大小
            file_size = os.path.getsize(file_path)
            
            # 创建图案对象
            pattern = Pattern(
                name=name,
                filename=filename,
                file_path=file_path,
                file_size=file_size,
                image_width=width,
                image_height=height
            )
            
            # 保存到数据库
            pattern_id = DatabaseManager.add_pattern(pattern)
            
            return f"印花图案添加成功！ID: {pattern_id}"
        
        except Exception as e:
            return f"添加失败: {str(e)}"
    
    def delete_pattern(self, pattern_id: int):
        """删除印花图案"""
        if not self.check_permission('pattern_manage'):
            return "权限不足"
        
        if not pattern_id:
            return "请输入图案ID"
        
        try:
            result = DatabaseManager.delete_pattern(pattern_id)
            if result > 0:
                return f"印花图案删除成功！"
            else:
                return "图案不存在或已删除"
        except Exception as e:
            return f"删除失败: {str(e)}"
    
    def clear_patterns(self):
        """清空所有印花图案"""
        if not self.check_permission('pattern_manage'):
            return "权限不足"
        
        try:
            result = DatabaseManager.execute_update("UPDATE patterns SET is_active = 0")
            return f"已清空所有印花图案，共 {result} 个"
        except Exception as e:
            return f"清空失败: {str(e)}"


def create_admin_interface():
    """创建Gradio管理界面"""
    admin = GradioAdmin()
    
    # 模块化的Gradio界面，使用Tab分组
    with gr.Blocks(title="产品印花平台 - 后台管理") as interface:
        gr.Markdown("# 🎨 产品印花平台 - 后台管理系统")
        
        # 登录状态显示
        with gr.Row():
            with gr.Column(scale=2):
                gr.Markdown("### 👤 用户登录")
            with gr.Column(scale=1):
                login_status = gr.Textbox(label="登录状态", value="未登录", interactive=False)
        
        with gr.Row():
            username_input = gr.Textbox(label="用户名", placeholder="admin")
            password_input = gr.Textbox(label="密码", type="password", placeholder="admin123")
            with gr.Column():
                login_btn = gr.Button("🔑 登录", variant="primary")
                logout_btn = gr.Button("🚪 退出登录")
        
        login_btn.click(
            admin.authenticate,
            inputs=[username_input, password_input],
            outputs=login_status
        )
        
        logout_btn.click(
            admin.logout,
            outputs=login_status
        )
        
        gr.Markdown("---")
        
        # 使用Tab组织不同的管理模块
        with gr.Tabs():
            # 印花图案管理模块
            with gr.TabItem("🎨 印花图案管理"):
                with gr.Row():
                    with gr.Column():
                        gr.Markdown("### 📋 图案列表")
                        refresh_patterns_btn = gr.Button("🔄 刷新列表")
                        patterns_list = gr.Textbox(label="图案列表", lines=10, interactive=False)
                        
                        refresh_patterns_btn.click(
                            admin.get_patterns_list,
                            outputs=patterns_list
                        )
                    
                    with gr.Column():
                        gr.Markdown("### ➕ 添加新图案")
                        add_pattern_name = gr.Textbox(label="图案名称", placeholder="请输入图案名称")
                        add_pattern_file = gr.File(label="上传图片", file_types=["image"])
                        add_pattern_btn = gr.Button("📤 添加图案", variant="primary")
                        add_pattern_result = gr.Textbox(label="操作结果", interactive=False)
                        
                        add_pattern_btn.click(
                            admin.add_pattern,
                            inputs=[add_pattern_name, add_pattern_file],
                            outputs=add_pattern_result
                        )
                
                gr.Markdown("### 🗑️ 删除操作")
                with gr.Row():
                    delete_pattern_id = gr.Number(label="要删除的图案ID", precision=0)
                    with gr.Column():
                        delete_pattern_btn = gr.Button("🗑️ 删除图案", variant="stop")
                        clear_patterns_btn = gr.Button("🧹 清空所有图案", variant="stop")
                
                delete_result = gr.Textbox(label="删除结果", interactive=False)
                
                delete_pattern_btn.click(
                    admin.delete_pattern,
                    inputs=delete_pattern_id,
                    outputs=delete_result
                )
                
                clear_patterns_btn.click(
                    admin.clear_patterns,
                    outputs=delete_result
                )
            
            # 产品管理模块
            with gr.TabItem("📦 产品管理"):
                gr.Markdown("### 🚧 产品管理功能")
                gr.Markdown("此模块正在开发中，将包含以下功能：")
                gr.Markdown("- 产品图片上传管理")
                gr.Markdown("- 深度图配置")
                gr.Markdown("- 产品分类设置")
                gr.Markdown("- 产品信息编辑")
            
            # 分类管理模块
            with gr.TabItem("📂 分类管理"):
                gr.Markdown("### 🚧 分类管理功能")
                gr.Markdown("此模块正在开发中，将包含以下功能：")
                gr.Markdown("- 产品分类创建")
                gr.Markdown("- 默认分类设置")
                gr.Markdown("- 分类排序管理")
                gr.Markdown("- 分类删除操作")
            
            # 授权码管理模块
            with gr.TabItem("🎫 授权码管理"):
                gr.Markdown("### 🚧 授权码管理功能")
                gr.Markdown("此模块正在开发中，将包含以下功能：")
                gr.Markdown("- 授权码生成")
                gr.Markdown("- 有效期设置")
                gr.Markdown("- 使用统计查看")
                gr.Markdown("- 授权码删除")
                
                gr.Markdown("### 📋 当前可用授权码")
                gr.Markdown("**A-OI5VLB** (有效期至 2025-09-09)")
            
            # 主题管理模块
            with gr.TabItem("🎨 主题管理"):
                gr.Markdown("### 🚧 主题管理功能")
                gr.Markdown("此模块正在开发中，将包含以下功能：")
                gr.Markdown("- 主题模板创建")
                gr.Markdown("- 颜色配置")
                gr.Markdown("- 默认主题设置")
                gr.Markdown("- 主题预览")
            
            # 用户管理模块
            with gr.TabItem("👥 用户管理"):
                gr.Markdown("### 🚧 用户管理功能")
                gr.Markdown("此模块正在开发中，将包含以下功能：")
                gr.Markdown("- 用户账号创建")
                gr.Markdown("- 权限分配")
                gr.Markdown("- 密码重置")
                gr.Markdown("- 用户状态管理")
            
            # 系统信息模块
            with gr.TabItem("ℹ️ 系统信息"):
                gr.Markdown("### 📊 系统状态")
                gr.Markdown("- **平台版本**: v1.0.0")
                gr.Markdown("- **数据库**: SQLite")
                gr.Markdown("- **后端框架**: Flask + Gradio")
                gr.Markdown("- **前端技术**: HTML5 + CSS3 + JavaScript")
                
                gr.Markdown("### 🔑 默认登录信息")
                gr.Markdown("- **管理员账号**: admin")
                gr.Markdown("- **管理员密码**: admin123")
                
                gr.Markdown("### 🌐 访问地址")
                gr.Markdown("- **前台界面**: http://localhost:5000")
                gr.Markdown("- **后台管理**: http://localhost:7860")
                
                gr.Markdown("### 📝 使用说明")
                gr.Markdown("1. 首先在此后台管理界面登录")
                gr.Markdown("2. 上传印花图案和产品图片")
                gr.Markdown("3. 使用授权码访问前台设计界面")
                gr.Markdown("4. 适合展会展台展示使用")
    
    return interface
