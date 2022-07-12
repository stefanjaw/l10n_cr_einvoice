# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
import logging

log = logging.getLogger(__name__)

class productCategoryInherit(models.Model):
    _inherit = 'product.category'
    
    cabys_code_id = fields.Many2one('cabys.code', string='Código cabys')