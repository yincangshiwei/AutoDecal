"""
角色管理路由
处理角色的增删改查操作
"""
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
import json
from backend.database import DatabaseManager
from backend.models import Role

# 创建角色管理蓝图
admin_roles_bp = Blueprint('admin_roles', __name__, url_prefix='/admin/roles')

# 添加自定义模板过滤器
@admin_roles_bp.app_template_filter('from_json')
def from_json_filter(value):
    """将JSON字符串转换为Python对象"""
    try:
        return json.loads(value) if value else {}
    except:
        return {}

def login_required(f):
    """登录检查装饰器"""
    def decorated_function(*args, **kwargs):
        from flask import session
        if 'admin_user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

@admin_roles_bp.route('/')
@login_required
def roles_list():
    """角色列表页面"""
    try:
        roles = DatabaseManager.get_roles()
        return render_template('admin/roles.html', roles=roles)
    except Exception as e:
        flash(f'获取角色列表失败: {str(e)}', 'error')
        return render_template('admin/roles.html', roles=[])

@admin_roles_bp.route('/add', methods=['POST'])
@login_required
def add_role():
    """添加角色"""
    try:
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        
        # 获取权限配置
        permissions = {}
        
        # 菜单权限
        menu_permissions = request.form.getlist('menu_permissions')
        permissions['menus'] = {
            'patterns': 'patterns' in menu_permissions,
            'products': 'products' in menu_permissions,
            'categories': 'categories' in menu_permissions,
            'access_codes': 'access_codes' in menu_permissions,
            'access_logs': 'access_logs' in menu_permissions,
            'users': 'users' in menu_permissions,
            'roles': 'roles' in menu_permissions,
            'theme_backgrounds': 'theme_backgrounds' in menu_permissions,
            'product_archives': 'product_archives' in menu_permissions,
            'settings': 'settings' in menu_permissions
        }
        
        # 操作权限
        action_permissions = request.form.getlist('action_permissions')
        permissions['actions'] = {
            'create': 'create' in action_permissions,
            'edit': 'edit' in action_permissions,
            'delete': 'delete' in action_permissions,
            'export': 'export' in action_permissions,
            'import': 'import' in action_permissions
        }
        
        if not name:
            flash('角色名称不能为空', 'error')
            return redirect(url_for('admin_roles.roles_list'))
        
        # 检查角色名是否已存在
        existing_roles = DatabaseManager.execute_query("SELECT * FROM roles WHERE name = ? AND is_active = 1", (name,))
        if existing_roles:
            flash('角色名称已存在', 'error')
            return redirect(url_for('admin_roles.roles_list'))
        
        # 添加角色
        role_id = DatabaseManager.add_role(name, description, json.dumps(permissions, ensure_ascii=False))
        
        if role_id:
            flash('角色添加成功', 'success')
        else:
            flash('角色添加失败', 'error')
            
    except Exception as e:
        flash(f'添加角色失败: {str(e)}', 'error')
    
    return redirect(url_for('admin_roles.roles_list'))

@admin_roles_bp.route('/edit/<int:role_id>', methods=['POST'])
@login_required
def edit_role(role_id):
    """编辑角色"""
    try:
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        
        # 获取权限配置
        permissions = {}
        
        # 菜单权限
        menu_permissions = request.form.getlist('menu_permissions')
        permissions['menus'] = {
            'patterns': 'patterns' in menu_permissions,
            'products': 'products' in menu_permissions,
            'categories': 'categories' in menu_permissions,
            'access_codes': 'access_codes' in menu_permissions,
            'access_logs': 'access_logs' in menu_permissions,
            'users': 'users' in menu_permissions,
            'roles': 'roles' in menu_permissions,
            'theme_backgrounds': 'theme_backgrounds' in menu_permissions,
            'product_archives': 'product_archives' in menu_permissions,
            'settings': 'settings' in menu_permissions
        }
        
        # 操作权限
        action_permissions = request.form.getlist('action_permissions')
        permissions['actions'] = {
            'create': 'create' in action_permissions,
            'edit': 'edit' in action_permissions,
            'delete': 'delete' in action_permissions,
            'export': 'export' in action_permissions,
            'import': 'import' in action_permissions
        }
        
        if not name:
            flash('角色名称不能为空', 'error')
            return redirect(url_for('admin_roles.roles_list'))
        
        # 检查角色名是否已存在（排除当前角色）
        existing_roles = DatabaseManager.execute_query(
            "SELECT * FROM roles WHERE name = ? AND id != ? AND is_active = 1", 
            (name, role_id)
        )
        if existing_roles:
            flash('角色名称已存在', 'error')
            return redirect(url_for('admin_roles.roles_list'))
        
        # 更新角色
        affected_rows = DatabaseManager.update_role(
            role_id, name, description, json.dumps(permissions, ensure_ascii=False)
        )
        
        if affected_rows > 0:
            flash('角色更新成功', 'success')
        else:
            flash('角色更新失败', 'error')
            
    except Exception as e:
        flash(f'更新角色失败: {str(e)}', 'error')
    
    return redirect(url_for('admin_roles.roles_list'))

@admin_roles_bp.route('/delete/<int:role_id>', methods=['POST'])
@login_required
def delete_role(role_id):
    """删除角色"""
    try:
        # 检查是否有用户使用此角色
        users_with_role = DatabaseManager.execute_query(
            "SELECT COUNT(*) as count FROM users WHERE role_id = ? AND is_active = 1", 
            (role_id,)
        )
        
        if users_with_role and users_with_role[0]['count'] > 0:
            flash('无法删除角色，还有用户正在使用此角色', 'error')
            return redirect(url_for('admin_roles.roles_list'))
        
        # 删除角色
        affected_rows = DatabaseManager.delete_role(role_id)
        
        if affected_rows > 0:
            flash('角色删除成功', 'success')
        else:
            flash('角色删除失败', 'error')
            
    except Exception as e:
        flash(f'删除角色失败: {str(e)}', 'error')
    
    return redirect(url_for('admin_roles.roles_list'))

@admin_roles_bp.route('/get/<int:role_id>')
@login_required
def get_role(role_id):
    """获取角色信息（AJAX）"""
    try:
        role = DatabaseManager.get_role_by_id(role_id)
        if role:
            # 解析权限JSON
            try:
                permissions = json.loads(role['permissions']) if role['permissions'] else {}
            except:
                permissions = {}
            
            role['permissions_parsed'] = permissions
            return jsonify({'success': True, 'role': role})
        else:
            return jsonify({'success': False, 'message': '角色不存在'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})