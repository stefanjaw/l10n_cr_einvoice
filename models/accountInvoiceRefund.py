from odoo import models, fields, api, _
from odoo.tools.safe_eval import safe_eval
from odoo.exceptions import UserError
        
class accountInvoiceRefund(models.TransientModel):
    _inherit = "account.invoice.refund"

    fe_payment_type = fields.Selection([
            ('01', 'Efectivo'),
            ('02', 'Tarjeta'),
            ('03', 'Cheque'),
            ('04', 'Transferencia - depósito bancario'),
            ('05', 'Recaudado por tercero'),
            ('99', ' Otros'),
    ], string="Tipo de pago", track_visibility='onchange',required=False,) 
    
    payment_term_id = fields.Many2one('account.payment.term', string='Payment Terms',)
    
    fe_receipt_status = fields.Selection([
               ('1', 'Normal'),
               ('2', 'Contingencia'),
               ('3', 'Sin Internet'),
    ], string="Situación del comprobante", track_visibility='onchange',required=False,)
    
    fe_activity_code_id = fields.Many2one(
        string="Actividad económica",
        comodel_name="activity.code",
        ondelete="set null",
    )
    
    fe_tipo_documento_referencia = fields.Selection(
        string="Tipo documento de referencia",
        selection=[                
                ('01','Factura electrónica'),
                ('02','Nota de débito electrónica'),
                ('03','Nota de crédito electrónica'),
	            ('04','Tiquete electrónico'),
                ('05','Nota de despacho'),
	            ('06','Contrato'),
                ('07','Procedimiento'),
                ('08','Comprobante emitido en contingencia'),
                ('09','Devolución mercadería'),
                ('10','Sustituye factura rechazada por el Ministerio de Hacienda'),
	            ('11','Sustituye factura rechazada por el Receptor del comprobante'),
                ('12','Sustituye Factura de exportación'),
                ('13','Facturación mes vencido'),
                ('99','Otros'),
        ],
    )
    
    fe_informacion_referencia_codigo = fields.Selection([
            ('01', 'Anula Documento de Referencia'),
            ('02', 'Corrige monto'),
            ('04', 'Referencia a otro documento'),
            ('05', 'Sustituye comprobante provisional por contingencia.'),
            ('99', 'Otros'),
    ], string="Codigo de Referencia", track_visibility='onchange')
    
    fe_current_country_company_code = fields.Char(string="Codigo pais de la compañia actual",compute="_get_country_code")

    company_id = fields.Many2one(
    'res.company',
    'Company',
    default=lambda self: self.env.user.company_id.id 
    )
    
        

    @api.depends('company_id')
    def _get_country_code(self):
        for s in self:
            s.fe_current_country_company_code = s.company_id.country_id.code 
                         

    def compute_refund(self, mode='refund'):
        inv_obj = self.env['account.invoice']
        inv_tax_obj = self.env['account.invoice.tax']
        inv_line_obj = self.env['account.invoice.line']
        context = dict(self._context or {})
        xml_id = False

        for form in self:
            created_inv = []
            date = False
            description = False
            for inv in inv_obj.browse(context.get('active_ids')):
                if inv.state in ['draft', 'cancel']:
                    raise UserError(_('Cannot create credit note for the draft/cancelled invoice.'))
                if inv.reconciled and mode in ('cancel', 'modify'):
                    raise UserError(_('Cannot create a credit note for the invoice which is already reconciled, invoice should be unreconciled first, then only you can add credit note for this invoice.'))

                date = form.date or False
                description = form.description or inv.name
                refund = inv.refund(form.date_invoice, date, description, inv.journal_id.id,form.fe_payment_type,form.payment_term_id.id,form.fe_activity_code_id.id,form.fe_receipt_status,form.fe_tipo_documento_referencia,form.fe_informacion_referencia_codigo)

                created_inv.append(refund.id)
                if mode in ('cancel', 'modify'):
                    movelines = inv.move_id.line_ids
                    to_reconcile_ids = {}
                    to_reconcile_lines = self.env['account.move.line']
                    for line in movelines:
                        if line.account_id.id == inv.account_id.id:
                            to_reconcile_lines += line
                            to_reconcile_ids.setdefault(line.account_id.id, []).append(line.id)
                        if line.reconciled:
                            line.remove_move_reconcile()
                    refund.action_invoice_open()
                    for tmpline in refund.move_id.line_ids:
                        if tmpline.account_id.id == inv.account_id.id:
                            to_reconcile_lines += tmpline
                    to_reconcile_lines.filtered(lambda l: l.reconciled == False).reconcile()
                    if mode == 'modify':
                        invoice = inv.read(inv_obj._get_refund_modify_read_fields())
                        invoice = invoice[0]
                        del invoice['id']
                        invoice_lines = inv_line_obj.browse(invoice['invoice_line_ids'])
                        invoice_lines = inv_obj.with_context(mode='modify')._refund_cleanup_lines(invoice_lines)
                        tax_lines = inv_tax_obj.browse(invoice['tax_line_ids'])
                        tax_lines = inv_obj._refund_cleanup_lines(tax_lines)
                        invoice.update({
                            'type': inv.type,
                            'date_invoice': form.date_invoice,
                            'state': 'draft',
                            'number': False,
                            'invoice_line_ids': invoice_lines,
                            'tax_line_ids': tax_lines,
                            'date': date,
                            'origin': inv.origin,
                            'fiscal_position_id': inv.fiscal_position_id.id,
                        })
                        for field in inv_obj._get_refund_common_fields():
                            if inv_obj._fields[field].type == 'many2one':
                                invoice[field] = invoice[field] and invoice[field][0]
                            else:
                                invoice[field] = invoice[field] or False
                        inv_refund = inv_obj.create(invoice)
                        if inv_refund.payment_term_id.id:
                            inv_refund._onchange_payment_term_date_invoice()
                        created_inv.append(inv_refund.id)
                xml_id = inv.type == 'out_invoice' and 'action_invoice_out_refund' or \
                         inv.type == 'out_refund' and 'action_invoice_tree1' or \
                         inv.type == 'in_invoice' and 'action_invoice_in_refund' or \
                         inv.type == 'in_refund' and 'action_invoice_tree2'
                # Put the reason in the chatter
                subject = _("Credit Note")
                body = description
                refund.message_post(body=body, subject=subject)
        if xml_id:
            result = self.env.ref('account.%s' % (xml_id)).read()[0]
            invoice_domain = safe_eval(result['domain'])
            invoice_domain.append(('id', 'in', created_inv))
            result['domain'] = invoice_domain
            return result
        return True