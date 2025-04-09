#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import time
import json
import logging
import random
import requests
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from config import Config
from utils import setup_logger, save_to_txt, create_dir_if_not_exists
from crawler_enhancements import CaptchaHandler, ProxyManager, ErrorHandler, ThreadedCrawler, IncrementalUpdater

# 引入Selenium相关库
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# 设置日志记录
logger = setup_logger('医疗问诊数据爬虫')

class MedicalConsultCrawler:
    """医疗咨询平台问诊数据爬虫"""
    
    def __init__(self, config):
        """初始化爬虫"""
        self.config = config
        self.LOGIN_URL = config.LOGIN_URL
        self.session = requests.Session()
        self.driver = None
        self.retry_count = 0  # 登录重试计数
        self.is_logged_in = False  # 登录状态标志
        
        # 设置会话的User-Agent
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        self.data_dir = os.path.join(os.getcwd(), 'data')
        create_dir_if_not_exists(self.data_dir)
        
        # 初始化增强模块
        self.captcha_handler = CaptchaHandler(
            use_api=config.CAPTCHA_AUTO_RECOGNIZE,
            api_key=config.CAPTCHA_API_KEY
        )
        self.proxy_manager = ProxyManager(
            proxy_source=config.PROXY_SOURCE,
            proxy_file=config.PROXY_FILE,
            proxy_api_url=config.PROXY_API_URL,
            proxy_api_key=config.PROXY_API_KEY
        )
        self.error_handler = ErrorHandler()
        self.incremental_updater = IncrementalUpdater(data_dir=self.data_dir)
        
        # 初始化多线程爬虫管理器
        self.threaded_crawler = ThreadedCrawler(
            max_workers=config.MAX_WORKERS
        )
        
    def init_browser(self):
        """初始化Selenium WebDriver"""
        logger.info('初始化Selenium WebDriver...')
        try:
            chrome_options = Options()
            
            # 如果不需要看到浏览器界面，可以设置无头模式
            if self.config.HEADLESS_MODE:
                chrome_options.add_argument('--headless')
            
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--window-size=1920,1080')
            
            # 设置User-Agent
            chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
            
            # 禁用浏览器扩展
            chrome_options.add_argument('--disable-extensions')
            
            # 禁用安全策略
            chrome_options.add_argument('--disable-web-security')
            
            # 添加忽略SSL证书错误的选项
            chrome_options.add_argument('--ignore-certificate-errors')
            chrome_options.add_argument('--ignore-ssl-errors')
            chrome_options.add_argument('--allow-insecure-localhost')
            
            # 设置默认下载目录
            prefs = {
                "download.default_directory": os.path.join(os.getcwd(), "downloads"),
                "download.prompt_for_download": False,
                "download.directory_upgrade": True,
                "safebrowsing.enabled": False
            }
            chrome_options.add_experimental_option("prefs", prefs)
            
            # 添加实验选项，忽略错误
            chrome_options.add_experimental_option('excludeSwitches', ['enable-logging', 'enable-automation'])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # 如果配置了使用代理，则添加代理设置
            proxy = None
            if self.config.USE_PROXY:
                proxy = self.proxy_manager.get_proxy()
                if proxy:
                    chrome_options.add_argument(f'--proxy-server={proxy}')
                    logger.info(f'使用代理: {proxy}')
            
            # 创建WebDriver实例，使用webdriver_manager自动下载适合的ChromeDriver
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.set_page_load_timeout(60)  # 增加页面加载超时时间
            
            # 保存使用的代理信息，用于失败时报告
            self.current_proxy = proxy
            
            logger.info('WebDriver初始化成功')
            return True
        except Exception as e:
            error_id = f"init_browser_{int(time.time())}"
            logger.error(f'初始化WebDriver失败: {str(e)}')
            
            # 使用增强的错误处理
            if self.error_handler.handle_error(error_id, e):
                logger.info("重试初始化WebDriver")
                return self.init_browser()
            else:
                return False
        
    def login(self):
        """登录网站，获取有效的会话"""
        # 如果配置了模拟登录，直接返回登录成功
        if self.config.MOCK_LOGIN:
            logging.info("启用了模拟登录模式，跳过实际登录过程")
            self.is_logged_in = True
            return True
        
        if not self.init_browser():
            logging.error("Selenium初始化失败，无法登录")
            return False
            
        logging.info("尝试使用Selenium登录...")
        
        try:
            # 打开登录页面
            logging.info(f"尝试访问登录页面: {self.LOGIN_URL}")
            self.driver.get(self.LOGIN_URL)
            time.sleep(3)  # 等待页面加载
            
            # 检查当前URL，确认是否正确加载了登录页面
            current_url = self.driver.current_url
            logging.info(f"当前加载页面URL: {current_url}")
            
            # 保存页面源码，用于调试
            try:
                page_source = self.driver.page_source
                with open("login_page_source.html", "w", encoding="utf-8") as f:
                    f.write(page_source)
                logging.info("登录页面源码已保存至 login_page_source.html")
            except:
                logging.warning("无法保存登录页面源码")
            
            # 截图并保存登录页面
            self.save_screenshot("login_page.png")
            logging.info("登录页面已截图保存")
            
            # 等待页面加载完成
            time.sleep(2)
            
            # 根据分析的页面结构，使用正确的选择器定位用户名输入框
            try:
                username_input = self.driver.find_element(By.CSS_SELECTOR, "input[name='userName']")
                logging.info("找到用户名输入框")
            except:
                logging.error("无法找到用户名输入框，尝试备选选择器")
                try:
                    username_input = self.driver.find_element(By.CSS_SELECTOR, "input[placeholder='请输入用户名']")
                    logging.info("使用备选选择器找到用户名输入框")
                except:
                    logging.error("所有备选选择器都无法找到用户名输入框")
                    self.save_screenshot("username_not_found.png")
                    return False
            
            # 填写用户名
            logging.info(f"尝试填写用户名: {self.config.USERNAME}")
            username_input.clear()
            username_input.send_keys(self.config.USERNAME)
            time.sleep(1)
            
            # 定位密码输入框
            try:
                password_input = self.driver.find_element(By.CSS_SELECTOR, "input[type='password']")
                logging.info("找到密码输入框")
            except:
                logging.error("无法找到密码输入框，尝试备选选择器")
                try:
                    password_input = self.driver.find_element(By.CSS_SELECTOR, "input[placeholder='请输入密码']")
                    logging.info("使用备选选择器找到密码输入框")
                except:
                    logging.error("所有备选选择器都无法找到密码输入框")
                    self.save_screenshot("password_not_found.png")
                    return False
            
            # 填写密码
            logging.info(f"尝试填写密码: {self.config.PASSWORD[:3]}***")
            password_input.clear()
            password_input.send_keys(self.config.PASSWORD)
            time.sleep(1)
            
            # 查找验证码图片元素
            try:
                captcha_img = self.driver.find_element(By.CSS_SELECTOR, "img[src*='captcha']")
                logging.info("找到验证码图片")
                
                # 自动识别验证码或等待用户输入
                if self.config.CAPTCHA_AUTO_RECOGNIZE:
                    # 使用验证码处理器自动识别
                    captcha_code = self.captcha_handler.recognize_from_element(self.driver, captcha_img)
                    logging.info(f"自动识别验证码结果: {captcha_code}")
                else:
                    # 保存验证码图片供用户查看
                    captcha_filename = "captcha_page.png"
                    self.save_screenshot(captcha_filename)
                    
                    # 尝试单独保存验证码图片
                    try:
                        captcha_img_path = os.path.join("screenshots", "captcha_only.png")
                        captcha_img.screenshot(captcha_img_path)
                        logging.info(f"验证码图片已保存为 {captcha_img_path}")
                        print(f"\n验证码图片已保存: {os.path.abspath(captcha_img_path)}")
                    except Exception as e:
                        logging.warning(f"无法单独保存验证码图片: {str(e)}")
                    
                    # 使用更醒目的提示
                    print("\n" + "*" * 50)
                    print("* 请查看浏览器上的验证码，并在下方输入")
                    print("* 验证码图片也已保存在screenshots目录")
                    print("*" * 50)
                    
                    # 等待用户输入验证码
                    captcha_code = input("\n请输入验证码 > ")
                    
                    # 记录用户输入的验证码
                    logging.info(f"用户输入的验证码: {captcha_code}")
                
                if not captcha_code:
                    logging.warning("未能获取有效的验证码")
                    print("您没有输入验证码，将使用默认值尝试登录，但可能会失败")
                    captcha_code = "1234"  # 使用默认值尝试
                    print(f"将使用默认验证码: {captcha_code}")
                
                # 填写验证码
                try:
                    captcha_input = self.driver.find_element(By.CSS_SELECTOR, "input[name='captcha']")
                    logging.info("找到验证码输入框")
                except:
                    logging.error("无法找到验证码输入框，尝试备选选择器")
                    try:
                        captcha_input = self.driver.find_element(By.CSS_SELECTOR, "input[placeholder='请输入验证码']")
                        logging.info("使用备选选择器找到验证码输入框")
                    except:
                        logging.error("尝试更多验证码输入框选择器")
                        try:
                            # 尝试使用XPath定位验证码输入框
                            selectors = [
                                "//input[@type='text' and contains(@placeholder, '验证码')]",
                                "//input[contains(@class, 'captcha')]",
                                "//div[contains(@class, 'captcha')]//input",
                                "//div[contains(text(), '验证码')]/following::input[1]",
                                "//span[contains(text(), '验证码')]/following::input[1]",
                                "//input[@type='text' and not(@name='userName') and not(@type='password')]",
                            ]
                            
                            for selector in selectors:
                                try:
                                    captcha_input = self.driver.find_element(By.XPATH, selector)
                                    logging.info(f"使用XPath选择器找到验证码输入框: {selector}")
                                    break
                                except:
                                    continue
                            
                            # 如果上面的都失败了，尝试找到所有的输入框
                            if not captcha_input:
                                # 找到所有输入字段
                                inputs = self.driver.find_elements(By.CSS_SELECTOR, "input[type='text']")
                                if len(inputs) >= 3:  # 假设第三个是验证码输入框
                                    captcha_input = inputs[2]
                                    logging.info("使用第三个文本输入框作为验证码输入框")
                        except:
                            logging.error("所有备选选择器都无法找到验证码输入框")
                            self.save_screenshot("captcha_not_found.png")
                            
                            # 保存页面内所有输入框信息以便调试
                            try:
                                inputs = self.driver.find_elements(By.TAG_NAME, "input")
                                logging.info(f"页面上找到 {len(inputs)} 个输入框")
                                for i, input_elem in enumerate(inputs):
                                    try:
                                        input_type = input_elem.get_attribute("type")
                                        input_name = input_elem.get_attribute("name")
                                        input_placeholder = input_elem.get_attribute("placeholder")
                                        logging.info(f"输入框 {i+1}: type={input_type}, name={input_name}, placeholder={input_placeholder}")
                                    except:
                                        pass
                            except:
                                pass
                            
                            # 保存完整的页面源码
                            try:
                                with open("login_page_full.html", "w", encoding="utf-8") as f:
                                    f.write(self.driver.page_source)
                                logging.info("已保存完整页面源码以便调试")
                            except:
                                pass
                                
                            return False
                
                captcha_input.clear()
                captcha_input.send_keys(captcha_code)
                time.sleep(1)
                
            except:
                logging.warning("未找到验证码图片元素，可能不需要验证码或元素选择器不正确")
                self.save_screenshot("no_captcha_page.png")
            
            # 点击登录按钮
            try:
                # 尝试多种方式查找登录按钮
                login_button = None
                
                # 方法1: 使用CSS选择器
                try:
                    login_button = self.driver.find_element(By.CSS_SELECTOR, ".el-button--primary")
                    logging.info("找到登录按钮 (CSS方式)")
                except:
                    pass
                    
                # 方法2: 使用XPath - 按文本内容查找
                if not login_button:
                    try:
                        login_button = self.driver.find_element(By.XPATH, "//button[contains(.,'登录')]")
                        logging.info("找到登录按钮 (XPath文本方式)")
                    except:
                        pass
                
                # 方法3: 使用元素类型和位置
                if not login_button:
                    try:
                        # 查找所有按钮
                        buttons = self.driver.find_elements(By.TAG_NAME, "button")
                        if buttons:
                            login_button = buttons[0]  # 假设第一个按钮是登录按钮
                            logging.info("找到登录按钮 (标签方式)")
                    except:
                        pass
                
                # 尝试使用不同方法点击按钮
                if login_button:
                    # 方法1: 直接点击
                    try:
                        login_button.click()
                        logging.info("已直接点击登录按钮")
                    except:
                        logging.warning("直接点击登录按钮失败，尝试JS点击")
                        
                        # 方法2: 使用JavaScript点击
                        try:
                            self.driver.execute_script("arguments[0].click();", login_button)
                            logging.info("已使用JS点击登录按钮")
                        except Exception as e:
                            logging.error(f"JS点击登录按钮失败: {str(e)}")
                            
                            # 方法3: 使用坐标点击
                            try:
                                from selenium.webdriver.common.action_chains import ActionChains
                                ActionChains(self.driver).move_to_element(login_button).click().perform()
                                logging.info("已使用ActionChains点击登录按钮")
                            except Exception as e:
                                logging.error(f"ActionChains点击登录按钮失败: {str(e)}")
                                raise
                else:
                    # 方法4: 直接使用JavaScript定位并点击
                    try:
                        self.driver.execute_script("""
                            var buttons = document.querySelectorAll('button');
                            for(var i=0; i<buttons.length; i++) {
                                if(buttons[i].textContent.includes('登录')) {
                                    buttons[i].click();
                                    return true;
                                }
                            }
                            // 如果没有找到包含'登录'的按钮，点击第一个按钮
                            if(buttons.length > 0) {
                                buttons[0].click();
                                return true;
                            }
                            return false;
                        """)
                        logging.info("已使用JS脚本查找并点击登录按钮")
                    except Exception as e:
                        logging.error(f"JS脚本点击登录按钮失败: {str(e)}")
                        self.save_screenshot("login_button_js_error.png")
                        return False
            except Exception as e:
                logging.error(f"点击登录按钮过程中出错: {str(e)}")
                self.save_screenshot("login_button_error.png")
                return False
            
            # 等待登录结果
            time.sleep(5)
            self.save_screenshot("after_login.png")
            
            # 检查是否登录成功
            current_url = self.driver.current_url
            logging.info(f"登录后当前URL: {current_url}")
            
            if "login" not in current_url or "home" in current_url:
                logging.info("Selenium登录成功!")
                
                # 获取cookies并添加到requests session
                cookies = self.driver.get_cookies()
                logging.info(f"获取到 {len(cookies)} 个cookies")
                
                for cookie in cookies:
                    self.session.cookies.set(cookie['name'], cookie['value'])
                    logging.debug(f"设置cookie: {cookie['name']} = {cookie['value']}")
                
                self.is_logged_in = True
                self.retry_count = 0  # 重置重试计数
                return True
                
            else:
                # 检查是否有错误信息
                try:
                    error_msg = self.driver.find_element(By.CSS_SELECTOR, ".el-message--error, .el-message__content")
                    logging.error(f"登录失败，错误信息: {error_msg.text}")
                except:
                    logging.error("登录失败，但未找到具体错误信息")
                
                # 如果使用代理且登录失败，报告代理失效
                if self.current_proxy:
                    self.proxy_manager.report_proxy_failure(self.current_proxy)
                
                self.retry_count += 1
                if self.retry_count < self.config.MAX_RETRIES:
                    logging.info(f"登录失败，尝试第 {self.retry_count + 1} 次登录...")
                    # 重置WebDriver，使用新代理
                    if self.driver:
                        self.driver.quit()
                        self.driver = None
                    return self.login()
                    
                logging.error("登录失败次数过多，放弃登录")
                return False
        
        except Exception as e:
            error_id = f"login_{int(time.time())}"
            logging.error(f"Selenium登录过程出现异常: {str(e)}")
            import traceback
            logging.error(traceback.format_exc())
            self.save_screenshot("login_exception.png")
            
            # 使用增强的错误处理
            if self.error_handler.handle_error(error_id, e):
                # 重置WebDriver，使用新代理
                if self.driver:
                    self.driver.quit()
                    self.driver = None
                return self.login()
            else:
                logging.error("登录异常处理失败，放弃登录")
                return False

    def check_pagination(self):
        """检查是否有下一页并点击下一页按钮"""
        try:
            # 查找分页元素
            pagination = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".pagination, .page-nav, nav.pagination"))
            )
            
            # 查找下一页按钮（多种可能的选择器）
            next_page_button = None
            for selector in [
                "li.next:not(.disabled) a", 
                "a.next:not(.disabled)", 
                "a[aria-label='Next']:not(.disabled)",
                "button.next:not([disabled])",
                "//a[contains(text(), '下一页') and not(contains(@class, 'disabled'))]",
                "//button[contains(text(), '下一页') and not(@disabled)]"
            ]:
                try:
                    if selector.startswith("//"):
                        # XPath 选择器
                        elements = pagination.find_elements(By.XPATH, selector)
                    else:
                        # CSS 选择器
                        elements = pagination.find_elements(By.CSS_SELECTOR, selector)
                        
                    if elements:
                        next_page_button = elements[0]
                        break
                except:
                    continue
            
            if next_page_button and next_page_button.is_displayed() and next_page_button.is_enabled():
                logger.info("找到下一页按钮，将点击进入下一页")
                # 保存点击前的截图
                self.save_screenshot("before_next_page.png")
                
                # 使用JavaScript点击，避免元素不可点击的问题
                self.driver.execute_script("arguments[0].click();", next_page_button)
                
                # 等待页面加载
                time.sleep(3)
                
                # 保存点击后的截图
                self.save_screenshot("after_next_page.png")
                
                # 检查页面是否已更新
                # (这里可以添加其他验证逻辑，如检查URL参数、页码显示等)
                
                return True
            else:
                logger.info("没有找到可用的下一页按钮，可能已经是最后一页")
                return False
                
        except Exception as e:
            error_id = f"check_pagination_{int(time.time())}"
            logger.error(f"检查分页时出错: {str(e)}")
            
            # 使用增强的错误处理
            if self.error_handler.handle_error(error_id, e):
                return self.check_pagination()
            else:
                logger.warning("分页检查失败，假设没有下一页")
                return False

    def save_screenshot(self, filename):
        """保存当前浏览器页面截图"""
        if not self.driver:
            logging.warning(f"无法保存截图 {filename}，WebDriver未初始化")
            return False
            
        try:
            screenshot_dir = "screenshots"
            if not os.path.exists(screenshot_dir):
                os.makedirs(screenshot_dir)
                
            filepath = os.path.join(screenshot_dir, filename)
            self.driver.save_screenshot(filepath)
            logging.info(f"截图已保存: {filepath}")
            return True
        except Exception as e:
            logging.error(f"保存截图失败 {filename}: {str(e)}")
            return False
    
    def get_inquiry_list(self, page=1, page_size=20):
        """获取问诊列表"""
        logging.info(f"获取问诊列表: 第{page}页, 每页{page_size}条")
        
        if not self.check_login_status():
            logging.error("获取问诊列表失败: 未登录")
            return []
            
        # 如果是模拟登录，返回模拟数据
        if self.config.MOCK_LOGIN:
            logging.info("使用模拟数据返回问诊列表")
            mock_data = []
            # 生成10条模拟数据
            for i in range(1, 11):
                mock_data.append({
                    "inquiryId": f"MOCK{page}_{i}",
                    "patientName": f"患者{page}_{i}",
                    "inquiryTime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "status": "待回复" if i % 3 == 0 else ("已完成" if i % 3 == 1 else "进行中"),
                    "department": "内科" if i % 2 == 0 else "外科",
                    "page": page
                })
            return mock_data
        
        try:
            # 创建调试目录
            debug_dir = "debug"
            if not os.path.exists(debug_dir):
                os.makedirs(debug_dir)
            
            # 尝试多个可能的URL
            url_templates = [
                "https://consult.ht-healthcare.com/manage/#/inquiryManage/inquiryMisOrderList",
                "https://consult.ht-healthcare.com/manage/login#/inquiryManage/inquiryMisOrderList",
                "https://consult.ht-healthcare.com/manage/#/home",  # 如果直接导航失败，可以先导航到首页
                "https://consult.ht-healthcare.com/manage/app/workbench",
                "https://consult.ht-healthcare.com/manage/inquiryManage/inquiryMisOrderList"
            ]
            
            success = False
            error_msgs = []
            
            # 尝试每个URL模板
            for url_template in url_templates:
                try:
                    workbench_url = url_template
                    logging.info(f"尝试访问URL: {workbench_url}")
                    
                    self.driver.get(workbench_url)
                    import time  # 确保每个作用域都有time模块导入
                    time.sleep(5)  # 增加等待时间，确保页面完全加载
                    
                    # 保存截图，用于调试
                    self.save_screenshot(f"page_attempt_{url_templates.index(url_template)}.png")
                    current_url = self.driver.current_url
                    logging.info(f"加载后当前URL: {current_url}")
                    
                    # 如果URL中包含login，则表示跳转到了登录页，说明会话失效
                    if "login" in current_url and "#/home" not in current_url:
                        error_msgs.append(f"访问 {workbench_url} 后跳转到登录页，可能会话失效")
                        # 尝试重新登录
                        if self.login():
                            # 登录成功后重新尝试该URL
                            logging.info("重新登录成功，再次尝试访问原URL")
                            self.driver.get(workbench_url)
                            import time  # 确保每个作用域都有time模块导入
                            time.sleep(5)
                            current_url = self.driver.current_url
                            if "login" in current_url and "#/home" not in current_url:
                                # 仍然跳转到登录页，说明URL不正确
                                continue
                        else:
                            # 登录失败，跳过该URL
                            continue
                    
                    # 检查页面是否有404错误
                    if "404" in self.driver.title or "找不到页面" in self.driver.title or "Not Found" in self.driver.title:
                        error_msgs.append(f"URL {workbench_url} 返回404错误")
                        # 保存页面源码，用于分析
                        try:
                            with open(f"error_404_{url_templates.index(url_template)}.html", "w", encoding="utf-8") as f:
                                f.write(self.driver.page_source)
                        except:
                            pass
                        continue
                        
                    # 检查是否存在表格数据
                    try:
                        # 尝试使用不同的选择器查找表格数据
                        table_selectors = [
                            ".el-table", 
                            ".el-table__body", 
                            ".inquiry-list",
                            "[class*='table']",
                            ".el-table__row",
                            ".dataTable"
                        ]
                        
                        found_table = False
                        for selector in table_selectors:
                            try:
                                tables = self.driver.find_elements(By.CSS_SELECTOR, selector)
                                if tables:
                                    found_table = True
                                    logging.info(f"在URL {workbench_url} 中找到表格元素: {selector}, 数量: {len(tables)}")
                                    break
                            except:
                                pass
                                
                        if not found_table:
                            # 检查是否正在加载中
                            try:
                                loading_elements = self.driver.find_elements(By.CSS_SELECTOR, ".el-loading-mask, .loading")
                                if loading_elements and any(elem.is_displayed() for elem in loading_elements):
                                    logging.info("页面正在加载中，等待完成...")
                                    import time  # 确保每个作用域都有time模块导入
                                    time.sleep(5)  # 多等待一段时间
                                    
                                    # 再次检查表格元素
                                    for selector in table_selectors:
                                        try:
                                            tables = self.driver.find_elements(By.CSS_SELECTOR, selector)
                                            if tables:
                                                found_table = True
                                                logging.info(f"等待后找到表格元素: {selector}, 数量: {len(tables)}")
                                                break
                                        except:
                                            pass
                            except:
                                pass
                                
                            if not found_table:
                                # 使用JavaScript检查DOM结构
                                try:
                                    table_count = self.driver.execute_script("""
                                        var tables = document.querySelectorAll('table, .el-table, [class*="table"]');
                                        return tables.length;
                                    """)
                                    if table_count > 0:
                                        found_table = True
                                        logging.info(f"通过JavaScript找到 {table_count} 个表格元素")
                                except:
                                    pass
                            
                            if not found_table:
                                error_msgs.append(f"URL {workbench_url} 没有找到表格数据")
                                continue
                    except Exception as e:
                        logging.warning(f"检查表格数据时出错: {str(e)}")
                    
                    # 如果没有继续到下一个URL，则认为当前URL有效
                    success = True
                    break
                    
                except Exception as e:
                    error_msgs.append(f"访问 {url_template} 出错: {str(e)}")
                    continue
            
            if not success:
                logging.error(f"所有URL尝试都失败: {', '.join(error_msgs)}")
                self.save_screenshot("all_urls_failed.png")
                
                # 额外尝试：针对Vue/React单页应用的特殊处理
                logging.info("尝试使用JavaScript导航函数")
                success = self.navigate_to_inquiry_page_js()
                
                if not success:
                    logging.error("JavaScript导航也失败了")
                    return []
                
            # 保存工作台截图，用于调试
            self.save_screenshot(f"inquiryList_page_{page}.png")
            
            # 保存完整页面源码和详细结构信息
            try:
                # 保存完整页面源码
                page_source = self.driver.page_source
                with open(f"{debug_dir}/inquiryList_full_source_{page}.html", "w", encoding="utf-8") as f:
                    f.write(page_source)
                logging.info(f"完整页面源码已保存至 {debug_dir}/inquiryList_full_source_{page}.html")
                
                # 获取并保存表格结构信息
                table_info = self.driver.execute_script("""
                    var result = {
                        tables: [],
                        rows: []
                    };
                    
                    // 分析所有表格
                    var tables = document.querySelectorAll('table, .el-table, [class*="table"]');
                    for (var i = 0; i < tables.length; i++) {
                        var tableInfo = {
                            index: i,
                            id: tables[i].id || '',
                            className: tables[i].className || '',
                            rowCount: tables[i].rows ? tables[i].rows.length : 0,
                            structure: {}
                        };
                        result.tables.push(tableInfo);
                    }
                    
                    // 详细分析表格行
                    var rows = document.querySelectorAll('.el-table__row, tr, .inquiry-item, [data-row-key]');
                    for (var i = 0; i < Math.min(rows.length, 5); i++) { // 仅分析前5行
                        var row = rows[i];
                        var rowInfo = {
                            index: i,
                            id: row.id || '',
                            className: row.className || '',
                            attributes: {},
                            cells: [],
                            html: row.outerHTML.substring(0, 500) // 限制长度
                        };
                        
                        // 获取所有属性
                        for (var j = 0; j < row.attributes.length; j++) {
                            var attr = row.attributes[j];
                            rowInfo.attributes[attr.name] = attr.value;
                        }
                        
                        // 获取所有单元格信息
                        var cells = row.querySelectorAll('td, .cell, [class*="cell"]');
                        for (var j = 0; j < cells.length; j++) {
                            var cell = cells[j];
                            rowInfo.cells.push({
                                index: j,
                                text: cell.textContent.trim(),
                                className: cell.className,
                                html: cell.innerHTML.substring(0, 200) // 限制长度
                            });
                        }
                        
                        result.rows.push(rowInfo);
                    }
                    
                    return result;
                """)
                
                # 保存表格结构信息
                with open(f"{debug_dir}/table_structure_{page}.json", "w", encoding="utf-8") as f:
                    import json
                    json.dump(table_info, f, ensure_ascii=False, indent=2)
                logging.info(f"表格结构信息已保存至 {debug_dir}/table_structure_{page}.json")
                
            except Exception as e:
                logging.warning(f"保存详细页面结构信息失败: {str(e)}")
                
            # 对于第一页以外的页面，需要通过翻页操作到达
            current_page = 1
            while current_page < page:
                if not self.check_pagination():
                    logging.warning(f"无法翻到第{page}页，只能到达第{current_page}页")
                    return []
                current_page += 1
                time.sleep(random.uniform(1.5, 3))  # 随机等待时间，模拟人类操作
            
            # 等待问诊列表加载
            wait = WebDriverWait(self.driver, 10)
            try:
                # 尝试多种选择器定位问诊列表元素
                selectors = [
                    ".inquiry-card", 
                    ".el-table__row",  # 常见表格行
                    ".inquiry-item",
                    "[data-row-key]"   # 表格行通用属性
                ]
                
                inquiry_elements = None
                for selector in selectors:
                    try:
                        inquiry_elements = wait.until(
                            EC.presence_of_all_elements_located((By.CSS_SELECTOR, selector))
                        )
                        logging.info(f"使用选择器 '{selector}' 找到 {len(inquiry_elements)} 个问诊元素")
                        break
                    except:
                        continue
                        
                if not inquiry_elements:
                    raise Exception("无法找到问诊列表元素")
                    
            except Exception as e:
                error_id = f"inquiry_list_load_{int(time.time())}"
                logging.error(f"等待问诊列表加载失败: {str(e)}")
                
                # 诊断问题
                self.save_screenshot(f"inquiry_list_error_{page}.png")
                # 尝试获取页面源码
                page_source = self.driver.page_source
                with open(f"workbench_page_source_{page}.html", "w", encoding="utf-8") as f:
                    f.write(page_source)
                logging.info(f"页面源码已保存至 workbench_page_source_{page}.html")
                
                # 使用增强的错误处理
                if self.error_handler.handle_error(error_id, e):
                    return self.get_inquiry_list(page, page_size)
                return []
                
            # 解析问诊列表
            inquiries = []
            
            # 记录解析结果
            parse_log = []
            parse_log.append(f"=== 开始解析问诊记录 - 页码: {page} ===")
            parse_log.append(f"找到 {len(inquiry_elements)} 个问诊元素")
            
            for i, card in enumerate(inquiry_elements):
                try:
                    parse_log.append(f"\n--- 正在处理第 {i+1} 个问诊元素 ---")
                    # 获取元素信息用于调试
                    try:
                        element_html = card.get_attribute("outerHTML")
                        element_html_short = element_html[:200] + "..." if len(element_html) > 200 else element_html
                        parse_log.append(f"元素HTML: {element_html_short}")
                    except Exception as e:
                        parse_log.append(f"无法获取元素HTML: {str(e)}")
                    
                    # 提取问诊ID (可能在href属性中)
                    inquiry_id = None
                    try:
                        detail_link = card.find_element(By.CSS_SELECTOR, "a[href*='inquiry']")
                        href = detail_link.get_attribute("href")
                        parse_log.append(f"找到问诊详情链接: {href}")
                        inquiry_id = self.extract_inquiry_id(href)
                        if inquiry_id:
                            parse_log.append(f"从链接提取到问诊ID: {inquiry_id}")
                    except Exception as e:
                        parse_log.append(f"未找到详情链接或提取失败: {str(e)}")
                        # 如果没有链接，直接从元素提取ID
                        inquiry_id = self.extract_inquiry_id(element=card)
                        parse_log.append(f"从元素直接提取到问诊ID: {inquiry_id}")
                    
                    if not inquiry_id:
                        parse_log.append("无法提取问诊ID，跳过该记录")
                        continue
                    
                    # 提取问诊详情
                    inquiry_record = {"inquiryId": inquiry_id}
                    
                    # 提取患者姓名
                    try:
                        # 尝试提取带有标识的元素
                        name_elements = card.find_elements(By.CSS_SELECTOR, "[data-label*='姓名'], [class*='name'], [class*='patient']")
                        if name_elements:
                            patient_name = name_elements[0].text.strip()
                            parse_log.append(f"找到患者姓名元素: {patient_name}")
                        else:
                            # 尝试按位置提取，通常第二个单元格是姓名
                            cells = card.find_elements(By.CSS_SELECTOR, "td, .cell")
                            if len(cells) > 1:
                                patient_name = cells[1].text.strip()
                                parse_log.append(f"从第二个单元格提取患者姓名: {patient_name}")
                            else:
                                patient_name = "未知患者"
                                parse_log.append("无法提取患者姓名，使用默认值")
                        
                        inquiry_record["patientName"] = patient_name
                    except Exception as e:
                        parse_log.append(f"提取患者姓名失败: {str(e)}")
                        inquiry_record["patientName"] = "未知患者"
                    
                    # 提取问诊时间
                    try:
                        # 尝试提取带有标识的元素
                        time_elements = card.find_elements(By.CSS_SELECTOR, "[data-label*='时间'], [class*='time'], [class*='date']")
                        if time_elements:
                            inquiry_time = time_elements[0].text.strip()
                            parse_log.append(f"找到问诊时间元素: {inquiry_time}")
                        else:
                            # 尝试查找包含时间格式的文本
                            cells = card.find_elements(By.CSS_SELECTOR, "td, .cell")
                            for cell in cells:
                                cell_text = cell.text.strip()
                                # 检查是否包含日期时间格式 (如: 2023-04-09 12:30:45)
                                if re.search(r'\d{4}[-/]\d{1,2}[-/]\d{1,2}\s+\d{1,2}:\d{1,2}(:\d{1,2})?', cell_text):
                                    inquiry_time = cell_text
                                    parse_log.append(f"从单元格找到问诊时间: {inquiry_time}")
                                    break
                            else:
                                inquiry_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                parse_log.append("无法提取问诊时间，使用当前时间")
                        
                        inquiry_record["inquiryTime"] = inquiry_time
                    except Exception as e:
                        parse_log.append(f"提取问诊时间失败: {str(e)}")
                        inquiry_record["inquiryTime"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    # 提取问诊状态
                    try:
                        status_elements = card.find_elements(By.CSS_SELECTOR, "[data-label*='状态'], [class*='status'], span[class*='tag'], .el-tag")
                        if status_elements:
                            status = status_elements[0].text.strip()
                            parse_log.append(f"找到状态元素: {status}")
                        else:
                            # 尝试查找可能包含状态的关键词
                            cells = card.find_elements(By.CSS_SELECTOR, "td, .cell")
                            status_keywords = ["待回复", "已完成", "进行中", "关闭", "超时"]
                            for cell in cells:
                                cell_text = cell.text.strip()
                                for keyword in status_keywords:
                                    if keyword in cell_text:
                                        status = keyword
                                        parse_log.append(f"从单元格找到问诊状态关键词: {status}")
                                        break
                                else:
                                    continue
                                break
                            else:
                                status = "未知"
                                parse_log.append("无法提取问诊状态，使用默认值")
                        
                        inquiry_record["status"] = status
                    except Exception as e:
                        parse_log.append(f"提取问诊状态失败: {str(e)}")
                        inquiry_record["status"] = "未知"
                    
                    # 提取科室信息
                    try:
                        department_elements = card.find_elements(By.CSS_SELECTOR, "[data-label*='科室'], [class*='department']")
                        if department_elements:
                            department = department_elements[0].text.strip()
                            parse_log.append(f"找到科室元素: {department}")
                        else:
                            # 默认值
                            department = "未知科室"
                            parse_log.append("无法提取科室，使用默认值")
                        
                        inquiry_record["department"] = department
                    except Exception as e:
                        parse_log.append(f"提取科室失败: {str(e)}")
                        inquiry_record["department"] = "未知科室"
                    
                    # 提取其他可能有用的信息
                    try:
                        all_cells = card.find_elements(By.CSS_SELECTOR, "td, .cell")
                        cell_texts = [cell.text.strip() for cell in all_cells if cell.text.strip()]
                        parse_log.append(f"所有单元格文本: {cell_texts}")
                        
                        # 如果有足够的单元格但我们没有识别出某些信息，尝试基于位置推断
                        if len(cell_texts) >= 4 and "department" not in inquiry_record:
                            inquiry_record["department"] = cell_texts[3] if len(cell_texts) > 3 else "未知科室"
                            parse_log.append(f"根据位置推断科室: {inquiry_record['department']}")
                    except Exception as e:
                        parse_log.append(f"提取额外信息失败: {str(e)}")
                    
                    # 添加页码信息
                    inquiry_record["page"] = page
                    
                    # 添加到结果列表
                    inquiries.append(inquiry_record)
                    parse_log.append(f"成功解析问诊记录: {inquiry_record}")
                    
                except Exception as e:
                    parse_log.append(f"解析问诊元素过程中出错: {str(e)}")
                    continue
            
            # 保存解析日志
            try:
                debug_dir = "debug"
                if not os.path.exists(debug_dir):
                    os.makedirs(debug_dir)
                    
                with open(f"{debug_dir}/parse_log_page_{page}_{int(time.time())}.log", "w", encoding="utf-8") as f:
                    f.write("\n".join(parse_log))
                logging.info(f"解析日志已保存至 {debug_dir}/parse_log_page_{page}_{int(time.time())}.log")
            except Exception as e:
                logging.warning(f"保存解析日志失败: {str(e)}")
            
            logging.info(f"成功解析 {len(inquiries)} 条问诊记录")
            
            # 检查是否需要只返回增量数据
            if self.config.INCREMENTAL_MODE:
                return self.incremental_updater.filter_new_inquiries(inquiries)
            else:
                return inquiries
            
        except Exception as e:
            error_id = f"get_inquiry_list_{int(time.time())}"
            logging.error(f"获取问诊列表过程出错: {str(e)}")
            import traceback
            logging.error(traceback.format_exc())
            
            # 使用增强的错误处理
            if self.error_handler.handle_error(error_id, e):
                return self.get_inquiry_list(page, page_size)
            return []
    
    def extract_inquiry_id(self, url=None, element=None):
        """从URL或表格元素中提取问诊ID"""
        debug_dir = "debug"
        if not os.path.exists(debug_dir):
            os.makedirs(debug_dir)
            
        # 记录分析过程
        analysis_log = []
        analysis_log.append(f"开始提取问诊ID - 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 如果提供了URL，尝试从URL中提取
        if url:
            analysis_log.append(f"分析URL: {url}")
            try:
                # 尝试使用正则表达式提取问诊ID
                import re
                match = re.search(r'inquiry/(\w+)', url)
                if match:
                    analysis_log.append(f"从URL路径提取到ID: {match.group(1)}")
                    return match.group(1)
                    
                # 尝试使用URL解析
                from urllib.parse import urlparse, parse_qs
                parsed_url = urlparse(url)
                query_params = parse_qs(parsed_url.query)
                
                # 检查常见的ID参数名
                for param in ['inquiryId', 'id', 'inquiry_id', 'orderId']:
                    if param in query_params:
                        analysis_log.append(f"从URL参数[{param}]提取到ID: {query_params[param][0]}")
                        return query_params[param][0]
                        
                # 如果上述方法都失败，尝试从路径中提取最后一段
                path_segments = parsed_url.path.split('/')
                if path_segments and path_segments[-1]:
                    analysis_log.append(f"从URL路径最后一段提取到可能的ID: {path_segments[-1]}")
                    return path_segments[-1]
                    
            except Exception as e:
                analysis_log.append(f"从URL提取ID失败: {str(e)}")
                logging.warning(f"从URL提取问诊ID失败: {url}, 错误: {str(e)}")
        
        # 如果提供了元素，尝试从元素属性或文本中提取
        if element:
            analysis_log.append("开始从元素中提取ID:")
            
            # 保存元素HTML内容用于调试
            try:
                element_html = element.get_attribute("outerHTML")
                analysis_log.append(f"元素HTML结构: {element_html[:300]}...")
                
                # 保存到文件
                with open(f"{debug_dir}/element_{int(time.time())}.html", "w", encoding="utf-8") as f:
                    f.write(element_html)
                    
            except Exception as e:
                analysis_log.append(f"获取元素HTML失败: {str(e)}")
            
            try:
                # 首先检查元素常见的ID属性
                for attr in ['id', 'data-id', 'data-row-key', 'data-inquiry-id', 'data-order-id']:
                    try:
                        value = element.get_attribute(attr)
                        if value:
                            analysis_log.append(f"从属性[{attr}]提取到ID: {value}")
                            return value
                    except:
                        continue
                
                # 尝试获取所有属性        
                try:
                    all_attributes = self.driver.execute_script("""
                        var result = {};
                        var attrs = arguments[0].attributes;
                        for(var i=0; i<attrs.length; i++) {
                            result[attrs[i].name] = attrs[i].value;
                        }
                        return result;
                    """, element)
                    
                    analysis_log.append(f"元素所有属性: {str(all_attributes)}")
                    
                    # 检查属性中是否有可能的ID
                    for attr_name, attr_value in all_attributes.items():
                        if 'id' in attr_name.lower() and attr_value:
                            analysis_log.append(f"从属性名包含'id'的属性[{attr_name}]提取到可能的ID: {attr_value}")
                            return attr_value
                            
                        # 检查属性值是否看起来像ID (长数字或特定格式)
                        if re.match(r'\d{8,}', str(attr_value)):
                            analysis_log.append(f"从属性[{attr_name}]提取到可能是数字ID的值: {attr_value}")
                            return attr_value
                except:
                    analysis_log.append("获取所有属性失败")
                        
                # 尝试查找元素内部的第一个单元格，通常包含ID
                try:
                    cell_selectors = [
                        "td:first-child", 
                        ".cell:first-child",
                        "td:nth-child(1)",
                        ".el-table__cell:first-child",
                        "[class*='id']",
                        "[data-label*='ID']",
                        "[data-label*='编号']"
                    ]
                    
                    for selector in cell_selectors:
                        try:
                            first_cell = element.find_element(By.CSS_SELECTOR, selector)
                            cell_text = first_cell.text.strip()
                            analysis_log.append(f"使用选择器[{selector}]找到单元格内容: {cell_text}")
                            
                            # 如果内容长度合适且包含数字，可能是ID
                            if cell_text and len(cell_text) > 4 and re.search(r'\d', cell_text):
                                analysis_log.append(f"从单元格提取到可能的ID: {cell_text}")
                                return cell_text
                        except:
                            continue
                except Exception as e:
                    analysis_log.append(f"查找第一个单元格失败: {str(e)}")
                    
                # 详细分析每个单元格
                try:
                    cells = element.find_elements(By.CSS_SELECTOR, "td, .cell")
                    analysis_log.append(f"找到 {len(cells)} 个单元格")
                    
                    for i, cell in enumerate(cells):
                        try:
                            cell_text = cell.text.strip()
                            analysis_log.append(f"单元格[{i}]内容: {cell_text}")
                            
                            # 检查内容是否像ID
                            if cell_text and (re.match(r'\d{8,}', cell_text) or 
                                              re.match(r'[A-Z0-9]{6,}', cell_text) or
                                              (len(cell_text) > 5 and i == 0)):  # 第一列通常是ID
                                analysis_log.append(f"从单元格[{i}]提取到可能的ID: {cell_text}")
                                return cell_text
                        except:
                            continue
                except Exception as e:
                    analysis_log.append(f"分析单元格内容时出错: {str(e)}")
                
                # 尝试从内部链接中提取ID
                try:
                    links = element.find_elements(By.TAG_NAME, "a")
                    analysis_log.append(f"找到 {len(links)} 个链接")
                    
                    for i, link in enumerate(links):
                        try:
                            href = link.get_attribute("href")
                            if href:
                                analysis_log.append(f"链接[{i}]href: {href}")
                                id_from_link = self.extract_inquiry_id(href)
                                if id_from_link:
                                    analysis_log.append(f"从链接提取到ID: {id_from_link}")
                                    return id_from_link
                        except:
                            continue
                except Exception as e:
                    analysis_log.append(f"从链接提取ID时出错: {str(e)}")
                    
                # 尝试查找包含特定格式的文本（例如时间戳格式的ID）
                try:
                    text = element.text
                    analysis_log.append(f"元素文本内容: {text[:100]}...")
                    
                    import re
                    # 按优先级尝试提取不同ID格式
                    
                    # 尝试提取时间戳格式ID
                    id_match = re.search(r'\d{14,}', text)
                    if id_match:
                        id_value = id_match.group(0)
                        analysis_log.append(f"从文本提取到时间戳格式ID: {id_value}")
                        return id_value
                    
                    # 尝试提取其他常见ID格式
                    id_matches = re.findall(r'[A-Z0-9]{8,}', text)
                    if id_matches:
                        id_value = id_matches[0]
                        analysis_log.append(f"从文本提取到字母数字格式ID: {id_value}")
                        return id_value
                    
                    # 提取单纯的数字ID
                    num_matches = re.findall(r'\b\d{6,}\b', text)
                    if num_matches:
                        id_value = num_matches[0]
                        analysis_log.append(f"从文本提取到数字ID: {id_value}")
                        return id_value
                    
                except Exception as e:
                    analysis_log.append(f"提取文本中的ID格式失败: {str(e)}")
                
                # 获取元素内所有可见文本，尝试查找第一个可能是ID的内容
                try:
                    cells = element.find_elements(By.CSS_SELECTOR, "td, .cell")
                    if cells and len(cells) > 0:
                        first_cell_text = cells[0].text.strip()
                        analysis_log.append(f"第一个单元格内容: {first_cell_text}")
                        if first_cell_text and len(first_cell_text) > 4:
                            return first_cell_text
                except Exception as e:
                    analysis_log.append(f"从第一个单元格获取文本失败: {str(e)}")
                
            except Exception as e:
                analysis_log.append(f"从元素提取ID的过程中发生错误: {str(e)}")
                logging.warning(f"从元素提取问诊ID失败: {str(e)}")
        
        # 如果所有方法都失败，返回一个自动生成的临时ID
        import time
        import random
        temp_id = f"TEMP_{int(time.time())}_{random.randint(1000, 9999)}"
        analysis_log.append(f"无法提取ID，生成临时ID: {temp_id}")
        logging.warning(f"无法从元素中提取问诊ID，生成临时ID: {temp_id}")
        
        # 保存分析日志
        try:
            with open(f"{debug_dir}/id_extraction_{int(time.time())}.log", "w", encoding="utf-8") as f:
                f.write("\n".join(analysis_log))
        except:
            pass
            
        return temp_id
    
    def get_inquiry_detail(self, inquiry_id):
        """获取单个问诊的详细信息"""
        if not inquiry_id:
            logging.warning("无法获取问诊详情: 问诊ID为空")
            return None
            
        logging.info(f"获取问诊详情: {inquiry_id}")
        
        if not self.check_login_status():
            logging.error("获取问诊详情失败: 未登录")
            return None
            
        # 如果是模拟登录，返回模拟数据
        if self.config.MOCK_LOGIN:
            logging.info(f"使用模拟数据返回问诊详情: {inquiry_id}")
            
            # 从ID中提取页码和序号信息
            page_num = 1
            item_num = 1
            if inquiry_id.startswith("MOCK"):
                parts = inquiry_id.split("_")
                if len(parts) == 2:
                    try:
                        page_num = int(parts[0][4:])
                        item_num = int(parts[1])
                    except:
                        pass
            
            # 生成模拟消息
            messages = []
            for i in range(1, 4):
                # 患者消息
                messages.append({
                    "sender": "patient",
                    "content": f"这是第{i}条患者消息，询问有关症状的问题。" + "症状描述内容" * (i % 3 + 1),
                    "time": (datetime.now() - timedelta(hours=4-i)).strftime("%Y-%m-%d %H:%M:%S")
                })
                
                # 医生回复
                if i < 3:  # 最后一条患者消息可能没有回复
                    messages.append({
                        "sender": "doctor",
                        "content": f"这是第{i}条医生回复，解答患者问题。" + "专业解答内容" * (i % 2 + 1),
                        "time": (datetime.now() - timedelta(hours=4-i, minutes=30)).strftime("%Y-%m-%d %H:%M:%S")
                    })
            
            # 返回模拟详情数据
            return {
                "inquiryId": inquiry_id,
                "patientInfo": f"患者{page_num}_{item_num}，性别: {'男' if item_num % 2 == 0 else '女'}，年龄: {20 + item_num}",
                "status": "待回复" if item_num % 3 == 0 else ("已完成" if item_num % 3 == 1 else "进行中"),
                "inquiryTime": (datetime.now() - timedelta(days=item_num % 7)).strftime("%Y-%m-%d %H:%M:%S"),
                "messages": messages,
                "department": "内科" if item_num % 2 == 0 else "外科"
            }
        
        try:
            # 构建问诊详情页面URL
            detail_url = f"https://consult.ht-healthcare.com/manage/app/inquiry/{inquiry_id}"
            
            # 访问详情页面
            self.driver.get(detail_url)
            time.sleep(3)  # 等待页面加载
            
            # 保存详情页面截图
            self.save_screenshot(f"inquiry_detail_{inquiry_id}.png")
            
            # 等待详情页面加载完成
            wait = WebDriverWait(self.driver, 10)
            try:
                # 等待页面标题或主要内容加载
                wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".inquiry-detail-container"))
                )
            except Exception as e:
                logging.error(f"等待问诊详情页面加载失败: {str(e)}")
                return None
                
            # 获取问诊基本信息
            detail_info = {}
            
            try:
                # 提取患者信息
                patient_info_element = self.driver.find_element(By.CSS_SELECTOR, ".patient-info")
                detail_info["patientInfo"] = patient_info_element.text
                
                # 提取问诊状态
                status_element = self.driver.find_element(By.CSS_SELECTOR, ".inquiry-status")
                detail_info["status"] = status_element.text
                
                # 提取问诊时间
                time_element = self.driver.find_element(By.CSS_SELECTOR, ".inquiry-time")
                detail_info["inquiryTime"] = time_element.text
                
                # 提取问诊内容
                content_elements = self.driver.find_elements(By.CSS_SELECTOR, ".message-item")
                messages = []
                
                for element in content_elements:
                    try:
                        sender_type = "doctor" if "doctor-message" in element.get_attribute("class") else "patient"
                        message_text = element.find_element(By.CSS_SELECTOR, ".message-content").text
                        message_time = element.find_element(By.CSS_SELECTOR, ".message-time").text
                        
                        messages.append({
                            "sender": sender_type,
                            "content": message_text,
                            "time": message_time
                        })
                    except Exception as e:
                        logging.warning(f"解析消息元素失败: {str(e)}")
                
                detail_info["messages"] = messages
                detail_info["inquiryId"] = inquiry_id
                
                logging.info(f"成功获取问诊详情, ID: {inquiry_id}, 消息数: {len(messages)}")
                return detail_info
                
            except Exception as e:
                logging.error(f"解析问诊详情失败: {str(e)}")
                return None
                
        except Exception as e:
            logging.error(f"获取问诊详情过程出错: {str(e)}")
            import traceback
            logging.error(traceback.format_exc())
            return None
            
    def save_results(self, results):
        """保存爬取结果到文件"""
        if not results:
            logging.warning("没有结果需要保存")
            return
            
        try:
            # 确保结果目录存在
            results_dir = "results"
            if not os.path.exists(results_dir):
                os.makedirs(results_dir)
                
            # 保存为JSON文件，使用当前时间作为文件名
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(results_dir, f"inquiry_results_{timestamp}.json")
            
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
                
            logging.info(f"结果已保存到文件: {filename}, 共 {len(results)} 条记录")
            
        except Exception as e:
            logging.error(f"保存结果失败: {str(e)}")
            # 尝试紧急保存到临时文件
            try:
                with open(f"emergency_save_{int(time.time())}.json", "w", encoding="utf-8") as f:
                    json.dump(results, f, ensure_ascii=False)
                logging.info("已紧急保存到临时文件")
            except:
                logging.critical("紧急保存也失败，数据可能丢失!")

    def check_login_status(self):
        """检查当前登录状态，如果未登录则尝试登录"""
        logging.info("检查登录状态...")
        
        # 如果配置了模拟登录，直接返回登录成功
        if self.config.MOCK_LOGIN:
            logging.info("启用了模拟登录模式，跳过实际登录")
            self.is_logged_in = True
            return True
        
        # 初始检查，看看是否已经登录
        if self.is_logged_in:
            # 验证会话是否仍然有效
            try:
                # 访问需要登录的页面 - 使用官方格式URL
                test_urls = [
                    "https://consult.ht-healthcare.com/manage/#/home",
                    "https://consult.ht-healthcare.com/manage/login#/home"
                ]
                
                for test_url in test_urls:
                    try:
                        if self.driver and self.driver.current_url != test_url:
                            self.driver.get(test_url)
                            time.sleep(2)
                            
                            # 检查是否到达了预期页面
                            if not "login" in self.driver.current_url:
                                break
                    except:
                        continue
                
                current_url = self.driver.current_url if self.driver else "unknown"
                logging.info(f"当前URL: {current_url}")
                
                if "login" in current_url and "#/home" not in current_url:
                    logging.warning("会话已过期，需要重新登录")
                    self.is_logged_in = False
                else:
                    logging.info("会话仍然有效")
                    return True
            except Exception as e:
                error_id = f"check_login_status_{int(time.time())}"
                logging.error(f"检查登录状态出错: {str(e)}")
                
                # 使用增强的错误处理
                if not self.error_handler.handle_error(error_id, e):
                    self.is_logged_in = False
        
        # 如果未登录，尝试登录
        if not self.is_logged_in:
            logging.info("未登录，尝试登录...")
            return self.login()
            
        return self.is_logged_in
    
    def process_inquiry_detail(self, inquiry_id):
        """处理单个问诊详情的任务函数，用于多线程处理"""
        logging.info(f"线程处理问诊详情: {inquiry_id}")
        return self.get_inquiry_detail(inquiry_id)
    
    def run(self):
        """运行爬虫主流程"""
        logging.info("开始运行医疗咨询爬虫...")
        
        try:
            # 初始化浏览器
            self.init_browser()
            
            # 登录系统
            if not self.login():
                logging.error("登录失败，无法继续爬取")
                return
            
            # 检查登录状态
            if not self.check_login_status():
                logging.error("登录状态检查失败，无法继续爬取")
                return
                
            # 导航到正确的URL页面
            if not self.navigate_to_inquiry_page_js():
                logging.warning("导航到问诊列表页面失败，将尝试使用其他方式获取数据")
                
            # 确定是增量更新还是全量更新
            is_full_update = not self.config.INCREMENTAL_MODE or self.incremental_updater.need_full_update(
                force=self.config.FORCE_FULL_UPDATE,
                days_threshold=self.config.FULL_UPDATE_DAYS
            )
            
            if is_full_update:
                logging.info("执行全量更新")
            else:
                logging.info("执行增量更新")
            
            # 爬取问诊列表和详情
            all_results = []
            current_page = 1
            max_pages = self.config.MAX_PAGES  # 从配置中获取最大页数
            has_next_page = True
            
            # 启动工作线程
            self.threaded_crawler.start_workers()
            
            while current_page <= max_pages and has_next_page:
                # 获取问诊列表
                inquiry_list = self.get_inquiry_list(page=current_page)
                
                if not inquiry_list:
                    logging.warning(f"第{current_page}页没有获取到问诊数据，停止爬取")
                    break
                    
                logging.info(f"成功获取第{current_page}页问诊列表，共{len(inquiry_list)}条")
                
                # 添加详情获取任务到多线程处理队列
                for inquiry in inquiry_list:
                    inquiry_id = inquiry.get("inquiryId")
                    if not inquiry_id:
                        logging.warning("问诊ID为空，跳过")
                        continue
                        
                    # 如果是多线程模式，添加到任务队列
                    if self.config.USE_THREADING:
                        self.threaded_crawler.add_task(self.process_inquiry_detail, inquiry_id)
                    else:
                        # 否则，直接获取问诊详情
                        detail = self.get_inquiry_detail(inquiry_id)
                        if detail:
                            # 将列表数据合并到详情中
                            detail.update(inquiry)
                            all_results.append(detail)
                            logging.info(f"成功获取问诊详情: {inquiry_id}, 患者: {inquiry.get('patientName', '未知')}")
                        else:
                            logging.warning(f"获取问诊详情失败: {inquiry_id}")
                    
                    # 间隔一段时间，避免请求过于频繁
                    time.sleep(random.uniform(1, 3))
                
                # 如果是单线程模式，保存当前页的结果
                if not self.config.USE_THREADING and all_results:
                    self.save_results(all_results)
                
                # 检查是否有下一页
                if current_page < max_pages:  
                    has_next_page = self.check_pagination()
                    if has_next_page:
                        current_page += 1
                        # 每爬取一页后检查登录状态
                        if not self.check_login_status():
                            logging.warning("登录状态已失效，尝试重新登录")
                            if not self.login():
                                logging.error("重新登录失败，停止爬取")
                                break
                    else:
                        logging.info("已到达最后一页，停止爬取")
                else:
                    logging.info(f"已达到最大页数限制 {max_pages}，停止爬取")
                    break
            
            # 如果是多线程模式，等待所有任务完成并获取结果
            if self.config.USE_THREADING:
                logging.info("等待所有详情获取任务完成...")
                # 停止接受新任务，等待现有任务完成
                self.threaded_crawler.stop_workers(wait_for_completion=True)
                # 获取所有结果
                thread_results = self.threaded_crawler.get_results()
                
                # 合并详情和列表数据
                for detail in thread_results:
                    if detail and "inquiryId" in detail:
                        # 查找对应的列表项
                        for inquiry in inquiry_list:
                            if inquiry.get("inquiryId") == detail["inquiryId"]:
                                detail.update(inquiry)
                                break
                        all_results.append(detail)
            
            logging.info(f"爬取完成，共获取{len(all_results)}条问诊记录")
            
            # 保存最终结果
            self.save_results(all_results)
            
            # 如果是增量模式，保存检查点
            if self.config.INCREMENTAL_MODE:
                self.incremental_updater.save_checkpoint()
            
        except Exception as e:
            logging.error(f"爬虫运行过程中发生异常: {str(e)}")
            import traceback
            logging.error(traceback.format_exc())
            
        finally:
            # 关闭浏览器
            if self.driver:
                logging.info("关闭Selenium浏览器")
                self.driver.quit()
                self.driver = None
            
            logging.info("爬虫运行结束")

    def navigate_to_inquiry_page_js(self):
        """尝试使用JavaScript直接导航到问诊列表页面"""
        logging.info("尝试使用JavaScript直接导航到问诊列表页面")
        try:
            # 先导航到主页
            self.driver.get("https://consult.ht-healthcare.com/manage/")
            time.sleep(3)
            
            # 保存导航前的截图
            self.save_screenshot("before_js_navigation.png")
            
            # 直接设置hash值 - 根据测试，这是最可靠的方法
            try:
                logging.info("尝试直接设置hash值")
                self.driver.execute_script("window.location.hash = '#/inquiryManage/inquiryMisOrderList';")
                time.sleep(5)  # 等待路由变化和页面加载
                
                # 检查是否导航成功
                if "#/inquiryManage/inquiryMisOrderList" in self.driver.current_url:
                    logging.info("Hash导航成功")
                    
                    # 等待表格元素出现
                    try:
                        wait = WebDriverWait(self.driver, 10)
                        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".el-table, table, [class*='table']")))
                        logging.info("表格元素已加载")
                    except:
                        logging.warning("等待表格元素超时")
                        pass
                        
                    # 保存导航后的截图
                    self.save_screenshot("after_js_navigation.png")
                    return True
            except Exception as e:
                logging.warning(f"直接设置hash值失败: {str(e)}")
            
            # 如果直接设置hash值失败，尝试Vue Router
            vue_routes = [
                "'/inquiryManage/inquiryMisOrderList'",
            ]
            
            for route in vue_routes:
                try:
                    logging.info(f"尝试导航到Vue路由: {route}")
                    result = self.driver.execute_script(f"""
                        try {{
                            // 检查常见的Vue Router实例名称
                            var routerInstances = ['$router', 'router', 'vueRouter', '$vueRouter', 'appRouter'];
                            for (var i = 0; i < routerInstances.length; i++) {{
                                var router = window[routerInstances[i]];
                                if (router && typeof router.push === 'function') {{
                                    console.log('使用' + routerInstances[i] + '导航');
                                    router.push({route});
                                    return true;
                                }}
                            }}
                            
                            // 尝试全局Vue实例
                            if (window.Vue && window.Vue.$router) {{
                                window.Vue.$router.push({route});
                                return true;
                            }}
                            
                            return false;
                        }} catch (e) {{
                            console.error(e);
                            return false;
                        }}
                    """)
                    
                    if result:
                        logging.info(f"Vue Router导航成功: {route}")
                        time.sleep(5)  # 等待页面加载
                        # 保存导航后的截图
                        self.save_screenshot("after_vue_navigation.png")
                        return True
                except Exception as e:
                    logging.warning(f"Vue Router导航失败: {str(e)}")
            
            # 如果上述方法都失败，尝试直接访问已知有效的URL
            try:
                logging.info("尝试直接访问已知有效的URL")
                self.driver.get("https://consult.ht-healthcare.com/manage/#/inquiryManage/inquiryMisOrderList")
                time.sleep(5)  # 等待页面加载
                
                # 如果当前URL包含目标路径，说明导航成功
                if "inquiryManage/inquiryMisOrderList" in self.driver.current_url:
                    logging.info("直接访问URL成功")
                    # 保存导航后的截图
                    self.save_screenshot("after_direct_navigation.png")
                    return True
            except Exception as e:
                logging.warning(f"直接访问URL失败: {str(e)}")
            
            # 检查导航结果
            current_url = self.driver.current_url
            logging.info(f"最终URL: {current_url}")
            
            # 判断是否导航成功（不是404页面且包含目标路径）
            is_success = "404" not in self.driver.title and "inquiryManage/inquiryMisOrderList" in current_url
            logging.info(f"导航{'成功' if is_success else '失败'}")
            
            return is_success
        except Exception as e:
            logging.error(f"JavaScript导航过程中出错: {str(e)}")
            self.save_screenshot("js_navigation_error.png")
            return False


