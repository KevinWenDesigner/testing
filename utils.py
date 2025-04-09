#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
工具类文件，提供日志设置、文件操作等通用功能
"""

import os
import logging
from logging.handlers import RotatingFileHandler


def setup_logger(name, log_file='crawler.log', level=logging.INFO):
    """设置日志记录器"""
    # 创建日志目录
    log_dir = os.path.join(os.getcwd(), 'logs')
    create_dir_if_not_exists(log_dir)
    log_path = os.path.join(log_dir, log_file)
    
    # 创建日志记录器
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # 设置格式化器
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # 添加控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 添加文件处理器（滚动日志）
    file_handler = RotatingFileHandler(
        log_path, maxBytes=10*1024*1024, backupCount=5, encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger


def create_dir_if_not_exists(directory):
    """如果目录不存在则创建"""
    if not os.path.exists(directory):
        os.makedirs(directory)
        return True
    return False


def save_to_txt(file_path, content, mode='w', encoding='utf-8'):
    """保存内容到文本文件"""
    try:
        with open(file_path, mode, encoding=encoding) as f:
            f.write(content)
        return True
    except Exception as e:
        print(f"保存文件失败: {str(e)}")
        return False


def read_from_txt(file_path, encoding='utf-8'):
    """从文本文件读取内容"""
    try:
        if not os.path.exists(file_path):
            return None
        with open(file_path, 'r', encoding=encoding) as f:
            content = f.read()
        return content
    except Exception as e:
        print(f"读取文件失败: {str(e)}")
        return None


def get_file_list(directory, ext=None):
    """获取目录下的文件列表，可以按扩展名筛选"""
    if not os.path.exists(directory):
        return []
    
    files = []
    for file in os.listdir(directory):
        file_path = os.path.join(directory, file)
        if os.path.isfile(file_path):
            if ext is None or file.endswith(ext):
                files.append(file_path)
    
    return files


def format_size(size_bytes):
    """格式化文件大小"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.2f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.2f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB" 