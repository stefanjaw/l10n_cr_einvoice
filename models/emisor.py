
# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging

log = logging.getLogger(__name__)

class Emisor(models.Model):
    _inherit = "res.company"

    log.info('--> Class Emisor')
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
            if s.email:
                if not re.match(pattern, s.email):
                    raise ValidationError("El correo electronico no tiene un formato valido")
    @api.multi
    @api.constrains("fe_url_server")
    def _check_fe_url_server(self):
        log.info('--> _check_fe_url_server')
        for s in self:
            if not s.fe_url_server[int(len(s.fe_url_server)-1):int(len( s.fe_url_server))] == "/" :
                raise ValidationError("El Server URL debe de terminar con un slash /")


    @api.multi
    @api.constrains("phone","fe_fax_number")
    def _check_phone_fe_fax_number(self):
        log.info('--> _check_phone_fe_fax_number')
        pattern = r"^[0-9]{1,20}$"
        for s in self:
            if s.phone :
                if not re.match(pattern,s.phone):
                    raise ValidationError("el campo telefono solo debe de contener numeros y Maximo de 20 digitos")
            #else:
            #        raise ValidationError("el campo telefono es requerido")

            if s.fe_fax_number :
                if not re.match(pattern,s.fe_fax_number):
                    raise ValidationError("el campo Fax solo debe de contener numeros y Maximo de 20 digitos")

    @api.multi
    @api.constrains("fe_code")
    def _check_fe_code(self):
        log.info('--> _check_phone_fe_code')
        pattern = r"^[0-9]{3}$"
        for s in self:
            if s.fe_code :
                if not re.match(pattern,s.fe_code):
                    raise ValidationError("el codigo de la compañia debe estar formado por 3 digitos!!")
