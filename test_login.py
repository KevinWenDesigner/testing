#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
简单的登录测试脚本
"""

from main import MedicalConsultCrawler
from config import Config
from utils import setup_logger

# 设置日志记录
logger = setup_logger('登录测试')

def test_login():
    """测试登录功能"""
    logger.info("开始测试登录功能...")
    
    # 创建配置
    config = Config()
    
    # 创建爬虫实例
    crawler = MedicalConsultCrawler(config)
    
    # 测试登录
    success = crawler.login()
    
    if success:
        logger.info("登录成功!")
    else:
        logger.error("登录失败!")
    
    # 关闭浏览器
    if crawler.driver:
        logger.info("关闭浏览器...")
        crawler.driver.quit()
    
    return success

if __name__ == "__main__":
    test_login() 