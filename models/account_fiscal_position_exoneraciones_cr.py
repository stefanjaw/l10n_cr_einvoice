# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

import requests
import logging
_logging = _logger = logging.getLogger(__name__)

class AccountFiscalPositionExoneracionesCR(models.Model):
    _name = "account.fiscal.position.exoneraciones_cr"
    _description = "Exoneraciones Hacienda para Costa Rica"

    fiscal_position_type = fields.Selection([
        ('01', 'Compras autorizadas'),
        ('02', 'Ventas exentas a diplomáticos'),
        ('03', 'Autorizado por Ley especial'),
        ('04', 'Exenciones Dirección General de Hacienda'),
        ('05', 'Transitorio V'),
        ('06', 'Transitorio IX'),
        ('07', 'Transitorio XVII'),
        ('99', 'Otros'),
    ], string="Tipo de Documento")

    document_number = fields.Char( string="Número de Documento" )
    partner_id = fields.Many2one( 'res.partner', string="Empresa" )
    partner_vat = fields.Char( related='partner_id.vat', string="Identification" )
    cfia_project_code = fields.Char( string="Código Proyecto CFIA" )
    exoneration_percentage = fields.Float( string="Porcenaje Exoneración" )
    institution_name = fields.Char( string="Nombre de la Institución" )
    issued_date = fields.Datetime( string="Fecha de la Emisión" )
    expiration_date = fields.Datetime( string="Fecha de Expiración" )
    has_cabys = fields.Boolean( string="Posee Cabys" )
    
    api.onchange('document_number')
    def get_autorizacion(self):
        for record in self:
            url1 = f"https://api.hacienda.go.cr/fe/ex?autorizacion={record.document_number}"
            response = requests.get(url1, timeout=5)
            _logging.info(f"DEF40 response: {response.json()}")
        _logging.info(f"DEF35 autoriacion: {autorizacion}")
        STOP35


