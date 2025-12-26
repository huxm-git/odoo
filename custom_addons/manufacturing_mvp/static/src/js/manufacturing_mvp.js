/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState } from "@odoo/owl";

// AI助手聊天组件
class AIAssistantChat extends Component {
    setup() {
        this.state = useState({
            question: '',
            answer: '您好！我是您的ERP智能助手。请输入问题或点击快捷查询按钮。',
            isLoading: false,
            chatHistory: []
        });
    }

    async submitQuestion() {
        if (!this.state.question.trim()) {
            this.showNotification('请输入问题', 'warning');
            return;
        }

        this.state.isLoading = true;
        this.state.answer = '🤖 正在思考中...';

        try {
            const result = await this.env.services.rpc({
                model: 'ai.assistant',
                method: 'chat',
                args: [this.state.question],
            });

            if (result.error) {
                this.state.answer = '❌ ' + result.error;
            } else {
                this.state.answer = result.answer;
                this.state.chatHistory.push({
                    question: this.state.question,
                    answer: result.answer,
                    timestamp: new Date().toLocaleString()
                });
                this.state.question = '';
            }
        } catch (error) {
            this.state.answer = '❌ 抱歉，出现了错误：' + error.message;
        } finally {
            this.state.isLoading = false;
        }
    }

    setQuickQuery(query) {
        this.state.question = query;
        this.submitQuestion();
    }

    showNotification(message, type = 'info') {
        this.env.services.notification.add(message, { type });
    }
}

AIAssistantChat.template = "manufacturing_mvp.AIAssistantChat";

// 扫码操作组件
class ScanOperation extends Component {
    setup() {
        this.state = useState({
            barcode: '',
            product: null,
            quantity: 1,
            scanResult: '',
            isScanning: false
        });
    }

    async scanProduct() {
        if (!this.state.barcode.trim()) {
            this.showNotification('请输入条码', 'warning');
            return;
        }

        this.state.isScanning = true;

        try {
            const result = await this.env.services.rpc({
                model: 'product.template',
                method: 'simulate_barcode_scan',
                args: [this.state.barcode],
            });

            if (result.success) {
                this.state.product = result;
                this.state.scanResult = result.message;
                this.showNotification('扫码成功', 'success');
            } else {
                this.state.product = null;
                this.state.scanResult = result.message;
                this.showNotification('扫码失败', 'danger');
            }
        } catch (error) {
            this.state.scanResult = '扫码出错：' + error.message;
            this.showNotification('扫码出错', 'danger');
        } finally {
            this.state.isScanning = false;
        }
    }

    clearScan() {
        this.state.barcode = '';
        this.state.product = null;
        this.state.quantity = 1;
        this.state.scanResult = '';
    }

    showNotification(message, type = 'info') {
        this.env.services.notification.add(message, { type });
    }
}

ScanOperation.template = "manufacturing_mvp.ScanOperation";

// 生产看板组件
class ProductionBoard extends Component {
    setup() {
        this.state = useState({
            productions: [],
            selectedLine: 'all',
            isLoading: false
        });
        this.loadProductions();
    }

    async loadProductions() {
        this.state.isLoading = true;
        try {
            const productions = await this.env.services.rpc({
                model: 'mrp.production',
                method: 'search_read',
                args: [[['state', 'in', ['confirmed', 'progress', 'to_close']]]],
                kwargs: {
                    fields: ['name', 'product_id', 'product_qty', 'production_line', 
                            'production_stage', 'priority_level', 'scheduled_workers', 'actual_workers']
                }
            });
            this.state.productions = productions;
        } catch (error) {
            this.showNotification('加载生产数据失败', 'danger');
        } finally {
            this.state.isLoading = false;
        }
    }

    get filteredProductions() {
        if (this.state.selectedLine === 'all') {
            return this.state.productions;
        }
        return this.state.productions.filter(p => p.production_line === this.state.selectedLine);
    }

    async updateProductionStage(productionId, stage) {
        try {
            await this.env.services.rpc({
                model: 'mrp.production',
                method: 'write',
                args: [[productionId], { production_stage: stage }],
            });
            this.loadProductions();
            this.showNotification('状态更新成功', 'success');
        } catch (error) {
            this.showNotification('状态更新失败', 'danger');
        }
    }

    showNotification(message, type = 'info') {
        this.env.services.notification.add(message, { type });
    }
}

ProductionBoard.template = "manufacturing_mvp.ProductionBoard";

// 库存概览组件
class InventoryOverview extends Component {
    setup() {
        this.state = useState({
            stats: {
                totalProducts: 0,
                inStock: 0,
                lowStock: 0,
                outOfStock: 0
            },
            isLoading: false
        });
        this.loadStats();
    }

    async loadStats() {
        this.state.isLoading = true;
        try {
            const products = await this.env.services.rpc({
                model: 'product.template',
                method: 'search_read',
                args: [[['type', '=', 'product']]],
                kwargs: {
                    fields: ['stock_status']
                }
            });

            const stats = {
                totalProducts: products.length,
                inStock: products.filter(p => p.stock_status === 'in_stock').length,
                lowStock: products.filter(p => p.stock_status === 'low_stock').length,
                outOfStock: products.filter(p => p.stock_status === 'out_of_stock').length
            };

            this.state.stats = stats;
        } catch (error) {
            this.showNotification('加载库存统计失败', 'danger');
        } finally {
            this.state.isLoading = false;
        }
    }

    showNotification(message, type = 'info') {
        this.env.services.notification.add(message, { type });
    }
}

InventoryOverview.template = "manufacturing_mvp.InventoryOverview";

// 注册组件
registry.category("public_components").add("AIAssistantChat", AIAssistantChat);
registry.category("public_components").add("ScanOperation", ScanOperation);
registry.category("public_components").add("ProductionBoard", ProductionBoard);
registry.category("public_components").add("InventoryOverview", InventoryOverview);

// 工具函数
export const ManufacturingMVPUtils = {
    // 格式化数字
    formatNumber(num, decimals = 2) {
        return Number(num).toFixed(decimals);
    },

    // 格式化日期
    formatDate(date) {
        return new Date(date).toLocaleDateString('zh-CN');
    },

    // 格式化时间
    formatDateTime(datetime) {
        return new Date(datetime).toLocaleString('zh-CN');
    },

    // 获取库存状态颜色
    getStockStatusColor(status) {
        const colors = {
            'in_stock': 'success',
            'low_stock': 'warning',
            'out_of_stock': 'danger'
        };
        return colors[status] || 'secondary';
    },

    // 获取优先级颜色
    getPriorityColor(priority) {
        const colors = {
            '0': 'secondary',
            '1': 'warning',
            '2': 'danger'
        };
        return colors[priority] || 'secondary';
    },

    // 获取生产阶段颜色
    getProductionStageColor(stage) {
        const colors = {
            'planning': 'secondary',
            'material_ready': 'info',
            'in_production': 'primary',
            'quality_check': 'warning',
            'completed': 'success',
            'on_hold': 'danger'
        };
        return colors[stage] || 'secondary';
    }
};

// 全局可用的工具函数
window.ManufacturingMVPUtils = ManufacturingMVPUtils;
