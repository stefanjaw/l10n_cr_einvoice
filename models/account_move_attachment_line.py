from odoo import models, fields, api, exceptions

import logging

log = _logging = logging.getLogger(__name__)

class AccountMoveAttachmentLine(models.Model):
    _name = "account.move.attachment.line"
    _description = "Adjuntos de los asientos contables"

    name = fields.Char("FileName")
    datas = fields.Binary("File")
    move_id = fields.Many2one('account.move', string="Asiento Contable o Factura")
    description = fields.Char("Description")



    