/**
 * 检验门诊开单系统 - 互认功能交互脚本
 */

// 在文档加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    console.log('检验门诊开单系统 - 互认功能原型已加载');

    // 在父窗口中监听消息，以便在iframe之间通信
    window.addEventListener('message', function(event) {
        // 确保消息来源可信
        if (event.origin !== window.location.origin) return;
        
        const { action, data } = event.data;
        
        switch (action) {
            case 'openRecognitionList':
                // 打开互认项目列表
                // 在实际应用中会向市平台发送请求
                console.log('打开互认项目列表', data);
                break;
                
            case 'viewRecognitionDetail':
                // 查看互认项目详情
                console.log('查看互认项目详情', data);
                break;
                
            case 'toggleRecognition':
                // 切换互认状态
                console.log('切换互认状态', data);
                break;
                
            case 'openReasonInput':
                // 打开不互认理由输入
                console.log('打开不互认理由输入', data);
                break;
                
            case 'printPDF':
                // 打印PDF
                console.log('打印PDF', data);
                break;
                
            default:
                console.log('未知操作', action, data);
        }
    });
});

// 模拟API调用获取互认项目数据
function fetchRecognitionData() {
    // 模拟的API响应数据
    return new Promise((resolve) => {
        setTimeout(() => {
            resolve({
                success: true,
                data: [
                    {
                        id: 'LIS20230001',
                        patientName: '张三',
                        patientId: 'P1001',
                        gender: '男',
                        age: '45岁',
                        checkDate: '2023-01-15',
                        hospital: '市第一医院',
                        department: '内科',
                        items: [
                            { 
                                code: 'CBC001', 
                                name: '血常规', 
                                status: '正常',
                                subItems: [
                                    { name: '白细胞', value: '6.5', unit: '10^9/L', refRange: '4.0-10.0', status: '正常' },
                                    { name: '红细胞', value: '4.8', unit: '10^12/L', refRange: '4.0-5.5', status: '正常' },
                                    { name: '血红蛋白', value: '145', unit: 'g/L', refRange: '120-160', status: '正常' },
                                    { name: '血小板', value: '230', unit: '10^9/L', refRange: '100-300', status: '正常' }
                                ]
                            },
                            { 
                                code: 'LFT002', 
                                name: '肝功能', 
                                status: '异常',
                                subItems: [
                                    { name: 'ALT', value: '45', unit: 'U/L', refRange: '5-40', status: '异常' },
                                    { name: 'AST', value: '38', unit: 'U/L', refRange: '5-40', status: '正常' },
                                    { name: '总胆红素', value: '15', unit: 'μmol/L', refRange: '3-20', status: '正常' },
                                    { name: '直接胆红素', value: '5', unit: 'μmol/L', refRange: '0-7', status: '正常' }
                                ]
                            }
                        ]
                    },
                    {
                        id: 'LIS20230002',
                        patientName: '李四',
                        patientId: 'P1002',
                        gender: '女',
                        age: '32岁',
                        checkDate: '2023-01-20',
                        hospital: '市第二医院',
                        department: '妇科',
                        items: [
                            { 
                                code: 'CBC001', 
                                name: '血常规', 
                                status: '正常',
                                subItems: [
                                    { name: '白细胞', value: '5.5', unit: '10^9/L', refRange: '4.0-10.0', status: '正常' },
                                    { name: '红细胞', value: '4.2', unit: '10^12/L', refRange: '3.5-5.0', status: '正常' },
                                    { name: '血红蛋白', value: '125', unit: 'g/L', refRange: '110-150', status: '正常' },
                                    { name: '血小板', value: '210', unit: '10^9/L', refRange: '100-300', status: '正常' }
                                ]
                            },
                            { 
                                code: 'TH001', 
                                name: '甲状腺功能', 
                                status: '异常',
                                subItems: [
                                    { name: 'TSH', value: '5.6', unit: 'mIU/L', refRange: '0.4-4.0', status: '异常' },
                                    { name: 'FT4', value: '12', unit: 'pmol/L', refRange: '9-25', status: '正常' },
                                    { name: 'FT3', value: '4.2', unit: 'pmol/L', refRange: '3.5-6.5', status: '正常' }
                                ]
                            }
                        ]
                    }
                ]
            });
        }, 500);
    });
}

// 向其他窗口发送消息
function sendMessage(targetFrame, action, data) {
    if (!targetFrame) return;
    
    const message = {
        action,
        data
    };
    
    targetFrame.postMessage(message, window.location.origin);
}

// 显示加载中提示
function showLoading(element) {
    if (!element) return;
    
    const loadingDiv = document.createElement('div');
    loadingDiv.className = 'pb-loading-container';
    loadingDiv.innerHTML = `
        <div class="pb-loading"></div>
        <div class="pb-loading-text">加载中...</div>
    `;
    
    element.appendChild(loadingDiv);
    return loadingDiv;
}

// 隐藏加载中提示
function hideLoading(loadingElement) {
    if (loadingElement && loadingElement.parentNode) {
        loadingElement.parentNode.removeChild(loadingElement);
    }
}

// 显示消息提示
function showMessage(message, type = 'info') {
    const messageDiv = document.createElement('div');
    messageDiv.className = `pb-message pb-message-${type}`;
    messageDiv.innerHTML = `
        <div class="pb-message-content">
            <i class="fas ${type === 'success' ? 'fa-check-circle' : type === 'error' ? 'fa-exclamation-circle' : 'fa-info-circle'}"></i>
            <span>${message}</span>
        </div>
    `;
    
    document.body.appendChild(messageDiv);
    
    // 3秒后自动移除
    setTimeout(() => {
        if (messageDiv.parentNode) {
            messageDiv.parentNode.removeChild(messageDiv);
        }
    }, 3000);
}

// 格式化日期
function formatDate(date) {
    if (!date) return '';
    
    if (typeof date === 'string') {
        // 如果已经是格式化的字符串，直接返回
        if (date.match(/^\d{4}-\d{2}-\d{2}$/)) {
            return date;
        }
        
        date = new Date(date);
    }
    
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    
    return `${year}-${month}-${day}`;
}

// 导出函数到全局，以便在iframe中调用
window.appFunctions = {
    fetchRecognitionData,
    sendMessage,
    showLoading,
    hideLoading,
    showMessage,
    formatDate
}; 