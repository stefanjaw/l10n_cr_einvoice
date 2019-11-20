
# -*- coding: utf-8 -*-

from odoo import models, fields, api

class Neighborhood(models.Model):
    _name = "client.neighborhood"
    name = fields.Char(string="Neighborhood Name")
    code = fields.Char(string="Neighborhood Code")
    district_id = fields.Many2one("client.district", string="Distrito")
