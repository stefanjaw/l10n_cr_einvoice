# -*- coding: utf-8 -*-

from odoo import models, fields, api

import logging

log = _logging = logging.getLogger(__name__)

class ResCompanyFunctions(models.Model):
    _inherit = "res.company"
    
    @api.depends('country_id')
    def _get_country_code(self):
        log.info('--> 1575319718')
        for s in self:
            s.fe_current_country_company_code = s.country_id.code
