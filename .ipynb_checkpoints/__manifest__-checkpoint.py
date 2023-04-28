# -*- coding: utf-8 -*-
{
    'name': "Costa Rica - Edi Electronic Invoicing",

    'summary': """Costa Rica - Edi Electronic Invoicing.""",

    'description': """
        Costa Rica - Edi Electronic Invoicing.
    """,

    'author': "Avalantec",
    'website': "http://www.avalantec.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/13.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Accounting',
    'version': '13.0.0.7',

    # any module necessary for this one to work correctly
    'depends': ['base','contacts','l10n_cr_zones','account_accountant','l10n_cr','sale_management'],

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
        'views/uom_views.xml',
        'views/cron_job_views.xml',
        'views/res_country_state_views.xml',
        # 'views/account_move_reversal_views.xml', # See note inside this document
        'views/report_invoice_document_with_payments.xml',
        'views/electronic_doc_views.xml',
        'views/email_views.xml',
        'views/cabys_views.xml',
        'views/account_fisical_position.xml',
        'views/wizard_agregar_contabilidad_views.xml',
        'views/wizard_account_debit_views.xml',
        'data/rules.xml',
        'data/cabys.code.csv',
        'data/ir.sequence.csv',
    ],
    'external_dependencies': {
        "python": [
            'xmltodict',
        ],
    },
}
