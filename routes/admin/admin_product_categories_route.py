from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from datetime import datetime
from backend.database import DatabaseManager

product_categories_bp = Blueprint('admin_product_categories', __name__, url_prefix='/admin/product_categories')

def login_required(f):
    def decorated_function(*args, **kwargs):
        from flask import session
        if 'admin_user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

@product_categories_bp.route('/')
@login_required
def product_categories():
    """产品分类管理页面"""
    try:
        categories = DatabaseManager.get_categories() or []
    except Exception as e:
        print(f"获取分类数据失败: {e}")
        categories = []
    return render_template('admin/product_categories.html', categories=categories)

@product_categories_bp.route('/add', methods=['POST'])
@login_required
def add_category():
    """添加分类"""
    try:
        data = request.get_json()
        name = data.get('name')
        
        if not name:
            return jsonify({'success': False, 'message': '请输入分类名称'})
        
        query = '''
            INSERT INTO product_categories (name, created_time)
            VALUES (?, ?)
        '''
        category_id = DatabaseManager.execute_insert(query, (name, datetime.now()))
        
        return jsonify({
            'success': True,
            'message': f'分类"{name}"添加成功！',
            'category_id': category_id
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'添加失败: {str(e)}'})

@product_categories_bp.route('/get')
@login_required
def get_category():
    """获取单个分类信息"""
    try:
        category_id = request.args.get('id', type=int)
        if not category_id:
            return jsonify({'success': False, 'message': '缺少分类ID'})
        
        query = "SELECT * FROM product_categories WHERE id = ?"
        results = DatabaseManager.execute_query(query, (category_id,))
        
        if results:
            category = dict(results[0])
            return jsonify({'success': True, 'data': category})
        else:
            return jsonify({'success': False, 'message': '分类不存在'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'获取失败: {str(e)}'})

@product_categories_bp.route('/update', methods=['POST'])
@login_required
def update_category():
    """更新分类"""
    try:
        data = request.get_json()
        category_id = data.get('id')
        name = data.get('name')
        
        if not category_id or not name:
            return jsonify({'success': False, 'message': '缺少必要参数'})
        
        query = "UPDATE product_categories SET name = ? WHERE id = ?"
        result = DatabaseManager.execute_update(query, (name, category_id))
        
        if result > 0:
            return jsonify({'success': True, 'message': '分类更新成功！'})
        else:
            return jsonify({'success': False, 'message': '分类不存在或更新失败'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'更新失败: {str(e)}'})

@product_categories_bp.route('/delete', methods=['POST'])
@login_required
def delete_category():
    """删除分类"""
    try:
        data = request.get_json()
        category_id = data.get('id')
        
        if not category_id:
            return jsonify({'success': False, 'message': '缺少分类ID'})
        
        # 删除数据库记录
        query = "DELETE FROM product_categories WHERE id = ?"
        result = DatabaseManager.execute_update(query, (category_id,))
        
        if result > 0:
            return jsonify({'success': True, 'message': '分类删除成功！'})
        else:
            return jsonify({'success': False, 'message': '分类不存在或已删除'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'删除失败: {str(e)}'})