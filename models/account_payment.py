# -*- coding: utf-8 -*-

from odoo import models, fields, api

class AccountPayment(models.Model):
    _inherit = "account.payment.term"
    fe_condition_sale = fields.Selection([
        ('01', "01-Contado"),
        ('02', "02-Crédito"),
        ('03', "03-Consignación"),
        ('04', "04-Apartado"),
        ('05', "05-Arrendamiento con opción de compra"),
        ('06', "06-Arrendamiento en función financiera"),
        ('07', "07-Cobro a favor de un tercero"),
        ('08', "08-Servicios prestados al Estado a crédito"),
        ('09', "09-Pago del servicios prestado al Estado"),
        ('10', "10-Venta a crédito en IVA hasta 90 días (Artículo 27, LIVA)"),
        ('11', "11-Pago de venta a crédito en IVA hasta 90 días (Artículo 27,LIVA)"),
        ('12', "12-Venta Mercancía No Nacionalizada"),
        ('13', "13-Venta Bienes Usados No Contribuyente"),
        ('14', "14-Arrendamiento Operativo"),
        ('15', "15-Arrendamiento Financiero"),
        ('99', "99-Otros (se debe indicar la condición de la venta en la representación gráfica)"),
    ], string="Condición de la Venta", track_visibility='onchange')
    payment_term_hacienda = fields.Char(string="Plazo Credito Hacienda",size=10)
    account_invoice_refund_ids = fields.One2many(
        string="account_invoice_refund_ids",
        comodel_name="account.move.reversal",
        inverse_name="payment_term_id",
    )
