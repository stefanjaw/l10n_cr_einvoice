# -*- coding: utf-8 -*-

from odoo import models, fields, api

import logging
_logging = _logger = logging.getLogger(__name__)

class ActivityCodeFunctions(models.Model):
    _inherit = "activity.code"
    
    @api.depends()
    def compute_name(self):
        for s in self:
            if s.code == False:
                s.code = ""
            if s.description == False:
                s.description = ""
            
            s.name = s.code + " " + s.description
