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
    def otro_xml_str_update(self):
        for record in self:
            if record.field_type:
                xml_str = f"<{record.field_type} {record.attributes_data or ''}>{record.field_data or ''}</{record.field_type}>"
                _logger.info(f"DEF24 --- xml_str: { xml_str }")
                record.otro_xml_str = xml_str
        return
