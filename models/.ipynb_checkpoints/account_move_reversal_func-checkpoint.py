from odoo import models, fields, api, _
from odoo.tools.safe_eval import safe_eval
from odoo.exceptions import UserError
        
class AccountMoveReversal(models.TransientModel):
    _inherit = "account.move.reversal"
    
    @api.depends('company_id')
    def _get_country_code(self):
        for s in self:
            s.fe_current_country_company_code = s.company_id.country_id.code 
    
    
    def _prepare_default_reversal(self, move):
        
        return {
            'ref': _('Reversal of: %s, %s') % (move.name, self.reason) if self.reason else _('Reversal of: %s') % (move.name),
            'date': self.date or move.date,
            'invoice_date': move.is_invoice(include_receipts=True) and (self.date or move.date) or False,
            'journal_id': self.journal_id and self.journal_id.id or move.journal_id.id,
            'auto_post': True if self.date > fields.Date.context_today(self) else False,
            'invoice_user_id': move.invoice_user_id.id,
            'invoice_payment_term_id': self.payment_term_id.id,
            'fe_payment_type':self.fe_payment_type,
            'fe_receipt_status':self.fe_receipt_status,
            'fe_activity_code_id':self.fe_activity_code_id.id,
            'fe_tipo_documento_referencia':self.fe_tipo_documento_referencia,
            'fe_informacion_referencia_codigo':self.fe_informacion_referencia_codigo,
            'fe_doc_ref': move.name,
            'fe_server_state':None,
            'fe_xml_sign':None,
            'fe_xml_hacienda':None
        }