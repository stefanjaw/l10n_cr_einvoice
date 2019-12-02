# -*- coding: utf-8 -*-

from odoo import models, fields, api

class activityCode(models.Model):
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
        comodel_name="account.invoice",
        inverse_name="fe_activity_code_id",
    )

    @api.multi
    @api.depends()
    def compute_name(self):
        for s in self:
            s.name = s.code+" "+s.description
