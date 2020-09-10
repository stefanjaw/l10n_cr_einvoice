# -*- coding: utf-8 -*-
from odoo import models, fields, api

import logging

log = logging.getLogger(__name__)

class ResCompany(models.Model):
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

    fe_identification_type = fields.Selection(related="partner_id.fe_identification_type", store=True )
    fe_comercial_name = fields.Char(related="partner_id.fe_comercial_name",store=True)
    fe_fax_number = fields.Char(related="partner_id.fe_fax_number",store=True)

    canton_id = fields.Many2one(related="partner_id.canton_id",store=True)
    distrito_id = fields.Many2one(related="partner_id.distrito_id",store=True)
    barrio_id = fields.Many2one(related="partner_id.barrio_id",store=True)

    fe_activity_code_ids = fields.One2many(
        string="Codigo de actividades economicas",
        comodel_name="activity.code",
        inverse_name="company_id",
    )
    fe_url_server = fields.Char(string="Url del server para facturar",default='http://localhost/api/v1/billing/')
    fe_current_country_company_code = fields.Char(string="Codigo pais de la compañia actual",compute="_get_country_code")

    