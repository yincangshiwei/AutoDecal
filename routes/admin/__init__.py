# Admin routes package
from .admin_patterns_route import patterns_bp
from .admin_products_route import products_bp
from .admin_product_categories_route import product_categories_bp
from .admin_pattern_categories_route import pattern_categories_bp
from .admin_access_codes_route import access_codes_bp
from .admin_users_route import users_bp
from .admin_roles_route import admin_roles_bp
from .admin_access_logs_route import access_logs_bp
from .admin_theme_backgrounds_route import theme_backgrounds_bp
from .admin_settings_route import settings_bp
from .admin_product_archives_route import product_archives_bp

def register_admin_blueprints(app):
    """注册所有管理员蓝图"""
    app.register_blueprint(patterns_bp)
    app.register_blueprint(products_bp)
    app.register_blueprint(product_categories_bp)
    app.register_blueprint(pattern_categories_bp)
    app.register_blueprint(access_codes_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(admin_roles_bp)
    app.register_blueprint(access_logs_bp)
    app.register_blueprint(theme_backgrounds_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(product_archives_bp)
