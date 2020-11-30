# -*- coding: utf-8 -*-

from odoo import _, api, fields, models


class wizardReversal(models.TransientModel):
    _inherit = 'account.move.reversal'

    def reverse_moves(self):
        action = super(wizardReversal, self).reverse_moves()
        moves = self.env['account.move'].browse(self.env.context['active_ids']) if self.env.context.get('active_model') == 'account.move' else self.move_id
        for move in moves:
            move._generar_clave()
        return action

    