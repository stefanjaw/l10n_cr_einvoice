# -*- coding: utf-8 -*-

from odoo import _, api, fields, models

class UOM(models.Model):
    _inherit = 'uom.uom'
    uom_mh = fields.Char(string='Unidad Medida MH')
