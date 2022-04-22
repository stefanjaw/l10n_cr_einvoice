from odoo import models, fields, api
from odoo.exceptions import ValidationError
import re
import json
import requests
import logging

log = logging.getLogger(__name__)

class ResPartnerFunctions(models.Model):
    _inherit = "res.partner"
    
    @api.depends('company_id')
    def _get_country_code(self):
        log.info('--> 1575319718')
        for s in self:
            s.fe_current_country_company_code = s.country_id.code
            log.info('--> codigo %s',s.fe_current_country_company_code)
            #raise ValidationError(s.fe_current_country_company_code)

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

            try:
                response = requests.get(url, headers = header)
            except:
                response = False
                log.info("  ==> SIN RESPUESTA DE API DE HACIENDA")
                return

            try:
                json_response = json.loads(response.text)
            except:
                log.info("  ==> SIN RESPUESTA DE API DE HACIENDA")
                json_response = False
                return
                
            if json_response.get("code") == 404:
                return
            if "nombre" in json_response.keys():
                return self.update({"name": json_response["nombre"],"fe_identification_type":json_response["tipoIdentificacion"]} )
