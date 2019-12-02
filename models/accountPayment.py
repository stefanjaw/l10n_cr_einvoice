# -*- coding: utf-8 -*-

from odoo import models, fields, api

class accountPayment(models.Model):
    _inherit = "account.payment.term"
    fe_condition_sale = fields.Selection([
        ('01', "Immediate Payment"),
        ('02', "Credit"),
        ('03', "Consignment"),
        ('04', "Separated"),
        ('05', "Lease with purchase option"),
        ('06', "Leasing in financial function"),
        ('99', "Others"),
    ], string="Sale Type", track_visibility='onchange')
