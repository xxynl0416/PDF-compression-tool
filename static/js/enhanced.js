/**
 * PDF 压缩工具 - 增强功能
 * - WebSocket 实时推送
 * - 压缩预设
 * - 高级选项
 */

// ==================== WebSocket 连接管理 ====================
class WebSocketManager {
    constructor() {
        this.socket = null;
        this.isConnected = false;
        this.currentTaskId = null;
        this.callbacks = {
            progress: [],
            completed: [],
            failed: [],
            connected: [],
            disconnected: []
        };
    }

    connect() {
        this.socket = io({ reconnection: true, reconnectionDelay: 1000, reconnectionAttempts: 10 });

        this.socket.on('connect', () => {
            this.isConnected = true;
            this.updateConnectionStatus(true);
            this.callbacks.connected.forEach(cb => cb());
            // Rejoin task room after reconnection
            if (this.currentTaskId) {
                this.socket.emit('join_task', { task_id: this.currentTaskId });
            }
        });

        this.socket.on('disconnect', () => {
            this.isConnected = false;
            this.updateConnectionStatus(false);
            this.callbacks.disconnected.forEach(cb => cb());
        });

        this.socket.on('task_update', (data) => {
            this.handleTaskUpdate(data);
        });
    }

    joinTask(taskId) {
        this.currentTaskId = taskId;
        if (this.isConnected) {
            this.socket.emit('join_task', { task_id: taskId });
        }
    }

    leaveTask(taskId) {
        if (this.isConnected) {
            this.socket.emit('leave_task', { task_id: taskId });
        }
        this.currentTaskId = null;
    }

    handleTaskUpdate(data) {
        if (data.progress !== undefined) {
            this.callbacks.progress.forEach(cb => cb(data));
        }

        if (data.status === 'completed') {
            this.callbacks.completed.forEach(cb => cb(data.result));
        } else if (data.status === 'failed') {
            this.callbacks.failed.forEach(cb => cb(data.message));
        }
    }

    updateConnectionStatus(connected) {
        const statusEl = document.getElementById('connectionStatus');
        const statusText = document.getElementById('statusText');

        if (statusEl && statusText) {
            statusEl.className = `connection-status ${connected ? 'connected' : 'disconnected'}`;
            statusText.textContent = connected ? '已连接' : '连接中...';
        }
    }

    on(event, callback) {
        if (this.callbacks[event]) {
            this.callbacks[event].push(callback);
        }
    }
}

// ==================== 压缩预设 ====================
const CompressionPresets = {
    aggressive: {
        name: '🔥 激进压缩',
        description: '最小体积 · 适合网络传输',
        target_size: 100,
        quality: 50,
        force_compress: true
    },
    balanced: {
        name: '⚖️ 平衡模式',
        description: '推荐 · 质量与体积平衡',
        target_size: 200,
        quality: 70,
        force_compress: true
    },
    conservative: {
        name: '💎 保守压缩',
        description: '最高质量 · 适合打印',
        target_size: 300,
        quality: 90,
        force_compress: false
    }
};

class PresetManager {
    constructor() {
        this.currentPreset = 'balanced';
        this.buttons = document.querySelectorAll('.preset-btn');
        this.targetSizeInput = document.getElementById('targetSize');
        this.qualityInput = document.getElementById('quality');
        this.forceCompressInput = document.getElementById('forceCompress');
        
        this.init();
    }

    init() {
        this.buttons.forEach(btn => {
            btn.addEventListener('click', () => {
                const preset = btn.dataset.preset;
                this.selectPreset(preset);
            });
        });

        // 监听手动修改，取消预设高亮
        [this.targetSizeInput, this.qualityInput].forEach(input => {
            input.addEventListener('input', () => {
                this.clearActive();
            });
        });

        // 初始化默认预设
        this.selectPreset('balanced');
    }

    selectPreset(presetName) {
        const preset = CompressionPresets[presetName];
        if (!preset) return;

        this.currentPreset = presetName;

        // 更新 UI
        this.clearActive();
        const activeBtn = document.querySelector(`[data-preset="${presetName}"]`);
        if (activeBtn) activeBtn.classList.add('active');

        // 应用设置
        this.targetSizeInput.value = preset.target_size;
        document.getElementById('targetSizeValue').textContent = `${preset.target_size} MB`;
        
        this.qualityInput.value = preset.quality;
        document.getElementById('qualityValue').textContent = `${preset.quality}%`;
        
        this.forceCompressInput.checked = preset.force_compress;
    }

    clearActive() {
        this.buttons.forEach(btn => btn.classList.remove('active'));
    }

    getCurrentSettings() {
        return {
            target_size: parseInt(this.targetSizeInput.value),
            quality: parseInt(this.qualityInput.value),
            force_compress: this.forceCompressInput.checked
        };
    }
}

// ==================== 初始化 ====================
document.addEventListener('DOMContentLoaded', () => {
    // 初始化 WebSocket
    const wsManager = new WebSocketManager();
    wsManager.connect();
    window.wsManager = wsManager;

    // 初始化预设管理器
    const presetManager = new PresetManager();
    window.presetManager = presetManager;

    // 将 wsManager 和 presetManager 暴露到全局
    console.log('✅ PDF 压缩工具增强功能已加载');
});
