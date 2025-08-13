"""
数据库操作类
处理SQLite数据库的创建、连接和基础操作
"""
import sqlite3
import os
from datetime import datetime
from typing import List, Optional, Dict, Any
from .models import Pattern, ProductCategory, Product, AccessCode, User, ThemeTemplate

DATABASE_PATH = 'database.db'

def get_db_connection():
    """获取数据库连接"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    """初始化数据库表结构"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 创建印花图案表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS patterns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            filename TEXT NOT NULL,
            file_path TEXT NOT NULL,
            upload_time DATETIME DEFAULT CURRENT_TIMESTAMP,
            file_size INTEGER DEFAULT 0,
            image_width INTEGER DEFAULT 0,
            image_height INTEGER DEFAULT 0,
            is_active BOOLEAN DEFAULT 1
        )
    ''')
    
    # 创建产品分类表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS product_categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            is_default BOOLEAN DEFAULT 0,
            sort_order INTEGER DEFAULT 0,
            is_active BOOLEAN DEFAULT 1,
            created_time DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 创建产品表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            category_id INTEGER NOT NULL,
            product_image TEXT NOT NULL,
            depth_image TEXT NOT NULL,
            product_image_path TEXT NOT NULL,
            depth_image_path TEXT NOT NULL,
            upload_time DATETIME DEFAULT CURRENT_TIMESTAMP,
            image_width INTEGER DEFAULT 0,
            image_height INTEGER DEFAULT 0,
            is_active BOOLEAN DEFAULT 1,
            FOREIGN KEY (category_id) REFERENCES product_categories (id)
        )
    ''')
    
    # 创建访问授权码表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS access_codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL UNIQUE,
            description TEXT,
            expires_at DATETIME,
            max_uses INTEGER,
            used_count INTEGER DEFAULT 0,
            is_active BOOLEAN DEFAULT 1,
            created_time DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 检查并添加新字段（用于数据库升级）
    try:
        cursor.execute("ALTER TABLE access_codes ADD COLUMN expires_at DATETIME")
    except sqlite3.OperationalError:
        pass  # 字段已存在
    
    try:
        cursor.execute("ALTER TABLE access_codes ADD COLUMN max_uses INTEGER")
    except sqlite3.OperationalError:
        pass  # 字段已存在
    
    try:
        cursor.execute("ALTER TABLE access_codes ADD COLUMN used_count INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass  # 字段已存在
    
    # 创建用户表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            is_admin BOOLEAN DEFAULT 0,
            permissions TEXT DEFAULT '{}',
            created_time DATETIME DEFAULT CURRENT_TIMESTAMP,
            last_login DATETIME,
            is_active BOOLEAN DEFAULT 1
        )
    ''')
    
    # 创建主题模板表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS theme_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            display_name TEXT NOT NULL,
            css_file TEXT NOT NULL,
            background_image TEXT,
            primary_color TEXT,
            secondary_color TEXT,
            is_default BOOLEAN DEFAULT 0,
            is_active BOOLEAN DEFAULT 1,
            created_time DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 插入默认数据
    init_default_data(cursor)
    
    conn.commit()
    conn.close()
    print("数据库初始化完成")

def init_default_data(cursor):
    """插入默认数据"""
    # 创建默认产品分类
    default_categories = [
        ('圣诞球工艺品', True, 1),
        ('家具工艺品', False, 2),
        ('装饰画工艺品', False, 3)
    ]
    
    for name, is_default, sort_order in default_categories:
        cursor.execute('''
            INSERT OR IGNORE INTO product_categories (name, is_default, sort_order)
            VALUES (?, ?, ?)
        ''', (name, is_default, sort_order))
    
    # 创建默认主题模板
    default_themes = [
        ('default', '默认主题', 'main.css', '', '#1976D2', '#424242', True),
        ('christmas', '圣诞主题', 'christmas.css', '', '#C62828', '#2E7D32', False),
        ('easter', '复活节主题', 'easter.css', '', '#7B1FA2', '#388E3C', False)
    ]
    
    for name, display_name, css_file, bg_image, primary, secondary, is_default in default_themes:
        cursor.execute('''
            INSERT OR IGNORE INTO theme_templates 
            (name, display_name, css_file, background_image, primary_color, secondary_color, is_default)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (name, display_name, css_file, bg_image, primary, secondary, is_default))

