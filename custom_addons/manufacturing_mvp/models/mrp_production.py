# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class MrpProduction(models.Model):
    _inherit = 'mrp.production'
    
    # 生产线字段
    production_line = fields.Selection([
        ('line_a', '生产线A'),
        ('line_b', '生产线B'),
        ('line_c', '生产线C'),
        ('line_d', '生产线D'),
    ], string='生产线', default='line_a', required=True)
    
    # 计划工人数
    scheduled_workers = fields.Integer(
        '计划工人数', 
        default=2,
        help="计划安排的工人数量"
    )
    
    # 实际工人数
    actual_workers = fields.Integer(
        '实际工人数',
        help="实际参与生产的工人数量"
    )
    
    # 预计工时
    estimated_hours = fields.Float(
        '预计工时', 
        compute='_compute_estimated_hours',
        store=True,
        help="根据产品数量和生产时间计算的预计工时"
    )
    
    # 实际工时
    actual_hours = fields.Float(
        '实际工时',
        help="实际消耗的工时"
    )
    
    # 生产效率
    production_efficiency = fields.Float(
        '生产效率(%)',
        compute='_compute_production_efficiency',
        store=True,
        help="实际工时与预计工时的比率"
    )
    
    # 优先级
    priority_level = fields.Selection([
        ('0', '正常'),
        ('1', '紧急'),
        ('2', '非常紧急'),
    ], string='优先级', default='0')
    
    # 生产状态扩展
    production_stage = fields.Selection([
        ('planning', '计划中'),
        ('material_ready', '物料就绪'),
        ('in_production', '生产中'),
        ('quality_check', '质检中'),
        ('completed', '已完成'),
        ('on_hold', '暂停'),
    ], string='生产阶段', default='planning')
    
    # 备注信息
    production_notes = fields.Text('生产备注')
    
    # 质量检查
    quality_check_required = fields.Boolean('需要质检', default=True)
    quality_check_passed = fields.Boolean('质检通过')
    quality_notes = fields.Text('质检备注')
    
    @api.depends('product_qty', 'product_id.production_time')
    def _compute_estimated_hours(self):
        """计算预计工时"""
        for production in self:
            if production.product_id and hasattr(production.product_id, 'production_time'):
                production.estimated_hours = production.product_qty * production.product_id.production_time
            else:
                production.estimated_hours = production.product_qty * 1.0  # 默认1小时/件
    
    @api.depends('estimated_hours', 'actual_hours')
    def _compute_production_efficiency(self):
        """计算生产效率"""
        for production in self:
            if production.estimated_hours and production.actual_hours:
                production.production_efficiency = (production.estimated_hours / production.actual_hours) * 100
            else:
                production.production_efficiency = 0
    
    def action_show_schedule_board(self):
        """显示生产排班看板"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('生产排班看板'),
            'res_model': 'mrp.production',
            'view_mode': 'kanban,tree,form',
            'domain': [('state', 'in', ['confirmed', 'progress', 'to_close'])],
            'context': {
                'group_by': 'production_line',
                'search_default_group_by_production_line': 1,
            }
        }
    
    def action_assign_workers(self):
        """分配工人"""
        self.ensure_one()
        
        if not self.scheduled_workers:
            raise UserError(_('请先设置计划工人数'))
        
        # 这里可以扩展为实际的工人分配逻辑
        self.actual_workers = self.scheduled_workers
        self.production_stage = 'material_ready'
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('工人分配'),
                'message': _('已分配 %d 名工人到生产线 %s') % (
                    self.actual_workers, 
                    dict(self._fields['production_line'].selection)[self.production_line]
                ),
                'type': 'success',
            }
        }
    
    def action_start_production(self):
        """开始生产"""
        self.ensure_one()

        if self.state != 'confirmed':
            raise UserError(_('只有已确认的生产订单才能开始生产'))

        if not self.actual_workers:
            raise UserError(_('请先分配工人'))

        # 更新生产阶段
        self.production_stage = 'in_production'

        # 如果有可用的开始生产方法，调用它
        if hasattr(super(), 'action_confirm'):
            super().action_confirm()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('生产开始'),
                'message': _('生产订单 %s 已开始生产') % self.name,
                'type': 'success',
            }
        }
    
    def action_complete_production(self):
        """完成生产"""
        self.ensure_one()
        
        if self.quality_check_required and not self.quality_check_passed:
            raise UserError(_('需要先通过质量检查才能完成生产'))
        
        # 更新生产阶段
        self.production_stage = 'completed'
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('生产完成'),
                'message': _('生产订单 %s 已完成') % self.name,
                'type': 'success',
            }
        }
    
    def action_quality_check(self):
        """质量检查"""
        self.ensure_one()
        
        if self.production_stage != 'in_production':
            raise UserError(_('只有正在生产的订单才能进行质量检查'))
        
        # 简化的质量检查逻辑
        self.quality_check_passed = True
        self.production_stage = 'quality_check'
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('质检完成'),
                'message': _('生产订单 %s 质检通过') % self.name,
                'type': 'success',
            }
        }
    
    def action_pause_production(self):
        """暂停生产"""
        self.ensure_one()
        
        self.production_stage = 'on_hold'
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('生产暂停'),
                'message': _('生产订单 %s 已暂停') % self.name,
                'type': 'warning',
            }
        }
    
    def action_resume_production(self):
        """恢复生产"""
        self.ensure_one()
        
        if self.production_stage == 'on_hold':
            self.production_stage = 'in_production'
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('生产恢复'),
                    'message': _('生产订单 %s 已恢复生产') % self.name,
                    'type': 'success',
                }
            }
    
    def get_production_summary(self):
        """获取生产摘要"""
        self.ensure_one()
        
        return {
            'production_name': self.name,
            'product_name': self.product_id.name,
            'production_line': dict(self._fields['production_line'].selection)[self.production_line],
            'scheduled_workers': self.scheduled_workers,
            'actual_workers': self.actual_workers,
            'estimated_hours': self.estimated_hours,
            'actual_hours': self.actual_hours,
            'production_efficiency': self.production_efficiency,
            'production_stage': dict(self._fields['production_stage'].selection)[self.production_stage],
            'priority': dict(self._fields['priority_level'].selection)[self.priority_level],
        }
