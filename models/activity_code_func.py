# -*- coding: utf-8 -*-

from odoo import models, fields, api

class ActivityCodeFunctions(models.Model):
    _inherit = "activity.code"
    
    @api.depends()
    def compute_name(self):
        for s in self:
            s.name = s.code+" "+s.description