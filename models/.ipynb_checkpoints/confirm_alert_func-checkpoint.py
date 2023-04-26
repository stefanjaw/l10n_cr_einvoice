from odoo import models, fields, api
import logging

log = logging.getLogger(__name__)

class ConfirmAlertFunctions(models.TransientModel):
    _name='confirm.alert'
    _description = "confirm.alert"
    
    log.info('--> 1570130107')
    
    def continuar(self):
        invoice = self.env['account.move'].search([("id","=",self._context['invoice'])])
        invoice.action_post(False)