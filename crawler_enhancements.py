#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
爬虫增强功能模块，提供验证码识别、代理IP管理、错误处理等增强功能
"""

import os
import time
import json
import random
import logging
import requests
import threading
import queue
import base64
import datetime
from concurrent.futures import ThreadPoolExecutor
from PIL import Image
from io import BytesIO

logger = logging.getLogger('爬虫增强模块')

# 1. 验证码处理优化
class CaptchaHandler:
    """验证码处理类，支持本地OCR和在线API识别"""
    
    def __init__(self, use_api=True, api_key=None):
        self.use_api = use_api
        self.api_key = api_key
        self.ocr_initialized = False
        self.ocr_engine = None
        
        # 如果设置了使用API但未提供API密钥，则尝试从环境变量获取
        if self.use_api and not self.api_key:
            self.api_key = os.environ.get('CAPTCHA_API_KEY')
            
        # 如果不使用API或没有提供API密钥，则尝试初始化本地OCR
        if not self.use_api or not self.api_key:
            self._init_local_ocr()
            
    def _init_local_ocr(self):
        """初始化本地OCR引擎"""
        try:
            import pytesseract
            from PIL import Image, ImageEnhance, ImageFilter
            
            # 检查pytesseract是否可用
            pytesseract.get_tesseract_version()
            
            self.ocr_engine = pytesseract
            self.ocr_initialized = True
            logger.info("本地OCR引擎初始化成功")
        except Exception as e:
            logger.warning(f"本地OCR引擎初始化失败: {str(e)}")
            self.ocr_initialized = False
    
    def preprocess_image(self, image_path):
        """预处理验证码图片以提高识别率"""
        try:
            img = Image.open(image_path)
            
            # 转换为灰度图
            img = img.convert('L')
            
            # 增强对比度
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(2)
            
            # 二值化处理
            threshold = 140
            table = [0 if i < threshold else 255 for i in range(256)]
            img = img.point(table, '1')
            
            # 去除噪点
            img = img.filter(ImageFilter.MedianFilter(3))
            
            # 保存预处理后的图片
            processed_path = image_path.replace('.png', '_processed.png')
            img.save(processed_path)
            
            return processed_path
        except Exception as e:
            logger.error(f"图像预处理失败: {str(e)}")
            return image_path
            
    def recognize_from_file(self, image_path):
        """从文件识别验证码"""
        # 预处理图像
        processed_image = self.preprocess_image(image_path)
        
        if self.use_api and self.api_key:
            return self._recognize_using_api(processed_image)
        elif self.ocr_initialized:
            return self._recognize_using_local_ocr(processed_image)
        else:
            logger.warning("没有可用的验证码识别方式，将返回空结果")
            return None
            
    def recognize_from_element(self, driver, element):
        """直接从网页元素截取并识别验证码"""
        try:
            # 截取元素图像
            element_png = element.screenshot_as_png
            img = Image.open(BytesIO(element_png))
            
            # 保存原始图像
            timestamp = int(time.time())
            original_path = f"captcha_original_{timestamp}.png"
            img.save(original_path)
            
            # 进行识别
            result = self.recognize_from_file(original_path)
            return result
        except Exception as e:
            logger.error(f"从元素识别验证码失败: {str(e)}")
            return None
            
    def _recognize_using_local_ocr(self, image_path):
        """使用本地OCR引擎识别验证码"""
        try:
            img = Image.open(image_path)
            result = self.ocr_engine.image_to_string(img, config='--psm 8 -c tessedit_char_whitelist=0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ')
            
            # 清理结果（去除空格和换行符）
            result = result.strip().replace(' ', '').replace('\n', '')
            
            logger.info(f"本地OCR识别结果: {result}")
            return result
        except Exception as e:
            logger.error(f"本地OCR识别失败: {str(e)}")
            return None
            
    def _recognize_using_api(self, image_path):
        """使用在线API识别验证码"""
        try:
            with open(image_path, 'rb') as f:
                img_base64 = base64.b64encode(f.read()).decode('utf-8')
                
            # 这里使用通用的验证码识别API结构，实际使用时需要替换为特定API的格式
            api_url = "https://api.example.com/v1/ocr/captcha"
            payload = {
                "api_key": self.api_key,
                "image": img_base64,
                "type": "general"
            }
            
            response = requests.post(api_url, json=payload, timeout=10)
            if response.status_code == 200:
                result = response.json().get('result', '')
                logger.info(f"API识别验证码结果: {result}")
                return result
            else:
                logger.warning(f"API识别验证码失败，状态码: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"API识别验证码出错: {str(e)}")
            return None
            

# 2. 代理IP管理
class ProxyManager:
    """代理IP管理器，支持动态更新和检测"""
    
    def __init__(self, proxy_source='file', proxy_file='proxies.txt', proxy_api_url=None, proxy_api_key=None):
        self.proxy_source = proxy_source  # 'file' 或 'api'
        self.proxy_file = proxy_file
        self.proxy_api_url = proxy_api_url
        self.proxy_api_key = proxy_api_key
        self.proxies = []
        self.working_proxies = []
        self.proxy_lock = threading.Lock()
        self.last_update_time = 0
        self.update_interval = 30 * 60  # 默认30分钟更新一次
        
        # 初始加载代理
        self.update_proxies()
        
    def update_proxies(self):
        """更新代理IP列表"""
        with self.proxy_lock:
            current_time = time.time()
            # 检查是否需要更新
            if current_time - self.last_update_time < self.update_interval:
                return
                
            if self.proxy_source == 'file':
                self._load_proxies_from_file()
            else:
                self._fetch_proxies_from_api()
                
            self.last_update_time = current_time
            logger.info(f"代理池已更新，当前有 {len(self.proxies)} 个代理")
    
    def _load_proxies_from_file(self):
        """从文件加载代理IP"""
        try:
            if not os.path.exists(self.proxy_file):
                logger.warning(f"代理文件不存在: {self.proxy_file}")
                return
                
            with open(self.proxy_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            self.proxies = [line.strip() for line in lines if line.strip()]
        except Exception as e:
            logger.error(f"从文件加载代理失败: {str(e)}")
            
    def _fetch_proxies_from_api(self):
        """从API获取代理IP"""
        try:
            headers = {}
            if self.proxy_api_key:
                headers['Authorization'] = f"Bearer {self.proxy_api_key}"
                
            response = requests.get(self.proxy_api_url, headers=headers, timeout=15)
            if response.status_code == 200:
                data = response.json()
                # 假设API返回格式为 {"proxies": ["ip:port", "ip:port", ...]}
                # 根据实际API调整解析逻辑
                self.proxies = data.get('proxies', [])
            else:
                logger.warning(f"从API获取代理失败，状态码: {response.status_code}")
        except Exception as e:
            logger.error(f"从API获取代理出错: {str(e)}")
            
    def get_proxy(self):
        """获取一个可用代理"""
        # 如果需要，更新代理列表
        if not self.proxies:
            self.update_proxies()
            
        with self.proxy_lock:
            # 优先使用已知可用的代理
            if self.working_proxies:
                proxy = random.choice(self.working_proxies)
                logger.debug(f"使用已知可用代理: {proxy}")
                return proxy
                
            # 如果没有可用代理，随机选择一个并验证
            if self.proxies:
                proxy = random.choice(self.proxies)
                if self._verify_proxy(proxy):
                    self.working_proxies.append(proxy)
                    return proxy
                    
            # 没有可用代理，返回None
            logger.warning("没有可用的代理IP")
            return None
            
    def _verify_proxy(self, proxy):
        """验证代理是否可用"""
        try:
            # 构建代理配置
            proxies = {
                "http": f"http://{proxy}",
                "https": f"http://{proxy}"
            }
            
            # 尝试访问一个网站来验证代理
            response = requests.get(
                "https://www.baidu.com", 
                proxies=proxies, 
                timeout=10
            )
            
            if response.status_code == 200:
                logger.debug(f"代理验证成功: {proxy}")
                return True
            else:
                logger.debug(f"代理验证失败，状态码: {response.status_code}, 代理: {proxy}")
                return False
        except Exception as e:
            logger.debug(f"代理验证出错: {proxy}, 错误: {str(e)}")
            return False
            
    def report_proxy_failure(self, proxy):
        """报告代理失效"""
        with self.proxy_lock:
            if proxy in self.working_proxies:
                self.working_proxies.remove(proxy)
            logger.info(f"已将代理标记为失效: {proxy}")


# 3. 错误处理增强
class ErrorHandler:
    """增强的错误处理器，根据错误类型采取不同策略"""
    
    def __init__(self):
        # 错误类型及其对应的处理策略
        self.error_strategies = {
            "network": {
                "max_retries": 5,
                "backoff_factor": 2,  # 指数退避因子
                "initial_wait": 1,     # 初始等待时间（秒）
            },
            "captcha": {
                "max_retries": 3,
                "backoff_factor": 1.5,
                "initial_wait": 2,
            },
            "login": {
                "max_retries": 3,
                "backoff_factor": 1,
                "initial_wait": 5,
            },
            "selenium": {
                "max_retries": 3,
                "backoff_factor": 1.5,
                "initial_wait": 3,
            },
            "parsing": {
                "max_retries": 2,
                "backoff_factor": 1,
                "initial_wait": 1,
            },
            "default": {
                "max_retries": 3,
                "backoff_factor": 1.5,
                "initial_wait": 2,
            }
        }
        
        # 保存各种错误的重试计数
        self.retry_counts = {}
        
    def classify_error(self, exception):
        """根据异常类型分类错误"""
        error_type = "default"
        
        if isinstance(exception, requests.exceptions.RequestException):
            error_type = "network"
        elif isinstance(exception, (requests.exceptions.Timeout, requests.exceptions.ConnectTimeout)):
            error_type = "network"
        elif "selenium.common.exceptions" in str(type(exception)):
            error_type = "selenium"
        elif "验证码" in str(exception).lower() or "captcha" in str(exception).lower():
            error_type = "captcha"
        elif "登录" in str(exception).lower() or "login" in str(exception).lower():
            error_type = "login"
        elif "解析" in str(exception).lower() or "parse" in str(exception).lower():
            error_type = "parsing"
            
        return error_type
        
    def handle_error(self, error_id, exception):
        """处理特定错误，返回是否应该重试"""
        error_type = self.classify_error(exception)
        strategy = self.error_strategies.get(error_type, self.error_strategies["default"])
        
        # 确保有重试计数记录
        if error_id not in self.retry_counts:
            self.retry_counts[error_id] = 0
            
        # 检查是否超过最大重试次数
        if self.retry_counts[error_id] >= strategy["max_retries"]:
            logger.warning(f"错误 {error_id} ({error_type}) 已达到最大重试次数 {strategy['max_retries']}，放弃重试")
            self.retry_counts[error_id] = 0  # 重置计数
            return False
            
        # 计算等待时间
        wait_time = strategy["initial_wait"] * (strategy["backoff_factor"] ** self.retry_counts[error_id])
        
        # 增加重试计数
        self.retry_counts[error_id] += 1
        
        logger.info(f"将在 {wait_time:.2f} 秒后尝试第 {self.retry_counts[error_id]} 次重试 错误 {error_id} ({error_type})")
        
        # 等待
        time.sleep(wait_time)
        
        return True
        
    def reset_retry_count(self, error_id):
        """重置特定错误的重试计数"""
        if error_id in self.retry_counts:
            self.retry_counts[error_id] = 0
            logger.debug(f"已重置错误 {error_id} 的重试计数")


# 4. 多线程爬取
class ThreadedCrawler:
    """多线程爬虫管理器"""
    
    def __init__(self, max_workers=5, task_queue_size=100):
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.task_queue = queue.Queue(maxsize=task_queue_size)
        self.results = []
        self.results_lock = threading.Lock()
        self.running = False
        self.worker_threads = []
        
    def add_task(self, task_func, *args, **kwargs):
        """添加爬取任务到队列"""
        try:
            # 创建任务对象
            task = {
                "func": task_func,
                "args": args,
                "kwargs": kwargs
            }
            
            # 添加到队列
            self.task_queue.put(task, block=True, timeout=10)
            logger.debug(f"已添加新任务到队列，当前队列大小: {self.task_queue.qsize()}")
            return True
        except queue.Full:
            logger.warning("任务队列已满，无法添加新任务")
            return False
        except Exception as e:
            logger.error(f"添加任务到队列时出错: {str(e)}")
            return False
            
    def start_workers(self):
        """启动工作线程"""
        if self.running:
            logger.warning("工作线程已在运行中")
            return
            
        self.running = True
        logger.info(f"启动 {self.max_workers} 个工作线程")
        
        for i in range(self.max_workers):
            thread = threading.Thread(
                target=self._worker_thread,
                name=f"CrawlerWorker-{i+1}"
            )
            thread.daemon = True  # 设置为守护线程
            thread.start()
            self.worker_threads.append(thread)
            
    def _worker_thread(self):
        """工作线程函数"""
        thread_name = threading.current_thread().name
        logger.info(f"工作线程 {thread_name} 已启动")
        
        while self.running:
            try:
                # 从队列获取任务，最多等待10秒
                task = self.task_queue.get(block=True, timeout=10)
                
                # 执行任务
                try:
                    func = task["func"]
                    args = task["args"]
                    kwargs = task["kwargs"]
                    
                    logger.debug(f"线程 {thread_name} 开始执行任务: {func.__name__}")
                    result = func(*args, **kwargs)
                    
                    # 保存结果
                    if result is not None:
                        with self.results_lock:
                            self.results.append(result)
                        logger.debug(f"线程 {thread_name} 任务 {func.__name__} 执行完成，获取到结果")
                    else:
                        logger.debug(f"线程 {thread_name} 任务 {func.__name__} 执行完成，无结果")
                        
                except Exception as e:
                    logger.error(f"线程 {thread_name} 执行任务时出错: {str(e)}")
                    import traceback
                    logger.error(traceback.format_exc())
                    
                finally:
                    # 标记任务完成
                    self.task_queue.task_done()
                    
            except queue.Empty:
                # 队列为空，继续等待
                continue
            except Exception as e:
                logger.error(f"工作线程 {thread_name} 出现异常: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
                
        logger.info(f"工作线程 {thread_name} 退出")
                
    def stop_workers(self, wait_for_completion=True):
        """停止工作线程"""
        logger.info("停止所有工作线程")
        self.running = False
        
        if wait_for_completion:
            # 等待队列中的任务完成
            logger.info("等待队列中的任务完成")
            self.task_queue.join()
            
        # 等待所有线程结束
        for thread in self.worker_threads:
            if thread.is_alive():
                thread.join(timeout=3)  # 最多等待3秒
                
        logger.info("所有工作线程已停止")
        
    def get_results(self, clear=True):
        """获取爬取结果"""
        with self.results_lock:
            results = self.results.copy()
            if clear:
                self.results.clear()
        return results


# 5. 增量更新器
class IncrementalUpdater:
    """支持增量更新的数据管理器"""
    
    def __init__(self, data_dir="data", checkpoint_file="crawler_checkpoint.json"):
        self.data_dir = data_dir
        self.checkpoint_file = os.path.join(data_dir, checkpoint_file)
        self.last_crawl_time = None
        self.last_inquiry_ids = set()
        
        # 确保数据目录存在
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
            
        # 加载检查点
        self.load_checkpoint()
        
    def load_checkpoint(self):
        """加载上次爬取的检查点信息"""
        try:
            if os.path.exists(self.checkpoint_file):
                with open(self.checkpoint_file, 'r', encoding='utf-8') as f:
                    checkpoint = json.load(f)
                    
                # 获取上次爬取时间
                last_time_str = checkpoint.get('last_crawl_time')
                if last_time_str:
                    self.last_crawl_time = datetime.datetime.fromisoformat(last_time_str)
                    
                # 获取上次爬取的问诊ID集合
                self.last_inquiry_ids = set(checkpoint.get('last_inquiry_ids', []))
                
                logger.info(f"加载检查点成功，上次爬取时间: {self.last_crawl_time}, 问诊ID数量: {len(self.last_inquiry_ids)}")
        except Exception as e:
            logger.error(f"加载检查点失败: {str(e)}")
            self.last_crawl_time = None
            self.last_inquiry_ids = set()
            
    def save_checkpoint(self, inquiry_ids=None):
        """保存当前爬取检查点"""
        try:
            checkpoint = {
                'last_crawl_time': datetime.datetime.now().isoformat(),
                'last_inquiry_ids': list(self.last_inquiry_ids if inquiry_ids is None else inquiry_ids)
            }
            
            with open(self.checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump(checkpoint, f, ensure_ascii=False, indent=2)
                
            logger.info(f"保存检查点成功，问诊ID数量: {len(checkpoint['last_inquiry_ids'])}")
        except Exception as e:
            logger.error(f"保存检查点失败: {str(e)}")
            
    def filter_new_inquiries(self, inquiries):
        """过滤出新的问诊记录"""
        if not inquiries:
            return []
            
        # 如果没有上次爬取的记录，则所有记录都视为新记录
        if not self.last_inquiry_ids:
            # 更新ID集合
            current_ids = {inq['inquiryId'] for inq in inquiries if 'inquiryId' in inq}
            self.last_inquiry_ids = current_ids
            return inquiries
            
        # 根据ID过滤新记录
        new_inquiries = []
        current_ids = set()
        
        for inquiry in inquiries:
            inquiry_id = inquiry.get('inquiryId')
            if inquiry_id:
                current_ids.add(inquiry_id)
                # 如果是新ID，则加入新记录列表
                if inquiry_id not in self.last_inquiry_ids:
                    new_inquiries.append(inquiry)
                    
        # 更新ID集合
        self.last_inquiry_ids = current_ids
        
        logger.info(f"过滤出 {len(new_inquiries)} 条新问诊记录，共 {len(inquiries)} 条记录")
        return new_inquiries
        
    def need_full_update(self, force=False, days_threshold=7):
        """判断是否需要全量更新"""
        if force:
            return True
            
        # 如果没有上次爬取时间，则需要全量更新
        if not self.last_crawl_time:
            return True
            
        # 计算距离上次爬取的天数
        days_passed = (datetime.datetime.now() - self.last_crawl_time).days
        
        # 如果超过阈值天数，则进行全量更新
        if days_passed >= days_threshold:
            logger.info(f"距离上次爬取已超过 {days_passed} 天，将进行全量更新")
            return True
            
        return False 