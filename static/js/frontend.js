/**
 * 前台主要功能模块
 */

class FrontendApp {
    constructor() {
        this.currentTheme = 'default';
        this.accessCode = null;
        this.patterns = [];
        this.products = [];
        this.categories = [];
        this.currentPattern = null;
        this.currentProduct = null;
        this.canvas = null;
        this.ctx = null;
        this.canvasState = {
            scale: 1,
            offsetX: 0,
            offsetY: 0,
            rotation: 0,
            opacity: 1,
            patternX: 0,
            patternY: 0,
            patternScale: 1,
            patternRotation: 0,
            patternOpacity: 1
        };
        
        this.init();
    }
    
    init() {
        this.bindEvents();
        this.loadTheme();
        this.checkAuth();
    }
    
    bindEvents() {
        // 授权码登录
        const loginForm = document.getElementById('login-form');
        if (loginForm) {
            loginForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.handleLogin();
            });
        }
        
        // 主题切换按钮
        const themeBtn = document.getElementById('theme-btn');
        if (themeBtn) {
            themeBtn.addEventListener('click', (e) => {
                e.preventDefault();
                console.log('Theme button clicked');
            });
        }
        
        // 分类切换 - 使用事件委托
        document.addEventListener('click', (e) => {
            if (e.target.closest('.category-item')) {
                const categoryItem = e.target.closest('.category-item');
                const categoryId = categoryItem.dataset.categoryId;
                this.switchCategory(categoryId);
            }
        });
        
        // 图案选择
        document.addEventListener('click', (e) => {
            if (e.target.closest('.pattern-item')) {
                const patternId = e.target.closest('.pattern-item').dataset.patternId;
                this.selectPattern(patternId);
            }
        });
        
        // 产品选择
        document.addEventListener('click', (e) => {
            if (e.target.closest('.product-item')) {
                const productId = e.target.closest('.product-item').dataset.productId;
                this.selectProduct(productId);
            }
        });
        
        // 控制面板事件
        this.bindControlEvents();
        
        // 退出登录
        const logoutBtn = document.getElementById('logout-btn');
        if (logoutBtn) {
            logoutBtn.addEventListener('click', () => {
                this.logout();
            });
        }
        
        // 导出功能
        const exportBtn = document.getElementById('export-btn');
        if (exportBtn) {
            exportBtn.addEventListener('click', () => {
                this.exportImage();
            });
        }
        
        // 重置功能
        const resetBtn = document.getElementById('reset-btn');
        if (resetBtn) {
            resetBtn.addEventListener('click', () => {
                this.resetCanvas();
            });
        }
    }
    
    bindControlEvents() {
        // 缩放控制
        const scaleSlider = document.getElementById('scale-slider');
        if (scaleSlider) {
            scaleSlider.addEventListener('input', (e) => {
                this.canvasState.patternScale = parseFloat(e.target.value);
                this.updateCanvas();
                document.getElementById('scale-value').textContent = Math.round(e.target.value * 100) + '%';
            });
        }
        
        // 旋转控制
        const rotationSlider = document.getElementById('rotation-slider');
        if (rotationSlider) {
            rotationSlider.addEventListener('input', (e) => {
                this.canvasState.patternRotation = parseFloat(e.target.value);
                this.updateCanvas();
                document.getElementById('rotation-value').textContent = e.target.value + '°';
            });
        }
        
        // 透明度控制
        const opacitySlider = document.getElementById('opacity-slider');
        if (opacitySlider) {
            opacitySlider.addEventListener('input', (e) => {
                this.canvasState.patternOpacity = parseFloat(e.target.value);
                this.updateCanvas();
                document.getElementById('opacity-value').textContent = Math.round(e.target.value * 100) + '%';
            });
        }
    }
    
    async handleLogin() {
        const accessCodeInput = document.getElementById('access-code');
        const accessCode = accessCodeInput.value.trim();
        
        if (!accessCode) {
            showError('请输入访问码');
            return;
        }
        
        showLoading('验证访问码...');
        
        try {
            const response = await fetch('/api/auth/verify', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ accessCode: accessCode })
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.accessCode = accessCode;
                Storage.set('access_code', accessCode);
                this.showMainInterface();
                await this.loadData();
                showSuccess('登录成功！');
            } else {
                showError(result.message || '访问码无效');
            }
        } catch (error) {
            console.error('Login error:', error);
            showError('网络错误，请重试');
        } finally {
            hideLoading();
        }
    }
    
    checkAuth() {
        const savedAccessCode = Storage.get('access_code');
        if (savedAccessCode) {
            this.accessCode = savedAccessCode;
            this.verifyAccessCode();
        }
    }
    
    async verifyAccessCode() {
        if (!this.accessCode) return;
        
        try {
            const response = await fetch('/api/auth/verify', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ accessCode: this.accessCode })
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.showMainInterface();
                await this.loadData();
            } else {
                this.logout();
            }
        } catch (error) {
            console.error('Auth verification error:', error);
            this.logout();
        }
    }
    
    showMainInterface() {
        document.getElementById('login-screen').classList.remove('active');
        document.getElementById('main-screen').classList.add('active');
        
        // 初始化Canvas
        this.initCanvas();
    }
    
    logout() {
        this.accessCode = null;
        Storage.remove('access_code');
        document.getElementById('login-screen').classList.add('active');
        document.getElementById('main-screen').classList.remove('active');
        
        // 清空表单
        const accessCodeInput = document.getElementById('access-code');
        if (accessCodeInput) {
            accessCodeInput.value = '';
        }
    }
    
    async loadData() {
        showLoading('加载数据...');
        
        try {
            // 并行加载所有数据
            const [patternsRes, productsRes, categoriesRes, themesRes] = await Promise.all([
                fetch('/api/patterns'),
                fetch('/api/products'),
                fetch('/api/categories'),
                fetch('/api/themes')
            ]);
            
            this.patterns = await patternsRes.json();
            this.products = await productsRes.json();
            this.categories = await categoriesRes.json();
            const themes = await themesRes.json();
            
            this.renderPatterns();
            this.renderProducts();
            this.renderCategories();
            this.renderThemeSelector(themes);
            
        } catch (error) {
            console.error('Load data error:', error);
            showError('数据加载失败');
        } finally {
            hideLoading();
        }
    }
    
    renderPatterns() {
        const container = document.getElementById('pattern-list');
        if (!container) return;
        
        const patterns = this.patterns.data || this.patterns;
        container.innerHTML = patterns.map(pattern => `
            <div class="pattern-item" data-pattern-id="${pattern.id}">
                <img src="/uploads/patterns/${pattern.filename}" alt="${pattern.name}" loading="lazy">
                <div class="pattern-info">
                    <h4>${pattern.name}</h4>
                </div>
            </div>
        `).join('');
    }
    
    renderProducts() {
        const container = document.getElementById('product-list');
        if (!container) return;
        
        const products = this.products.data || this.products;
        container.innerHTML = products.map(product => `
            <div class="product-item" data-product-id="${product.id}">
                <img src="/uploads/products/${product.product_image}" alt="${product.title}" loading="lazy">
                <div class="product-info">
                    <h4>${product.title}</h4>
                </div>
            </div>
        `).join('');
    }
    
    renderCategories() {
        const container = document.getElementById('category-list');
        if (!container) return;
        
        const categories = this.categories.data || this.categories;
        container.innerHTML = categories.map(category => `
            <div class="category-item ${category.is_default ? 'active' : ''}" data-category-id="${category.id}">
                <span>${category.name}</span>
            </div>
        `).join('');
    }
    
    renderThemeSelector(themes) {
        const themeBtn = document.getElementById('theme-btn');
        if (!themeBtn) return;
        
        const themeData = themes.data || themes;
        const currentTheme = themeData.find(t => t.is_default) || themeData[0];
        if (currentTheme) {
            const themeNameSpan = document.getElementById('current-theme-name');
            if (themeNameSpan) {
                themeNameSpan.textContent = currentTheme.display_name || currentTheme.name;
            }
        }
    }
    
    switchCategory(categoryId) {
        // 更新标签状态
        document.querySelectorAll('.category-item').forEach(item => {
            item.classList.remove('active');
        });
        
        const selectedCategory = document.querySelector(`[data-category-id="${categoryId}"]`);
        if (selectedCategory) {
            selectedCategory.classList.add('active');
        }
        
        // 过滤产品
        const container = document.getElementById('product-list');
        if (!container) return;
        
        const products = this.products.data || this.products;
        const filteredProducts = categoryId === 'all' 
            ? products 
            : products.filter(product => product.category_id == categoryId);
            
        container.innerHTML = filteredProducts.map(product => `
            <div class="product-item" data-product-id="${product.id}">
                <img src="/uploads/products/${product.product_image}" alt="${product.title}" loading="lazy">
                <div class="product-info">
                    <h4>${product.title}</h4>
                </div>
            </div>
        `).join('');
    }
    
    selectPattern(patternId) {
        const patterns = this.patterns.data || this.patterns;
        this.currentPattern = patterns.find(p => p.id == patternId);
        
        // 更新选中状态
        document.querySelectorAll('.pattern-item').forEach(item => {
            item.classList.remove('selected');
        });
        document.querySelector(`[data-pattern-id="${patternId}"]`).classList.add('selected');
        
        // 更新Canvas
        this.updateCanvas();
        
        // 更新选择信息
        const selectedPatternSpan = document.getElementById('selected-pattern');
        if (selectedPatternSpan && this.currentPattern) {
            selectedPatternSpan.textContent = this.currentPattern.name;
        }
    }
    
    selectProduct(productId) {
        const products = this.products.data || this.products;
        this.currentProduct = products.find(p => p.id == productId);
        
        // 更新选中状态
        document.querySelectorAll('.product-item').forEach(item => {
            item.classList.remove('selected');
        });
        document.querySelector(`[data-product-id="${productId}"]`).classList.add('selected');
        
        // 更新Canvas
        this.updateCanvas();
        
        // 更新选择信息
        const selectedProductSpan = document.getElementById('selected-product');
        if (selectedProductSpan && this.currentProduct) {
            selectedProductSpan.textContent = this.currentProduct.title;
        }
    }
    
    initCanvas() {
        this.canvas = document.getElementById('design-canvas');
        if (!this.canvas) {
            console.warn('Canvas element not found');
            return;
        }
        
        this.ctx = this.canvas.getContext('2d');
        
        // 设置Canvas尺寸
        this.resizeCanvas();
        
        // 绑定Canvas事件
        this.bindCanvasEvents();
        
        // 监听窗口大小变化
        window.addEventListener('resize', debounce(() => {
            this.resizeCanvas();
            this.updateCanvas();
        }, 250));
    }
    
    resizeCanvas() {
        if (!this.canvas) {
            console.warn('Canvas not found');
            return;
        }
        
        const container = this.canvas.parentElement;
        if (!container) {
            console.warn('Canvas container not found');
            // 使用默认尺寸
            this.canvas.width = 800;
            this.canvas.height = 600;
            return;
        }
        
        try {
            const rect = container.getBoundingClientRect();
            this.canvas.width = rect.width || 800;
            this.canvas.height = rect.height || 600;
            
            // 重新绘制
            this.updateCanvas();
        } catch (error) {
            console.error('resizeCanvas error:', error);
            // 使用默认尺寸
            this.canvas.width = 800;
            this.canvas.height = 600;
        }
    }
    
    bindCanvasEvents() {
        if (!this.canvas) return;
        
        let isDragging = false;
        let lastPoint = { x: 0, y: 0 };
        
        // 鼠标事件
        this.canvas.addEventListener('mousedown', (e) => {
            isDragging = true;
            lastPoint = { x: e.offsetX, y: e.offsetY };
        });
        
        this.canvas.addEventListener('mousemove', (e) => {
            if (!isDragging) return;
            
            const currentPoint = { x: e.offsetX, y: e.offsetY };
            const deltaX = currentPoint.x - lastPoint.x;
            const deltaY = currentPoint.y - lastPoint.y;
            
            this.canvasState.patternX += deltaX;
            this.canvasState.patternY += deltaY;
            
            this.updateCanvas();
            lastPoint = currentPoint;
        });
        
        this.canvas.addEventListener('mouseup', () => {
            isDragging = false;
        });
        
        // 触摸事件
        this.canvas.addEventListener('touchstart', (e) => {
            e.preventDefault();
            const touch = e.touches[0];
            const rect = this.canvas.getBoundingClientRect();
            isDragging = true;
            lastPoint = { 
                x: touch.clientX - rect.left, 
                y: touch.clientY - rect.top 
            };
        });
        
        this.canvas.addEventListener('touchmove', (e) => {
            e.preventDefault();
            if (!isDragging) return;
            
            const touch = e.touches[0];
            const rect = this.canvas.getBoundingClientRect();
            const currentPoint = { 
                x: touch.clientX - rect.left, 
                y: touch.clientY - rect.top 
            };
            
            const deltaX = currentPoint.x - lastPoint.x;
            const deltaY = currentPoint.y - lastPoint.y;
            
            this.canvasState.patternX += deltaX;
            this.canvasState.patternY += deltaY;
            
            this.updateCanvas();
            lastPoint = currentPoint;
        });
        
        this.canvas.addEventListener('touchend', (e) => {
            e.preventDefault();
            isDragging = false;
        });
    }
    
    async updateCanvas() {
        if (!this.ctx) return;
        
        // 清空Canvas
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        
        // 绘制产品背景
        if (this.currentProduct) {
            await this.drawProduct();
        }
        
        // 绘制图案
        if (this.currentPattern) {
            await this.drawPattern();
        }
    }
    
    async drawProduct() {
        try {
            const img = await loadImage(`/uploads/products/${this.currentProduct.product_image}`);
            
            // 计算适合Canvas的尺寸
            const scale = Math.min(
                this.canvas.width / img.width,
                this.canvas.height / img.height
            ) * 0.8;
            
            const width = img.width * scale;
            const height = img.height * scale;
            const x = (this.canvas.width - width) / 2;
            const y = (this.canvas.height - height) / 2;
            
            this.ctx.drawImage(img, x, y, width, height);
            
        } catch (error) {
            console.error('Draw product error:', error);
        }
    }
    
    async drawPattern() {
        try {
            const img = await loadImage(`/uploads/patterns/${this.currentPattern.filename}`);
            
            this.ctx.save();
            
            // 设置透明度
            this.ctx.globalAlpha = this.canvasState.patternOpacity;
            
            // 计算图案位置和尺寸
            const baseSize = Math.min(this.canvas.width, this.canvas.height) * 0.3;
            const size = baseSize * this.canvasState.patternScale;
            
            const x = this.canvas.width / 2 + this.canvasState.patternX;
            const y = this.canvas.height / 2 + this.canvasState.patternY;
            
            // 移动到图案中心
            this.ctx.translate(x, y);
            
            // 旋转
            this.ctx.rotate(degToRad(this.canvasState.patternRotation));
            
            // 绘制图案
            this.ctx.drawImage(img, -size/2, -size/2, size, size);
            
            this.ctx.restore();
            
        } catch (error) {
            console.error('Draw pattern error:', error);
        }
    }
    
    resetCanvas() {
        this.canvasState = {
            scale: 1,
            offsetX: 0,
            offsetY: 0,
            rotation: 0,
            opacity: 1,
            patternX: 0,
            patternY: 0,
            patternScale: 1,
            patternRotation: 0,
            patternOpacity: 1
        };
        
        // 重置控制面板
        const scaleSlider = document.getElementById('scale-slider');
        const rotationSlider = document.getElementById('rotation-slider');
        const opacitySlider = document.getElementById('opacity-slider');
        
        if (scaleSlider) scaleSlider.value = 1;
        if (rotationSlider) rotationSlider.value = 0;
        if (opacitySlider) opacitySlider.value = 1;
        
        // 更新显示值
        const scaleValue = document.getElementById('scale-value');
        const rotationValue = document.getElementById('rotation-value');
        const opacityValue = document.getElementById('opacity-value');
        
        if (scaleValue) scaleValue.textContent = '100%';
        if (rotationValue) rotationValue.textContent = '0°';
        if (opacityValue) opacityValue.textContent = '100%';
        
        this.updateCanvas();
        showSuccess('已重置');
    }
    
    async exportImage() {
        if (!this.canvas || !this.currentProduct || !this.currentPattern) {
            showError('请先选择产品和图案');
            return;
        }
        
        showLoading('导出图片...');
        
        try {
            const blob = await canvasToBlob(this.canvas);
            const filename = `${this.currentProduct.title}_${this.currentPattern.name}_${Date.now()}.png`;
            downloadFile(blob, filename);
            showSuccess('导出成功！');
        } catch (error) {
            console.error('Export error:', error);
            showError('导出失败');
        } finally {
            hideLoading();
        }
    }
    
    loadTheme() {
        // 移除旧的主题样式
        const oldThemeLink = document.getElementById('theme-css');
        if (oldThemeLink) {
            oldThemeLink.remove();
        }
        
        // 加载新的主题样式
        const link = document.createElement('link');
        link.id = 'theme-css';
        link.rel = 'stylesheet';
        link.href = `/static/themes/${this.currentTheme}.css`;
        document.head.appendChild(link);
    }
}

// 页面加载完成后初始化应用
document.addEventListener('DOMContentLoaded', () => {
    window.frontendApp = new FrontendApp();
});