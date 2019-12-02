
# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError
import re
import json
import requests
import logging

log = logging.getLogger(__name__)

class resCompany(models.Model):
    _inherit = "res.company"

    log.info('--> Class Emisor')
    fe_certificate = fields.Binary(string="Upload Certificate")
    fe_certificate_name = fields.Char(string="Certificate name")
    fe_password_certificate = fields.Char(string="Contraseña Certificado", )
    fe_user_name = fields.Char(string="Nombre usuario hacienda")
    fe_user_password = fields.Char(string="Contraseña hacienda", )

    vat = fields.Char(size = 12, required=False)
    name = fields.Char(size = 100, )
    email = fields.Char(size=160,required=False )

    fe_identification_type = fields.Selection(related="partner_id.fe_identification_type",store=True)
    fe_comercial_name = fields.Char(related="partner_id.fe_comercial_name")

    fe_canton_id = fields.Many2one(related="partner_id.fe_canton_id")
    fe_district_id = fields.Many2one(related="partner_id.fe_district_id")
    fe_neighborhood_id = fields.Many2one(related="partner_id.fe_neighborhood_id")
    fe_other_signs = fields.Text(related="partner_id.fe_other_signs")

    fe_fax_number = fields.Char(related="partner_id.fe_fax_number")

    fe_activity_code_ids = fields.One2many(
        string="Codigo de actividades economicas",
        comodel_name="activity.code",
        inverse_name="company_id",
    )
    fe_url_server = fields.Char(string="Url del server para facturar", )

    fe_current_country_company_code = fields.Char(string="Codigo pais de la compañia actual",compute="_get_country_code")

    @api.multi
    @api.depends('country_id')
    def _get_country_code(self):
        log.info('--> 1575319718')
        for s in self:
            s.fe_current_country_company_code = s.country_id.code

    @api.multi
    def update_credentials_server_side(self):
        log.info('--->1574963401')
        json_string = {
                          'token_user_password':self.fe_user_password,
                          'certificate_password':self.fe_password_certificate,
                          }
        json_to_send = json.dumps(json_string)
        url = self.fe_url_server+'credential/update/'+self.vat
        log.info('--->url %s',url)
        header = {'Content-Type':'application/json'}
        response = requests.post(url, headers = header, data = json_to_send)
        log.info('--->response %s',response.text)
        json_response = json.loads(response.text)

        if "result" in json_response.keys():
            result = json_response['result']
            if "status" in result.keys():
                if result['status'] == "200":
                    log.info('====== Exito \n')
                    raise ValidationError("Actualizado con éxito")

            elif "validation" in  result.keys():
                result = json_response['result']['validation']
                raise ValidationError(result)


    @api.onchange("country_id")
    def _onchange_field(self):
        log.info('--> _onchange_field')
        vals={}
        if not self.country_id.code == "CR":
            vals = {'value':{
                            'fe_identification_type':None,
                            'fe_comercial_name':None,
                            'fe_canton_id':None,
                            'fe_district_id':None,
                            'fe_neighborhood_id':None,
                            'fe_other_signs':None,
                            'fe_fax_number':None,
                            'fe_code':None,
                            }
                   }
        return vals



    @api.multi
    @api.constrains("email")
    def _check_email(self):
        log.info('--> _check_email')
        pattern = r"\s*\w+([-+.']\w+)*@\w+([-.]\w+)*\.\w+([-.]\w+)*\s*"
        for s in self:
            if s.country_id.code == 'CR':
                if s.email:
                    if not re.match(pattern, s.email):
                        raise ValidationError("El correo electronico no tiene un formato valido")
    @api.multi
    @api.constrains("fe_url_server")
    def _check_fe_url_server(self):
        log.info('--> _check_fe_url_server')
        for s in self:
            if s.country_id.code == 'CR':
                if not s.fe_url_server[int(len(s.fe_url_server)-1):int(len( s.fe_url_server))] == "/" :
                    raise ValidationError("El Server URL debe de terminar con un slash /")
                    
    
    @api.multi
    @api.constrains("country_id")
    def _check_country_id(self):
        log.info('--> _check_country')
        for s in self:
            log.info('--->country %s %s',s.country_id, s.country_id.code)
            if not s.country_id:
                raise ValidationError("Seleccione el país de la compañia")


    '''@api.multi
    @api.constrains("phone","fe_fax_number")
    def _check_phone_fe_fax_number(self):
        log.info('--> _check_phone_fe_fax_number')
        pattern = r"^[0-9]{1,20}$"
        for s in self:
            if s.phone :
                if not re.match(pattern,s.phone):
                    raise ValidationError("el campo telefono solo debe de contener numeros y Maximo de 20 digitos")


            if s.fe_fax_number :
                if not re.match(pattern,s.fe_fax_number):
                    raise ValidationError("el campo Fax solo debe de contener numeros y Maximo de 20 digitos")'''
