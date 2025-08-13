"""
Flask后台管理界面扩展API
补充完整的CRUD操作接口
"""
from flask import Blueprint, request, jsonify
from .database import DatabaseManager
from .auth import login_required, admin_required
from .models import Product, ProductCategory, AccessCode, ThemeTemplate, User
from datetime import datetime
import os
from werkzeug.utils import secure_filename
from PIL import Image

# 创建扩展API蓝图
admin_ext_bp = Blueprint('admin_ext', __name__, url_prefix='/admin')

# 产品管理扩展API
@admin_ext_bp.route('/products/update', methods=['POST'])
@login_required
def update_product():
    """更新产品"""
    try:
        data = request.get_json()
        product_id = data.get('id')
        name = data.get('name')
        category_id = data.get('category_id')
        
        if not product_id or not name or not category_id:
            return jsonify({'success': False, 'message': '缺少必要参数'})
        
        result = DatabaseManager.update_product(product_id, title=name, category_id=category_id)
        if result > 0:
            return jsonify({'success': True, 'message': '产品更新成功！'})
        else:
            return jsonify({'success': False, 'message': '产品不存在或更新失败'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'更新失败: {str(e)}'})

@admin_ext_bp.route('/products/delete', methods=['POST'])
@login_required
def delete_product():
    """删除产品"""
    try:
        data = request.get_json()
        product_id = data.get('id')
        
        if not product_id:
            return jsonify({'success': False, 'message': '缺少产品ID'})
        
        result = DatabaseManager.delete_product(product_id)
        if result > 0:
            return jsonify({'success': True, 'message': '产品删除成功！'})
        else:
            return jsonify({'success': False, 'message': '产品不存在或已删除'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'删除失败: {str(e)}'})

@admin_ext_bp.route('/products/clear', methods=['POST'])
@login_required
def clear_products():
    """清空所有产品"""
    try:
        result = DatabaseManager.clear_products()
        return jsonify({'success': True, 'message': f'已清空所有产品，共 {result} 个'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'清空失败: {str(e)}'})

# 分类管理扩展API
@admin_ext_bp.route('/categories/get')
@login_required
def get_category():
    """获取单个分类信息"""
    try:
        category_id = request.args.get('id', type=int)
        if not category_id:
            return jsonify({'success': False, 'message': '缺少分类ID'})
        
        category = DatabaseManager.get_category_by_id(category_id)
        if category:
            return jsonify({'success': True, 'data': category})
        else:
            return jsonify({'success': False, 'message': '分类不存在'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'获取失败: {str(e)}'})

@admin_ext_bp.route('/categories/update', methods=['POST'])
@login_required
def update_category():
    """更新分类"""
    try:
        data = request.get_json()
        category_id = data.get('id')
        name = data.get('name')
        description = data.get('description', '')
        
        if not category_id or not name:
            return jsonify({'success': False, 'message': '缺少必要参数'})
        
        result = DatabaseManager.update_category(category_id, name=name, description=description)
        if result > 0:
            return jsonify({'success': True, 'message': '分类更新成功！'})
        else:
            return jsonify({'success': False, 'message': '分类不存在或更新失败'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'更新失败: {str(e)}'})

@admin_ext_bp.route('/categories/delete', methods=['POST'])
@login_required
def delete_category():
    """删除分类"""
    try:
        data = request.get_json()
        category_id = data.get('id')
        
        if not category_id:
            return jsonify({'success': False, 'message': '缺少分类ID'})
        
        result = DatabaseManager.delete_category(category_id)
        if result > 0:
            return jsonify({'success': True, 'message': '分类删除成功！'})
        else:
            return jsonify({'success': False, 'message': '分类不存在或已删除'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'删除失败: {str(e)}'})

# 授权码管理扩展API
@admin_ext_bp.route('/access-codes/get')
@login_required
def get_access_code():
    """获取单个授权码信息"""
    try:
        code_id = request.args.get('id', type=int)
        if not code_id:
            return jsonify({'success': False, 'message': '缺少授权码ID'})
        
        code = DatabaseManager.get_access_code_by_id(code_id)
        if code:
            return jsonify({'success': True, 'data': code})
        else:
            return jsonify({'success': False, 'message': '授权码不存在'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'获取失败: {str(e)}'})

