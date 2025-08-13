/**
 * 印花图案贴合系统 - 最终版本
 * 完整对接后台API数据
 */

class PatternEditor {
    constructor() {
        this.canvas = document.getElementById('canvas');
        if (!this.canvas) {
            console.error('Canvas元素未找到');
            return;
        }
        this.ctx = this.canvas.getContext('2d');
        
        // 图片对象
        this.patternImg = null;
        this.productImg = null;
        this.depthImg = null;
        this.depthData = null;
        
        // 图案属性
        this.patternX = 400;
        this.patternY = 300;
        this.patternScale = 1;
        this.patternOpacity = 1;
        
        // 3D效果属性
        this.horizontalSkew = 0;
        this.verticalSkew = 0;
        this.wrapIntensity = 0.5;
        
        // 交互状态
        this.isDragging = false;
        this.lastMouseX = 0;
        this.lastMouseY = 0;
        this.lastTouchDistance = null;
        
        // 当前选择的数据
        this.currentPattern = null;
        this.currentProduct = null;
        
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.setupCanvasInteraction();
    }
    
    setupEventListeners() {
        // 控制面板事件
        const controls = {
            'pattern-opacity': (value) => { 
                this.patternOpacity = parseFloat(value); 
                this.render(); 
            },
            'horizontal-skew': (value) => { 
                this.horizontalSkew = parseFloat(value); 
                this.render(); 
            },
            'vertical-skew': (value) => { 
                this.verticalSkew = parseFloat(value); 
                this.render(); 
            },
            'wrap-intensity': (value) => { 
                this.wrapIntensity = parseFloat(value); 
                this.render(); 
            }
        };
        
        Object.keys(controls).forEach(id => {
            const element = document.getElementById(id);
            if (element) {
                element.addEventListener('input', (e) => controls[id](e.target.value));
            }
        });
        
        // 导出按钮
        const exportBtn = document.getElementById('export-btn');
        if (exportBtn) {
            exportBtn.addEventListener('click', this.exportImage.bind(this));
        }
    }
    
    setupCanvasInteraction() {
        // 鼠标事件
        this.canvas.addEventListener('mousedown', this.onMouseDown.bind(this));
        this.canvas.addEventListener('mousemove', this.onMouseMove.bind(this));
        this.canvas.addEventListener('mouseup', this.onMouseUp.bind(this));
        this.canvas.addEventListener('wheel', this.onWheel.bind(this));
        
        // 触摸事件
        this.canvas.addEventListener('touchstart', this.onTouchStart.bind(this));
        this.canvas.addEventListener('touchmove', this.onTouchMove.bind(this));
        this.canvas.addEventListener('touchend', this.onTouchEnd.bind(this));
    }
    
    // 加载印花图案
    async loadPattern(pattern) {
        try {
            console.log('开始加载印花图案:', pattern);
            this.currentPattern = pattern;
            
            this.patternImg = new Image();
            this.patternImg.crossOrigin = 'anonymous';
            
            return new Promise((resolve, reject) => {
                this.patternImg.onload = () => {
                    console.log('印花图案加载成功:', pattern.name);
                    this.render();
                    resolve();
                };
                this.patternImg.onerror = (error) => {
                    console.error('印花图案加载失败:', pattern.file_path, error);
                    reject(error);
                };
                
                // 确保路径正确
                const imagePath = pattern.file_path.replace(/\\/g, '/');
                this.patternImg.src = '/' + imagePath;
            });
            
        } catch (error) {
            console.error('加载印花图案时出错:', error);
        }
    }
    
    // 加载产品
    async loadProduct(product) {
        try {
            console.log('开始加载产品:', product);
            this.currentProduct = product;
            
            this.productImg = new Image();
            this.productImg.crossOrigin = 'anonymous';
            
            return new Promise((resolve, reject) => {
                this.productImg.onload = () => {
                    console.log('产品图片加载成功:', product.title);
                    this.render();
                    resolve();
                };
                this.productImg.onerror = (error) => {
                    console.error('产品图片加载失败:', product.product_image_path, error);
                    reject(error);
                };
                
                // 使用正确的字段名和路径
                const imagePath = product.product_image_path ? product.product_image_path.replace(/\\/g, '/') : '';
                this.productImg.src = '/uploads/products/' + imagePath;
            });
            
            // 尝试加载深度图
            if (product.depth_image_path) {
                await this.loadDepthImage(product.depth_image_path);
            }
            
        } catch (error) {
            console.error('加载产品时出错:', error);
        }
    }
    
