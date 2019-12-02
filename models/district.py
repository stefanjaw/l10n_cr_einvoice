
# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging

log = logging.getLogger(__name__)

class District(models.Model):
    _name = "client.district"
    log.info('--> Class District')
    name = fields.Char(string="District Name")
    code = fields.Char(string="District Code")
    canton_id = fields.Many2one("client.canton", string="Canton")
