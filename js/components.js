// 主界面功能
const MainOrder = {
    init() {
        this.bindEvents();
        this.initializeForm();
    },

    bindEvents() {
        // 添加检验项目按钮点击事件
        document.getElementById('addItemBtn')?.addEventListener('click', () => {
            document.getElementById('addItemModal').style.display = 'block';
        });

        // 关闭模态框按钮点击事件
        document.getElementById('closeModal')?.addEventListener('click', () => {
            document.getElementById('addItemModal').style.display = 'none';
        });

        // 确认添加项目按钮点击事件
        document.getElementById('confirmAdd')?.addEventListener('click', () => {
            this.addSelectedItems();
            document.getElementById('addItemModal').style.display = 'none';
        });
    },

    initializeForm() {
        // 初始化表单数据
        const mockPatientData = {
            name: '张三',
            gender: '男',
            age: '45',
            cardNo: '330106197505064317'
        };
        
        // 填充病人信息
        Object.entries(mockPatientData).forEach(([key, value]) => {
            const element = document.getElementById(`patient${key.charAt(0).toUpperCase() + key.slice(1)}`);
            if (element) element.value = value;
        });
    },

    addSelectedItems() {
        // 获取选中的项目并添加到列表中
        const selectedItems = document.querySelectorAll('#itemTable input[type="checkbox"]:checked');
        const itemList = document.getElementById('selectedItemList');
        
        selectedItems.forEach(checkbox => {
            const row = checkbox.closest('tr');
            const itemData = {
                code: row.cells[1].textContent,
                name: row.cells[2].textContent,
                price: row.cells[3].textContent
            };
            
            this.appendItemToList(itemData);
        });
        
        this.updateTotalAmount();
    },

    appendItemToList(itemData) {
        const itemList = document.getElementById('selectedItemList');
        const newRow = document.createElement('tr');
        
        newRow.innerHTML = `
            <td><input type="checkbox" class="selected-item"></td>
            <td>${itemData.code}</td>
            <td>${itemData.name}</td>
            <td>${itemData.price}</td>
            <td>
                <button class="pb-button-text delete-item">
                    <i class="fas fa-trash-alt"></i>
                </button>
            </td>
        `;
        
        itemList.appendChild(newRow);
    },

    updateTotalAmount() {
        const items = document.querySelectorAll('#selectedItemList tr');
        let total = 0;
        
        items.forEach(item => {
            const price = parseFloat(item.cells[3].textContent);
            if (!isNaN(price)) total += price;
        });
        
        document.getElementById('totalAmount').textContent = total.toFixed(2);
    }
};

// 互认项目列表功能
const RecognitionList = {
    init() {
        this.bindEvents();
        this.loadProjects();
    },

    bindEvents() {
        // 搜索按钮点击事件
        document.getElementById('searchBtn')?.addEventListener('click', () => {
            this.searchProjects();
        });

        // 状态筛选变化事件
        document.getElementById('statusFilter')?.addEventListener('change', () => {
            this.filterProjects();
        });
    },

    loadProjects() {
        // 模拟加载项目数据
        const mockProjects = [
            {
                code: 'XY001',
                name: '血常规',
                spec: '五分类',
                price: '35.00',
                status: '已互认',
                hospital: '省人民医院',
                updateTime: '2024-01-15'
            },
            // 添加更多模拟数据...
        ];

        this.renderProjects(mockProjects);
    },

    renderProjects(projects) {
        const tbody = document.querySelector('#projectTable tbody');
        if (!tbody) return;

        tbody.innerHTML = projects.map(project => `
            <tr>
                <td>${project.code}</td>
                <td>${project.name}</td>
                <td>${project.spec}</td>
                <td>${project.price}</td>
                <td>
                    <span class="status-label ${this.getStatusClass(project.status)}">
                        ${project.status}
                    </span>
                </td>
                <td>${project.hospital}</td>
                <td>${project.updateTime}</td>
                <td>
                    <button class="pb-button-text view-detail" onclick="window.parent.appFunctions.openDetailView(${JSON.stringify(project)})">
                        <i class="fas fa-eye"></i>
                    </button>
                    <button class="pb-button-text edit-project">
                        <i class="fas fa-edit"></i>
                    </button>
                </td>
            </tr>
        `).join('');
    },

    getStatusClass(status) {
        const statusMap = {
            '已互认': 'success',
            '待确认': 'warning',
            '不互认': 'error'
        };
        return statusMap[status] || '';
    },

    searchProjects() {
        const searchText = document.getElementById('searchInput')?.value;
        // 实现搜索逻辑
    },

    filterProjects() {
        const status = document.getElementById('statusFilter')?.value;
        // 实现筛选逻辑
    }
};

