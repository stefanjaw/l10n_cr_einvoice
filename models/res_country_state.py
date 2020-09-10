# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging

log = logging.getLogger(__name__)

class ResCountryState(models.Model):
    _inherit = "res.country.state"
    log.info('--> Class ResCountryState')
    fe_code = fields.Char(string="Codigo Provincia Para Facturacion", )
    