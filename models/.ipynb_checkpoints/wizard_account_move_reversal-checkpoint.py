# -*- coding: utf-8 -*-

from odoo import _, api, fields, models

import logging
_logging = _logger = logging.getLogger(__name__)

class wizardReversal(models.TransientModel):
    _inherit = 'account.move.reversal'
    
    def reverse_moves(self):
        _logger.info(f"  Reversing Moves\n")
        move_data = super(wizardReversal,self).reverse_moves()
        
        res_model = move_data.get('res_model')
        res_id_int = move_data.get('res_id')
        domain = move_data.get('domain')
        
        if domain not in [False, None]:
            credit_move_ids = self.env[ res_model ].search( domain )
        elif res_id_int not in [False, None]:
            credit_move_ids = self.env[ res_model ].browse( res_id_int )
        
        for credit_move_id in credit_move_ids:
            
            if credit_move_id.state == "posted" \
            and credit_move_id.fe_clave == False \
            and credit_move_id.fe_doc_type != False:
                
                credit_move_id._generar_clave()
            
        return move_data
