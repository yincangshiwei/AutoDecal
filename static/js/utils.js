/**
 * 工具函数库
 */

// 防抖函数
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// 节流函数
function throttle(func, limit) {
    let inThrottle;
    return function() {
        const args = arguments;
        const context = this;
        if (!inThrottle) {
            func.apply(context, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    }
}

// 显示加载状态
function showLoading(message = '加载中...') {
    const loading = document.getElementById('loading');
    const loadingText = loading.querySelector('p');
    if (loadingText) {
        loadingText.textContent = message;
    }
    loading.style.display = 'flex';
}

// 隐藏加载状态
function hideLoading() {
    const loading = document.getElementById('loading');
    loading.style.display = 'none';
}

// 显示错误消息
function showError(message, container = null) {
    const errorDiv = container || document.getElementById('login-error');
    if (errorDiv) {
        errorDiv.textContent = message;
        errorDiv.style.display = 'block';
        
        // 3秒后自动隐藏
        setTimeout(() => {
            errorDiv.style.display = 'none';
        }, 3000);
    }
}

// 显示成功消息
function showSuccess(message) {
    // 创建临时成功提示
    const successDiv = document.createElement('div');
    successDiv.className = 'success-message';
    successDiv.textContent = message;
    successDiv.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: #4caf50;
        color: white;
        padding: 15px 20px;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        z-index: 10000;
        animation: slideInRight 0.3s ease;
    `;
    
    document.body.appendChild(successDiv);
    
    // 3秒后移除
    setTimeout(() => {
        successDiv.style.animation = 'slideOutRight 0.3s ease';
        setTimeout(() => {
            document.body.removeChild(successDiv);
        }, 300);
    }, 3000);
}

// 格式化文件大小
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// 生成唯一ID
function generateId() {
    return Date.now().toString(36) + Math.random().toString(36).substr(2);
}

// 深拷贝对象
function deepClone(obj) {
    if (obj === null || typeof obj !== 'object') return obj;
    if (obj instanceof Date) return new Date(obj.getTime());
    if (obj instanceof Array) return obj.map(item => deepClone(item));
    if (typeof obj === 'object') {
        const clonedObj = {};
        for (const key in obj) {
            if (obj.hasOwnProperty(key)) {
                clonedObj[key] = deepClone(obj[key]);
            }
        }
        return clonedObj;
    }
}

// 检测设备类型
function getDeviceType() {
    const userAgent = navigator.userAgent.toLowerCase();
    const isMobile = /mobile|android|iphone|ipad|phone/i.test(userAgent);
    const isTablet = /tablet|ipad/i.test(userAgent) || 
                    (window.innerWidth >= 768 && window.innerWidth <= 1024);
    
    if (isMobile && !isTablet) return 'mobile';
    if (isTablet) return 'tablet';
    return 'desktop';
}

// 检测触控支持
function isTouchDevice() {
    return 'ontouchstart' in window || navigator.maxTouchPoints > 0;
}

// 获取元素相对于页面的位置
function getElementPosition(element) {
    if (!element) {
        console.warn('getElementPosition: element is null');
        return { x: 0, y: 0, width: 0, height: 0 };
    }
    
    try {
        const rect = element.getBoundingClientRect();
        return {
            x: rect.left + window.scrollX,
            y: rect.top + window.scrollY,
            width: rect.width,
            height: rect.height
        };
    } catch (error) {
        console.error('getElementPosition error:', error);
        return { x: 0, y: 0, width: 0, height: 0 };
    }
}

// 计算两点之间的距离
function getDistance(point1, point2) {
    const dx = point2.x - point1.x;
    const dy = point2.y - point1.y;
    return Math.sqrt(dx * dx + dy * dy);
}

// 计算角度
function getAngle(point1, point2) {
    const dx = point2.x - point1.x;
    const dy = point2.y - point1.y;
    return Math.atan2(dy, dx) * 180 / Math.PI;
}

// 限制数值范围
function clamp(value, min, max) {
    return Math.min(Math.max(value, min), max);
}

// 线性插值
function lerp(start, end, factor) {
    return start + (end - start) * factor;
}

// 将角度转换为弧度
function degToRad(degrees) {
    return degrees * Math.PI / 180;
}

// 将弧度转换为角度
function radToDeg(radians) {
    return radians * 180 / Math.PI;
}

// 检查点是否在矩形内
function isPointInRect(point, rect) {
    return point.x >= rect.x && 
           point.x <= rect.x + rect.width &&
           point.y >= rect.y && 
           point.y <= rect.y + rect.height;
}

// 本地存储工具
const Storage = {
    set(key, value) {
        try {
            localStorage.setItem(key, JSON.stringify(value));
            return true;
        } catch (e) {
            console.error('Storage set error:', e);
            return false;
        }
    },
    
    get(key, defaultValue = null) {
        try {
            const item = localStorage.getItem(key);
            return item ? JSON.parse(item) : defaultValue;
        } catch (e) {
            console.error('Storage get error:', e);
            return defaultValue;
        }
    },
    
    remove(key) {
        try {
            localStorage.removeItem(key);
            return true;
        } catch (e) {
            console.error('Storage remove error:', e);
            return false;
        }
    },
    
    clear() {
        try {
            localStorage.clear();
            return true;
        } catch (e) {
            console.error('Storage clear error:', e);
            return false;
        }
    }
};

// 图片加载工具
function loadImage(src) {
    return new Promise((resolve, reject) => {
        const img = new Image();
        img.onload = () => resolve(img);
        img.onerror = reject;
        img.src = src;
    });
}

// 下载文件
function downloadFile(blob, filename) {
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

// Canvas转换为Blob
function canvasToBlob(canvas, type = 'image/png', quality = 0.92) {
    return new Promise(resolve => {
        canvas.toBlob(resolve, type, quality);
    });
}

// 添加CSS动画样式
function addAnimationStyles() {
    if (document.getElementById('animation-styles')) return;
    
    const style = document.createElement('style');
    style.id = 'animation-styles';
    style.textContent = `
        @keyframes slideInRight {
            from {
                transform: translateX(100%);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }
        
        @keyframes slideOutRight {
            from {
                transform: translateX(0);
                opacity: 1;
            }
            to {
                transform: translateX(100%);
                opacity: 0;
            }
        }
        
        @keyframes pulse {
            0% { transform: scale(1); }
            50% { transform: scale(1.05); }
            100% { transform: scale(1); }
        }
        
        @keyframes shake {
            0%, 100% { transform: translateX(0); }
            25% { transform: translateX(-5px); }
            75% { transform: translateX(5px); }
        }
        
        .pulse { animation: pulse 0.6s ease; }
        .shake { animation: shake 0.5s ease; }
    `;
    
    document.head.appendChild(style);
}

// 初始化工具函数
function initUtils() {
    addAnimationStyles();
    
    // 设置设备类型类名
    document.body.classList.add(`device-${getDeviceType()}`);
    
    if (isTouchDevice()) {
        document.body.classList.add('touch-device');
    }
}

// 页面加载完成后初始化
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initUtils);
} else {
    initUtils();
}

// 导出工具函数（如果使用模块系统）
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        debounce,
        throttle,
        showLoading,
        hideLoading,
        showError,
        showSuccess,
        formatFileSize,
        generateId,
        deepClone,
        getDeviceType,
        isTouchDevice,
        getElementPosition,
        getDistance,
        getAngle,
        clamp,
        lerp,
        degToRad,
        radToDeg,
        isPointInRect,
        Storage,
        loadImage,
        downloadFile,
        canvasToBlob
    };
}