@admin_ext_bp.route('/access-codes/update', methods=['POST'])
@login_required
def update_access_code():
    """更新授权码"""
    try:
        data = request.get_json()
        code_id = data.get('id')
        code = data.get('code')
        description = data.get('description', '')
        max_uses = data.get('max_uses')
        expires_at = data.get('expires_at')
        
        if not code_id or not code:
            return jsonify({'success': False, 'message': '缺少必要参数'})
        
        # 处理过期时间
        expires_datetime = None
        if expires_at:
            expires_datetime = datetime.fromisoformat(expires_at.replace('T', ' '))
        
        result = DatabaseManager.update_access_code(
            code_id, 
            code=code, 
            description=description,
            max_uses=max_uses,
            expires_at=expires_datetime
        )
        
        if result > 0:
            return jsonify({'success': True, 'message': '授权码更新成功！'})
        else:
            return jsonify({'success': False, 'message': '授权码不存在或更新失败'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'更新失败: {str(e)}'})

@admin_ext_bp.route('/access-codes/delete', methods=['POST'])
@login_required
def delete_access_code():
    """删除授权码"""
    try:
        data = request.get_json()
        code_id = data.get('id')
        
        if not code_id:
            return jsonify({'success': False, 'message': '缺少授权码ID'})
        
        result = DatabaseManager.delete_access_code(code_id)
        if result > 0:
            return jsonify({'success': True, 'message': '授权码删除成功！'})
        else:
            return jsonify({'success': False, 'message': '授权码不存在或已删除'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'删除失败: {str(e)}'})

@admin_ext_bp.route('/access-codes/toggle-status', methods=['POST'])
@login_required
def toggle_access_code_status():
    """切换授权码状态"""
    try:
        data = request.get_json()
        code_id = data.get('id')
        status = data.get('status')
        
        if not code_id or status is None:
            return jsonify({'success': False, 'message': '缺少必要参数'})
        
        result = DatabaseManager.update_access_code_status(code_id, status)
        if result > 0:
            action = '启用' if status == 'active' else '禁用'
            return jsonify({'success': True, 'message': f'授权码{action}成功！'})
        else:
            return jsonify({'success': False, 'message': '授权码不存在或操作失败'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'操作失败: {str(e)}'})

# 用户管理扩展API
@admin_ext_bp.route('/users/add', methods=['POST'])
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
        
        # 使用AuthManager创建用户
        is_admin = role == 'admin'
        user_id = AuthManager.create_user(username, password, is_admin)
        
        return jsonify({
            'success': True,
            'message': f'用户"{username}"添加成功！',
            'user_id': user_id
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'添加失败: {str(e)}'})

@admin_ext_bp.route('/users/get')
@admin_required
def get_user():
    """获取单个用户信息"""
    try:
        user_id = request.args.get('id', type=int)
        if not user_id:
            return jsonify({'success': False, 'message': '缺少用户ID'})
        
        user = DatabaseManager.get_user_by_id(user_id)
        if user:
            return jsonify({'success': True, 'data': user})
        else:
            return jsonify({'success': False, 'message': '用户不存在'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'获取失败: {str(e)}'})

@admin_ext_bp.route('/users/update', methods=['POST'])
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
        
        # 构建更新字段
        update_fields = ["username = ?"]
        params = [username]
        
        # 处理角色
        if role:
            is_admin = 1 if role == 'admin' else 0
            update_fields.append("is_admin = ?")
            params.append(is_admin)
        
        # 处理密码
        if password:
            from backend.auth import AuthManager
            password_hash = AuthManager.hash_password(password)
            update_fields.append("password_hash = ?")
            params.append(password_hash)
        
        # 处理状态
        update_fields.append("is_active = ?")
        params.append(is_active)
        
        # 添加用户ID到参数末尾
        params.append(user_id)
        
        # 构建完整的更新查询
        query = f"UPDATE users SET {', '.join(update_fields)} WHERE id = ?"
        result = DatabaseManager.execute_update(query, tuple(params))
        
        if result > 0:
            return jsonify({'success': True, 'message': '用户更新成功！'})
        else:
            return jsonify({'success': False, 'message': '用户不存在或更新失败'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'更新失败: {str(e)}'})

