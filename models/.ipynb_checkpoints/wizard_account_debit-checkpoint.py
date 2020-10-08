from odoo import api, fields, models, _

class accountMoveDebit(models.TransientModel):
    _name = "account.move.debit"
    _description = "Debit Note"
    fe_reason = fields.Char(string="reason", )
    journal_id = fields.Many2one("account.journal", string="Journal")


    def add_note(self):
        Invoice = self.env['account.move']
        invoice_id = Invoice.browse(self.env.context.get('active_id'))

        debit_note = Invoice.create({
            'partner_id': invoice_id.partner_id.id,
            'journal_id': self.journal_id.id,
            'name':self.fe_reason,
            'origin': invoice_id.number or "",
            'type': 'out_invoice',
            'debit_note': True
        })

        return {
            'name': _("Debit Notes"),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', [debit_note.id])],
            'context': {
                'tree_view_ref': 'account.view_invoice_tree',
                'form_view_ref': 'account.view_move_form',
            }
        }