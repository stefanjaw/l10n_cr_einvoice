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
                _logger.info(f"DEF54 act_codes: {self.fe_activity_code_ids.ids}")
                
                res_partner_activity_codes = self.action_activity_codes_build( response_json )
                _logger.info(f"DEF57 res_partner_activity_codes: \n{res_partner_activity_codes}\n")
                data = {
                            "name": response_json["nombre"].title(),
                            "fe_identification_type":response_json["tipoIdentificacion"],
                        }
                
                # if res_partner_activity_codes:
                #     # STOP64
                #     data.update({
                #         "fe_activity_code_ids": res_partner_activity_codes
                #     })
                _logger.info(f"DEF67 data: \n{data}")
                _logger.info(f"DEF68 self.id: {self.id} ===============")
                _logger.info(f"DEF69 self._origin.id: {self._origin.id} ===============")
                
                return self.update( data )

    def action_activity_codes_build(self, response_json):
        
        _logger.info(f"DEF74 fe_activity_code_ids: {self.fe_activity_code_ids}")


        
        activity_json_lst = response_json.get("actividades")
        if len( activity_json_lst ) == 0:
            return None
        
        res_partner_activity_codes = []
        for activity_json in activity_json_lst:
            code = activity_json['codigo']
            _logger.info(f"DEF81      code: {code}")
            partner_id = self.id

            data = {
                "active": True,
                "status": activity_json.get('estado'),
                "type": activity_json.get('tipo'),
                "code": code,
                "name": activity_json.get('descripcion'),
                "partner_id": partner_id
            }
            _logger.info(f"DEF93 data: \n{data}")
            records = self.env["res.partner.activity.codes"].search([
                ('code', '=', code ),
                ('partner_id', '=', self.id )
            ])
            _logger.info(f"DEF98      records: {records}")
            result = "No action done"
            if len( records ) == 0:
                # res_partner_activity_codes.append( (0,0, data )  )
                result = self.env["res.partner.activity.codes"].create(data)
                # _logger.info(f"DEF103 result: {result}")
                
            elif len( records ) == 1:
                result = records.write(data)
                # res_partner_activity_codes.append( (1,records.id, data )  )
            else:
                msg = f"To many records to update: {records}"
                raise ValidationError( msg )
            _logger.info(f"DEF112 result: {result}")
            
        return res_partner_activity_codes
        