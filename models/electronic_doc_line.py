from odoo import api, exceptions, fields, models, _

class ElectronicDocLine(models.Model):
    _inherit = 'account.move.line'
    electronic_doc_id = fields.Many2one('electroni.doc',string='documento electronico')
    is_selected = fields.Boolean(string = 'seleccionar',default=False)
    