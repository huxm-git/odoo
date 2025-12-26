# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'
    
    # 扫码模式字段
    scan_mode = fields.Boolean(
        '扫码模式', 
        default=False,
        help="启用扫码模式进行快速入库/出库操作"
    )
    
    # 扫码操作记录
    scan_log = fields.Text(
        '扫码记录',
        readonly=True,
        help="记录扫码操作的历史"
    )
    
    # 快速操作状态
    quick_operation = fields.Boolean(
        '快速操作',
        default=False,
        help="标记为快速操作的单据"
    )
    
    def action_simulate_scan(self):
        """模拟扫码入库/出库"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('扫码操作'),
            'res_model': 'stock.scan.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_picking_id': self.id,
                'default_operation_type': self.picking_type_id.code,
            }
        }
    
    def action_toggle_scan_mode(self):
        """切换扫码模式"""
        self.ensure_one()
        self.scan_mode = not self.scan_mode
        
        if self.scan_mode:
            message = _('已启用扫码模式')
            notification_type = 'success'
        else:
            message = _('已关闭扫码模式')
            notification_type = 'info'
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('扫码模式'),
                'message': message,
                'type': notification_type,
            }
        }
    
    def action_quick_validate(self):
        """快速验证操作"""
        self.ensure_one()
        
        if self.state not in ['assigned', 'confirmed']:
            raise UserError(_('只有已确认或已分配的单据才能进行快速验证。'))
        
        # 自动设置所有移动行的完成数量
        for move in self.move_ids:
            if move.state in ['assigned', 'confirmed']:
                move.quantity = move.product_uom_qty
        
        # 验证单据
        try:
            self.button_validate()
            self.quick_operation = True
            
            # 记录操作日志
            log_entry = f"{fields.Datetime.now()}: 快速验证操作完成\n"
            self.scan_log = (self.scan_log or '') + log_entry
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('操作成功'),
                    'message': _('单据已快速验证完成'),
                    'type': 'success',
                }
            }
        except Exception as e:
            raise UserError(_('快速验证失败: %s') % str(e))
    
    def action_scan_product_in(self, product_id, quantity=1):
        """扫码入库产品"""
        self.ensure_one()
        
        if self.picking_type_id.code != 'incoming':
            raise UserError(_('此操作只适用于入库单据'))
        
        product = self.env['product.product'].browse(product_id)
        if not product.exists():
            raise UserError(_('产品不存在'))
        
        # 查找或创建移动行
        move = self.move_ids.filtered(lambda m: m.product_id.id == product_id)
        if move:
            # 更新现有移动行
            move[0].product_uom_qty += quantity
        else:
            # 创建新的移动行
            self.env['stock.move'].create({
                'name': product.name,
                'product_id': product_id,
                'product_uom_qty': quantity,
                'product_uom': product.uom_id.id,
                'picking_id': self.id,
                'location_id': self.location_id.id,
                'location_dest_id': self.location_dest_id.id,
            })
        
        # 记录扫码日志
        log_entry = f"{fields.Datetime.now()}: 扫码入库 {product.name} x{quantity}\n"
        self.scan_log = (self.scan_log or '') + log_entry
        
        return {
            'success': True,
            'message': f'已添加 {product.name} x{quantity} 到入库单'
        }
    
    def action_scan_product_out(self, product_id, quantity=1):
        """扫码出库产品"""
        self.ensure_one()
        
        if self.picking_type_id.code != 'outgoing':
            raise UserError(_('此操作只适用于出库单据'))
        
        product = self.env['product.product'].browse(product_id)
        if not product.exists():
            raise UserError(_('产品不存在'))
        
        # 检查库存
        if product.qty_available < quantity:
            raise UserError(_('产品 %s 库存不足，当前库存: %s') % (product.name, product.qty_available))
        
        # 查找或创建移动行
        move = self.move_ids.filtered(lambda m: m.product_id.id == product_id)
        if move:
            # 更新现有移动行
            move[0].product_uom_qty += quantity
        else:
            # 创建新的移动行
            self.env['stock.move'].create({
                'name': product.name,
                'product_id': product_id,
                'product_uom_qty': quantity,
                'product_uom': product.uom_id.id,
                'picking_id': self.id,
                'location_id': self.location_id.id,
                'location_dest_id': self.location_dest_id.id,
            })
        
        # 记录扫码日志
        log_entry = f"{fields.Datetime.now()}: 扫码出库 {product.name} x{quantity}\n"
        self.scan_log = (self.scan_log or '') + log_entry
        
        return {
            'success': True,
            'message': f'已添加 {product.name} x{quantity} 到出库单'
        }
    
    def get_scan_summary(self):
        """获取扫码操作摘要"""
        self.ensure_one()
        
        summary = {
            'picking_name': self.name,
            'operation_type': self.picking_type_id.name,
            'scan_mode': self.scan_mode,
            'total_products': len(self.move_ids),
            'total_quantity': sum(self.move_ids.mapped('product_uom_qty')),
            'scan_log': self.scan_log or '暂无扫码记录',
        }
        
        return summary
