from odoo import models, fields, api, exceptions

import logging

log = _logging = logging.getLogger(__name__)

class AccountMoveOtrosLine(models.Model):
    _name = "account.move.otros.line"
    _description = "Otros Lineas"

    field_type = fields.Selection([
        ('OtroTexto', 'Otro Texto'),
        ('OtroContenido', 'Otro Contenido')
    ], string="Tipo de Otros", required=True)
    attributes_data = fields.Char(string="Atributos y valores")
    field_data = fields.Char()
    move_id = fields.Many2one('account.move')

