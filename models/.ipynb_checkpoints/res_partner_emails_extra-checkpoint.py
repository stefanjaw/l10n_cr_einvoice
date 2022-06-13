# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError
import logging
import re

log = logging.getLogger(__name__)

class ResPartner(models.Model):
    _name = "res.partner.emails_extra"
    _description = "res.partner.emails_extra"

    partner_id = fields.Many2one('res.partner')
    email_additional = fields.Char(placeholder="Email Adicional" )
    email_main = fields.Boolean(string="Principal")
    email_send = fields.Boolean(string="Enviar")
    
    
    