# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

import datetime, pytz
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

    name = fields.Char( string="Número de Documento" )
    partner_id = fields.Many2one( 'res.partner', string="Empresa" )
    partner_vat = fields.Char( related='partner_id.vat', string="Identification" )
    cfia_project_code = fields.Char( string="Código Proyecto CFIA" )
    exoneration_percentage = fields.Float( string="Porcenaje Exoneración" )
    institution_name = fields.Char( string="Nombre de la Institución" )
    issued_date = fields.Datetime( string="Fecha de la Emisión" )
    expiration_date = fields.Datetime( string="Fecha de Expiración" )
    has_cabys = fields.Boolean( string="Posee Cabys" )
    autorizacion = fields.Char( string="Autorización" )
    
    @api.onchange('name')
    def get_autorizacion(self):
        _logging.info(f"DEF37 self: {self}")
        for record in self:
            _logging.info(f"DEF39 record: {record}")
            _logging.info(f"DEF40 name: {record.name}")
            if record.name:
                _logging.info(f"DEF42 document_number: {record.name}")
                url1 = f"https://api.hacienda.go.cr/fe/ex?autorizacion={record.name}"
                _logging.info(f"DEF44 url1: {url1}")
                response = requests.get(url1, timeout=5)
                
                try:
                    response_json = response.json()
                except:
                    response_json = False
                    continue

                partner_id = self.env['res.partner'].search([('vat','=', response_json.get('identificacion'))])
                if len(partner_id) > 1:
                    partner_id = self.env['res.partner'].search([
                        ('vat','=', response_json.get('identificacion') ),
                        ('child_ids', '!=', False),
                    ])

                if len( partner_id ) == 0:
                    msg = f"No Encontrada la Identificación Física o Jurídica: { response_json.get('identificacion') }"
                    raise ValidationError(msg)

                issued_date = datetime.datetime.fromisoformat( response_json.get('fechaEmision') + '-06:00').astimezone( pytz.timezone('UTC') )
                expiration_date = datetime.datetime.fromisoformat( response_json.get('fechaVencimiento') + '-06:00').astimezone( pytz.timezone('UTC') )

                try:
                    codigo = response_json.get('tipoDocumento').get('codigo')
                except:
                    codigo = False

                record.write({
                    'partner_id': partner_id[0].id or False,
                    'fiscal_position_type': codigo,
                    'cfia_project_code': str(response_json.get('codigoProyectoCFIA') ) or False,
                    'issued_date': issued_date.strftime('%Y-%m-%d %H:%M'),
                    'institution_name': response_json.get('nombreInstitucion') or False,
                    'expiration_date': expiration_date.strftime('%Y-%m-%d %H:%M'),
                    'exoneration_percentage': response_json.get('porcentajeExoneracion') or 0,
                    'has_cabys': response_json.get('poseeCabys') or False,

                })

