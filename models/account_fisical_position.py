# -*- coding: utf-8 -*-

from odoo import _, api, fields, models


class AccountFiscalPosition(models.Model):
    _inherit = "account.fiscal.position"

    fiscal_position_type = fields.Selection([
        ('01', 'Authorized purchases'),
        ('02', 'Exempt sales to diplomats'),
        ('03', 'Purchase Order (Public Institutions and other organisms)'),
        ('04', 'Exemptions General Directorate of Finance'),
        ('05', 'Free trade zone'),
        ('99', 'Others'),
    ], string="Fiscal Position Type")
    document_number = fields.Char(string="Document Number")
    institution_name = fields.Char(string="Institution Name")
    issued_date = fields.Date(string="Issued Date")
