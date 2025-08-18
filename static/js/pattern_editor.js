/**
 * 3D环绕贴图编辑器
 * 整合了原有的数据管理功能和新的3D渲染引擎
 */

// 数据管理类 - 从 pattern_editor_final.js 移植
class DataManager {
    static async fetchAPI(url) {
        try {
            const response = await fetch(url);
            
            // 检查会话是否失效
            if (response.status === 401) {
                const result = await response.json();
                if (result.redirect) {
                    alert(result.message || '会话已失效，请重新登录');
                    window.location.href = result.redirect;
                    return [];
                }
            }
            
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

// 将translations暴露给全局作用域，供其他脚本使用
window.translations = window.translations || {};

// 主编辑器类 - 基于 templates/ref/editor.js 的3D引擎
window.addEventListener('load', () => {
    // 等待所有预加载图片完全加载
    const allImages = document.querySelectorAll('#preload-images img');
    const imageLoadPromises = Array.from(allImages).map(img => {
        return new Promise((resolve) => {
            if (img.complete && img.naturalWidth > 0) {
                resolve();
            } else {
                img.onload = () => resolve();
                img.onerror = () => resolve(); // 即使某些图片失败也继续
            }
        });
    });

    Promise.all(imageLoadPromises).then(() => {
        // 额外延迟确保WebGL上下文准备就绪
        setTimeout(() => {
            init();
        }, 100);
    });

    // --- Part 1: 设置和状态 ---
    const canvas = document.getElementById('editorCanvas');
    const canvasContainer = document.querySelector('.canvas-container');
    const placeholder = document.getElementById('canvasPlaceholder');

    // 安全检查：确保必要的DOM元素存在
    if (!canvas || !canvasContainer || !placeholder) {
        console.error('必需的DOM元素未找到');
        return;
    }

    let renderer, scene, camera, plane, shaderMaterial;
    let textureLoader = new THREE.TextureLoader();

    const patternListContainer = document.querySelector('.pattern-list');
    const productListContainer = document.querySelector('.product-list');

    // 数据存储
    let patterns = [];
    let products = [];
    let categories = [];

    let activePatternItem = null;
    let activeProductItem = null;

    const state = {
        patternId: null,
        productId: null,
        depthId: null,
        
        tx: 0, ty: 0, scale: 1,

        distortion: 0.3,
        opacity: 1.0,
        skewX: 0.0,
        skewY: 0.0,
        blendMode: 'normal',
        depthThreshold: 0.7,
        perspective: 0.0,
    };

    // --- Part 2: 着色器 ---
    const vertexShader = `
        varying vec2 vUv;
        void main() {
            vUv = uv;
            gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
        }
    `;

    const fragmentShader = `
        precision highp float;
        varying vec2 vUv;

        uniform sampler2D uProduct;
        uniform sampler2D uPattern;
        uniform sampler2D uDepth;
        uniform vec2 uCanvasSize;
        uniform vec2 uPatSize;
        uniform vec2 uProductSize;
        uniform vec2 uPatternSize;
        uniform vec2 uTranslate;
        uniform mat2 uTransform;
        uniform float uDistortion;
        uniform float uOpacity;
        uniform int uBlend;
        uniform float uDepthTh;
        uniform float uPerspective;
        
        uniform float uNormalStrength;

        vec3 blendOverlay(vec3 b, vec3 s){
            vec3 lt = step(s, vec3(0.5));
            return lt*(2.0*b*s) + (1.0-lt)*(1.0 - 2.0*(1.0-b)*(1.0-s));
        }
        
        vec3 blendScreen(vec3 b, vec3 s) {
            return 1.0 - (1.0 - b) * (1.0 - s);
        }
        
        vec3 blendDarken(vec3 b, vec3 s) {
            return min(b, s);
        }
        
        vec3 blendLighten(vec3 b, vec3 s) {
            return max(b, s);
        }
        
        vec3 blendColorDodge(vec3 b, vec3 s) {
            return b / (1.0 - s + 0.001);
        }
        
        vec3 blendColorBurn(vec3 b, vec3 s) {
            return 1.0 - (1.0 - b) / (s + 0.001);
        }
        
        vec3 blendSoftLight(vec3 b, vec3 s) {
            vec3 lt = step(s, vec3(0.5));
            return lt * (2.0 * b * s + b * b * (1.0 - 2.0 * s)) + 
                   (1.0 - lt) * (sqrt(b) * (2.0 * s - 1.0) + 2.0 * b * (1.0 - s));
        }
        
        vec3 blendHardLight(vec3 b, vec3 s) {
            vec3 lt = step(s, vec3(0.5));
            return lt * (2.0 * b * s) + (1.0 - lt) * (1.0 - 2.0 * (1.0 - b) * (1.0 - s));
        }
        
        vec3 blendHologram(vec3 b, vec3 s) {
            float hue = fract(s.r * 6.0);
            vec3 rainbow = vec3(
                abs(hue * 6.0 - 3.0) - 1.0,
                2.0 - abs(hue * 6.0 - 2.0),
                2.0 - abs(hue * 6.0 - 4.0)
            );
            rainbow = clamp(rainbow, 0.0, 1.0);
            return mix(b, rainbow * s, 0.7);
        }

        vec2 displacementWarp(vec2 screenPx, vec2 uv, float depth) {
            vec2 texel = 1.0 / uCanvasSize;
            
            vec2 grad = vec2(
                texture2D(uDepth, uv + vec2(texel.x, 0.0)).r - texture2D(uDepth, uv - vec2(texel.x, 0.0)).r,
                texture2D(uDepth, uv + vec2(0.0, texel.y)).r - texture2D(uDepth, uv - vec2(0.0, texel.y)).r
            );
            
            float depthFactor = pow(depth, 0.7);
            vec2 displacement = grad * uDistortion * depthFactor * 200.0;
            
            return screenPx + displacement;
        }

        vec2 perspectiveWarp(vec2 screenPx, vec2 uv, float depth) {
            vec2 center = uCanvasSize * 0.5;
            vec2 fromCenter = screenPx - center;
            
            float perspectiveFactor = 1.0 + (depth - 0.5) * uPerspective;
            perspectiveFactor = max(0.1, perspectiveFactor);
            
            vec2 warped = center + fromCenter * perspectiveFactor;
            return warped;
        }

        vec2 complexWarp(vec2 screenPx, vec2 uv, float depth) {
            vec2 displaced = displacementWarp(screenPx, uv, depth);
            vec2 perspective = perspectiveWarp(displaced, uv, depth);
            
            float totalStrength = uDistortion + uPerspective + 0.001;
            float w_dist = uDistortion / totalStrength;
            float w_pers = uPerspective / totalStrength;

            return mix(screenPx, mix(displaced, perspective, w_pers), 1.0);
        }

        void main(){
            vec2 canvasAspect = uCanvasSize / max(uCanvasSize.x, uCanvasSize.y);
            vec2 productAspect = uProductSize / max(uProductSize.x, uProductSize.y);
            
            float scaleX = canvasAspect.x / productAspect.x;
            float scaleY = canvasAspect.y / productAspect.y;
            float scale = min(scaleX, scaleY);
            
            vec2 scaledSize = productAspect * scale;
            vec2 offset = (canvasAspect - scaledSize) * 0.5;
            vec2 productUV = (vUv * canvasAspect - offset) / scaledSize;
            
            if (productUV.x < 0.0 || productUV.x > 1.0 || productUV.y < 0.0 || productUV.y > 1.0) {
                gl_FragColor = vec4(0.0, 0.0, 0.0, 0.0);
                return;
            }
            
            vec4 base = texture2D(uProduct, productUV);
            float depth = texture2D(uDepth, productUV).r;
            
            float pixelFeather = 2.0 / min(uCanvasSize.x, uCanvasSize.y);
            float maskDepth = smoothstep(uDepthTh - pixelFeather, uDepthTh + pixelFeather, depth);
            
            if(maskDepth < 0.01) {
                gl_FragColor = base;
                return;
            }

            vec2 screenPx = vUv * uCanvasSize;
            vec2 warpedScreenPx = complexWarp(screenPx, productUV, depth);

            vec2 canvasCenter = uCanvasSize * 0.5;
            vec2 centeredPx = warpedScreenPx - canvasCenter;
            vec2 translatedPx = centeredPx - vec2(uTranslate.x, uTranslate.y);
            
            float det = uTransform[0][0] * uTransform[1][1] - uTransform[0][1] * uTransform[1][0];
            mat2 invTransform = mat2(uTransform[1][1], -uTransform[0][1], -uTransform[1][0], uTransform[0][0]) / max(det, 1e-6);
            vec2 patPx = invTransform * translatedPx;
            
            vec2 patUV = (patPx + 0.5 * uPatternSize) / uPatternSize;

            if (patUV.x < 0.0 || patUV.x > 1.0 || patUV.y < 0.0 || patUV.y > 1.0) {
                gl_FragColor = base;
                return;
            }

            vec4 pat = texture2D(uPattern, patUV);
            
            float finalAlpha = pat.a * uOpacity * maskDepth;

            vec3 blended;
            if(uBlend == 0){ // normal
                blended = mix(base.rgb, pat.rgb, finalAlpha);
            } else if(uBlend == 1){ // multiply
                blended = mix(base.rgb, base.rgb * pat.rgb, finalAlpha);
            } else if(uBlend == 2){ // screen
                blended = mix(base.rgb, blendScreen(base.rgb, pat.rgb), finalAlpha);
            } else if(uBlend == 3){ // overlay
                blended = mix(base.rgb, blendOverlay(base.rgb, pat.rgb), finalAlpha);
            } else if(uBlend == 4){ // darken
                blended = mix(base.rgb, blendDarken(base.rgb, pat.rgb), finalAlpha);
            } else if(uBlend == 5){ // lighten
                blended = mix(base.rgb, blendLighten(base.rgb, pat.rgb), finalAlpha);
            } else if(uBlend == 6){ // color-dodge
                blended = mix(base.rgb, blendColorDodge(base.rgb, pat.rgb), finalAlpha);
            } else if(uBlend == 7){ // color-burn
                blended = mix(base.rgb, blendColorBurn(base.rgb, pat.rgb), finalAlpha);
            } else if(uBlend == 8){ // soft-light
                blended = mix(base.rgb, blendSoftLight(base.rgb, pat.rgb), finalAlpha);
            } else if(uBlend == 9){ // hard-light
                blended = mix(base.rgb, blendHardLight(base.rgb, pat.rgb), finalAlpha);
            } else { // hologram
                blended = mix(base.rgb, blendHologram(base.rgb, pat.rgb), finalAlpha);
            }
            
            gl_FragColor = vec4(blended, base.a);
        }
    `;

    // --- Part 3: 初始化 ---
    function init() {
        renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true, preserveDrawingBuffer: true });
        renderer.setPixelRatio(window.devicePixelRatio);
        
        scene = new THREE.Scene();
        camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);

        shaderMaterial = new THREE.ShaderMaterial({
            uniforms: {
                uProduct: { value: null },
                uPattern: { value: null },
                uDepth: { value: null },
                uCanvasSize: { value: new THREE.Vector2(canvas.width, canvas.height) },
                uProductSize: { value: new THREE.Vector2(1, 1) },
                uPatSize: { value: new THREE.Vector2(1, 1) },
                uPatternSize: { value: new THREE.Vector2(1, 1) },
                uTranslate: { value: new THREE.Vector2(0, 0) },
                uTransform: { value: new Float32Array([1, 0, 0, 1]) },
                uDistortion: { value: state.distortion },
                uOpacity: { value: state.opacity },
                uBlend: { value: 0 },
                uDepthTh: { value: state.depthThreshold },
                uPerspective: { value: state.perspective },
            },
            vertexShader,
            fragmentShader,
            transparent: true,
        });

        const geometry = new THREE.PlaneGeometry(2, 2);
        plane = new THREE.Mesh(geometry, shaderMaterial);
        scene.add(plane);

        setupUIListeners();
        setupCanvasInteraction();
        setupActions();
        
        window.addEventListener('resize', onWindowResize, false);
        onWindowResize();
        
        loadAllData();
        
        animate();
    }

    // --- Part 4: 尺寸调整和纹理加载 ---
    function onWindowResize() {
        const { clientWidth, clientHeight } = canvasContainer;
        renderer.setSize(clientWidth, clientHeight);
        
        camera.left = -1;
        camera.right = 1;
        camera.top = 1;
        camera.bottom = -1;
        camera.updateProjectionMatrix();
        
        shaderMaterial.uniforms.uCanvasSize.value.set(clientWidth, clientHeight);
    }

    // 创建预加载图片并加载纹理 - 关键修复
    function createImageAndLoadTexture(imageURL, id) {
        return new Promise((resolve, reject) => {
            if (!imageURL) return resolve(null);
            
            // 创建预加载图片元素
            const img = document.createElement('img');
            img.id = id;
            img.style.display = 'none';
            img.crossOrigin = 'anonymous';
            
            img.onload = () => {
                // 图片加载完成后，使用TextureLoader加载纹理
                textureLoader.load(
                    imageURL,
                    (texture) => {
                        texture.flipY = true;
                        texture.format = THREE.RGBAFormat;
                        texture.type = THREE.UnsignedByteType;
                        resolve(texture);
                    },
                    undefined,
                    (error) => {
                        console.error(`纹理加载失败 ${imageURL}:`, error);
                        resolve(null); // 失败时返回null而不是reject
                    }
                );
            };
            
            img.onerror = (error) => {
                console.error(`图片加载失败 ${imageURL}:`, error);
                resolve(null); // 失败时返回null而不是reject
            };
            
            // 添加到预加载容器
            const preloadContainer = document.getElementById('preload-images');
            if (preloadContainer) {
                preloadContainer.appendChild(img);
            }
            
            img.src = imageURL;
        });
    }

    function updatePattern(texture) {
        if (texture) {
            shaderMaterial.uniforms.uPattern.value = texture;
            shaderMaterial.uniforms.uPatSize.value.set(texture.image.width, texture.image.height);
            shaderMaterial.uniforms.uPatternSize.value.set(texture.image.width, texture.image.height);
        } else {
            shaderMaterial.uniforms.uPattern.value = null;
            shaderMaterial.uniforms.uPatSize.value.set(1, 1);
            shaderMaterial.uniforms.uPatternSize.value.set(1, 1);
        }
    }

    function updateProduct(productTexture, depthTexture) {
        if (productTexture) {
            shaderMaterial.uniforms.uProduct.value = productTexture;
            shaderMaterial.uniforms.uProductSize.value.set(productTexture.image.width, productTexture.image.height);
            shaderMaterial.uniforms.uDepth.value = depthTexture || productTexture;
        } else {
            shaderMaterial.uniforms.uProduct.value = null;
            shaderMaterial.uniforms.uProductSize.value.set(1, 1);
            shaderMaterial.uniforms.uDepth.value = null;
        }
    }

    function checkAndUpdatePreview() {
        if (!state.productId) {
            placeholder.style.display = 'flex';
            placeholder.innerText = '请选择产品图';
            return;
        }
        
        placeholder.style.display = 'none';
    }

    // --- Part 5: UI事件监听器 ---
    // 背景图：获取/应用/按主题加载
    let bgOverlayOpacityTop = parseFloat(localStorage.getItem('bgOpacityTop') || '0.3');
    let bgOverlayOpacityBottom = parseFloat(localStorage.getItem('bgOpacityBottom') || '0.3');
    async function fetchBackgrounds(themeKey) {
        try {
            const resp = await fetch(`/api/theme-backgrounds?theme=${encodeURIComponent(themeKey)}`);
            const json = await resp.json();
            if (json && json.success && Array.isArray(json.data)) {
                return json.data;
            }
        } catch (error) {
            console.error('获取背景图失败:', error);
        }
        return [];
    }

    function applyBackground(url, themeKey) {
        const body = document.body;
        const container = document.querySelector('.editor-container');

        if (url) {
            // 叠加半透明白，保持白色为主；透明度分为上下两端可独立调节
            const a1 = Math.max(0, Math.min(1, Number.isFinite(bgOverlayOpacityTop) ? bgOverlayOpacityTop : 0.3));
            const a2 = Math.max(0, Math.min(1, Number.isFinite(bgOverlayOpacityBottom) ? bgOverlayOpacityBottom : 0.3));
            const layered = `linear-gradient(rgba(255,255,255,${a1}), rgba(255,255,255,${a2})), url('${url}')`;

            if (body) {
                body.style.setProperty('background-image', layered, 'important');
                body.style.setProperty('background-size', 'cover, cover', 'important');
                body.style.setProperty('background-position', 'center center, center center', 'important');
                body.style.setProperty('background-repeat', 'no-repeat, no-repeat', 'important');
                body.style.setProperty('background-attachment', 'fixed, fixed', 'important');
            }
            if (container) {
                container.style.setProperty('background-image', layered, 'important');
                container.style.setProperty('background-size', 'cover, cover', 'important');
                container.style.setProperty('background-position', 'center center, center center', 'important');
                container.style.setProperty('background-repeat', 'no-repeat, no-repeat', 'important');
            }
        } else {
            // 恢复为纯色（移除覆盖样式）
            if (body) {
                body.style.removeProperty('background-image');
                body.style.removeProperty('background-size');
                body.style.removeProperty('background-position');
                body.style.removeProperty('background-repeat');
                body.style.removeProperty('background-attachment');
            }
            if (container) {
                container.style.removeProperty('background-image');
                container.style.removeProperty('background-size');
                container.style.removeProperty('background-position');
                container.style.removeProperty('background-repeat');
            }
        }

        if (themeKey) {
            try {
                localStorage.setItem(`selectedBgUrl_${themeKey}`, url || '');
            } catch (_) {}
        }
    }

    // 更新透明度标签的全局函数
    window.updateBgOpacityLabels = function() {
        const topLabel = document.getElementById('bgOpacityTopLabel');
        const bottomLabel = document.getElementById('bgOpacityBottomLabel');
        
        if (!topLabel || !bottomLabel) return;
        
        const currentLang = localStorage.getItem('language') || 'zh-CN';
        const upperText = window.translations && window.translations[currentLang] && window.translations[currentLang]['upper-opacity'] 
            ? window.translations[currentLang]['upper-opacity'] 
            : 'Upper Opacity';
        const lowerText = window.translations && window.translations[currentLang] && window.translations[currentLang]['lower-opacity'] 
            ? window.translations[currentLang]['lower-opacity'] 
            : 'Lower Opacity';
        
        topLabel.textContent = `${upperText} (${bgOverlayOpacityTop.toFixed(2)})`;
        bottomLabel.textContent = `${lowerText} (${bgOverlayOpacityBottom.toFixed(2)})`;
    };

    // 设置背景透明度控件事件监听
    function setupBgOpacityControls() {
        const bgSelect = document.getElementById('bgSelect');
        const topSlider = document.getElementById('bgOpacityTop');
        const bottomSlider = document.getElementById('bgOpacityBottom');
        const topLabel = document.getElementById('bgOpacityTopLabel');
        const bottomLabel = document.getElementById('bgOpacityBottomLabel');

        if (!bgSelect || !topSlider || !bottomSlider || !topLabel || !bottomLabel) return;

        // 初始化滑块值
        topSlider.value = String(Number.isFinite(bgOverlayOpacityTop) ? bgOverlayOpacityTop : 0.3);
        bottomSlider.value = String(Number.isFinite(bgOverlayOpacityBottom) ? bgOverlayOpacityBottom : 0.3);

        // 初始化标签显示
        window.updateBgOpacityLabels();

        const updateDisabled = () => {
            const disabled = !bgSelect.value;
            topSlider.disabled = disabled;
            bottomSlider.disabled = disabled;
        };
        updateDisabled();

        topSlider.addEventListener('input', () => {
            bgOverlayOpacityTop = parseFloat(topSlider.value) || 0;
            try { localStorage.setItem('bgOpacityTop', String(bgOverlayOpacityTop)); } catch (_) {}
            window.updateBgOpacityLabels();
            if (bgSelect.value) {
                const themeKey = (document.getElementById('themeSelect') && document.getElementById('themeSelect').value) || 'default';
                applyBackground(bgSelect.value, themeKey);
            }
        });

        bottomSlider.addEventListener('input', () => {
            bgOverlayOpacityBottom = parseFloat(bottomSlider.value) || 0;
            try { localStorage.setItem('bgOpacityBottom', String(bgOverlayOpacityBottom)); } catch (_) {}
            window.updateBgOpacityLabels();
            if (bgSelect.value) {
                const themeKey = (document.getElementById('themeSelect') && document.getElementById('themeSelect').value) || 'default';
                applyBackground(bgSelect.value, themeKey);
            }
        });

        bgSelect.addEventListener('change', updateDisabled);
    }

    async function loadBackgroundsForTheme(themeKey, autoApplyFirst = false) {
        const list = await fetchBackgrounds(themeKey);
        const bgSelect = document.getElementById('bgSelect');
        if (bgSelect) {
            // "默认"=不加载背景
            bgSelect.innerHTML = '<option value="">默认</option>';
            list.forEach(item => {
                const opt = document.createElement('option');
                opt.value = item.url;
                // 显示背景图名称，不需要去除扩展名（数据库中存储的是完整名称）
                opt.textContent = item.name;
                bgSelect.appendChild(opt);
            });

            let savedUrl = '';
            try { savedUrl = localStorage.getItem(`selectedBgUrl_${themeKey}`) || ''; } catch (_) {}

            const topSlider = document.getElementById('bgOpacityTop');
            const bottomSlider = document.getElementById('bgOpacityBottom');
            const setDisabled = (disabled) => {
                if (topSlider) topSlider.disabled = disabled;
                if (bottomSlider) bottomSlider.disabled = disabled;
            };

            if (savedUrl && list.some(x => x.url === savedUrl)) {
                bgSelect.value = savedUrl;
                applyBackground(savedUrl, themeKey);
                setDisabled(false);
                return;
            }

            if (autoApplyFirst && list.length > 0) {
                // 仅当主题下有背景图时，才自动应用第一张
                bgSelect.value = list[0].url;
                applyBackground(list[0].url, themeKey);
                setDisabled(false);
            } else {
                // 找不到对应主题背景 → 选择"默认"（不加载背景）
                bgSelect.value = '';
                applyBackground('', themeKey);
                setDisabled(true);
            }
        }
    }
    function setupUIListeners() {
        const controls = {
            'distortion': 'uDistortion',
            'opacity': 'uOpacity',
            'skewX': null,
            'skewY': null,
            'depthThreshold': 'uDepthTh',
            'perspective': 'uPerspective'
        };

        Object.keys(controls).forEach(id => {
            const input = document.getElementById(id);
            if (input) {
                input.addEventListener('input', (e) => {
                    const value = parseFloat(e.target.value);
                    state[id] = value;
                    const label = input.previousElementSibling;
                    if (label) {
                        const key = label.getAttribute('data-i18n');
                        const currentLang = localStorage.getItem('language') || 'zh-CN';
                        const baseText = window.translations && window.translations[currentLang] && window.translations[currentLang][key] 
                            ? window.translations[currentLang][key] 
                            : label.textContent.split('(')[0].trim();
                        label.textContent = `${baseText} (${value.toFixed(3)})`;
                    }
                    
                    if (controls[id]) {
                        shaderMaterial.uniforms[controls[id]].value = value;
                    }
                    updateTransformMatrix();
                });
            }
        });

        const blendModeSelect = document.getElementById('blendMode');
        if (blendModeSelect) {
            blendModeSelect.addEventListener('change', (e) => {
                const blendModes = { 
                    'normal': 0, 'multiply': 1, 'screen': 2, 'overlay': 3,
                    'darken': 4, 'lighten': 5, 'color-dodge': 6, 'color-burn': 7,
                    'soft-light': 8, 'hard-light': 9, 'hologram': 10
                };
                state.blendMode = e.target.value;
                shaderMaterial.uniforms.uBlend.value = blendModes[e.target.value];
            });
        }

        // 图案选择事件
        if (patternListContainer) {
            patternListContainer.addEventListener('click', async (e) => {
                const item = e.target.closest('.pattern-item');
                if (!item) return;

                if (item.classList.contains('active')) {
                    item.classList.remove('active');
                    state.patternId = null;
                    activePatternItem = null;
                    updatePattern(null);
                    checkAndUpdatePreview();
                    return;
                }

                const currentActive = patternListContainer.querySelector('.pattern-item.active');
                if (currentActive) currentActive.classList.remove('active');
                item.classList.add('active');
                activePatternItem = item;
                
                const patternId = item.dataset.patternId;
                const pattern = patterns.find(p => p.id == patternId);
                if (pattern) {
                    state.patternId = patternId;
                    try {
                        const imagePath = pattern.file_path.replace(/\\/g, '/');
                        const imageURL = '/' + imagePath;
                        const texture = await createImageAndLoadTexture(imageURL, `pattern-${patternId}`);
                        if (texture) {
                            updatePattern(texture);
                            checkAndUpdatePreview();
                            centerPattern();
                            fitPattern();
                        }
                    } catch (err) {
                        console.error('加载图案错误:', err);
                    }
                }
            });
        }

        // 产品选择事件
        if (productListContainer) {
            productListContainer.addEventListener('click', async (e) => {
                const item = e.target.closest('.product-item');
                if (!item) return;

                if (item.classList.contains('active')) {
                    item.classList.remove('active');
                    state.productId = null;
                    state.depthId = null;
                    activeProductItem = null;
                    updateProduct(null, null);
                    checkAndUpdatePreview();
                    return;
                }

                const currentActive = productListContainer.querySelector('.product-item.active');
                if (currentActive) currentActive.classList.remove('active');
                item.classList.add('active');
                activeProductItem = item;

                const productId = item.dataset.productId;
                const product = products.find(p => p.id == productId);
                if (product) {
                    state.productId = productId;

                    try {
                        const productImagePath = product.product_image_path ? product.product_image_path.replace(/\\/g, '/') : '';
                        const depthImagePath = product.depth_image_path ? product.depth_image_path.replace(/\\/g, '/') : '';
                        
                        const productURL = '/uploads/products/' + productImagePath;
                        const depthURL = depthImagePath ? '/uploads/depth_maps/' + depthImagePath : null;
                        
                        const [productTex, depthTex] = await Promise.all([
                            createImageAndLoadTexture(productURL, `product-${productId}`),
                            depthURL ? createImageAndLoadTexture(depthURL, `depth-${productId}`) : Promise.resolve(null)
                        ]);
                        
                        if (productTex) {
                            updateProduct(productTex, depthTex);
                            checkAndUpdatePreview();
                        }
                    } catch (err) {
                        console.error('加载产品错误:', err);
                    }
                }
            });
        }
        
        // 分类选择事件
        const categorySelect = document.getElementById('categorySelect');
        if (categorySelect) {
            categorySelect.addEventListener('change', async (e) => {
                const selectedCategory = e.target.value;
                if (selectedCategory === 'all') {
                    const allProducts = await DataManager.loadProducts();
                    products = allProducts;
                    renderProducts(allProducts);
                } else {
                    const categoryId = parseInt(selectedCategory);
                    const filteredProducts = await DataManager.loadProducts(categoryId);
                    products = filteredProducts;
                    renderProducts(filteredProducts);
                }
            });
        }

        // 主题切换功能
        const themeSelect = document.getElementById('themeSelect');
        if (themeSelect) {
            themeSelect.addEventListener('change', async (e) => {
                const selectedTheme = e.target.value;
                const themeStylesheet = document.getElementById('themeStylesheet');
                
                if (selectedTheme === 'default') {
                    themeStylesheet.href = `/static/themes/default.css`;
                } else {
                    themeStylesheet.href = `/static/themes/${selectedTheme}.css`;
                }
                
                localStorage.setItem('selectedTheme', selectedTheme);
                // 切换主题后只尝试加载该主题前缀背景；若没有则回退"默认"（不加载）
                await loadBackgroundsForTheme(selectedTheme, true);
            });

            // 恢复主题选择
            const savedTheme = localStorage.getItem('selectedTheme');
            const themeStylesheet = document.getElementById('themeStylesheet');
            const bgSelect = document.getElementById('bgSelect');
            if (bgSelect) {
                bgSelect.addEventListener('change', () => {
                    const url = bgSelect.value;
                    applyBackground(url || '', themeSelect.value);
                });
            }
            if (savedTheme) {
                themeSelect.value = savedTheme;
                if (savedTheme === 'default') {
                    themeStylesheet.href = `/static/themes/default.css`;
                } else {
                    themeStylesheet.href = `/static/themes/${savedTheme}.css`;
                }
                loadBackgroundsForTheme(savedTheme, true);
            } else {
                themeSelect.value = 'default';
                themeStylesheet.href = `/static/themes/default.css`;
                loadBackgroundsForTheme('default', true);
            }

        }
        setupBgOpacityControls();
    }
    
    function updateTransformMatrix() {
        const { scale, skewX, skewY } = state;
        const t = shaderMaterial.uniforms.uTransform.value;
        
        t[0] = scale;   // m00 - X轴缩放
        t[1] = skewX;   // m10 - X轴倾斜
        t[2] = skewY;   // m01 - Y轴倾斜  
        t[3] = scale;   // m11 - Y轴缩放
    }

    // --- Part 6: 画布交互 ---
    function setupCanvasInteraction() {
        let isDragging = false;
        let lastMousePos = { x: 0, y: 0 };
        let touchSensitivity = 1.0;

        const isTouchDevice = () => {
            return 'ontouchstart' in window || navigator.maxTouchPoints > 0;
        };

        if (isTouchDevice()) {
            touchSensitivity = 1.5;
            canvas.style.cursor = 'grab';
        }

        const getMousePos = (e) => {
            if (!canvas) return { x: 0, y: 0 };
            const rect = canvas.getBoundingClientRect();
            return {
                x: e.clientX - rect.left,
                y: e.clientY - rect.top
            };
        };

        canvas.addEventListener('pointerdown', (e) => {
            if (e.pointerType === 'mouse' && e.button !== 0) return;
            
            e.preventDefault();
            e.stopPropagation();
            
            isDragging = true;
            lastMousePos = getMousePos(e);
            canvas.setPointerCapture(e.pointerId);
            
            if (isTouchDevice()) {
                canvas.style.cursor = 'grabbing';
            }
        });

        canvas.addEventListener('pointermove', (e) => {
            if (!isDragging) return;
            
            e.preventDefault();
            e.stopPropagation();
            
            const pos = getMousePos(e);
            const dx = (pos.x - lastMousePos.x) * touchSensitivity;
            const dy = (pos.y - lastMousePos.y) * touchSensitivity;
            
            const minMovement = isTouchDevice() ? 0.5 : 0.1;
            if (Math.abs(dx) > minMovement || Math.abs(dy) > minMovement) {
                state.tx += dx;
                state.ty -= dy;
                lastMousePos = pos;
            }
        });

        const onPointerUp = (e) => {
            if (isDragging) {
                isDragging = false;
                canvas.releasePointerCapture(e.pointerId);
                
                if (isTouchDevice()) {
                    canvas.style.cursor = 'grab';
                }
            }
        };
        
        canvas.addEventListener('pointerup', onPointerUp);
        canvas.addEventListener('pointercancel', onPointerUp);
        canvas.addEventListener('pointerleave', onPointerUp);

        canvasContainer.addEventListener('wheel', (e) => {
            e.preventDefault();
            const factor = Math.exp(-e.deltaY * 0.001);
            const newScale = Math.max(0.01, Math.min(10, state.scale * factor));
            
            const rect = canvas.getBoundingClientRect();
            const mouseX = e.clientX - rect.left;
            const mouseY = e.clientY - rect.top;
            
            const canvasCenterX = rect.width * 0.5;
            const canvasCenterY = rect.height * 0.5;
            const mouseCenteredX = mouseX - canvasCenterX;
            const mouseCenteredY = mouseY - canvasCenterY;

            const scaleRatio = newScale / state.scale;
            state.tx = mouseCenteredX - (mouseCenteredX - state.tx) * scaleRatio;
            state.ty = -mouseCenteredY - (-mouseCenteredY - state.ty) * scaleRatio;
            state.scale = newScale;
            
            updateTransformMatrix();
        }, { passive: false });

        // 防止页面滚动
        canvasContainer.addEventListener('touchstart', (e) => {
            e.preventDefault();
            e.stopPropagation();
        }, { passive: false });

        canvasContainer.addEventListener('touchmove', (e) => {
            e.preventDefault();
            e.stopPropagation();
        }, { passive: false });

        canvasContainer.addEventListener('touchend', (e) => {
            e.preventDefault();
            e.stopPropagation();
        }, { passive: false });
    }

    // --- Part 7: 操作按钮 ---
    function setupActions() {
        const exportBtn = document.getElementById('exportBtn');
        if (exportBtn) {
            exportBtn.addEventListener('click', () => {
                const a = document.createElement('a');
                a.href = renderer.domElement.toDataURL('image/png');
                a.download = 'stamp_pattern_export.png';
                a.click();
                URL.revokeObjectURL(a.href);
            });
        }
        
        const resetBtn = document.getElementById('resetBtn');
        if (resetBtn) {
            resetBtn.addEventListener('click', () => {
                // 重置状态
                state.tx = 0; state.ty = 0; state.scale = 1;
                state.distortion = 0.3; state.opacity = 1.0; state.skewX = 0.0; state.skewY = 0.0;
                state.blendMode = 'normal'; state.depthThreshold = 0.7; state.perspective = 0.0;
                
                // 重置UI
                const distortionInput = document.getElementById('distortion');
                const opacityInput = document.getElementById('opacity');
                const skewXInput = document.getElementById('skewX');
                const skewYInput = document.getElementById('skewY');
                const blendModeSelect = document.getElementById('blendMode');
                const depthThresholdInput = document.getElementById('depthThreshold');
                const perspectiveInput = document.getElementById('perspective');
                
                if (distortionInput) distortionInput.value = 0.3;
                if (opacityInput) opacityInput.value = 1.0;
                if (skewXInput) skewXInput.value = 0.0;
                if (skewYInput) skewYInput.value = 0.0;
                if (blendModeSelect) blendModeSelect.value = 'normal';
                if (depthThresholdInput) depthThresholdInput.value = 0.7;
                if (perspectiveInput) perspectiveInput.value = 0.0;
                
                // 触发输入事件以更新标签和uniforms
                document.querySelectorAll('.control-panel input, .control-panel select').forEach(el => {
                    if (el.dispatchEvent) {
                        el.dispatchEvent(new Event('input'));
                    }
                });
                
                fitPattern();
            });
        }
    }
    
    function centerPattern() {
        // 将图案定位到画布的绝对中心
        // 在着色器坐标系统中，(0,0)对应画布中心
        state.tx = 0;
        state.ty = 0;
    }
    
    function fitPattern() {
        const { uCanvasSize, uPatternSize } = shaderMaterial.uniforms;
        
        if (!uPatternSize.value || !uCanvasSize.value) return;
        
        // 计算合适的缩放比例，让图案在画布中显示合适的大小
        const canvasSize = Math.min(uCanvasSize.value.x, uCanvasSize.value.y);
        const patternSize = Math.max(uPatternSize.value.x, uPatternSize.value.y);
        
        // 设置图案大小为画布的1/3，这样既不会太大也不会太小
        state.scale = (canvasSize / 3) / patternSize;
        
        // 将图案居中到画布中心（对应产品图中心）
        state.tx = 0;
        state.ty = 0;
        
        updateTransformMatrix();
    }

    // --- Part 8: 数据加载和UI渲染 ---
    async function loadAllData() {
        try {
            // 并行加载所有数据
            const [patternsData, categoriesData] = await Promise.all([
                DataManager.loadPatterns(),
                DataManager.loadCategories()
            ]);
            
            patterns = patternsData;
            categories = categoriesData;
            
            // 渲染UI
            renderPatterns(patterns);
            renderCategories(categories);
            
            // 加载默认分类的产品
            if (categories.length > 0) {
                const defaultCategory = categories.find(c => c.is_default) || categories[0];
                const productsData = await DataManager.loadProducts(defaultCategory.id);
                products = productsData;
                renderProducts(products);
            } else {
                const productsData = await DataManager.loadProducts();
                products = productsData;
                renderProducts(products);
            }
            
            console.log('所有数据加载完成');
            
        } catch (error) {
            console.error('数据加载失败:', error);
        }
    }

    // 渲染印花图案网格
    function renderPatterns(patternsData) {
        if (!patternListContainer) return;
        
        patternListContainer.innerHTML = '';
        
        patternsData.forEach(pattern => {
            const item = document.createElement('div');
            item.className = 'pattern-item p-2 bg-gray-700 rounded-md';
            item.dataset.patternId = pattern.id;
            
            // 确保图片路径正确
            const imagePath = pattern.file_path.replace(/\\/g, '/');
            
            item.innerHTML = `
                <img src="/${imagePath}" class="w-full rounded" alt="${pattern.name}" 
                     onerror="this.style.display='none'; this.nextElementSibling.style.display='block';">
                <div style="display:none; padding:10px; text-align:center; color:#666; font-size:10px;">
                    图片加载失败<br>${pattern.name}
                </div>
                <p class="text-sm mt-1 text-center">${pattern.name}</p>
            `;
            
            patternListContainer.appendChild(item);
        });
    }
    
    // 渲染产品网格
    function renderProducts(productsData) {
        if (!productListContainer) return;
        
        productListContainer.innerHTML = '';
        
        if (!productsData || productsData.length === 0) {
            productListContainer.innerHTML = '<div class="text-center text-gray-400 p-4">暂无产品数据</div>';
            return;
        }
        
        productsData.forEach(product => {
            const item = document.createElement('div');
            item.className = 'product-item p-2 bg-gray-700 rounded-md mb-2';
            item.dataset.productId = product.id;
            
            // 使用正确的字段名：product_image_path 和 title
            const imagePath = product.product_image_path ? product.product_image_path.replace(/\\/g, '/') : '';
            
            item.innerHTML = `
                <img src="/uploads/products/${imagePath}" class="w-full rounded" alt="${product.title}"
                     onerror="this.style.display='none'; this.nextElementSibling.style.display='block';">
                <div style="display:none; padding:10px; text-align:center; color:#666; font-size:10px;">
                    图片加载失败<br>${product.title}
                </div>
                <p class="text-sm mt-1 text-center">${product.title}</p>
            `;
            
            productListContainer.appendChild(item);
        });
    }
    
    // 渲染分类选择器
    function renderCategories(categoriesData) {
        const categorySelect = document.getElementById('categorySelect');
        if (!categorySelect) return;
        
        // 保留"全部产品"选项
        categorySelect.innerHTML = '<option value="all">全部产品</option>';
        
        categoriesData.forEach(category => {
            const option = document.createElement('option');
            option.value = category.id;
            option.textContent = category.name;
            if (category.is_default) {
                option.selected = true;
            }
            categorySelect.appendChild(option);
        });
    }

    // --- Part 9: 渲染循环 ---
    function animate() {
        requestAnimationFrame(animate);
        
        const unis = shaderMaterial.uniforms;
        
        // 如果没有产品图，清空画布
        if (!unis.uProduct.value || !unis.uDepth.value) {
            renderer.clear();
            return;
        }
        
        // 如果有产品图但没有贴图，创建透明贴图来只显示产品图
        if (!unis.uPattern.value) {
            // 创建一个透明的1x1贴图作为占位符
            if (!shaderMaterial.transparentTexture) {
                const canvas = document.createElement('canvas');
                canvas.width = canvas.height = 1;
                const ctx = canvas.getContext('2d');
                ctx.clearRect(0, 0, 1, 1);
                shaderMaterial.transparentTexture = new THREE.CanvasTexture(canvas);
                shaderMaterial.transparentTexture.flipY = true;
            }
            unis.uPattern.value = shaderMaterial.transparentTexture;
            unis.uPatSize.value.set(1, 1);
            unis.uPatternSize.value.set(1, 1);
        }
        
        // 更新每帧变化的uniforms
        shaderMaterial.uniforms.uTranslate.value.set(state.tx, state.ty);
        updateTransformMatrix();
        
        renderer.render(scene, camera);
    }
});
