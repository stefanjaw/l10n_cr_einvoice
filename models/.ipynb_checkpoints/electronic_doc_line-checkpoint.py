from odoo import api, exceptions, fields, models, _

class ElectronicDocLine(models.Model):
    _name = 'electronic.doc.line'
    electronic_doc_id = fields.Many2one('electronic.doc',string='documento electronico')
    name = fields.Char(string='Descripción')
    quantity = fields.Float(string='Cantidad')
    price_unit = fields.Float(string='Precio')
    tax_ids = fields.Many2many('account.tax', string='Taxes', help="Taxes that apply on the base amount")
    tax_amount = fields.Float('Monto Impuesto',compute="_compute_monto_impuesto")
    account_id = fields.Many2one('account.account', string='Account',
        index=True, ondelete="restrict", check_company=True,
        domain=[('deprecated', '=', False)])
    price_subtotal = fields.Float(string='Subtotal',compute="_compute_subtotal_linea")
    price_total = fields.Float(string='Total',compute="_compute_total_linea")
    is_selected = fields.Boolean(string = 'seleccionar',default=False)
    
    @api.depends("price_subtotal", "tax_amount" )
    def _compute_total_linea(self):
        for record in self:
            record.price_total = record.price_subtotal + record.tax_amount
    
    @api.depends("quantity", "price_unit" )
    def _compute_subtotal_linea(self):
        for record in self:
            record.price_subtotal = record.quantity * record.price_unit
            
    @api.depends("price_subtotal")       
    def _compute_monto_impuesto(self):
        for record in self:
            total = 0
            for tax in record.tax_ids:
                total = total + record.price_subtotal * (tax.amount/100)
            record.tax_amount = total
                