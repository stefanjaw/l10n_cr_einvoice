# -*- coding: utf-8 -*-

from odoo import _, api, fields, models

class cabys(models.Model):
    _name = 'forma.farmaceutica'
    _description = "Forma Farmaceutica"
    
    _rec_name = 'display_name'
    name = fields.Char(string='Nombre')
    code = fields.Char(string='Código')
    active = fields.Boolean(default=True)

    display_name = fields.Char(compute='_compute_display_name',store=True)

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        recs = self.browse()
        if not recs:
               recs = self.search([('display_name', operator, name)] + args, limit=limit)
        return recs.name_get()

    @api.depends('code','name')
    def _compute_display_name(self):
        for record in self:
            record.display_name = f'{record.code}-{record.name}'


    