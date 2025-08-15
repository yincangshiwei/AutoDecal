"""
产品管理模块的Gradio界面扩展
"""
import gradio as gr

def create_product_management_interface(admin):
    """创建产品管理界面"""
    
    # 产品管理界面
    with gr.Tab("产品管理"):
        gr.Markdown("## 产品管理")
        
        with gr.Row():
            with gr.Column():
                gr.Markdown("### 查看产品列表")
                refresh_products_btn = gr.Button("刷新列表")
                products_list = gr.Textbox(label="产品列表", lines=10, interactive=False)
                
                refresh_products_btn.click(
                    admin.get_products_list,
                    outputs=products_list
                )
            
            with gr.Column():
                gr.Markdown("### 添加新产品")
                add_product_title = gr.Textbox(label="产品标题", placeholder="请输入产品标题")
                add_product_category = gr.Number(label="分类ID", precision=0, placeholder="请输入分类ID")
                add_product_image = gr.File(label="产品图片", file_types=["image"])
                add_depth_image = gr.File(label="深度图片", file_types=["image"])
                add_product_btn = gr.Button("添加产品", variant="primary")
                add_product_result = gr.Textbox(label="操作结果", interactive=False)
                
                add_product_btn.click(
                    admin.add_product,
                    inputs=[add_product_title, add_product_category, add_product_image, add_depth_image],
                    outputs=add_product_result
                )
        
        with gr.Row():
            with gr.Column():
                gr.Markdown("### 更新产品")
                update_product_id = gr.Number(label="产品ID", precision=0)
                update_product_title = gr.Textbox(label="新标题")
                update_product_category = gr.Number(label="新分类ID", precision=0)
                update_product_image = gr.File(label="新产品图片（可选）", file_types=["image"])
                update_depth_image = gr.File(label="新深度图片（可选）", file_types=["image"])
                update_product_btn = gr.Button("更新产品")
                update_product_result = gr.Textbox(label="操作结果", interactive=False)
                
                update_product_btn.click(
                    admin.update_product,
                    inputs=[update_product_id, update_product_title, update_product_category, 
                            update_product_image, update_depth_image],
                    outputs=update_product_result
                )
            
            with gr.Column():
                gr.Markdown("### 删除操作")
                delete_product_id = gr.Number(label="要删除的产品ID", precision=0)
                delete_product_btn = gr.Button("删除产品", variant="stop")
                clear_products_btn = gr.Button("清空所有产品", variant="stop")
                delete_product_result = gr.Textbox(label="操作结果", interactive=False)
                
                delete_product_btn.click(
                    admin.delete_product,
                    inputs=delete_product_id,
                    outputs=delete_product_result
                )
                
                clear_products_btn.click(
                    admin.clear_products,
                    outputs=delete_product_result
                )

def create_access_code_management_interface(admin):
    """创建授权码管理界面"""
    
    # 授权码管理界面
    with gr.Tab("授权码管理"):
        gr.Markdown("## 访问授权码管理")
        
        with gr.Row():
            with gr.Column():
                gr.Markdown("### 查看授权码列表")
                refresh_codes_btn = gr.Button("刷新列表")
                codes_list = gr.Textbox(label="授权码列表", lines=10, interactive=False)
                
                refresh_codes_btn.click(
                    admin.get_access_codes_list,
                    outputs=codes_list
                )
            
            with gr.Column():
                gr.Markdown("### 生成新授权码")
                add_code_desc = gr.Textbox(label="授权码描述", placeholder="请输入授权码用途描述")
                add_code_start = gr.Textbox(label="开始日期", placeholder="YYYY-MM-DD HH:MM:SS")
                add_code_end = gr.Textbox(label="结束日期", placeholder="YYYY-MM-DD HH:MM:SS")
                add_code_btn = gr.Button("生成授权码", variant="primary")
                add_code_result = gr.Textbox(label="操作结果", interactive=False)
                
                add_code_btn.click(
                    admin.create_access_code,
                    inputs=[add_code_desc, add_code_start, add_code_end],
                    outputs=add_code_result
                )
        
        with gr.Row():
            with gr.Column():
                gr.Markdown("### 更新授权码")
                update_code_id = gr.Number(label="授权码ID", precision=0)
                update_code_desc = gr.Textbox(label="新描述")
                update_code_start = gr.Textbox(label="新开始日期", placeholder="YYYY-MM-DD HH:MM:SS")
                update_code_end = gr.Textbox(label="新结束日期", placeholder="YYYY-MM-DD HH:MM:SS")
                update_code_btn = gr.Button("更新授权码")
                update_code_result = gr.Textbox(label="操作结果", interactive=False)
                
                update_code_btn.click(
                    admin.update_access_code,
                    inputs=[update_code_id, update_code_desc, update_code_start, update_code_end],
                    outputs=update_code_result
                )
            
            with gr.Column():
                gr.Markdown("### 删除授权码")
                delete_code_id = gr.Number(label="要删除的授权码ID", precision=0)
                delete_code_btn = gr.Button("删除授权码", variant="stop")
                delete_code_result = gr.Textbox(label="操作结果", interactive=False)
                
                delete_code_btn.click(
                    admin.delete_access_code,
                    inputs=delete_code_id,
                    outputs=delete_code_result
                )

def create_user_management_interface(admin):
    """创建用户管理界面"""
    
    # 用户管理界面
    with gr.Tab("用户管理"):
        gr.Markdown("## 用户账号管理")
        
        with gr.Row():
            with gr.Column():
                gr.Markdown("### 查看用户列表")
                refresh_users_btn = gr.Button("刷新列表")
                users_list = gr.Textbox(label="用户列表", lines=10, interactive=False)
                
                refresh_users_btn.click(
                    admin.get_users_list,
                    outputs=users_list
                )
            
            with gr.Column():
                gr.Markdown("### 添加新用户")
                add_user_username = gr.Textbox(label="用户名", placeholder="请输入用户名")
                add_user_password = gr.Textbox(label="密码", type="password", placeholder="请输入密码")
                add_user_is_admin = gr.Checkbox(label="管理员权限")
                add_user_btn = gr.Button("添加用户", variant="primary")
                add_user_result = gr.Textbox(label="操作结果", interactive=False)
                
                add_user_btn.click(
                    admin.create_user,
                    inputs=[add_user_username, add_user_password, add_user_is_admin],
                    outputs=add_user_result
                )
        
        with gr.Row():
            with gr.Column():
                gr.Markdown("### 权限管理")
                perm_user_id = gr.Number(label="用户ID", precision=0)
                perm_pattern = gr.Checkbox(label="印花图案管理")
                perm_product = gr.Checkbox(label="产品管理")
                perm_category = gr.Checkbox(label="分类管理")
                perm_access_code = gr.Checkbox(label="授权码管理")
                perm_user = gr.Checkbox(label="用户管理")
                update_perm_btn = gr.Button("更新权限")
                update_perm_result = gr.Textbox(label="操作结果", interactive=False)
                
                update_perm_btn.click(
                    admin.update_user_permissions,
                    inputs=[perm_user_id, perm_pattern, perm_product, perm_category, 
                           perm_access_code, perm_user],
                    outputs=update_perm_result
                )
