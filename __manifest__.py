# -*- coding: utf-8 -*-
{
    'name': "l10n_cr_einvoice",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "My Company",
    'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','contacts','account_accountant', 'l10n_cr'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'data/cabys.code.csv',
        'views/views.xml',
        'views/templates.xml',
        'views/cabys_views.xml',
        'views/electronic_doc_views.xml',
        'views/wizard_agregar_contabilidad_views.xml',
        'views/account_move_views.xml',
        'views/account_journal_views.xml',
        'views/res_partner.xml',
        'views/res_company.xml',
        'views/account_payment_term.xml',
        'views/product_template.xml',
        'views/uom_uom.xml',
        'views/account_tax.xml',
        'views/account_fiscal_position.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}

