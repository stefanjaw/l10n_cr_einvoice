# -*- coding: utf-8 -*-
 
from odoo import models, fields, api
import base64

import requests
import json

from urllib.parse import quote

import logging
import datetime

_logging = logging.getLogger(__name__)

class AccountHacienda(models.Model):
    _name = "account.hacienda"
    _description = "account.hacienda"

    def _get_token( self, record ):
        _logging.info("  ==> Get Access Token")
        access_token_data = record.company_id.fe_hacienda_token

        u_name = record.company_id.fe_user_name
        pwd = record.company_id.fe_user_password
        
        if access_token_data:
            _logging.info("    ACCESS TOKEN FOUND")
            access_token_data_json = json.loads(access_token_data)
            access_token_jwt = access_token_data_json.get("access_token")
            access_token_jwt_payload = access_token_jwt.split(".")[1] + "=="
            access_token_jwt_payload_json = json.loads(
                    base64.b64decode( access_token_jwt_payload ).decode('utf-8')
                )
            access_token_expire_time = access_token_jwt_payload_json.get('exp')
            timestamp_now = int( datetime.datetime.now().timestamp() )
            if int(access_token_expire_time - 10 ) > timestamp_now:
                _logging.info("    ACCESS TOKEN NOT EXPIRED")
                return access_token_jwt

        _logging.info("    ACCESS TOKEN Expired, REQUEST IN PROGESS!!")
        errors = []

        if u_name == False:
            errors.append("Hacienda Username Indefinido")
        if pwd == False:
            errors.append("Hacienda Password Indefinido")
        
        if len(errors) > 0:
            _logging.info("ERRORS %s", errors)
            record.write({
                'fe_server_state': "Errors"
            })
            errors_txt = '<br>'.join( map(str, errors ) )
            record.env['mail.message'].create({
                'res_id': record.id,
                'model':  record._name,
                'body':   errors_txt,
            })
            return False

        hacienda_ambiente = record.company_id.fe_hacienda_ambiente
        _logging.info("  ==> Hacienda Token Ambiente: {0}".format( hacienda_ambiente ))
        if not hacienda_ambiente:
            oauth_url = False
        elif hacienda_ambiente == "production":
            oauth_url = "https://idp.comprobanteselectronicos.go.cr/auth/realms/rut/protocol/openid-connect/token"
        elif hacienda_ambiente == "staging":
            oauth_url = "https://idp.comprobanteselectronicos.go.cr/auth/realms/rut-stag/protocol/openid-connect/token"

        if not oauth_url:
            record.write({
                'fe_server_state': "Error",
            })
            record.env['mail.message'].create({
                'res_id': record.id,
                'model':'account.move',
                'body': "Ambiente de Hacienda Producción o Staging, no seleccionado en la compañía",
            })
            return False
        payload = "grant_type=password&client_id={0}&username={1}&password={2}".format(
                      "api-stag",
                      quote(u_name),
                      quote(pwd),
                  )

        headers = {
            'Content-Type': "application/x-www-form-urlencoded",
            'Cache-Control': "no-cache"
        }

        response = requests.request(
                "POST", oauth_url, data=payload, headers=headers)

        response_json_full = {
            "headers": response.headers,
            "text": response.text,
            "status_code": response.status_code,
            "reason": response.reason,
        }

        if response.text:
            record.company_id.write({
                'fe_hacienda_token': response.text
            })

        access_token_json = json.loads(response.text)
        access_token_jwt = access_token_json.get("access_token")
        return access_token_jwt
    
    def hacienda_post_json(self, record):
        
        hacienda_ambiente = record.company_id.fe_hacienda_ambiente
        access_token_jwt = record.company_id.fe_hacienda_token
        hacienda_json = record.fe_tohacienda_json
        
        _logging.info("  ==> Hacienda POST Ambiente: {0}".format( hacienda_ambiente ))

        if not hacienda_ambiente:
            hacienda_url = False
        elif hacienda_ambiente == "production":
            hacienda_url = "https://api.comprobanteselectronicos.go.cr/recepcion/v1/recepcion"
        elif hacienda_ambiente == "staging":
            hacienda_url = "https://api.comprobanteselectronicos.go.cr/recepcion-sandbox/v1/recepcion"

        if not hacienda_url:
            record.write({
                'fe_server_state': "Error",
            })
            record.env['mail.message'].create({
                'res_id': record.id,
                'model':'account.move',
                'body': "Ambiente de Hacienda Producción o Staging, no seleccionado en la compañía",
            })
            return False

        errors = []

        if not hacienda_json or hacienda_json == False:
            msg = "JSON no generado para enviarlo a Hacienda"
            errors.append( msg )
            
        if len(errors) > 0:
            return errors
        
        try:
            access_token_jwt_json = json.loads( access_token_jwt )
            access_token = access_token_jwt_json.get('access_token')
        except:
            access_token = False
        
        authorization = "bearer " + access_token

        headers = {
            'Content-Type': "application/json",
            'Authorization': authorization,
        }
        
        try:
            hacienda_json = json.loads( hacienda_json )
            hacienda_json = json.dumps(hacienda_json)
        except:
            hacienda_json = json.loads( hacienda_json.replace("'", '"') )
            hacienda_json = json.dumps(hacienda_json)
        
        response = requests.post( hacienda_url, headers = headers, data = hacienda_json )
        
        response_json_full = {
            'headers': dict( response.headers ),
            'text': response.text,
            'status_code': response.status_code,
            'reason': response.reason
        }

        record.write({
            'fe_server_state': 'Enviado',
            'fe_fromhacienda_json': json.dumps(response_json_full),
        })
        
        return True
        

    def get_contact_data_json(self, record ):
        _logging.info("  get_contact_data_json=========")
        _logging.info("      Get contact record: %s", record.name  )
        
        contact_keys = ['id' , 'name', 'vat', 'state_id', 'canton_id',
                        'distrito_id', 'barrio_id', 'phone','fe_identification_type',
                        'country_id', 'email', 'street',
                       ]
        contact_data = record.search_read(
            [ ( 'id', '=', record.id )  ],
            contact_keys
        )
        #_logging.info("DEB170 contact_data: %s", contact_data)

        #Try the company_registry if it ss a company
        keys = ['company_registry']
        try:
            output = record.search_read(
                [ ( 'id', '=', record.id )  ],
                keys,
            )
            output[0].pop("id")
            contact_data[0].update( output[0] )
        except:
            msg = "      Not Found Keys: " + ", ".join(keys)
            output = []
            _logging.info( msg )

        #_logging.info("DEB187 contact_data: %s", contact_data)

        #Set the Company State Code
        try:
            state_tuple = contact_data[0]['state_id']
            #_logging.info("  DEBDDa state_tuple: %s", state_tuple)
            state_keys = ['id' , 'code', 'fe_code' ]
            state_data = record.state_id.search_read(
                [ ( 'id', '=', state_tuple[0] )  ],
                state_keys
            )
            #_logging.info("  DEBF state_data: %s", state_data )
            contact_data[0]['state_id'] = state_data
        except:
            msg = "      Contact: State not Defined"
            _logging.info(msg)
        
        try: #Set the Company Canton Code
            canton_tuple = contact_data[0]['canton_id']
            #_logging.info("  DEBGa canton_tuple: %s", canton_tuple)
            canton_keys = ['id' , 'code', 'name']
            canton_data = record.canton_id.search_read(
                [ ( 'id', '=', canton_tuple[0] )  ],
                canton_keys
            )
            #_logging.info("   DEBGb state_data: %s", canton_data )
            contact_data[0]['canton_id'] = canton_data

        except:
            msg = "      Contact: Canton not Defined"
            _logging.info(msg)
            
        try: #Set the Company Distrito Code
            distrito_tuple = contact_data[0]['distrito_id']
            #_logging.info("   DEBHa distrito_tuple: %s", distrito_tuple)
            distrito_keys = ['id' , 'code', 'name']
            distrito_data = record.distrito_id.search_read(
                [ ( 'id', '=', distrito_tuple[0] )  ],
                distrito_keys
            )
            #_logging.info("   DEBHb distrito_data: %s", distrito_data )
            contact_data[0]['distrito_id'] = distrito_data

        except:
            msg = "      Contact: Distrito not Defined"
            _logging.info( msg )

        try:  #Set the Contact Barrio Code
            barrio_tuple = contact_data[0]['barrio_id']
            #_logging.info("   DEBIa barrio_tuple: %s", barrio_tuple)
            barrio_keys = ['id' , 'code', 'name']
            barrio_data = record.barrio_id.search_read(
                [ ( 'id', '=', barrio_tuple[0] )  ],
                barrio_keys
            )
            #_logging.info("   DEBIb barrio_data: %s", barrio_data )
            contact_data[0]['barrio_id'] = barrio_data

        except:
            msg = "      Contact: Barrio Not Defined"
            _logging.info( msg )

        return contact_data[0]
        
            
    def account_move_create_json(self, record, partner_data ):
        _logging.info("   DEB233 account_move_create_json=========")
        
        account_move_data_json = {}

        consecutivo_format = True
        if record.fe_server_state != False:
            msg = "     Procesado anteriormente: " + str( record.name )
            _logging.info( msg)
            consecutivo_format = False
        elif len( str(record.name) ) != 20:
            msg = "     Warning: Largo de Consecutivo no cumple: " + str(record.name)
            _logging.info( msg )
            consecutivo_format = False

        if consecutivo_format == False:
            _logging.info("     Formato del consecutivo invalido, no se procesa")
            return []

        errors = []
        #Construyendo el JSON
        keys = ['name', 'invoice_date','partner_id', 'company_id', 'invoice_payment_term_id',  
                'fiscal_position_id', 'payment_reference', 'invoice_line_ids',
                'move_type', 'currency_id', 'amount_untaxed', 'amount_tax', 'amount_total',
                'narration', 'fe_activity_code_id', 'fe_payment_type', 'fe_receipt_status',
                #'line_ids', 
               ]
        invoice_data = record.search_read([ ('id','=', record.id) ], keys)
        
        try:
            if str(invoice_data[0]['partner_id'][0]) == str( partner_data.get('id') ):
                invoice_data[0]['partner_id'] = partner_data
        except:
            _logging.info("  Error: Partner ID not matching")
        
        try: #Activity Code Data
            activity_code_tuple = invoice_data[0]['fe_activity_code_id']
            _logging.info("EDB102 =====DATA: %s", activity_code_tuple )
            activity_code_keys = ['code','description']
            activity_code_data = self.env['activity.code'].search_read(
                [ ( 'id', '=', activity_code_tuple[0] )  ],
                activity_code_keys
            )
            _logging.info("EDB108 =====DATA: %s", activity_code_data )
            if activity_code_data:
                invoice_data[0]['fe_activity_code_id'] = activity_code_data
        except:
            msg = "No Activity Code"
            
        try: #Payment Term
            payment_term_tuple = invoice_data[0]['invoice_payment_term_id']
            _logging.info("DEBDD payment_term_tuple: %s", payment_term_tuple)
            payment_term_keys = [ 'id', 'name', 'note', 'fe_condition_sale', 'line_ids',
                                ]
            payment_term_data = self.env['account.payment.term'].search_read(
                [ ( 'id', '=', payment_term_tuple[0] )  ],
                payment_term_keys
            )
            _logging.info("DEBGGG=====payment_term_data: %s", payment_term_data )
        except:
            msg = "No Payment Term"
        
        try: #Payment Term Lines
            payment_term_lines_tuple = payment_term_data[0]['line_ids']
            _logging.info("DEBDD payment_term_lines_tuple: %s", payment_term_lines_tuple)
            payment_term_lines_keys = ['id', 'value', 'value_amount', 'days', 'option']
            payment_term_lines_data = self.env['account.payment.term.line'].search_read(
                [ ( 'id', 'in', payment_term_lines_tuple )  ],
                payment_term_lines_keys
            )
            payment_term_data[0]['line_ids'] = payment_term_lines_data
            _logging.info("DEBGGB=====payment_term_data: %s", payment_term_data )
            #Adding Payment_TERM_DATA TO INVOICE_DATA
            invoice_data[0]['invoice_payment_term_id'] = payment_term_data
        except:
            msg = "No Payment Term Lines"
        
        #invoice_lines_data
        invoice_line_ids = invoice_data[0]['invoice_line_ids']
        invoice_lines_keys = ['id' ,'sequence', 'name', 'quantity', 'product_id',
                'price_unit', 'discount',
                'price_subtotal', 'price_total', 'product_uom_id', 'tax_ids', 
                #'tax_fiscal_country_id', 
               ]
        invoice_lines_data = self.env['account.move.line'].search_read(
            [ ( 'id', 'in', invoice_line_ids )  ],
            invoice_lines_keys
        )
        _logging.info("DEBF invoice lines DATA: %s", invoice_lines_data )
        
        for invoice_line in invoice_lines_data:
            _logging.info("DEBG invoice_line: %s", invoice_line)

            #TODALADATA
            query_id = invoice_line['id']
            query_keys = []
            query_data = self.env['account.move.line'].search_read(
                [ ( 'id', '=', query_id )  ],
                query_keys,
            )
            _logging.info("DEBHA query_data DATA: %s", query_data )

            
            try: #Adding product_id
                product_tuple = invoice_line['product_id']
                product_keys = [ 'id', 'name', 'type', 'lst_price', 'default_code', 'taxes_id',
                                 'cabys_code_id',
                               ]
                product_data = self.env['product.product'].search_read(
                    [ ( 'id', '=', product_tuple[0] )  ],
                    product_keys,
                )
                _logging.info("DEBHB product_uom_data DATA: %s", product_data )
                invoice_line['product_id'] = product_data
            except:
                msg="Product ID not defined or manual"

            try: #Add the Cabys Code Information
                cabys_code_tuple = product_data[0]['cabys_code_id']
                cabys_code_keys = ['id', 'name', 'code']
                cabys_code_data = self.env['cabys.code'].search_read(
                    [ ( 'id', '=', cabys_code_tuple[0] )  ],
                    cabys_code_keys,
                )
                product_data[0]['cabys_code_id'] = cabys_code_data
                invoice_line['product_id'] = product_data
            except:
                msg = "no cabys code"
              
            try: #Add the Tax configured in the Product
                product_tax_list = product_data[0]['taxes_id']
                product_tax_keys = ['id', 'name', 'type_tax_use', 'amount_type', 'amount', 'description']
                product_taxes_data = self.env['account.tax'].search_read(
                    [ ( 'id', 'in', product_tax_list )  ],
                    product_tax_keys,
                )
                _logging.info("DEBI product taxes_data DATA: %s", product_taxes_data )
                product_data[0]['taxes_id'] = product_taxes_data
            except:
                msg = "No Tax Defined"
            
            try: #Adding product_uom to invoice_lines_data
                product_uom_tuple = invoice_line['product_uom_id']
                product_uom_keys = ['id','name', 'uom_mh']
                product_uom_data = self.env['uom.uom'].search_read(
                    [ ( 'id', '=', product_uom_tuple[0] )  ],
                    product_uom_keys,
                )
                _logging.info("DEBHC product_uom_data DATA: %s", product_uom_data )
                invoice_line['product_uom_id'] = product_uom_data
            except:
                msg ="No Product UOM Defined"
            
            #Adding Tax ID SRC if there's a fiscal Position
            #Fiscal Position Tax Id Source
            fiscal_position_tuple = invoice_data[0].get('fiscal_position_id')

            if fiscal_position_tuple:
                #Buscar el taxid destination en Fiscal Position y encontrar el tax_src
                _logging.info("DEBIA fiscal_position_tuple: %s", fiscal_position_tuple )
                #1638224077
                fiscal_position_tax_ids_keys = [ 'id', 'tax_src_id', 'tax_dest_id' ]
                fiscal_position_tax_ids_data = self.env['account.fiscal.position.tax'].search_read(
                    [   ( 'position_id', '=', fiscal_position_tuple[0] ),
                        ( 'tax_dest_id', 'in',  invoice_line['tax_ids'] ),
                        ( 'tax_src_id', 'in',  product_tax_list ),
                     
                    ],
                    fiscal_position_tax_ids_keys
                )
                _logging.info("DEBGGCBA===== fiscal_position_tax_ids_data: %s", fiscal_position_tax_ids_data )
                #Add tax_src_id data
                #[{'id': 3, 'tax_src_id': (6, 'Sales Tax 13%'), 'tax_dest_id': (8, 'Sales Tax 1%')}]
                tax_src_tuple = fiscal_position_tax_ids_data[0].get('tax_src_id')
                tax_keys = ['id', 'name', 'type_tax_use', 'amount_type', 'amount', 'description']
                taxes_data = self.env['account.tax'].search_read(
                    [ ( 'id', '=', tax_src_tuple[0] )  ],
                    tax_keys,
                )
                _logging.info("DEBIbAA taxes_data DATA: %s", taxes_data )
                fiscal_position_tax_ids_data[0]['tax_src_id'] = taxes_data
                
                invoice_line['fiscal_position_tax_ids'] = fiscal_position_tax_ids_data
            

            #Adding Taxes Data to invoice_lines_data 'tax_ids': [3]
            tax_ids = invoice_line['tax_ids']
            _logging.info("DEBIa taxes_ids DATA: %s", tax_ids )
            
            tax_keys = ['id', 'name', 'type_tax_use', 'amount_type', 'amount',
                        'description', 'codigo_impuesto', 'tarifa_impuesto',
                        'tipo_documento', ]
            taxes_data = self.env['account.tax'].search_read(
                [ ( 'id', 'in', tax_ids )  ],
                tax_keys,
            )
            _logging.info("DEBIb taxes_data DATA: %s", taxes_data )
            invoice_line['tax_ids'] = taxes_data
            

        #Adding to invoice_data the invoice_lines_data
        invoice_data[0]['invoice_line_ids'] = invoice_lines_data
        
        invoice_data[0].update( {'errors': errors}  )
        _logging.info("DEB279 ENDED account_move_create_json ")
        return invoice_data

    def query_hacienda(self, record):
        _logging.info("==> Consultando Hacienda por documento: {0}".format( record.name ) )

        hacienda_ambiente = record.company_id.fe_hacienda_ambiente 
        _logging.info("DEF496 record: {0}".format( hacienda_ambiente ) )
        clave = record.fe_clave
        if hacienda_ambiente == "production":
            location_url = \
                "https://api.comprobanteselectronicos.go.cr/recepcion/v1/recepcion/{0}".format(
                    clave
                )
        elif hacienda_ambiente == "staging":
            location_url = \
                "https://api.comprobanteselectronicos.go.cr/recepcion-sandbox/v1/recepcion/{0}".format(
                    clave
                )
        else:
            location_url = False

        if not location_url:
            return False
        
        access_token = self._get_token( record )
        if not access_token:
            _logging.info("  ==> Hacienda access_token indefinido")
            return
        
        authorization = "bearer " + access_token

        headers = {
            'Content-Type': "application/json",
            'Authorization': authorization,
        }
        
        hacienda_json = {}
        

        response = requests.get( location_url, headers = headers, data = hacienda_json )

        response_text = response.text
        try:
            response_json = dict(response_text)
        except:
            response_json = json.loads( response_text )

        if response_json:
            record.write({
                'fe_fromhacienda_json': json.dumps( response_json ),
                'fe_xml_hacienda': response_json.get('respuesta-xml'),
                'fe_name_xml_hacienda': 'MH-' + str( response_json.get('clave') + '.xml' ),
                'fe_server_state': response_json.get('ind-estado'),
            })
        
        return
