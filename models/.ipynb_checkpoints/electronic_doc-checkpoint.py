from odoo import api, exceptions, fields, models, _
from odoo.exceptions import ValidationError
from lxml.etree import Element, fromstring, parse, tostring, XMLParser
from .xslt import __path__ as path
import lxml.etree as ET
import xmltodict
import logging
import base64

from io import BytesIO

log = logging.getLogger(__name__)


class ElectronicDoc(models.Model):

    _name = 'electronic.doc'
    _rec_name = 'display_name'
    key = fields.Char(string="Clave")
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
                                    ('MH', 'Aceptacion Ministerio Hacienda'),
                                    ('OT', 'Otro'),
                                ])

    state = fields.Selection(string='Respuesta Hacienda',
                             selection=[
                                 ('P', 'Pendiente'),
                                 ('', ''),
                             ])

    total_amount = fields.Float(string="Monto Total", )

    xslt = fields.Html(string="Representacion Grafica", )

    fe_msg_type = fields.Selection([ # 1570035130
            ('1', 'Accept'),
            ('2', 'Partially Accept'),
            ('3', 'Reject'),
        ], string="Mensaje", track_visibility="onchange",)

    fe_detail_msg = fields.Text(string="Detalle Mensaje", size=80, copy=False,)# 1570035143
    

    display_name = fields.Char(
        string='Name',
        compute='_compute_display_name',
    )
    _sql_constraints = [
        ('unique_key', 'UNIQUE(key)',
         'El documento ya existe en la base de datos!!'),
    ]



    @api.depends('key', 'provider', 'date')
    def _compute_display_name(self):
        self.display_name = '{0} {1} {2}'.format(self.date, self.provider, self.key)


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
            if 'xml' in self.xml_bill_name:
                dic = self.convert_xml_to_dic(self.xml_bill)
                doc_type = self.get_doc_type(dic)
                if doc_type == 'TE' or doc_type == 'FE':
                    self.key = self.get_key(dic, doc_type)
                    self.xslt = self.transform_to_xslt(self.xml_bill, doc_type)
                    self.electronic_doc_bill_number = self.get_bill_number(
                        dic, doc_type)
                    self.date = self.get_date(dic, doc_type)
                    self.doc_type = doc_type
                    self.provider = self.get_provider(dic, doc_type)
                    self.receiver_name = self.get_receiver_name(dic, doc_type)
                    self.receiver_number = self.get_receiver_identification(
                        dic, doc_type)
                    self.total_amount = self.get_total_amount(dic, doc_type)
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
                            'state': None,
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
                            'state': None,
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
                            'state': None,
                            'total_amount': None,
                            'xslt': None,
                            'odoo_bill': None
                        }
            }



    def create_electronic_doc(self, xml, xml_name):

        dic = self.convert_xml_to_dic(xml)
        doc_type = self.get_doc_type(dic)

        key = self.get_key(dic, doc_type)

        electronic_doc = self.env['electronic.doc']
        "UC07"
        if (not electronic_doc.search([('key', '=', key),
                                       ('doc_type', '=', doc_type)])):
            "UC05A"
            provider = self.get_provider(dic, doc_type)
            receiver_number = self.get_receiver_identification(dic, doc_type)
            receiver_name = self.get_receiver_name(dic, doc_type)
            bill_number = self.get_bill_number(dic, doc_type)
            xml_bill = xml
            xml_bill_name = xml_name
            date = self.get_date(dic, doc_type)
            state = 'P'
            total_amount = self.get_total_amount(dic, doc_type)

            "UC05C"
            xslt = self.transform_to_xslt(xml, doc_type)
            if (not receiver_number):
                receiver_number = ''
                log.info(
                    '\n "el documento XML Clave: %s no contiene numero del proveedor \n',
                    key)
            "UC05C"
            if (not receiver_name):
                receiver_name = ''
                log.info(
                    '\n "el documento XML Clave: %s no contiene nombre del proveedor \n',
                    key)

            electronic_doc.create({
                'key': key,
                'provider': provider,
                'receiver_number': receiver_number,
                'receiver_name': receiver_name,
                'electronic_doc_bill_number': bill_number,
                'xml_bill': xml,
                'xml_bill_name': xml_bill_name,
                'date': date,
                'doc_type': doc_type,
                'state': 'P',
                'total_amount': total_amount,
                'xslt': xslt,
            })
        else:
            self.key = ""
            "UC09"
            log.info(
                '\n "el documento XML Clave: %s tipo %s ya se encuentra en la base de datos \n',
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
            transform = ET.XSLT(
                ET.parse(
                    '/home/odoo/addons/localization_cr_client/static/src/templateTE.xslt'
                ))
        nuevodom = transform(dom)
        return ET.tostring(nuevodom, pretty_print=True)

    "UC03"

    def get_doc_type(self, dic):
                 
        tag_FE = 'https://cdn.comprobanteselectronicos.go.cr/xml-schemas/v4.3/facturaElectronica'
        tag_TE = 'https://cdn.comprobanteselectronicos.go.cr/xml-schemas/v4.3/tiqueteElectronica'
        tag_MH = 'https://cdn.comprobanteselectronicos.go.cr/xml-schemas/v4.3/mensajeHacienda'
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
        return dic[key]['Clave']

    def get_bill_number(self, dic, doc_type):
        try:
            if (doc_type == 'TE'):
                key = 'TiqueteElectronico'
            elif (doc_type == 'FE'):
                key = 'FacturaElectronica'
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
        return dic[key]['Emisor']['Nombre']

    def get_date(self, dic, doc_type):
        if (doc_type == 'TE'):
            key = 'TiqueteElectronico'
        elif (doc_type == 'MH'):
            key = 'MensajeHacienda'
        elif (doc_type == 'FE'):
            key = 'FacturaElectronica'
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
            return dic[key]['Receptor']['Nombre']

        except:
            return False

    def get_total_amount(self, dic, doc_type):
        if (doc_type == 'TE'):
            key = 'TiqueteElectronico'
        elif (doc_type == 'FE'):
            key = 'FacturaElectronica'
        return dic[key]['ResumenFactura']['TotalComprobante']

    def convert_xml_to_dic(self, xml):
        dic = xmltodict.parse(base64.b64decode(xml))
        return dic

    def automatic_bill_creation(self, docs_tuple):
        for doc_list in docs_tuple:
            for item in doc_list:

                xml = base64.b64encode(item.content)
                xml_name = item.fname
                dic = self.convert_xml_to_dic(xml)
                doc_type = self.get_doc_type(dic)

                if doc_type == 'FE' or doc_type == 'TE':
                    self.create_electronic_doc(xml, xml_name)

                elif doc_type == 'MH':
                    self.add_acceptance(xml, xml_name)
