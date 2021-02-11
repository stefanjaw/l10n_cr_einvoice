# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError
import logging

log = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = "product.template"

    log.info('--> Class factelec-Product')
    fe_codigo_comercial_tipo = fields.Selection([
        ('01', 'Reference Code from Vendor'),
        ('02', 'Reference Code from Seller'),
        ('03', 'Reference Code Assigned by the Industry'),
        ('04', 'Code used Internally'),
        ('99', 'Other'),
    ], string="Type of the Comercial Code", track_visibility='onchange')

    fe_codigo_comercial_codigo = fields.Char(size = 20, string="Commercial Code" )

    fe_unidad_medida_comercial = fields.Char(string='Unidad de Medida Comercial',size=20)

    cabys_code_id = fields.Many2one('cabys.code', string='Código cabys')

    @api.constrains('name')
    def _constrains_name(self):
        for record in self:
            if len(record.name) > 200:
                raise ValidationError("El nombre del registro no puede ser mayor a 200 caracteres.")
    
    @api.constrains('type')
    def _constrains_type(self):
        service_units = ['Os','Sp','Spe','St']
        for record in self:
            if record.type == 'service':
                    if record.uom_id.uom_mh not in service_units:
                        raise ValidationError(("La unidad de medida {0} no corresponde a una unidad valida para un servicio ! configure el campo Unidad Medida MH en la Unidad {1}".format(record.uom_id.uom_mh,record.uom_id.name)))
