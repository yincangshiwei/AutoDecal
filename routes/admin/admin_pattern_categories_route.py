from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from datetime import datetime
from backend.database import DatabaseManager

pattern_categories_bp = Blueprint('admin_pattern_categories', __name__, url_prefix='/admin/pattern_categories')

def login_required(f):
    def decorated_function(*args, **kwargs):
        from flask import session
        if 'admin_user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

@pattern_categories_bp.route('/')
@login_required
def pattern_categories():
    """印花分类管理页面"""
    try:
        categories = DatabaseManager.get_pattern_categories() or []
    except Exception as e:
        print(f"获取印花分类数据失败: {e}")
        categories = []
    return render_template('admin/pattern_categories.html', categories=categories)

@pattern_categories_bp.route('/add', methods=['POST'])
@login_required
def add_pattern_category():
    """添加印花分类"""
    try:
        data = request.get_json()
        name = data.get('name')
        description = data.get('description', '')
        
        if not name:
            return jsonify({'success': False, 'message': '请输入分类名称'})
        
        query = '''
            INSERT INTO pattern_categories (name, description, created_time)
            VALUES (?, ?, ?)
        '''
        category_id = DatabaseManager.execute_insert(query, (name, description, datetime.now()))
        
        return jsonify({
            'success': True,
            'message': f'印花分类"{name}"添加成功！',
            'category_id': category_id
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'添加失败: {str(e)}'})

@pattern_categories_bp.route('/get')
@login_required
def get_pattern_category():
    """获取单个印花分类信息"""
    try:
        category_id = request.args.get('id', type=int)
        if not category_id:
            return jsonify({'success': False, 'message': '缺少分类ID'})
        
        query = "SELECT * FROM pattern_categories WHERE id = ?"
        results = DatabaseManager.execute_query(query, (category_id,))
        
        if results:
            category = dict(results[0])
            return jsonify({'success': True, 'data': category})
        else:
            return jsonify({'success': False, 'message': '印花分类不存在'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'获取失败: {str(e)}'})

@pattern_categories_bp.route('/update', methods=['POST'])
@login_required
def update_pattern_category():
    """更新印花分类"""
    try:
        data = request.get_json()
        category_id = data.get('id')
        name = data.get('name')
        description = data.get('description', '')
        
        if not category_id or not name:
            return jsonify({'success': False, 'message': '缺少必要参数'})
        
        query = "UPDATE pattern_categories SET name = ?, description = ? WHERE id = ?"
        result = DatabaseManager.execute_update(query, (name, description, category_id))
        
        if result > 0:
            return jsonify({'success': True, 'message': '印花分类更新成功！'})
        else:
            return jsonify({'success': False, 'message': '印花分类不存在或更新失败'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'更新失败: {str(e)}'})

@pattern_categories_bp.route('/delete', methods=['POST'])
@login_required
def delete_pattern_category():
    """删除印花分类"""
    try:
        data = request.get_json()
        category_id = data.get('id')
        
        if not category_id:
            return jsonify({'success': False, 'message': '缺少分类ID'})
        
        # 删除数据库记录
        query = "DELETE FROM pattern_categories WHERE id = ?"
        result = DatabaseManager.execute_update(query, (category_id,))
        
        if result > 0:
            return jsonify({'success': True, 'message': '印花分类删除成功！'})
        else:
            return jsonify({'success': False, 'message': '印花分类不存在或已删除'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'删除失败: {str(e)}'})