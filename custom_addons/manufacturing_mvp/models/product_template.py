# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # 添加生产相关字段
    production_time = fields.Float(
        '生产时间(小时)',
        default=1.0,
        help="生产一个单位产品所需的时间（小时）"
    )
    min_stock_level = fields.Float(
        '最低库存',
        default=10.0,
        help="产品的最低库存水平，低于此值时需要补货"
    )
    supplier_lead_time = fields.Integer(
        '供应商交期(天)',
        default=7,
        help="供应商交货所需的天数"
    )

    # 库存状态字段
    stock_status = fields.Selection([
        ('in_stock', '有库存'),
        ('low_stock', '库存不足'),
        ('out_of_stock', '缺货'),
    ], string='库存状态', compute='_compute_stock_status', store=True)

    # 生产状态字段
    production_status = fields.Selection([
        ('ready', '可生产'),
        ('planning', '计划中'),
        ('producing', '生产中'),
        ('completed', '已完成'),
    ], string='生产状态', default='ready')

    @api.depends('qty_available', 'min_stock_level')
    def _compute_stock_status(self):
        """计算库存状态"""
        for product in self:
            if product.qty_available <= 0:
                product.stock_status = 'out_of_stock'
            elif product.qty_available <= product.min_stock_level:
                product.stock_status = 'low_stock'
            else:
                product.stock_status = 'in_stock'

    @api.depends('type')
    def compute_is_storable(self):
        """重写库存跟踪计算逻辑，确保consu类型产品可以跟踪库存"""
        # 对于consu类型的产品，默认启用库存跟踪
        for product in self:
            if product.type == 'consu':
                product.is_storable = True
            elif product.type != 'consu' and product.is_storable:
                product.is_storable = False

    # 重写is_storable字段，强制为True
    is_storable = fields.Boolean(
        'Is Storable',
        compute='compute_is_storable',
        store=True,
        default=True,
        help="Technical field to determine if the product should be tracked in inventory"
    )
    
    @api.model
    def simulate_barcode_scan(self, barcode_input):
        """模拟扫码功能"""
        if not barcode_input:
            return {
                'success': False, 
                'message': '请输入条码'
            }
        
        # 查找产品
        product = self.search([('barcode', '=', barcode_input)], limit=1)
        if not product:
            # 如果没找到，尝试按名称搜索
            product = self.search([('name', 'ilike', barcode_input)], limit=1)
        
        if product:
            return {
                'success': True,
                'product_id': product.id,
                'product_name': product.name,
                'current_stock': product.qty_available,
                'stock_status': product.stock_status,
                'min_stock_level': product.min_stock_level,
                'barcode': product.barcode or '无条码',
                'message': f'找到产品: {product.name}'
            }
        else:
            return {
                'success': False, 
                'message': f'未找到条码为 "{barcode_input}" 的产品'
            }
    
    def action_check_stock_level(self):
        """检查库存水平"""
        self.ensure_one()
        if self.qty_available <= self.min_stock_level:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('库存预警'),
                    'message': _('产品 %s 库存不足！当前库存: %s，最低库存: %s') % (
                        self.name, self.qty_available, self.min_stock_level
                    ),
                    'type': 'warning',
                    'sticky': True,
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('库存正常'),
                    'message': _('产品 %s 库存充足。当前库存: %s') % (
                        self.name, self.qty_available
                    ),
                    'type': 'success',
                }
            }
    
    def action_create_production_order(self):
        """创建生产订单"""
        self.ensure_one()
        if not self.bom_ids:
            raise UserError(_('产品 %s 没有配置物料清单(BOM)，无法创建生产订单。') % self.name)
        
        # 创建生产订单
        production_vals = {
            'product_id': self.product_variant_id.id,
            'product_qty': max(self.min_stock_level - self.qty_available, 1),
            'bom_id': self.bom_ids[0].id,
            'origin': f'库存补充 - {self.name}',
        }
        
        production = self.env['mrp.production'].create(production_vals)
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('生产订单'),
            'res_model': 'mrp.production',
            'res_id': production.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def get_production_capacity(self):
        """获取生产能力信息"""
        self.ensure_one()
        return {
            'product_name': self.name,
            'production_time': self.production_time,
            'current_stock': self.qty_available,
            'min_stock_level': self.min_stock_level,
            'recommended_production': max(self.min_stock_level - self.qty_available, 0),
            'estimated_production_time': max(self.min_stock_level - self.qty_available, 0) * self.production_time,
        }

    def setup_manufacturing_routes(self):
        """为成品设置制造和MTO路由"""
        self.ensure_one()

        # 获取制造和MTO路由
        manufacture_route = self.env.ref('mrp.route_warehouse0_manufacture', raise_if_not_found=False)
        mto_route = self.env.ref('stock.route_warehouse0_mto', raise_if_not_found=False)

        if not manufacture_route:
            raise UserError(_('制造路由未找到，请确保MRP模块已正确安装。'))

        # 激活MTO路由
        if mto_route and not mto_route.active:
            mto_route.active = True

        # 为成品配置路由
        if self.sale_ok and not self.purchase_ok:  # 成品
            route_ids = []
            if manufacture_route:
                route_ids.append(manufacture_route.id)
            if mto_route:
                route_ids.append(mto_route.id)

            if route_ids:
                self.route_ids = [(6, 0, route_ids)]
                return True

        return False

    @api.model
    def setup_all_manufacturing_routes(self):
        """为所有成品设置制造路由"""
        finished_products = self.search([
            ('sale_ok', '=', True),
            ('purchase_ok', '=', False)
        ])

        success_count = 0
        for product in finished_products:
            if product.setup_manufacturing_routes():
                success_count += 1

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('路由配置完成'),
                'message': _('已为 %d 个成品配置制造路由') % success_count,
                'type': 'success',
            }
        }

    def action_view_stock_moves(self):
        """查看产品的库存移动"""
        self.ensure_one()

        # 获取该产品的所有库存移动
        stock_moves = self.env['stock.move'].search([
            ('product_id', 'in', self.product_variant_ids.ids)
        ])

        if not stock_moves:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('提示'),
                    'message': _('产品 %s 没有库存移动记录') % self.name,
                    'type': 'info',
                }
            }

        return {
            'type': 'ir.actions.act_window',
            'name': _('库存移动 - %s') % self.name,
            'res_model': 'stock.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', stock_moves.ids)],
            'context': {
                'search_default_group_by_location_id': 1,
                'search_default_group_by_date': 1,
            },
            'target': 'current',
        }