    // 加载深度图
    async loadDepthImage(depthImagePath) {
        try {
            this.depthImg = new Image();
            this.depthImg.crossOrigin = 'anonymous';
            
            return new Promise((resolve, reject) => {
                this.depthImg.onload = () => {
                    console.log('深度图加载成功');
                    this.processDepthData();
                    resolve();
                };
                this.depthImg.onerror = (error) => {
                    console.log('深度图加载失败，使用2D模式:', error);
                    this.depthImg = null;
                    this.depthData = null;
                    resolve(); // 不阻塞主流程
                };
                
                const imagePath = depthImagePath.replace(/\\/g, '/');
                this.depthImg.src = '/uploads/products/' + imagePath;
            });
            
        } catch (error) {
            console.error('加载深度图时出错:', error);
        }
    }
    
    // 处理深度数据
    processDepthData() {
        if (!this.depthImg) return;
        
        try {
            const canvas = document.createElement('canvas');
            const ctx = canvas.getContext('2d');
            canvas.width = this.depthImg.width;
            canvas.height = this.depthImg.height;
            
            ctx.drawImage(this.depthImg, 0, 0);
            const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
            this.depthData = imageData.data;
            
            console.log('深度数据处理完成');
        } catch (error) {
            console.error('处理深度数据失败:', error);
            this.depthData = null;
        }
    }
    
    // 渲染画布
    render() {
        if (!this.productImg || !this.patternImg) {
            return;
        }
        
        // 清空画布
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        
        // 绘制产品图片
        this.ctx.drawImage(this.productImg, 0, 0, this.canvas.width, this.canvas.height);
        
        // 绘制图案
        this.ctx.save();
        this.ctx.globalAlpha = this.patternOpacity;
        this.ctx.globalCompositeOperation = 'multiply';
        
        const scaledWidth = this.patternImg.width * this.patternScale * 0.3;
        const scaledHeight = this.patternImg.height * this.patternScale * 0.3;
        
        this.ctx.translate(this.patternX, this.patternY);
        
        // 应用倾斜变形
        if (this.horizontalSkew !== 0 || this.verticalSkew !== 0) {
            this.ctx.transform(1, this.verticalSkew * 0.5, this.horizontalSkew * 0.5, 1, 0, 0);
        }
        
        this.ctx.drawImage(
            this.patternImg,
            -scaledWidth / 2,
            -scaledHeight / 2,
            scaledWidth,
            scaledHeight
        );
        
        this.ctx.restore();
    }
    
    // 鼠标事件处理
    onMouseDown(e) {
        const rect = this.canvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        
        if (this.isPointInPattern(x, y)) {
            this.isDragging = true;
            this.lastMouseX = x;
            this.lastMouseY = y;
            this.canvas.style.cursor = 'grabbing';
        }
    }
    
    onMouseMove(e) {
        if (!this.isDragging) return;
        
        const rect = this.canvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        
        const deltaX = x - this.lastMouseX;
        const deltaY = y - this.lastMouseY;
        
        this.patternX += deltaX;
        this.patternY += deltaY;
        
        this.lastMouseX = x;
        this.lastMouseY = y;
        
        this.render();
    }
    
    onMouseUp() {
        this.isDragging = false;
        this.canvas.style.cursor = 'grab';
    }
    
    onWheel(e) {
        e.preventDefault();
        
        const rect = this.canvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        
        if (this.isPointInPattern(x, y)) {
            const scaleFactor = e.deltaY > 0 ? 0.9 : 1.1;
            this.patternScale = Math.max(0.1, Math.min(3, this.patternScale * scaleFactor));
            this.render();
        }
    }
    
    // 触摸事件处理
    onTouchStart(e) {
        e.preventDefault();
        if (e.touches.length === 1) {
            const touch = e.touches[0];
            const rect = this.canvas.getBoundingClientRect();
            const x = touch.clientX - rect.left;
            const y = touch.clientY - rect.top;
            
            if (this.isPointInPattern(x, y)) {
                this.isDragging = true;
                this.lastMouseX = x;
                this.lastMouseY = y;
            }
        } else if (e.touches.length === 2) {
            this.lastTouchDistance = this.getTouchDistance(e.touches);
        }
    }
    
