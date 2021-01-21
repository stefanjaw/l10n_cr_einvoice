# -*- coding: utf-8 -*-

from odoo import _, api, fields, models


class Router(models.Model):
    _name = 'router.router'
    _inherit = ['mail.thread']
    _description = 'esta clase permite el ingreso correcto de los email'
    _auto = False



    