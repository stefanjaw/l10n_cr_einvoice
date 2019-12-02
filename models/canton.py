# -*- coding: utf-8 -*-
from odoo import models, fields, api
import logging

log = logging.getLogger(__name__)

class Canton(models.Model):
    _name = "client.canton"

    log.info('--> Class Canton')

    name = fields.Char(string="Canton Name")
    code = fields.Char(string="Canton Code")
    state_id = fields.Many2one("res.country.state", string="Provincia")