    onTouchMove(e) {
        e.preventDefault();
        if (e.touches.length === 1 && this.isDragging) {
            const touch = e.touches[0];
            const rect = this.canvas.getBoundingClientRect();
            const x = touch.clientX - rect.left;
            const y = touch.clientY - rect.top;
            
            const deltaX = x - this.lastMouseX;
            const deltaY = y - this.lastMouseY;
            
            this.patternX += deltaX;
            this.patternY += deltaY;
            
            this.lastMouseX = x;
            this.lastMouseY = y;
            
            this.render();
        } else if (e.touches.length === 2) {
            const currentDistance = this.getTouchDistance(e.touches);
            if (this.lastTouchDistance) {
                const scaleFactor = currentDistance / this.lastTouchDistance;
                this.patternScale = Math.max(0.1, Math.min(3, this.patternScale * scaleFactor));
                this.render();
            }
            this.lastTouchDistance = currentDistance;
        }
    }
    
    onTouchEnd(e) {
        e.preventDefault();
        this.isDragging = false;
        this.lastTouchDistance = null;
    }
    
    getTouchDistance(touches) {
        const dx = touches[0].clientX - touches[1].clientX;
        const dy = touches[0].clientY - touches[1].clientY;
        return Math.sqrt(dx * dx + dy * dy);
    }
    
    isPointInPattern(x, y) {
        if (!this.patternImg) return false;
        
        const scaledWidth = this.patternImg.width * this.patternScale * 0.3;
        const scaledHeight = this.patternImg.height * this.patternScale * 0.3;
        
        return x >= this.patternX - scaledWidth / 2 && 
               x <= this.patternX + scaledWidth / 2 &&
               y >= this.patternY - scaledHeight / 2 && 
               y <= this.patternY + scaledHeight / 2;
    }
    
    // 导出图片
    async exportImage() {
        try {
            const exportCanvas = document.createElement('canvas');
            const exportCtx = exportCanvas.getContext('2d');
            
            const scale = 2;
            exportCanvas.width = this.canvas.width * scale;
            exportCanvas.height = this.canvas.height * scale;
            
            exportCtx.scale(scale, scale);
            
            if (this.productImg) {
                exportCtx.drawImage(this.productImg, 0, 0, this.canvas.width, this.canvas.height);
            }
            
            if (this.patternImg) {
                exportCtx.save();
                exportCtx.globalAlpha = this.patternOpacity;
                exportCtx.globalCompositeOperation = 'multiply';
                
                const scaledWidth = this.patternImg.width * this.patternScale * 0.3;
                const scaledHeight = this.patternImg.height * this.patternScale * 0.3;
                
                exportCtx.translate(this.patternX, this.patternY);
                
                if (this.horizontalSkew !== 0 || this.verticalSkew !== 0) {
                    exportCtx.transform(1, this.verticalSkew * 0.5, this.horizontalSkew * 0.5, 1, 0, 0);
                }
                
                exportCtx.drawImage(
                    this.patternImg,
                    -scaledWidth / 2,
                    -scaledHeight / 2,
                    scaledWidth,
                    scaledHeight
                );
                
                exportCtx.restore();
            }
            
            exportCanvas.toBlob((blob) => {
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `design_${Date.now()}.png`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);
            }, 'image/png');
            
        } catch (error) {
            console.error('导出失败:', error);
            alert('导出失败，请重试');
        }
    }
}

// 数据管理类
class DataManager {
    static async fetchAPI(url) {
        try {
            const response = await fetch(url);
            const result = await response.json();
            
            console.log(`API ${url} 返回:`, result);
            
            if (result.success) {
                return result.data || [];
            } else {
                console.error(`API ${url} 失败:`, result.message);
                return [];
            }
        } catch (error) {
            console.error(`API ${url} 请求失败:`, error);
            return [];
        }
    }
    
    static async loadPatterns() {
        return await this.fetchAPI('/api/patterns');
    }
    
    static async loadProducts(categoryId = null) {
        const url = categoryId ? `/api/products?category_id=${categoryId}` : '/api/products';
        return await this.fetchAPI(url);
    }
    
    static async loadCategories() {
        return await this.fetchAPI('/api/categories');
    }
    
    static async loadThemes() {
        return await this.fetchAPI('/api/themes');
    }
}

// UI管理类
class UIManager {
    constructor(patternEditor) {
        this.patternEditor = patternEditor;
        this.currentTheme = 'default';
    }
    
