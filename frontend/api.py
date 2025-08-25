"""
前台API接口
提供前台界面所需的数据接口
"""
from flask import Blueprint, jsonify, request, session
from backend.database import DatabaseManager
from backend.auth import AccessCodeManager, access_code_required
import time

def create_api_blueprint():
    """创建API蓝图"""
    api = Blueprint('api', __name__)
    
    @api.route('/validate_access', methods=['POST'])
    def validate_access():
        """验证访问授权码"""
        data = request.get_json()
        access_code = data.get('access_code')
        
        if not access_code:
            return jsonify({'success': False, 'message': '请输入访问授权码'})
        
        if AccessCodeManager.validate_access_code(access_code):
            session['access_code_validated'] = True
            session['access_code'] = access_code
            return jsonify({'success': True, 'message': '授权码验证成功'})
        else:
            return jsonify({'success': False, 'message': '无效的访问授权码或已过期'})
    
    @api.route('/patterns')
    @access_code_required
    def get_patterns():
        """获取印花图案列表"""
        try:
            patterns = DatabaseManager.get_patterns()
            return jsonify({
                'success': True,
                'data': patterns
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'message': f'获取印花图案失败: {str(e)}'
            })
    
    @api.route('/categories')
    @access_code_required
    def get_categories():
        """获取产品分类列表"""
        try:
            categories = DatabaseManager.get_categories()
            return jsonify({
                'success': True,
                'data': categories
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'message': f'获取产品分类失败: {str(e)}'
            })
    
    @api.route('/products')
    @access_code_required
    def get_products():
        """获取产品列表"""
        try:
            category_id = request.args.get('category_id', type=int)
            products = DatabaseManager.get_products(category_id)
            return jsonify({
                'success': True,
                'data': products
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'message': f'获取产品列表失败: {str(e)}'
            })
    
    @api.route('/default_category')
    @access_code_required
    def get_default_category():
        """获取默认分类"""
        try:
            category = DatabaseManager.get_default_category()
            return jsonify({
                'success': True,
                'data': category
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'message': f'获取默认分类失败: {str(e)}'
            })
    
    
    @api.route('/auth/verify', methods=['POST'])
    def verify_auth():
        """验证授权码（前台JavaScript调用的接口）"""
        data = request.get_json()
        access_code = data.get('accessCode')
        
        if not access_code:
            return jsonify({'success': False, 'message': '请输入访问授权码'})
        
        if AccessCodeManager.validate_access_code(access_code):
            session['access_code_validated'] = True
            session['access_code'] = access_code
            return jsonify({'success': True, 'message': '授权码验证成功'})
        else:
            return jsonify({'success': False, 'message': '无效的访问授权码或已过期'})
    
    
    @api.route('/export', methods=['POST'])
    @access_code_required
    def export_design():
        """导出设计图"""
        try:
            data = request.get_json()
            image_data = data.get('imageData')
            
            if not image_data:
                return jsonify({'success': False, 'message': '没有图像数据'})
            
            # 这里可以添加保存图像的逻辑
            # 目前只返回成功响应
            return jsonify({
                'success': True,
                'message': '导出成功',
                'data': {
                    'filename': f'design_{int(time.time())}.png'
                }
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'message': f'导出失败: {str(e)}'
            })
    
    @api.route('/theme-backgrounds')
    @access_code_required
    def theme_backgrounds():
        """按主题列出可用背景图"""
        try:
            theme = request.args.get('theme', default='default', type=str)
            # 从数据库获取主题背景图
            backgrounds = DatabaseManager.get_theme_backgrounds(theme_name=theme)
            
            results = []
            for bg in backgrounds:
                results.append({
                    'id': bg['id'],
                    'name': bg['background_name'],
                    'url': bg['file_path'],
                    'theme': bg['theme_name'],
                    'file_size': bg['file_size']
                })
            
            return jsonify({'success': True, 'data': results})
        except Exception as e:
            return jsonify({'success': False, 'message': f'获取背景图失败: {str(e)}'})
    
    @api.route('/archive', methods=['POST'])
    @access_code_required
    def archive_product():
        """产品效果归档登记"""
        try:
            data = request.get_json()
            
            # 获取表单数据
            register_person = data.get('registerPerson', '').strip()
            register_info = data.get('registerInfo', '').strip()
            effect_category = data.get('effectCategory', '基础效果')
            product_id = data.get('productId')
            pattern_id = data.get('patternId')
            effect_image_data = data.get('effectImageData')
            
            if not register_person:
                return jsonify({'success': False, 'message': '请填写登记人'})
            
            if not product_id:
                return jsonify({'success': False, 'message': '请先选择产品图'})
            
            if not effect_image_data:
                return jsonify({'success': False, 'message': '请先生成效果图'})
            
            # 获取当前授权码
            access_code = session.get('access_code', '')
            
            # 获取产品信息
            product_query = "SELECT * FROM products WHERE id = ?"
            product_results = DatabaseManager.execute_query(product_query, (product_id,))
            if not product_results:
                return jsonify({'success': False, 'message': '产品不存在'})
            
            product = product_results[0]
            
            # 创建归档目录
            import os
            from datetime import datetime
            import base64
            
            archive_dir = os.path.join('uploads', 'archives')
            os.makedirs(archive_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # 复制原产品图到归档目录
            # 复制原产品图到归档目录（使用与后台管理一致的命名格式）
            original_product_path = os.path.join('uploads', 'products', product['product_image_path'])
            archive_product_filename = f"original_product_{timestamp}.png"
            archive_product_path = os.path.join(archive_dir, archive_product_filename)
            
            if os.path.exists(original_product_path):
                import shutil
                shutil.copy2(original_product_path, archive_product_path)
            
            # 复制深度图到归档目录（使用与后台管理一致的命名格式）
            original_depth_path = os.path.join('uploads', 'depth_maps', product['depth_image_path'])
            archive_depth_filename = f"original_depth_{timestamp}.png"
            archive_depth_path = os.path.join(archive_dir, archive_depth_filename)
            
            if os.path.exists(original_depth_path):
                shutil.copy2(original_depth_path, archive_depth_path)
            
            # 保存效果图（使用与后台管理一致的命名格式）
            effect_filename = f"effect_{timestamp}.png"
            effect_path = os.path.join(archive_dir, effect_filename)
            
            # 解码base64图片数据
            if effect_image_data.startswith('data:image/png;base64,'):
                image_data = effect_image_data.split(',')[1]
                with open(effect_path, 'wb') as f:
                    f.write(base64.b64decode(image_data))
            
            # 保存归档记录到数据库
            # 保存归档记录到数据库
            archive_id = DatabaseManager.add_product_archive(
                access_code=access_code,
                original_product_image=product['product_image'],
                original_depth_image=product['depth_image'],
                effect_image=effect_filename,
                effect_category=effect_category,
                register_info=register_info,
                follow_up_person=register_person,
                original_product_path=archive_product_filename,
                original_depth_path=archive_depth_filename,
                effect_image_path=effect_filename
            )
            
            return jsonify({
                'success': True,
                'message': '归档登记成功！',
                'archive_id': archive_id
            })
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({'success': False, 'message': f'归档失败: {str(e)}'})
    
    return api
