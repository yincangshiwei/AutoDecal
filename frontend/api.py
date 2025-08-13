"""
前台API接口
提供前台界面所需的数据接口
"""
from flask import Blueprint, jsonify, request, session
from backend.database import DatabaseManager
from backend.auth import AccessCodeManager, access_code_required

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
    
    @api.route('/themes')
    @access_code_required
    def get_themes():
        """获取主题模板列表"""
        try:
            themes = DatabaseManager.get_themes()
            return jsonify({
                'success': True,
                'data': themes
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'message': f'获取主题列表失败: {str(e)}'
            })
    
    @api.route('/default_theme')
    @access_code_required
    def get_default_theme():
        """获取默认主题"""
        try:
            theme = DatabaseManager.get_default_theme()
            return jsonify({
                'success': True,
                'data': theme
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'message': f'获取默认主题失败: {str(e)}'
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
    
    @api.route('/theme/switch', methods=['POST'])
    @access_code_required
    def switch_theme():
        """切换主题"""
        try:
            data = request.get_json()
            theme_id = data.get('themeId')
            
            if not theme_id:
                return jsonify({'success': False, 'message': '请提供主题ID'})
            
            # 获取主题信息
            theme = DatabaseManager.get_theme_by_id(theme_id)
            if not theme:
                return jsonify({'success': False, 'message': '主题不存在'})
            
            # 在session中保存当前主题
            session['current_theme'] = theme_id
            
            return jsonify({
                'success': True,
                'message': '主题切换成功',
                'data': theme
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'message': f'主题切换失败: {str(e)}'
            })
    
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
    
    return api
