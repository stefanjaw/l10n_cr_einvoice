from odoo import models, fields, api

class accountJournal(models.Model):
    _inherit = "account.journal"
    electronic_doc_ids = fields.One2many('electronic.doc', 'sequence_id')
    
    sequence_fe = fields.Many2one('ir.sequence', string='Secuencia Factura Electrónica', help='Default Prefix: 0010000101')
    sequence_nd = fields.Many2one('ir.sequence', string='Secuencia Notas Debito', help='Default Prefix: 0010000102')
    #sequence_nc = fields.Many2one('ir.sequence', string='Secuencia Notas Crédito')
    sequence_te = fields.Many2one('ir.sequence', string='Secuencia Tiquete Electrónico', help='Default Prefix: 0010000104')
    sequence_fec = fields.Many2one('ir.sequence', string='Secuencia Factura Electrónica de Compra', help='Default Prefix: 0010000108')
    sequence_fee = fields.Many2one('ir.sequence', string='Secuencia Factura Electrónica Exportación', help='Default Prefix: 0010000109')
