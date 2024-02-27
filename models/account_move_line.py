from odoo import models, fields, api, exceptions
from odoo.exceptions import ValidationError

class AccountMoveLineEinvoice(models.Model):
    _inherit = "account.move.line"

    product_type = fields.Selection([
        ('product', 'Producto'),
        ('service', 'Servicio'),
        ('other', 'Otro')
    ])
    
    cabys_code = fields.Char( )

    @api.onchange('product_id')
    def _compute_cabys_code(self):
        try:
            if self.product_id.detailed_type == "service":
                product_type = "service"
            elif self.product_id.detailed_type == "consu":
                product_type = "product"
            elif self.product_id.detailed_type == "product":
                product_type = "product"
            else:
                product_type = "other"
            
            self.cabys_code = self.product_id.cabys_code_id.code
            self.product_type = product_type
        except:
            pass
        
        return

    def create(self, params):
        lines = super().create(params)
        
        for line in lines:
            if line.product_type in [False, None] or \
            line.cabys_code   in [False, None]:
                line._compute_cabys_code()
        return lines
