from odoo import api, fields, models, _

class accountMoveDebit(models.TransientModel):
    _name = "account.move.debit"
    _description = "Debit Note"
    fe_reason = fields.Char(string="reason", )
    journal_id = fields.Many2one("account.journal", string="Journal")


    def add_note(self):
        id = self.env.context.get('active_id')
        doc_ref = self.env.context.get('doc_ref')
        copy = self.env['account.move'].browse(id).copy({'debit_note':True,
                                                         'journal_id':self.journal_id.id,
                                                         'ref':self.fe_reason,
                                                         'fe_doc_ref':doc_ref})
        return {
            'name': _("Debit Notes"),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id':copy.id,
            'view_type': 'form',
            'view_mode': 'form',
        }