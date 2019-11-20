# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging

log = logging.getLogger(__name__)

class Provincia(models.Model):
    _inherit = "res.country.state"
    fe_code = fields.Char(string="Codigo Provincia Para Facturacion", )
    log.info('--> Class Provincia')
