from odoo import models, fields, api, exceptions

import logging

log = _logging = logging.getLogger(__name__)

class AccountMoveInforefLine(models.Model):
    _name = "account.move.inforef.line"
    _description = "Informacion Referencia"

    tipodoc = fields.Selection([
        ('01', 'Factura electrónica'),
        ('02', 'Nota de débito electrónica '),
        ('03', 'Nota de crédito electrónica'),
        ('04', 'Tiquete electrónico'),
        ('05', 'Nota de despacho'),
        ('06', 'Contrato'),
        ('07', 'Procedimiento'),
        ('08', 'Comprobante emitido en contingencia'),
        ('09', 'Devolución mercadería'),
        ('10', 'Sustituye factura rechazada por el Ministerio de Hacienda'),
        ('11', 'Sustituye factura rechazada por el Receptor del comprobante'),
        ('12', 'Sustituye Factura de exportación'),
        ('13', 'Facturación mes vencido'),
        ('14', 'Comprobante aportado por contribuyente del Régimen de Tributación Simplificado'),
        ('15', 'Sustituye una Factura electrónica de Compra'),
        ('99', 'Otros'),
    ], string="TipoDocumento", required=True)
    numero = fields.Char(string="Numero", size=50, copy=False)
    fecha_emision = fields.Datetime()
    codigo = fields.Selection([
        ('01', 'Anula Documento de Referencia'),
        ('02', 'Corrige monto'),
        ('03', 'Referencia a otro documento'),
        ('04', 'Sustituye comprobante provisional por contingencia.'),
        ('05', 'Otros'),
    ])
    razon = fields.Char(size=180,)
    move_id = fields.Many2one('account.move', string="Asiento Contable o Factura")


    