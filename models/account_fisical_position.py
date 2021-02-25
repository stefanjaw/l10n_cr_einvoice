# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

class AccountFiscalPosition(models.Model):
    _inherit = "account.fiscal.position"

    fiscal_position_type = fields.Selection([
        ('01', 'Compras autorizadas'),
        ('02', 'Ventas exentas a diplomáticos'),
        ('03', 'Autorizado por Ley especial'),
        ('04', 'Exenciones Dirección General de Hacienda'),
        ('05', 'Transitorio V'),
        ('06', 'Transitorio IX'),
        ('07', 'Transitorio XVII'),
        ('99', 'Otros'),
    ], string="Tipo de Documento")
    document_number = fields.Char(string="Número de Documento")
    institution_name = fields.Char(string="Nombre de la Institución")
    issued_date = fields.Date(string="Fecha de la Emisión")
    

    @api.constrains('tax_ids')
    def _constrains_tax_ids(self):
        for record in self:
            if len(self.tax_ids) == 0:
                raise ValidationError('En Mapeo de impuestos debe de existir al menos una linea')
