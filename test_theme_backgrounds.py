#!/usr/bin/env python3
"""
测试主题背景图管理功能
"""
import os
import requests
import json

def test_theme_backgrounds_api():
    """测试主题背景图API"""
    base_url = "http://localhost:7860"
    
    print("=" * 50)
    print("测试主题背景图管理功能")
    print("=" * 50)
    
    # 1. 测试获取主题列表
    print("\n1. 检查主题目录...")
    theme_dir = 'static/themes'
    if os.path.exists(theme_dir):
        themes = [f.replace('.css', '') for f in os.listdir(theme_dir) if f.endswith('.css')]
        print(f"   发现主题: {themes}")
    else:
        print("   主题目录不存在")
        return
    
    # 2. 检查背景图目录
    print("\n2. 检查背景图目录...")
    bg_dir = 'static/images/themes_bg'
    if os.path.exists(bg_dir):
        bg_files = [f for f in os.listdir(bg_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))]
        print(f"   发现背景图文件: {len(bg_files)} 个")
        
        # 按主题分组
        theme_bg_count = {}
        for theme in themes:
            count = len([f for f in bg_files if f.startswith(f'{theme}_bg')])
            theme_bg_count[theme] = count
            print(f"   - {theme}: {count} 张背景图")
    else:
        print("   背景图目录不存在")
        return
    
    # 3. 测试前台API接口
    print("\n3. 测试前台API接口...")
    try:
        # 测试获取default主题的背景图
        response = requests.get(f"{base_url}/api/theme-backgrounds?theme=default", timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                backgrounds = data.get('data', [])
                print(f"   ✓ API返回 default 主题背景图: {len(backgrounds)} 张")
                for bg in backgrounds[:3]:  # 只显示前3个
                    print(f"     - {bg['name']}")
            else:
                print(f"   ✗ API返回错误: {data.get('message')}")
        else:
            print(f"   ✗ API请求失败: HTTP {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"   ✗ API请求异常: {e}")
    
    # 4. 检查后台管理页面
    print("\n4. 检查后台管理功能...")
    try:
        response = requests.get(f"{base_url}/theme-backgrounds", timeout=5)
        if response.status_code == 200:
            print("   ✓ 后台管理页面可访问")
        elif response.status_code == 302:
            print("   ✓ 后台管理页面需要登录（正常）")
        else:
            print(f"   ✗ 后台管理页面异常: HTTP {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"   ✗ 后台管理页面请求异常: {e}")
    
    print("\n" + "=" * 50)
    print("测试完成")
    print("=" * 50)
    
    # 5. 输出使用说明
    print("\n使用说明:")
    print("1. 访问 http://localhost:7860/theme-backgrounds 进入后台管理")
    print("2. 使用管理员账号登录: admin / admin123")
    print("3. 可以上传、删除、重命名主题背景图")
    print("4. 背景图文件命名规则: 主题名_bg-描述.扩展名")
    print("5. 支持格式: PNG, JPG, JPEG, WEBP")

if __name__ == "__main__":
    test_theme_backgrounds_api()