// 不互认理由填写功能
const RejectionReason = {
    init() {
        this.bindEvents();
    },

    bindEvents() {
        // 提交按钮点击事件
        document.getElementById('submitReason')?.addEventListener('click', () => {
            this.submitReason();
        });

        // 上传附件按钮点击事件
        document.getElementById('uploadBtn')?.addEventListener('click', () => {
            document.getElementById('fileInput').click();
        });

        // 文件选择变化事件
        document.getElementById('fileInput')?.addEventListener('change', (e) => {
            this.handleFileUpload(e);
        });
    },

    submitReason() {
        const formData = {
            projectInfo: this.getProjectInfo(),
            reasons: this.getSelectedReasons(),
            explanation: document.getElementById('explanation')?.value,
            attachments: this.getAttachments()
        };

        // 发送数据到服务器
        console.log('提交的数据：', formData);
    },

    getProjectInfo() {
        return {
            code: document.getElementById('projectCode')?.value,
            name: document.getElementById('projectName')?.value,
            spec: document.getElementById('projectSpec')?.value
        };
    },

    getSelectedReasons() {
        const checkboxes = document.querySelectorAll('input[name="reason"]:checked');
        return Array.from(checkboxes).map(cb => cb.value);
    },

    getAttachments() {
        const attachmentList = document.getElementById('attachmentList');
        return Array.from(attachmentList.children).map(item => ({
            name: item.querySelector('.file-name').textContent,
            size: item.querySelector('.file-size').textContent
        }));
    },

    handleFileUpload(event) {
        const files = event.target.files;
        if (!files.length) return;

        Array.from(files).forEach(file => {
            this.addAttachmentToList(file);
        });
    },

    addAttachmentToList(file) {
        const attachmentList = document.getElementById('attachmentList');
        const listItem = document.createElement('div');
        listItem.className = 'attachment-item';
        
        listItem.innerHTML = `
            <span class="file-name">${file.name}</span>
            <span class="file-size">${this.formatFileSize(file.size)}</span>
            <button class="pb-button-text delete-file">
                <i class="fas fa-times"></i>
            </button>
        `;
        
        attachmentList.appendChild(listItem);
    },

    formatFileSize(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
};

// 检验明细查看功能
const DetailView = {
    init() {
        this.bindEvents();
    },

    bindEvents() {
        // 打印按钮点击事件
        document.getElementById('printBtn')?.addEventListener('click', () => {
            window.print();
        });

        // 关闭按钮点击事件
        document.getElementById('closeBtn')?.addEventListener('click', () => {
            window.parent.history.back();
        });
    },

    loadDetail(data) {
        // 加载项目详细信息
        this.fillBasicInfo(data);
        this.loadComparisonData();
        this.loadRecognitionHistory();
    },

    fillBasicInfo(data) {
        if (!data) return;
        
        const fields = ['code', 'name', 'spec', 'price', 'status'];
        fields.forEach(field => {
            const element = document.getElementById(`project${field.charAt(0).toUpperCase() + field.slice(1)}`);
            if (element) element.textContent = data[field];
        });
    },

    loadComparisonData() {
        // 加载对比数据
        const mockComparisonData = {
            method: {
                current: 'PCR法',
                other: 'PCR法'
            },
            instrument: {
                current: 'AB-2000',
                other: 'AB-3000'
            },
            reagent: {
                current: '试剂A',
                other: '试剂B'
            }
        };

        this.renderComparison(mockComparisonData);
    },

    renderComparison(data) {
        const tbody = document.querySelector('#comparisonTable tbody');
        if (!tbody) return;

        Object.entries(data).forEach(([key, value]) => {
            const row = document.createElement('tr');
            const isDifferent = value.current !== value.other;
            
            row.innerHTML = `
                <td>${key}</td>
                <td>${value.current}</td>
                <td class="${isDifferent ? 'different' : ''}">${value.other}</td>
            `;
            
            tbody.appendChild(row);
        });
    },

    loadRecognitionHistory() {
        // 加载互认历史记录
        const mockHistory = [
            {
                date: '2024-01-15',
                action: '提交不互认申请',
                operator: '张医生',
                reason: '检验方法不一致'
            },
            // 添加更多历史记录...
        ];

        this.renderHistory(mockHistory);
    },

    renderHistory(history) {
        const timeline = document.getElementById('timeline');
        if (!timeline) return;

        timeline.innerHTML = history.map(item => `
            <div class="timeline-item">
                <div class="timeline-marker"></div>
                <div class="timeline-content">
                    <h4>${item.date}</h4>
                    <p>${item.action}</p>
                    <p>操作人：${item.operator}</p>
                    ${item.reason ? `<p>原因：${item.reason}</p>` : ''}
                </div>
            </div>
        `).join('');
    }
};

// PDF预览功能
const PdfPreview = {
    init() {
        this.bindEvents();
    },

    bindEvents() {
        // 打印按钮点击事件
        document.getElementById('printBtn')?.addEventListener('click', () => {
            window.print();
        });

        // 下载按钮点击事件
        document.getElementById('downloadBtn')?.addEventListener('click', () => {
            this.downloadPdf();
        });

        // 缩放控制
        document.getElementById('zoomIn')?.addEventListener('click', () => {
            this.zoom(1.1);
        });

        document.getElementById('zoomOut')?.addEventListener('click', () => {
            this.zoom(0.9);
        });
    },

    zoom(factor) {
        const content = document.querySelector('.preview-content');
        if (!content) return;

        const currentScale = parseFloat(content.style.transform.replace('scale(', '')) || 1;
        const newScale = currentScale * factor;
        
        if (newScale >= 0.5 && newScale <= 2) {
            content.style.transform = `scale(${newScale})`;
        }
    },

    downloadPdf() {
        // 实现PDF下载逻辑
        console.log('下载PDF文件');
    },

    loadPdfData(data) {
        // 加载PDF数据
        this.fillApplicationForm(data);
        this.fillRejectionExplanation(data);
    },

    fillApplicationForm(data) {
        // 填充申请表数据
        if (!data) return;
        
        const fields = ['projectName', 'projectCode', 'hospital', 'department'];
        fields.forEach(field => {
            const element = document.getElementById(field);
            if (element) element.textContent = data[field];
        });
    },

    fillRejectionExplanation(data) {
        // 填充不互认说明数据
        if (!data?.rejection) return;
        
        const explanation = document.getElementById('rejectionExplanation');
        if (explanation) {
            explanation.textContent = data.rejection.explanation;
        }
    }
};

// 导出所有组件
window.Components = {
    MainOrder,
    RecognitionList,
    RejectionReason,
    DetailView,
    PdfPreview
}; 