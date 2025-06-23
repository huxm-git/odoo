# -*- coding: utf-8 -*-
{
    'name': '小型生产型企业 ERP 系统 MVP',
    'version': '18.0.1.0.0',
    'category': 'Manufacturing',
    'summary': '小型生产型企业 ERP 系统 MVP 实现',
    'description': """
小型生产型企业 ERP 系统 MVP
============================

快速构建一个可演示的 ERP 系统原型，展示核心功能概念，用于客户演示和需求验证。

主要功能：
---------
* 智能库存管理 (简化版)
  - 基础产品管理
  - 简单的入库/出库操作
  - 库存查询界面
  - 模拟扫码功能

* 生产管理 (概念展示)
  - 简单的生产订单
  - 基础排班界面
  - 工时记录
  - 生产状态看板

* 订单管理 (基础版)
  - 销售订单创建
  - 订单状态跟踪
  - 简单的客户管理

* AI 助手 (模拟版)
  - 预设问答系统
  - 简单的对话界面
  - 常用查询快捷键

* 中文界面
  - 基础中文翻译
  - 中文菜单和标签
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': [
        'base',
        'product',
        'stock',
        'mrp',
        'sale',
        'purchase',
        'barcodes',
    ],
    'data': [
        # Security
        'security/ir.model.access.csv',
        
        # Data
        'data/demo_data.xml',
        'data/bom_data.xml',
        'data/product_routes.xml',
        'data/ai_responses.xml',
        
        # Views
        'views/product_views.xml',
        'views/stock_views.xml',
        'views/production_views.xml',
        'views/ai_assistant_views.xml',
        'views/menu_views.xml',
        
        # Wizards
        'wizard/stock_scan_wizard_views.xml',
    ],
    'demo': [
    ],
    'assets': {
        'web.assets_backend': [
            'manufacturing_mvp/static/src/css/manufacturing_mvp.css',
            'manufacturing_mvp/static/src/js/manufacturing_mvp.js',
        ],
    },
    'images': ['static/description/icon.png'],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': True,
    'sequence': 10,
}
