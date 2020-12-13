# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

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
    

    @api.constrains('tax_ids')
    def _constrains_tax_ids(self):
        for record in self:
            if len(self.tax_ids) == 0:
                raise ValidationError('En Mapeo de impuestos debe de existir al menos una linea')