from odoo import models, fields, api, exceptions

import logging

log = _logger = _logging = logging.getLogger(__name__)

class AccountMoveOtrosLine(models.Model):
    _name = "account.move.otros.line"
    _description = "Otros Lineas"
    
    field_type = fields.Selection([
        ('OtroTexto', 'Otro Texto'),
        ('OtroContenido', 'Otro Contenido')
    ], string="Tipo de Otros", required=True)
    attributes_data = fields.Char(string="Atributos y valores")
    field_data = fields.Char()
    otro_xml_str = fields.Char()
    move_id = fields.Many2one('account.move')

    @api.onchange('field_type', 'attributes_data', 'field_data')
    def testing(self):
        for record in self:
            xml_str = f"<{record.field_type} {record.attributes_data or None}>{record.field_data}</{record.field_type}>"
            record.otro_xml_str = xml_str
        return
    
    # def write(self, vals):
    #     _logger.info(f"DEF21 self: {self}\nwrite vals:\n{vals}")
    #     for record in self
    #         STOP23
    #     STOP25
