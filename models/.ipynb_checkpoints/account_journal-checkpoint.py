from odoo import models, fields, api

class accountJournal(models.Model):
    _inherit = "account.journal"
    electronic_doc_ids = fields.One2many('electronic.doc', 'journal_id')
