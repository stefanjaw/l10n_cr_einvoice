from odoo import models, fields, api
import logging
log = logging.getLogger(__name__)

class irSequence(models.Model):
    _inherit = 'ir.sequence'
    prefix_code = fields.Char(string ='codigo prefijo', compute = '_compute_prefix_code',store=True)
    
    @api.depends("prefix",)
    def _compute_prefix_code(self):
        for record in self:
            if record.prefix:
                if len(record.prefix) == 10:
                    record.prefix_code = record.prefix[8:10]
            
            
