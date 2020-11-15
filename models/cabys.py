# -*- coding: utf-8 -*-

from odoo import _, api, fields, models

class cabys(models.Model):
    _name = 'cabys.code'
    _rec_name = 'display_name'
    name = fields.Char(string='Nombre')
    code = fields.Char(string='Código')
    tax = fields.Char(string='Impuesto')
    cabys_category_1 = fields.Char(string='Categoría 1')
    cabys_category_2 = fields.Char(string='Categoría 2')
    cabys_category_3 = fields.Char(string='Categoría 3')
    cabys_category_4 = fields.Char(string='Categoría 4')
    cabys_category_5 = fields.Char(string='Categoría 5')
    cabys_category_6 = fields.Char(string='Categoría 6')
    cabys_category_7 = fields.Char(string='Categoría 7')
    cabys_category_8 = fields.Char(string='Categoría 8')
    display_name = fields.Char(compute='_compute_display_name',)
    @api.depends('code','name')
    def _compute_display_name(self):
        for record in self:
            record.display_name = '{}-{}'.format(record.code,record.name)


    