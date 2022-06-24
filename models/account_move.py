from odoo import models, fields, api, exceptions
from datetime import datetime,timezone
import pytz
import logging

log = _logging = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"
    
    fe_clave = fields.Char(string="Clave", size=50, copy=False)

    def default_activity(self): #1655869588
        fe_activity_code_int = False
        fe_activity_code_id = False
        try:
            companies_arr = str(self._context.get('params').get('cids')).split(",")
            if len(companies_arr) == 1:
                company_ids = self.env['res.company'].sudo().browse( int(companies_arr[0]) )
                if len(company_ids[0].fe_activity_code_ids) == 1:
                    fe_activity_code_int = company_ids[0].fe_activity_code_ids[0].id
        except:
            pass
        return fe_activity_code_int
    
    fe_activity_code_id = fields.Many2one(
        string="Actividad económica",
        comodel_name="activity.code",
        ondelete="set null",
        states={'posted': [('readonly', True)]},
        default=default_activity,
    )

    fe_payment_type = fields.Selection([
        ('01', 'Efectivo'),
        ('02', 'Tarjeta'),
        ('03', 'Cheque'),
        ('04', 'Transferencia - depósito bancario'),
        ('05', 'Recaudado por tercero'),
        ('99', ' Otros'),
    ], string="Tipo de pago", track_visibility='onchange',required=False,
    states={'posted': [('readonly', True)]})

    fe_receipt_status = fields.Selection([
           ('1', 'Normal'),
           ('2', 'Contingencia'),
           ('3', 'Sin Internet'),
    ], string="Situación del comprobante", track_visibility='onchange',required=False, 
    states={'posted': [('readonly', True)]})
    
    fe_name_xml_sign = fields.Char(string="nombre xml firmado",copy=False )
    fe_xml_sign = fields.Binary(string="XML firmado",copy=False )
    
    fe_name_xml_hacienda = fields.Char(string="nombre xml hacienda",copy=False )
    fe_xml_hacienda = fields.Binary(string="XML Hacienda",copy=False )# 1570034790
    
    fe_tohacienda_json = fields.Text(string="JSON hacia Hacienda", copy=False )
    fe_fromhacienda_json = fields.Text(string="JSON respuesta Hacienda", copy=False )
    fe_fromhacienda_xml_html = fields.Html(string="Respuesta de Hacienda", copy=False )
    
    fe_server_state = fields.Char(string="Estado Hacienda",copy=False )
    
    electronic_doc_id = fields.Many2one('electronic.doc', string='XML',readonly = True, )

    otros_ids = fields.One2many('account.move.otros.line','move_id')
    
    inforef_ids = fields.One2many('account.move.inforef.line','move_id')
    
    other_attachments_ids = fields.One2many('account.move.attachment.line','move_id')
    
    def _move_type_extra_lst(self):
        out_invoice_lst= [
                ('fe', 'Factura Electrónica'),
                ('nd', 'Nota Débito'),
                ('te', 'Tiquete Electrónico'),
                ('fee', 'Factura Electronica Exportación'),
            ]
        out_refund_lst = [ ('nc', 'Nota Crédito') ]
        in_invoice = [ ('fec', 'Factura Electrónica Compra') ]

        default_move_type = self._context.get('default_move_type')

        lst = False
        if default_move_type == "out_invoice":
            lst = out_invoice_lst
        elif default_move_type == "out_refund":
            lst = out_refund_lst
        elif default_move_type == "in_invoice":
            lst = in_invoice
        else:
            lst = []
            lst.extend(out_invoice_lst)
            lst.extend(out_refund_lst)
            lst.extend(in_invoice)
        return lst

    move_type_extra =  fields.Selection(
        _move_type_extra_lst,
        string="Tipo Documento Electrónico",
        default=lambda self: self.fields_get().get('move_type_extra').get('selection')[0][0],
    )
    
    exchange_rate = fields.Float(string="Tipo de Cambio", compute="_compute_exchange_rate")
    exchange_rate_date = fields.Date(string="Fecha Tipo de Cambio")
    
    @api.onchange('invoice_date', 'currency_id')
    def _compute_exchange_rate(self):
        
        from_currency = self.currency_id
        to_currency = self.company_id.currency_id
        company_id = self.company_id
        currency_date = self.invoice_date or datetime.utcnow( )
        exchange_rate = self.env['res.currency']._get_conversion_rate(
            from_currency, to_currency, company_id, currency_date
        )
        self.exchange_rate = round(exchange_rate, 2)
        self.exchange_rate_date = currency_date
        return
    