    // 渲染印花图案网格
    renderPatterns(patterns) {
        const patternGrid = document.getElementById('pattern-grid');
        if (!patternGrid) return;
        
        patternGrid.innerHTML = '';
        
        patterns.forEach(pattern => {
            const item = document.createElement('div');
            item.className = 'pattern-item';
            item.dataset.patternId = pattern.id;
            
            // 确保图片路径正确
            const imagePath = pattern.file_path.replace(/\\/g, '/');
            
            item.innerHTML = `
                <img src="/${imagePath}" alt="${pattern.name}" 
                     onerror="this.style.display='none'; this.nextElementSibling.style.display='block';">
                <div style="display:none; padding:20px; text-align:center; color:#666; font-size:12px;">
                    图片加载失败<br>${pattern.name}
                </div>
                <div class="name">${pattern.name}</div>
            `;
            
            item.addEventListener('click', () => {
                this.selectPattern(pattern);
            });
            
            patternGrid.appendChild(item);
        });
    }
    
    // 渲染产品网格
    renderProducts(products) {
        const productsGrid = document.getElementById('products-grid');
        if (!productsGrid) return;
        
        productsGrid.innerHTML = '';
        
        if (!products || products.length === 0) {
            productsGrid.innerHTML = '<div class="no-data">暂无产品数据</div>';
            return;
        }
        
        products.forEach(product => {
            const item = document.createElement('div');
            item.className = 'product-item';
            item.dataset.productId = product.id;
            
            // 使用正确的字段名：product_image_path 和 title
            const imagePath = product.product_image_path ? product.product_image_path.replace(/\\/g, '/') : '';
            
            item.innerHTML = `
                <img src="/uploads/products/${imagePath}" alt="${product.title}"
                     onerror="this.style.display='none'; this.nextElementSibling.style.display='block';">
                <div style="display:none; padding:10px; text-align:center; color:#666; font-size:10px;">
                    图片加载失败<br>${product.title}
                </div>
                <div class="name">${product.title}</div>
            `;
            
            item.addEventListener('click', () => {
                this.selectProduct(product);
            });
            
            productsGrid.appendChild(item);
        });
    }
    
    // 渲染分类选择器
    renderCategories(categories) {
        const categorySelect = document.getElementById('category-select');
        if (!categorySelect) return;
        
        categorySelect.innerHTML = '<option value="">全部分类</option>';
        
        let defaultCategoryId = null;
        
        categories.forEach(category => {
            const option = document.createElement('option');
            option.value = category.id;
            option.textContent = category.name;
            if (category.is_default) {
                option.selected = true;
                defaultCategoryId = category.id;
            }
            categorySelect.appendChild(option);
        });
        
        // 监听分类变化
        categorySelect.addEventListener('change', async (e) => {
            const categoryId = e.target.value || null;
            const products = await DataManager.loadProducts(categoryId);
            this.renderProducts(products);
        });
        
        // 加载默认分类的产品
        if (defaultCategoryId) {
            DataManager.loadProducts(defaultCategoryId).then(products => {
                this.renderProducts(products);
            });
        }
    }
    
    // 渲染主题选择器
    renderThemes(themes) {
        const themeSelect = document.getElementById('theme-select');
        if (!themeSelect) return;
        
        themeSelect.innerHTML = '';
        
        // 如果没有主题数据，使用默认主题
        if (themes.length === 0) {
            themeSelect.innerHTML = `
                <option value="default" selected>默认主题</option>
                <option value="christmas">圣诞主题</option>
                <option value="easter">复活节主题</option>
                <option value="halloween">万圣节主题</option>
                <option value="valentine">情人节主题</option>
            `;
        } else {
            themes.forEach(theme => {
                const option = document.createElement('option');
                option.value = theme.code || theme.id;
                option.textContent = theme.name;
                if (theme.is_default) {
                    option.selected = true;
                    this.applyTheme(theme);
                }
                themeSelect.appendChild(option);
            });
        }
        
        // 监听主题变化
        themeSelect.addEventListener('change', (e) => {
            this.applyTheme(e.target.value);
        });
    }
    