if __name__ == "__main__":
    try:
        import argparse
        
        # 解析命令行参数
        parser = argparse.ArgumentParser(description='医疗咨询平台问诊数据爬虫')
        parser.add_argument('--config', dest='config_file', help='配置文件路径')
        parser.add_argument('--incremental', dest='incremental', action='store_true', help='启用增量爬取')
        parser.add_argument('--full', dest='full_update', action='store_true', help='强制全量更新')
        parser.add_argument('--headless', dest='headless', action='store_true', help='使用无头模式')
        parser.add_argument('--pages', dest='max_pages', type=int, help='最大爬取页数')
        parser.add_argument('--threads', dest='max_workers', type=int, help='线程数量')
        parser.add_argument('--no-threads', dest='no_threading', action='store_true', help='禁用多线程')
        parser.add_argument('--proxies', dest='proxy_file', help='代理文件路径')
        parser.add_argument('--use-proxy', dest='use_proxy', action='store_true', help='启用代理')
        parser.add_argument('--auto-captcha', dest='auto_captcha', action='store_true', help='启用自动验证码识别')
        args = parser.parse_args()
        
        # 创建配置
        config = Config()
        
        # 从环境变量更新配置
        config.update_from_env()
        
        # 从配置文件更新配置（如果指定）
        if args.config_file:
            if config.update_from_file(args.config_file):
                logger.info(f"已从配置文件 {args.config_file} 加载配置")
            else:
                logger.warning(f"无法从配置文件 {args.config_file} 加载配置")
                
        # 应用命令行参数
        if args.incremental:
            config.INCREMENTAL_MODE = True
            logger.info("启用增量爬取模式")
            
        if args.full_update:
            config.FORCE_FULL_UPDATE = True
            logger.info("启用强制全量更新")
            
        if args.headless:
            config.HEADLESS_MODE = True
            logger.info("启用无头模式")
            
        if args.max_pages:
            config.MAX_PAGES = args.max_pages
            logger.info(f"设置最大爬取页数为 {args.max_pages}")
            
        if args.max_workers:
            config.MAX_WORKERS = args.max_workers
            logger.info(f"设置线程数量为 {args.max_workers}")
            
        if args.no_threading:
            config.USE_THREADING = False
            logger.info("禁用多线程")
            
        if args.proxy_file:
            config.PROXY_FILE = args.proxy_file
            logger.info(f"设置代理文件路径为 {args.proxy_file}")
            
        if args.use_proxy:
            config.USE_PROXY = True
            logger.info("启用代理")
            
        if args.auto_captcha:
            config.CAPTCHA_AUTO_RECOGNIZE = True
            logger.info("启用自动验证码识别")
        
        # 运行爬虫
        logger.info("开始运行爬虫...")
        crawler = MedicalConsultCrawler(config)
        crawler.run()
        
    except KeyboardInterrupt:
        logger.info("用户终止了程序")
    except Exception as e:
        logger.error(f"程序运行出错: {str(e)}")
        import traceback
        logger.error(traceback.format_exc()) 