from odoo import api, exceptions, fields, models, _
from odoo.exceptions import ValidationError
from lxml.etree import Element, fromstring, parse, tostring, XMLParser
from datetime import datetime,timezone
from .xslt import __path__ as path
import lxml.etree as ET
import xmltodict
import re
import logging
import base64
import pytz
import json
import requests
from io import BytesIO

log = logging.getLogger(__name__)
_logger = logging.getLogger(__name__)


class ElectronicDoc(models.Model):

    _name = 'electronic.doc'
    _rec_name = 'display_name'
    _inherit = ['mail.thread']
    
    invoice_id = fields.Many2one('account.move', string='Invoice',readonly = True,)
    key = fields.Char(string="Clave")
    consecutivo = fields.Char(string="Consecutivo")
    electronic_doc_bill_number = fields.Char(string="Numero Factura", )

    provider = fields.Char(string="Proveedor", )
    provider_vat = fields.Char(string="Proveedor Identificacion", )
    provider_vat_type = fields.Selection(
         string="ProveedorTipo Identificacion",
         selection=[
                 ('01', 'Cédula Física'),
                 ('02', 'Cédula Jurídica'),
                 ('03','DIMEX'),
                 ('04','NITE')
         ],
    )
    
    receiver_number = fields.Char(string="Identificacion del Receptor", )
    receiver_name = fields.Char(string="Receptor", )

    xml_bill = fields.Binary(string="Factura Electronica", )
    xml_bill_name = fields.Char(string="Nombre Factura Electronica", )

    xml_acceptance = fields.Binary(string="Aceptacion de hacienda", )
    xml_acceptance_name = fields.Char(string="Nombre Aceptacion hacienda", )

    has_acceptance = fields.Boolean(string="Tiene aceptacion de hacienda",
                                    compute='_compute_has_acceptance')
    date = fields.Date(string="Fecha", )

    doc_type = fields.Selection(string='Tipo',
                                selection=[
                                    ('TE', 'Tiquete Electronico'),
                                    ('FE', 'Factura Electronica'),
                                    ('NC', 'Nota Crédito Electronica'),
                                    ('MH', 'Aceptacion Ministerio Hacienda'),
                                    ('OT', 'Otro'),
                                ])


    state = fields.Selection(selection=[
            ('draft', 'Draft'),
            ('posted', 'Posted'),
            ('accounting', 'Accounting')
        ], string='Status', required=True, readonly=True, copy=False, tracking=True,
        default='draft')

    fe_server_state = fields.Char(string="Estado Hacienda", )
    
    total_amount = fields.Float(string="Monto Total", )

    xslt = fields.Html(string="Representacion Grafica", )

    fe_msg_type = fields.Selection([ # 1570035130
            ('1', 'Aceptado'),
            ('2', 'Aceptación parcial'),
            ('3', 'Rechazado'),
        ], string="Mensaje", track_visibility="onchange",)

    fe_detail_msg = fields.Text(string="Detalle Mensaje", size=80, copy=False,)# 1570035143
    
    sequence_id = fields.Many2one('ir.sequence', string='Secuencia')
    fe_name_pdf = fields.Char(string="nombre pdf", )
    fe_pdf = fields.Binary(string="pdf", )
    fe_name_xml_sign = fields.Char(string="nombre xml firmado", )
    fe_xml_sign = fields.Binary(string="XML firmado", )
    fe_name_xml_hacienda = fields.Char(string="nombre xml hacienda", )
    fe_xml_hacienda = fields.Binary(string="XML Hacienda", )# 1570034790
    fe_server_state = fields.Char(string="Estado Hacienda", )
    company_id = fields.Many2one(
        'res.company',
        'Company',
         default=lambda self: self.env.company.id,
    )
    
    fe_monto_total_impuesto = fields.Float(string="Monto Total Impuesto", )
    fe_condicio_impuesto =fields.Selection([ # 1570035130
            ('01', 'General Credito IVA'),
            ('02', 'General Crédito parcial del IVA'),
            ('03', 'Bienes de Capital'),
            ('04', 'Gasto corriente no genera crédito'),
            ('05', 'Proporcionalidad'),
        ], string="Condición Impuesto", track_visibility="onchange",)
    
    fe_monto_total_impuesto_acreditar = fields.Float(string="Monto Total Impuesto Acreditar",compute = '_compute_impuesto_acreditar' )
    fe_monto_total_gasto_aplicable = fields.Float(string="Monto Total De Gasto Aplicable",compute = '_compute_gasto_aplicable' )
    fe_actividad_economica = fields.Many2one('activity.code',string='Actividad Económica')
    line_ids = fields.One2many('electronic.doc.line', 'electronic_doc_id', string='Lineas', copy=True,ondelete="cascade",)
    currency_id = fields.Many2one('res.currency', string='Moneda')
    currency_exchange = fields.Float(string="Tipo de Cambio")
    display_name = fields.Char(
        string='Name',
        compute='_compute_display_name',
    )
    
    fe_hacienda_json = fields.Text(string="Hacienda JSON",copy=False )
    
    _sql_constraints = [
        ('unique_key', 'UNIQUE(key)',
         'El documento ya existe en la base de datos!!'),
    ]
    
    @api.depends("line_ids" )
    def _compute_gasto_aplicable(self):
        for record in self:
            gasto = 0
            for line in record.line_ids:
                if line.is_selected:
                    gasto = gasto + line.price_subtotal
            self.fe_monto_total_gasto_aplicable = gasto
            
    @api.depends("line_ids" )
    def _compute_impuesto_acreditar(self):
        for record in self:
            impuesto = 0
            for line in record.line_ids:
                if line.is_selected:
                    impuesto = impuesto + line.tax_amount
            self.fe_monto_total_impuesto_acreditar = impuesto
            
    @api.depends('key', 'provider', 'date')
    def _compute_display_name(self):
        for record in self:
            record.display_name = '{0} {1} {2}'.format(record.date, record.provider, record.key)


    @api.depends('xml_acceptance')
    def _compute_has_acceptance(self):
        for record in self:
            if record.xml_acceptance:
                record.has_acceptance = True
            else:
                record.has_acceptance = False
