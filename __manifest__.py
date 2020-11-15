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
    # Check https://github.com/odoo/odoo/blob/13.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','contacts','l10n_cr_zones','account_accountant','l10n_cr'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/account_move_views.xml',
        'views/confirm_alert_views.xml',
        'views/confirm_message_views.xml',
        'views/res_company_views.xml',
        'views/res_partner_views.xml',
        'views/account_journal_views.xml',
        'views/account_move_views.xml',
        'views/account_payment_term_views.xml',
        'views/account_tax_views.xml',
        'views/product_template_views.xml',
        'views/cron_job_views.xml',
        'views/res_country_state_views.xml',
        'views/account_move_reversal_views.xml',
        'views/report_invoice_document_with_payments.xml',
        'views/electronic_doc_views.xml',
        'views/email_views.xml',
        'views/cabys_views.xml',
        'views/wizard_agregar_contabilidad_views.xml',
        'views/wizard_account_debit_views.xml',
        'data/sequence_data.xml',
        'data/cabys.code.csv',
    ],
    # only loaded in demonstration mode
    'demo': [
        #'demo/demo.xml',
    ],
}
