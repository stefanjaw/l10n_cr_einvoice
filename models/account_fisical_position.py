# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

import json
import requests

import logging
_logging = _logger = logging.getLogger(__name__)

class AccountFiscalPosition(models.Model):
    _inherit = "account.fiscal.position"

    document_number = fields.Char(string="Número de Documento")
    fiscal_position_type = fields.Selection([
        ('01', '01-Compras autorizadas por la Dirección General de Tributación'),
        ('02', '02-Ventas exentas a diplomáticos'),
        ('03', '03-Autorizado por Ley especial'),
        ('04', '04-Exenciones Dirección General de Hacienda Autorización Local Genérica'),
        ('05', '05-Exenciones Dirección General de Hacienda Transitorio V (servicios de ingeniería, arquitectura, topografía obra civil)'),
        ('06', '06-Servicios turísticos inscritos ante el Instituto Costarricense de Turismo (ICT)'),
        ('07', '07-Transitorio XVII (Recolección, Clasificación, almacenamiento de Reciclaje y reutilizable)'),
        ('08', '08-Exoneración a Zona Franca'),
        ('09', '09-Exoneración de servicios complementarios para la exportación articulo 11 RLIVA'),
        ('10', '10-Órgano de las corporaciones municipales'),
        ('11', '11-Exenciones Dirección General de Hacienda Autorización de Impuesto Local Concreta'),
        ('99', '99-Otros')
    ], string="Tipo de Documento")

    fe_tipo_documento_otro = fields.Char(string="Tipo de Documento Otro")

    fe_exoneracion_articulo = fields.Char(string="Articulo")

    fe_exoneracion_inciso = fields.Char(string="Inciso")
    
    institution_name = fields.Char(string="Nombre de la Institución Otro")
    
    fe_codigo_institucion = fields.Selection([
        ('01', '01-Ministerio de Hacienda'),
        ('02', '02-Ministerio de Relaciones Exteriores y Culto'),
        ('03', '03-Ministerio de Agricultura y Ganadería'),
        ('04', '04-Ministerio de Economía, Industria y Comercio'),
        ('05', '05-Cruz Roja Costarricense'),
        ('06', '06-Benemérito Cuerpo de Bomberos de Costa Rica'),
        ('07', '07-Asociación Obras del Espíritu Santo'),
        ('08', '08-Federación Cruzada Nacional de protección al Anciano(Fecrunapa)'),
        ('09', '09-Escuela de Agricultura de la Región Húmeda (EARTH)'),
        ('10', '10-Instituto Centroamericano de Administración de Empresas(INCAE)'),
        ('11', '11-Junta de Protección Social (JPS)'),
        ('12', '12-Autoridad Reguladora de los Servicios Públicos (Aresep)'),
        ('99', '99-Otros')
    ], string="Código de la institución")
    
    issued_date = fields.Date(string="Fecha de la Emisión")
    
    fe_expiration_date = fields.Date(string="Fecha de Expiración")
    fe_document_txt = fields.Text(string="Información del Documento")

    fe_exoneracion_porcentaje = fields.Float(string="Porcentaje Exoneracion")
    fe_exoneracion_type = fields.Char(string="Tipo de Exoneración")

    fe_exoneracion_identificacion = fields.Char(string="Identificación para la Exoneración")
    
    @api.constrains('tax_ids')
    def _constrains_tax_ids(self):
        for record in self:
            if len(self.tax_ids) == 0:
                raise ValidationError('En Mapeo de impuestos debe de existir al menos una linea')

    @api.onchange('document_number')
    def action_fiscal_position_cr_data_update(self):
        _logger.info(f"Querying Fiscal Positions of Costa Rica ======")

        fields_values_none = {
            'fiscal_position_type': None,
            'issued_date': None,
            'institution_name': None,
            'fe_expiration_date': None,
            'fe_exoneracion_porcentaje': None,
            'fe_exoneracion_type': None
        }        
        header = {'Content-Type':'application/json'}
        
        for record in self:
            autorizacion = self.document_number
            if autorizacion:
                url = f"https://api.hacienda.go.cr/fe/ex?autorizacion={autorizacion.lower()}"
                
                try:
                    response = requests.get(url, headers = header, timeout=5)
                except Exception as e:
                    fe_document_txt = f"Servidor del Gobierno No responde {autorizacion}\n\n{str(e)[98:]}"
                    data = {
                        'fe_document_txt': fe_document_txt,
                    }
                    data.update( fields_values_none )
                    
                    record.update( data )
                    continue
                
                try:
                    response_json = response.json()
                    fe_document_txt = json.dumps( response_json, indent=4)
                except:
                    fe_document_txt = f"No encontrado el Documento {autorizacion}\n\n{response.text}"
                    data = {
                        'fe_document_txt': fe_document_txt,
                    }
                    data.update( fields_values_none )
                    
                    record.update( data )
                    continue

                if response_json.get('code') in [400, "400"]:
                    data = {
                        'fe_document_txt': fe_document_txt,
                    }
                    data.update( fields_values_none )
                    record.update( data )
                    continue

                data_dict = {
                    'fe_document_txt': json.dumps( response_json, indent=4),
                }

                tipoDocumento = response_json.get('tipoDocumento')
                if tipoDocumento:
                    codigo = tipoDocumento.get('codigo')
                    if codigo:
                        data_dict.update({
                            'fiscal_position_type': codigo
                        })

                data_dict = self.data_add_value(
                    response_json,data_dict,'identificacion','fe_exoneracion_identificacion' )
                
                data_dict = self.data_add_value(
                    response_json,data_dict,'fechaEmision','issued_date' )
                
                data_dict = self.data_add_value( 
                    response_json,data_dict,'nombreInstitucion','institution_name' )

                data_dict = self.data_add_value( 
                    response_json,data_dict,'CodigoInstitucion','fe_codigo_institucion' )
                
                data_dict = self.data_add_value(
                    response_json,data_dict,'fechaVencimiento','fe_expiration_date' )

                data_dict = self.data_add_value(
                    response_json,data_dict,'porcentajeExoneracion','fe_exoneracion_porcentaje' )

                data_dict = self.data_add_value(
                    response_json,data_dict,'tipoAutorizacion','fe_exoneracion_type' )
                
                record.update( data_dict )
        return

    def data_add_value( self, response_json, data_dict, key_name, field_name):
        key_value = response_json.get(key_name)
        if key_value:
            data_dict.update({
                field_name: key_value
            })
        return data_dict