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

from lxml import etree

log = _logger = _logging = logging.getLogger(__name__)

from .account_hacienda import AccountHacienda as hacienda

class ElectronicDoc(models.Model):

    _inherit = 'electronic.doc'

    def electronic_docs_prepare_cron(self):
        log.info("electronic_doc_cron===============")
        records = self.search([],limit=100, order='id asc') # OJO EL FILTRO
        log.info(" Registros a procesar: %s", len(records) )
        data_array = self.hacienda_data_prepare(records)
        if len( data_array ) > 0:
            server_side = self.send_server_side( data_array )
            if server_side == False:
                _logging.info("    ERROR AL ENVIAR AL SERVER SIDE")
        else:
            _logging.info(" Sin Registros a Procesar")
        log.info("electronic_doc_cron END==================")
    
    def electronic_docs_post_cron(self):
        _logging.info("electronic_docs_post_cron========")
        estado = "Procesado"
        records = self.env['electronic.doc'].search([('fe_server_state','=', estado )])
        #_logging.info(" DEB187 records: %s", records)
        for record in records:
            _logging.info("  Hacienda posting consecutivo: %s", record.consecutivo)
            company_id = record.company_id.id
            access_token_jwt = hacienda._get_token( record )
            #_logging.info("DEB192 hacienda_get_token: %s", access_token_jwt)
            json_to_send = record.fe_hacienda_json
            #_logging.info("\n\nDEB194 json_to_send: %s", json_to_send)

            
            authorization = "bearer " + access_token_jwt
            #_logging.info("DEB198 Bearer: %s", authorization)
            headers = {
                'content-type': "application/json",
                'authorization': authorization,
                'cache-control': "no-cache",
            }
            hacienda_url = \
                "https://api.comprobanteselectronicos.go.cr/recepcion-sandbox/v1/recepcion/"
            
            u_name = record.company_id.fe_user_name
            u_password = record.company_id.fe_user_password
            if u_name and u_password:
                _logging.info("  HACIENDA USER AND PASS FOUND")
                
                response = requests.post(
                    hacienda_url, headers = headers, data = json_to_send,
                )
                response_json_full = {
                    "headers": response.headers,
                    "text": response.text,
                    "status_code": response.status_code,
                    "reason": response.reason
                }

                if response_json_full.get("status_code") == 400:
                    response_headers = response_json_full.get('headers')
                    error_msg = response_headers.get("x-error-cause")
                    record.write({
                        'fe_server_state': "Error"
                    })
                    self.env['mail.message'].create({
                        'res_id': record.id,
                        'model': record._name,
                        'body': "Hacienda: " + error_msg,
                    })
        return
    
    
    def hacienda_data_prepare(self, records):
        _logging.info(" hacienda_data_prepare============")
        
        #_logging.info("DEB36 RECORDS: %s", records)
        data_array = []
        for record in records:
            account_move_data_json = {}
            if record.fe_server_state != False:
                msg = "   Procesado anteriormente: " + str( record.consecutivo )
                _logging.info( msg)
                continue
            
            if len( str(record.consecutivo) ) != 20:
                msg = "   Warning: Largo de Consecutivo no cumple: " + str(record.consecutivo)
                _logging.info( msg )
                continue

            #Agregar el Company Data JSON
            xml_bill = record.xml_bill
            if xml_bill:
                xml_bill_b64 = xml_bill.decode('utf-8')
                #_logging.info("DEB50 XML_BILL_TXT: %s", xml_bill_b64)
                xml_bill = etree.fromstring( base64.b64decode( xml_bill_b64 ) )
                #_logging.info("DEB52 XML_BILL: %s", xml_bill)

                nss = xml_bill.nsmap
                nss['xmlns'] = nss[None]
                nss.pop(None)

                Clave = xml_bill.xpath(u'xmlns:Clave', namespaces=nss)[0].text
                #_logging.info("DEB41 Clave: %s", Clave)
                NumeroCedulaEmisor = xml_bill.xpath(u'xmlns:Emisor/xmlns:Identificacion/xmlns:Numero', namespaces=nss)[0].text
                #_logging.info("DEB43 NumeroCedulaEmisor: %s", NumeroCedulaEmisor)
                TipoCedulaEmisor = xml_bill.xpath(u'xmlns:Emisor/xmlns:Identificacion/xmlns:Tipo', namespaces=nss)[0].text
                #_logging.info("DEB45 TipoCedulaEmisor: %s", TipoCedulaEmisor)
                record.write({
                    'provider_vat': NumeroCedulaEmisor,
                    'provider_vat_type': TipoCedulaEmisor,
                })
            #Busqueda de la DATA
            keys = [ 'key', 'provider_vat' , 'provider_vat_type','fe_msg_type','fe_detail_msg', 
                     'fe_actividad_economica',
                     'fe_condicio_impuesto', 'fe_monto_total_impuesto_acreditar',
                     'fe_monto_total_gasto_aplicable', 'fe_monto_total_impuesto',
                     'total_amount', 'company_id', 'consecutivo',
                   ]
            record_data = record.search_read([ ('id','=', record.id) ], keys)
            #_logging.info("DEB91 record_data %s", record_data)
            
            #Company Data
            company_tuple = record_data[0]['company_id']
            #_logging.info("DEBDD company_tuple: %s", company_tuple)
            
            #validar si está en data_array
            company_data = [ element for element in data_array if element['company_data'].get('id') == company_tuple[0] ]
            #_logging.info("DEB88 company_data: %s", company_data )
            if not company_data:
                company_keys = [ 'id' , 'name', 'vat', 'fe_identification_type', 'fe_certificate' ]
                companies_data = record.env['res.company'].search_read(
                    [ ( 'id', '=', company_tuple[0] )  ],
                    company_keys
                )
                companies_data[0]['records'] = []
                
                companies_data[0]['fe_certificate'] = companies_data[0].get('fe_certificate').decode('utf-8')
                data_array.append( {'company_data': companies_data[0] } )
            #_logging.info("DEB97 data_array: %s", data_array )
            
            #Actividad Economica Info
            fe_actividad_economica_tuple = record_data[0]['fe_actividad_economica']
            fe_actividad_keys = [ 'code', 'description' ]
            fe_actividad_economica_data = record.env['activity.code'].search_read(
                [ ( 'id', '=', fe_actividad_economica_tuple[0] )  ],
                fe_actividad_keys
            )
            #_logging.info("DEBC533=====DATA: %s", fe_actividad_economica_data )
            record_data[0]['fe_actividad_economica'] = fe_actividad_economica_data

            companies_data = [ element for element in data_array if element['company_data'].get('id') == company_tuple[0] ]
            companies_data[0]['company_data']['records'].append( record_data[0] )
        return data_array

    def send_server_side(self, data_array ):
        _logging.info(" send_server_side =====================")
        header = {'Content-Type':'application/json'}
        url1 = "http://34.122.72.168/api/odoov14/createxmlaceptacion_fev43/"
        data_json = {'data_array': data_array}

        response_obj = self.post_data_json( data_json, url1, header  )
        if response_obj.status_code != 200:
            return False
        
        response_txt = response_obj.text
        response_json = json.loads( response_txt )
        for response_record in response_json.get('result'):
            #_logging.info("DEB134 response_record: %s",response_record )
            output = self.comprobantes_electronicos_procesado( response_record )
            if output == False:
                _logging.info("   Error al procesar el comprobante electrónico")
        return
        
    def comprobantes_electronicos_procesado(self, response_json):
        _logging.info("DEB142 response_json: %s", response_json)
        consecutivo = response_json.get('consecutivo')

        msg = "   Procesado Comprobante: " + str( consecutivo )
        _logging.info( msg)
        #Buscar el registro en electronic_doc por el consecutivo

        #_logging.info("DEB144 consecutivo: %s", consecutivo)
        record = self.env['electronic.doc'].search([('consecutivo','=', str(consecutivo) )])
        #_logging.info("DEB146 record: %s", record)
        if len(record) == 0:
            msg = "Comprobante Electronico no encontrado: " + str( consecutivo )
            _logging.info( msg )
            return False

        errors = response_json.get('errors')
        if len(errors) > 0:
            record.write({
                'fe_server_state':  "Error"
            })
            errors_txt = '<br>'.join( map(str, errors) )
            self.env['mail.message'].create({
                'res_id': record.id,
                'model':'electronic.doc',
                'body': errors_txt,
            })
            return False

        json_to_send = json.loads( response_json.get('json_to_send') )
        #_logging.info("DEB128 json_to_send: %s", json_to_send)
        fe_name_xml_sign = str( json_to_send.get('clave') ) + ".xml"
        #_logging.info("DEB168 xml_filename: %s", fe_name_xml_sign)
        fe_xml_sign = json_to_send.get('comprobanteXml')
        #_logging.info("DEB170 xml_file: %s", fe_xml_sign)
        
        record.write({
            'fe_server_state': "Procesado",
            'fe_xml_sign': fe_xml_sign,
            'fe_name_xml_sign': fe_name_xml_sign,
            'fe_hacienda_json': json.dumps(json_to_send),
        })
        return


    
    def hacienda_get_token(self, record):
        
        output = hacienda._get_token(self,
                    self.company_id.fe_user_name,
                    self.company_id.fe_user_password,
                )
        if not output:
            return
        STOP205
        access_token_data = json.loads( output.get('text') )
        if access_token_data.get('error'):
            self.env['mail.message'].create({
                'res_id': self.id,
                'model': self._name,
                'body': "Hacienda: " + access_token_data.get('error_description'),
            })
            return
        access_token = access_token_data.get('access_token')
        _logging.info("DEB157 token: %s", access_token)
        
        STOP201ANTESDELPOSTAHACIENDA
        output = hacienda.hacienda_post_json(self, access_token  )
        
        
        #output = hacienda.hacienda_post_json(self)
        #_logging.info("DEB141 output: %s", output)
        
        
        
    def post_data_json( self, data_json, url, header ):
        #_logging.info("DEB76 data_json: %s", data_json)
        #post_to_server_side
        
        json_to_send = json.dumps(data_json, indent=4)
        response = requests.post(url, headers = header, data = json_to_send)
        return response
        
    
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
                

    @api.onchange("xml_bill")
    def _onchange_load_xml(self):
        if self.xml_bill:
            if '.xml' in self.xml_bill_name.lower():
                dic = self.convert_xml_to_dic(self.xml_bill)
                doc_type = self.get_doc_type(dic)
                if doc_type == 'TE' or doc_type == 'FE' or doc_type == 'NC':
                    list_lineas = self.crear_lineas_xml(self.xml_bill)
                    xml_currency = self.get_currency(dic, doc_type).get('CodigoMoneda')
                    currency_id = self.env['res.currency'].search([('name','=',xml_currency)])
                    currency_exchange = self.get_currency(dic, doc_type).get('TipoCambio')

                    receiver_number = self.get_receiver_identification(dic, doc_type)
                    receiver_company =  self.env['res.company'].search([ ('vat','=', receiver_number) ])
                    if receiver_company.id != self.env.company.id:
                        message1 = "Error:\n El receptor de este document es: {}\n y fue enviado por: {},\nLa compañía seleccionada es: {}".format( 
                           self.get_receiver_name(dic, doc_type), self.get_provider(dic, doc_type),
                           self.env.company.name
                        )
                        raise ValidationError( _(message1) )

                    self.write({
                        'key':self.get_key(dic, doc_type),
                        'xslt':self.transform_to_xslt(self.xml_bill, doc_type),
                        'currency_id':currency_id,
                        'currency_exchange': currency_exchange,
                        'electronic_doc_bill_number':self.get_bill_number(dic, doc_type),
                        'date':self.get_date(dic, doc_type),
                        'doc_type':doc_type,
                        'provider':self.get_provider(dic, doc_type),
                        'provider_vat':self.get_provider_identification(dic, doc_type),
                        'provider_vat_type':self.get_provider_identification_type(dic, doc_type),
                        'receiver_name':self.get_receiver_name(dic, doc_type) or self.env.user.company_id.name,
                        'receiver_number':self.get_receiver_identification(dic, doc_type) or self.env.user.company_id.vat,
                        'total_amount':self.format_to_valid_float(self.get_total_amount(dic, doc_type)),
                        'fe_monto_total_impuesto':self.format_to_valid_float(self.get_total_tax(dic, doc_type)),
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
            account = self.env.company.default_account_for_invoice_email
            if not account:
                  account = self.env['account.account'].search([("company_id","=",self.company_id.id)])[0]

            for linea in lineasDetalle: 
                    percent = linea.xpath("xmlns:Impuesto/xmlns:Tarifa", namespaces=namespace)
                    discount = linea.xpath("xmlns:Descuento/xmlns:MontoDescuento", namespaces=namespace)
                    log.info("============descuento2==========={0}".format(str(discount)))
                    if len(discount)>0:
                        discount = float(discount[0].text)
                    else:
                        discount = 0
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
                            'discount':discount,
                            'quantity': self.format_to_valid_float(linea.xpath("xmlns:Cantidad", namespaces=namespace)[0].text),
                            'price_unit':self.format_to_valid_float(linea.xpath("xmlns:PrecioUnitario", namespaces=namespace)[0].text),
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
            account = company_id.default_account_for_invoice_email
            if not account:
                  account = self.env['account.account'].search([("company_id","=",self.company_id.id)])[0]
                                
            for linea in lineasDetalle: 
                    percent = linea.xpath("xmlns:Impuesto/xmlns:Tarifa", namespaces=namespace)
                    discount = linea.xpath("xmlns:Descuento/xmlns:MontoDescuento", namespaces=namespace)
                    log.info("============descuento2==========={0}".format(str(discount)))
                    if len(discount)>0:
                        discount = float(discount[0].text)
                    else:
                        discount = 0
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
                                        'discount':discount,
                                        'quantity': self.format_to_valid_float(linea.xpath("xmlns:Cantidad", namespaces=namespace)[0].text),
                                        'price_unit':self.format_to_valid_float(linea.xpath("xmlns:PrecioUnitario", namespaces=namespace)[0].text),
                                       }]
                    invoice_lines.append(new_line)

            otros_cargos = root_xml.xpath("xmlns:OtrosCargos", namespaces=namespace)
            for otro in otros_cargos:
                new_line =  [0, 0, {'name': otro.xpath("xmlns:Detalle", namespaces=namespace)[0].text,
                                        'tax_ids': False,
                                        'account_id': account.id,
                                        'quantity': '1',
                                        'price_unit':self.format_to_valid_float(otro.xpath("xmlns:MontoCargo", namespaces=namespace)[0].text),
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
            
            new_company = self.env['res.company'].search([ ( 'vat', '=', receiver_number ) ])
            if new_company:
                company = new_company
            else:
                _logger.info("ERROR:   Vendor Bill with Receiver Tax ID: %s Not Found", receiver_number)
                return False

            receiver_name = self.get_receiver_name(dic, doc_type) or company.name or False
            bill_number = self.get_bill_number(dic, doc_type) 
            xml_bill = xml
            xml_bill_name = xml_name
            date = self.get_date(dic, doc_type)
            total_amount = self.format_to_valid_float(self.get_total_amount(dic, doc_type))
            fe_monto_total_impuesto = self.format_to_valid_float(self.get_total_tax(dic, doc_type))
            xml_currency = self.get_currency(dic, doc_type).get('CodigoMoneda')
            currency_id = self.env['res.currency'].search([('name','=',xml_currency)])
            currency_exchange = self.get_currency(dic, doc_type).get('TipoCambio')

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
                'currency_exchange': currency_exchange,
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

    def add_pdf(self,key,pdf,fname):
        log.info("=====pdf========{}".format(key))
        document = self.env['electronic.doc'].search([('key', '=', key)])
        if (document):
            document.update({
                'fe_pdf': base64.b64encode(pdf),
                'fe_name_pdf': fname,
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
            
        if dic[key]['ResumenFactura'].get('CodigoTipoMoneda') == None:
            return { 'CodigoMoneda': 'CRC', 'TipoCambio': 1,}
        elif dic[key]['ResumenFactura'].get('CodigoTipoMoneda').get('CodigoMoneda') == None:
            return { 'CodigoMoneda': 'CRC', 'TipoCambio': 1,}

        return  { 'CodigoMoneda': dic[key]['ResumenFactura']['CodigoTipoMoneda']['CodigoMoneda'],
                 'TipoCambio': dic[key]['ResumenFactura']['CodigoTipoMoneda']['TipoCambio']
                }
    
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

    def get_provider_identification_type(self, dic, doc_type):
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
            return dic[key]['Emisor']['Identificacion']['Tipo']

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

        if dic[key]['ResumenFactura'].get('TotalImpuesto'):
            return dic[key]['ResumenFactura']['TotalImpuesto']
        else:
            return "0"
    
    def convert_xml_to_dic(self, xml):
        dic = xmltodict.parse(base64.b64decode(xml))
        return dic

    def automatic_bill_creation(self, docs_tuple,company=None):
        clave = False
        for doc_list in docs_tuple:
            for item in doc_list:

                if '.xml' in str(item.fname).lower():
                    xml = base64.b64encode(item.content)
                    xml_name = item.fname
                    dic = self.convert_xml_to_dic(xml)
                    doc_type = self.get_doc_type(dic)
                    if doc_type == 'FE' or doc_type == 'TE' or doc_type == 'NC' or doc_type == 'ND' :
                        clave = self.get_key(dic,doc_type)
                        is_created = self.create_electronic_doc(xml, xml_name,company)
                        if is_created == False:
                            return

                    elif doc_type == 'MH':
                        self.add_acceptance(xml, xml_name)

                log.info("pdf ======={}====clave=={}".format(str(item.fname).lower(),clave))
                if '.pdf' in str(item.fname).lower() and clave:
                    if 'interpretacion' in str(item.fname).lower():
                        _logger.info("ERROR: PDF COMIENZA CON LA PALABRA INTERPRETACION, NO SE TOMA EN CUENTA")
                        continue
                    log.info("pdf ======creando====")
                    pdf = item.content
                    self.add_pdf( clave, pdf, str(item.fname).lower() )

             

                    
                    
    def send_bill(self):
        STOP648
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
                'TotalFactura':'{0:.5f}'.format(float(self.format_to_valid_float(bill_dic[key]['ResumenFactura']['TotalComprobante']))),
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
        STOP22
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

    def format_to_valid_float(self,str_number):
        new_str = ''
        comma = 0
        dot = 0
        for i in str_number:
            if i == ',':
                comma = comma + 1
            elif i == '.':
                dot = dot + 1
        if comma > 0 and dot > 0:
            if comma < dot:
                new_str = str_number.replace(".","").replace(",",".")
            if comma > dot:
                new_str = str_number.replace(",","")
        elif comma > 1 and dot == 0:
            new_str = str_number.replace(",","")
        elif dot > 1 and comma == 0:
            new_str = str_number.replace(".","")
        else:
             new_str = str_number.replace(",",".")
             
        return new_str

