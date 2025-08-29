from odoo import models, fields, api, _
from odoo.tools.safe_eval import safe_eval
from odoo.exceptions import UserError
from datetime import datetime,timezone
import pytz
        
class AccountMoveReversal(models.TransientModel):
    _inherit = "account.move.reversal"
    
    date = fields.Date(string='Reversal date', default=datetime.now(tz=pytz.timezone('America/Costa_Rica')).strftime("%Y-%m-%d %H:%M:%S"), required=True)
    
    fe_payment_type = fields.Selection([
            ('01', 'Efectivo'),
            ('02', 'Tarjeta'),
            ('03', 'Cheque'),
            ('04', 'Transferencia - depósito bancario'),
            ('05', 'Recaudado por terceros'),
            ('06', 'SINPE MOVIL'),
            ('07', 'Plataforma digital'),
            ('99', 'Otros'),
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
                ('10','Comprobante electrónico rechazado por el Ministerio de Hacienda'),
                ('11','Sustituye factura rechazada por el Receptor del comprobante'),
                ('12','Sustituye Factura de exportación'),
                ('13','Facturación mes vencido'),
                ('14','Comprobante aportado por contribuyente de Régimen Especial.'),
                ('15','Sustituye una Factura electrónica de Compra'),
                ('16','Comprobante de Proveedor No Domiciliado'),
                ('17','Nota de Crédito a Factura Electrónica de Compra'),
                ('18','Nota de Debito a Factura Electrónica de Compra'),
                ('99','Otros')
        ],
    )
    
    fe_informacion_referencia_codigo = fields.Selection([
            ('01', 'Anula Documento de Referencia'),
            ('02', 'Corrige monto'),
            ('04', 'Referencia a otro documento'),
            ('05', 'Sustituye comprobante provisional por contingencia.'),   
            ('06', 'Devolución de mercancía'),   
            ('07', 'Sustituye comprobante electrónico.'),   
            ('08', 'Factura Endosada'),   
            ('09', 'Nota de crédito financiera'),   
            ('10', 'Nota de débito financiera'),   
            ('11', 'Proveedor No Domiciliado'),   
            ('12', 'Crédito por exoneración posterior a la facturación'),   
            ('99', 'Otros'),
    ], string="Codigo de Referencia", track_visibility='onchange')
    
    fe_current_country_company_code = fields.Char(string="Codigo pais de la compañia actual",compute="_get_country_code")
    
    company_id = fields.Many2one(
        'res.company',
        'Company',
         default=lambda self: self.env.company.id 
    )
