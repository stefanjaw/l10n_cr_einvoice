# -*- coding: utf-8 -*-

from odoo import models, fields, api

class ActivityCode(models.Model):
    _name = "activity.code"
    name = fields.Char(string="descripcion", compute = 'compute_name' )
    code = fields.Char(string="Codigo", )
    description = fields.Char(string="Descripcion", )
    company_id = fields.Many2one(
        string="Compañia",
        comodel_name="res.company",
        ondelete="set null",
        default= lambda self: self.env.company_id.id,
    )
    invoice_ids = fields.One2many(
        string="Invoice",
        comodel_name="account.move",
        inverse_name="fe_activity_code_id",
    )
    
    invoice_refund_ids = fields.One2many(
            string="Invoice",
            comodel_name="account.move.reversal",
            inverse_name="fe_activity_code_id",
    )
   