#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
配置文件，包含项目所需的各种参数设置
"""

class Config:
    # 医疗咨询平台登录信息
    USERNAME = "admin"  # 请替换为实际的用户名
    PASSWORD = "Bjgxyy123!@#"  # 请替换为实际的密码
    CAPTCHA_CODE = "1234"  # 验证码，需要实际获取后填写
    MANUAL_CAPTCHA = True  # 是否手动输入验证码
    AUTO_RETRY = True  # 是否自动重试登录
    MAX_RETRIES = 3  # 最大重试次数
    LOGIN_URL = "https://consult.ht-healthcare.com/manage/login"  # 登录页面URL
    
    # 爬虫相关参数
    REQUEST_INTERVAL = 2.0  # 两次请求之间的间隔时间(秒)
    PAGE_INTERVAL = 5.0     # 翻页时的间隔时间(秒)
    MAX_PAGES = 10          # 最多爬取的页数
    HEADLESS_MODE = False   # 是否使用无头模式（不显示浏览器窗口）
    
    # 验证码自动识别配置
    CAPTCHA_AUTO_RECOGNIZE = False  # 是否自动识别验证码
    CAPTCHA_API_KEY = ""    # 验证码识别API密钥
    CAPTCHA_API_URL = ""    # 验证码识别API地址
    
    # 代理IP配置
    USE_PROXY = False       # 是否使用代理IP
    PROXY_SOURCE = "file"   # 代理来源，可选 "file" 或 "api"
    PROXY_FILE = "proxies.txt"  # 代理文件路径
    PROXY_API_URL = ""      # 代理API地址
    PROXY_API_KEY = ""      # 代理API密钥
    
    # 多线程配置
    USE_THREADING = True    # 是否使用多线程
    MAX_WORKERS = 5         # 最大工作线程数
    
    # 增量爬取配置
    INCREMENTAL_MODE = True  # 是否启用增量爬取
    FORCE_FULL_UPDATE = False  # 是否强制全量更新
    FULL_UPDATE_DAYS = 7      # 全量更新间隔天数
    
    # 日志配置
    LOG_LEVEL = "INFO"      # 日志级别: DEBUG, INFO, WARNING, ERROR, CRITICAL
    LOG_FILE = "crawler.log" # 日志文件名
    
    # 数据保存路径
    DATA_DIR = "data"       # 数据保存目录
    
    # 模拟登录配置（用于开发测试）
    MOCK_LOGIN = False  # 是否启用模拟登录
    MOCK_USER_INFO = {
        "username": "admin",
        "role": "管理员",
        "permissions": ["all"]
    }
    
    def __init__(self):
        """初始化配置，可以在这里做一些动态配置"""
        # 转换字典访问方式，允许使用 config["username"] 形式访问
        self.__dict__["__wrapped__"] = {}

    def __getitem__(self, key):
        """支持字典式访问"""
        try:
            return getattr(self, key)
        except AttributeError:
            raise KeyError(key)
            
    def __setitem__(self, key, value):
        """支持字典式赋值"""
        setattr(self, key, value)
            
    def update_from_file(self, config_file):
        """从配置文件更新配置"""
        try:
            import json
            with open(config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
                
            for key, value in config_data.items():
                if hasattr(self, key):
                    setattr(self, key, value)
                    
            return True
        except Exception as e:
            print(f"从配置文件更新配置失败: {str(e)}")
            return False
            
    def update_from_env(self):
        """从环境变量更新配置"""
        try:
            import os
            
            # 遍历当前类的所有属性
            for key in dir(self):
                # 跳过私有属性和方法
                if key.startswith('_') or callable(getattr(self, key)):
                    continue
                    
                # 构造环境变量名(如 USERNAME -> CRAWLER_USERNAME)
                env_key = f"CRAWLER_{key}"
                
                # 检查环境变量是否存在
                if env_key in os.environ:
                    value = os.environ[env_key]
                    
                    # 尝试转换类型
                    attr_value = getattr(self, key)
                    if isinstance(attr_value, bool):
                        value = value.lower() in ('true', '1', 'yes', 'y')
                    elif isinstance(attr_value, int):
                        value = int(value)
                    elif isinstance(attr_value, float):
                        value = float(value)
                        
                    # 更新配置
                    setattr(self, key, value)
                    
            return True
        except Exception as e:
            print(f"从环境变量更新配置失败: {str(e)}")
            return False 