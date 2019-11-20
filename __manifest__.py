# -*- coding: utf-8 -*-
{
    'name': "Electronic Invoice Costa Rica Version 4.3 l10n_cr_einvoice",

    'summary': """
        Module to generate Electronic Invoices from Costa Rica
        """,

    'description': """
        Configuration:
        --> Journals with Type Sale:
            Enable Credit Notes with Own Sequence Numbers
            Enable Debit Notes with Own Sequence Numbers

            For each Journal - Sequence:
               Disable 'Use subsequences per date_range	'
               Sequence Size: 10 Digits
               Prefix has the format: CompanyID(001) + TerminalID(00001) + Doc Type(01)
    """,

    'author': "Avalantec",
    'website': "http://www.avalantec.com",

    'category': 'Localization',
    'version': '20190811.1424',

    'depends': ['base','contacts','account_accountant'],


    'data': [
        'views/canton.xml',
        'views/cron.xml',
        'views/district.xml',
        'views/invoice.xml',
        'views/neighborhood.xml',
        'views/partner.xml',
        'views/payment_term.xml',
        'views/product.xml',
        'views/provincia.xml',
        'views/report.xml',
        'views/tax.xml',
    ],

    'demo': [
        'demo/demo.xml',
    ],
}
