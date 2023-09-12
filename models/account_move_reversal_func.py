from odoo import models, fields, api, _
from odoo.tools.safe_eval import safe_eval
from odoo.exceptions import UserError

import json
import requests

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
        _logger.info(f"DEF19a  refund_method: {self.refund_method}")
        _logger.info(f"DEF19b  context: {self._context}")
        

        data = super(AccountMoveReversal,self)._prepare_default_reversal(move_id)
        
        data['fe_informacion_referencia_codigo'] = self.fe_informacion_referencia_codigo
        _logger.info(f"DEF26 data: {data}")
        
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

        data['name'] = "/"
        
        return data

    def reverse_moves(self):
        _logger.info(f"DEF64 self: {self} self._context: {self._context}\n")
        
        url = f'{self.company_id.fe_url_server}'.replace('/api/v1/billing/','')
        url += '/api/v1/reverse_moves'
        
        doc_fields = [  'id', 'move_ids',
                        'refund_method', 'reason', 'date_mode', 'date',
                        'fe_payment_type', 'payment_term_id', 'fe_receipt_status',
                        'fe_tipo_documento_referencia', 'fe_informacion_referencia_codigo'
                     ]
        data = self.search_read([
            ('id', '=', self.id)
        ],doc_fields)
        _logger.info(f"DEF83 data: {data}")

        if len(data) != 1:
            raise ValidationError("Error: Multiple Records Found: {data}")
        else:
            data = data[0]

        active_id = self._context.get('active_id')
        _logger.info(f"DEF74 active_id: {active_id}\n")
        if active_id:
            move_id = self.env['account.move'].browse(active_id)
            data['fe_consecutivo'] = move_id.name
            data['fe_clave'] = move_id.fe_clave
            
        #data['move_id'] = self.partner_id.country_id.code
        _logger.info(f"DEF90 data: {data}")
        
        
        #raise UserError("STOP90")
        
        header = { 'Content-Type': 'application/json', }
        response = requests.post(url,
                        headers = header,
                        data = json.dumps(data, default=str),
                        timeout=15)
        _logger.info(f"DEF84 response: {response}\n{response.json()}")
        
        try:
            msg_errors = response.json().get('result').get('is_valid')
        except:
            raise ValidationError(f"Error Server-Side: \n{response.text}")
        
        _logger.info(f"DEF109 msg_errors: {msg_errors}")
        msg = ""
        if len(msg_errors) > 0:
            for msg_error in msg_errors:
                msg += msg_error + "\n"
            raise UserError(f"Errores:\n{msg}")
        action = super(AccountMoveReversal, self).reverse_moves()
        return action
        