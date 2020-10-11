from odoo import models, fields, api

class irSequence(models.Model):
    _inherit = 'ir.sequence'
    prefix_code = fields.Char(string ='codigo prefijo', compute = '_compute_prefix_code')
    
    @api.depends("prefix",)
    def _compute_prefix_code(self):
        if len(self.prefix) == 10:
            self.prefix_code = self.prefix[8:10]
            
            