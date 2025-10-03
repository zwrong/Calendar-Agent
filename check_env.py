#!/usr/bin/env python3
"""
环境配置检查脚本
运行此脚本来验证您的环境配置是否正确
"""

import os
from dotenv import load_dotenv

def check_environment():
    """检查环境变量配置"""
    print("🔍 检查环境配置...")
    print("=" * 50)

    # 加载环境变量
    load_dotenv()

    # 检查必要的环境变量
    required_vars = {
        'APPLE_CALENDAR_USERNAME': 'Apple日历用户名',
        'APPLE_CALENDAR_PASSWORD': 'Apple应用专用密码',
        'DEEPSEEK_API_KEY': 'DeepSeek API密钥'
    }

    all_good = True

    for var_name, description in required_vars.items():
        value = os.getenv(var_name)
        if value and value not in ['your_apple_id@icloud.com', 'your_app_specific_password', 'your_deepseek_api_key']:
            print(f"✅ {description}: 已配置")
            # 显示部分信息用于验证
            if var_name == 'APPLE_CALENDAR_PASSWORD':
                print(f"   密码格式: {'*' * 16}")
            elif var_name == 'DEEPSEEK_API_KEY':
                print(f"   API密钥: sk-...{value[-8:]}")
            else:
                print(f"   值: {value}")
        else:
            print(f"❌ {description}: 未配置或使用默认值")
            all_good = False

    print("\n" + "=" * 50)

    if all_good:
        print("🎉 所有环境变量已正确配置！")
        print("\n接下来可以运行应用：")
        print("1. source venv/bin/activate")
        print("2. python app.py")
        print("3. 访问 http://localhost:5000")
    else:
        print("⚠️  请按照 SETUP_GUIDE.md 中的说明配置环境变量")
        print("\n配置步骤：")
        print("1. 编辑 .env 文件")
        print("2. 设置正确的 Apple ID 和应用专用密码")
        print("3. 设置 DeepSeek API 密钥")

    return all_good

def check_dependencies():
    """检查依赖包是否安装"""
    print("\n📦 检查依赖包...")
    print("=" * 50)

    dependencies = [
        'caldav',
        'icalendar',
        'deepseek',
        'flask',
        'python-dotenv'
    ]

    all_installed = True

    for dep in dependencies:
        try:
            if dep == 'python-dotenv':
                __import__('dotenv')
            else:
                __import__(dep)
            print(f"✅ {dep}: 已安装")
        except ImportError:
            print(f"❌ {dep}: 未安装")
            all_installed = False

    if not all_installed:
        print("\n⚠️  请安装缺失的依赖：")
        print("pip install -r requirements.txt")

    return all_installed

if __name__ == "__main__":
    print("🤖 AI日程管理助手 - 环境检查")
    print("=" * 50)

    env_ok = check_environment()
    deps_ok = check_dependencies()

    print("\n" + "=" * 50)

    if env_ok and deps_ok:
        print("🎉 所有检查通过！可以启动应用了。")
    else:
        print("❌ 请解决上述问题后再运行应用。")