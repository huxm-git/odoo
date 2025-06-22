# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import json
import re
from datetime import datetime, timedelta


class AIAssistant(models.Model):
    _name = 'ai.assistant'
    _description = 'AI 助手'
    _order = 'create_date desc'
    
    name = fields.Char('会话名称', default='AI助手会话')
    question = fields.Text('问题', required=True)
    answer = fields.Text('回答', readonly=True)
    
    category = fields.Selection([
        ('inventory', '库存查询'),
        ('production', '生产管理'),
        ('order', '订单管理'),
        ('general', '一般问题'),
        ('help', '帮助信息'),
    ], string='分类', default='general')
    
    user_id = fields.Many2one('res.users', '用户', default=lambda self: self.env.user)
    session_id = fields.Char('会话ID', default=lambda self: self._generate_session_id())
    
    # 对话状态
    is_resolved = fields.Boolean('已解决', default=False)
    confidence_score = fields.Float('置信度', default=0.8)
    
    def _generate_session_id(self):
        """生成会话ID"""
        return f"session_{self.env.user.id}_{int(datetime.now().timestamp())}"
    
    @api.model
    def chat(self, message, session_id=None):
        """模拟AI对话"""
        if not message:
            return {'error': '请输入问题'}
        
        # 分析问题类别
        category = self._analyze_question_category(message)
        
        # 生成回答
        answer = self._generate_answer(message, category)
        
        # 创建对话记录
        chat_record = self.create({
            'question': message,
            'answer': answer['content'],
            'category': category,
            'session_id': session_id or self._generate_session_id(),
            'confidence_score': answer.get('confidence', 0.8),
        })
        
        return {
            'id': chat_record.id,
            'question': message,
            'answer': answer['content'],
            'category': category,
            'confidence': answer.get('confidence', 0.8),
            'suggestions': answer.get('suggestions', []),
        }
    
    def _analyze_question_category(self, message):
        """分析问题类别"""
        message_lower = message.lower()
        
        # 库存相关关键词
        inventory_keywords = ['库存', '存货', '现货', '缺货', '补货', '盘点', '入库', '出库']
        # 生产相关关键词
        production_keywords = ['生产', '制造', '工单', '排产', '工时', '生产线', '产能']
        # 订单相关关键词
        order_keywords = ['订单', '销售', '采购', '客户', '供应商', '交期']
        # 帮助相关关键词
        help_keywords = ['帮助', '怎么', '如何', '操作', '使用', '功能']
        
        if any(keyword in message_lower for keyword in inventory_keywords):
            return 'inventory'
        elif any(keyword in message_lower for keyword in production_keywords):
            return 'production'
        elif any(keyword in message_lower for keyword in order_keywords):
            return 'order'
        elif any(keyword in message_lower for keyword in help_keywords):
            return 'help'
        else:
            return 'general'
    
    def _generate_answer(self, message, category):
        """生成回答"""
        message_lower = message.lower()
        
        if category == 'inventory':
            return self._handle_inventory_question(message_lower)
        elif category == 'production':
            return self._handle_production_question(message_lower)
        elif category == 'order':
            return self._handle_order_question(message_lower)
        elif category == 'help':
            return self._handle_help_question(message_lower)
        else:
            return self._handle_general_question(message_lower)
    
    def _handle_inventory_question(self, message):
        """处理库存相关问题"""
        try:
            # 获取库存数据
            products = self.env['product.template'].search([('type', '=', 'product')], limit=10)
            
            if '库存' in message or '现货' in message:
                stock_info = []
                for product in products:
                    stock_info.append(f"• {product.name}: {product.qty_available} {product.uom_id.name}")
                
                content = f"📦 当前库存情况：\n" + "\n".join(stock_info[:5])
                if len(products) > 5:
                    content += f"\n... 还有 {len(products) - 5} 个产品"
                
                return {
                    'content': content,
                    'confidence': 0.9,
                    'suggestions': ['查看库存预警', '生成库存报表', '创建补货单']
                }
            
            elif '缺货' in message or '不足' in message:
                low_stock_products = products.filtered(lambda p: hasattr(p, 'min_stock_level') and p.qty_available <= p.min_stock_level)
                
                if low_stock_products:
                    content = "⚠️ 以下产品库存不足：\n"
                    for product in low_stock_products[:5]:
                        content += f"• {product.name}: 当前 {product.qty_available}，最低 {getattr(product, 'min_stock_level', 0)}\n"
                else:
                    content = "✅ 目前所有产品库存充足"
                
                return {
                    'content': content,
                    'confidence': 0.85,
                    'suggestions': ['创建采购单', '调整安全库存', '查看供应商信息']
                }
            
        except Exception as e:
            pass
        
        return {
            'content': "📦 库存管理功能：\n• 实时库存查询\n• 库存预警提醒\n• 快速入库出库\n• 库存盘点功能\n\n您可以问我具体的库存问题，比如'某个产品的库存'或'哪些产品缺货'。",
            'confidence': 0.7,
            'suggestions': ['查看所有库存', '库存预警设置', '扫码入库']
        }
    
    def _handle_production_question(self, message):
        """处理生产相关问题"""
        try:
            # 获取生产数据
            productions = self.env['mrp.production'].search([('state', 'in', ['confirmed', 'progress'])], limit=5)
            
            if '生产' in message and ('计划' in message or '排产' in message):
                if productions:
                    content = "🏭 当前生产计划：\n"
                    for prod in productions:
                        line_name = dict(prod._fields['production_line'].selection).get(prod.production_line, '未知')
                        content += f"• {prod.name}: {prod.product_id.name} x{prod.product_qty} - {line_name}\n"
                else:
                    content = "📋 当前没有进行中的生产订单"
                
                return {
                    'content': content,
                    'confidence': 0.9,
                    'suggestions': ['创建生产订单', '查看生产看板', '分配工人']
                }
            
            elif '工时' in message or '效率' in message:
                content = "⏱️ 生产工时统计：\n"
                total_estimated = sum(productions.mapped('estimated_hours'))
                content += f"• 预计总工时: {total_estimated:.1f} 小时\n"
                content += f"• 平均每单工时: {total_estimated/len(productions):.1f} 小时\n" if productions else "• 暂无生产数据\n"
                
                return {
                    'content': content,
                    'confidence': 0.8,
                    'suggestions': ['查看详细工时', '生产效率分析', '工人排班']
                }
            
        except Exception as e:
            pass
        
        return {
            'content': "🏭 生产管理功能：\n• 生产订单管理\n• 生产排班看板\n• 工时统计分析\n• 生产进度跟踪\n\n您可以问我'今日生产计划'、'生产效率'等问题。",
            'confidence': 0.7,
            'suggestions': ['查看生产看板', '创建生产订单', '工时统计']
        }
    
    def _handle_order_question(self, message):
        """处理订单相关问题"""
        try:
            # 获取订单数据
            sale_orders = self.env['sale.order'].search([('state', 'in', ['draft', 'sent', 'sale'])], limit=5)
            
            if '订单' in message:
                if sale_orders:
                    content = "📋 当前订单情况：\n"
                    for order in sale_orders:
                        status_name = dict(order._fields['state'].selection).get(order.state, order.state)
                        content += f"• {order.name}: {order.partner_id.name} - {status_name}\n"
                else:
                    content = "📋 当前没有待处理的销售订单"
                
                return {
                    'content': content,
                    'confidence': 0.9,
                    'suggestions': ['创建销售订单', '查看订单详情', '订单发货']
                }
            
        except Exception as e:
            pass
        
        return {
            'content': "📋 订单管理功能：\n• 销售订单管理\n• 采购订单管理\n• 订单状态跟踪\n• 客户管理\n\n您可以问我'待处理订单'、'今日发货'等问题。",
            'confidence': 0.7,
            'suggestions': ['查看所有订单', '创建新订单', '订单统计']
        }
    
    def _handle_help_question(self, message):
        """处理帮助相关问题"""
        return {
            'content': "🤖 我是您的ERP智能助手，可以帮您：\n\n📦 库存管理\n• 查询产品库存\n• 库存预警提醒\n• 扫码入库出库\n\n🏭 生产管理\n• 生产计划查询\n• 工时统计分析\n• 生产进度跟踪\n\n📋 订单管理\n• 订单状态查询\n• 客户信息管理\n• 发货跟踪\n\n💡 使用技巧：\n• 直接问我'库存情况'、'生产计划'等\n• 点击下方快捷按钮快速查询\n• 支持中文自然语言交流",
            'confidence': 1.0,
            'suggestions': ['库存查询', '生产计划', '订单状态', '系统功能']
        }
    
    def _handle_general_question(self, message):
        """处理一般问题"""
        # 简单的关键词匹配
        responses = {
            '你好': '您好！我是您的ERP智能助手，很高兴为您服务！有什么可以帮助您的吗？',
            '谢谢': '不客气！如果还有其他问题，随时可以问我。',
            '再见': '再见！祝您工作愉快！',
            '时间': f'现在时间是 {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
        }
        
        for keyword, response in responses.items():
            if keyword in message:
                return {
                    'content': response,
                    'confidence': 0.9,
                    'suggestions': ['库存查询', '生产管理', '订单管理']
                }
        
        return {
            'content': '抱歉，我还在学习中。请尝试询问库存、生产、订单相关问题，或者点击下方的快捷查询按钮。\n\n💡 您可以这样问我：\n• \'当前库存情况如何？\'\n• \'今天有哪些生产计划？\'\n• \'待处理的订单有哪些？\'',
            'confidence': 0.3,
            'suggestions': ['库存查询', '生产计划', '订单管理', '使用帮助']
        }
    
    @api.model
    def get_quick_queries(self):
        """获取快捷查询"""
        return [
            {'label': '📦 查看库存状态', 'query': '当前库存情况'},
            {'label': '🏭 今日生产计划', 'query': '今天的生产计划'},
            {'label': '📋 订单处理情况', 'query': '待处理订单'},
            {'label': '⚠️ 库存预警', 'query': '哪些产品缺货'},
            {'label': '⏱️ 生产工时统计', 'query': '生产工时情况'},
            {'label': '❓ 使用帮助', 'query': '如何使用系统'},
        ]
    
    def action_ask_question(self):
        """处理用户提问"""
        self.ensure_one()
        if not self.question:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('提示'),
                    'message': _('请先输入问题'),
                    'type': 'warning',
                }
            }

        # 调用chat方法生成回答
        result = self.chat(self.question)

        if 'error' in result:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('错误'),
                    'message': result['error'],
                    'type': 'danger',
                }
            }

        # 更新当前记录的回答
        self.answer = result['answer']
        self.category = result['category']
        self.confidence_score = result['confidence']

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('AI回答'),
                'message': _('已生成回答，请查看下方内容'),
                'type': 'success',
            }
        }

    def action_quick_query(self):
        """快捷查询"""
        self.ensure_one()
        query = self.env.context.get('query', '')

        if not query:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('错误'),
                    'message': _('查询内容为空'),
                    'type': 'warning',
                }
            }

        # 设置问题并生成回答
        self.question = query
        result = self.chat(query)

        if 'error' not in result:
            self.answer = result['answer']
            self.category = result['category']
            self.confidence_score = result['confidence']

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('查询完成'),
                'message': _('已生成回答'),
                'type': 'success',
            }
        }

    def action_clear_chat(self):
        """清空对话"""
        self.ensure_one()
        self.question = ''
        self.answer = ''
        self.category = ''
        self.confidence_score = 0.0

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('已清空'),
                'message': _('对话内容已清空'),
                'type': 'info',
            }
        }

    def action_mark_resolved(self):
        """标记为已解决"""
        self.ensure_one()
        self.is_resolved = True

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('已标记'),
                'message': _('问题已标记为已解决'),
                'type': 'success',
            }
        }
