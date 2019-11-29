from odoo import models, fields, api, exceptions
from odoo.exceptions import ValidationError
from datetime import datetime,timezone
from lxml.etree import Element, fromstring, parse, tostring, XMLParser
from openerp.osv.orm import except_orm
from openerp.osv import osv
from openerp.tools.translate import _
import lxml.etree as ET
import pytz
import json
import re
import requests
import base64
import xmltodict
import logging

log = logging.getLogger(__name__)

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

    current_country_code = fields.Char(string="country code", compute='_get_current_company')

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


    fe_in_invoice_type = fields.Selection(#1569867120
        string="Tipo Documento",
        selection=[
                ('FE', 'Factura Electronica'),
                ('ME', 'Mensaje Aceptación'),
        ],
        default="FE",
    )

    @api.onchange("fe_in_invoice_type",)
    def _onchange_fe_in_invoice_type(self):
        #1569867217
        if self.fe_in_invoice_type == "FE":
            return {'domain': {'journal_id': [('sequence_id.prefix', 'ilike', '08')]},
                         'value': {
                                     'journal_id': None,
                                  }
                   }
        else:
            return {'domain': {'journal_id': [('sequence_id.prefix', 'ilike', '05')]},
                         'value': {
                                     'journal_id': None,
                                  }
                   }



    @api.multi
    def _compute_total_descuento(self):
        log.info('--> factelec/_compute_total_descuento')
        for s in self:
            totalDiscount = 0
            for i in s.invoice_line_ids:
                if i.discount:
                    discount = i.price_unit * (i.discount/100)
                    totalDiscount = totalDiscount + discount
        self.fe_total_descuento = totalDiscount

    @api.multi
    def _compute_total_venta(self):
        log.info('--> factelec/_compute_total_venta')
        for s in self:
            totalSale = 0
            for i in s.invoice_line_ids:
                totalAmount = i.price_unit * i.quantity
                totalSale = totalSale + totalAmount

        self.fe_total_venta = totalSale


    @api.multi
    @api.depends("fe_total_servicio_exentos", "fe_total_mercancias_exentas" )
    def _compute_total_exento(self):
        log.info('--> factelec/_compute_total_exento')
        for s in self:
            s.fe_total_exento = s.fe_total_servicio_exentos + s.fe_total_mercancias_exentas

    @api.multi
    @api.depends("fe_total_servicio_gravados", "fe_total_mercancias_gravadas" )
    def _compute_total_gravado(self):
        log.info('--> factelec/_compute_total_gravado')
        for s in self:
            s.fe_total_gravado = s.fe_total_servicio_gravados + s.fe_total_mercancias_gravadas

    @api.multi
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

    @api.multi
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

    @api.multi
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

    @api.multi
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


    @api.multi
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

    @api.multi
    def _cr_validate_mensaje_receptor(self):
        log.info('--> factelec-Invoice-_cr_validate_mensaje_receptor')
        #if self.state != 'open':  #Se cambio de 'open' a draft or cancel
        if (self.state != 'open' and self.state != 'paid'):
           msg = 'La factura debe de estar en Open o Paid para poder confirmarse'
           raise exceptions.Warning((msg))
        if self.fe_msg_type == False:
            msg = 'Falta seleccionar el mensaje: Acepta, Acepta Parcial o Rechaza el documento'
            raise exceptions.Warning((msg))
        else:
            if self.fe_detail_msg == False and  self.fe_msg_type != '1':
                msg = 'Falta el detalle mensaje'
                raise exceptions.Warning((msg))


        log.info('===> XXXX VALIDACION QUE HAY ADJUNTO UN XML DEL EMISOR/PROVEEDOR')
        log.info('===> XXXX VALIDACION QUE EL XML ES DEL TIPO FacturaElectronica')

    @api.multi
    def _cr_xml_mensaje_receptor(self):
        log.info('--> factelec-Invoice-_cr_xml_mensaje_receptor')

        bill_dic = self.convert_xml_to_dic(self.fe_xml_supplier)

        if 'FacturaElectronica' in bill_dic.keys():

            self.invoice = {self.fe_doc_type:{
                'Clave':bill_dic['FacturaElectronica']['Clave'],
                'NumeroCedulaEmisor':bill_dic['FacturaElectronica']['Emisor']['Identificacion']['Numero'],
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
                'NumeroConsecutivoReceptor':self.number,
                #'EmisorEmail':self.partner_id.email,
                #'pdf':self._get_pdf_bill(self.id) or None,
                }}
        else:
            msg = 'adjunte una factura electronica antes de confirmar la aceptacion'
            raise exceptions.Warning((msg))

    def _cr_post_server_side(self):
        log.info('--> factelec-Invoice-_cr_post_server_side')
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
        response = requests.post(url, headers = header, data = json_to_send)
        try:
           log.info('===340==== Response : \n  %s',response.text )
           '''Response : {"id": null, "jsonrpc": "2.0", "result": {"status": "200"}}'''
           json_response = json.loads(response.text)

           if "result" in json_response.keys():
               result = json_response['result']
           if "status" in result.keys():
               if result['status'] == "200":
                   log.info('====== Exito \n')
                   self.update({'fe_server_state':'enviado a procesar'})

               elif "error" in  result.keys():
                  result = json_response['result']['error']
                  body = "Error1 "+result
                  self.write_chatter(body)

        except Exception as e:
            body = "Error2 "+str(e)
            self.write_chatter(body)

    @api.multi
    def confirm_bill(self):
        log.info('--> factelec-Invoice-confirm_bill')

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

        if(type == 'FE'):
            transform = ET.XSLT(ET.parse('/home/odoo/addons/factelec_43/static/src/fe.xslt'))
        nuevodom = transform(dom)
        return ET.tostring(nuevodom, pretty_print=True)

    @api.multi
    @api.depends()
    def _get_current_company(self):
        log.info('--> factelec-Invoice-_get_current_company')
        for s in self:
            #current_country_code = s.company_id.partner_id.country_id.code
            current_country_code = s.company_id.country_id.code


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

        if error:
            raise exceptions.Warning((msg))

    def _validate_invoice_line(self):
        log.info('--> _validate_invoice_line')
        for line in self.invoice_line_ids:

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
            mensaje_validacion += validation[key]['Mensaje']+" debe ser como minimo "+str(validation[key]['Tamano']['Min'])+" y como máximo "+str(validation[key]['Tamano']['Max'])
        if validation[key]['Tipo'] == 'Integer':
            if not self._try_parse_int(obj):
                self.mensaje_validacion += validation[key]['Mensaje'] +" debe ser un numero entero"+'\n'
        if validation[key]['Patron'] != '':
            if not re.search(obj,validation[key]['Patron']):
                self.mensaje_validacion += validation[key]['Mensaje']+" no cumple con el formato correcto "+validation[key]['Patron']+'\n'

    def validacion(self):
        tipo = self.number[8:10]

        emisor_str = "Emisor"
        receptor_str = "Receptor"
        if tipo =='01' or tipo =='02' or tipo =='03' or tipo =='09':

            emisor = "company_id"
            receptor = "partner_id"

        elif tipo  == '05' or tipo  =='08':

            emisor = "partner_id"
            receptor = "company_id"

        translate = {}
        translate['CodigoActividad'] = 'fe_activity_code_id.code'
        translate['Clave'] = 'fe_clave'
        translate['NumeroConsecutivo'] = 'number'
        translate['FechaEmision'] = 'fe_fecha_emision'
        translate['Emisor-Nombre'] = emisor+'.name'
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


        validation = {}
        validation['CodigoActividad'] = {}
        validation['CodigoActividad']['CondicionCampo'] = {'01':'1','09':'1','08':'1','04':'1','03':'1','02':'1'}
        validation['CodigoActividad']['Tipo'] = 'String'
        validation['CodigoActividad']['Tamano'] = {'Min':6,'Max':6}
        validation['CodigoActividad']['Patron'] = ''
        validation['CodigoActividad']['Mensaje'] = 'El codigo actividad'

        validation['Clave'] = {}
        validation['Clave']['CondicionCampo'] =  {'01':'1','09':'1','08':'1','04':'1','03':'1','02':'1'}
        validation['Clave']['Tipo'] = 'String'
        validation['Clave']['Tamano']  = {'Min':50,'Max':50}
        validation['Clave']['Patron'] = ''
        validation['Clave']['Mensaje'] = 'La clave'

        validation['NumeroConsecutivo'] = {}
        validation['NumeroConsecutivo']['CondicionCampo'] =  {'01':'1','09':'1','08':'1','04':'1','03':'1','02':'1'}
        validation['NumeroConsecutivo']['Tipo'] = 'String'
        validation['NumeroConsecutivo']['Tamano'] = {'Min':20,'Max':20}
        validation['NumeroConsecutivo']['Patron'] = ''
        validation['NumeroConsecutivo']['Mensaje'] = 'El numero consecutivo'

        validation['FechaEmision'] = {}
        validation['FechaEmision']['CondicionCampo'] = {'01':'1','09':'1','08':'1','04':'1','03':'1','02':'1'}
        validation['FechaEmision']['Tipo'] = 'DateTime'
        validation['FechaEmision']['Tamano'] = {'Min':1,'Max':100}
        validation['FechaEmision']['Patron'] = ''
        validation['FechaEmision']['Mensaje'] = 'La fecha emisión'

        validation['Emisor-Nombre'] = {}
        validation['Emisor-Nombre']['CondicionCampo'] = {'01':'1','09':'1','08':'1','04':'01','03':'1','02':'1'}
        validation['Emisor-Nombre']['Tipo'] = 'String'
        validation['Emisor-Nombre']['Tamano'] = {'Min':1,'Max':100}
        validation['Emisor-Nombre']['Patron'] = ''
        validation['Emisor-Nombre']['Mensaje'] = 'El nombre del ' + emisor_str

        validation['Emisor-Identifacion-Tipo'] = {}
        validation['Emisor-Identifacion-Tipo']['CondicionCampo'] = {'01':'1','09':'1','08':'1','04':'1','03':'1','02':'1'}
        validation['Emisor-Identifacion-Tipo']['Tipo'] = 'String'
        validation['Emisor-Identifacion-Tipo']['Tamano'] = {'Min':2,'Max':2}
        validation['Emisor-Identifacion-Tipo']['Patron'] = ''
        validation['Emisor-Identifacion-Tipo']['Mensaje'] = 'El tipo de identificación del '+emisor_str

        validation['Emisor-Identifacion-Numero'] = {}
        validation['Emisor-Identifacion-Numero']['CondicionCampo'] = {'01':'1','09':'1','08':'1','04':'1','03':'1','02':'1'}
        validation['Emisor-Identifacion-Numero']['Tipo'] = 'String'
        validation['Emisor-Identifacion-Numero']['Tamano'] = {'Min':9,'Max':12}
        validation['Emisor-Identifacion-Numero']['Patron'] = ''
        validation['Emisor-Identifacion-Numero']['Mensaje'] = 'El numero de identificación del '+emisor_str

        validation['Emisor-Ubicacion-Provincia'] = {}
        validation['Emisor-Ubicacion-Provincia']['CondicionCampo'] = {'01':'1','09':'1','08':'1','04':'1','03':'1','02':'1'}
        validation['Emisor-Ubicacion-Provincia']['Tamano'] = {'Min':1,'Max':1}
        validation['Emisor-Ubicacion-Provincia']['Tipo'] = 'String'
        validation['Emisor-Ubicacion-Provincia']['Patron'] = ''
        validation['Emisor-Ubicacion-Provincia']['Mensaje'] = 'La provincia del '+emisor_str

        validation['Emisor-Ubicacion-Canton'] = {}
        validation['Emisor-Ubicacion-Canton']['CondicionCampo'] = {'01':'1','09':'1','08':'1','04':'1','03':'1','02':'1'}
        validation['Emisor-Ubicacion-Canton']['Tipo'] = 'String'
        validation['Emisor-Ubicacion-Canton']['Tamano'] = {'Min':2,'Max':2}
        validation['Emisor-Ubicacion-Canton']['Patron'] = ''
        validation['Emisor-Ubicacion-Canton']['Mensaje'] = 'El canton del '+emisor_str

        validation['Emisor-Ubicacion-Distrito'] = {}
        validation['Emisor-Ubicacion-Distrito']['CondicionCampo'] = {'01':'1','09':'1','08':'1','04':'1','03':'1','02':'1'}
        validation['Emisor-Ubicacion-Distrito']['Tipo'] = 'String'
        validation['Emisor-Ubicacion-Distrito']['Tamano'] = {'Min':2,'Max':2}
        validation['Emisor-Ubicacion-Distrito']['Patron'] = ''
        validation['Emisor-Ubicacion-Distrito']['Mensaje'] = 'El distrito del '+emisor_str

        validation['Emisor-Ubicacion-Barrio'] = {}
        validation['Emisor-Ubicacion-Barrio']['CondicionCampo'] = {'01':'2','09':'2','08':'2','04':'2','03':'2','02':'2'}
        validation['Emisor-Ubicacion-Barrio']['Tipo'] = 'String'
        validation['Emisor-Ubicacion-Barrio']['Tamano'] = {'Min':2,'Max':2}
        validation['Emisor-Ubicacion-Barrio']['Patron'] = ''
        validation['Emisor-Ubicacion-Barrio']['Mensaje'] = 'El barrio del '+emisor_str

        validation['Emisor-Ubicacion-OtrasSenas'] = {}
        validation['Emisor-Ubicacion-OtrasSenas']['CondicionCampo'] = {'01':'1','09':'1','08':'1','04':'1','03':'1','02':'1'}
        validation['Emisor-Ubicacion-OtrasSenas']['Tipo'] = 'String'
        validation['Emisor-Ubicacion-OtrasSenas']['Tamano'] = {'Min':1,'Max':250}
        validation['Emisor-Ubicacion-OtrasSenas']['Patron'] = ''
        validation['Emisor-Ubicacion-OtrasSenas']['Mensaje'] = 'Las otras señas del '+emisor_str

        validation['Emisor-Telefono-NumTelefono'] = {}
        validation['Emisor-Telefono-NumTelefono']['CondicionCampo'] = {'01':'2','09':'2','08':'2','04':'2','03':'2','02':'2'}
        validation['Emisor-Telefono-NumTelefono']['Tipo'] = 'Integer'
        validation['Emisor-Telefono-NumTelefono']['Tamano'] = {'Min':8,'Max':20}
        validation['Emisor-Telefono-NumTelefono']['Patron'] = ''
        validation['Emisor-Telefono-NumTelefono']['Mensaje'] = 'El numero de telefono del '+emisor_str

        validation['Emisor-Fax-NumTelefono'] = {}
        validation['Emisor-Fax-NumTelefono']['CondicionCampo'] = {'01':'2','09':'2','08':'2','04':'2','03':'2','02':'2'}
        validation['Emisor-Fax-NumTelefono']['Tipo'] = 'Integer'
        validation['Emisor-Fax-NumTelefono']['Tamano'] = {'Min':8,'Max':20}
        validation['Emisor-Fax-NumTelefono']['Patron'] = ''
        validation['Emisor-Fax-NumTelefono']['Mensaje'] = 'El numero de fax del '+emisor_str

        validation['Emisor-CorreoElectronico'] = {}
        validation['Emisor-CorreoElectronico']['CondicionCampo'] = {'01':'1','09':'1','08':'1','04':'1','03':'1','02':'1'}
        validation['Emisor-CorreoElectronico']['Tipo'] = 'String'
        validation['Emisor-CorreoElectronico']['Tamano'] = {'Min':1,'Max':160}
        validation['Emisor-CorreoElectronico']['Patron'] = ''
        validation['Emisor-CorreoElectronico']['Mensaje'] = 'El correo electronico del '+emisor_str

        #Receptor
        #validation['Receptor-Nombre'] = {}
        #validation['Receptor-Nombre']['CondicionCampo'] = {'01':'1','09':'1','08':'1','04':'1','03':'1','02':'1'}
        #validation['Receptor-Nombre']['Tipo'] = 'String'
        #validation['Receptor-Nombre']['Tamano'] = {'Min':1,'Max':100}
        #validation['Receptor-Nombre']['Patron'] = ''

        validation['Receptor-TipoIdentifacion'] = {}
        validation['Receptor-TipoIdentifacion']['CondicionCampo'] = {'01':'1','09':'1','08':'1','04':'1','03':'1','02':'1'}
        validation['Receptor-TipoIdentifacion']['Tipo'] = 'String'
        validation['Receptor-TipoIdentifacion']['Tamano'] = {'Min':2,'Max':2}
        validation['Receptor-TipoIdentifacion']['Patron'] = ''
        validation['Receptor-TipoIdentifacion']['Mensaje'] = 'El tipo de identificacion del '+receptor_str

        validation['Receptor-NumeroIdentifacion'] = {}
        validation['Receptor-NumeroIdentifacion']['CondicionCampo'] = {'01':'1','09':'1','08':'1','04':'1','03':'1','02':'1'}
        validation['Receptor-NumeroIdentifacion']['Tipo'] = 'String'
        validation['Receptor-NumeroIdentifacion']['Tamano'] = {'Min':9,'Max':12}
        validation['Receptor-NumeroIdentifacion']['Patron'] = ''
        validation['Receptor-NumeroIdentifacion']['Mensaje'] = 'El numero de identificacion del '+receptor_str

        validation['Receptor-Ubicacion-Provincia'] = {}
        validation['Receptor-Ubicacion-Provincia']['CondicionCampo'] = {'01':'1','09':'1','08':'1','04':'1','03':'1','02':'1'}
        validation['Receptor-Ubicacion-Provincia']['Tipo'] = 'String'
        validation['Receptor-Ubicacion-Provincia']['Tamano'] = {'Min':1,'Max':1}
        validation['Receptor-Ubicacion-Provincia']['Patron'] = ''
        validation['Receptor-Ubicacion-Provincia']['Mensaje'] = 'La provincia del '+receptor_str

        validation['Receptor-Ubicacion-Canton'] = {}
        validation['Receptor-Ubicacion-Canton']['CondicionCampo'] = {'01':'1','09':'1','08':'1','04':'1','03':'1','02':'1'}
        validation['Receptor-Ubicacion-Canton']['Tipo'] = 'String'
        validation['Receptor-Ubicacion-Canton']['Tamano'] = {'Min':2,'Max':2}
        validation['Receptor-Ubicacion-Canton']['Patron'] = ''
        validation['Receptor-Ubicacion-Canton']['Mensaje'] = 'El canton del '+receptor_str

        validation['Receptor-Ubicacion-Distrito'] = {}
        validation['Receptor-Ubicacion-Distrito']['CondicionCampo'] = {'01':'1','09':'1','08':'1','04':'1','03':'1','02':'1'}
        validation['Receptor-Ubicacion-Distrito']['Tipo'] = 'String'
        validation['Receptor-Ubicacion-Distrito']['Tamano'] = {'Min':2,'Max':2}
        validation['Receptor-Ubicacion-Distrito']['Patron'] = ''
        validation['Receptor-Ubicacion-Distrito']['Mensaje'] = 'El distrito del '+receptor_str

        validation['Receptor-Ubicacion-Barrio'] = {}
        validation['Receptor-Ubicacion-Barrio']['CondicionCampo'] = {'01':'2','09':'2','08':'2','04':'2','03':'2','02':'2'}
        validation['Receptor-Ubicacion-Barrio']['Tipo'] = 'String'
        validation['Receptor-Ubicacion-Barrio']['Tamano'] = {'Min':2,'Max':2}
        validation['Receptor-Ubicacion-Barrio']['Patron'] = ''
        validation['Receptor-Ubicacion-Barrio']['Mensaje'] = 'El barrio del '+receptor_str

        validation['Receptor-Ubicacion-OtrasSenas'] = {}
        validation['Receptor-Ubicacion-OtrasSenas']['CondicionCampo'] = {'01':'1','09':'1','08':'1','04':'1','03':'1','02':'1'}
        validation['Receptor-Ubicacion-OtrasSenas']['Tipo'] = 'String'
        validation['Receptor-Ubicacion-OtrasSenas']['Tamano'] = {'Min':1,'Max':250}
        validation['Receptor-Ubicacion-OtrasSenas']['Patron'] = ''
        validation['Receptor-Ubicacion-OtrasSenas']['Mensaje'] = 'Las otras señas del '+receptor_str

        validation['Receptor-Telefono-NumTelefono'] = {}
        validation['Receptor-Telefono-NumTelefono']['CondicionCampo'] = {'01':'2','09':'2','08':'2','04':'2','03':'2','02':'2'}
        validation['Receptor-Telefono-NumTelefono']['Tipo'] = 'Integer'
        validation['Receptor-Telefono-NumTelefono']['Tamano'] = {'Min':8,'Max':20}
        validation['Receptor-Telefono-NumTelefono']['Patron'] = ''
        validation['Receptor-Telefono-NumTelefono']['Mensaje'] = 'El numero de telefono del '+receptor_str

        validation['Receptor-Fax-NumTelefono'] = {}
        validation['Receptor-Fax-NumTelefono']['CondicionCampo'] = {'01':'2','09':'2','08':'2','04':'2','03':'2','02':'2'}
        validation['Receptor-Fax-NumTelefono']['Tipo'] = 'Integer'
        validation['Receptor-Fax-NumTelefono']['Tamano'] = {'Min':8,'Max':20}
        validation['Receptor-Fax-NumTelefono']['Patron'] = ''
        validation['Receptor-Fax-NumTelefono']['Mensaje'] = 'El numero de fax del '+receptor_str

        validation['Receptor-CorreoElectronico'] = {}
        validation['Receptor-CorreoElectronico']['CondicionCampo'] = {'01':'1','09':'1','08':'1','04':'1','03':'1','02':'1'}
        validation['Receptor-CorreoElectronico']['Tipo'] = 'String'
        validation['Receptor-CorreoElectronico']['Tamano'] = {'Min':1,'Max':160}
        validation['Receptor-CorreoElectronico']['Patron'] = ''
        validation['Receptor-CorreoElectronico']['Mensaje'] = 'El correo electronico del '+receptor_str


        validation['CondicionVenta'] = {}
        validation['CondicionVenta']['CondicionCampo'] = {'01':'1','09':'1','08':'1','04':'1','03':'1','02':'1'}
        validation['CondicionVenta']['Tipo'] = 'String'
        validation['CondicionVenta']['Tamano'] = {'Min':2,'Max':2}
        validation['CondicionVenta']['Patron'] = ''
        validation['CondicionVenta']['Mensaje'] = 'La condición de venta'

        '''plazo credito'''
        validation['MedioPago'] = {}
        validation['MedioPago']['CondicionCampo'] = {'01':'1','09':'1','08':'1','04':'1','03':'2','02':'2'}
        validation['MedioPago']['Tipo'] = 'String'
        validation['MedioPago']['Tamano'] = {'Min':2,'Max':2}
        validation['MedioPago']['Patron'] = ''
        validation['MedioPago']['Mensaje'] = 'El medio de pago'

        for key in validation:
            if validation[key]['CondicionCampo'][tipo] == "1":
                translate_key = translate[key]
                obj = self._getField(translate_key)
                if obj:
                    self._validate_size_type_pattern(obj,validation,key)
                else:
                    self.mensaje_validacion += 'Falta '+validation[key]['Mensaje']+'\n'

            elif validation[key]['CondicionCampo'][tipo] == "2":
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
           vat_complete = "0" * (12 - len(vat)) + vat
           clave = str(country_code) + document_date_invoice.strftime("%d%m%y") \
              + str(vat_complete) + str(self.number) + str(self.fe_receipt_status) \
              + str("87654321")
           self.fe_clave = clave

    @api.multi
    def action_invoice_open(self,validate = True):
        if validate:
            log.info('--> 1570130084')
            for item in self.invoice_line_ids:
                if item.price_subtotal == False:
                    return {
                            'type': 'ir.actions.act_window',
                            'name': '¡Alerta!',
                            'res_model': 'confirm.message',
                            'view_type': 'form',
                            'view_mode': 'form',
                            'views': [(False, 'form')],
                            'target': 'new',
                            'context': {'invoice': self.id}
                        }

        log.info('--> action_invoice_open')

        if self.company_id.country_id.code == 'CR':
            log.info('--> Factura Electronica Costa Rica')
            res = super(Invoice, self).action_invoice_open()
            tz = pytz.timezone('America/Costa_Rica')
            self.fe_fecha_emision = datetime.now(tz=tz).strftime("%Y-%m-%d %H:%M:%S")
            self.date_invoice = self.fe_fecha_emision
            self._validate_company()
            self._generar_clave()
            log.info('--->Clave %s',self.fe_clave)
            self.validacion()
            self._validate_invoice_line()
        else:
            log.info('--> Factura común')
            res = super(Invoice, self).action_invoice_open()


    @api.multi
    def get_invoice(self):
            #peticion al servidor a partir de la clave
            log.info('--> 1569447129')
            log.info('--> get_invoice')

            if self.fe_xml_hacienda:
                 raise ValidationError("Ya se tiene la RESPUESTA de Hacienda")

            if self.number[8:10] == "05":
               url = self.company_id.fe_url_server+'{0}'.format(self.fe_clave+'-'+self.number)
            else:
               url = self.company_id.fe_url_server+'{0}'.format(self.fe_clave)

            header = {'Content-Type':'application/json'}

            r = requests.get(url, headers = header, data=json.dumps({}))

            data = r.json()
            #1569447795
            #alamacena la informacion suministrada por el servidor
            if data:

                if data.get('error'):
                   params = {
                      'fe_server_state':data['error']['message']}
                else:
                   params = {
                      'fe_server_state':data['result']['ind-estado'],
                      'fe_name_xml_sign':data['result']['nombre_xml_firmado'],
                      'fe_xml_sign':data['result']['xml_firmado'],
                      'fe_name_xml_hacienda':data['result']['nombre_xml_hacienda'],
                      'fe_xml_hacienda':data['result']['xml_hacienda'],
                   }
                self.update(params)


    def _get_pdf_bill(self,id):
        log.info('--> _get_pdf_bill')
        ctx = self.env.context.copy()
        ctx.pop('default_type', False)
        pdf = self.env.ref('account.account_invoices_without_payment').with_context(ctx).render(id)
        pdf64 = base64.b64encode(pdf[0]).decode('utf-8')
        return pdf64


    @api.model
    def get_server_bills(self):
        log.info('--> get_server_bills')
        list = self.env['account.invoice'].search(['|',('fe_xml_sign','=',False),('fe_xml_hacienda','=',False),'&',('state','=','open'),
        ('fe_server_state','!=','pendiente enviar')])

        array = []
        dic = {}

        for item in list:
            if item.fe_clave:
               if item.type == 'in_invoice' and item.fe_clave:   #CAMBIO se agrego and item.fe_clave
                  array.append(item.fe_clave+'-'+item.number)
               else:
                  array.append(item.fe_clave)


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


    def write_chatter(self,body):
        log.info('--> write_chatter')
        chatter = self.env['mail.message']
        chatter.create({
                        'res_id': self.id,
                        'model':'account.invoice',
                        'body': body,
                       })

    @api.multi
    def _cr_xml_factura_electronica(self):
        log.info('--> factelec-Invoice-_cr_xml_factura_electronica')

        self.invoice = {}
        self.invoice[self.fe_doc_type] = {'CodigoActividad':self.fe_activity_code_id.code}
        self.invoice[self.fe_doc_type].update({'Clave':self.fe_clave})
        self.invoice[self.fe_doc_type].update({'NumeroConsecutivo':self.number})
        self.invoice[self.fe_doc_type].update({'FechaEmision':self.fe_fecha_emision.split(' ')[0]+'T'+self.fe_fecha_emision.split(' ')[1]+'-06:00'})
        self.invoice[self.fe_doc_type].update({'Emisor':{
             'Nombre':self.company_id.company_registry
        }})
        self.invoice[self.fe_doc_type]['Emisor'].update({
           'Identificacion':{
              'Tipo': self.env.user.company_id.fe_identification_type or None,
              'Numero':self.env.user.company_id.vat,
           },
        })

        if self.env.user.company_id.fe_comercial_name:
           self.invoice[self.fe_doc_type]['Emisor'].update({'NombreComercial':self.env.user.company_id.fe_comercial_name})

        self.invoice[self.fe_doc_type]['Emisor'].update({'Ubicacion':{
           'Provincia':self.env.user.company_id.state_id.fe_code,
           'Canton':self.env.user.company_id.fe_canton_id.code,
           'Distrito':self.env.user.company_id.fe_district_id.code,
        }})

        if self.company_id.fe_neighborhood_id.code:
           self.invoice[self.fe_doc_type]['Emisor']['Ubicacion'].update({'Barrio':self.env.user.company_id.fe_neighborhood_id.code})

        self.invoice[self.fe_doc_type]['Emisor']['Ubicacion'].update({'OtrasSenas':self.env.user.company_id.fe_other_signs})

        if self.company_id.phone:
           self.invoice[self.fe_doc_type]['Emisor'].update({'Telefono':{
              'CodigoPais':str(self.company_id.country_id.phone_code),
              'NumTelefono':self.company_id.phone,
           }})
        if self.env.user.company_id.fe_fax_number:
           self.invoice[self.fe_doc_type]['Emisor'].update({'Fax':{
              'CodigoPais':str(self.company_id.country_id.phone_code),
              'NumTelefono':self.company_id.fe_fax_number,
        }})

        self.invoice[self.fe_doc_type]['Emisor'].update({'CorreoElectronico':self.company_id.email})

        self.invoice[self.fe_doc_type].update({'Receptor':{
           'Nombre':self.partner_id.name,
        }})

        if self.partner_id.vat:
           self.invoice[self.fe_doc_type]['Receptor'].update({'Identificacion':{
              'Tipo':self.partner_id.fe_identification_type,
              'Numero':self.partner_id.vat,
        }})

        if self.partner_id.fe_receptor_identificacion_extranjero:
           self.invoice[self.fe_doc_type]['Receptor'].update({'IdentificacionExtranjero':self.partner_id.fe_receptor_identificacion_extranjero})

        if self.partner_id.fe_comercial_name:
           self.invoice[self.fe_doc_type]['Receptor'].update({'NombreComercial':self.partner_id.fe_comercial_name})

        if self.partner_id.state_id.fe_code:
           self.invoice[self.fe_doc_type]['Receptor'].update({'Ubicacion':{
              'Provincia':self.partner_id.state_id.fe_code,
              'Canton':self.partner_id.fe_canton_id.code,
              'Distrito':self.partner_id.fe_district_id.code,
              'OtrasSenas':self.partner_id.fe_other_signs,
           }})

        if self.partner_id.fe_neighborhood_id.code:
           self.invoice[self.fe_doc_type]['Receptor']['Ubicacion'].update({'Barrio':self.partner_id.fe_neighborhood_id.code})

        if self.partner_id.fe_receptor_otras_senas_extranjero:
           self.invoice[self.fe_doc_type]['Receptor'].update({'OtrasSenasExtranjero':self.partner_id.fe_receptor_otras_senas_extranjero})

        if self.partner_id.phone:
           self.invoice[self.fe_doc_type]['Receptor'].update({'Telefono':{
              'CodigoPais':str(self.company_id.country_id.phone_code),
              'NumTelefono':self.partner_id.phone or None,
           }})

        if self.partner_id.fe_fax_number:
           self.invoice[self.fe_doc_type]['Receptor'].update({'Fax':{
              'CodigoPais':str(self.company_id.country_id.phone_code),
              'NumTelefono':self.partner_id.fe_fax_number,
           }})

        if self.partner_id.email:
           self.invoice[self.fe_doc_type]['Receptor'].update({'CorreoElectronico':self.partner_id.email})

        self.invoice[self.fe_doc_type].update({'CondicionVenta':self.payment_term_id.fe_condition_sale})

        if self.payment_term_id.name:
           self.invoice[self.fe_doc_type].update({'PlazoCredito':self.payment_term_id.name})

        self.invoice[self.fe_doc_type].update({'MedioPago':self.fe_payment_type})

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

        for i in self.invoice_line_ids:
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

            inv_lines[arrayCount]['UnidadMedida'] = i.product_id.uom_id.name

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
                LineaNaturalezaDescuento = "PENDIENTE_REFERENCIA AL NOMBRE DE LA TARIFA O UNO DEFAULT"

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

            if i.product_id.type == 'Service':
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

        self.invoice[self.fe_doc_type]['DetalleServicio'] = {'LineaDetalle':inv_lines}



        self.invoice[self.fe_doc_type].update({
           'OtrosCargos':OtrosCargos_array
        })

        self.invoice[self.fe_doc_type].update(
            {'ResumenFactura':{
                   'CodigoTipoMoneda':{
                      'CodigoMoneda':self.currency_id.name,
                      'TipoCambio':'{0:.5f}'.format(self.currency_id.rate),
                   }
            }})

        TotalGravado = TotalServGravados + TotalMercanciasGravadas
        TotalExento = TotalServExentos + TotalMercanciasExentas
        TotalExonerado = TotalServExonerado + TotalMercExonerada
        TotalVenta = TotalGravado + TotalExento #+ TotalExonerado   #REVISAR EL EXONERADO SI SE SUMA O RESTA
        TotalVentaNeta = TotalVenta - TotalDescuentos

        if TotalServGravados:
           self.invoice[self.fe_doc_type]['ResumenFactura'].update({'TotalServGravados':'{0:.5f}'.format(TotalServGravados)})

        if TotalServExentos:
           self.invoice[self.fe_doc_type]['ResumenFactura'].update({'TotalServExentos':'{0:.5f}'.format(TotalServExentos)})

        if TotalServExonerado:
           self.invoice[self.fe_doc_type]['ResumenFactura'].update({'TotalServExonerado':'{0:.5f}'.format(TotalServExonerado)})

        if TotalMercanciasGravadas:
           self.invoice[self.fe_doc_type]['ResumenFactura'].update({'TotalMercanciasGravadas':'{0:.5f}'.format(TotalMercanciasGravadas)})

        if TotalMercanciasExentas:
           self.invoice[self.fe_doc_type]['ResumenFactura'].update({'TotalMercanciasExentas':'{0:.5f}'.format(TotalMercanciasExentas)})

        if TotalMercExonerada:
           self.invoice[self.fe_doc_type]['ResumenFactura'].update({'TotalMercExonerada':'{0:.5f}'.format(TotalMercExonerada)})

        if TotalGravado:
           self.invoice[self.fe_doc_type]['ResumenFactura'].update({'TotalGravado':'{0:.5f}'.format(TotalServGravados + TotalMercanciasGravadas)})

        if TotalExento:
           self.invoice[self.fe_doc_type]['ResumenFactura'].update({'TotalExento':'{0:.5f}'.format(TotalServExentos + TotalMercanciasExentas)})

        if TotalExonerado:
           self.invoice[self.fe_doc_type]['ResumenFactura'].update({'TotalExonerado':'{0:.5f}'.format(TotalServExonerado + TotalMercExonerada)})

        if TotalVenta:
           self.invoice[self.fe_doc_type]['ResumenFactura'].update({'TotalVenta':'{0:.5f}'.format(TotalVenta)})
        else:
            self.invoice[self.fe_doc_type]['ResumenFactura'].update({'TotalVenta':'0'})

        if TotalDescuentos:
           self.invoice[self.fe_doc_type]['ResumenFactura'].update({'TotalDescuentos':'{0:.5f}'.format(TotalDescuentos)})

        if TotalVentaNeta:
           self.invoice[self.fe_doc_type]['ResumenFactura'].update({'TotalVentaNeta':'{0:.5f}'.format(TotalVentaNeta)})
        else:
            self.invoice[self.fe_doc_type]['ResumenFactura'].update({'TotalVentaNeta':'0'})

        if TotalImpuesto:
           self.invoice[self.fe_doc_type]['ResumenFactura']['TotalImpuesto'] = '{0:.5f}'.format(TotalImpuesto)
        else:
            self.invoice[self.fe_doc_type]['ResumenFactura']['TotalImpuesto'] = '0'



        ##PENDINETE TOTALIVADEVUELTO
        #self.invoice[self.fe_doc_type]['ResumenFactura']['TotalIVADevuelto'] = 'PENDIENTE_TOTAL_IVA_DEVUELTO'     # CONDICIONAL
             #Este campo será de condición obligatoria cuando se facturen servicios de salud y cuyo método de pago sea “Tarjeta”.
             #Se obtiene de la sumatoria del Monto de los Impuestos pagado por los servicios de salud en tarjetas.
             #Es un número decimal compuesto por 13 enteros y 5 decimales.

        if TotalOtrosCargos:
           self.invoice[self.fe_doc_type]['ResumenFactura']['TotalOtrosCargos'] = '{0:.5f}'.format(TotalOtrosCargos)

        TotalComprobante = TotalVentaNeta + TotalImpuesto #+ TotalOtrosCargos - TotalIVADevuelto
        if TotalComprobante:
           self.invoice[self.fe_doc_type]['ResumenFactura']['TotalComprobante'] = '{0:.5f}'.format(TotalComprobante) #'PENDIENTE_TOTAL_Comprobante'
           #SUMA DE: "total venta neta" + "monto total del impuesto" + "total otros cargos" - total IVA devuelto
        else:
            self.invoice[self.fe_doc_type]['ResumenFactura']['TotalComprobante'] ='0'

        if self.number[8:10] == "02" or self.number[8:10] == "03":
           if not self.origin:
              error = True
              msg = 'Indique el NUMERO CONSECUTIVO de REFERENCIA\n'
           else:
              if len(self.origin) == 20:
                 origin_doc = self.search([('number', '=', self.origin)])
                 origin_doc_fe_fecha_emision = origin_doc.fe_fecha_emision.split(' ')[0] + 'T' + origin_doc.fe_fecha_emision.split(' ')[1]+'-06:00'
                 self.invoice[self.fe_doc_type].update({
                    'InformacionReferencia':{
                       'TipoDoc':origin_doc.number[8:10],
                       'Numero':origin_doc.number,
                       'FechaEmision': origin_doc_fe_fecha_emision,
                       'Codigo':self.fe_informacion_referencia_codigo,
                       'Razon':self.name,
                    }
                 })

        if self.comment:
           self.invoice[self.fe_doc_type].update({
              'Otros':{
                 'OtroTexto':self.comment,
                 #'OtroContenido':'ELEMENTO OPCIONAL'
              }
           })
        #PDF de FE,FEE,FEC,ND,NC
        #En caso de que el server-side envie el mail

        self.invoice[self.fe_doc_type].update({'PDF':self._get_pdf_bill(self.id)})



    @api.multi
    def _send_invoice(self,inv):
        log.info('--> factelec-Invoice-_send_invoice')

        self._cr_xml_factura_electronica()
        json_string = json.dumps(inv)
        header = {'Content-Type':'application/json'}
        url = self.env.user.company_id.fe_url_server
        log.info('XXXX JSON STRING \n%s\n',json_string)
        response = requests.post(url, headers = header, data = json_string)



        try:
            log.info('\n ====853=== Response : %s\n',response.text )
            '''Response : {"id": null, "jsonrpc": "2.0", "result": {"status": "200"}}'''
            json_response = json.loads(response.text)

            if "result" in json_response.keys():
                result = json_response['result']
                if "status" in result.keys():
                    if result['status'] == "200":
                        log.info('\n ========== exito : %s\n')
                        inv.update({'fe_server_state':'enviado a procesar'})

                elif "error" in  result.keys():
                    result = json_response['result']['error']
                    body = "Error3 "+result
                    inv.write_chatter(body)

        except Exception as e:
            body = "Error4 "+str(e)  #DEBUG
            inv.write_chatter(body)

    @api.model
    def build_json(self):
        log.info('--> factelec-Invoice-build_json')
        inv_list = self.env['account.invoice'].search([('fe_server_state','=','pendiente enviar'),('state','=','open')])
        for inv in inv_list:
            self._send_invoice(inv)