class DatabaseManager:
    """数据库管理类"""
    
    @staticmethod
    def execute_query(query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """执行查询并返回结果"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results
    
    @staticmethod
    def execute_update(query: str, params: tuple = ()) -> int:
        """执行更新操作并返回影响的行数"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        affected_rows = cursor.rowcount
        conn.close()
        return affected_rows
    
    @staticmethod
    def execute_insert(query: str, params: tuple = ()) -> int:
        """执行插入操作并返回新记录的ID"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        last_id = cursor.lastrowid
        conn.close()
        return last_id

    # 印花图案相关操作
    @staticmethod
    def get_patterns(active_only: bool = True) -> List[Dict[str, Any]]:
        """获取印花图案列表"""
        query = "SELECT * FROM patterns"
        if active_only:
            query += " WHERE is_active = 1"
        query += " ORDER BY upload_time DESC"
        return DatabaseManager.execute_query(query)
    
    @staticmethod
    def add_pattern(pattern: Pattern) -> int:
        """添加印花图案"""
        query = '''
            INSERT INTO patterns (name, filename, file_path, file_size, image_width, image_height)
            VALUES (?, ?, ?, ?, ?, ?)
        '''
        return DatabaseManager.execute_insert(query, (
            pattern.name, pattern.filename, pattern.file_path,
            pattern.file_size, pattern.image_width, pattern.image_height
        ))
    
    @staticmethod
    def update_pattern(pattern_id: int, pattern: Pattern) -> int:
        """更新印花图案"""
        query = '''
            UPDATE patterns 
            SET name = ?, filename = ?, file_path = ?, file_size = ?, 
                image_width = ?, image_height = ?
            WHERE id = ?
        '''
        return DatabaseManager.execute_update(query, (
            pattern.name, pattern.filename, pattern.file_path,
            pattern.file_size, pattern.image_width, pattern.image_height, pattern_id
        ))
    
    @staticmethod
    def delete_pattern(pattern_id: int) -> int:
        """删除印花图案（软删除）"""
        query = "UPDATE patterns SET is_active = 0 WHERE id = ?"
        return DatabaseManager.execute_update(query, (pattern_id,))
    
    @staticmethod
    def clear_patterns() -> int:
        """清空所有印花图案（软删除）"""
        query = "UPDATE patterns SET is_active = 0"
        return DatabaseManager.execute_update(query)

    # 产品分类相关操作
    @staticmethod
    def get_categories(active_only: bool = True) -> List[Dict[str, Any]]:
        """获取产品分类列表"""
        query = "SELECT * FROM product_categories"
        if active_only:
            query += " WHERE is_active = 1"
        query += " ORDER BY sort_order, created_time"
        return DatabaseManager.execute_query(query)
    
    @staticmethod
    def get_default_category() -> Optional[Dict[str, Any]]:
        """获取默认分类"""
        query = "SELECT * FROM product_categories WHERE is_default = 1 AND is_active = 1 LIMIT 1"
        results = DatabaseManager.execute_query(query)
        return results[0] if results else None
    
    @staticmethod
    def add_category(name: str, is_default: bool = False) -> int:
        """添加产品分类"""
        # 如果设置为默认分类，先取消其他默认分类
        if is_default:
            DatabaseManager.execute_update("UPDATE product_categories SET is_default = 0")
        
        query = "INSERT INTO product_categories (name, is_default) VALUES (?, ?)"
        return DatabaseManager.execute_insert(query, (name, is_default))

    # 产品相关操作
    @staticmethod
    def get_products(category_id: Optional[int] = None, active_only: bool = True) -> List[Dict[str, Any]]:
        """获取产品列表"""
        query = '''
            SELECT p.*, c.name as category_name 
            FROM products p 
            LEFT JOIN product_categories c ON p.category_id = c.id
        '''
        params = []
        conditions = []
        
        if active_only:
            conditions.append("p.is_active = 1")
        
        if category_id:
            conditions.append("p.category_id = ?")
            params.append(category_id)
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        query += " ORDER BY p.upload_time DESC"
        return DatabaseManager.execute_query(query, tuple(params))
    
    @staticmethod
    @staticmethod
    def add_product(product: Product) -> int:
        """添加产品"""
        query = '''
            INSERT INTO products 
            (title, category_id, product_image, depth_image, product_image_path, depth_image_path, image_width, image_height)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        '''
        return DatabaseManager.execute_insert(query, (
            product.title, product.category_id, product.product_image, product.depth_image,
            product.product_image_path, product.depth_image_path, product.image_width, product.image_height
        ))
    
    @staticmethod
    def update_product(product_id: int, title: str = None, category_id: int = None) -> int:
        """更新产品"""
        updates = []
        params = []
        
        if title:
            updates.append("title = ?")
            params.append(title)
        
        if category_id:
            updates.append("category_id = ?")
            params.append(category_id)
        
        if not updates:
            return 0
        
        params.append(product_id)
        query = f"UPDATE products SET {', '.join(updates)} WHERE id = ?"
        return DatabaseManager.execute_update(query, tuple(params))
    
    @staticmethod
    def delete_product(product_id: int) -> int:
        """删除产品（软删除）"""
        query = "UPDATE products SET is_active = 0 WHERE id = ?"
        return DatabaseManager.execute_update(query, (product_id,))
    
    @staticmethod
    def clear_products() -> int:
        """清空所有产品（软删除）"""
        query = "UPDATE products SET is_active = 0"
        return DatabaseManager.execute_update(query)

    # 主题模板相关操作
    @staticmethod
    def get_themes(active_only: bool = True) -> List[Dict[str, Any]]:
        """获取主题模板列表"""
        query = "SELECT * FROM theme_templates"
        if active_only:
            query += " WHERE is_active = 1"
        query += " ORDER BY is_default DESC, created_time"
        return DatabaseManager.execute_query(query)
    
    @staticmethod
    @staticmethod
    def get_default_theme() -> Optional[Dict[str, Any]]:
        """获取默认主题"""
        query = "SELECT * FROM theme_templates WHERE is_default = 1 AND is_active = 1 LIMIT 1"
        results = DatabaseManager.execute_query(query)
        return results[0] if results else None
    
    @staticmethod
    def get_theme_by_id(theme_id: int) -> Optional[Dict[str, Any]]:
        """根据ID获取主题"""
        query = "SELECT * FROM theme_templates WHERE id = ? AND is_active = 1"
        results = DatabaseManager.execute_query(query, (theme_id,))
        return results[0] if results else None
    
    @staticmethod
    def add_theme(theme: ThemeTemplate) -> int:
        """添加主题模板"""
        # 如果设置为默认主题，先取消其他默认主题
        if theme.is_default:
            DatabaseManager.execute_update("UPDATE theme_templates SET is_default = 0")
        
        query = '''
            INSERT INTO theme_templates 
            (name, display_name, css_file, background_image, primary_color, secondary_color, is_default)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        '''
        return DatabaseManager.execute_insert(query, (
            theme.name, theme.display_name, theme.css_file, theme.background_image,
            theme.primary_color, theme.secondary_color, theme.is_default
        ))
    
    @staticmethod
    def update_theme(theme_id: int, theme: ThemeTemplate) -> int:
        """更新主题模板"""
        # 如果设置为默认主题，先取消其他默认主题
        if theme.is_default:
            DatabaseManager.execute_update("UPDATE theme_templates SET is_default = 0 WHERE id != ?", (theme_id,))
        
        query = '''
            UPDATE theme_templates 
            SET name = ?, display_name = ?, css_file = ?, background_image = ?, 
                primary_color = ?, secondary_color = ?, is_default = ?
            WHERE id = ?
        '''
        return DatabaseManager.execute_update(query, (
            theme.name, theme.display_name, theme.css_file, theme.background_image,
            theme.primary_color, theme.secondary_color, theme.is_default, theme_id
        ))
    
    @staticmethod
    def delete_theme(theme_id: int) -> int:
        """删除主题模板（软删除）"""
        query = "UPDATE theme_templates SET is_active = 0 WHERE id = ?"
        return DatabaseManager.execute_update(query, (theme_id,))

    # 访问授权码相关操作
    @staticmethod
    def get_access_codes(active_only: bool = True) -> List[Dict[str, Any]]:
        """获取访问授权码列表"""
        query = "SELECT * FROM access_codes"
        if active_only:
            query += " WHERE is_active = 1"
        query += " ORDER BY created_time DESC"
        return DatabaseManager.execute_query(query)
    
    @staticmethod
    def add_access_code(access_code: AccessCode) -> int:
        """添加访问授权码"""
        query = '''
            INSERT INTO access_codes (code, description, start_date, end_date)
            VALUES (?, ?, ?, ?)
        '''
        return DatabaseManager.execute_insert(query, (
            access_code.code, access_code.description, 
            access_code.start_date, access_code.end_date
        ))
    
    @staticmethod
    def validate_access_code(code: str) -> bool:
        """验证访问授权码"""
        query = '''
            SELECT * FROM access_codes 
            WHERE code = ? AND is_active = 1 
            AND (expires_at IS NULL OR expires_at >= datetime('now'))
            AND (max_uses IS NULL OR used_count < max_uses)
        '''
        results = DatabaseManager.execute_query(query, (code,))
        return len(results) > 0
    
    @staticmethod
    def increment_usage_count(code: str) -> int:
        """增加授权码使用次数"""
        query = "UPDATE access_codes SET used_count = used_count + 1 WHERE code = ?"
        return DatabaseManager.execute_update(query, (code,))

    # 用户相关操作
    @staticmethod
    def get_users(active_only: bool = True) -> List[Dict[str, Any]]:
        """获取用户列表"""
        query = "SELECT id, username, is_admin, permissions, created_time, last_login, is_active FROM users"
        if active_only:
            query += " WHERE is_active = 1"
        query += " ORDER BY created_time DESC"
        return DatabaseManager.execute_query(query)
    
    @staticmethod
    def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
        """根据用户名获取用户"""
        query = "SELECT * FROM users WHERE username = ? AND is_active = 1"
        results = DatabaseManager.execute_query(query, (username,))
        return results[0] if results else None
    
    @staticmethod
    def add_user(user: User) -> int:
        """添加用户"""
        query = '''
            INSERT INTO users (username, password_hash, is_admin, permissions)
            VALUES (?, ?, ?, ?)
        '''
        return DatabaseManager.execute_insert(query, (
            user.username, user.password_hash, user.is_admin, user.permissions
        ))
    
    @staticmethod
    def update_last_login(username: str) -> int:
        """更新用户最后登录时间"""
        query = "UPDATE users SET last_login = datetime('now') WHERE username = ?"
        return DatabaseManager.execute_update(query, (username,))
