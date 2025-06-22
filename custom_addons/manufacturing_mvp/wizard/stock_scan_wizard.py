# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class StockScanWizard(models.TransientModel):
    _name = 'stock.scan.wizard'
    _description = '库存扫码向导'
    
    picking_id = fields.Many2one(
        'stock.picking', 
        '库存单据', 
        required=True,
        readonly=True
    )
    
    operation_type = fields.Selection([
        ('incoming', '入库'),
        ('outgoing', '出库'),
        ('internal', '内部调拨'),
    ], string='操作类型', required=True, readonly=True)
    
    barcode_input = fields.Char(
        '条码输入',
        help="输入产品条码或产品名称"
    )
    
    product_id = fields.Many2one(
        'product.product',
        '产品',
        readonly=True
    )
    
    product_name = fields.Char(
        '产品名称',
        readonly=True
    )
    
    current_stock = fields.Float(
        '当前库存',
        readonly=True
    )
    
    quantity = fields.Float(
        '数量',
        default=1.0,
        required=True
    )
    
    scan_result = fields.Text(
        '扫码结果',
        readonly=True
    )
    
    operation_log = fields.Text(
        '操作记录',
        readonly=True
    )
    
    @api.onchange('barcode_input')
    def _onchange_barcode_input(self):
        """条码输入变化时查找产品"""
        if self.barcode_input:
            # 使用产品模板的扫码模拟功能
            result = self.env['product.template'].simulate_barcode_scan(self.barcode_input)
            
            if result['success']:
                product = self.env['product.template'].browse(result['product_id'])
                self.product_id = product.product_variant_id.id
                self.product_name = result['product_name']
                self.current_stock = result['current_stock']
                self.scan_result = result['message']
            else:
                self.product_id = False
                self.product_name = ''
                self.current_stock = 0
                self.scan_result = result['message']
    
    def action_scan_product(self):
        """执行扫码操作"""
        self.ensure_one()
        
        if not self.product_id:
            raise UserError(_('请先扫描有效的产品条码'))
        
        if self.quantity <= 0:
            raise UserError(_('数量必须大于0'))
        
        try:
            if self.operation_type == 'incoming':
                result = self.picking_id.action_scan_product_in(
                    self.product_id.id, 
                    self.quantity
                )
            elif self.operation_type == 'outgoing':
                result = self.picking_id.action_scan_product_out(
                    self.product_id.id, 
                    self.quantity
                )
            else:
                raise UserError(_('暂不支持此操作类型'))
            
            # 更新操作记录
            log_entry = f"{fields.Datetime.now()}: {result['message']}\n"
            self.operation_log = (self.operation_log or '') + log_entry
            
            # 清空输入准备下次扫码
            self.barcode_input = ''
            self.product_id = False
            self.product_name = ''
            self.current_stock = 0
            self.quantity = 1.0
            self.scan_result = '操作成功，可以继续扫码'
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('扫码成功'),
                    'message': result['message'],
                    'type': 'success',
                }
            }
            
        except Exception as e:
            self.scan_result = f'操作失败: {str(e)}'
            raise UserError(_('扫码操作失败: %s') % str(e))
    
    def action_finish_scan(self):
        """完成扫码操作"""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('库存单据'),
            'res_model': 'stock.picking',
            'res_id': self.picking_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def action_quick_validate(self):
        """快速验证单据"""
        self.ensure_one()
        
        try:
            self.picking_id.action_quick_validate()
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('验证成功'),
                    'message': _('单据已验证完成'),
                    'type': 'success',
                }
            }
        except Exception as e:
            raise UserError(_('验证失败: %s') % str(e))
    
    def get_picking_summary(self):
        """获取单据摘要"""
        self.ensure_one()
        
        return {
            'picking_name': self.picking_id.name,
            'operation_type': self.picking_id.picking_type_id.name,
            'total_products': len(self.picking_id.move_ids),
            'state': self.picking_id.state,
        }
