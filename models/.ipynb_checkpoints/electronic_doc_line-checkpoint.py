from odoo import api, exceptions, fields, models, _
import logging
log = logging.getLogger(__name__)

class ElectronicDocLine(models.Model):
    _name = 'electronic.doc.line'
    _description = "electronic.doc.line"
    
    electronic_doc_id = fields.Many2one('electronic.doc',string='documento electronico')
    name = fields.Char(string='Descripción')
    quantity = fields.Float(string='Cantidad')
    price_unit = fields.Float(string='Precio')
    tax_ids = fields.Many2many('account.tax', string='Taxes', help="Taxes that apply on the base amount",
    domain=lambda self: self.tax_domain())
    tax_amount = fields.Float('Monto Impuesto',compute="_compute_monto_impuesto")
    account_id = fields.Many2one('account.account', string='Account',
        index=True, ondelete="restrict", check_company=True,
        domain=[('deprecated', '=', False)])
    price_subtotal = fields.Float(string='Subtotal',compute="_compute_subtotal_linea")
    price_total = fields.Float(string='Total',compute="_compute_total_linea")
    is_selected = fields.Boolean(string = 'seleccionar',default=True)
    state = fields.Char(compute='_compute_state', string='Line state')
    discount = fields.Float(string='Descuento', digits=(15,2))
    discount_percent = fields.Float(compute='_compute_discount_percent', string='',digits=(15,2))
    
    
    @api.depends('discount','price_subtotal')
    def _compute_discount_percent(self):
        for record in self:
            if record.price_unit > 0.00 and record.quantity > 0.00:
                record.discount_percent =  (record.discount * 100) / (record.quantity * record.price_unit)
            else:
                record.discount_percent = 0.00

    def tax_domain(self):
        #agreger filtro por compañia luego
        return [('type_tax_use','=','purchase'),('company_id','=',self.env.company.id)]

    @api.onchange('tax_ids')
    def _onchange_tax_ids(self):
        for record in self:
            total = 0
            for tax in record.tax_ids:
                total = total + record.price_subtotal * (tax.amount/100)
            record.tax_amount = total
    
    @api.depends('electronic_doc_id.state')
    def _compute_state(self):
        self.state = self.electronic_doc_id.state
    
    @api.depends("price_subtotal", "tax_amount" )
    def _compute_total_linea(self):
        for record in self:
            record.price_total = record.price_subtotal + record.tax_amount
    
    @api.depends("quantity", "price_unit" )
    def _compute_subtotal_linea(self):
        for record in self:
            record.price_subtotal = (record.quantity * record.price_unit) - record.discount
            
    @api.depends("price_subtotal")       
    def _compute_monto_impuesto(self):
        for record in self:
            total = 0
            for tax in record.tax_ids:
                total = total + record.price_subtotal * (tax.amount/100)
            record.tax_amount = total
                
