#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
简单测试脚本，检查Python环境是否正常
"""

import os
import sys

def main():
    print("=" * 50)
    print("Python 简单测试脚本")
    print("=" * 50)
    print(f"Python 版本: {sys.version}")
    print(f"当前工作目录: {os.getcwd()}")
    print("=" * 50)
    print("尝试导入爬虫所需的关键模块...")
    
    try:
        import requests
        print("✅ requests 模块已安装")
    except ImportError:
        print("❌ requests 模块未安装")
    
    try:
        from selenium import webdriver
        print("✅ selenium 模块已安装")
    except ImportError:
        print("❌ selenium 模块未安装")
    
    try:
        from config import Config
        print("✅ config 模块已成功导入")
    except ImportError:
        print("❌ 无法导入 config 模块")
        
    try:
        from main import MedicalConsultCrawler
        print("✅ MedicalConsultCrawler 类已成功导入")
    except ImportError:
        print("❌ 无法导入 MedicalConsultCrawler 类")
    
    print("=" * 50)
    return True

if __name__ == "__main__":
    main()
    print("测试脚本执行完成!") 