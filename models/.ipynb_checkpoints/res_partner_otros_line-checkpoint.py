from odoo import models, fields, api, exceptions

import logging

log = _logging = logging.getLogger(__name__)

class AccountMoveOtrosLine(models.Model):
    _name = "res.partner.otros.line"
    _description = "res.partner.otros.line"

    field_type = fields.Selection([
        ('OtroTexto', 'Otro Texto'),
        ('OtroContenido', 'Otro Contenido')
    ], string="Tipo de Otros", required=True)
    attributes_data = fields.Char(string="Atributos y valores")
    field_data = fields.Char()
    partner_id = fields.Many2one('res.partner')
    move_type = fields.Selection([
        ('out_invoice', 'Factura'),
        ('out_refund', 'Nota de Crédito')
    ])

