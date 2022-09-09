# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

class AccountFiscalPositionTaxInherit(models.Model):
    _inherit = "account.fiscal.position.tax"

    line_exoneracion = fields.Many2one('account.fiscal.position.exoneraciones_cr', string="Exoneración Costa Rica")

