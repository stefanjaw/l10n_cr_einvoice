# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging

log = logging.getLogger(__name__)

class confirmPopUp(models.TransientModel):
    _name='confirm.message'
    log.info('--> 1570130107')
    def continuar(self):
        invoice = self.env['account.invoice'].search([("id","=",self._context['invoice'])])
        invoice.action_invoice_open(False)
