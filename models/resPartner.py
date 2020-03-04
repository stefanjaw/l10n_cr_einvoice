
# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError
import re
import json
import requests
import logging

log = logging.getLogger(__name__)

class resPartner(models.Model):
    _inherit = "res.partner"

    log.info('--> Class Receptor')
    vat = fields.Char(size = 12, )
    name = fields.Char(size = 100, )


    fe_comercial_name = fields.Char(string="Nombre Comercial",size = 80 )

    fe_identification_type = fields.Selection(
         string="Tipo Identificacion",
         selection=[
                 ('01', 'Cédula Física'),
                 ('02', 'Cédula Jurídica'),
                 ('03','DIMEX'),
                 ('04','NITE')
         ],
    )
    #IdentificacionExtranjero
#    fe_foreign_identity = fields.Char(string="Identificacion Extranjero", size = 20)
    fe_receptor_identificacion_extranjero = fields.Char(string="Identificacion Extranjero", size = 20)

    fe_canton_id = fields.Many2one("client.canton", )
    fe_district_id = fields.Many2one("client.district", )
    fe_neighborhood_id = fields.Many2one("client.neighborhood",)

    fe_other_signs = fields.Text(string="Otras Señas", size = 250 )
    #fe_other_foreign_signs = fields.Text(string="Otras Señas Extranjero", size = 20 )
    fe_receptor_otras_senas_extranjero = fields.Text(string="Otras Señas Extranjero", size = 300 )
    #debajo movil
    fe_fax_number = fields.Char(string="Fax",size = 20 )

    fe_current_country_company_code = fields.Char(string="Codigo pais de la compañia actual",compute="_get_country_code")

    @api.multi
    @api.depends('company_id')
    def _get_country_code(self):
        log.info('--> 1575319718')
        for s in self:
            s.fe_current_country_company_code = s.company_id.country_id.code
            log.info('--> codigo %s',s.fe_current_country_company_code)

    @api.multi
    @api.constrains("email")
    def _check_field(self):
        log.info('--> _check_field REPETIDO1')
        pattern = r"\s*\w+([-+.']\w+)*@\w+([-.]\w+)*\.\w+([-.]\w+)*\s*"
        for s in self:
            if s.email:
                if not re.match(pattern, s.email):
                    raise ValidationError("El correo electronico no tiene un formato valido")
    
    @api.onchange('vat')
    def _onchange_(self):
        if self.vat:
            header = {'Content-Type':'application/json'}
            url = "https://api.hacienda.go.cr/fe/ae?identificacion={0}".format(self.vat)
            log.info(url)
            response = requests.get(url, headers = header)
 
            json_response = json.loads(response.text)
                
            if json_response.get("code") == 404:
                return
            return self.update({"name": json_response["nombre"],"fe_identification_type":json_response["tipoIdentificacion"]} )

              
    '''
    @api.multi
    @api.constrains("phone","fe_fax_number")
    def _check_field(self):
        log.info('--> check_field REPETIDO2')
        pattern = r"^[0-9]{1,20}$"
        for s in self:
            if s.phone :
                if not re.match(pattern,s.phone):
                    raise ValidationError("el campo telefono solo debe de contener numeros y un maximo de 20 digitos")
            if s.fe_fax_number :
                if not re.match(pattern,s.fe_fax_number):
                    raise ValidationError("el campo Fax solo debe de contener numeros")'''