    // 选择印花图案
    selectPattern(pattern) {
        // 移除之前的选中状态
        document.querySelectorAll('.pattern-item').forEach(item => {
            item.classList.remove('selected');
        });
        
        // 添加选中状态
        const selectedItem = document.querySelector(`[data-pattern-id="${pattern.id}"]`);
        if (selectedItem) {
            selectedItem.classList.add('selected');
        }
        
        // 加载图案到编辑器
        this.patternEditor.loadPattern(pattern);
    }
    
    // 选择产品
    selectProduct(product) {
        // 移除之前的选中状态
        document.querySelectorAll('.product-item').forEach(item => {
            item.classList.remove('selected');
        });
        
        // 添加选中状态
        const selectedItem = document.querySelector(`[data-product-id="${product.id}"]`);
        if (selectedItem) {
            selectedItem.classList.add('selected');
        }
        
        // 加载产品到编辑器
        this.patternEditor.loadProduct(product);
    }
    
    // 应用主题
    applyTheme(theme) {
        const body = document.body;
        
        if (typeof theme === 'string') {
            body.className = `theme-${theme}`;
            this.currentTheme = theme;
            
            switch(theme) {
                case 'christmas':
                    body.style.background = 'linear-gradient(135deg, #c41e3a 0%, #2e8b57 100%)';
                    break;
                case 'easter':
                    body.style.background = 'linear-gradient(135deg, #ffb6c1 0%, #98fb98 100%)';
                    break;
                case 'halloween':
                    body.style.background = 'linear-gradient(135deg, #ff4500 0%, #2f4f4f 100%)';
                    break;
                case 'valentine':
                    body.style.background = 'linear-gradient(135deg, #ff69b4 0%, #dc143c 100%)';
                    break;
                default:
                    body.style.background = 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)';
            }
        } else if (theme && theme.styles) {
            body.className = `theme-${theme.code}`;
            this.currentTheme = theme.code;
            
            if (theme.styles.background) {
                body.style.background = theme.styles.background;
            }
        }
    }
    
    // 初始化滑条值显示
    initializeRangeDisplays() {
        const ranges = [
            { id: 'pattern-opacity', valueId: 'opacity-value' },
            { id: 'horizontal-skew', valueId: 'h-skew-value' },
            { id: 'vertical-skew', valueId: 'v-skew-value' },
            { id: 'wrap-intensity', valueId: 'wrap-value' }
        ];

        ranges.forEach(range => {
            const slider = document.getElementById(range.id);
            const valueDisplay = document.getElementById(range.valueId);
            
            if (slider && valueDisplay) {
                slider.addEventListener('input', function() {
                    valueDisplay.textContent = parseFloat(this.value).toFixed(3);
                });
            }
        });
    }
}

// 应用程序主类
class PatternApp {
    constructor() {
        this.patternEditor = null;
        this.uiManager = null;
    }
    
    async init() {
        // 等待DOM加载完成
        if (document.readyState === 'loading') {
            await new Promise(resolve => {
                document.addEventListener('DOMContentLoaded', resolve);
            });
        }
        
        // 延迟初始化确保所有元素都已渲染
        setTimeout(async () => {
            await this.initializeApp();
        }, 100);
    }
    
    async initializeApp() {
        try {
            // 初始化编辑器
            this.patternEditor = new PatternEditor();
            this.uiManager = new UIManager(this.patternEditor);
            
            // 初始化UI
            this.uiManager.initializeRangeDisplays();
            
            // 加载所有数据
            await this.loadAllData();
            
            console.log('印花图案贴合系统初始化完成');
            
        } catch (error) {
            console.error('应用初始化失败:', error);
        }
    }
    
    async loadAllData() {
        try {
            // 并行加载所有数据
            const [patterns, categories, themes] = await Promise.all([
                DataManager.loadPatterns(),
                DataManager.loadCategories(),
                DataManager.loadThemes()
            ]);
            
            // 渲染UI
            this.uiManager.renderPatterns(patterns);
            this.uiManager.renderCategories(categories);
            this.uiManager.renderThemes(themes);
            
            console.log('所有数据加载完成');
            
        } catch (error) {
            console.error('数据加载失败:', error);
        }
    }
}

// 全局应用实例
window.patternApp = new PatternApp();

// 启动应用
window.patternApp.init();

// 兼容性：为了保持与现有代码的兼容性
window.patternEditor = null;
window.addEventListener('load', () => {
    setTimeout(() => {
        if (window.patternApp && window.patternApp.patternEditor) {
            window.patternEditor = window.patternApp.patternEditor;
        }
    }, 200);
});