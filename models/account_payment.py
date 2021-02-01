# -*- coding: utf-8 -*-

from odoo import models, fields, api

class AccountPayment(models.Model):
    _inherit = "account.payment.term"
    fe_condition_sale = fields.Selection([
        ('01', "Contado"),
        ('02', "Crédito"),
        ('03', "Consignación"),
        ('04', "Apartado"),
        ('05', "Arrendamiento con opción de compra"),
        ('06', "Arrendamiento en función financiera"),
        ('07', "Cobro a favor de un tercero"),
        ('08', "Servicios prestados al Estado a crédito"),
        ('09', "Pago del servicios prestado al Estado"),
        ('99', "Otros (se debe indicar la condición de la venta)"),
    ], string="Condición de la Venta", track_visibility='onchange')
    payment_term_hacienda = fields.Char(string="Plazo Credito Hacienda",size=10)
    account_invoice_refund_ids = fields.One2many(
        string="account_invoice_refund_ids",
        comodel_name="account.move.reversal",
        inverse_name="payment_term_id",
    )
