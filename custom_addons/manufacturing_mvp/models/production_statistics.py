# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import timedelta


class ProductionStatistics(models.TransientModel):
    _name = 'production.statistics'
    _description = '生产统计报表'
    
    date_from = fields.Date('开始日期', default=lambda self: fields.Date.today().replace(day=1))
    date_to = fields.Date('结束日期', default=fields.Date.today)
    
    # 统计数据字段
    total_orders = fields.Integer('总订单数', readonly=True)
    total_hours = fields.Float('总工时', readonly=True)
    total_workers = fields.Integer('总工人数', readonly=True)
    average_efficiency = fields.Float('平均效率(%)', readonly=True)
    
    # 生产线统计
    line_a_orders = fields.Integer('生产线A订单数', readonly=True)
    line_a_hours = fields.Float('生产线A工时', readonly=True)
    line_a_usage = fields.Float('生产线A使用率(%)', readonly=True)
    
    line_b_orders = fields.Integer('生产线B订单数', readonly=True)
    line_b_hours = fields.Float('生产线B工时', readonly=True)
    line_b_usage = fields.Float('生产线B使用率(%)', readonly=True)
    
    line_c_orders = fields.Integer('生产线C订单数', readonly=True)
    line_c_hours = fields.Float('生产线C工时', readonly=True)
    line_c_usage = fields.Float('生产线C使用率(%)', readonly=True)
    
    line_d_orders = fields.Integer('生产线D订单数', readonly=True)
    line_d_hours = fields.Float('生产线D工时', readonly=True)
    line_d_usage = fields.Float('生产线D使用率(%)', readonly=True)
    
    # 工人统计
    total_worker_hours = fields.Float('总工人工时', readonly=True)
    average_workers_per_order = fields.Float('平均工人数/订单', readonly=True)
    daily_average_hours = fields.Float('日均工时', readonly=True)
    workload_percentage = fields.Float('工作负荷(%)', readonly=True)
    
    def action_refresh_statistics(self):
        """刷新统计数据"""
        self.ensure_one()
        
        # 获取生产订单数据
        domain = [
            ('date_start', '>=', self.date_from),
            ('date_start', '<=', self.date_to),
            ('state', 'in', ['confirmed', 'progress', 'done'])
        ]
        
        productions = self.env['mrp.production'].search(domain)
        
        if not productions:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('提示'),
                    'message': _('选定时间范围内没有生产订单数据'),
                    'type': 'warning',
                }
            }
        
        # 计算总体统计
        total_orders = len(productions)
        total_hours = sum(p.estimated_hours or 0 for p in productions)
        total_workers = sum(p.scheduled_workers or 0 for p in productions)
        
        # 计算效率
        actual_hours = sum(p.actual_hours or 0 for p in productions if p.actual_hours)
        estimated_hours = sum(p.estimated_hours or 0 for p in productions if p.estimated_hours)
        average_efficiency = (estimated_hours / actual_hours * 100) if actual_hours > 0 else 0
        
        # 按生产线统计
        line_stats = {}
        for line_code, line_name in self.env['mrp.production']._fields['production_line'].selection:
            line_productions = productions.filtered(lambda p: p.production_line == line_code)
            line_stats[line_code] = {
                'orders': len(line_productions),
                'hours': sum(p.estimated_hours or 0 for p in line_productions),
                'usage': (len(line_productions) / total_orders * 100) if total_orders > 0 else 0
            }
        
        # 工人统计
        total_worker_hours = sum((p.estimated_hours or 0) * (p.scheduled_workers or 0) for p in productions)
        average_workers_per_order = total_workers / total_orders if total_orders > 0 else 0
        
        # 计算日期范围
        date_range = (self.date_to - self.date_from).days + 1
        daily_average_hours = total_hours / date_range if date_range > 0 else 0
        
        # 假设每天8小时工作制，4条生产线
        max_daily_hours = 8 * 4
        workload_percentage = (daily_average_hours / max_daily_hours * 100) if max_daily_hours > 0 else 0
        
        # 更新统计数据
        self.write({
            'total_orders': total_orders,
            'total_hours': total_hours,
            'total_workers': total_workers,
            'average_efficiency': average_efficiency,
            
            'line_a_orders': line_stats.get('line_a', {}).get('orders', 0),
            'line_a_hours': line_stats.get('line_a', {}).get('hours', 0),
            'line_a_usage': line_stats.get('line_a', {}).get('usage', 0),
            
            'line_b_orders': line_stats.get('line_b', {}).get('orders', 0),
            'line_b_hours': line_stats.get('line_b', {}).get('hours', 0),
            'line_b_usage': line_stats.get('line_b', {}).get('usage', 0),
            
            'line_c_orders': line_stats.get('line_c', {}).get('orders', 0),
            'line_c_hours': line_stats.get('line_c', {}).get('hours', 0),
            'line_c_usage': line_stats.get('line_c', {}).get('usage', 0),
            
            'line_d_orders': line_stats.get('line_d', {}).get('orders', 0),
            'line_d_hours': line_stats.get('line_d', {}).get('hours', 0),
            'line_d_usage': line_stats.get('line_d', {}).get('usage', 0),
            
            'total_worker_hours': total_worker_hours,
            'average_workers_per_order': average_workers_per_order,
            'daily_average_hours': daily_average_hours,
            'workload_percentage': workload_percentage,
        })
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('统计完成'),
                'message': _('生产统计数据已更新，共分析了 %d 个生产订单') % total_orders,
                'type': 'success',
            }
        }
    
    def action_this_month_stats(self):
        """本月统计"""
        today = fields.Date.today()
        first_day = today.replace(day=1)
        
        self.write({
            'date_from': first_day,
            'date_to': today
        })
        
        return self.action_refresh_statistics()
    
    def action_last_month_stats(self):
        """上月统计"""
        today = fields.Date.today()
        first_day_this_month = today.replace(day=1)
        last_month = first_day_this_month - timedelta(days=1)
        first_day_last_month = last_month.replace(day=1)
        
        self.write({
            'date_from': first_day_last_month,
            'date_to': last_month
        })
        
        return self.action_refresh_statistics()
