from odoo import api, fields, models, _

class accountMoveDebit(models.TransientModel):
    _name = "account.move.debit"
    _description = "Debit Note"
    
    fe_reason = fields.Char(string="reason", )
    journal_id = fields.Many2one("account.journal", string="Journal")
    
    fe_informacion_referencia_codigo = fields.Selection([
        ('01', 'Anula Documento de Referencia'),
        ('02', 'Corrige monto'),
        ('04', 'Referencia a otro documento'),
        ('05', 'Sustituye comprobante provisional por contingencia.'),
        ('99', 'Otros'),
    ], string="Codigo de Referencia", track_visibility='onchange',)
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
        ],)

    def add_note(self):
        _logger.info(f"DEF40 wizard context: {self._context} journal_id: {self.journal_id}")
        
        id = self.env.context.get('active_id')
        doc_ref = self.env.context.get('doc_ref')
        journal_id = self.env.context.get('journal_id')
        
        move_id = self.env['account.move'].browse(id).copy({'debit_note':True,
                                                         'ref':self.fe_reason,
                                                         'fe_doc_ref':doc_ref,
                                                         'fe_informacion_referencia_codigo':self.fe_informacion_referencia_codigo,
                                                         'fe_tipo_documento_referencia':self.fe_tipo_documento_referencia,
                                                         'fe_in_invoice_type':'ND',
                                                         'fe_doc_type': 'NotaDebitoElectronica'
                                                        })
        
        return {
            'name': _("Debit Notes"),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id':move_id.id,
            'view_type': 'form',
            'view_mode': 'form',
        }