# 主题背景图管理路由 - 临时文件，用于更新 admin_app.py

@app.route('/theme-backgrounds/update', methods=['POST'])
@login_required
def update_theme_background():
    """更新主题背景图"""
    try:
        # 支持表单数据和文件上传
        if request.content_type and 'multipart/form-data' in request.content_type:
            bg_id = request.form.get('id')
            background_name = request.form.get('background_name')
            theme_name = request.form.get('theme_name')
            file = request.files.get('file')
        else:
            data = request.get_json()
            bg_id = data.get('id')
            background_name = data.get('background_name')
            theme_name = data.get('theme_name')
            file = None
        
        if not bg_id:
            return jsonify({'success': False, 'message': '缺少背景图ID'})
        
        # 获取原始记录
        original_bg = DatabaseManager.get_theme_background_by_id(int(bg_id))
        if not original_bg:
            return jsonify({'success': False, 'message': '背景图不存在'})
        
        # 处理文件上传
        new_file_path = None
        new_file_size = None
        
        if file and file.filename:
            # 检查文件类型
            allowed_extensions = {'.png', '.jpg', '.jpeg', '.webp'}
            file_ext = os.path.splitext(file.filename)[1].lower()
            if file_ext not in allowed_extensions:
                return jsonify({'success': False, 'message': '只支持 PNG、JPG、JPEG、WEBP 格式'})
            
            # 删除旧文件
            old_file_path = original_bg['file_path'].replace('/uploads/', 'uploads/')
            if os.path.exists(old_file_path):
                os.remove(old_file_path)
            
            # 保存新文件
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            safe_name = secure_filename(background_name or original_bg['background_name'])
            filename = f"theme_bg_{timestamp}_{safe_name}{file_ext}"
            
            bg_dir = 'uploads/themes_bgs'
            os.makedirs(bg_dir, exist_ok=True)
            file_path = os.path.join(bg_dir, filename)
            file.save(file_path)
            
            new_file_path = f'/uploads/themes_bgs/{filename}'
            new_file_size = os.path.getsize(file_path)
        
        # 更新数据库
        result = DatabaseManager.update_theme_background(
            bg_id=int(bg_id),
            background_name=background_name,
            theme_name=theme_name,
            file_path=new_file_path,
            file_size=new_file_size
        )
        
        if result > 0:
            return jsonify({'success': True, 'message': '背景图更新成功！'})
        else:
            return jsonify({'success': False, 'message': '背景图不存在或更新失败'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'更新失败: {str(e)}'})

@app.route('/theme-backgrounds/delete', methods=['POST'])
@login_required
def delete_theme_background():
    """删除主题背景图"""
    try:
        data = request.get_json()
        bg_id = data.get('id')
        
        if not bg_id:
            return jsonify({'success': False, 'message': '缺少背景图ID'})
        
        # 获取文件路径
        background = DatabaseManager.get_theme_background_by_id(bg_id)
        if background:
            # 删除物理文件
            file_path = background['file_path'].replace('/uploads/', 'uploads/')
            if os.path.exists(file_path):
                os.remove(file_path)
        
        # 从数据库删除记录
        result = DatabaseManager.delete_theme_background(bg_id)
        
        if result > 0:
            return jsonify({'success': True, 'message': '背景图删除成功！'})
        else:
            return jsonify({'success': False, 'message': '背景图不存在或已删除'})
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'删除失败: {str(e)}'})

@app.route('/theme-backgrounds/clear-all', methods=['POST'])
@login_required
def clear_all_theme_backgrounds():
    """清空所有主题背景图"""
    try:
        # 获取所有背景图
        backgrounds = DatabaseManager.get_theme_backgrounds()
        
        # 删除物理文件
        for bg in backgrounds:
            file_path = bg['file_path'].replace('/uploads/', 'uploads/')
            if os.path.exists(file_path):
                os.remove(file_path)
        
        # 从数据库删除所有记录
        query = "DELETE FROM theme_backgrounds"
        deleted_count = DatabaseManager.execute_update(query)
        
        return jsonify({
            'success': True,
            'message': f'已清空所有背景图，共删除 {deleted_count} 张'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'清空失败: {str(e)}'})