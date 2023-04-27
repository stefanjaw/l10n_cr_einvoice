from odoo import models, fields, api, _
from odoo.tools.safe_eval import safe_eval
from odoo.exceptions import UserError

import logging
_logging = _logger = logging.getLogger(__name__)

class AccountMoveReversal(models.TransientModel):
    _inherit = "account.move.reversal"
    
    @api.depends('company_id')
    def _get_country_code(self):
        for s in self:
            s.fe_current_country_company_code = s.company_id.country_id.code 
    
    
    def _prepare_default_reversal(self, move_id ):
        _logger.info(f"  Reversal default values\n")

        data = super(AccountMoveReversal,self)._prepare_default_reversal(move_id)
        
        data['fe_informacion_referencia_codigo'] = self.fe_informacion_referencia_codigo
        
        if move_id.name[8:10] == '01':
            fe_tipo_documento_referencia = '01'
            is_electronic_document = True
        elif move_id.name[8:10] == '02':
            fe_tipo_documento_referencia = '02'
            is_electronic_document = True
        elif move_id.name[8:10] == '03':
            fe_tipo_documento_referencia = '03'
            is_electronic_document = True
        elif move_id.name[8:10] == '04':
            fe_tipo_documento_referencia = '04'
            is_electronic_document = True
        else:
            fe_tipo_documento_referencia = False
            is_electronic_document = False
            
        data['fe_tipo_documento_referencia'] = fe_tipo_documento_referencia
        
        if is_electronic_document == True:
            data['fe_doc_type'] = "NotaCreditoElectronica"
        
        data['invoice_payment_term_id'] = move_id.invoice_payment_term_id.id
        
        data['fe_doc_ref'] = move_id.name
        data['fe_payment_type'] = move_id.fe_payment_type
        data['fe_receipt_status'] = move_id.fe_receipt_status
        data['fe_activity_code_id'] = move_id.fe_activity_code_id.id
        
        return data
