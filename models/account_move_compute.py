from odoo import models, fields, api, exceptions
from odoo.exceptions import ValidationError

import logging

_logger = log = logging.getLogger(__name__)

class AccountMoveFunctions(models.Model):
    _inherit = "account.move"

    def _compute_total_serv_merc(self):
        for record in self:
            total_serv_gravado = 0
            total_serv_exento = 0
            total_serv_exonerado = 0

            total_merc_gravado = 0
            total_merc_exento = 0
            total_merc_exonerado = 0
            
            total_gravado = 0
            total_exento = 0
            total_exonerado = 0

            total_venta = 0
            total_descuento = 0
            
            total_impuesto = 0
            total_iva_devuelto = 0

            total_otros_cargos = 0

            total_comprobante = 0

            fiscal_position_id = record.fiscal_position_id
            _logger.info(f"DEF36 fiscal_position_id: {fiscal_position_id.id}-{fiscal_position_id.name}")
            for line_id in record.invoice_line_ids:
                _logger.info(f"DEF38 line_id: {line_id.name}")

                tax_ids = line_id.tax_ids
                _logger.info(f"DEF40a      tax_ids: {tax_ids}")
                if len(tax_ids) > 0:
                    for tax_id in tax_ids:
                        _logger.info(f"DEF43          tax_id: {tax_id}")
                _logger.info(f"DEF44      taxes: {taxes}")
                
            
        STOP69