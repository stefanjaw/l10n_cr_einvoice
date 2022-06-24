# -*- coding: utf-8 -*-

from odoo import models, fields, api
import base64

import requests
import json

from urllib.parse import quote

from odoo import _
from odoo.exceptions import ValidationError

import logging

_logging = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = "account.move"

    def create_xml(self):
        _logging.info("==> Creating XML for: {0}".format( self.name ) )
        record_data_json = {}
        account_move_json = self.get_account_move_data( self.id )
        if account_move_json:
            record_data_json['account_move'] = account_move_json

        fe_activity_code = self.get_fe_activity_code( self.fe_activity_code_id.id  )
        if fe_activity_code:
            record_data_json['fe_activity_code'] = fe_activity_code
            
        account_move_lines_lst = self.get_account_move_lines_data( self.id )
        if not account_move_lines_lst:
            _logging.info("  ==> NO LINES IN INVOICE")
            return False
        if len(account_move_lines_lst) > 0:
            record_data_json['account_move_line'] = account_move_lines_lst

        product_product_data_lst = self.get_product_product_data_lst( account_move_lines_lst )
        if len(product_product_data_lst) > 0:
            record_data_json['product_product'] = product_product_data_lst

        cabys_code_lst = self.get_cabys_code( product_product_data_lst )
        if len(cabys_code_lst) > 0:
            record_data_json['cabys_code'] = cabys_code_lst
            
        uom_uom = self.get_uoms( account_move_lines_lst )
        if len(uom_uom) > 0:
            record_data_json['uom_uom'] = uom_uom
            
        res_partner_json = self.get_res_partner_data( self.partner_id.id )
        if res_partner_json:
            record_data_json['res_partner'] = res_partner_json
        
        account_fiscal_position = self.get_account_fiscal_position( self.fiscal_position_id.id )
        account_fiscal_position_line = False
        if account_fiscal_position:
            record_data_json['account_fiscal_position'] = account_fiscal_position
        
            if len( account_fiscal_position ) > 1:
                _logging.info("  ==> Hay más de una Posición Fiscal")
                PENDIENTE_DESARROLLAR_ESTO_POSIBLE_AGREGAR_ACTIVE
        
            account_fiscal_position_line = \
                self.get_account_fiscal_position_line( account_fiscal_position[0].get('tax_ids') )
            if account_fiscal_position_line:
                record_data_json['account_fiscal_position_line'] = account_fiscal_position_line

        all_invoice_taxes_int_array = []
        if account_fiscal_position_line:
            for record in account_fiscal_position_line:
                all_invoice_taxes_int_array.append( record.get('tax_src_id')[0] )
                all_invoice_taxes_int_array.append( record.get('tax_dest_id')[0] )
        
        if self.invoice_line_ids.tax_ids.ids:
            all_invoice_taxes_int_array += self.invoice_line_ids.tax_ids.ids
            all_invoice_taxes_int_array = list( dict.fromkeys( all_invoice_taxes_int_array ) )
        
        account_tax_lst = self.get_account_tax_lst( all_invoice_taxes_int_array )
        if account_tax_lst:
            record_data_json['account_tax'] = account_tax_lst
        
        res_company_json = self.get_res_company_data( self.company_id.id )
        if res_company_json:
            record_data_json['res_company'] = res_company_json

        fe_certificate = self.company_id.fe_certificate
        if fe_certificate:
            record_data_json['fe_certificate'] = fe_certificate
            
        state_lst = self.get_state_data( [ self.partner_id.id, self.company_id.partner_id.id ]  )
        if state_lst:
            record_data_json['res_country_state'] = state_lst
            
        canton_lst = self.get_canton_data( [ self.partner_id.id, self.company_id.partner_id.id ]  )
        if canton_lst:
            record_data_json['res_country_canton'] = canton_lst
            
        distrito_lst = self.get_distrito_data( [ self.partner_id.id, self.company_id.partner_id.id ]  )
        if distrito_lst:
            record_data_json['res_country_distrito'] = distrito_lst
            
        barrio_lst = self.get_barrio_data( [ self.partner_id.id, self.company_id.partner_id.id ]  )
        if barrio_lst:
            record_data_json['res_country_barrio'] = barrio_lst

        record_data_json['exchange_rate'] = self.exchange_rate
            
        if self.narration:
            record_data_json['narration'] = self.narration

        otros_lst = self.get_otros_ids ( self.id )
        if otros_lst:
            record_data_json['otros'] = otros_lst

        informacion_referencia = self.get_informacion_referencia( self.id )
        if informacion_referencia:
            record_data_json['informacion_referencia'] = informacion_referencia

        res_country = self.get_res_country_data( [self.company_id.country_id.id, self.partner_id.country_id.id] )
        if res_country:
            record_data_json['res_country'] = res_country

        account_payment_term = self.get_account_payment_term(  self.invoice_payment_term_id.id )
        if account_payment_term:
            record_data_json['account_payment_term'] = account_payment_term
            
        if account_payment_term:
            account_payment_term_line = self.get_account_payment_term_line(  self.invoice_payment_term_id.line_ids.ids )
            if account_payment_term_line:
                record_data_json['account_payment_term_line'] = account_payment_term_line
        
        result = self.server_side_post( self.company_id, record_data_json)

        try:
            error_list = result['result']['errors'][0]
        except:
            error_list = []

        try:
            error_list = error_list + result.json().get('result').get('errors')
        except:
            pass
        
        if error_list:
            self.write_to_chatter('account.move', self.id, error_list )
            self.write({
                'fe_server_state': "Error",
                'fe_xml_sign': False,
                'fe_name_xml_sign': False,
                'fe_tohacienda_json': False,
                'fe_fromhacienda_json': False,
            })
            return

        try:
            json_to_send = result.json().get('result').get('json_to_send')
        except:
            json_to_send = False
        
        if json_to_send:
            
            server_url_list = self.env['ir.config_parameter'].search_read(
                                [('key','=','web.base.url')],
                                ['value'],
                            )
            server_url = server_url_list[0].get('value')
            callbackUrl = "{0}/api/callbackurl/v43".format( server_url )
            
            json_to_send['callbackUrl'] = callbackUrl
            
            clave = json_to_send.get('clave')
            if clave and len(clave) == 50:
                doc_type = clave[29:31]
            else:
                doc_type = False

            if   doc_type == "01": prefix = "FE-"
            elif doc_type == "02": prefix = "ND-"
            elif doc_type == "03": prefix = "NC-"
            elif doc_type == "04": prefix = "TE-"
            elif doc_type == "08": prefix = "FEC-"
            elif doc_type == "09": prefix = "FEE-"
            else: prefix == "UNK-"
        
            self.write({
                'fe_clave': clave,
                'fe_tohacienda_json': json.dumps(json_to_send),
                'fe_server_state': "XML Generado",
                'fe_xml_sign': json_to_send.get('comprobanteXml'),
                'fe_name_xml_sign': prefix + str( json_to_send.get('clave') ) + ".xml",
                'fe_xml_hacienda': False,
                'fe_name_xml_hacienda': False,
            })

        return
    
    def electronic_docs_prepare_cron(self):
        STOP70
        logging.info("electronic_doc_cron===============")
        records = self.search([],limit=100, order='id asc') # OJO EL FILTRO
        logging.info(" Registros a procesar: %s", len(records) )
        data_array = self.hacienda_data_prepare(records)
        if len( data_array ) > 0:
            _logging.info("  DEB26 data_array to server_side: \n\n%s\n\n", data_array)
            STOP27
            server_side = self.send_server_side( data_array )
            if server_side == False:
                _logging.info("    ERROR AL ENVIAR AL SERVER SIDE")
        else:
            _logging.info(" Sin Registros a Procesar")
        logging.info("electronic_doc_cron END==================")
    
    


    def hacienda_data_prepare(self, records):
        STOP89
        _logging.info("hacienda_data_prepare========")
        _logging.info(" recorriendo: %s", records)
        data_array = []

        #Validar el estado del documento y el largo del Consecutivo
        for record in records:
            _logging.info("DEB46 RECORD: %s", record.name)
            #Validar si existe el company_id en el data_array
            #_logging.info("\n\nDEB48 data_array: %s", data_array )
            try:
                company_data = [ element for element in data_array if \
                                element['company_data'].get('id') == record.company_id.id ]
            except:
                company_data = []

            if len(company_data) == 0:
                _logging.info(" DEB56 Agregada la company al data_array")
                
                company_data = hacienda.get_contact_data_json(self, record.company_id)
                company_data.update({"records": []})
                
                data_array.append({'company_data': company_data, })

            #Create Record Data
            partner_data = hacienda.get_contact_data_json(self, record.partner_id )
            
            #Crear el JSON con todos los registros
            account_move_create_json = hacienda.account_move_create_json(self, record, partner_data )
            if len(account_move_create_json) == 0:
                _logging.info("  Skipped record: %s", record.name)
                continue
            errors =  account_move_create_json[0].get('errors')
            _logging.info("DEB71 Errors: %s", errors)
            if errors and len(errors) > 0:
                _logging.info("  Errores en el registro: %s", record.name)
                errors_txt = '<br>'.join( map(str, errors) )
                self.env['mail.message'].create({
                    'res_id': record.id,
                    'model': record._name,
                    'body': errors_txt,
                })
                record.write({
                    "fe_server_state": "Errors"
                })
                continue
            account_move_create_json[0].pop("errors")

            try:
                company_data = [ element for element in data_array if \
                                element['company_data'].get('id') == record.company_id.id ]
            except:
                company_data = []
                
            if len(company_data) != 1:
                msg = "ERROR: Company Data Array is incorrect, for record: " + record.name
                _logging.info(msg)
                continue
            
            company_data[0]['company_data']['records'].append( account_move_create_json )
        return data_array

    @api.depends('company_id')
    def _get_country_code(self):
        log.info('--> 1575319718')
        for s in self:
            s.fe_current_country_company_code = s.company_id.country_id.code  

    def query_hacienda(self):
        response = self.env['account.hacienda'].sudo().query_hacienda( self )
        _logging.info("  DEF254 Response Hacienda: {0}".format( response )  )
        return

    def query_xml_status(self):
        _logging.info("DEB463 Executed===========")
        Clave = self.fe_clave
        if not Clave or Clave == "":
            self.write({
                'fe_server_state': "Error"
            })
            self.env['mail.message'].create({
                'res_id': self.id,
                'model':'account.move',
                'body': "Clave de Factura Electrónica no está generada",
            })
            return
        
        hacienda_url = "https://api.comprobanteselectronicos.go.cr/recepcion-sandbox/v1/recepcion/"
        
        query_url = hacienda_url + Clave
        
        _logging.info("DEB470 QUERY_URL \n%s", query_url)
        
        oauth_url = "https://idp.comprobanteselectronicos.go.cr/auth/realms/rut-stag/protocol/openid-connect/token"
        
        u_name = self.company_id.fe_user_name
        pwd = self.company_id.fe_user_password
        
        _logging.info("DEB476 Username: %s", u_name)
        _logging.info("DEB477 PSS: %s", pwd)
        if not u_name or not pwd:
            self.write({
                'fe_server_state': "Error"
            })
            self.env['mail.message'].create({
                'res_id': self.id,
                'model':'account.move',
                'body': "Usuario o Password de Hacienda Indefinidos",
            })
            return
        
        token_data_json = self._get_token(oauth_url, u_name, pwd  )
        _logging.info("DEB482 TOKEN DATA: %s", token_data_json)
        
        token_txt = token_data_json.get("text")
        token_json = json.loads( token_data_json.get("text") )
        token = token_json.get("access_token")
        _logging.info("DEB487 token: %s", token)
        
        authorization = "bearer " + str(token)
        _logging.info("DEB492 Bearer: %s", authorization)
        
        headers = {
            'content-type': "application/json",
            'authorization': authorization,
            'cache-control': "no-cache",
        }
        
        
        url = query_url
        response = requests.request("GET", url, headers=headers)
        response_json_full = {
            "headers": response.headers,
            "text": response.text,
            "status_code": response.status_code,
            "reason": response.reason
        }
        _logging.info("DEB497 RESPONSE QUERY: %s", response_json_full)
        
        _logging.info("\n")
        _logging.info( "DEB512 response_json_full: %s", response_json_full )

        if response_json_full["text"] == '' or response_json_full["text"] == False:
            self.write({
                'fe_server_state': "Error"
            })
            _logging.info("DEB587 XYZ: %s", response_json_full.get('status_code'))
            error_msg = "Respuesta Hacienda:"\
                       + "<br>" \
                       + str( response_json_full.get('status_code') ) \
                       + " - " + str( response_json_full.get('reason') ) \
                       + "<br>" \
                       + str( response_json_full.get('headers').get('X-Error-Cause') )
            _logging.info("DEB592 ERRR MSG: %s", error_msg)

            self.env['mail.message'].create({
                'res_id': self.id,
                'model':'account.move',
                'body': error_msg,
            })
            return
        
        hacienda_data_json =  json.loads( response_json_full["text"] )
        _logging.info("DEB514 hacienda_data_txt: %s", hacienda_data_json)
        
        hacienda_ind_estado = hacienda_data_json.get("ind-estado")
        self.write({
            'fe_server_state': hacienda_ind_estado
        })
        
        hacienda_respuesta_xml_b64 = hacienda_data_json.get("respuesta-xml")
        
        _logging.info("DEB519 HACIENDA Estado  %s Respuesta: \n%s", hacienda_ind_estado, hacienda_respuesta_xml_b64)
        
        self.write({
            'fe_name_xml_hacienda': self.fe_clave + "-hacienda.xml",
            'fe_xml_hacienda': hacienda_respuesta_xml_b64,
        })
        
        hacienda_respuesta_xml = certificate = base64.b64decode( hacienda_respuesta_xml_b64 ).decode('utf-8')
        _logging.info( "DEB522 hacienda_respuesta_xml: \n%s", hacienda_respuesta_xml )
        
        
    def hacienda_post_json(self):
        _logging.info("==> POST a HACIENDA para: {0}".format( self.name ))
        hacienda_json = self.fe_tohacienda_json
        account_hacienda = self.env['account.hacienda'].sudo()
        
        access_token = account_hacienda._get_token( self )

        if not access_token:
            msg = "Hacienda Access Token Indefinido"
            _logging.info( "==> " + msg )
            
            raise ValidationError( _( msg ) )
        
        hacienda_post_result = account_hacienda.hacienda_post_json( self )
        if hacienda_post_result == True:
            _logging.info("==> POST a HACIENDA Finalizado para: {0}".format( self.name ))
            return
        elif hacienda_post_result:
            raise ValidationError( _( str(hacienda_post_result) ))

        
    def action_post(self):
        _logging.info("  ==> Action Post Record ID: %s", self)
        
        res = super(AccountMove,self)
        
        if self.company_id.country_id.code != "CR":
            _logging.info("    Company not from Costa Rica")
            return res.action_post()
        
        if self.name and len(self.name) >= 6:
            _logging.info("    Ya tiene un numero consecutivo asignado")
            return res.action_post()
        
        next_number = sequence_prefix = sequence_number = False

        sequence_data = self._get_sequence_data()
        if sequence_data:
            self.name = sequence_data.get('next_number')

            self.sequence_prefix = sequence_data.get('sequence_prefix')
            self.sequence_number = sequence_data.get('sequence_number')
            self.state = "posted"
        else:
            return res.action_post()

    def _get_sequence_data(self):
        if self._name != "account.move":
            _logging.info("    ==> Get Sequence Data MODEL: {0} is not model 'account.move".format( self._name) )
            return
        if self.move_type == "out_refund":
            _logging.info("    ==> Get Sequence Data no aplica para Tipo Nota de Crédito")
            return False
        
        next_number = sequence_prefix = sequence_number = False
        if  self.move_type == "out_invoice" \
        and self.move_type_extra in [ False,"fe"] \
        and self.journal_id.sequence_fe:
            next_number = self.journal_id.sequence_fe.next_by_id()
            sequence_prefix = self.journal_id.sequence_fe.prefix
            sequence_number = self.journal_id.sequence_fe.number_next_actual
            self.move_type_extra = 'fe'
            
        elif self.move_type == "out_invoice" \
        and  self.journal_id.sequence_nd \
        and  self.move_type_extra == "nd":
            next_number = self.journal_id.sequence_nd.next_by_id()
            sequence_prefix = self.journal_id.sequence_nd.prefix
            sequence_number = self.journal_id.sequence_nd.number_next_actual
            
        elif self.move_type == "out_invoice" \
        and  self.journal_id.sequence_te \
        and self.move_type_extra == "te":
            next_number = self.journal_id.sequence_te.next_by_id()
            sequence_prefix = self.journal_id.sequence_te.prefix
            sequence_number = self.journal_id.sequence_te.number_next_actual
        
        elif self.move_type == "in_invoice" \
        and  self.journal_id.sequence_fec \
        and  self.move_type_extra == "fec":
            next_number = self.journal_id.sequence_fec.next_by_id()
            sequence_prefix = self.journal_id.sequence_fec.prefix
            sequence_number = self.journal_id.sequence_fec.number_next_actual
            
        elif self.move_type == "out_invoice" \
        and self.journal_id.sequence_fee \
        and self.move_type_extra == "fee":
            next_number = self.journal_id.sequence_fee.next_by_id()
            sequence_prefix = self.journal_id.sequence_fee.prefix
            sequence_number = self.journal_id.sequence_fee.number_next_actual

        _logging.info("DEF490 self: %s", self)
        _logging.info("DEF491 self.next_number: %s", next_number)
        _logging.info("DEF492 self.move_type: %s", self.move_type)
        _logging.info("DEF493 self.move_type_extra: %s", self.move_type_extra)
        _logging.info("DEF494 self.reversed_entry_id: %s", self.reversed_entry_id)
            
        if next_number == False:
            msg = "Error Tipo de Documento: Secuencia Indefinida en el Diario"
            raise ValidationError( _( msg ) )

        return {
            'next_number': next_number,
            'sequence_prefix': sequence_prefix,
            'sequence_number': sequence_number,
        }

    @api.model_create_multi
    def create(self, vals_list):
        _logging.info("    DEF513 CREATE")
        _logging.info("    DEF514 self._context: {0}".format( self._context ) )
        _logging.info("    DEF515 vals_list: {0}".format( vals_list ) )
        _logging.info("    ==================516============" )
        res = super(AccountMove,self)
        
        move_type_extra_options = ['fe', 'nd', 'fee']

        try:
            reversed_entry_int = vals_list[0].get('reversed_entry_id')
            reversed_entry_id = self.env['account.move'].search([('id','=', reversed_entry_int)])
            if reversed_entry_id.move_type_extra in move_type_extra_options:
                vals_list[0]['move_type_extra'] = 'nc'
        except:
            reversed_entry_int = False
            pass

        if self.env['account.move'].browse( reversed_entry_int ):
            
            razon = vals_list[0].get('ref')
            invoiceref_line_id = self.get_invoiceref_info( reversed_entry_int, razon )
            _logging.info("    DEF534 invoiceref_line_id: {0}".format( invoiceref_line_id ) )
            if invoiceref_line_id:
                vals_list[0]['inforef_ids'] = [( 4, invoiceref_line_id.id )]

            
            '''
            STOP532
            reversed_entry_id = self.env['account.move'].browse( reversed_entry_int )
            _logging.info("    DEF531 reversed_entry_id: {0}".format( reversed_entry_id ) )
            _logging.info("    DEF531 reversed_entry_id: {0}".format( reversed_entry_id.name[8:10] ) )
            
            if reversed_entry_id.name[8:10] == "01":
                tipodoc = "01"
            elif reversed_entry_id.name[8:10] == "02":
                tipodoc = "02"
            elif reversed_entry_id.name[8:10] == "03":
                tipodoc = "03"
            elif reversed_entry_id.name[8:10] == "04":
                tipodoc = "04"
                
            invoiceref_line = self.env['account.move.inforef.line'].sudo()            
            invoiceref_line_id = invoiceref_line.create({
                'move_id': reversed_entry_int,
                'tipodoc': tipodoc,
                'numero': reversed_entry_id.fe_clave,
                'fecha_emision': reversed_entry_id.invoice_date,
                'razon': vals_list[0].get('ref'),
                'codigo': "01", # 01-Anula Documento de Referencia
            })
            _logging.info("DEF 539 invoiceref_line_id: {0}".format( invoiceref_line_id )  )
            
            vals_list[0]['inforef_ids'] = [( 4, invoiceref_line_id.id )]
            '''
            '''
            self.write({
                'inforef_ids': [( 4, invoiceref_line_id.id )]
            })
            '''
            
        return res.create(vals_list)
    
    def get_invoiceref_info(self, reversed_entry_int, razon):
        reversed_entry_id = self.env['account.move'].browse( reversed_entry_int )
        if reversed_entry_id.name[8:10] == "01":
            tipodoc = "01"
        elif reversed_entry_id.name[8:10] == "02":
            tipodoc = "02"
        elif reversed_entry_id.name[8:10] == "03":
            tipodoc = "03"
        elif reversed_entry_id.name[8:10] == "04":
            tipodoc = "04"
        elif reversed_entry_id.name[8:10] == "09": #FEE
            tipodoc = "12" # 12-Sustituye Factura Electronica Exportacion
        else:
            _logging.info("Documento de Reference no es: FE, ND, NC, TE, FEE")
            return False

        invoiceref_line = self.env['account.move.inforef.line'].sudo()            
        invoiceref_line_id = invoiceref_line.create({
            'move_id': reversed_entry_int,
            'tipodoc': tipodoc,
            'numero': reversed_entry_id.fe_clave,
            'fecha_emision': reversed_entry_id.invoice_date,
            'razon': razon,
            'codigo': "01", # 01-Anula Documento de Referencia
        })
        return invoiceref_line_id
    ''' 
    def action_invoice_sent(self):
        STOP514
        _logging.info("DEF_974 action_invoice_sent")
        res = super(AccountMove,self)
        
        if self.move_type_extra == False:
            return res.action_invoice_sent()
        
        
        template_id = self.env.ref('account.email_template_edi_invoice').id
        template = self.env['mail.template'].browse( template_id )
        
        attachment = self.env['ir.attachment']
        attachment_ids = []
        if self.fe_xml_sign:
            attachment_id = attachment.create({
                'name': self.fe_name_xml_sign,
                'datas': self.fe_xml_sign,
                'type': 'binary',
            })
            attachment_ids.append( attachment_id.id )
            
        if self.fe_xml_hacienda:
            attachment_id = attachment.create({
                'name': self.fe_name_xml_hacienda,
                'datas': self.fe_xml_hacienda,
                'type': 'binary',
            })
            attachment_ids.append( attachment_id.id )
            
        template.attachment_ids = attachment_ids
        template.send_mail(self.id)
        
        return
    '''    
    def get_account_move_data(self, account_move_id_int):
        filter_records = [['id','=', self.id]]
        get_keys = ['name', 'invoice_date','partner_id', 'company_id', 'invoice_payment_term_id',  
                'fiscal_position_id', 'payment_reference', 'invoice_line_ids',
                'move_type', 'currency_id', 'amount_untaxed', 'amount_tax', 'amount_total',
                'narration', 'fe_activity_code_id', 'fe_payment_type', 'fe_receipt_status',
                'line_ids',
               ]
        output = self.env['account.move'].sudo().search_read(
            filter_records,
            get_keys
        )
        if output: return output
        else: return False
    
    def get_account_move_lines_data(self, account_move_id_int):
        get_keys = ['id' ,'sequence', 'name', 'quantity', 'product_id',
                'price_unit', 'discount',
                'price_subtotal', 'price_total', 'product_uom_id', 'tax_ids',
                'move_id', 'display_type', 'tax_base_amount'
                #'tax_fiscal_country_id', 
               ]
        output = self.env['account.move.line'].sudo().search_read(
            [   ( 'move_id.id', '=', account_move_id_int ),
                ('exclude_from_invoice_tab', '=', False),
            ],
            get_keys,
        )
        if output: return output
        else: return False

    def get_res_partner_data(self, res_partner_int ):
        
        get_keys = ['id' , 'name', 'vat', 'phone', 'street', 'street2','country_id', 'state_id',
                        'canton_id', 'distrito_id', 'barrio_id', 'fe_identification_type', 'email',
                   ]
        output = self.env['res.partner'].search_read(
            [ ( 'id', '=',  res_partner_int )  ],
            get_keys
        )
        
        if output: return output
        else: return False
        
    def get_product_product_data_lst(self, account_move_lines_json ):
        product_product_lst = []
        #QUITAR ESTO, SOLO PARA EFECTOS DE LA PRUEBA

        #_logging.info("DEF1055 account_move_line_json: {0}".format(account_move_lines_json))
        for account_move_line in account_move_lines_json:
            
            product_product_tuple = account_move_line.get('product_id')
            if not product_product_tuple:
                _logging.info("DEF1130 No product found in line")
                continue
            #_logging.info("DEF1059 product_product_tuple: {0}".format(product_product_tuple))

            try:
                value = [element for element in product_product_lst if element['id'] == product_product_tuple[0]]
                if len(value) > 0:
                    _logging.info("DEF1063 FOUNDED PRODUCT in LST NOT ADDED, THEN CONTINUE")
                    continue
            except:
                pass

            get_keys = [    'id', 'name', 'type', 'lst_price', 'default_code', 'taxes_id',
                            'cabys_code_id', 'fe_codigo_comercial_tipo', 'fe_codigo_comercial_codigo',
                            'fe_unidad_medida_comercial',
                           ]
            output_lst = self.env['product.product'].search_read(
                [ ( 'id', '=', product_product_tuple[0] )  ],
                get_keys,
            )
            product_product_lst.append( output_lst[0] )

        if len(product_product_lst) > 0:
            return product_product_lst
        else:
            return False

    def get_account_tax_lst(self, tax_ids_int):
        get_keys = ['id', 'name', 'type_tax_use', 'amount_type', 'amount',
                    'description', 'type', 'codigo_impuesto', 'tarifa_impuesto',
                    'tipo_documento', 'company_id',
                   ]
        output_lst = self.env['account.tax'].search_read(
            [ ( 'id', 'in', tax_ids_int )  ],
            get_keys,
        )
        
        if len( output_lst ) > 0:
            return output_lst
        else:
            return False

    def get_res_company_data( self, res_company_int ):
        get_keys = ['id' , 'name', 'vat', 'company_registry', 'state_id', 'canton_id',
                        'distrito_id', 'barrio_id', 'phone','fe_identification_type',
                        'country_id', 'email', 'street', 'street2',
                       ]
        output_lst = self.env['res.company'].search_read(
            [ ( 'id', '=', res_company_int )  ],
            get_keys
        )
        if output_lst:
            return output_lst
        else:
            return False
        

    def get_state_data(self, res_partner_int_lst ):
        res_partners_id = self.env['res.partner'].sudo().browse( res_partner_int_lst )
        state_ids = res_partners_id.state_id.ids
        get_keys = ['id' , 'code', 'fe_code', 'name' ]
        output_lst = self.env['res.country.state'].search_read(
            [ ( 'id', 'in',  state_ids  )  ],
            get_keys,
        )
        if len(output_lst) > 0:
            return output_lst
        else:
            return False

    def get_canton_data(self, res_partner_int_lst ):
        res_partners_id = self.env['res.partner'].sudo().browse( res_partner_int_lst )
        canton_ids = res_partners_id.canton_id.ids
        get_keys = ['id' , 'code', 'name']
        output_lst = self.env['res.country.canton'].search_read(
            [ ( 'id', 'in',  canton_ids  )  ],
            get_keys,
        )
        if len(output_lst) > 0:
            return output_lst
        else:
            return False
        
    def get_distrito_data(self, res_partner_int_lst ):
        res_partners_id = self.env['res.partner'].sudo().browse( res_partner_int_lst )
        distrito_ids = res_partners_id.distrito_id.ids
        get_keys = ['id' , 'code', 'name']
        output_lst = self.env['res.country.distrito'].search_read(
            [ ( 'id', 'in',  distrito_ids  )  ],
            get_keys,
        )
        if len(output_lst) > 0:
            return output_lst
        else:
            return False

    def get_barrio_data(self, res_partner_int_lst ):
        res_partners_id = self.env['res.partner'].sudo().browse( res_partner_int_lst )
        barrio_ids = res_partners_id.barrio_id.ids
        get_keys = ['id' , 'code', 'name']
        output_lst = self.env['res.country.barrio'].search_read(
            [ ( 'id', 'in',  barrio_ids  )  ],
            get_keys,
        )
        if len(output_lst) > 0:
            return output_lst
        else:
            return False

    def get_otros_ids(self, account_move_id_int):
        #otros_ids = self.env['account.move.otros.line'].sudo().browse( account_move_id_int )
        get_keys = ['id','field_type' , 'attributes_data', 'field_data', 'move_id']
        output_lst = self.env['account.move.otros.line'].search_read(
            [ ( 'move_id', 'in',  [ account_move_id_int ]  )  ],
            get_keys,
        )
        if len(output_lst) > 0:
            return output_lst
        else:
            return False

    def get_informacion_referencia(self, account_move_id_int):
        get_keys = ['id','tipodoc' , 'numero', 'fecha_emision', 'codigo', 'razon', 'move_id']
        output_lst = self.env['account.move.inforef.line'].search_read(
            [ ( 'move_id', 'in',  [ account_move_id_int ]  )  ],
            get_keys,
        )
        if len(output_lst) > 0:
            return output_lst
        else:
            return False
       
    def server_side_post(self, company_id_obj, account_move_data_json):
        _logging.info("  ==> server_side_post for: {0}".format( self.name ) )

        url1 = company_id_obj.fe_url_server
        if not url1:
            msg = { 'result':
                        {'errors': ['Compañía: no tiene configurado el servidor server-side'] }
                  }  
            return msg
        header = {'Content-Type':'application/json'}
        json_to_send = json.dumps(account_move_data_json, indent=4, sort_keys=True, default=str)
        try:
            response = requests.post(url1, headers = header, data = json_to_send)
        except:
            msg = "Error Conectando al Server Side: {0}".format( url1 )
            raise ValidationError( _(msg))
        return response
        XXXXXXXXXXXx
        xml_signed_text = response_obj.text
        _logging.info("DEB443 Response: %s %s", response_obj.status_code, xml_signed_text ) #es un string

        server_side_errors = json.loads( xml_signed_text ).get('result').get('errors')
        _logging.info("DEB455 server_side_errors: %s", server_side_errors)
        _logging.info("DEB455 LENGTH server_side_errors: %s", len(server_side_errors) )
        if len(server_side_errors) > 0:
            self.write({
                'fe_server_state': "Error"
            })
            
            errors_array = json.loads(response_obj.text ).get("result").get("errors")
            errors_txt = '<br>'.join( map(str, errors_array) )
            
            self.env['mail.message'].create({
                'res_id': self.id,
                'model':'account.move',
                'body': errors_txt,
            })
            return

    def get_fe_activity_code( self, fe_activity_code_int ):
        get_keys = ['id' , 'description', 'code']
        output_lst = self.env['activity.code'].search_read(
            [ ( 'id', 'in',  [ fe_activity_code_int ]  )  ],
            get_keys,
        )
        if len(output_lst) > 0:
            return output_lst
        else:
            return False
        
        
    def get_res_country_data( self, country_ids ):
        get_keys = ['id' , 'name','phone_code', 'currency_id']
        output_lst = self.env['res.country'].search_read(
            [ ( 'id', 'in',  country_ids  )  ],
            get_keys,
        )
        if len(output_lst) > 0:
            return output_lst
        else:
            return False
        
    def get_account_payment_term(  self, invoice_payment_term_int ):
        get_keys = ['id' , 'name', 'fe_condition_sale', 'note', 'line_ids']
        output_lst = self.env['account.payment.term'].search_read(
            [ ( 'id', 'in',  [invoice_payment_term_int]  )  ],
            get_keys,
        )
        if len(output_lst) > 0:
            return output_lst
        else:
            return False
        
    def get_account_payment_term_line(  self, invoice_payment_term_line_int ):
        get_keys = ['id' , 'payment_id','option', 'value', 'value_amount', 'days']
        output_lst = self.env['account.payment.term.line'].search_read(
            [ ( 'id', 'in',  invoice_payment_term_line_int  )  ],
            get_keys,
        )
        if len(output_lst) > 0:
            return output_lst
        else:
            return False
       
    def get_cabys_code( self, product_product_data_lst ):
        cabys_code_int_array = []
        for record in product_product_data_lst:
            cabys_code_id = record.get('cabys_code_id')
            if cabys_code_id:
                cabys_code_int_array.append( cabys_code_id[0] )
        if not cabys_code_int_array:
            return []

        get_keys = ['id' , 'code', 'name', 'tax']
        output_lst = self.env['cabys.code'].search_read(
            [ ( 'id', 'in',  cabys_code_int_array  )  ],
            get_keys,
        )
        if len(output_lst) > 0:
            return output_lst
        else:
            return False
       
    def get_uoms( self, account_move_lines_lst ):
        uoms_array = []
        
        for record in account_move_lines_lst:
            uom_id = record.get('product_uom_id')
            if uom_id:
                uoms_array.append( uom_id[0] )
        if not uoms_array:
            return []
        
        get_keys = ['id' , 'name', 'uom_mh']
        output_lst = self.env['uom.uom'].search_read(
            [ ( 'id', 'in',  uoms_array  )  ],
            get_keys,
        )
        if len(output_lst) > 0:
            return output_lst
        else:
            return False

    def get_account_fiscal_position( self, fiscal_position_int ):
        get_keys = [    'id' , 'name', 'tax_ids', 'fiscal_position_type', 'document_number',
                        'institution_name', 'issued_date',
                   ]
        output_lst = self.env['account.fiscal.position'].search_read(
            [ ( 'id', 'in',  [ fiscal_position_int ]  )  ],
            get_keys,
        )
        if len(output_lst) > 0:
            return output_lst
        else:
            return False
        
    def get_account_fiscal_position_line( self, fiscal_position_line_ids ):
        _logging.info("    DEF1450 fiscal_position_line_ids: {0}".format( fiscal_position_line_ids ) )
        get_keys = ['id' , 'tax_src_id', 'tax_dest_id', 'position_id']
        output_lst = self.env['account.fiscal.position.tax'].search_read(
            [ ( 'id', 'in',  fiscal_position_line_ids  )  ],
            get_keys,
        )
        if len(output_lst) > 0:
            return output_lst
        else:
            return False
        
    def write_to_chatter(self, model, res_id, body):
        self.env['mail.message'].create({
            'res_id': res_id,
            'model': model,
            'body': body,
        })
        return
        
