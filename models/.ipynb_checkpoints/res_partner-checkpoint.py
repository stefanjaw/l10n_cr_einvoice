# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError
import logging
import re

log = _logging = logging.getLogger(__name__)

class ResPartner(models.Model):
    _inherit = "res.partner"

    fe_comercial_name = fields.Char(string="Nombre Comercial",size = 80 )

    fe_identification_type = fields.Selection(
         string="Tipo Identificacion",
         selection=[
                 ('01', 'Cédula Física'),
                 ('02', 'Cédula Jurídica'),
                 ('03','DIMEX'),
                 ('04','NITE'),
                 ('05','Extranjero'),
         ],
    )

    fe_receptor_identificacion_extranjero = fields.Char(string="Identificacion Extranjero", size = 20)

    fe_other_signs = fields.Text(string="Otras Señas", size = 250 )

    fe_receptor_otras_senas_extranjero = fields.Text(string="Otras Señas Extranjero", size = 300 )

    fe_fax_number = fields.Char(string="Fax",size = 20 )
    fe_current_country_company_code = fields.Char(string="Codigo pais de la compañia actual",compute="_get_country_code")
    
    emails_extra_ids = fields.One2many('res.partner.emails_extra', 'partner_id',
        help="Enviar: Incluye el correo en C.C\nPrincipal: Incluye el correo como Principal" )
    
    def _payment_method_lst(self):
        return self.env['account.move']._fields['fe_payment_type'].selection
    
    fe_payment_type = fields.Selection(_payment_method_lst,'Método de Pago', translate=True)
    
    is_invoice_export_default = fields.Boolean('Factura Electrónica Exportación')
    has_fiscal_position = fields.Boolean('Contribuyente especial')
    
    fe_otros_ids = fields.One2many('res.partner.otros.line', 'partner_id',
        help="Otras Lineas para factura electrónica")
