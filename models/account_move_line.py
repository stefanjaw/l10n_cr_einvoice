from odoo import models, fields, api, exceptions
from odoo.exceptions import ValidationError

import logging

_logger = log = logging.getLogger(__name__)

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
        _logger.info(f"DEF19 self: {self}-{self.product_id.detailed_type} \n\n")
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
        

    