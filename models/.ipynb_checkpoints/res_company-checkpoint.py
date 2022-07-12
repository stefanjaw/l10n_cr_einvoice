# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError
import logging

log = logging.getLogger(__name__)

class ResCompany(models.Model):
    _inherit = "res.company"

    fe_certificate = fields.Binary(string="Upload Certificate")
    fe_certificate_name = fields.Char(string="Certificate name")
    fe_password_certificate = fields.Char(string="Contraseña Certificado", )
    fe_user_name = fields.Char(string="Nombre usuario hacienda")
    fe_user_password = fields.Char(string="Contraseña hacienda", )
    fe_hacienda_token = fields.Text(string="Token de Hacienda")
    fe_hacienda_ambiente = fields.Selection([
        ('production', 'Producción'),
        ('staging', 'Pruebas'),
    ])
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
    fe_url_server = fields.Char(string="Avalantec Server Side URL")
    fe_current_country_company_code = fields.Char(string="Codigo pais de la compañia actual",compute="_get_country_code")
    
    fe_email = fields.Char(string="Email de Recepcion XMLs")
    fecth_server = fields.Many2one('fetchmail.server', string='Servidor Correo')
    default_account_for_invoice_email = fields.Many2one('account.account', string='Cuenta contable facturas por email',
    help="Esta cuenta sera asignada por default a las lineas de las facturas creadas automaticamente por email")

    @api.constrains('fecth_server')
    def _constrains_fecth_server(self):
        for record in self:
            company = record.env['res.company'].search([('fecth_server','=',record.fecth_server.id),('id','!=',record.id)])
            if company:
                raise ValidationError('El servidor de correo {} no se puede utilizar ya que se configuro en otra compañia'.format(record.fecth_server.name))

    
