# -*- coding: utf-8 -*-

from odoo import _, api, fields, models

import logging
_logging = _logger = logging.getLogger(__name__)

class wizardReversal(models.TransientModel):
    _inherit = 'account.move.reversal'

    def reverse_moves(self):
        moves = self.env['account.move'].browse(self.env.context['active_ids']) if self.env.context.get('active_model') == 'account.move' else self.move_id
        # Create default values.
        default_values_list = []
        for move in moves:
            default_values_list.append(self._prepare_default_reversal(move))

        batches = [
            [self.env['account.move'], [], True],   # Moves to be cancelled by the reverses.
            [self.env['account.move'], [], False],  # Others.
        ]
        for move, default_vals in zip(moves, default_values_list):
            is_auto_post = bool(default_vals.get('auto_post'))
            is_cancel_needed = not is_auto_post and self.refund_method in ('cancel', 'modify')
            batch_index = 0 if is_cancel_needed else 1
            batches[batch_index][0] |= move
            batches[batch_index][1].append(default_vals)
        _logger.info(f"DEF28 =========")
        # Handle reverse method.
        moves_to_redirect = self.env['account.move']
        for moves, default_values_list, is_cancel_needed in batches:
            new_moves = moves._reverse_moves(default_values_list, cancel=is_cancel_needed)
            _logger.info(f"DEF33 =========")
            if self.refund_method == 'modify':
                moves_vals_list = []
                _logger.info(f"DEF36 =========")
                for move in moves.with_context(include_business_fields=True):
                    _logger.info(f"DEF37 =========")
                    moves_vals_list.append(move.copy_data({'date': self.date or move.date})[0])
                    
                _logger.info(f"DEF43 journal_id: {move.journal_id.name}")
                STOP40
                
                new_moves = self.env['account.move'].create(moves_vals_list)
            _logger.info(f"DEF45 =========")
            moves_to_redirect |= new_moves
            for move in moves_to_redirect:
                if len( move.name ) == 20:
                    move._generar_clave()

        # Create action.
        action = {
            'name': _('Reverse Moves'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
        }
        if len(moves_to_redirect) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': moves_to_redirect.id,
            })
        else:
            action.update({
                'view_mode': 'tree,form',
                'domain': [('id', 'in', moves_to_redirect.ids)],
            })
        return action

    
