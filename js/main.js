/**
 * 检验门诊开单系统 - 主程序脚本
 */

// 全局应用状态
const appState = {
    currentUser: {
        name: '管理员',
        role: 'admin',
        hospital: '市第一医院'
    },
    currentPage: 'main-order',
    isMaximized: false,
    menuState: {
        file: false,
        edit: false,
        settings: false,
        help: false
    }
};

// 页面加载完成后的处理
document.addEventListener('DOMContentLoaded', function() {
    console.log('检验门诊开单系统已启动');
    initializeApp();
});

// 初始化应用程序
function initializeApp() {
    // 初始化窗口控制
    initializeWindowControls();
    
    // 初始化菜单
    initializeMenu();
    
    // 初始化导航
    initializeNavigation();
    
    // 更新状态栏
    updateStatusBar();
    
    // 加载初始页面
    loadPage('main-order');
}

// 初始化窗口控制
function initializeWindowControls() {
    // 最小化窗口
    document.getElementById('minimizeBtn')?.addEventListener('click', () => {
        window.electron?.minimize();
    });

    // 最大化/还原窗口
    document.getElementById('maximizeBtn')?.addEventListener('click', () => {
        if (appState.isMaximized) {
            window.electron?.restore();
        } else {
            window.electron?.maximize();
        }
        appState.isMaximized = !appState.isMaximized;
        updateMaximizeButton();
    });

    // 关闭窗口
    document.getElementById('closeBtn')?.addEventListener('click', () => {
        if (confirm('确定要退出系统吗？')) {
            window.electron?.close();
        }
    });
}

// 更新最大化按钮图标
function updateMaximizeButton() {
    const maximizeBtn = document.getElementById('maximizeBtn');
    if (maximizeBtn) {
        maximizeBtn.innerHTML = `<i class="fas fa-${appState.isMaximized ? 'window-restore' : 'window-maximize'}"></i>`;
    }
}

// 初始化菜单
function initializeMenu() {
    const menuItems = document.querySelectorAll('.menu-item');
    menuItems.forEach(item => {
        item.addEventListener('click', (e) => {
            const menu = e.currentTarget.textContent.trim();
            handleMenuClick(menu);
        });
    });
}

// 处理菜单点击
function handleMenuClick(menu) {
    switch (menu) {
        case '文件':
            showFileMenu();
            break;
        case '编辑':
            showEditMenu();
            break;
        case '设置':
            showSettings();
            break;
        case '帮助':
            showHelp();
            break;
    }
}

// 初始化导航
function initializeNavigation() {
    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', () => {
            const page = item.dataset.page;
            if (page) {
                loadPage(page);
                updateNavigation(item);
            }
        });
    });
}

// 加载页面
function loadPage(page) {
    const mainFrame = document.getElementById('mainFrame');
    const loading = document.getElementById('loading');
    
    if (mainFrame && loading) {
        // 显示加载动画
        loading.style.display = 'flex';
        
        // 更新当前页面状态
        appState.currentPage = page;
        
        // 加载新页面
        mainFrame.src = `components/${page}.html`;
        
        // 监听加载完成
        mainFrame.onload = () => {
            loading.style.display = 'none';
            updateStatusBar();
        };
    }
}

// 更新导航状态
function updateNavigation(activeItem) {
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('active');
    });
    activeItem.classList.add('active');
}

// 更新状态栏
function updateStatusBar() {
    const statusLeft = document.querySelector('.status-left');
    const statusRight = document.querySelector('.status-right');
    
    if (statusLeft && statusRight) {
        statusLeft.textContent = `就绪 - ${getPageTitle(appState.currentPage)}`;
        statusRight.textContent = `当前用户：${appState.currentUser.name} | ${appState.currentUser.hospital}`;
    }
}

// 获取页面标题
function getPageTitle(page) {
    const titles = {
        'main-order': '主界面',
        'recognition-list': '互认项目列表',
        'rejection-reason': '不互认理由填写',
        'detail-view': '检验明细查看',
        'pdf-preview': 'PDF预览'
    };
    return titles[page] || '未知页面';
}

// 显示文件菜单
function showFileMenu() {
    const menuOptions = [
        { label: '新建', icon: 'fa-plus' },
        { label: '打开', icon: 'fa-folder-open' },
        { label: '保存', icon: 'fa-save' },
        { label: '导出', icon: 'fa-file-export' },
        { type: 'separator' },
        { label: '打印', icon: 'fa-print' },
        { type: 'separator' },
        { label: '退出', icon: 'fa-power-off' }
    ];
    showContextMenu('file', menuOptions);
}

