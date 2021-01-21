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


class ElectronicDoc(models.Model):

    _name = 'electronic.doc'
    _rec_name = 'display_name'
    _inherit = ['mail.thread']
    
    invoice_id = fields.Many2one('account.move', string='Invoice',readonly = True,)
    key = fields.Char(string="Clave")
    consecutivo = fields.Char(string="Consecutivo")
    electronic_doc_bill_number = fields.Char(string="Numero Factura", )

    provider = fields.Char(string="Proveedor", )
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
            ('1', 'Accept'),
            ('2', 'Partially Accept'),
            ('3', 'Reject'),
        ], string="Mensaje", track_visibility="onchange",)

    fe_detail_msg = fields.Text(string="Detalle Mensaje", size=80, copy=False,)# 1570035143
    
    sequence_id = fields.Many2one('ir.sequence', string='Secuencia')
    
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
    display_name = fields.Char(
        string='Name',
        compute='_compute_display_name',
    )
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
            
    @api.onchange('line_ids')
    def _onchange_line_ids(self):
        for record in self:
            impuesto = 0
            for line in record.line_ids:
                if line.is_selected:
                    impuesto = impuesto + line.tax_amount
            self.fe_monto_total_impuesto_acreditar = impuesto

    @api.onchange("sequence_id")
    def _onchange_sequence_id(self):
        if self.sequence_id:
            if self.sequence_id.prefix[8:10] == '05':
                self.update({'fe_msg_type':'1'})
            elif self.sequence_id.prefix[8:10] == '06':
                self.update({'fe_msg_type':'2'})
            elif self.sequence_id.prefix[8:10] == '07':
                self.update({'fe_msg_type':'3'})
        
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


    @api.onchange("xml_bill")
    def _onchange_load_xml(self):
        if self.xml_bill:
            if '.xml' in self.xml_bill_name.lower():
                dic = self.convert_xml_to_dic(self.xml_bill)
                doc_type = self.get_doc_type(dic)
                if doc_type == 'TE' or doc_type == 'FE' or doc_type == 'NC':
                    list_lineas = self.crear_lineas_xml(self.xml_bill)
                    xml_currency = self.get_currency(dic, doc_type)
                    currency_id = self.env['res.currency'].search([('name','=',xml_currency)])
                    self.write({
                        'key':self.get_key(dic, doc_type),
                        'xslt':self.transform_to_xslt(self.xml_bill, doc_type),
                        'currency_id':currency_id,
                        'electronic_doc_bill_number':self.get_bill_number(dic, doc_type),
                        'date':self.get_date(dic, doc_type),
                        'doc_type':doc_type,
                        'provider':self.get_provider(dic, doc_type),
                        'receiver_name':self.get_receiver_name(dic, doc_type) or self.env.user.company_id.name,
                        'receiver_number':self.get_receiver_identification(dic, doc_type) or self.env.user.company_id.vat,
                        'total_amount':self.get_total_amount(dic, doc_type).replace(',','.'),
                        'fe_monto_total_impuesto':self.get_total_tax(dic, doc_type).replace(',','.'),
                        'line_ids':list_lineas,
                    })
                                        
                else:
                    return {
                    'warning': {
                    'title': 'Atencion!',
                    'message': 'el documento que ingreso no corresponde a una factura o tiquete electronico!!'
                    },
                        'value': {
                            'key': None,
                            'electronic_doc_bill_number': None,
                            'provider': None,
                            'receiver_number': None,
                            'receiver_name': None,
                            'xml_bill': None,
                            'xml_bill_name': None,
                            'xml_acceptance': None,
                            'xml_acceptance_name': None,
                            'date': None,
                            'doc_type': None,
                            'total_amount': None,
                            'xslt': None,
                            'odoo_bill': None
                        }
                    }

            else:
                 return {
                    'warning': {
                    'title': 'Atencion!',
                    'message': 'el documento que ingreso no corresponde a un archivo XML!!'
                    },
                        'value': {
                            'key': None,
                            'electronic_doc_bill_number': None,
                            'provider': None,
                            'receiver_number': None,
                            'receiver_name': None,
                            'xml_bill': None,
                            'xml_bill_name': None,
                            'xml_acceptance': None,
                            'xml_acceptance_name': None,
                            'date': None,
                            'doc_type': None,
                            'total_amount': None,
                            'xslt': None,
                            'odoo_bill': None
                        }
                    }
        else:
            return{
                'value': {
                            'key': None,
                            'electronic_doc_bill_number': None,
                            'provider': None,
                            'receiver_number': None,
                            'receiver_name': None,
                            'xml_bill': None,
                            'xml_bill_name': None,
                            'xml_acceptance': None,
                            'xml_acceptance_name': None,
                            'date': None,
                            'doc_type': None,
                            'total_amount': None,
                            'xslt': None,
                            'odoo_bill': None
                        }
            }

    def validar_xml_aceptacion(self):
         for record in self:
            if record.xml_acceptance:
                if '.xml' in record.xml_acceptance_name.lower():
                    dic = record.convert_xml_to_dic(record.xml_acceptance)
                    doc_type = record.get_doc_type(dic)
                    if doc_type != 'MH':
                        raise ValidationError(
                            _("El documento de Aceptacion del Ministerio de Hacienda no tiene un formato valido!"
                              ))
                    else:
                        key = record.get_key(dic, doc_type)
                        if key != record.key:
                            raise ValidationError(
                                _("El documento de Aceptacion del Ministerio de Hacienda no corresponde para esta factura o tiquete electronico"
                                  ))
                else:
                    raise ValidationError(
                        _("El documento de Aceptacion del Ministerio de Hacienda No corresponde a un archivo xml!!"
                          ))
                    
    def agregar_contabilidad(self):
        
        if self.state == 'draft':
            raise ValidationError("Primero confirme este documento")
        if self.state == 'accounting':
            raise ValidationError("Este documento ya fue agregado en contabilidad")
        if self.sequence_id.prefix[8:10] == '07':
            raise ValidationError("Este documento no se puede agregar a contabilidad por que se rechazó previamente")
            
        if self.state != 'draft' and self.state != 'accounting' and self.sequence_id.prefix[8:10] != '07':
            return {
                    'type': 'ir.actions.act_window',
                    'name': 'Agregar documento a contabilidad',
                    'res_model': 'wizard.agregar.contabilidad',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'views': [(False, 'form')],
                    'target': 'new',
                    'context': {
                        'doc': self.id,
                        'xml':self.xml_bill,
                     }
                 }                                       

                    
    def confirmar(self):
        self.validar_xml_aceptacion
        if self.sequence_id:
            next_number = self.sequence_id.next_by_id()
            self.update({
                'consecutivo':next_number,
                'sequence_id':self.sequence_id,
                'fe_msg_type':self.fe_msg_type,
                'fe_detail_msg':self.fe_detail_msg,
                'state':'posted'
            }) 

    def _get_namespace(self, xml):
        name = ""
        form = re.match('\{.*\}', xml.tag)
        if form:
            name = form.group(0).split('}')[0].strip('{')
        return {'xmlns': name}

    def crear_lineas_xml(self,xml):
            root_xml = fromstring(base64.b64decode(xml))
            ds = "http://www.w3.org/2000/09/xmldsig#"
            xades = "http://uri.etsi.org/01903/v1.3.2#"
            ns2 = {"ds": ds, "xades": xades}
            signature = root_xml.xpath("//ds:Signature", namespaces=ns2)[0]
            namespace = self.env['electronic.doc']._get_namespace(root_xml)

            lineasDetalle = root_xml.xpath(
                    "xmlns:DetalleServicio/xmlns:LineaDetalle", namespaces=namespace)
            invoice_lines = []   
            account = self.env['account.account'].search([("code","=","0-511301"),("company_id","=",self.company_id.id)])
            if not account:
                  account = self.env['account.account'].search([("company_id","=",self.company_id.id)])[0]

            for linea in lineasDetalle: 
                    percent = linea.xpath("xmlns:Impuesto/xmlns:Tarifa", namespaces=namespace)
                    tax = False
                    if percent:
                        tax = self.env['account.tax'].search([("type_tax_use","=","purchase"),("amount","=",percent[0].text.replace(',','.')),("company_id","=",self.company_id.id)])
                        if tax:
                            if len(tax)>1:
                                tax = tax[0]
                            tax = [(6,0,[tax.id])]
                    obj =  {
                            'name': linea.xpath("xmlns:Detalle", namespaces=namespace)[0].text,
                            'tax_ids': tax,
                            'account_id': account.id,
                            'quantity': linea.xpath("xmlns:Cantidad", namespaces=namespace)[0].text.replace(',','.'),
                            'price_unit':linea.xpath("xmlns:PrecioUnitario", namespaces=namespace)[0].text.replace(',','.'),
                            }

                    line =  [0,0,obj]                
                    invoice_lines.append(line)

            otros_cargos = root_xml.xpath("xmlns:OtrosCargos", namespaces=namespace)
            for otro in otros_cargos:
                new_line =  [0, 0, {'name': otro.xpath("xmlns:Detalle", namespaces=namespace)[0].text,
                                        'tax_ids': False,
                                        'account_id': account.id,
                                        'quantity': '1',
                                        'price_unit':otro.xpath("xmlns:MontoCargo", namespaces=namespace)[0].text,
                                       }]
                invoice_lines.append(new_line)

            return invoice_lines
        
    def cargar_lineas_xml(self,xml,company_id=False):
            root_xml = fromstring(base64.b64decode(xml))
            ds = "http://www.w3.org/2000/09/xmldsig#"
            xades = "http://uri.etsi.org/01903/v1.3.2#"
            ns2 = {"ds": ds, "xades": xades}
            signature = root_xml.xpath("//ds:Signature", namespaces=ns2)[0]
            namespace = self.env['electronic.doc']._get_namespace(root_xml)

            lineasDetalle = root_xml.xpath(
                    "xmlns:DetalleServicio/xmlns:LineaDetalle", namespaces=namespace)
            invoice_lines = []   
            account = self.env['account.account'].search([("code","=","0-511301"),("company_id","=",company_id.id)])
                
                
            for linea in lineasDetalle: 
                    percent = linea.xpath("xmlns:Impuesto/xmlns:Tarifa", namespaces=namespace)
                    tax = False
                    if percent:
                        tax = self.env['account.tax'].search([("type_tax_use","=","purchase"),("amount","=",percent[0].text.replace(',','.')),("company_id","=",company_id.id)])
                        if tax:
                            if len(tax)>1:
                                tax = tax[0]
                            tax = [(6,0,[tax.id])]
                    new_line =  [0, 0, {'name': linea.xpath("xmlns:Detalle", namespaces=namespace)[0].text,
                                        'tax_ids': tax,
                                        'account_id': account.id,
                                        'quantity': linea.xpath("xmlns:Cantidad", namespaces=namespace)[0].text.replace(',','.'),
                                        'price_unit':linea.xpath("xmlns:PrecioUnitario", namespaces=namespace)[0].text.replace(',','.'),
                                       }]
                    invoice_lines.append(new_line)

            otros_cargos = root_xml.xpath("xmlns:OtrosCargos", namespaces=namespace)
            for otro in otros_cargos:
                new_line =  [0, 0, {'name': otro.xpath("xmlns:Detalle", namespaces=namespace)[0].text.replace(',','.'),
                                        'tax_ids': False,
                                        'account_id': account.id,
                                        'quantity': '1',
                                        'price_unit':otro.xpath("xmlns:MontoCargo", namespaces=namespace)[0].text.replace(',','.'),
                                       }]
                invoice_lines.append(new_line)
            

            return invoice_lines
        
    def create_electronic_doc(self, xml, xml_name,company=False):

        dic = self.convert_xml_to_dic(xml)
        doc_type = self.get_doc_type(dic)

        key = self.get_key(dic, doc_type)

        electronic_doc = self.env['electronic.doc']
        "UC07"
        if (not electronic_doc.search([('key', '=', key),
                                       ('doc_type', '=', doc_type)])):
            "UC05A"
            provider = self.get_provider(dic, doc_type)
            receiver_number = self.get_receiver_identification(dic, doc_type) or company.vat or False
            receiver_name = self.get_receiver_name(dic, doc_type) or company.name or False
            bill_number = self.get_bill_number(dic, doc_type) 
            xml_bill = xml
            xml_bill_name = xml_name
            date = self.get_date(dic, doc_type)
            total_amount = self.get_total_amount(dic, doc_type).replace(',','.')
            fe_monto_total_impuesto = self.get_total_tax(dic, doc_type).replace(',','.')
            xml_currency = self.get_currency(dic, doc_type)
            currency_id = self.env['res.currency'].search([('name','=',xml_currency)])
            
            "UC05C"
            xslt = self.transform_to_xslt(xml, doc_type)
            if (not receiver_number):
                receiver_number = ''
                log.info(
                    '\n "el documento XML Clave: %s no contiene numero del receptor \n',
                    key)
            "UC05C"
            if not receiver_name:
                receiver_name = ''
                log.info(
                    '\n "el documento XML Clave: %s no contiene nombre del receptor \n',
                    key)
             
            invoice_lines = self.cargar_lineas_xml(xml,company) 
                 
            comprobante = electronic_doc.create({
                'key': key,
                'provider': provider,
                'currency_id':currency_id.id,
                'company_id':company.id or False,
                'receiver_number': receiver_number,
                'receiver_name': receiver_name,
                'fe_monto_total_impuesto': fe_monto_total_impuesto,
                'electronic_doc_bill_number': bill_number,
                'xml_bill': xml,
                'xml_bill_name': xml_bill_name,
                'date': date,
                'doc_type': doc_type,
                'total_amount': total_amount,
                'line_ids': invoice_lines,
                'xslt': xslt,
            })
            log.info("============Comprobante=={}======{}===Creado".format(bill_number,comprobante))
        else:
            self.key = ""
            "UC09"
            log.info(
                '\n "el documento XML Clave: %s tipo %s ya se encuentra en la base de datos. Refresque la Pantalla\n',
                key, doc_type)

    def add_acceptance(self, xml_acceptance, xml_acceptance_name):
        "UC05A"
        'Validar que la <Clave> dentro del XML del “Mensaje de Hacienda”, se tenga ya'
        dic = self.convert_xml_to_dic(xml_acceptance)
        doc_type = self.get_doc_type(dic)
        key = self.get_key(dic, doc_type)
        document = self.env['electronic.doc'].search([('key', '=', key)])
        if (document):
            document.update({
                'xml_acceptance': xml_acceptance,
                'xml_acceptance_name': xml_acceptance_name or '{}_aceptacion.xml'.format(key),
            })

    def transform_to_xslt(self, root_xml, doc_type):
        dom = ET.fromstring(base64.b64decode(root_xml))
        if (doc_type == 'FE'):
            ruta = path._path[0]+"/fe.xslt"
            transform = ET.XSLT(
                ET.parse(
                    ruta
                ))
        elif (doc_type == 'TE'):
            ruta = path._path[0]+"/te.xslt"
            transform = ET.XSLT(
                ET.parse(
                    ruta
                ))
        elif (doc_type == 'NC'):
            ruta = path._path[0]+"/nc.xslt"
            transform = ET.XSLT(
                ET.parse(
                    ruta
                ))
        nuevodom = transform(dom)
        return ET.tostring(nuevodom, pretty_print=True)

    "UC03"

    def get_doc_type(self, dic):
                 
        tag_FE = 'https://cdn.comprobanteselectronicos.go.cr/xml-schemas/v4.3/facturaElectronica'
        tag_TE = 'https://cdn.comprobanteselectronicos.go.cr/xml-schemas/v4.3/tiqueteElectronico'
        tag_MH = 'https://cdn.comprobanteselectronicos.go.cr/xml-schemas/v4.3/mensajeHacienda'
        tag_NC = 'https://cdn.comprobanteselectronicos.go.cr/xml-schemas/v4.3/notaCreditoElectronica'
        try:
            if 'TiqueteElectronico' in dic.keys():
                if dic['TiqueteElectronico']['@xmlns'] == tag_TE:
                    return 'TE'
            elif 'FacturaElectronica' in dic.keys():
                if dic['FacturaElectronica']['@xmlns'] == tag_FE:
                    return 'FE'
            elif 'MensajeHacienda' in dic.keys():
                if dic['MensajeHacienda']['@xmlns'] == tag_MH:
                    return 'MH'
            elif 'NotaCreditoElectronica' in dic.keys():
                if dic['NotaCreditoElectronica']['@xmlns'] == tag_NC:
                    return 'NC'
        except Exception as e:
            log.info('\n "erro al obtener tipo de archivo xml %s"\n', e)
            return False

    def get_key(self, dic, doc_type):
        if (doc_type == 'TE'):
            key = 'TiqueteElectronico'
        elif (doc_type == 'MH'):
            key = 'MensajeHacienda'
        elif (doc_type == 'FE'):
            key = 'FacturaElectronica'
        elif (doc_type == 'NC'):
            key = 'NotaCreditoElectronica'
        return dic[key]['Clave']


    def get_inverse_doc_type(self, dic, doc_type):
        if (doc_type == 'TE'):
            key = 'TiqueteElectronico'
        elif (doc_type == 'MH'):
            key = 'MensajeHacienda'
        elif (doc_type == 'FE'):
            key = 'FacturaElectronica'
        elif (doc_type == 'NC'):
            key = 'NotaCreditoElectronica'
        return key

    def get_bill_number(self, dic, doc_type):
        try:
            if (doc_type == 'TE'):
                key = 'TiqueteElectronico'
            elif (doc_type == 'FE'):
                key = 'FacturaElectronica'
            elif (doc_type == 'NC'):
                key = 'NotaCreditoElectronica'
            return dic[key]['NumeroConsecutivo']
        except Exception as e:
            return False

    def get_provider(self, dic, doc_type):
        if (doc_type == 'TE'):
            key = 'TiqueteElectronico'
        elif (doc_type == 'MH'):
            key = 'MensajeHacienda'
        elif (doc_type == 'FE'):
            key = 'FacturaElectronica'
        elif (doc_type == 'NC'):
            key = 'NotaCreditoElectronica'
        return dic[key]['Emisor']['Nombre']


    def get_currency(self, dic, doc_type):
        if (doc_type == 'TE'):
            key = 'TiqueteElectronico'
        elif (doc_type == 'MH'):
            key = 'MensajeHacienda'
        elif (doc_type == 'FE'):
            key = 'FacturaElectronica'
        elif (doc_type == 'NC'):
            key = 'NotaCreditoElectronica'
        return dic[key]['ResumenFactura']['CodigoTipoMoneda']['CodigoMoneda']
    
    def get_provider_identification(self, dic, doc_type):
        #this method validate that exist a receiver number
        try:
            if (doc_type == 'TE'):
                key = 'TiqueteElectronico'
            elif (doc_type == 'MH'):
                key = 'MensajeHacienda'
            elif (doc_type == 'FE'):
                key = 'FacturaElectronica'
            elif (doc_type == 'NC'):
                key = 'NotaCreditoElectronica'
            return dic[key]['Emisor']['Identificacion']['Numero']

        except:
            return False

    def get_date(self, dic, doc_type):
        if (doc_type == 'TE'):
            key = 'TiqueteElectronico'
        elif (doc_type == 'MH'):
            key = 'MensajeHacienda'
        elif (doc_type == 'FE'):
            key = 'FacturaElectronica'
        elif (doc_type == 'NC'):
            key = 'NotaCreditoElectronica'
        return dic[key]['FechaEmision']

    def get_receiver_identification(self, dic, doc_type):
        #this method validate that exist a receiver number
        try:
            if (doc_type == 'TE'):
                key = 'TiqueteElectronico'
            elif (doc_type == 'MH'):
                key = 'MensajeHacienda'
            elif (doc_type == 'FE'):
                key = 'FacturaElectronica'
            elif (doc_type == 'NC'):
                key = 'NotaCreditoElectronica'
            return dic[key]['Receptor']['Identificacion']['Numero']

        except:
            return False

    def get_receiver_name(self, dic, doc_type):
        try:
            if (doc_type == 'TE'):
                key = 'TiqueteElectronico'
            elif (doc_type == 'MH'):
                key = 'MensajeHacienda'
            elif (doc_type == 'FE'):
                key = 'FacturaElectronica'
            elif (doc_type == 'NC'):
                key = 'NotaCreditoElectronica'
            return dic[key]['Receptor']['Nombre']

        except:
            return False
        
    


    def get_total_amount(self, dic, doc_type):
        if (doc_type == 'TE'):
            key = 'TiqueteElectronico'
        elif (doc_type == 'FE'):
            key = 'FacturaElectronica'
        elif (doc_type == 'NC'):
            key = 'NotaCreditoElectronica'
        return dic[key]['ResumenFactura']['TotalComprobante']
    
    def get_total_tax(self, dic, doc_type):
        if (doc_type == 'TE'):
            key = 'TiqueteElectronico'
        elif (doc_type == 'FE'):
            key = 'FacturaElectronica'
        elif (doc_type == 'NC'):
            key = 'NotaCreditoElectronica'
        return dic[key]['ResumenFactura']['TotalImpuesto']
    
    def convert_xml_to_dic(self, xml):
        dic = xmltodict.parse(base64.b64decode(xml))
        return dic

    def automatic_bill_creation(self, docs_tuple,company=None):
        for doc_list in docs_tuple:
            for item in doc_list:

                xml = base64.b64encode(item.content)
                xml_name = item.fname
                dic = self.convert_xml_to_dic(xml)
                doc_type = self.get_doc_type(dic)

                if doc_type == 'FE' or doc_type == 'TE':
                    self.create_electronic_doc(xml, xml_name,company)

                elif doc_type == 'MH':
                    self.add_acceptance(xml, xml_name)
                    
                    
    def send_bill(self):
        if not 'http://' in self.company_id.fe_url_server and  not 'https://' in self.company_id.fe_url_server:
            raise ValidationError("El campo Server URL en comapañia no tiene el formato correcto, asegurese que contenga http://")

        if self.state == 'draft':
           raise exceptions.Warning('VALIDE primero este documento')
        if self.fe_xml_hacienda:
           raise exceptions.Warning("Ya se tiene la RESPUESTA de Hacienda")

        country_code = self.company_id.partner_id.country_id.code 
        if country_code == 'CR':
            self.validar_compania
            if self.consecutivo[8:10] == "05" or self.consecutivo[8:10] == "06" or  self.consecutivo[8:10] == "07":                

                if self.fe_xml_hacienda:
                   msg = '--> Ya se tiene el XML de Hacienda Almacenado'
                   log.info(msg)
                   raise exceptions.Warning((msg))

                else:
                   self._cr_post_server_side()
                    

    def write_chatter(self,body):
        log.info('--> write_chatter')
        chatter = self.env['mail.message']
        chatter.create({
                        'res_id': self.id,
                        'model':'electronic.doc',
                        'body': body,
                       })   
        
    def _cr_xml_mensaje_receptor(self):
        log.info('--> factelec-Invoice-_cr_xml_mensaje_receptor')

        bill_dic = self.convert_xml_to_dic(self.xml_bill)
        doc_type = self.get_doc_type(bill_dic)
        key = self.get_inverse_doc_type(bill_dic, doc_type)
        if key in bill_dic.keys():
            tz = pytz.timezone('America/Costa_Rica')
            fecha = datetime.now(tz=tz).strftime("%Y-%m-%d %H:%M:%S")
            json = {'MensajeReceptor':{
                'Clave':bill_dic[key]['Clave'],
                'NumeroCedulaEmisor':bill_dic[key]['Emisor']['Identificacion']['Numero'],
                'TipoCedulaEmisor':bill_dic[key]['Emisor']['Identificacion']['Tipo'],
                'FechaEmisionDoc':fecha.split(' ')[0]+'T'+fecha.split(' ')[1]+'-06:00',
                'Mensaje':self.fe_msg_type,
                'DetalleMensaje':self.fe_detail_msg,
                'MontoTotalImpuesto':'{0:.5f}'.format(self.fe_monto_total_impuesto),
                'MontoTotalAcreditar':'{0:.5f}'.format(self.fe_monto_total_impuesto_acreditar),
                'ActividadEconomica':self.fe_actividad_economica.code,
                'CondicionImpuesto':self.fe_condicio_impuesto,
                'MontoTotalGastoAplicable':'{0:.5f}'.format(self.fe_monto_total_gasto_aplicable),
                'TotalFactura':'{0:.5f}'.format(float(bill_dic[key]['ResumenFactura']['TotalComprobante'].replace(',','.'))),
                'NumeroCedulaReceptor':self.company_id.vat.replace('-','').replace(' ','') or None,#bill_dic['FacturaElectronica']
                'TipoCedulaReceptor':bill_dic[key]['Receptor']['Identificacion']['Tipo'],
                'NumeroConsecutivoReceptor':self.consecutivo,
                }}
            return json
        else:
            msg = 'adjunte una factura electronica antes de confirmar la aceptacion'
            raise exceptions.Warning((msg))
            
    def validar_compania(self):
        
            msg = ''               
            if not self.consecutivo:
                msg += 'El documento no contiene numero consecutivo \n'
            elif len(self.consecutivo) != 20:
                msg += 'El consecutivo del documento debe ser de un largo de 20 \n'
            
            if not self.key:
                msg += 'El documento no contiene clave \n'

            elif len(self.key) != 50:
                msg += 'La clave tiene que tener un largo de 50 \n'
               
            if not self.company_id.company_registry:
                msg += 'En compañia, falta el campo registro de la compañia \n'
            
            if not self.company_id.fe_comercial_name:
                msg += 'En compañia, falta el campo nombre comercial \n'
            if not self.company_id.fe_identification_type:
                msg += 'En compañia, falta el tipo de identificación \n'
            if not self.company_id.vat:
                msg += 'En compañia, falta el campo NIF \n'
            elif len(self.company_id.vat) < 9 and len(self.company_id.vat) >12:
                msg += 'En compañia, el largo del NIF debe ser entre 9 y 12 \n'
         
            if not self.company_id.state_id:
                 msg += 'En compañia, la provincia es requerida \n'
            elif not self.company_id.state_id.fe_code:
                 msg += 'En compañia, el codigo para factura electronica de la provincia es requerida \n'
                    
            if not self.company_id.canton_id:
                msg += 'En compañia, el canton es requerido \n'
                
            if not self.company_id.distrito_id:
                    msg += 'En compañia, el distrito es requerido \n'
            
            if not self.company_id.street:
                msg += 'En compañia, el campo otras señas es requerido \n'
            
            if not self.company_id.phone:
                msg += 'En compañia, falta el numero de teléfono \n'
            elif len(self.company_id.phone) < 8 and len(self.company_id.phone) > 20:
                 msg += 'En compañia, el numero de teléfono debe ser igual o mayor que 8 y menor que 20 \n'
            elif not re.search('^\d+$',self.company_id.phone):
                msg += 'En compañia, el numero de teléfono debe contener solo numeros \n'
            
            if self.company_id.fe_fax_number:
                if len(self.company_id.fe_fax_number)  < 8 and len(self.company_id.fe_fax_number) > 20:
                    msg += 'En compañia, el numero de fax debe ser igual o mayor que 8 y menor que 20 \n' 
            if not self.company_id.email:
                 msg += 'En compañia, el correo electronico es requerido \n'
            if not self.company_id.fe_url_server:
                msg += "Configure el URL del Servidor en Settings/User & Companies/ TAB: Factura Electronica -> URL\n"
            if not self.company_id.fe_activity_code_ids:
                msg += "Falta agregar codigo de actividad en Settings/User & Companies/TAB: Factura Electronica\n"  
            if msg:        
                raise ValidationError(msg)
                
    def get_bill(self):
        for s in self:
            if s.state == 'draft':
              raise exceptions.Warning('VALIDE primero este documento')
            #peticion al servidor a partir de la clave
            log.info('--> 1569447129')
            log.info('--> get_invoice')
            if not 'http://' in s.company_id.fe_url_server and  not 'https://' in s.company_id.fe_url_server:
               raise ValidationError("El campo Server URL en comapañia no tiene el formato correcto, asegurese que contenga http://")
            if s.fe_xml_hacienda:
                 raise ValidationError("Ya se tiene la RESPUESTA de Hacienda")
 
            if s.consecutivo[8:10] == "05"or s.consecutivo[8:10] == "06" or  s.consecutivo[8:10] == "07": 
                url = s.company_id.fe_url_server+'{0}'.format(s.key+'-'+s.consecutivo)
                header = {'Content-Type':'application/json'}

                try:
                    r = requests.get(url, headers = header, data=json.dumps({}))
                except Exception as ex:
                    if 'Name or service not known' in str(ex.args):
                        raise ValidationError('Error al conectarse con el servidor! valide que sea un URL valido ya que el servidor no responde')
                    else:
                        raise ValidationError(ex) 

                data = r.json()
                log.info('---> %s',data)
                log.info('-->1569447795')
                #alamacena la informacion suministrada por el servidor
                if data.get('result'):

                    if data.get('result').get('error'):
                       s.write_chatter(data['result']['error'])
                    else:
                       params = {
                          'fe_server_state':data['result']['ind-estado'],
                          'fe_name_xml_sign':data['result']['nombre_xml_firmado'],
                          'fe_xml_sign':data['result']['xml_firmado'],
                          'fe_name_xml_hacienda':data['result']['nombre_xml_hacienda'],
                          'fe_xml_hacienda':data['result']['xml_hacienda'],
                       }
                       s.update(params)
                    
                
    def _cr_post_server_side(self):
        if not self.company_id.fe_certificate:
            raise exceptions.Warning(('No se encuentra el certificado en compañia'))
            
        log.info('--> factelec-Invoice-_cr_post_server_side')
        
        if self.consecutivo[8:10] == '05'or self.consecutivo[8:10] == "06" or  self.consecutivo[8:10] == "07": 
            invoice = self._cr_xml_mensaje_receptor()      
            json_string = {
                      'invoice': invoice,
                      'certificate':base64.b64encode(self.company_id.fe_certificate).decode('utf-8'),
                      'token_user_name':self.company_id.fe_user_name,
                      }
            json_to_send = json.dumps(json_string)
            log.info('========== json to send : \n%s\n', json_string)
            header = {'Content-Type':'application/json'}
            url = self.company_id.fe_url_server
            try:
                response = requests.post(url, headers = header, data = json_to_send)
            except Exception as ex:
                if 'Name or service not known' in str(ex.args):
                    raise ValidationError('Error al conectarse con el servidor! valide que sea un URL valido ya que el servidor no responde')
                else:
                     raise ValidationError(ex) 
            try:
               log.info('===340==== Response : \n  %s',response.text )
               '''Response : {"id": null, "jsonrpc": "2.0", "result": {"status": "200"}}'''
               json_response = json.loads(response.text)

               result = ""
               if "result" in json_response.keys():
                   result = json_response['result']
                   if "status" in result.keys():
                       if result['status'] == "200":
                           log.info('====== Exito \n')
                           self.update({'fe_server_state':'enviado a procesar'})

                   elif "error" in  result.keys():
                        result = json_response['result']['error']
                        body = "Error "+result
                        self.write_chatter(body)

            except Exception as e:
                body = "Error "+str(e)
                self.write_chatter(body)
                
    @api.model
    def cron_send_bill(self):
        invoice_list = self.env['electronic.doc'].search(['&',('fe_server_state','=',False),('state','=','posted')])
        log.info('-->invoice_list %s',invoice_list)
        for invoice in invoice_list:
            if invoice.company_id.country_id.code == 'CR':
                log.info('-->consecutivo %s',invoice.consecutivo)
                invoice.send_bill()
    @api.model
    def cron_get_bill(self):
        log.info('--> cron_get_bills')
        list = self.env['electronic.doc'].search(['|',('fe_xml_sign','=',False),('fe_xml_hacienda','=',False),'&',('state','=','posted'),
        ('fe_server_state','!=','pendiente enviar'),('fe_server_state','!=',False)])
        for item in list:
            if item.company_id.country_id.code == 'CR':
                log.info(' item name %s',item.consecutivo)
                item.get_bill()
