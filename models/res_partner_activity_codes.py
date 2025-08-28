# -*- coding: utf-8 -*-

from odoo import models, fields, api

class ResPartnerActivityCodes(models.Model):
    _name = "res.partner.activity.codes"
    _description = "Res Partner Activity Codes"
    
    name = fields.Char(string="descripcion", compute='_compute_name' )
    code = fields.Char(string="Codigo", )
    description = fields.Char(string="Descripcion", )
    partner_id = fields.Many2one(
        string="Contacto",
        comodel_name="res.partner",
        ondelete="set null",
    )
    
    @api.depends()
    def _compute_name(self):
        for record in self:
            record.name = record.code + " " + record.description