@admin_ext_bp.route('/users/delete', methods=['POST'])
@admin_required
def delete_user():
    """删除用户"""
    try:
        data = request.get_json()
        user_id = data.get('id')
        
        if not user_id:
            return jsonify({'success': False, 'message': '缺少用户ID'})
        
        result = DatabaseManager.delete_user(user_id)
        if result > 0:
            return jsonify({'success': True, 'message': '用户删除成功！'})
        else:
            return jsonify({'success': False, 'message': '用户不存在或已删除'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'删除失败: {str(e)}'})

@admin_ext_bp.route('/users/toggle-status', methods=['POST'])
@admin_required
def toggle_user_status():
    """切换用户状态"""
    try:
        data = request.get_json()
        user_id = data.get('id')
        is_active = data.get('is_active')
        
        if not user_id or is_active is None:
            return jsonify({'success': False, 'message': '缺少必要参数'})
        
        result = DatabaseManager.update_user_status(user_id, is_active)
        if result > 0:
            action = '启用' if is_active else '禁用'
            return jsonify({'success': True, 'message': f'用户{action}成功！'})
        else:
            return jsonify({'success': False, 'message': '用户不存在或操作失败'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'操作失败: {str(e)}'})

# 主题管理扩展API
@admin_ext_bp.route('/themes/add', methods=['POST'])
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
        
        theme_id = DatabaseManager.add_theme(
            name=name,
            season=season,
            description=description,
            primary_color=primary_color,
            secondary_color=secondary_color,
            accent_color=accent_color,
            is_active=is_active
        )
        
        return jsonify({
            'success': True,
            'message': f'主题"{name}"添加成功！',
            'theme_id': theme_id
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'添加失败: {str(e)}'})

@admin_ext_bp.route('/themes/get')
@login_required
def get_theme():
    """获取单个主题信息"""
    try:
        theme_id = request.args.get('id', type=int)
        if not theme_id:
            return jsonify({'success': False, 'message': '缺少主题ID'})
        
        theme = DatabaseManager.get_theme_by_id(theme_id)
        if theme:
            return jsonify({'success': True, 'data': theme})
        else:
            return jsonify({'success': False, 'message': '主题不存在'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'获取失败: {str(e)}'})

@admin_ext_bp.route('/themes/update', methods=['POST'])
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
        
        result = DatabaseManager.update_theme(
            theme_id,
            name=name,
            season=season,
            description=description,
            primary_color=primary_color,
            secondary_color=secondary_color,
            accent_color=accent_color,
            is_active=is_active
        )
        
        if result > 0:
            return jsonify({'success': True, 'message': '主题更新成功！'})
        else:
            return jsonify({'success': False, 'message': '主题不存在或更新失败'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'更新失败: {str(e)}'})

@admin_ext_bp.route('/themes/delete', methods=['POST'])
@login_required
def delete_theme():
    """删除主题"""
    try:
        data = request.get_json()
        theme_id = data.get('id')
        
        if not theme_id:
            return jsonify({'success': False, 'message': '缺少主题ID'})
        
        result = DatabaseManager.delete_theme(theme_id)
        if result > 0:
            return jsonify({'success': True, 'message': '主题删除成功！'})
        else:
            return jsonify({'success': False, 'message': '主题不存在或已删除'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'删除失败: {str(e)}'})

@admin_ext_bp.route('/themes/toggle-status', methods=['POST'])
@login_required
def toggle_theme_status():
    """切换主题状态"""
    try:
        data = request.get_json()
        theme_id = data.get('id')
        is_active = data.get('is_active')
        
        if not theme_id or is_active is None:
            return jsonify({'success': False, 'message': '缺少必要参数'})
        
        result = DatabaseManager.update_theme_status(theme_id, is_active)
        if result > 0:
            action = '启用' if is_active else '禁用'
            return jsonify({'success': True, 'message': f'主题{action}成功！'})
        else:
            return jsonify({'success': False, 'message': '主题不存在或操作失败'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'操作失败: {str(e)}'})