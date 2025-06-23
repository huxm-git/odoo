#!/usr/bin/env python3
"""
库存修复脚本 - 修复Odoo 18中consu类型产品的库存跟踪问题

这个脚本解决了Odoo 18中的一个关键问题：
- consu类型产品默认不跟踪库存(is_storable=False)
- 但是有库存移动记录的产品无法修改is_storable字段
- 导致库存计算错误

解决方案：
1. 直接在数据库层面修改is_storable字段
2. 重新计算所有产品的库存数量
3. 创建缺失的stock.quant记录
"""

import logging
from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)

def fix_inventory_tracking(cr, registry):
    """修复库存跟踪问题"""
    
    with api.Environment.manage():
        env = api.Environment(cr, SUPERUSER_ID, {})
        
        _logger.info("开始修复库存跟踪问题...")
        
        # 1. 查找所有Strict产品
        strict_products = env['product.template'].search([('name', 'ilike', 'Strict')])
        _logger.info(f"找到 {len(strict_products)} 个Strict产品")
        
        # 2. 直接在数据库层面修改is_storable字段
        product_ids = [p.id for p in strict_products]
        if product_ids:
            cr.execute("""
                UPDATE product_template 
                SET is_storable = true 
                WHERE id = ANY(%s) AND type = 'consu'
            """, (product_ids,))
            _logger.info(f"已在数据库层面设置 {len(product_ids)} 个产品的is_storable=true")
        
        # 3. 修复每个产品的库存
        for product in strict_products:
            try:
                _fix_product_inventory(env, product)
            except Exception as e:
                _logger.error(f"修复产品 {product.name} 失败: {e}")
        
        # 4. 提交事务
        cr.commit()
        _logger.info("库存修复完成！")

def _fix_product_inventory(env, product):
    """修复单个产品的库存"""
    
    variant = product.product_variant_id
    
    # 计算理论库存
    moves = env['stock.move'].search([
        ('product_id', '=', variant.id),
        ('state', '=', 'done')
    ])
    
    incoming = 0
    outgoing = 0
    
    for move in moves:
        if move.location_dest_id.usage == 'internal':
            incoming += move.quantity
        elif move.location_id.usage == 'internal':
            outgoing += move.quantity
    
    theoretical_stock = incoming - outgoing
    
    if theoretical_stock <= 0:
        return  # 没有库存，不需要修复
    
    # 获取主仓库位置
    warehouse = env['stock.warehouse'].search([('company_id', '=', env.company.id)], limit=1)
    if not warehouse:
        _logger.warning(f"未找到仓库，跳过产品 {product.name}")
        return
    
    stock_location = warehouse.lot_stock_id
    
    # 检查是否已有stock.quant记录
    existing_quant = env['stock.quant'].search([
        ('product_id', '=', variant.id),
        ('location_id', '=', stock_location.id)
    ])
    
    if existing_quant:
        # 更新现有记录
        existing_quant.write({
            'quantity': theoretical_stock,
            'available_quantity': theoretical_stock,
        })
        _logger.info(f"更新产品 {product.name} 库存: {theoretical_stock}")
    else:
        # 直接在数据库层面创建stock.quant记录
        env.cr.execute("""
            INSERT INTO stock_quant (
                product_id, location_id, quantity, available_quantity, 
                create_date, write_date, create_uid, write_uid
            ) VALUES (%s, %s, %s, %s, NOW(), NOW(), %s, %s)
        """, (
            variant.id, stock_location.id, theoretical_stock, theoretical_stock,
            env.uid, env.uid
        ))
        _logger.info(f"创建产品 {product.name} 库存记录: {theoretical_stock}")

# 在模块安装/升级时自动执行
def post_init_hook(cr, registry):
    """模块安装后执行的钩子函数"""
    fix_inventory_tracking(cr, registry)