// 显示编辑菜单
function showEditMenu() {
    const menuOptions = [
        { label: '撤销', icon: 'fa-undo' },
        { label: '重做', icon: 'fa-redo' },
        { type: 'separator' },
        { label: '剪切', icon: 'fa-cut' },
        { label: '复制', icon: 'fa-copy' },
        { label: '粘贴', icon: 'fa-paste' },
        { type: 'separator' },
        { label: '查找', icon: 'fa-search' },
        { label: '替换', icon: 'fa-exchange-alt' }
    ];
    showContextMenu('edit', menuOptions);
}

// 显示设置对话框
function showSettings() {
    // TODO: 实现设置对话框
    console.log('打开设置');
}

// 显示帮助信息
function showHelp() {
    // TODO: 实现帮助信息
    console.log('打开帮助');
}

// 显示上下文菜单
function showContextMenu(type, options) {
    // 关闭其他菜单
    closeAllMenus();
    
    // 创建菜单元素
    const menu = document.createElement('div');
    menu.className = 'context-menu';
    menu.id = `${type}Menu`;
    
    // 生成菜单项
    menu.innerHTML = options.map(option => {
        if (option.type === 'separator') {
            return '<div class="menu-separator"></div>';
        }
        return `
            <div class="menu-option">
                <i class="fas ${option.icon}"></i>
                <span>${option.label}</span>
            </div>
        `;
    }).join('');
    
    // 定位菜单
    const menuButton = document.querySelector(`.menu-item:contains('${type}')`);
    const rect = menuButton.getBoundingClientRect();
    menu.style.top = `${rect.bottom}px`;
    menu.style.left = `${rect.left}px`;
    
    // 添加到文档
    document.body.appendChild(menu);
    
    // 更新菜单状态
    appState.menuState[type] = true;
    
    // 添加点击事件监听
    menu.addEventListener('click', (e) => {
        const option = e.target.closest('.menu-option');
        if (option) {
            handleMenuOption(type, option.querySelector('span').textContent);
        }
    });
    
    // 添加关闭事件监听
    document.addEventListener('click', (e) => {
        if (!menu.contains(e.target) && !menuButton.contains(e.target)) {
            closeMenu(type);
        }
    });
}

// 关闭指定菜单
function closeMenu(type) {
    const menu = document.getElementById(`${type}Menu`);
    if (menu) {
        menu.remove();
        appState.menuState[type] = false;
    }
}

// 关闭所有菜单
function closeAllMenus() {
    Object.keys(appState.menuState).forEach(closeMenu);
}

// 处理菜单选项
function handleMenuOption(type, option) {
    console.log(`选择了${type}菜单的${option}选项`);
    closeMenu(type);
    
    // TODO: 实现具体的菜单功能
}

// 导出函数到全局，以便在iframe中调用
window.appFunctions = {
    // 发送消息到指定iframe
    sendMessage: function(targetFrame, action, data) {
        if (targetFrame && targetFrame.postMessage) {
            targetFrame.postMessage({ action, data }, '*');
        }
    },
    
    // 打开不互认理由填写界面
    openRejectionReason: function(data) {
        loadPage('rejection-reason');
        const frame = document.getElementById('mainFrame');
        frame.onload = () => {
            this.sendMessage(frame.contentWindow, 'initRejectionReason', data);
        };
    },
    
    // 打开检验明细查看界面
    openDetailView: function(data) {
        loadPage('detail-view');
        const frame = document.getElementById('mainFrame');
        frame.onload = () => {
            this.sendMessage(frame.contentWindow, 'initDetailView', data);
        };
    },
    
    // 打开PDF预览界面
    openPdfPreview: function(data) {
        loadPage('pdf-preview');
        const frame = document.getElementById('mainFrame');
        frame.onload = () => {
            this.sendMessage(frame.contentWindow, 'initPdfPreview', data);
        };
    }
};

// 监听来自iframe的消息
window.addEventListener('message', function(event) {
    // 确保消息来源可信
    if (event.origin !== window.location.origin) return;
    
    const { action, data } = event.data;
    
    // 根据不同的action处理不同的iframe通信
    switch(action) {
        case 'openRejectionReason':
            window.appFunctions.openRejectionReason(data);
            break;
        case 'openDetailView':
            window.appFunctions.openDetailView(data);
            break;
        case 'openPdfPreview':
            window.appFunctions.openPdfPreview(data);
            break;
        case 'updateStatus':
            updateStatusBar();
            break;
    }
}); 