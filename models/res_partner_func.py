from odoo import models, fields, api
from odoo.exceptions import ValidationError
import re
import json
import requests
import logging

log = _logger = logging.getLogger(__name__)

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
    def action_partner_data_costa_rica_update(self):
        if self.vat:
            header = {'Content-Type':'application/json'}
            url = "https://api.hacienda.go.cr/fe/ae?identificacion={0}".format(self.vat)
            _logger.info(f"Querying {url[20:]}")
            
            try:
                response = requests.get(url, headers = header, timeout=5)
            except:
                response = False
                log.info("  ==> SIN RESPUESTA DE API DE HACIENDA")
                return

            try:
                response_json = json.loads(response.text)
            except:
                log.info("  ==> SIN RESPUESTA DE API DE HACIENDA")
                response_json = False
                return
                
            if response_json.get("code") == 404:
                return
            elif "nombre" in response_json.keys():
                _logger.info(f"Updating partner information ======")
                res_partner_activity_codes = self.action_activity_codes_build( response_json )
                data = {
                            "name": response_json["nombre"].title(),
                            "fe_identification_type":response_json["tipoIdentificacion"],
                        }
                
                if res_partner_activity_codes  \
                and len(res_partner_activity_codes) > 0:
                    data.update({
                        "fe_activity_code_ids": res_partner_activity_codes
                    })
                
                return self.update( data )

    def action_activity_codes_build(self, response_json):
        _logger.info(f"    Updating Activity Codes ======")
        activity_json_lst = response_json.get("actividades")
        if len( activity_json_lst ) == 0:
            return None
        
        partner_id = self
        partner_has_id = self._origin.id
        
        res_partner_activity_codes = []
        for activity_json in activity_json_lst:
            code = activity_json['codigo']
            
            data = {
                "active": True,
                "status": activity_json.get('estado'),
                "type": activity_json.get('tipo'),
                "code": code,
                "name": activity_json.get('descripcion'),
                "partner_id": partner_id.id
            }
            
            records = self.env["res.partner.activity.codes"].search([
                ('code', '=', code ),
                ('partner_id', '=', partner_id.id )
            ])
            
            result = "No Record Created"
            if len( records ) == 0:
                if partner_has_id:
                    result = self.env["res.partner.activity.codes"].create(data)
                    _logger.info(f"        Record Partner Activity Code {code} created: {result} ")
                else:
                    res_partner_activity_codes.append( (0,0, data )  )
            elif len( records ) == 1:
                if partner_has_id:
                    result = records.write(data)
                    _logger.info(f"        Record Partner Activity Code {code} updated result: {result} ")
                else:
                    res_partner_activity_codes.append( (1,records.id, data )  )
            else:
                msg = f"To many records to update: {records}"
                raise ValidationError( msg )
            
        return res_partner_activity_codes
        