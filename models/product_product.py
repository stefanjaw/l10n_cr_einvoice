# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
import logging

log = logging.getLogger(__name__)

class productProduct(models.Model):
    _inherit = 'product.product'
    fe_codigo_comercial_tipo = fields.Selection([
        ('01', 'Reference Code from Vendor'),
        ('02', 'Reference Code from Seller'),
        ('03', 'Reference Code Assigned by the Industry'),
        ('04', 'Code used Internally'),
        ('99', 'Other'),
    ], string="Type of the Comercial Code", track_visibility='onchange',
    compute="_compute_fe_codigo_comercial_tipo",inverse="_set_fe_codigo_comercial_tipo")

    fe_codigo_comercial_codigo = fields.Char(size = 20, string="Commercial Code",compute='_compute_fe_codigo_comercial_codigo',
    inverse="_set_fe_codigo_comercial_codigo" )

    fe_unidad_medida_comercial = fields.Char(string='Unidad de Medida Comercial',size=20,compute='_compute_fe_unidad_comercial',
    inverse="_set_fe_unidad_comercial")

    cabys_code_id = fields.Many2one('cabys.code', string='Código cabys',compute='_compute_cabys_code_id',
    inverse='_set_cabys_code')

    @api.depends('product_tmpl_id', 'product_tmpl_id.cabys_code_id')
    def _compute_cabys_code_id(self):
        for record in self:
                record.cabys_code_id = record.product_tmpl_id.cabys_code_id
                
    def _set_cabys_code(self):
        self.product_tmpl_id.cabys_code_id = self.cabys_code_id
    
    @api.depends('product_tmpl_id', 'product_tmpl_id.fe_unidad_medida_comercial')
    def _compute_fe_unidad_comercial(self):
        for record in self:
            if len(record.product_tmpl_id.product_variant_ids) == 1:
                record.fe_unidad_medida_comercial = record.product_tmpl_id.fe_unidad_medida_comercial
            else:
                record.fe_unidad_medida_comercial = record.fe_unidad_medida_comercial

    def _set_fe_unidad_comercial(self):
        if len(self.product_tmpl_id.product_variant_ids) == 1:
            self.product_tmpl_id.fe_unidad_medida_comercial = self.fe_unidad_medida_comercial
        else:
            self.product_tmpl_id.fe_unidad_medida_comercial =  self.product_tmpl_id.fe_unidad_medida_comercial

    @api.depends('product_tmpl_id', 'product_tmpl_id.fe_codigo_comercial_codigo')
    def _compute_fe_codigo_comercial_codigo(self):
        for record in self:
            if len(record.product_tmpl_id.product_variant_ids) == 1:
                record.fe_codigo_comercial_codigo = record.product_tmpl_id.fe_codigo_comercial_codigo
            else:
                record.fe_codigo_comercial_codigo = record.fe_codigo_comercial_codigo

    def _set_fe_codigo_comercial_codigo(self):
        if len(self.product_tmpl_id.product_variant_ids) == 1:
            self.product_tmpl_id.fe_codigo_comercial_codigo = self.fe_codigo_comercial_codigo
        else:
            self.product_tmpl_id.fe_codigo_comercial_codigo = self.product_tmpl_id.fe_codigo_comercial_codigo

    @api.depends('product_tmpl_id', 'product_tmpl_id.fe_codigo_comercial_tipo')
    def _compute_fe_codigo_comercial_tipo(self):
        for record in self:
            if len(record.product_tmpl_id.product_variant_ids) == 1:
                record.fe_codigo_comercial_tipo = record.product_tmpl_id.fe_codigo_comercial_tipo
            else:
                record.fe_codigo_comercial_tipo = record.fe_codigo_comercial_tipo

    def _set_fe_codigo_comercial_tipo(self):
        if len(self.product_tmpl_id.product_variant_ids) == 1:
            self.product_tmpl_id.fe_codigo_comercial_tipo = self.fe_codigo_comercial_tipo
        else:
            self.product_tmpl_id.fe_codigo_comercial_tipo = self.product_tmpl_id.fe_codigo_comercial_tipo

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
                        raise ValidationError(("La unidad de medida {0} no corresponde a una unidad valida para un servicio ! configure el campo Unidad Medida MH en la Unidad {1}".format(record.product_uom_id.uom_mh,record.product_uom_id.name)))


    