# -*- coding: utf-8 -*-

from odoo import models, fields, api

class ResPartnerActivityCodes(models.Model):
    _name = "res.partner.activity.codes"
    _description = "Res Partner Activity Codes"
    
    active = fields.Boolean(default=True)
    name = fields.Char(string="Nombre" )
    code = fields.Char(string="Codigo", )
    type = fields.Char(string="Tipo" )
    status = fields.Char(string="Estado" )
    description = fields.Char(string="Descripcion" )
    
    partner_id = fields.Many2one(
        string="Contacto",
        comodel_name="res.partner",
        ondelete="set null",
    )
    
    # @api.depends()
    # def _compute_name(self):
    #     for record in self:
    #         name = record.name
    #         if not name:
    #                 name = "Unkown"
    #         record.display_name = record.code + " " + name