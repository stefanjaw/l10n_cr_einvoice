# -*- coding: utf-8 -*-

from odoo import models, fields, api

import logging
_logging = logging.getLogger(__name__)


class AccountJournal(models.Model):
    _inherit = 'account.journal'
    
    _logging.info("DEB __________ account.journal" )

    sequence_fe = fields.Many2one('ir.sequence', string='Secuencia Factura Electrónica')
    sequence_nd = fields.Many2one('ir.sequence', string='Secuencia Notas Debito')
    #sequence_nc = fields.Many2one('ir.sequence', string='Secuencia Notas Crédito')
    sequence_te = fields.Many2one('ir.sequence', string='Secuencia Tiquete Electrónico')
    sequence_fec = fields.Many2one('ir.sequence', string='Secuencia Factura Electrónica de Compra')
    sequence_fee = fields.Many2one('ir.sequence', string='Secuencia Factura Electrónica Exportación')
