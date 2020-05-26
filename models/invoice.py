from odoo import models, fields, api, exceptions
from odoo.exceptions import ValidationError
from datetime import datetime,timezone
from lxml.etree import Element, fromstring, parse, tostring, XMLParser
from openerp.osv.orm import except_orm
from openerp.osv import osv
from openerp.tools.translate import _
from .xslt import __path__ as path
import lxml.etree as ET
import pytz
import json
import re
import requests
import base64
import xmltodict
import logging
import time
#import os


log = logging.getLogger(__name__)

TYPE2REFUND = {
    'out_invoice': 'out_refund',        # Customer Invoice
    'in_invoice': 'in_refund',          # Vendor Bill
    'out_refund': 'out_invoice',        # Customer Credit Note
    'in_refund': 'in_invoice',          # Vendor Credit Note
}

class Invoice(models.Model):
    _inherit = "account.invoice"

    log.info('--> Class factelec-Invoice')
    mensaje_validacion = ''
    fe_clave = fields.Char(string="Clave", size=50, copy=False)
    source_date = fields.Datetime(string="Fecha Emision_S")
    fe_fecha_emision = fields.Char(string="Fecha Emision")
    fe_payment_type = fields.Selection([
        ('01', 'Efectivo'),
        ('02', 'Tarjeta'),
        ('03', 'Cheque'),
        ('04', 'Transferencia - depósito bancario'),
        ('05', 'Recaudado por tercero'),
        ('99', ' Otros'),
    ], string="Tipo de pago", track_visibility='onchange',required=False,)  #Cambio de True a False, se debe colocar True pero en la vista Invoice

    fe_receipt_status = fields.Selection([
           ('1', 'Normal'),
           ('2', 'Contingencia'),
           ('3', 'Sin Internet'),
    ], string="Situación del comprobante", track_visibility='onchange',required=False,) #Cambio de True a False, se debe colocar True pero en la vista Invoice
    fe_doc_type = fields.Char(string="FE Tipo Documento")
    fe_doc_type_id = fields.Char()
    fe_informacion_referencia_codigo = fields.Selection([
        ('01', 'Anula Documento de Referencia'),
        ('02', 'Corrige monto'),
        ('04', 'Referencia a otro documento'),
        ('05', 'Sustituye comprobante provisional por contingencia.'),
        ('99', 'Otros'),
    ], string="Codigo de Referencia", track_visibility='onchange')

    tax_condition = fields.Selection(
        string="Condicion del IVA",
        selection= [
                ('01', 'General Credito IVA'),
                ('02', 'General Crédito parcial del IVA'),
                ('03', 'Bienes de Capital'),
                ('04', 'Gasto corriente no genera crédito'),
                ('05', 'Proporcionalidad'),
            ],
    )

    fe_name_xml_sign = fields.Char(string="nombre xml firmado", )
    fe_xml_sign = fields.Binary(string="XML firmado", )
    fe_name_xml_hacienda = fields.Char(string="nombre xml hacienda", )
    fe_xml_hacienda = fields.Binary(string="XML Hacienda", )# 1570034790
    fe_server_state = fields.Char(string="Estado Hacienda", )

    #FIELDS FOR SUPPLIER INVOICE
    fe_xml_supplier = fields.Binary(string="Factura XML", ) # 1569524296
    fe_xml_supplier_name = fields.Char(string="Nombre XML", )
    fe_xml_supplier_xslt = fields.Html(string="Representacion Grafica", )

    fe_xml_supplier_hacienda = fields.Binary(string="Factura XML", )# 1569524732
    fe_xml_supplier_hacienda_name = fields.Char(string="Nombre XML", )

    fe_msg_type = fields.Selection([ # 1570035130
            ('1', 'Accept'),
            ('2', 'Partially Accept'),
            ('3', 'Reject'),
        ], string="Mensaje", track_visibility="onchange")

    fe_detail_msg = fields.Text(string="Detalle Mensaje", size=80, copy=False)# 1570035143

    fe_total_servicio_gravados = fields.Float(string="Total servicios gravados", compute = '_compute_total_servicios_gravados' )
    fe_total_servicio_exentos = fields.Float(string="Total servicios exentos", compute = '' )
    fe_total_mercancias_gravadas = fields.Float(string="Total mercancias gravadas", compute = '_compute_total_mercancias_gravadas' )
    fe_total_mercancias_exentas = fields.Integer(string="Total mercancias exentas", compute = '_compute_total_mercancias_exentas')
    fe_total_gravado = fields.Float(string="Total gravado", compute = '_compute_total_gravado')
    fe_total_exento = fields.Float(string="Total exento", compute = '_compute_total_exento' )
    fe_total_venta = fields.Float(string="Total venta",compute = '_compute_total_venta' )
    fe_total_descuento = fields.Float(string="Total descuento", compute = '_compute_total_descuento' )

    fe_activity_code_id = fields.Many2one(
        string="Actividad económica",
        comodel_name="activity.code",
        ondelete="set null",
    )

    #Cambio

    fe_in_invoice_type = fields.Selection(#1569867120
        string="Tipo Documento",
        selection=[
                ('ME', 'Mensaje Aceptación'),
                ('FE', 'Factura Electronica Compra'),
                ('OTRO', 'Otros'),                
        ],
    )

    fe_current_country_company_code = fields.Char(string="Codigo pais de la compañia actual",compute="_get_country_code")
    
    fe_tipo_documento_referencia = fields.Selection(
        string="Tipo documento de referencia",
        selection=[                
                ('01','Factura electrónica'),
                ('02','Nota de débito electrónica'),
                ('03','Nota de crédito electrónica'),
	            ('04','Tiquete electrónico'),
                ('05','Nota de despacho'),
	            ('06','Contrato'),
                ('07','Procedimiento'),
                ('08','Comprobante emitido en contingencia'),
                ('09','Devolución mercadería'),
                ('10','Sustituye factura rechazada por el Ministerio de Hacienda'),
	            ('11','Sustituye factura rechazada por el Receptor del comprobante'),
                ('12','Sustituye Factura de exportación'),
                ('13','Facturación mes vencido'),
                ('99','Otros'),
        ],
    )
    
    fe_condicion_impuesto = fields.Selection(
        string="Condición de impuestos",
        selection=[
                ('01', 'Genera crédito IVA'),
                ('02', 'Genera Crédito parcial del IVA'),
                ('03', 'Bienes de Capital'),
                ('04', 'Gasto corriente no genera crédito'),
                ('04', 'Proporcionalidad'),
        ],
    )
    
    fe_currency_rate = fields.Char(string="Tipo de cambio",)
    
    @api.onchange('fe_msg_type')
    def _onchange_fe_msg_type(self):
        if self.fe_msg_type == '3':
           account_id =  self.env['account.account'].search([('code','=','0-511301')])
           accountLine = self.env['account.invoice.line']
           accountLine_id = accountLine.create({
                'name': 'Rechazado',
                'account_id':account_id.id,
                'price_unit':0,
                'quantity':1,
                })

           log.info("----------->{}".format(accountLine_id.id))
           self.invoice_line_ids = [(6, 0,[accountLine_id.id])]

    #Cambio
    '''
    @api.onchange('fe_in_invoice_type')
    def _onchange_(self):
        if self.fe_in_invoice_type == 'FEX':
            self.update({'fe_server_state':'sin envio'})
        else:
            self.update({'fe_server_state':''})
    '''

    @api.onchange("journal_id",)
    def _onchange_journal_id(self):
        if len(self.journal_id.sequence_id.prefix) == 10 :
            if self.journal_id.sequence_id.prefix[8:10] == '08':
                self.fe_in_invoice_type = 'FE'
            elif self.journal_id.sequence_id.prefix[8:10] == '05':
                self.fe_in_invoice_type = 'ME'
            else:
                self.fe_in_invoice_type = 'OTRO'
        else:
            self.fe_in_invoice_type = 'OTRO'
            log.info('largo del prefijo del diario menor a 10')

            
    @api.onchange("currency_id","date_invoice",)
    def _onchange_currency_rate(self):
        for s in self:
            log.info('-->577381353')
            if s.currency_id.name == "USD": 
                date = None
                if not s.date_invoice:
                    date = time.strftime("%Y-%m-%d")
                else:
                    date = s.date_invoice 
                                        
                s._rate(date)
                    
            
                       
    def _rate(self,date):
        rate_obj = self.env['res.currency.rate'].search([('name','=',date),('company_id','=',self.company_id.id)])
        if rate_obj:
            rate_calculation = 1 / rate_obj.rate
            rate_name =  datetime.strptime(rate_obj.name,"%Y-%m-%d")
            self.fe_currency_rate = "Fecha : %s || Cambio: %s" % (rate_name.strftime("%d/%m/%Y"), round(rate_calculation , 2) )
            return
        else:
            update_currency = getattr(self.company_id, "_update_currency_bccr", None)
            if callable(update_currency):
                success = self.company_id._update_currency_bccr(date)
                if success:
                    return self._rate(date)
                else:
                    self.fe_currency_rate = "Se produjo un error"
                    return
            else:
                self.fe_currency_rate = "No existe el tipo de cambio"
                return 
    
    
    

    @api.depends('company_id')
    def _get_country_code(self):
        log.info('--> 1575319718')
        for s in self:
            s.fe_current_country_company_code = s.company_id.country_id.code

    #Cambio
    '''
    @api.onchange("fe_in_invoice_type",)
    def _onchange_fe_in_invoice_type(self):
        #1569867217
        if self.fe_in_invoice_type == "FE":
            return {'domain': {'journal_id': [('sequence_id.prefix', 'ilike', '08')]},
                         'value': {
                                     'journal_id': None,
                                  }
                   }
        elif self.fe_in_invoice_type == "ME":
            return {'domain': {'journal_id': [('sequence_id.prefix', 'ilike', '05')]},
                         'value': {
                                     'journal_id': None,
                                  }
                   }
        elif self.fe_in_invoice_type == "FEX":
              return {'domain': {'journal_id': [('type', '=', 'purchase'),('sequence_id.prefix', 'not ilike', '08'),('sequence_id.prefix', 'not ilike', '05')] },
                         'value': {
                                     'journal_id': None,
                                  }
                   }
    '''





    def _compute_total_descuento(self):
        log.info('--> factelec/_compute_total_descuento')
        for s in self:
            totalDiscount = 0
            for i in s.invoice_line_ids:
                if i.discount:
                    discount = i.price_unit * (i.discount/100)
                    totalDiscount = totalDiscount + discount
        self.fe_total_descuento = totalDiscount


    def _compute_total_venta(self):
        log.info('--> factelec/_compute_total_venta')
        for s in self:
            totalSale = 0
            for i in s.invoice_line_ids:
                totalAmount = i.price_unit * i.quantity
                totalSale = totalSale + totalAmount

        self.fe_total_venta = totalSale



    @api.depends("fe_total_servicio_exentos", "fe_total_mercancias_exentas" )
    def _compute_total_exento(self):
        log.info('--> factelec/_compute_total_exento')
        for s in self:
            s.fe_total_exento = s.fe_total_servicio_exentos + s.fe_total_mercancias_exentas


    @api.depends("fe_total_servicio_gravados", "fe_total_mercancias_gravadas" )
    def _compute_total_gravado(self):
        log.info('--> factelec/_compute_total_gravado')
        for s in self:
            s.fe_total_gravado = s.fe_total_servicio_gravados + s.fe_total_mercancias_gravadas


    def _compute_total_servicios_gravados(self):
        log.info('--> factelec/_compute_total_servicios_gravados')
        totalServGravados = 0
        for s in self:
            for i in s.invoice_line_ids:
                if i.product_id.type == 'Service':
                    if i.invoice_line_tax_ids:
                        totalAmount = i.price_unit * i.quantity
                        totalServGravados = totalServGravados + totalAmount

        self.fe_total_servicio_gravados = totalServGravados


    def _compute_total_servicios_exentos(self):
        log.info('--> factelec/_compute_total_servicios_exentos')
        totalServExentos = 0
        for s in self:
            for i in s.invoice_line_ids:
                if i.product_id.type == 'Service':
                    if i.invoice_line_tax_ids:
                        totalAmount = i.price_unit * i.quantity
                        totalServExentos = totalServExentos + totalAmount

        self.fe_total_servicio_exentos  = totalServExentos


    def _compute_total_mercancias_gravadas(self):
        log.info('--> factelec/_compute_total_mercancias_gravadas')
        totalMercanciasGravadas = 0
        for s in self:
            for i in s.invoice_line_ids:
                if i.product_id.type != 'Service':
                        if i.invoice_line_tax_ids:
                            totalAmount = i.price_unit * i.quantity
                            totalMercanciasGravadas = totalMercanciasGravadas + totalAmount
        self.fe_total_mercancias_gravadas =  totalMercanciasGravadas


    def _compute_total_mercancias_exentas(self):
        log.info('--> factelec/_compute_total_mercancias_exentas REPETIDO1')
        totalMercanciasExentas = 0
        for s in self:
            for i in s.invoice_line_ids:
                if i.product_id.type != 'Service':
                        if not i.invoice_line_tax_ids:
                            totalAmount = i.price_unit * i.quantity
                            totalMercanciasExentas = totalMercanciasExentas + totalAmount
        self.fe_total_mercancias_exentas =  totalMercanciasExentas



    @api.depends("fe_total_mercancias_exentas")
    def _compute_total_mercancias_exentas(self):
        log.info('--> factelec/_compute_total_mercancias_exentas REPETIDO2')
        total_mercancias_exentas = 0
        for s in self:
            for i in s.invoice_line_ids:
                if i.product_id.type != 'Service':
                    #asking for tax for know if the product is exempt
                    if not i.invoice_line_tax_ids:
                        totalAmount = i.price_unit * i.quantity
                        total_mercancias_exentas = total_mercancias_exentas + totalAmount

        self.fe_total_mercancias_exentas = total_mercancias_exentas

    def _remove_sign(self,xml):
        log.info('--> factelec/_remove_sign')
        ds = "http://www.w3.org/2000/09/xmldsig#"
        xades = "http://uri.etsi.org/01903/v1.3.2#"

        root_xml = fromstring(base64.b64decode(xml))
        ns2 = {"ds": ds, "xades": xades}
        signature = root_xml.xpath("//ds:Signature", namespaces=ns2)[0]
        root_xml.remove(signature)
        return root_xml

    def convert_xml_to_dic(self, xml):
        log.info('--> factelec-Invoice-convert_xml_to_dic')
        dic = xmltodict.parse(base64.b64decode(xml))
        return dic

    def get_doc_type(self, dic):
        log.info('--> factelec/get_doc_type')
        tag_TE = 'https://cdn.comprobanteselectronicos.go.cr/xml-schemas/v4.3/tiqueteElectronico'
        tag_FE = 'https://cdn.comprobanteselectronicos.go.cr/xml-schemas/v4.3/facturaElectronica'
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
            log.info('\n "error al obtener tipo de archivo xml %s"\n', e)
            return False

    @api.onchange("fe_xml_supplier_hacienda")
    def _onchange_xml_hacienda(self):
       #1569524732
       if self.fe_xml_supplier_hacienda:
           root_xml = self._remove_sign(self.fe_xml_supplier_hacienda)
           dic = self.convert_xml_to_dic(self.fe_xml_supplier_hacienda)
           if not dic.get("MensajeHacienda"):
               raise exceptions.Warning(("El xml de hacienda no es un archivo valido"))

    @api.onchange("fe_xml_supplier")
    def _onchange_xml_factura(self):
        #1569524296
        log.info('--> factelec/_onchange_field')
        if self.fe_xml_supplier:
            root_xml = self._remove_sign(self.fe_xml_supplier)
            dic = self.convert_xml_to_dic(self.fe_xml_supplier)
            if not dic.get("FacturaElectronica"):
                raise exceptions.Warning(("La factura xml no es un archivo de factura valido"))
            type = self.get_doc_type(dic)
            # 1570054332
            self.fe_xml_supplier_xslt = self.transform_doc(root_xml,type);
            self.update({'fe_clave' : dic['FacturaElectronica']['Clave']})
        else:
            return{
                'value': {
                            'fe_xml_supplier_xslt': None,
                            'fe_msg_type': None,
                            'fe_detail_msg':None,
                            'fe_clave':None,
                        }
            }


    def _cr_validate_mensaje_receptor(self):
        log.info('--> factelec-Invoice-_cr_validate_mensaje_receptor')
        #if self.state != 'open':  #Se cambio de 'open' a draft or cancel
        #if (self.state != 'open' and self.state != 'paid'):
        #   msg = 'La factura debe de estar en Open o Paid para poder confirmarse'
        #   raise exceptions.Warning((msg))
        if self.fe_msg_type == False:
            msg = 'Falta seleccionar el mensaje: Acepta, Acepta Parcial o Rechaza el documento'
            raise exceptions.Warning((msg))
        else:
            if self.fe_detail_msg == False and  self.fe_msg_type != '1':
                msg = 'Falta el detalle mensaje'
                raise exceptions.Warning((msg))


        log.info('===> XXXX VALIDACION QUE HAY ADJUNTO UN XML DEL EMISOR/PROVEEDOR')
        log.info('===> XXXX VALIDACION QUE EL XML ES DEL TIPO FacturaElectronica')


    def _cr_xml_mensaje_receptor(self):
        log.info('--> factelec-Invoice-_cr_xml_mensaje_receptor')

        bill_dic = self.convert_xml_to_dic(self.fe_xml_supplier)

        if 'FacturaElectronica' in bill_dic.keys():

            self.invoice = {self.fe_doc_type:{
                'Clave':bill_dic['FacturaElectronica']['Clave'],
                'NumeroCedulaEmisor':bill_dic['FacturaElectronica']['Emisor']['Identificacion']['Numero'],
                'TipoCedulaEmisor':bill_dic['FacturaElectronica']['Emisor']['Identificacion']['Tipo'],
                'FechaEmisionDoc':self.fe_fecha_emision_doc.split(' ')[0]+'T'+self.fe_fecha_emision_doc.split(' ')[1]+'-06:00',
                'Mensaje':self.fe_msg_type,
                'DetalleMensaje':self.fe_detail_msg,
                'CodigoActividad': self.fe_activity_code_id.code,
                'CondicionImpuesto':self.tax_condition,
                #PENDIENTE AGREGAR CAMPO 'MontoTotalImpuestoAcreditar':'PENDIENTE2 CALCULAR 0.00',
                #PENDIENTE AGREGAR CAMPO 'MontoTotalDeGastoAplicable':'PENDIENTE2 CALCULAR 0.00',
                'MontoTotalImpuesto':bill_dic['FacturaElectronica']['ResumenFactura']['TotalImpuesto'],
                'TotalFactura':bill_dic['FacturaElectronica']['ResumenFactura']['TotalComprobante'],
                'NumeroCedulaReceptor':bill_dic['FacturaElectronica']['Receptor']['Identificacion']['Numero'],
                'TipoCedulaReceptor':bill_dic['FacturaElectronica']['Receptor']['Identificacion']['Tipo'],
                'NumeroConsecutivoReceptor':self.number,
                #'EmisorEmail':self.partner_id.email,
                #'pdf':self._get_pdf_bill(self.id) or None,
                }}
        else:
            msg = 'adjunte una factura electronica antes de confirmar la aceptacion'
            raise exceptions.Warning((msg))

    def _cr_post_server_side(self):
        if not self.company_id.fe_certificate:
            raise exceptions.Warning(('No se encuentra el certificado en compañia'))
            
        log.info('--> factelec-Invoice-_cr_post_server_side')
        
        if self.number[8:10] == '05':
            self._cr_validate_mensaje_receptor()
            self._cr_xml_mensaje_receptor()
        else:
            self._cr_xml_factura_electronica()
        
        json_string = {
                      'invoice':self.invoice,
                      'certificate':base64.b64encode(self.company_id.fe_certificate).decode('utf-8'),
                      'token_user_name':self.company_id.fe_user_name,
                      }
        json_to_send = json.dumps(json_string)
        log.info('========== json to send : \n%s\n', json_string)
        header = {'Content-Type':'application/json'}
        url = self.env.user.company_id.fe_url_server
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


    def confirm_bill(self):
        log.info('--> factelec-Invoice-confirm_bill')
        if not 'http://' in self.company_id.fe_url_server and  not 'https://' in self.company_id.fe_url_server:
            raise ValidationError("El campo Server URL en comapañia no tiene el formato correcto, asegurese que contenga http://")

        if self.state == 'draft':
           raise exceptions.Warning('VALIDE primero este documento')

        elif not self.fe_payment_type:
           raise exceptions.Warning('Seleccione el TIPO de PAGO')

        if self.fe_xml_hacienda:
           raise exceptions.Warning("Ya se tiene la RESPUESTA de Hacienda")

        country_code = self.company_id.partner_id.country_id.code

        self.source_date = self.date_invoice

        if country_code == 'CR':
            self._validate_company()
            self.validacion()
            self._validate_invoice_line()

            if self.number[8:10] == "01":                    #FACTURA ELECTRONICA
                self.fe_doc_type = "FacturaElectronica"
                self._cr_post_server_side()

            elif self.number[8:10] == "02":                  #NOTA DEBITO ELECTRONICA
                self.fe_doc_type = "NotaDebitoElectronica"
                self._cr_post_server_side()

            elif self.number[8:10] == "03":                  #NOTA CREDITO ELECTRONICA
                self.fe_doc_type = "NotaCreditoElectronica"
                self._cr_post_server_side()

            elif self.number[8:10] == "05":                 #Vendor Bill - Mensaje Receptor - Aceptar Factura

                if self.fe_xml_hacienda:
                   msg = '--> Ya se tiene el XML de Hacienda Almacenado'
                   log.info(msg)
                   raise exceptions.Warning((msg))

                else:
                   self.fe_doc_type = "MensajeReceptor"
                   tz = pytz.timezone('America/Costa_Rica')
                   self.fe_fecha_emision_doc = datetime.now(tz=tz).strftime("%Y-%m-%d %H:%M:%S")
                   self._cr_post_server_side()

            elif self.number[8:10] == "08":                    #FACTURA ELECTRONICA COMPRA
                self.fe_doc_type = "FacturaElectronicaCompra"
                self._cr_post_server_side()

            elif self.number[8:10] == "09":                    #FACTURA ELECTRONICA COMPRA
                self.fe_doc_type = "FacturaElectronicaExportacion"
                self._cr_post_server_side()

    def transform_doc(self,root_xml,type):
        log.info('--> transform_doc')
        transform = None
        dom = ET.fromstring(tostring(root_xml,pretty_print=True))
        
        #filedir = os.path.dirname(os.path.realpath(__file__))
        #filepath = os.path.join(filedir, 'xslt/fe.xslt')
        ruta = path._path[0]+"/fe.xslt"
        if(type == 'FE'):
            transform = ET.XSLT(ET.parse(ruta))
        nuevodom = transform(dom)
        return ET.tostring(nuevodom, pretty_print=True)


    def _get_date(self, date):
       log.info('--> factelec/Invoice/_get_date')
       date_obj = datetime.strptime(date, "%Y-%m-%d")

       tm = pytz.timezone(self.env.user.tz or 'America/Costa_Rica')
       now_timezone  =  pytz.utc.localize(date_obj).astimezone(tm)
       date = now_timezone
       return date.strftime("%y-%m-%d").split('-')


    def _transform_date(self,date,tz):
        log.info('--> factelec-Invoice-_transform_date')
        new_date = ''
        if tz == "GMT":
             date_obj = datetime.strptime(date, "%Y-%m-%d %H:%M:%S")
             tm = pytz.timezone(self.env.user.tz or 'America/Costa_Rica')
             now_timezone  =  pytz.utc.localize(date_obj).astimezone(tm)
             new_date = now_timezone.isoformat('T')
        if tz == "UTC":
             new_date = datetime.strptime(date,"%Y-%m-%d %H:%M:%S").isoformat('T')+"Z"
        return new_date

    def _validate_company(self):
        log.info('--> _validate_company')
        error = False
        msg = 'En Compania:\n'
        if not self.company_id.country_id:
            error = True
            msg += "El pais de la compañia es requerido.\n"

        if not self.company_id.fe_url_server:
            error = True
            msg += "Configure el URL del Servidor en Settings/User & Companies/ TAB: Factura Electronica -> URL\n"
        if not self.company_id.fe_activity_code_ids:
            error = True
            msg += "Falta agregar codigo de actividad en Settings/User & Companies/TAB: Factura Electronica\n"
        if error:
            raise exceptions.Warning((msg))

    def _validate_invoice_line(self):
        units = ['Al', 'Alc', 'Cm', 'I', 'Os', 'Sp', 'Spe', 'St', 'd', 'm', 'kg', 's', 'A', 'K', 'mol', 'cd', 'm²', 'm³', 'm/s', 'm/s²', '1/m', 'kg/m³', 'A/m²', 'A/m', 'mol/m³', 'cd/m²', '1', 'rad', 'sr', 'Hz', 'N', 'Pa', 'J', 'W', 'C', 'V', 'F', 'Ω', 'S', 'Wb', 'T', 'H', '°C', 'lm', 'lx', 'Bq', 'Gy', 'Sv', 'kat', 'Pa·s', 'N·m', 'N/m', 'rad/s', 'rad/s²', 'W/m²', 'J/K', 'J/(kg·K)', 'J/kg', 'W/(m·K)', 'J/m³', 'V/m', 'C/m³', 'C/m²', 'F/m', 'H/m', 'J/mol', 'J/(mol·K)', 'C/kg', 'Gy/s', 'W/sr', 'W/(m²·sr)', 'kat/m³', 'min', 'h', 'd', 'º', '´', '´´', 'L', 't', 'Np', 'B', 'eV', 'u', 'ua', 'Unid', 'Gal', 'g', 'Km', 'Kw', 'ln', 'cm', 'mL', 'mm', 'Oz', 'Otros']
        log.info('--> _validate_invoice_line')
        for line in self.invoice_line_ids:

            if line.uom_id.name not in units:
                raise exceptions.Warning(("La unidad de medida {0} no corresponde a una unidad valida en el ministerio de hacienda".format(line.uom_id.name)))
                return

            if line.invoice_line_tax_ids:

               for tax_id in line.invoice_line_tax_ids:

                  if tax_id.type == 'OTHER':
                     if not tax_id.tipo_documento:
                        raise exceptions.Warning(("CONFIGURE el TIPO de DOCUMENTO de OTROS CARGOS  en Accounting/Configuration/Taxes"))
                        return
                  else:
                     if not tax_id.codigo_impuesto:
                        raise exceptions.Warning(("CONFIGURE el TIPO de IMPUESTO en Accounting/Configuration/Taxes"))
                        return

                     if not tax_id.tarifa_impuesto:
                        raise exceptions.Warning(("Configure la TARIFA de IMPUESTO en Accounting/Configuration/Taxes"))
                        return




    def validate_journal(self):
        msg = ""
        error = False
        if "INV" in self.journal_id.sequence_id.prefix:
            error = True
            msg += 'Factura Electronica: El Numero Consecutivo configurado es el default por Odoo (INV...), se tiene que cambiar\n \
                    Configurar en Customer Invoices/OtherInfo/Journal/Link al Next Sequence Number/prefix\n\n'
        if self.journal_id.refund_sequence:
            if "RINV" in self.journal_id.refund_sequence_id.prefix:
                error = True
                msg += 'Notas de Credito: El Numero Consecutivo configurado es el default por Odoo (RINV...), se tiene que cambiar\n \
                        Configurar en Customer Invoices/OtherInfo/Journal/Link al Credit Notes: Next Number/prefix\n\n'
        else:
            error = True
            msg += 'Notas de Credito: Active la opcion de secuencia dedicada de notas de credito\n \
                    Configurar en Customer Invoices/OtherInfo/Journal\n\n'

        if len(self.journal_id.sequence_id.prefix) != 10:
            error = True
            msg += 'Factura Electronica: El Prefijo en la SECUENCIA del Journal debe tener 10 digitos\n \
                    Ejemplo de Factura Electronica:\n \
                    la compania (Ej: 001)\n \
                    la terminal (Ej: 00001)\n \
                    El tipo de documento electronico (Ej: 01 Factura Electronica)\n \
                    Ejemplo Factura Electronica Odoo PREFIX = 0010000101\n \
                    Configurar en Customer Invoices/OtherInfo/Journal/Link al Next Sequence Number/prefix\n\n'

        if len(self.journal_id.refund_sequence_id.prefix) != 10:
            error = True
            msg += 'Nota de Credito: El Prefijo en la SECUENCIA del Journal debe tener 10 digitos\n \
                    Ejemplo de Nota de Credito:\n \
                    la compania (Ej: 001)\n \
                    la terminal (Ej: 00001)\n \
                    El tipo de documento electronico (Ej: 03 Nota de Credito)\n \
                    Ejemplo Nota Credito Electronica Odoo PREFIX = 0010000103\n \
                    Configurar en Customer Invoices/OtherInfo/Journal/Link al Credit Notes: Next Number/prefix\n\n'

        if self.journal_id.sequence_id.padding != 10:
            error = True
            msg += 'Factura Electronica: La Secuencia debe ser 10\n \
                    Ejemplo Odoo Sequence Size = 10\n\
                    Configurar en Customer Invoices/OtherInfo/Journal/Link al Next Sequence Number/Sequence Size\n\n'

        if self.journal_id.refund_sequence_id.padding != 10:
            error = True
            msg += 'Nota de Credito: La Secuencia debe ser 10\n \
                    Ejemplo Odoo Sequence Size = 10\n\
                    Configurar en Customer Invoices/OtherInfo/Journal/Link al Credit Notes: Next Number/Sequence Size\n\n'

        if self.journal_id.sequence_id.use_date_range:
            error = True
            msg += 'Factura Electronica: Desabilitar el uso de Numero Consecutivo por Año\n \
                    UNCHECK en Customer Invoices/OtherInfo/Journal/Link al Next Sequence Number/Use subsequences per date_range\n\n'

        if self.journal_id.refund_sequence_id.use_date_range:
            error = True
            msg += 'Nota Debito: Desabilitar el uso de Numero Consecutivo por Año\n \
                    UNCHECK en Customer Invoices/OtherInfo/Journal/Link al Credit Notes: Next Number/Use subsequences per date_range\n\n'
        if not self.journal_id.refund_sequence:
            error = True
            msg += 'Nota de Credito: NO tiene una Secuencia Separada a las Facturas\n \
                    Configurar en Customer Invoices/OtherInfo/Journal/Check en Dedicated Credit Note Sequence\n \
                    luego Refresh a la página, para que aparezca el link a la secuencia de las notas de crédito\n\n'
        if error == True:
            raise exceptions.Warning(msg)

    def _try_parse_int(self,param):
            try:
                return True
            except IgnoreException:
                return False

    def _getField(self,param):
        log.info('\n ========== get field param : %s\n', param)
        list = param.split('.')
        obj = None
        for index, item in enumerate(list, start=0):

            if index == 0:
                obj = getattr(self,item)
            else:
                obj = getattr(obj,item)
        return obj

    def _validate_size_type_pattern(self,obj,validation,key):

        if len(obj) < validation[key]['Tamano']['Min'] or len(obj) > validation[key]['Tamano']['Max']:
            self.mensaje_validacion += validation[key]['Mensaje']+" debe ser como minimo "+str(validation[key]['Tamano']['Min'])+" y como máximo "+str(validation[key]['Tamano']['Max'])+"\n"
        if validation[key]['Tipo'] == 'Integer':
            if not self._try_parse_int(obj):
                self.mensaje_validacion += validation[key]['Mensaje'] +" debe ser un numero entero"+'\n'
        if validation[key]['Patron'] != '':
            if not re.search(obj,validation[key]['Patron']):
                self.mensaje_validacion += validation[key]['Mensaje']+" no cumple con el formato correcto "+validation[key]['Patron']+'\n'

    def validacion(self):
        tipo = self.number[8:10]
        log.info(tipo)
        if tipo !='01' and tipo !='02' and tipo !='03' and tipo  != '05' and tipo  !='08' and tipo !='09':
            raise exceptions.Warning(("Configure el prefijo del diario contable para facturación electronica antes de validar"))
        emisor_str = ""
        receptor_str = ""

        translate = {}
        if self.type == 'out_invoice' or self.type == 'out_refund':
            if tipo =='01' or tipo =='02' or tipo =='03' or tipo =='09':
                emisor_str = "Compañia"
                receptor_str = "Cliente"
                emisor = "company_id"
                receptor = "partner_id"
                translate['Emisor-Nombre'] = emisor+'.company_registry'
                translate['Receptor-Nombre'] = receptor+'.fe_comercial_name'
        elif  self.type == 'in_invoice' or self.type == 'in_refund':   
            if tipo  == '05' or tipo  =='08':
                emisor_str = "Proveedor"
                receptor_str = "Compañia" 
                emisor = "partner_id"
                receptor = "company_id"
                translate['Emisor-Nombre'] = emisor+'.fe_comercial_name'
                translate['Receptor-Nombre'] = receptor+'.company_registry'
                

        
        translate['CodigoActividad'] = 'fe_activity_code_id.code'
        translate['Clave'] = 'fe_clave'
        translate['PlazoCredito'] = 'payment_term_id.name'
        translate['NumeroConsecutivo'] = 'number'
        translate['FechaEmision'] = 'fe_fecha_emision'
        translate['Emisor-Identifacion-Tipo'] = emisor+'.fe_identification_type'
        translate['Emisor-Identifacion-Numero'] = emisor+'.vat'
        translate['Emisor-Ubicacion-Provincia'] = emisor+'.state_id.fe_code'
        translate['Emisor-Ubicacion-Canton'] = emisor+'.fe_canton_id.code'
        translate['Emisor-Ubicacion-Distrito'] = emisor+'.fe_district_id.code'
        translate['Emisor-Ubicacion-Barrio'] = emisor+'.fe_neighborhood_id.code'
        translate['Emisor-Ubicacion-OtrasSenas'] = emisor+'.fe_other_signs'
        translate['Emisor-Telefono-NumTelefono'] = emisor+'.phone'
        translate['Emisor-Fax-NumTelefono'] = emisor+'.fe_fax_number'
        translate['Emisor-CorreoElectronico'] = emisor+'.email'

        #translate['Receptor-Nombre'] = receptor+'.fe_comercial_name'

        translate['Receptor-TipoIdentifacion'] = receptor+'.fe_identification_type'
        translate['Receptor-NumeroIdentifacion'] = receptor+'.vat'
        translate['Receptor-Ubicacion-Provincia'] = receptor+'.state_id.fe_code'
        translate['Receptor-Ubicacion-Canton'] = receptor+'.fe_canton_id.code'
        translate['Receptor-Ubicacion-Distrito'] = receptor+'.fe_district_id.code'
        translate['Receptor-Ubicacion-Barrio'] = receptor+'.fe_neighborhood_id.code'
        translate['Receptor-Ubicacion-OtrasSenas'] = receptor+'.fe_other_signs'
        translate['Receptor-Telefono-NumTelefono'] = receptor+'.phone'
        translate['Receptor-Fax-NumTelefono'] = receptor+'.fe_fax_number'
        translate['Receptor-CorreoElectronico'] = receptor+'.email'
        translate['CondicionVenta'] = 'payment_term_id.fe_condition_sale'
        translate['MedioPago'] = 'fe_payment_type'
        translate['Mensaje'] = 'fe_msg_type'


        validation = {}
        validation['CodigoActividad'] = {}
        validation['CodigoActividad']['CondicionCampo'] = {'01':'1','09':'1','08':'1','05':'1','03':'1','02':'1'}
        validation['CodigoActividad']['Tipo'] = 'String'
        validation['CodigoActividad']['Tamano'] = {'Min':6,'Max':6}
        validation['CodigoActividad']['Patron'] = ''
        validation['CodigoActividad']['Mensaje'] = 'Seleccionar la actividad económica'
        validation['CodigoActividad']['Padre'] = ''

        validation['Clave'] = {}
        validation['Clave']['CondicionCampo'] =  {'01':'1','09':'1','08':'1','05':'1','03':'1','02':'1'}
        validation['Clave']['Tipo'] = 'String'
        validation['Clave']['Tamano']  = {'Min':50,'Max':50}
        validation['Clave']['Patron'] = ''
        validation['Clave']['Mensaje'] = 'La clave'
        validation['Clave']['Padre'] = ''
        
        
        validation['PlazoCredito'] = {}
        validation['PlazoCredito']['CondicionCampo'] =  {'01':'1','09':'1','08':'1','05':'1','03':'1','02':'1'}
        validation['PlazoCredito']['Tipo'] = 'String'
        validation['PlazoCredito']['Tamano']  = {'Min':1,'Max':10}
        validation['PlazoCredito']['Patron'] = ''
        validation['PlazoCredito']['Mensaje'] = 'El nombre plazo pago'
        validation['PlazoCredito']['Padre'] = ''

        validation['NumeroConsecutivo'] = {}
        validation['NumeroConsecutivo']['CondicionCampo'] =  {'01':'1','09':'1','08':'1','05':'1','03':'1','02':'1'}
        validation['NumeroConsecutivo']['Tipo'] = 'String'
        validation['NumeroConsecutivo']['Tamano'] = {'Min':20,'Max':20}
        validation['NumeroConsecutivo']['Patron'] = ''
        validation['NumeroConsecutivo']['Mensaje'] = 'El numero consecutivo'
        validation['NumeroConsecutivo']['Padre'] = ''

        validation['FechaEmision'] = {}
        validation['FechaEmision']['CondicionCampo'] = {'01':'1','09':'1','08':'1','05':'1','03':'1','02':'1'}
        validation['FechaEmision']['Tipo'] = 'DateTime'
        validation['FechaEmision']['Tamano'] = {'Min':1,'Max':100}
        validation['FechaEmision']['Patron'] = ''
        validation['FechaEmision']['Mensaje'] = 'La fecha emisión'
        validation['FechaEmision']['Padre'] = ''
        
        validation['Mensaje'] = {}
        validation['Mensaje']['CondicionCampo'] = {'01':'2','09':'2','08':'2','05':'2','03':'2','02':'2'}
        validation['Mensaje']['Tipo'] = 'String'
        validation['Mensaje']['Tamano'] = {'Min':1,'Max':100}
        validation['Mensaje']['Patron'] = ''
        validation['Mensaje']['Mensaje'] = 'El mensaje'
        validation['Mensaje']['Padre'] = ''

        validation['Emisor-Nombre'] = {}
        validation['Emisor-Nombre']['CondicionCampo'] = {'01':'1','09':'1','08':'2','05':'2','03':'1','02':'1'}
        validation['Emisor-Nombre']['Tipo'] = 'String'
        validation['Emisor-Nombre']['Tamano'] = {'Min':1,'Max':100}
        validation['Emisor-Nombre']['Patron'] = ''
        validation['Emisor-Nombre']['Mensaje'] = 'El nombre del ' + emisor_str
        validation['Emisor-Nombre']['Padre'] = ''

        validation['Emisor-Identifacion-Tipo'] = {}
        validation['Emisor-Identifacion-Tipo']['CondicionCampo'] = {'01':'1','09':'1','08':'1','05':'1','03':'1','02':'1'}
        validation['Emisor-Identifacion-Tipo']['Tipo'] = 'String'
        validation['Emisor-Identifacion-Tipo']['Tamano'] = {'Min':2,'Max':2}
        validation['Emisor-Identifacion-Tipo']['Patron'] = ''
        validation['Emisor-Identifacion-Tipo']['Mensaje'] = 'El tipo de identificación del '+emisor_str
        validation['Emisor-Identifacion-Tipo']['Padre'] = ''
        
        validation['Emisor-Identifacion-Numero'] = {}
        validation['Emisor-Identifacion-Numero']['CondicionCampo'] = {'01':'1','09':'1','08':'1','05':'1','03':'1','02':'1'}
        validation['Emisor-Identifacion-Numero']['Tipo'] = 'String'
        validation['Emisor-Identifacion-Numero']['Tamano'] = {'Min':9,'Max':12}
        validation['Emisor-Identifacion-Numero']['Patron'] = ''
        validation['Emisor-Identifacion-Numero']['Mensaje'] = 'El numero de identificación del '+emisor_str
        validation['Emisor-Identifacion-Numero']['Padre'] = ''
        
        validation['Emisor-Ubicacion-Provincia'] = {}
        validation['Emisor-Ubicacion-Provincia']['CondicionCampo'] = {'01':'1','09':'1','08':'1','05':'2','03':'1','02':'1'}
        validation['Emisor-Ubicacion-Provincia']['Tamano'] = {'Min':1,'Max':1}
        validation['Emisor-Ubicacion-Provincia']['Tipo'] = 'String'
        validation['Emisor-Ubicacion-Provincia']['Patron'] = ''
        validation['Emisor-Ubicacion-Provincia']['Mensaje'] = 'Seleccionar provincia o configurar el codigo de factura electronica en la provincia '+emisor_str
        validation['Emisor-Ubicacion-Provincia']['Padre'] = ''
        
        validation['Emisor-Ubicacion-Canton'] = {}
        validation['Emisor-Ubicacion-Canton']['CondicionCampo'] = {'01':'1','09':'1','08':'1','05':'2','03':'1','02':'1'}
        validation['Emisor-Ubicacion-Canton']['Tipo'] = 'String'
        validation['Emisor-Ubicacion-Canton']['Tamano'] = {'Min':2,'Max':2}
        validation['Emisor-Ubicacion-Canton']['Patron'] = ''
        validation['Emisor-Ubicacion-Canton']['Mensaje'] = 'El canton del '+emisor_str
        validation['Emisor-Ubicacion-Canton']['Padre'] = ''
        
        validation['Emisor-Ubicacion-Distrito'] = {}
        validation['Emisor-Ubicacion-Distrito']['CondicionCampo'] = {'01':'1','09':'1','08':'1','05':'2','03':'1','02':'1'}
        validation['Emisor-Ubicacion-Distrito']['Tipo'] = 'String'
        validation['Emisor-Ubicacion-Distrito']['Tamano'] = {'Min':2,'Max':2}
        validation['Emisor-Ubicacion-Distrito']['Patron'] = ''
        validation['Emisor-Ubicacion-Distrito']['Mensaje'] = 'El distrito del '+emisor_str
        validation['Emisor-Ubicacion-Distrito']['Padre'] = ''
        
        validation['Emisor-Ubicacion-Barrio'] = {}
        validation['Emisor-Ubicacion-Barrio']['CondicionCampo'] = {'01':'2','09':'2','08':'2','05':'2','03':'2','02':'2'}
        validation['Emisor-Ubicacion-Barrio']['Tipo'] = 'String'
        validation['Emisor-Ubicacion-Barrio']['Tamano'] = {'Min':2,'Max':2}
        validation['Emisor-Ubicacion-Barrio']['Patron'] = ''
        validation['Emisor-Ubicacion-Barrio']['Mensaje'] = 'El barrio del '+emisor_str
        validation['Emisor-Ubicacion-Barrio']['Padre'] = ''
        
        validation['Emisor-Ubicacion-OtrasSenas'] = {}
        validation['Emisor-Ubicacion-OtrasSenas']['CondicionCampo'] = {'01':'1','09':'1','08':'1','05':'2','03':'1','02':'1'}
        validation['Emisor-Ubicacion-OtrasSenas']['Tipo'] = 'String'
        validation['Emisor-Ubicacion-OtrasSenas']['Tamano'] = {'Min':1,'Max':250}
        validation['Emisor-Ubicacion-OtrasSenas']['Patron'] = ''
        validation['Emisor-Ubicacion-OtrasSenas']['Mensaje'] = 'Las otras señas del '+emisor_str
        validation['Emisor-Ubicacion-OtrasSenas']['Padre'] = ''
        
        validation['Emisor-Telefono-NumTelefono'] = {}
        validation['Emisor-Telefono-NumTelefono']['CondicionCampo'] = {'01':'1','09':'1','08':'2','05':'2','03':'2','02':'2'}
        validation['Emisor-Telefono-NumTelefono']['Tipo'] = 'Integer'
        validation['Emisor-Telefono-NumTelefono']['Tamano'] = {'Min':8,'Max':20}
        validation['Emisor-Telefono-NumTelefono']['Patron'] = ''
        validation['Emisor-Telefono-NumTelefono']['Mensaje'] = 'El numero de telefono del '+emisor_str
        validation['Emisor-Telefono-NumTelefono']['Padre'] = ''
        
        validation['Emisor-Fax-NumTelefono'] = {}
        validation['Emisor-Fax-NumTelefono']['CondicionCampo'] = {'01':'2','09':'2','08':'2','05':'2','03':'2','02':'2'}
        validation['Emisor-Fax-NumTelefono']['Tipo'] = 'Integer'
        validation['Emisor-Fax-NumTelefono']['Tamano'] = {'Min':8,'Max':20}
        validation['Emisor-Fax-NumTelefono']['Patron'] = ''
        validation['Emisor-Fax-NumTelefono']['Mensaje'] = 'El numero de fax del '+emisor_str
        validation['Emisor-Fax-NumTelefono']['Padre'] = ''
        
        validation['Emisor-CorreoElectronico'] = {}
        validation['Emisor-CorreoElectronico']['CondicionCampo'] = {'01':'1','09':'1','08':'1','05':'2','03':'1','02':'1'}
        validation['Emisor-CorreoElectronico']['Tipo'] = 'String'
        validation['Emisor-CorreoElectronico']['Tamano'] = {'Min':1,'Max':160}
        validation['Emisor-CorreoElectronico']['Patron'] = ''
        validation['Emisor-CorreoElectronico']['Mensaje'] = 'El correo electronico del '+emisor_str
        validation['Emisor-CorreoElectronico']['Padre'] = ''
        #Receptor
        validation['Receptor-Nombre'] = {}
        validation['Receptor-Nombre']['CondicionCampo'] = {'01':'2','09':'2','08':'1','05':'1','03':'2','02':'2'}
        validation['Receptor-Nombre']['Tipo'] = 'String'
        validation['Receptor-Nombre']['Tamano'] = {'Min':1,'Max':100}
        validation['Receptor-Nombre']['Patron'] = ''
        validation['Receptor-Nombre']['Mensaje'] = 'El nombre de la razon social '+receptor_str
        validation['Receptor-Nombre']['Padre'] = ''

        validation['Receptor-TipoIdentifacion'] = {}
        validation['Receptor-TipoIdentifacion']['CondicionCampo'] = {'01':'1','09':'2','08':'1','05':'1','03':'2','02':'2'}
        validation['Receptor-TipoIdentifacion']['Tipo'] = 'String'
        validation['Receptor-TipoIdentifacion']['Tamano'] = {'Min':2,'Max':2}
        validation['Receptor-TipoIdentifacion']['Patron'] = ''
        validation['Receptor-TipoIdentifacion']['Mensaje'] = 'El tipo de identificacion del '+receptor_str
        validation['Receptor-TipoIdentifacion']['Padre'] = ''
        
        validation['Receptor-NumeroIdentifacion'] = {}
        validation['Receptor-NumeroIdentifacion']['CondicionCampo'] = {'01':'1','09':'2','08':'1','05':'1','03':'2','02':'2'}
        validation['Receptor-NumeroIdentifacion']['Tipo'] = 'String'
        validation['Receptor-NumeroIdentifacion']['Tamano'] = {'Min':9,'Max':12}
        validation['Receptor-NumeroIdentifacion']['Patron'] = ''
        validation['Receptor-NumeroIdentifacion']['Mensaje'] = 'El numero de identificacion del '+receptor_str
        validation['Receptor-NumeroIdentifacion']['Padre'] = ''
        
        validation['Receptor-Ubicacion-Provincia'] = {}
        validation['Receptor-Ubicacion-Provincia']['CondicionCampo'] = {'01':'2','09':'2','08':'1','05':'1','03':'2','02':'2'}
        validation['Receptor-Ubicacion-Provincia']['Tipo'] = 'String'
        validation['Receptor-Ubicacion-Provincia']['Tamano'] = {'Min':1,'Max':1}
        validation['Receptor-Ubicacion-Provincia']['Patron'] = ''
        validation['Receptor-Ubicacion-Provincia']['Mensaje'] = 'La provincia del '+receptor_str
        validation['Receptor-Ubicacion-Provincia']['Padre'] = ''
        
        validation['Receptor-Ubicacion-Canton'] = {}
        validation['Receptor-Ubicacion-Canton']['CondicionCampo'] = {'01':'2','09':'2','08':'2','05':'2','03':'2','02':'2'}
        validation['Receptor-Ubicacion-Canton']['Tipo'] = 'String'
        validation['Receptor-Ubicacion-Canton']['Tamano'] = {'Min':2,'Max':2}
        validation['Receptor-Ubicacion-Canton']['Patron'] = ''
        validation['Receptor-Ubicacion-Canton']['Mensaje'] = 'El canton del '+receptor_str
        validation['Receptor-Ubicacion-Canton']['Padre'] = 'Receptor-Ubicacion-Provincia'
        
        validation['Receptor-Ubicacion-Distrito'] = {}
        validation['Receptor-Ubicacion-Distrito']['CondicionCampo'] = {'01':'2','09':'2','08':'2','05':'2','03':'2','02':'2'}
        validation['Receptor-Ubicacion-Distrito']['Tipo'] = 'String'
        validation['Receptor-Ubicacion-Distrito']['Tamano'] = {'Min':2,'Max':2}
        validation['Receptor-Ubicacion-Distrito']['Patron'] = ''
        validation['Receptor-Ubicacion-Distrito']['Mensaje'] = 'El distrito del '+receptor_str
        validation['Receptor-Ubicacion-Distrito']['Padre'] = 'Receptor-Ubicacion-Provincia'
        
        validation['Receptor-Ubicacion-Barrio'] = {}
        validation['Receptor-Ubicacion-Barrio']['CondicionCampo'] = {'01':'2','09':'2','08':'2','05':'2','03':'2','02':'2'}
        validation['Receptor-Ubicacion-Barrio']['Tipo'] = 'String'
        validation['Receptor-Ubicacion-Barrio']['Tamano'] = {'Min':2,'Max':2}
        validation['Receptor-Ubicacion-Barrio']['Patron'] = ''
        validation['Receptor-Ubicacion-Barrio']['Mensaje'] = 'El barrio del '+receptor_str
        validation['Receptor-Ubicacion-Barrio']['Padre'] = ''
        
        validation['Receptor-Ubicacion-OtrasSenas'] = {}
        validation['Receptor-Ubicacion-OtrasSenas']['CondicionCampo'] = {'01':'2','09':'2','08':'2','05':'2','03':'2','02':'2'}
        validation['Receptor-Ubicacion-OtrasSenas']['Tipo'] = 'String'
        validation['Receptor-Ubicacion-OtrasSenas']['Tamano'] = {'Min':1,'Max':250}
        validation['Receptor-Ubicacion-OtrasSenas']['Patron'] = ''
        validation['Receptor-Ubicacion-OtrasSenas']['Mensaje'] = 'Las otras señas del '+receptor_str
        validation['Receptor-Ubicacion-OtrasSenas']['Padre'] = 'Receptor-Ubicacion-Provincia'
        
        validation['Receptor-Telefono-NumTelefono'] = {}
        validation['Receptor-Telefono-NumTelefono']['CondicionCampo'] = {'01':'2','09':'2','08':'2','05':'2','03':'2','02':'2'}
        validation['Receptor-Telefono-NumTelefono']['Tipo'] = 'Integer'
        validation['Receptor-Telefono-NumTelefono']['Tamano'] = {'Min':8,'Max':20}
        validation['Receptor-Telefono-NumTelefono']['Patron'] = ''
        validation['Receptor-Telefono-NumTelefono']['Mensaje'] = 'El numero de telefono del '+receptor_str
        validation['Receptor-Telefono-NumTelefono']['Padre'] = ''
        
        validation['Receptor-Fax-NumTelefono'] = {}
        validation['Receptor-Fax-NumTelefono']['CondicionCampo'] = {'01':'2','09':'2','08':'2','05':'2','03':'2','02':'2'}
        validation['Receptor-Fax-NumTelefono']['Tipo'] = 'Integer'
        validation['Receptor-Fax-NumTelefono']['Tamano'] = {'Min':8,'Max':20}
        validation['Receptor-Fax-NumTelefono']['Patron'] = ''
        validation['Receptor-Fax-NumTelefono']['Mensaje'] = 'El numero de fax del '+receptor_str
        validation['Receptor-Fax-NumTelefono']['Padre'] = ''
        
        validation['Receptor-CorreoElectronico'] = {}
        validation['Receptor-CorreoElectronico']['CondicionCampo'] = {'01':'1','09':'1','08':'1','05':'1','03':'1','02':'1'}
        validation['Receptor-CorreoElectronico']['Tipo'] = 'String'
        validation['Receptor-CorreoElectronico']['Tamano'] = {'Min':1,'Max':160}
        validation['Receptor-CorreoElectronico']['Patron'] = ''
        validation['Receptor-CorreoElectronico']['Mensaje'] = 'El correo electronico del '+receptor_str
        validation['Receptor-CorreoElectronico']['Padre'] = ''

        validation['CondicionVenta'] = {}
        validation['CondicionVenta']['CondicionCampo'] = {'01':'1','09':'1','08':'1','05':'1','03':'1','02':'1'}
        validation['CondicionVenta']['Tipo'] = 'String'
        validation['CondicionVenta']['Tamano'] = {'Min':2,'Max':2}
        validation['CondicionVenta']['Patron'] = ''
        validation['CondicionVenta']['Mensaje'] = 'Tipo de pago o configuración en plazos de pago el tipo de pago'
        validation['CondicionVenta']['Padre'] = ''
        '''plazo credito'''
        validation['MedioPago'] = {}
        validation['MedioPago']['CondicionCampo'] = {'01':'1','09':'1','08':'1','05':'1','03':'2','02':'2'}
        validation['MedioPago']['Tipo'] = 'String'
        validation['MedioPago']['Tamano'] = {'Min':2,'Max':2}
        validation['MedioPago']['Patron'] = ''
        validation['MedioPago']['Mensaje'] = 'El medio de pago'
        validation['MedioPago']['Padre'] = ''

        for key in validation:
            if validation[key]['CondicionCampo'][tipo] == "1":
                translate_key = translate[key]
                obj = self._getField(translate_key)
                if obj:
                    self._validate_size_type_pattern(obj,validation,key)
                else:
                    self.mensaje_validacion += 'Falta '+validation[key]['Mensaje']+'\n'

            elif validation[key]['CondicionCampo'][tipo] == "2":
                if validation[key]['Padre'] != '':
                    padre_translate_key = translate[ validation[key]['Padre']  ]
                    obj_padre = self._getField(padre_translate_key)
                    if obj_padre:
                        translate_key = translate[key]
                        obj = self._getField(translate_key)
                        if obj:
                            self._validate_size_type_pattern(obj,validation,key)
                        else:
                            self.mensaje_validacion += 'Falta '+validation[key]['Mensaje']+'\n'
                else:
                    translate_key = translate[key]
                    obj = self._getField(translate_key)
                    if obj:
                        self._validate_size_type_pattern(obj,validation,key)

        if self.mensaje_validacion != '':
            raise ValidationError(self.mensaje_validacion)
            self.mensaje_validacion = ''

    def _generar_clave(self):
        document_date_invoice = datetime.strptime(self.date_invoice,'%Y-%m-%d')
        if self.fe_doc_type != "MensajeReceptor":
           country_code = self.company_id.country_id.phone_code
           vat = self.company_id.vat or ''
           vat = vat.replace('-','')
           vat = vat.replace(' ','')
           vat_complete = "0" * (12 - len(vat)) + vat
           clave = str(country_code) + document_date_invoice.strftime("%d%m%y") \
              + str(vat_complete) + str(self.number) + str(self.fe_receipt_status) \
              + str("87654321")
           self.fe_clave = clave


    def action_invoice_open(self,validate = True):
        for s in self:
            log.info('--> action_invoice_open')
            if s.company_id.country_id.code == 'CR' and s.fe_in_invoice_type != 'OTRO':
                if validate:
                            if s.fe_msg_type != '3':
                                log.info('--> 1570130084')
                                for item in s.invoice_line_ids:
                                    if item.price_subtotal == False:
                                        return {
                                                'type': 'ir.actions.act_window',
                                                'name': '¡Alerta!',
                                                'res_model': 'confirm.message',
                                                'view_type': 'form',
                                                'view_mode': 'form',
                                                'views': [(False, 'form')],
                                                'target': 'new',
                                                'context': {'invoice': s.id}
                                        }
                                #es mensaje de aceptacion??
                                if len(s.journal_id.sequence_id.prefix) >= 10:
                                    if s.journal_id.sequence_id.prefix[8:10] == '05':
                                            if s.fe_msg_type == False:
                                                msg = 'Falta seleccionar el mensaje: Acepta, Acepta Parcial o Rechaza el documento'
                                                raise exceptions.Warning((msg))

                                            bill_dic = s.convert_xml_to_dic(s.fe_xml_supplier)
                                            total = bill_dic['FacturaElectronica']['ResumenFactura']['TotalComprobante']
                                            if float(total) != s.amount_total:
                                                return {
                                                    'type': 'ir.actions.act_window',
                                                    'name': '¡Alerta!',
                                                    'res_model': 'confirm.alert',
                                                    'view_type': 'form',
                                                    'view_mode': 'form',
                                                    'views': [(False, 'form')],
                                                    'target': 'new',
                                                    'context': {'invoice': s.id}
                                                }
                            else:

                                if s.fe_msg_type == False:
                                    msg = 'Falta seleccionar el mensaje: Acepta, Acepta Parcial o Rechaza el documento'
                                    raise exceptions.Warning((msg))
                                else:
                                    if s.fe_detail_msg == False and  s.fe_msg_type != '1':
                                        msg = 'Falta el detalle mensaje'
                                        raise exceptions.Warning((msg))
                                    if s.fe_msg_type == '3':
                                        if s.amount_total > 0:
                                            raise exceptions.Warning('Esta factura fue rechazada, por lo tanto su total no puede ser mayor a cero')
                                    



                date_temp = s.date_invoice 
                log.info('--> 1575061615')
                res = super(Invoice, s).action_invoice_open()
                tz = pytz.timezone('America/Costa_Rica')
                
                if not date_temp:
                    s.fe_fecha_emision = datetime.now(tz=tz).strftime("%Y-%m-%d %H:%M:%S")
                    s.date_invoice = s.fe_fecha_emision
                else:
                    s.fe_fecha_emision = '{0} 00:00:00'.format(date_temp) 
                
                s._validate_company()
                if s.number[8:10] != '05':
                    s._generar_clave()
                log.info('--->Clave %s',s.fe_clave)
                s.validacion()
                s._validate_invoice_line()
            else:
                log.info('--> 1575061637')
                res = super(Invoice, s).action_invoice_open()



    def get_invoice(self):
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

            if s.number[8:10] == "05":
               url = s.company_id.fe_url_server+'{0}'.format(s.fe_clave+'-'+s.number)
            else:
               url = s.company_id.fe_url_server+'{0}'.format(s.fe_clave)

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
                
                
    def _get_pdf_bill(self,id):
        log.info('--> _get_pdf_bill')
        ctx = self.env.context.copy()
        ctx.pop('default_type', False)
        pdf = self.env.ref('account.account_invoices_without_payment').with_context(ctx).render(id)
        pdf64 = base64.b64encode(pdf[0]).decode('utf-8')
        return pdf64


    @api.model
    def cron_get_server_bills(self):
        log.info('--> cron_get_server_bills')
        list = self.env['account.invoice'].search(['|',('fe_xml_sign','=',False),('fe_xml_hacienda','=',False),'&',('state','=','open'),
        ('fe_server_state','!=','pendiente enviar')])

        array = []
        dic = {}

        for item in list:
            if item.company_id.country_id.code == 'CR' and item.fe_in_invoice_type != 'OTRO':
                item.get_invoice()
                '''if item.fe_clave:
                   if item.type == 'in_invoice' and item.fe_clave:   #CAMBIO se agrego and item.fe_clave
                      array.append(item.fe_clave+'-'+item.number)
                   else:
                      array.append(item.fe_clave)
                '''

        '''
        dic['ids'] = array
        json_string = json.dumps(dic)
        header = {'Content-Type':'application/json'}
        #url = "http://35.222.38.247/api/1v/billing"
        url = self.env.user.company_id.fe_url_server

        response = requests.get(url, headers = header, data = json_string)

        if response.text:
            log.info('\n ========== response : %s\n', response.text)
            dic = json.loads(response.text)
        else:
            dic = {}

        if 'result' in dic.keys():
            for item in dic['result']:
                if item['doc-type']=='05':
                    bill = self.env['account.invoice'].search([('number','=',item['clave'].split('-')[1]),('type','=','in_invoice')])
                else:
                    bill = self.env['account.invoice'].search([('fe_clave','=',item['clave'])])

                if bill:
                    params = {}
                    params['fe_server_state'] = item['ind-estado']
                    params['fe_name_xml_sign'] = item['clave']+'-firmado.xml'
                    params['fe_xml_sign'] = item['xml-sign']
                    params['fe_name_xml_hacienda'] = item['clave']+'-hacienda.xml'
                    params['fe_xml_hacienda'] = item['xml-hacienda']
                    bill.update(params)
        '''

    def write_chatter(self,body):
        log.info('--> write_chatter')
        chatter = self.env['mail.message']
        chatter.create({
                        'res_id': self.id,
                        'model':'account.invoice',
                        'body': body,
                       })


    def _cr_xml_factura_electronica(self):
        log.info('--> factelec-Invoice-_cr_xml_factura_electronica')
        for s in self:
            s.invoice = {}
            s.invoice[s.fe_doc_type] = {'CodigoActividad':s.fe_activity_code_id.code}
            s.invoice[s.fe_doc_type].update({'Clave':s.fe_clave})
            s.invoice[s.fe_doc_type].update({'NumeroConsecutivo':s.number})
            s.invoice[s.fe_doc_type].update({'FechaEmision':s.fe_fecha_emision.split(' ')[0]+'T'+s.fe_fecha_emision.split(' ')[1]+'-06:00'})
            s.invoice[s.fe_doc_type].update({'Emisor':{
                'Nombre':s.company_id.company_registry
            }})
            s.invoice[s.fe_doc_type]['Emisor'].update({
            'Identificacion':{
                'Tipo': s.env.user.company_id.fe_identification_type or None,
                'Numero':s.env.user.company_id.vat.replace('-','').replace(' ','') or None,
            },
            })

            if s.env.user.company_id.fe_comercial_name:
                s.invoice[s.fe_doc_type]['Emisor'].update({'NombreComercial':s.env.user.company_id.fe_comercial_name})

            s.invoice[s.fe_doc_type]['Emisor'].update({'Ubicacion':{
            'Provincia':s.env.user.company_id.state_id.fe_code,
            'Canton':s.env.user.company_id.fe_canton_id.code,
            'Distrito':s.env.user.company_id.fe_district_id.code,
            }})

            if s.company_id.fe_neighborhood_id.code:
                s.invoice[s.fe_doc_type]['Emisor']['Ubicacion'].update({'Barrio':s.env.user.company_id.fe_neighborhood_id.code})

            s.invoice[s.fe_doc_type]['Emisor']['Ubicacion'].update({'OtrasSenas':s.env.user.company_id.fe_other_signs})

            if s.company_id.phone:
                s.invoice[s.fe_doc_type]['Emisor'].update({'Telefono':{
                    'CodigoPais':str(s.company_id.country_id.phone_code),
                    'NumTelefono':s.company_id.phone.replace('-','').replace(' ',''),
                }})
            if s.env.user.company_id.fe_fax_number:
                s.invoice[s.fe_doc_type]['Emisor'].update({'Fax':{
                    'CodigoPais':str(s.company_id.country_id.phone_code),
                    'NumTelefono':s.company_id.fe_fax_number,
                }})

            s.invoice[s.fe_doc_type]['Emisor'].update({'CorreoElectronico':s.company_id.email})

            s.invoice[s.fe_doc_type].update({'Receptor':{
            'Nombre':s.partner_id.name,
            }})

            if s.partner_id.vat:
                s.invoice[s.fe_doc_type]['Receptor'].update({'Identificacion':{
                    'Tipo':s.partner_id.fe_identification_type,
                    'Numero':s.partner_id.vat.replace('-','').replace(' ','') or None,
                }})

            if s.partner_id.fe_receptor_identificacion_extranjero:
                s.invoice[s.fe_doc_type]['Receptor'].update({'IdentificacionExtranjero':s.partner_id.fe_receptor_identificacion_extranjero})

            if s.partner_id.fe_comercial_name:
                s.invoice[s.fe_doc_type]['Receptor'].update({'NombreComercial':s.partner_id.fe_comercial_name})

            if s.partner_id.state_id.fe_code:
                s.invoice[s.fe_doc_type]['Receptor'].update({'Ubicacion':{
                    'Provincia':s.partner_id.state_id.fe_code,
                    'Canton':s.partner_id.fe_canton_id.code,
                    'Distrito':s.partner_id.fe_district_id.code,
                    'OtrasSenas':s.partner_id.fe_other_signs,
                }})

            if s.partner_id.fe_neighborhood_id.code:
                s.invoice[s.fe_doc_type]['Receptor']['Ubicacion'].update({'Barrio':s.partner_id.fe_neighborhood_id.code})

            if s.partner_id.fe_receptor_otras_senas_extranjero:
                s.invoice[s.fe_doc_type]['Receptor'].update({'OtrasSenasExtranjero':s.partner_id.fe_receptor_otras_senas_extranjero})

            if s.partner_id.phone:
                s.invoice[s.fe_doc_type]['Receptor'].update({'Telefono':{
                    'CodigoPais':str(s.company_id.country_id.phone_code),
                    'NumTelefono':s.partner_id.phone.replace('-','').replace(' ','') or None,
                }})

            if s.partner_id.fe_fax_number:
                s.invoice[s.fe_doc_type]['Receptor'].update({'Fax':{
                    'CodigoPais':str(s.company_id.country_id.phone_code),
                    'NumTelefono':s.partner_id.fe_fax_number,
                }})

            if s.partner_id.email:
                s.invoice[s.fe_doc_type]['Receptor'].update({'CorreoElectronico':s.partner_id.email})

            s.invoice[s.fe_doc_type].update({'CondicionVenta':s.payment_term_id.fe_condition_sale})

            if s.payment_term_id.name:
                s.invoice[s.fe_doc_type].update({'PlazoCredito':s.payment_term_id.name})
            if s.fe_condicion_impuesto:
                s.invoice[s.fe_doc_type].update({'CondicionImpuesto':s.fe_condicion_impuesto})
            
            s.invoice[s.fe_doc_type].update({'MedioPago':s.fe_payment_type})
            
            if s.fe_msg_type:
                s.invoice[s.fe_doc_type].update({'Mensaje':s.fe_msg_type})
                if s.fe_detail_msg:
                    s.invoice[s.fe_doc_type].update({'DetalleMensaje':s.fe_detail_msg})

            inv_lines = []
            OtrosCargos_array = []
            NumeroLinea = 1
            arrayCount = 0
            totalSale = 0
            TotalDescuentos = 0
            TotalServGravados = 0
            TotalServExentos = 0
            TotalServExonerado = 0
            TotalMercanciasGravadas = 0
            TotalMercanciasExentas = 0
            TotalMercExonerada = 0
            TotalImpuesto = 0
            TotalOtrosCargos = 0
            OtrosCargos_array = []

            for i in s.invoice_line_ids:
                LineaCantidad = 0
                LineaImpuestoTarifa = 0
                LineaMontoDescuento = 0
                MontoTotalLinea = 0
                LineaImpuestoNeto = 0

                inv_lines.append({'NumeroLinea':NumeroLinea})

                #PartidaArancelaria   #PENDIENTE, Cuando el comprobante es del tipo Exportacion

                if i.product_id.default_code:
                    inv_lines[arrayCount]['Codigo'] = i.product_id.default_code

                if i.product_id.fe_codigo_comercial_codigo:
                    inv_lines[arrayCount]['CodigoComercial'] = {
                        'Tipo':i.product_id.fe_codigo_comercial_tipo,
                        'Codigo':i.product_id.fe_codigo_comercial_codigo,
                    }

                LineaCantidad = round(i.quantity,3)
                inv_lines[arrayCount]['Cantidad'] = '{0:.3f}'.format(LineaCantidad)

                inv_lines[arrayCount]['UnidadMedida'] = i.uom_id.name

                if i.product_id.fe_unidad_medida_comercial:
                    inv_lines[arrayCount]['UnidadMedidaComercial'] = i.product_id.fe_unidad_medida_comercial

                if i.name:
                    inv_lines[arrayCount]['Detalle'] = i.name or None

                LineaPrecioUnitario = round(i.price_unit,5)
                inv_lines[arrayCount]['PrecioUnitario'] = '{0:.5f}'.format(LineaPrecioUnitario)

                LineaMontoTotal = round((LineaCantidad * LineaPrecioUnitario),5)
                inv_lines[arrayCount]['MontoTotal'] = '{0:.5f}'.format(LineaMontoTotal)

                if i.discount:
                    LineaMontoDescuento = round((LineaMontoTotal * (i.discount/100)),5)
                    LineaNaturalezaDescuento = "Se aplica %s porciento de descuento" % (i.discount,)

                    inv_lines[arrayCount]['Descuento'] ={
                    'MontoDescuento':'{0:.5f}'.format(LineaMontoDescuento),
                    'NaturalezaDescuento':LineaNaturalezaDescuento[:80]
                    }
                    TotalDescuentos = round((TotalDescuentos + LineaMontoDescuento),5)

                LineaSubTotal = round((LineaMontoTotal - LineaMontoDescuento),5)
                inv_lines[arrayCount]['SubTotal'] = '{0:.5f}'.format(LineaSubTotal)

                if i.invoice_line_tax_ids:

                    ## COMIENZA TAXES y OTROS CARGOS

                    for tax_id in i.invoice_line_tax_ids :
                        MontoCargo = 0
                        LineaImpuestoMonto = 0

                        if tax_id.type == 'OTHER': #

                            OtrosCargos_json = { 'TipoDocumento':tax_id.tipo_documento }

                            OtrosCargos_json.update({'Detalle':tax_id.name})

                            OtrosCargos_json.update({'Porcentaje':'{0:.5f}'.format(tax_id.amount)})

                            MontoCargo = LineaMontoTotal * (tax_id.amount/100)

                            OtrosCargos_json.update({'MontoCargo':'{0:.5f}'.format(MontoCargo)})

                            OtrosCargos_array.append(OtrosCargos_json)

                            TotalOtrosCargos += MontoCargo

                        else:

                            LineaImpuestoTarifa = round(tax_id.amount,2)

                            inv_lines[arrayCount]['Impuesto'] = {
                                'Codigo':tax_id.tarifa_impuesto,
                                'CodigoTarifa':tax_id.codigo_impuesto,
                                'Tarifa':'{0:.2f}'.format(LineaImpuestoTarifa)
                                }

                            LineaImpuestoMonto = round((LineaSubTotal * LineaImpuestoTarifa/100),5)
                            inv_lines[arrayCount]['Impuesto'].update(dict({'Monto':'{0:.5f}'.format(LineaImpuestoMonto)}))

                            LineaImpuestoNeto = round(LineaImpuestoMonto,5) # - LineaImpuestoExoneracion
                            inv_lines[arrayCount]['ImpuestoNeto'] = '{0:.5f}'.format(round(LineaImpuestoNeto,5))
                        #Si esta exonerado al 100% se debe colocar 0-Zero

                    #XXXXXX FALTA TOTAL IVA DEVUELTO

                            TotalImpuesto = round((TotalImpuesto + LineaImpuestoNeto),5)

                MontoTotalLinea = round((LineaSubTotal + LineaImpuestoNeto),5)
                inv_lines[arrayCount]['MontoTotalLinea'] = '{0:.5f}'.format(MontoTotalLinea)

                if i.product_id.type == 'service':
                    #asking for tax for know if the product is Tax Free
                    if i.invoice_line_tax_ids:
                        TotalServGravados = TotalServGravados + LineaMontoTotal
                    else:
                        TotalServExentos = TotalServExentos + LineaMontoTotal
                    #  XXXX PENDIENTE LOS ServExonerados
                else:
                    if i.invoice_line_tax_ids:
                        TotalMercanciasGravadas = TotalMercanciasGravadas + LineaMontoTotal #LineaSubTotal
                    else:
                        TotalMercanciasExentas = TotalMercanciasExentas + LineaMontoTotal #LineaSubTotal
                    #   XXXX PENDIENTE LOS MercanciasExoneradas


                NumeroLinea = NumeroLinea + 1
                arrayCount = arrayCount + 1

            s.invoice[s.fe_doc_type]['DetalleServicio'] = {'LineaDetalle':inv_lines}



            s.invoice[s.fe_doc_type].update({
            'OtrosCargos':OtrosCargos_array
            })

            s.invoice[s.fe_doc_type].update(
                {'ResumenFactura':{
                    'CodigoTipoMoneda':{
                        'CodigoMoneda':s.currency_id.name,
                        'TipoCambio':'{0:.2f}'.format((1/s.currency_id.rate) or None),
                    }
                }})

            TotalGravado = TotalServGravados + TotalMercanciasGravadas
            TotalExento = TotalServExentos + TotalMercanciasExentas
            TotalExonerado = TotalServExonerado + TotalMercExonerada
            TotalVenta = TotalGravado + TotalExento #+ TotalExonerado   #REVISAR EL EXONERADO SI SE SUMA O RESTA
            TotalVentaNeta = TotalVenta - TotalDescuentos

            if TotalServGravados:
                s.invoice[s.fe_doc_type]['ResumenFactura'].update({'TotalServGravados':'{0:.5f}'.format(TotalServGravados)})

            if TotalServExentos:
                s.invoice[s.fe_doc_type]['ResumenFactura'].update({'TotalServExentos':'{0:.5f}'.format(TotalServExentos)})

            if TotalServExonerado:
                s.invoice[s.fe_doc_type]['ResumenFactura'].update({'TotalServExonerado':'{0:.5f}'.format(TotalServExonerado)})

            if TotalMercanciasGravadas:
                s.invoice[s.fe_doc_type]['ResumenFactura'].update({'TotalMercanciasGravadas':'{0:.5f}'.format(TotalMercanciasGravadas)})

            if TotalMercanciasExentas:
                s.invoice[s.fe_doc_type]['ResumenFactura'].update({'TotalMercanciasExentas':'{0:.5f}'.format(TotalMercanciasExentas)})

            if TotalMercExonerada:
                s.invoice[s.fe_doc_type]['ResumenFactura'].update({'TotalMercExonerada':'{0:.5f}'.format(TotalMercExonerada)})

            if TotalGravado:
                s.invoice[s.fe_doc_type]['ResumenFactura'].update({'TotalGravado':'{0:.5f}'.format(TotalServGravados + TotalMercanciasGravadas)})

            if TotalExento:
                s.invoice[s.fe_doc_type]['ResumenFactura'].update({'TotalExento':'{0:.5f}'.format(TotalServExentos + TotalMercanciasExentas)})

            if TotalExonerado:
                s.invoice[s.fe_doc_type]['ResumenFactura'].update({'TotalExonerado':'{0:.5f}'.format(TotalServExonerado + TotalMercExonerada)})

            if TotalVenta:
                s.invoice[s.fe_doc_type]['ResumenFactura'].update({'TotalVenta':'{0:.5f}'.format(TotalVenta)})
            else:
                s.invoice[s.fe_doc_type]['ResumenFactura'].update({'TotalVenta':'0'})

            if TotalDescuentos:
                s.invoice[s.fe_doc_type]['ResumenFactura'].update({'TotalDescuentos':'{0:.5f}'.format(TotalDescuentos)})

            if TotalVentaNeta:
                s.invoice[s.fe_doc_type]['ResumenFactura'].update({'TotalVentaNeta':'{0:.5f}'.format(TotalVentaNeta)})
            else:
                s.invoice[s.fe_doc_type]['ResumenFactura'].update({'TotalVentaNeta':'0'})

            if TotalImpuesto:
                s.invoice[s.fe_doc_type]['ResumenFactura']['TotalImpuesto'] = '{0:.5f}'.format(TotalImpuesto)
            else:
                s.invoice[s.fe_doc_type]['ResumenFactura']['TotalImpuesto'] = '0'



            ##PENDINETE TOTALIVADEVUELTO
            #self.invoice[self.fe_doc_type]['ResumenFactura']['TotalIVADevuelto'] = 'PENDIENTE_TOTAL_IVA_DEVUELTO'     # CONDICIONAL
                #Este campo será de condición obligatoria cuando se facturen servicios de salud y cuyo método de pago sea “Tarjeta”.
                #Se obtiene de la sumatoria del Monto de los Impuestos pagado por los servicios de salud en tarjetas.
                #Es un número decimal compuesto por 13 enteros y 5 decimales.

            if TotalOtrosCargos:
                s.invoice[s.fe_doc_type]['ResumenFactura']['TotalOtrosCargos'] = '{0:.5f}'.format(TotalOtrosCargos)

            TotalComprobante = TotalVentaNeta + TotalImpuesto #+ TotalOtrosCargos - TotalIVADevuelto
            if TotalComprobante:
                s.invoice[s.fe_doc_type]['ResumenFactura']['TotalComprobante'] = '{0:.5f}'.format(TotalComprobante) #'PENDIENTE_TOTAL_Comprobante'
            #SUMA DE: "total venta neta" + "monto total del impuesto" + "total otros cargos" - total IVA devuelto
            else:
                s.invoice[s.fe_doc_type]['ResumenFactura']['TotalComprobante'] ='0'

            if s.number[8:10] == "02" or s.number[8:10] == "03":
                if not s.origin:
                    error = True
                    msg = 'Indique el NUMERO CONSECUTIVO de REFERENCIA\n'
                else:
                    if len(s.origin) == 20:
                        origin_doc = s.search([('number', '=', s.origin)])
                        origin_doc_fe_fecha_emision = origin_doc.fe_fecha_emision.split(' ')[0] + 'T' + origin_doc.fe_fecha_emision.split(' ')[1]+'-06:00'
                        s.invoice[s.fe_doc_type].update({
                            'InformacionReferencia':{
                            'TipoDoc':s.fe_tipo_documento_referencia,
                            'Numero':origin_doc.number,
                            'FechaEmision': origin_doc_fe_fecha_emision,
                            'Codigo':s.fe_informacion_referencia_codigo or None,
                            'Razon':s.name,
                            }
                        })

            if s.comment:
            s.invoice[s.fe_doc_type].update({
                'Otros':{
                    'OtroTexto':s.comment,
                    #'OtroContenido':'ELEMENTO OPCIONAL'
                }
            })
            #PDF de FE,FEE,FEC,ND,NC
            #En caso de que el server-side envie el mail

            s.invoice[s.fe_doc_type].update({'PDF':s._get_pdf_bill(s.id)})

    @api.model
    def cron_send_json(self):
        log.info('--> factelec-Invoice-build_json')
        invoice_list = self.env['account.invoice'].search([('fe_server_state','=',False),('state','=','open')])
        for invoice in invoice_list:
            if invoice.company_id.country_id.code == 'CR' and invoice.fe_in_invoice_type != 'OTRO':
                log.info('-->consecutivo %s',invoice.number)
                invoice.confirm_bill()
                
                
    #metodo original heredado            
    @api.model
    def _prepare_refund(self, invoice, date_invoice=None, date=None, description=None, journal_id=None,fe_payment_type=None,payment_term_id=None,fe_activity_code_id=None,fe_receipt_status=None,fe_tipo_documento_referencia=None,fe_informacion_referencia_codigo=None):
            """ Prepare the dict of values to create the new credit note from the invoice.
                This method may be overridden to implement custom
                credit note generation (making sure to call super() to establish
                a clean extension chain).
    
                :param record invoice: invoice as credit note
                :param string date_invoice: credit note creation date from the wizard
                :param integer date: force date from the wizard
                :param string description: description of the credit note from the wizard
                :param integer journal_id: account.journal from the wizard
                :return: dict of value to create() the credit note
            """
            values = {}
            for field in self._get_refund_copy_fields():
                if invoice._fields[field].type == 'many2one':
                    values[field] = invoice[field].id
                else:
                    values[field] = invoice[field] or False
    
            values['invoice_line_ids'] = self._refund_cleanup_lines(invoice.invoice_line_ids)
    
            tax_lines = invoice.tax_line_ids
            values['tax_line_ids'] = self._refund_cleanup_lines(tax_lines)
    
            if journal_id:
                journal = self.env['account.journal'].browse(journal_id)
            elif invoice['type'] == 'in_invoice':
                journal = self.env['account.journal'].search([('type', '=', 'purchase')], limit=1)
            else:
                journal = self.env['account.journal'].search([('type', '=', 'sale')], limit=1)
            values['journal_id'] = journal.id
    
            values['type'] = TYPE2REFUND[invoice['type']]
            values['date_invoice'] = date_invoice or fields.Date.context_today(invoice)
            values['state'] = 'draft'
            values['number'] = False
            values['origin'] = invoice.number
            values['payment_term_id'] = False
            values['refund_invoice_id'] = invoice.id
            values['fe_payment_type'] = fe_payment_type
            values['payment_term_id'] = payment_term_id
            values['fe_activity_code_id'] = fe_activity_code_id
            values['fe_receipt_status'] = fe_receipt_status
            values['fe_tipo_documento_referencia'] = fe_tipo_documento_referencia
            values['fe_informacion_referencia_codigo'] = fe_informacion_referencia_codigo
            if date:
                values['date'] = date
            if description:
                values['name'] = description
            return values
            
    #metodo original heredado          

    @api.returns('self')
    def refund(self, date_invoice=None, date=None, description=None, journal_id=None,fe_payment_type=None,payment_term_id=None,fe_activity_code_id=None,fe_receipt_status=None,fe_tipo_documento_referencia=None,fe_informacion_referencia_codigo=None):
            new_invoices = self.browse()
            for invoice in self:
                # create the new invoice
                values = self._prepare_refund(invoice, date_invoice=date_invoice, date=date,
                                        description=description, journal_id=journal_id,fe_payment_type=fe_payment_type,payment_term_id=payment_term_id,fe_activity_code_id=fe_activity_code_id,fe_receipt_status=fe_receipt_status,fe_tipo_documento_referencia=fe_tipo_documento_referencia,fe_informacion_referencia_codigo=fe_informacion_referencia_codigo)
                refund_invoice = self.create(values)
                invoice_type = {'out_invoice': ('customer invoices credit note'),
                    'in_invoice': ('vendor bill credit note')}
                message = _("This %s has been created from: <a href=# data-oe-model=account.invoice data-oe-id=%d>%s</a>") % (invoice_type[invoice.type], invoice.id, invoice.number)
                refund_invoice.message_post(body=message)
                new_invoices += refund_invoice
            return new_invoices
