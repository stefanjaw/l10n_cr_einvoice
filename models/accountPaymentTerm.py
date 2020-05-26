from odoo import models, fields, api, _
from odoo.tools.safe_eval import safe_eval
from odoo.exceptions import UserError

class accountPaymentTerm(models.Model):
    _inherit = "account.payment.term"
    account_invoice_refund_ids = fields.One2many(
        string="account_invoice_refund_ids",
        comodel_name="account.move.reversal",
        inverse_name="payment_term_id",
    )