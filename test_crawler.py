#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试医疗咨询爬虫的功能
"""

import os
import time
import json
import logging
import sys
import traceback
from config import Config
from main import MedicalConsultCrawler
from selenium.webdriver.common.by import By

def main():
    """运行爬虫测试"""
    # 确保输出立即显示，不被缓存
    sys.stdout.flush()
    
    print("\n")
    print("=" * 60)
    print("           医疗咨询爬虫测试程序 - 真实登录模式")
    print("=" * 60)
    print(" ⚠️ 重要提示：该程序将进行真实登录，需要手动输入验证码 ⚠️")
    print(" 1. 将会打开浏览器窗口访问登录页面")
    print(" 2. 程序会自动填写用户名和密码")
    print(" 3. 当出现验证码时，请查看验证码并在命令行中输入")
    print(" 4. 如果验证码图片不清晰，可以去screenshots目录查看保存的验证码图片")
    print("=" * 60)
    print("\n")
    
    try:
        # 使用默认配置
        config = Config()
        
        # 修改配置用于测试
        config.HEADLESS_MODE = False  # 显示浏览器窗口以便查看验证码
        config.MAX_PAGES = 1  # 限制爬取页数，减少测试时间
        config.MOCK_LOGIN = False  # 禁用模拟登录，使用真实登录模式
        config.MANUAL_CAPTCHA = True  # 启用手动输入验证码
        
        print(f"登录URL: {config.LOGIN_URL}")
        print(f"用户名: {config.USERNAME}")
        print(f"是否模拟登录: {config.MOCK_LOGIN} (False=使用真实登录)")
        print(f"是否手动输入验证码: {config.MANUAL_CAPTCHA} (True=需要手动输入)")
        print("=" * 60)
        
        # 确保screenshots目录存在，用于保存验证码图片
        screenshots_dir = "screenshots"
        if not os.path.exists(screenshots_dir):
            os.makedirs(screenshots_dir)
            print(f"创建了screenshots目录: {os.path.abspath(screenshots_dir)}")
            
        # 创建爬虫实例
        print("正在初始化爬虫...")
        crawler = MedicalConsultCrawler(config)
        
        try:
            print("\n【1/4】 开始初始化浏览器...")
            # 初始化浏览器
            sys.stdout.flush()
            if not crawler.init_browser():
                print("❌ 浏览器初始化失败，程序退出")
                return
            print("✅ 浏览器初始化成功")
                
            print("\n【2/4】 开始登录过程...")
            print("⚠️ 请注意：浏览器窗口将打开，并且可能需要您输入验证码")
            print("⚠️ 验证码图片将保存在screenshots目录中，文件名为captcha_page.png")
            # 登录
            sys.stdout.flush()
            if not crawler.login():
                print("❌ 登录失败，程序退出")
                return
            print("✅ 登录成功")
                
            print("\n【3/4】 开始获取数据...")
            # 获取问诊列表
            sys.stdout.flush()
            inquiry_list = crawler.get_inquiry_list(page=1)
            if not inquiry_list:
                print("❌ 未获取到问诊列表数据，程序退出")
                return
            print(f"✅ 获取到问诊列表数据: {len(inquiry_list)}条")
            
            # 运行爬虫
            all_results = []
            
            # 处理问诊详情
            print("\n【4/4】 处理问诊详情...")
            sys.stdout.flush()
            for i, inquiry in enumerate(inquiry_list):
                inquiry_id = inquiry.get("inquiryId")
                if inquiry_id:
                    print(f"正在处理 [{i+1}/{len(inquiry_list)}]: {inquiry_id}")
                    detail = crawler.get_inquiry_detail(inquiry_id)
                    if detail:
                        detail.update(inquiry)
                        all_results.append(detail)
                        print(f"  ✅ 成功获取问诊详情: {inquiry_id}")
                    else:
                        print(f"  ❌ 获取问诊详情失败: {inquiry_id}")
                time.sleep(1)  # 添加延迟，避免请求过于频繁
            
            # 保存结果
            print(f"\n爬取完成，共获取{len(all_results)}条记录")
            save_results(all_results)
            
        except Exception as e:
            print(f"\n❌ 爬虫测试过程中出错: {str(e)}")
            traceback.print_exc()
            
            # 检查是否有与验证码相关的错误
            error_str = str(e).lower()
            if "captcha" in error_str or "验证码" in error_str:
                print("\n可能是验证码识别出现问题。请检查：")
                print("1. 验证码图片是否清晰可见")
                print("2. 验证码输入是否正确")
                print("3. 网站验证码机制是否有变化")
            
            # 检查是否有与登录相关的错误
            elif "login" in error_str or "登录" in error_str:
                print("\n可能是登录过程出现问题。请检查：")
                print("1. 用户名和密码是否正确")
                print("2. 登录页面元素是否发生变化")
                print("3. 网站是否有反爬虫机制")
            
            # 检查是否有与网络相关的错误
            elif "network" in error_str or "连接" in error_str or "timeout" in error_str:
                print("\n可能是网络连接问题。请检查：")
                print("1. 网络连接是否稳定")
                print("2. 目标网站是否可访问")
                print("3. 是否需要使用代理")
            
        finally:
            # 清理资源
            if crawler.driver:
                print("\n关闭浏览器...")
                crawler.driver.quit()
            print("程序执行结束")
    except Exception as e:
        print(f"严重错误: {str(e)}")
        traceback.print_exc()

def save_results(results):
    """保存爬取结果到文件"""
    if not results:
        print("没有结果需要保存")
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
            
        print(f"✅ 结果已保存到文件: {filename}, 共 {len(results)} 条记录")
        
        # 显示结果内容
        print("\n爬取结果示例:")
        for i, result in enumerate(results[:3]):  # 只显示前3条
            print(f"记录 {i+1}:")
            print(json.dumps(result, ensure_ascii=False, indent=2)[:500] + "...")
            print("-" * 40)
        
    except Exception as e:
        print(f"保存结果失败: {str(e)}")

def test_urls(config):
    """测试不同的URL格式，找出可以正常访问的URL"""
    print("\n")
    print("=" * 60)
    print("           URL格式测试 - 检查网站路由结构")
    print("=" * 60)
    print(" ⚠️ 提示：该程序将依次尝试不同URL格式，找出正确的访问方式 ⚠️")
    print(" 1. 将会打开浏览器窗口访问不同URL形式")
    print(" 2. 程序会自动执行登录")
    print(" 3. 对于404错误的页面会自动尝试其他格式")
    print("=" * 60)
    print("\n")
    
    try:
        # 修改配置用于测试
        config.HEADLESS_MODE = False  # 显示浏览器窗口以便查看
        config.MOCK_LOGIN = False     # 禁用模拟登录
        
        # 创建爬虫实例
        print("正在初始化爬虫...")
        crawler = MedicalConsultCrawler(config)
        
        try:
            print("\n【1/3】 开始初始化浏览器...")
            # 初始化浏览器
            if not crawler.init_browser():
                print("❌ 浏览器初始化失败，程序退出")
                return
            print("✅ 浏览器初始化成功")
                
            print("\n【2/3】 开始登录过程...")
            # 登录
            if not crawler.login():
                print("❌ 登录失败，程序退出")
                return
            print("✅ 登录成功")
            
            print("\n【3/3】 开始测试不同URL格式...")
            
            # 尝试的不同URL格式
            test_urls = [
                "https://consult.ht-healthcare.com/manage/#/inquiryManage/inquiryMisOrderList",
                "https://consult.ht-healthcare.com/manage/#/inquiryManage/inquiryOrderList",
                "https://consult.ht-healthcare.com/manage/login#/inquiryManage/inquiryMisOrderList",
                "https://consult.ht-healthcare.com/manage/login#/inquiryManage/inquiryOrderList",
                "https://consult.ht-healthcare.com/manage/app/workbench",
                "https://consult.ht-healthcare.com/manage/inquiryManage/inquiryMisOrderList",
                "https://consult.ht-healthcare.com/manage/",
                "https://consult.ht-healthcare.com/manage",
                "https://consult.ht-healthcare.com/manage/#/home"
            ]
            
            # 存储测试结果
            results = []
            
            for i, url in enumerate(test_urls):
                print(f"\n测试 URL [{i+1}/{len(test_urls)}]: {url}")
                
                try:
                    crawler.driver.get(url)
                    time.sleep(5)  # 等待页面加载
                    
                    # 保存截图
                    screenshot_path = f"screenshots/url_test_{i+1}.png"
                    crawler.save_screenshot(f"url_test_{i+1}.png")
                    print(f"  截图已保存: {screenshot_path}")
                    
                    # 检查状态
                    current_url = crawler.driver.current_url
                    is_404 = "404" in crawler.driver.title or "Not Found" in crawler.driver.title
                    
                    # 检查是否有表格元素
                    has_table = False
                    table_count = 0
                    try:
                        tables = crawler.driver.find_elements(By.CSS_SELECTOR, ".el-table, table, [class*='table']")
                        table_count = len(tables)
                        has_table = table_count > 0
                        if has_table:
                            print(f"  ✅ 找到表格元素: {table_count}个")
                        else:
                            print(f"  ❌ 未找到表格元素")
                    except:
                        print(f"  ❌ 检查表格元素时出错")
                    
                    # 保存结果
                    result = {
                        "url": url,
                        "current_url": current_url,
                        "is_404": is_404,
                        "has_table": has_table,
                        "table_count": table_count,
                        "title": crawler.driver.title
                    }
                    results.append(result)
                    
                    # 显示测试结果
                    if is_404:
                        print(f"  ❌ 页面返回404错误")
                    else:
                        print(f"  ✅ 页面加载成功，当前URL: {current_url}")
                        print(f"  页面标题: {crawler.driver.title}")
                    
                except Exception as e:
                    print(f"  ❌ 测试过程出错: {str(e)}")
                    results.append({
                        "url": url,
                        "error": str(e)
                    })
            
            # 保存所有测试结果
            try:
                with open("url_test_results.json", "w", encoding="utf-8") as f:
                    import json
                    json.dump(results, f, ensure_ascii=False, indent=2)
                print("\n✅ 测试结果已保存到 url_test_results.json")
            except Exception as e:
                print(f"\n❌ 保存测试结果失败: {str(e)}")
            
            # 显示成功的URL
            print("\n测试结果总结:")
            success_urls = [r["url"] for r in results if not r.get("is_404", True) and r.get("has_table", False)]
            
            if success_urls:
                print("\n✅ 以下URL访问成功且找到了表格元素:")
                for url in success_urls:
                    print(f"  - {url}")
                    
                print("\n推荐在代码中使用这些URL格式")
            else:
                print("\n❌ 所有URL测试都未能找到有效的表格数据")
                print("建议检查网站结构或登录状态")
            
        except Exception as e:
            print(f"\n❌ URL测试过程中出错: {str(e)}")
            import traceback
            traceback.print_exc()
            
        finally:
            # 清理资源
            if crawler.driver:
                print("\n关闭浏览器...")
                crawler.driver.quit()
            print("程序执行结束")
    except Exception as e:
        print(f"严重错误: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import sys
    
    # 检查命令行参数
    if len(sys.argv) > 1 and sys.argv[1] == "--test-urls":
        # 使用默认配置
        config = Config()
        
        # 修改配置用于测试
        config.HEADLESS_MODE = False  # 显示浏览器窗口以便查看验证码
        config.MAX_PAGES = 1  # 限制爬取页数，减少测试时间
        config.MOCK_LOGIN = False  # 禁用模拟登录，使用真实登录模式
        config.MANUAL_CAPTCHA = True  # 启用手动输入验证码
        
        # 运行URL测试模式
        test_urls(config)
    else:
        # 运行常规测试
        main() 