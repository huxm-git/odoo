# -*- coding: utf-8 -*-
{
    'name': '中文本地化支持',
    'version': '18.0.1.0.0',
    'category': 'Localization',
    'summary': '为制造MVP系统提供中文本地化支持',
    'description': """
中文本地化支持
==============

为小型生产型企业ERP系统MVP提供完整的中文本地化支持，包括：

* 界面中文翻译
* 中文菜单和标签
* 中文错误信息
* 中文帮助文档
* 中文数据格式
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': [
        'base',
        'manufacturing_mvp',
    ],
    'data': [
        'data/base_data.xml',
    ],
    'images': [],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
    'sequence': 20,
}
