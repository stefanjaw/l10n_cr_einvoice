from odoo import models, fields, api, exceptions
from odoo.exceptions import ValidationError
from datetime import datetime,timezone
from lxml.etree import Element, fromstring, parse, tostring, XMLParser
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

class AccountMoveFunctions(models.Model):
    _inherit = "account.move"
    

    @api.model
    def default_fe_in_invoice_type(self):
        journal = super(AccountMoveFunctions, self)._get_default_journal()
        if len(journal.sequence_id.prefix) == 10 :
                if journal.sequence_id.prefix[8:10] == '08':
                   return 'FEC'
                elif journal.sequence_id.prefix[8:10] == '09':
                    return 'FEX'
                elif journal.sequence_id.prefix[8:10] == '01':
                    return 'FE'
                elif journal.sequence_id.prefix[8:10] == '02':
                    return 'ND'
                else:
                    return 'OTRO'


    @api.onchange("journal_id",)
    def _onchange_journal_id(self):
        self.fe_in_invoice_type = 'OTRO'
        if self.journal_id:
            if len(self.journal_id.sequence_id.prefix) == 10 :
                if self.journal_id.sequence_id.prefix[8:10] == '08':
                    self.fe_in_invoice_type = 'FEC'
                elif self.journal_id.sequence_id.prefix[8:10] == '09':
                    self.fe_in_invoice_type = 'FEX'
                elif self.journal_id.sequence_id.prefix[8:10] == '01':
                    self.fe_in_invoice_type = 'FE'
                elif self.journal_id.sequence_id.prefix[8:10] == '02':
                    self.fe_in_invoice_type = 'ND'
                else:
                    self.fe_in_invoice_type = 'OTRO'
            else:
                self.fe_in_invoice_type = 'OTRO'
                log.info('largo del prefijo del diario menor a 10')
                
    @api.onchange("currency_id","invoice_date",)
    def _onchange_currency_rate(self):
        #buscar error con respecto a dolares
        '''for s in self:
            log.info('-->577381353')
            if s.currency_id.name == "USD": 
                date = None
                if not s.invoice_date:
                    date = time.strftime("%Y-%m-%d")
                else:
                    date = s.invoice_date 
                                        
                s._rate(date)'''
                            
    @api.constrains('fe_doc_ref')
    def _constrains_fe_doc_ref(self):
         if self.name[8:10] == '03' or self.name[8:10] == '02':
                doc = self.search([('name', '=', self.fe_doc_ref)])
                if not doc:
                    raise ValidationError('El documento de referencia no existe')
                
        
    
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
                    if i.tax_ids:
                        totalAmount = i.price_unit * i.quantity
                        totalServGravados = totalServGravados + totalAmount

        self.fe_total_servicio_gravados = totalServGravados


    def _compute_total_servicios_exentos(self):
        log.info('--> factelec/_compute_total_servicios_exentos')
        totalServExentos = 0
        for s in self:
            for i in s.invoice_line_ids:
                if i.product_id.type == 'Service':
                    if i.tax_ids:
                        totalAmount = i.price_unit * i.quantity
                        totalServExentos = totalServExentos + totalAmount

        self.fe_total_servicio_exentos  = totalServExentos


    def _compute_total_mercancias_gravadas(self):
        log.info('--> factelec/_compute_total_mercancias_gravadas')
        totalMercanciasGravadas = 0
        for s in self:
            for i in s.invoice_line_ids:
                if i.product_id.type != 'Service':
                        if i.tax_ids:
                            totalAmount = i.price_unit * i.quantity
                            totalMercanciasGravadas = totalMercanciasGravadas + totalAmount
        self.fe_total_mercancias_gravadas =  totalMercanciasGravadas


    def _compute_total_mercancias_exentas(self):
        log.info('--> factelec/_compute_total_mercancias_exentas REPETIDO1')
        totalMercanciasExentas = 0
        for s in self:
            for i in s.invoice_line_ids:
                if i.product_id.type != 'Service':
                        if not i.tax_ids:
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
                    if not i.tax_ids:
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
            doc_type = self.get_doc_type(dic)
            # 1570054332
            self.fe_xml_supplier_xslt = self.transform_doc(root_xml,doc_type)
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
                'NumeroCedulaReceptor':self.company_id.vat.replace('-','').replace(' ','') or None,#bill_dic['FacturaElectronica']['Receptor']['Identificacion']['Numero'],
                'TipoCedulaReceptor':bill_dic['FacturaElectronica']['Receptor']['Identificacion']['Tipo'],
                'NumeroConsecutivoReceptor':self.name,
                #'EmisorEmail':self.partner_id.email,
                #'pdf':self._get_pdf_bill(self.id) or None,
                }}
            return self.invoice
        else:
            msg = 'adjunte una factura electronica antes de confirmar la aceptacion'
            raise exceptions.Warning((msg))

    def _cr_post_server_side(self):
        if not self.company_id.fe_certificate:
            raise exceptions.Warning(('No se encuentra el certificado en compañia'))
            
        log.info('--> factelec-Invoice-_cr_post_server_side')
        
        if self.name[8:10] == '05':
            self._cr_validate_mensaje_receptor()
            invoice = self._cr_xml_mensaje_receptor()
        else:
            invoice = self._cr_xml_factura_electronica()
        
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

        self.source_date = self.invoice_date

        if country_code == 'CR':
            if self.name[8:10] == "01": 
                self._validate_company()
                self.validar_datos_factura()
                self._validate_invoice_line()                   #FACTURA ELECTRONICA
                self.fe_doc_type = "FacturaElectronica"
                self._cr_post_server_side()

            elif self.name[8:10] == "02":
                self._validate_company()
                self.validar_datos_factura()
                self._validate_invoice_line()                  #NOTA DEBITO ELECTRONICA
                self.fe_doc_type = "NotaDebitoElectronica"
                self._cr_post_server_side()

            elif self.name[8:10] == "03": 
                self._validate_company()
                self.validar_datos_factura()
                self._validate_invoice_line()                 #NOTA CREDITO ELECTRONICA
                self.fe_doc_type = "NotaCreditoElectronica"
                self._cr_post_server_side()

            elif self.name[8:10] == "05":                 #Vendor Bill - Mensaje Receptor - Aceptar Factura

                if self.fe_xml_hacienda:
                   msg = '--> Ya se tiene el XML de Hacienda Almacenado'
                   log.info(msg)
                   raise exceptions.Warning((msg))

                else:
                   self.fe_doc_type = "MensajeReceptor"
                   tz = pytz.timezone('America/Costa_Rica')
                   self.fe_fecha_emision_doc = datetime.now(tz=tz).strftime("%Y-%m-%d %H:%M:%S")
                   self._cr_post_server_side()

            elif self.name[8:10] == "08":  
                self._validate_company()
                self.validar_datos_factura()
                self._validate_invoice_line()                  #FACTURA ELECTRONICA COMPRA
                self.fe_doc_type = "FacturaElectronicaCompra"
                self._cr_post_server_side()

            elif self.name[8:10] == "09":
                self._validate_company()
                self.validar_datos_factura()
                self._validate_invoice_line()                    #FACTURA ELECTRONICA COMPRA
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

            if line.product_uom_id.uom_mh not in units:
                raise exceptions.Warning(("La unidad de medida {0} no corresponde a una unidad valida en el ministerio de hacienda! configure el campo Unidad Medida MH en la Unidad {1}".format(line.product_uom_id.uom_mh,line.product_uom_id.name)))

            if not line.product_id.cabys_code_id:
                raise exceptions.Warning(("El producto {0} no contiene código CABYS".format(line.product_id.name)))


            if line.tax_ids:

               for tax_id in line.tax_ids:

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

           
    def validar_datos_factura(self):
        
            msg = ''
            if self.name[8:10] != '08':
                if self.partner_id.state_id:                
                    if not self.partner_id.state_id.fe_code:
                        msg += 'En el Cliente, el codigo para factura electronica de la provincia es requerida \n'

                    if not self.partner_id.canton_id:
                        msg += 'En el Cliente, el canton es requerido \n'
                        
                    if not self.partner_id.distrito_id:
                        msg += 'En el Cliente, el distrito es requerido \n'

                    if not self.partner_id.street:
                        msg += 'En el Cliente, el campo otras señas es requerido \n'

            if not self.fe_activity_code_id:
                msg += 'Falta la actividad económica \n'
            elif len(self.fe_activity_code_id.code) != 6:
                msg += 'El codigo de la actividad económica debe ser de un largo de 6 \n'
            
            if not self.invoice_payment_term_id.payment_term_hacienda:
                msg += 'En el plazo de pago falta el plazo credito hacienda \n'
            elif len(self.invoice_payment_term_id.payment_term_hacienda) > 10:
                msg += 'El nombre del plazo de pago debe ser menor aun largo de 10 \n'
                
            if not self.name:
                msg += 'El documento no contiene numero consecutivo \n'
            elif len(self.name) != 20:
                msg += 'El consecutivo del documento debe ser de un largo de 20 \n'
            
            if not self.fe_clave:
                msg += 'El documento no contiene clave \n'

            elif len(self.fe_clave) != 50:
                msg += 'La clave tiene que tener un largo de 50 \n'
            
            if not self.fe_fecha_emision:
                msg += 'Falta la fecha de emisión \n'
                
            if not self.invoice_payment_term_id.fe_condition_sale:
                msg += 'Falta definir en el plazo de pago la condición de venta\n'
            
            if not self.fe_payment_type:
                msg += 'Falta el tipo de pago \n'
                
            if not self.fe_receipt_status:
                msg += 'Falta la situación del comprobante \n'
            
            if self.name[8:10] == '03' or self.name[8:10] == '02':
                if not self.fe_doc_ref:
                    msg += 'Falta el documento de referencia \n'
                if not self.fe_tipo_documento_referencia:
                    msg += 'Falta el tipo documento referencia \n'
                if not self.fe_informacion_referencia_codigo:
                    msg += 'Falta el codigo referencia \n'
                if not self.ref:
                    msg += 'Falta la razón en el campo referencia \n'
            
                
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
                
                
             #Docuemento tipo 08 factura de proveedor regimen simplificado   
            if self.name[8:10] == '08':
                
                if not self.partner_id.state_id:
                     msg += 'En el proveedor, la provincia es requerida \n'
                
                elif not self.partner_id.state_id.fe_code:
                     msg += 'En el proveedor, el codigo para factura electronica de la provincia es requerida \n'

                if not self.partner_id.canton_id:
                    msg += 'En el proveedor, el canton es requerido \n'
                    
                if not self.partner_id.distrito_id:
                    msg += 'En el proveedor, el distrito es requerido \n'

                if not self.partner_id.street:
                    msg += 'En el proveedor, el campo otras señas es requerido \n'
                    
            
            
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
            
            if  self.name[8:10] != '09':
            
                if not self.partner_id.fe_identification_type:
                    msg += 'En el cliente, falta el tipo de identificación \n'

                if not self.partner_id.vat:
                    msg += 'En el cliente, falta el campo NIF \n'
                
            elif len(self.company_id.vat) < 9 and len(self.company_id.vat) >12:
                msg += 'En el cliente, el largo del NIF debe ser entre 9 y 12 \n'
            
            if self.partner_id.phone:
                if len(self.partner_id.phone) < 8 and len(self.partner_id.phone) > 20:
                  msg += 'En el cliente, el numero de teléfono debe ser igual o mayor que 8 y menor que 20 \n'
            
            if self.partner_id.fe_fax_number:
                if len(self.partner_id.fe_fax_number)  < 8 and len(self.partner_id.fe_fax_number) > 20:
                   msg += 'En el cliente, el numero de fax debe ser igual o mayor que 8 y menor que 20 \n'
            
            if not self.partner_id.email:
                 msg += 'En el cliente, el correo electrónico es requerido \n'
                    
            if msg:        
                raise ValidationError(msg)
   
           

    def _generar_clave(self):
        document_date_invoice = datetime.strptime(str(self.invoice_date),'%Y-%m-%d')
        if self.fe_doc_type != "MensajeReceptor":
           country_code = self.company_id.country_id.phone_code
           vat = self.company_id.vat or ''
           vat = vat.replace('-','')
           vat = vat.replace(' ','')
           vat_complete = "0" * (12 - len(vat)) + vat
           clave = str(country_code) + document_date_invoice.strftime("%d%m%y") \
              + str(vat_complete) + str(self.name) + str(self.fe_receipt_status or '1') \
              + str("87654321")
           self.fe_clave = clave


    def action_post(self,validate = True):
        for s in self:
            log.info('--> action_post')
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
                                            if s.fe_xml_supplier == False:
                                                msg = 'Falta el XML del proveedor'
                                                raise exceptions.Warning((msg))
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
                                    



                date_temp = s.invoice_date 
                log.info('--> 1575061615')
                res = super(AccountMoveFunctions, s).action_post()
                tz = pytz.timezone('America/Costa_Rica')
                
                if not date_temp:
                    s.fe_fecha_emision = datetime.now(tz=tz).strftime("%Y-%m-%d %H:%M:%S")
                    s.invoice_date = s.fe_fecha_emision
                else:
                    s.fe_fecha_emision = '{0} {1}'.format(date_temp,datetime.now(tz=tz).strftime("%H:%M:%S"))
                
                s._validate_company()
                if s.name[8:10] != '05':
                    s._generar_clave()
                log.info('--->Clave %s',s.fe_clave)
                s.validar_datos_factura()
                #s.validacion()
                s._validate_invoice_line()
            else:
                log.info('--> 1575061637')
                res = super(AccountMoveFunctions, s).action_post()



    def get_invoice(self):
        for s in self:
            if not s.fe_server_state:
                raise exceptions.Warning('Porfavor envie el documento antes de consultarlo')
            if s.state == 'draft':
              raise exceptions.Warning('VALIDE primero este documento')
            #peticion al servidor a partir de la clave
            log.info('--> 1569447129')
            log.info('--> get_invoice')
            if not 'http://' in s.company_id.fe_url_server and  not 'https://' in s.company_id.fe_url_server:
               raise ValidationError("El campo Server URL en comapañia no tiene el formato correcto, asegurese que contenga http://")
            if s.fe_xml_hacienda:
                 raise ValidationError("Ya se tiene la RESPUESTA de Hacienda")

            if s.name[8:10] == "05":
               if not s.fe_clave:
                  log.info("soy un documento 05 sin clave {}".format(s.name))
               url = s.company_id.fe_url_server+'{0}'.format(s.fe_clave+'-'+s.name)
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
        #pdf = self.env.ref('account.account_invoices_without_payment').with_context(ctx).render(id)
        pdf = self.env.ref('account.account_invoices').with_context(ctx).render(id)
        pdf64 = base64.b64encode(pdf[0]).decode('utf-8')
        return pdf64


    @api.model
    def cron_get_server_bills(self):
        log.info('--> cron_get_server_bills')
        list = self.env['account.move'].search(['|',('fe_xml_sign','=',False),('fe_xml_hacienda','=',False),'&',('state','=','posted'),
        ('fe_server_state','!=','pendiente enviar'),('fe_server_state','!=',False)])

        for item in list:
            if item.company_id.country_id.code == 'CR' and item.fe_in_invoice_type != 'OTRO':
                log.info(' item name %s',item.name)
                item.get_invoice()
               

    def write_chatter(self,body):
        log.info('--> write_chatter')
        chatter = self.env['mail.message']
        chatter.create({
                        'res_id': self.id,
                        'model':'account.move',
                        'body': body,
                       })


    def _cr_xml_factura_electronica(self):
        log.info('--> factelec-Invoice-_cr_xml_factura_electronica')
        for s in self:
            s.invoice = {}
            s.invoice[s.fe_doc_type] = {'CodigoActividad':s.fe_activity_code_id.code}
            s.invoice[s.fe_doc_type].update({'Clave':s.fe_clave})
            s.invoice[s.fe_doc_type].update({'NumeroConsecutivo':s.name})
            s.invoice[s.fe_doc_type].update({'FechaEmision':s.fe_fecha_emision.split(' ')[0]+'T'+s.fe_fecha_emision.split(' ')[1]+'-06:00'})
            s.invoice[s.fe_doc_type].update({'Emisor':{
                'Nombre':s.company_id.company_registry
            }})
            s.invoice[s.fe_doc_type]['Emisor'].update({
            'Identificacion':{
                'Tipo': s.company_id.fe_identification_type or None,
                'Numero':s.company_id.vat.replace('-','').replace(' ','') or None,
            },
            })

            if s.company_id.fe_comercial_name:
                s.invoice[s.fe_doc_type]['Emisor'].update({'NombreComercial':s.company_id.fe_comercial_name})
            
            s.invoice[s.fe_doc_type]['Emisor'].update({'Ubicacion':{
            'Provincia':s.company_id.state_id.fe_code,
            'Canton':s.company_id.canton_id.code,
            'Distrito':s.company_id.distrito_id.code,
            }})

            if s.company_id.barrio_id.code:
                s.invoice[s.fe_doc_type]['Emisor']['Ubicacion'].update({'Barrio':s.company_id.barrio_id.code})

            s.invoice[s.fe_doc_type]['Emisor']['Ubicacion'].update({'OtrasSenas':s.company_id.street})

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
                    'Provincia':s.partner_id.state_id.fe_code or '',
                    'Canton':s.partner_id.canton_id.code or '',
                    'Distrito':s.partner_id.distrito_id.code or '',
                    'OtrasSenas':s.partner_id.street or '',
                }})

            if  s.partner_id.state_id.fe_code and s.partner_id.barrio_id.code:
                s.invoice[s.fe_doc_type]['Receptor']['Ubicacion'].update({'Barrio':s.partner_id.barrio_id.code})

            #if s.partner_id.fe_receptor_otras_senas_extranjero:
            #   s.invoice[s.fe_doc_type]['Receptor'].update({'OtrasSenasExtranjero':s.partner_id.fe_receptor_otras_senas_extranjero})

            if s.partner_id.phone:
                s.invoice[s.fe_doc_type]['Receptor'].update({'Telefono':{
                    'CodigoPais':str(s.company_id.country_id.phone_code),
                    'NumTelefono':s.partner_id.phone.replace('-','').replace(' ','').replace('+506','') or None,
                }})

            if s.partner_id.fe_fax_number:
                s.invoice[s.fe_doc_type]['Receptor'].update({'Fax':{
                    'CodigoPais':str(s.company_id.country_id.phone_code),
                    'NumTelefono':s.partner_id.fe_fax_number,
                }})

            if s.partner_id.email:
                s.invoice[s.fe_doc_type]['Receptor'].update({'CorreoElectronico':s.partner_id.email})

            s.invoice[s.fe_doc_type].update({'CondicionVenta':s.invoice_payment_term_id.fe_condition_sale})

            if s.invoice_payment_term_id.payment_term_hacienda:
                s.invoice[s.fe_doc_type].update({'PlazoCredito':s.invoice_payment_term_id.payment_term_hacienda})
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
                MontoExoneracion = 0
                percent = 0

                inv_lines.append({'NumeroLinea':NumeroLinea})

                #PartidaArancelaria   #PENDIENTE, Cuando el comprobante es del tipo Exportacion

                #if i.product_id.default_code:
                inv_lines[arrayCount]['Codigo'] = i.product_id.cabys_code_id.code

                if i.product_id.fe_codigo_comercial_codigo:
                    inv_lines[arrayCount]['CodigoComercial'] = {
                        'Tipo':i.product_id.fe_codigo_comercial_tipo,
                        'Codigo':i.product_id.fe_codigo_comercial_codigo,
                    }

                LineaCantidad = round(i.quantity,3)
                inv_lines[arrayCount]['Cantidad'] = '{0:.3f}'.format(LineaCantidad)

                inv_lines[arrayCount]['UnidadMedida'] = i.product_uom_id.uom_mh

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

                if i.tax_ids:

                    ## COMIENZA TAXES y OTROS CARGOS

                    for tax_id in i.tax_ids :
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
                            
                            if self.fiscal_position_id:
                                old_tax = self.fiscal_position_id.tax_ids.search([('tax_dest_id','=',tax_id.id)]).tax_src_id
                                LineaImpuestoTarifa = round(old_tax.amount,2)
                                inv_lines[arrayCount]['Impuesto'] = {
                                    'Codigo':old_tax.tarifa_impuesto,
                                    'CodigoTarifa':old_tax.codigo_impuesto,
                                    'Tarifa':'{0:.2f}'.format(LineaImpuestoTarifa)
                                    }
                            else:
                                LineaImpuestoTarifa = round(tax_id.amount,2)
                                inv_lines[arrayCount]['Impuesto'] = {
                                    'Codigo':tax_id.tarifa_impuesto,
                                    'CodigoTarifa':tax_id.codigo_impuesto,
                                    'Tarifa':'{0:.2f}'.format(LineaImpuestoTarifa)
                                    }

                            LineaImpuestoMonto = round((LineaSubTotal * LineaImpuestoTarifa/100),5)
                            inv_lines[arrayCount]['Impuesto'].update(dict({'Monto':'{0:.5f}'.format(LineaImpuestoMonto)}))

                            if self.fiscal_position_id:
                                fisical = self.fiscal_position_id.tax_ids.search([('tax_dest_id','=',tax_id.id)])
                                percent = fisical.tax_src_id.amount - fisical.tax_dest_id.amount
                                exoneration = {}
                                exoneration['TipoDocumento'] = self.fiscal_position_id.fiscal_position_type or ''
                                exoneration['NumeroDocumento'] = self.fiscal_position_id.document_number or ''
                                exoneration['NombreInstitucion'] = self.fiscal_position_id.institution_name or ''
                                exoneration['FechaEmision'] = self.fiscal_position_id.issued_date.strftime("%Y-%m-%dT%H:%M:%S-06:00") or ''
                                exoneration['PorcentajeExoneracion'] =  int(percent) or '0'
                                MontoExoneracion = round(LineaSubTotal * ( percent / 100),5)
                                exoneration['MontoExoneracion'] =  MontoExoneracion
                                inv_lines[arrayCount]['Impuesto'].update( dict({'Exoneracion': exoneration }) )
                                if i.product_id.type == 'service':
                                    TotalServExonerado = TotalServExonerado + LineaSubTotal * ( percent / LineaImpuestoTarifa )
                                else:
                                    TotalMercExonerada = TotalMercExonerada + LineaSubTotal * ( percent / LineaImpuestoTarifa )

                                

   
                            LineaImpuestoNeto = round(LineaImpuestoMonto - MontoExoneracion,5) # - LineaImpuestoExoneracion
                            inv_lines[arrayCount]['ImpuestoNeto'] = '{0:.5f}'.format(round(LineaImpuestoNeto,5))
                        #Si esta exonerado al 100% se debe colocar 0-Zero

                    #XXXXXX FALTA TOTAL IVA DEVUELTO

                            TotalImpuesto = round((TotalImpuesto + LineaImpuestoNeto),5)

                MontoTotalLinea = round((LineaSubTotal + LineaImpuestoNeto),5)
                inv_lines[arrayCount]['MontoTotalLinea'] = '{0:.5f}'.format(MontoTotalLinea)

                if i.product_id.type == 'service':
                    #asking for tax for know if the product is Tax Free
                    if i.tax_ids:
                        if self.fiscal_position_id:
                            TotalServGravados = TotalServGravados + (1-percent/LineaImpuestoTarifa) * LineaMontoTotal
                        else:
                            TotalServGravados = TotalServGravados + LineaMontoTotal
                    else:
                        TotalServExentos = TotalServExentos + LineaMontoTotal
                    #  XXXX PENDIENTE LOS ServExonerados
                else:
                    if i.tax_ids:
                         if self.fiscal_position_id:
                            TotalMercanciasGravadas = TotalMercanciasGravadas + (1-percent/LineaImpuestoTarifa) * LineaMontoTotal
                         else:
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
            TotalVenta = TotalGravado + TotalExento + TotalExonerado   #REVISAR EL EXONERADO SI SE SUMA O RESTA
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

            if s.name[8:10] == "02" or s.name[8:10] == "03" or  s.name[8:10] == "08":
                if not s.fe_doc_ref:
                    error = True
                    msg = 'Indique el NUMERO CONSECUTIVO de REFERENCIA\n'
                else:
                    if len(s.fe_doc_ref) == 20:
                        origin_doc = s.search([('name', '=', s.fe_doc_ref)])
                        if origin_doc:
                            origin_doc_fe_fecha_emision = origin_doc.fe_fecha_emision.split(' ')[0] + 'T' + origin_doc.fe_fecha_emision.split(' ')[1]+'-06:00'
                            s.invoice[s.fe_doc_type].update({
                                'InformacionReferencia':{
                                'TipoDoc':s.fe_tipo_documento_referencia,
                                'Numero':origin_doc.name,
                                'FechaEmision': origin_doc_fe_fecha_emision,
                                'Codigo':s.fe_informacion_referencia_codigo or None,
                                'Razon':s.ref,
                                }
                            })
                        else:
                            error = True
                            msg = 'El documento de referencia {} no existe! \n'.format(s.fe_doc_ref)
                    else:
                        if s.fe_doc_ref:
                            s.invoice[s.fe_doc_type].update({
                                    'InformacionReferencia':{
                                    'TipoDoc':s.fe_tipo_documento_referencia,
                                    'Numero':s.fe_doc_ref,
                                    'FechaEmision':s.fecha_factura_simplificada.astimezone(tz=pytz.timezone('America/Costa_Rica')).isoformat('T'),
                                    'Codigo':s.fe_informacion_referencia_codigo or None,
                                    'Razon':s.ref,
                                    }
                                })


            if s.narration:
                s.invoice[s.fe_doc_type].update({
                    'Otros':{
                        'OtroTexto':s.narration,
                        #'OtroContenido':'ELEMENTO OPCIONAL'
                    }
                })
            #PDF de FE,FEE,FEC,ND,NC
            #En caso de que el server-side envie el mail

            s.invoice[s.fe_doc_type].update({'PDF':s._get_pdf_bill(s.id)})
            return s.invoice

    @api.model
    def cron_send_json(self):
        log.info('--> factelec-Invoice-build_json')
        invoice_list = self.env['account.move'].search(['&',('fe_server_state','=',False),('state','=','posted')])
        log.info('-->invoice_list %s',invoice_list)
        for invoice in invoice_list:
            if invoice.company_id.country_id.code == 'CR' and invoice.fe_in_invoice_type != 'OTRO':
                try:
                    log.info('-->consecutivo %s',invoice.name)
                    invoice.confirm_bill()
                except Exception as ex:
                    invoice.write_chatter(ex)
                    invoice.update({
                        'fe_server_state':'error'
                    })

        
    def mostrar_wizard_nota_debito(self):
        return {
                'type': 'ir.actions.act_window',
                'name': 'Nota Débito',
                'res_model': 'account.move.debit',
                'view_type': 'form',
                'view_mode': 'form',
                'views': [(False, 'form')],
                'target': 'new',
                'context': {
                    'active_id':self.id,
                    'doc_ref':self.name,
                 }
             }    
