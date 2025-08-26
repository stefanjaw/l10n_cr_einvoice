# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError
import logging
import re

log = logging.getLogger(__name__)

class ResPartner(models.Model):
    _inherit = "res.partner"
    
    log.info('--> Class Receptor')
    
    fe_comercial_name = fields.Char(string="Nombre Comercial",size = 80 )

    fe_identification_type = fields.Selection(
         string="Tipo Identificacion",
         selection=[
                 ('01','Cédula Física'),
                 ('02','Cédula Jurídica'),
                 ('03','DIMEX'),
                 ('04','NITE'),
                 ('05','Extranjero No Domiciliado'),
                 ('06','No Contribuyente')
         ],
    )
    #IdentificacionExtranjero
    fe_receptor_identificacion_extranjero = fields.Char(string="Identificacion Extranjero", size = 20)
    
    fe_other_signs = fields.Text(string="Otras Señas", size = 250 )

    fe_receptor_otras_senas_extranjero = fields.Text(string="Otras Señas Extranjero", size = 300 )
    #debajo movil
    fe_fax_number = fields.Char(string="Fax",size = 20 )
    fe_current_country_company_code = fields.Char(string="Codigo pais de la compañia actual",compute="_get_country_code")
    
    @api.constrains('email')
    def _constrains_email(self):
        if self.email:
             if not re.match(r'^(\s?[^\s,]+@[^\s,]+\.[^\s,]+\s?,)*(\s?[^\s,]+@[^\s,]+\.[^\s,]+)$', self.email.lower()):
                 raise ValidationError('El email no tiene un formato valido.')
    
    @api.constrains('vat')
    def _constrains_vat(self):
        for record in self:
            if record.vat:
                if not re.search('^\d+$',record.vat):
                    log.info("Skipped letter and numbers TBD development =====")
                    # raise ValidationError('La identificación solo debe de contener números1')
                else:
                    if record.fe_identification_type == '01':
                        if len(record.vat) != 9:
                            raise ValidationError('La identificación de tipo "Física" debe contener 9 digitos')
                    elif record.fe_identification_type == '02':
                        if len(record.vat) != 10:
                            raise ValidationError('La identificación de tipo "Jurídico" debe contener 10 digitos')
                    elif record.fe_identification_type == '03':
                        if len(record.vat) != 11 and len(record.vat) != 12:
                            raise ValidationError('La identificación de tipo "DIMEX" debe contener 11 ó 12 digitos')
                    elif record.fe_identification_type == '04':
                        if len(record.vat) != 10:
                            raise ValidationError('La identificación de tipo "NITE" debe contener 10 digitos')
            #else:
            #    raise ValidationError('La identificación es requerida')
