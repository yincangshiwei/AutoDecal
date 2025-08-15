"""
数据模型定义
定义所有数据库表结构和数据模型
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List

@dataclass
class Pattern:
    """印花图案模型"""
    id: Optional[int] = None
    name: str = ""
    filename: str = ""
    file_path: str = ""
    upload_time: Optional[datetime] = None
    file_size: int = 0
    image_width: int = 0
    image_height: int = 0
    is_active: bool = True

@dataclass
class ProductCategory:
    """产品分类模型"""
    id: Optional[int] = None
    name: str = ""
    is_default: bool = False
    sort_order: int = 0
    is_active: bool = True
    created_time: Optional[datetime] = None

@dataclass
class Product:
    """产品模型"""
    id: Optional[int] = None
    title: str = ""
    category_id: int = 0
    product_image: str = ""
    depth_image: str = ""
    product_image_path: str = ""
    depth_image_path: str = ""
    upload_time: Optional[datetime] = None
    image_width: int = 0
    image_height: int = 0
    is_active: bool = True

@dataclass
class AccessCode:
    """访问授权码模型"""
    id: Optional[int] = None
    code: str = ""
    description: str = ""
    expires_at: Optional[datetime] = None
    max_uses: Optional[int] = None
    used_count: int = 0
    is_active: bool = True
    created_time: Optional[datetime] = None

@dataclass
class User:
    """用户模型"""
    id: Optional[int] = None
    username: str = ""
    password_hash: str = ""
    is_admin: bool = False
    permissions: str = ""  # JSON格式存储权限配置
    created_time: Optional[datetime] = None
    last_login: Optional[datetime] = None
    is_active: bool = True

"""
数据模型定义
定义所有数据库表结构和数据模型
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List

@dataclass
class Pattern:
    """印花图案模型"""
    id: Optional[int] = None
    name: str = ""
    filename: str = ""
    file_path: str = ""
    upload_time: Optional[datetime] = None
    file_size: int = 0
    image_width: int = 0
    image_height: int = 0
    is_active: bool = True

@dataclass
class ProductCategory:
    """产品分类模型"""
    id: Optional[int] = None
    name: str = ""
    is_default: bool = False
    sort_order: int = 0
    is_active: bool = True
    created_time: Optional[datetime] = None

@dataclass
class Product:
    """产品模型"""
    id: Optional[int] = None
    title: str = ""
    category_id: int = 0
    product_image: str = ""
    depth_image: str = ""
    product_image_path: str = ""
    depth_image_path: str = ""
    upload_time: Optional[datetime] = None
    image_width: int = 0
    image_height: int = 0
    is_active: bool = True

@dataclass
class AccessCode:
    """访问授权码模型"""
    id: Optional[int] = None
    code: str = ""
    description: str = ""
    expires_at: Optional[datetime] = None
    max_uses: Optional[int] = None
    used_count: int = 0
    is_active: bool = True
    created_time: Optional[datetime] = None

@dataclass
class User:
    """用户模型"""
    id: Optional[int] = None
    username: str = ""
    password_hash: str = ""
    is_admin: bool = False
    permissions: str = ""  # JSON格式存储权限配置
    created_time: Optional[datetime] = None
    last_login: Optional[datetime] = None
    is_active: bool = True


@dataclass
class AccessLog:
    """访问记录模型"""
    id: Optional[int] = None
    session_id: str = ""
    access_code: str = ""
    ip_address: str = ""
    location: str = ""
    browser: str = ""
    operating_system: str = ""
    login_time: Optional[datetime] = None
    last_activity: Optional[datetime] = None
    is_active: bool = True
    logout_time: Optional[datetime] = None
