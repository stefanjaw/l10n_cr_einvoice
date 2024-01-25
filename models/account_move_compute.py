from odoo import models, fields, api, exceptions
from odoo.exceptions import ValidationError

import logging

_logger = log = logging.getLogger(__name__)

class AccountMoveFunctions(models.Model):
    _inherit = "account.move"

    @api.depends("invoice_line_ids")
    def _compute_currency_rate(self):
        for record in self:
            currency_rate = record.invoice_line_ids.currency_rate
            if currency_rate > 0.0000:
                record.write({"fe_currency_rate": round(1/currency_rate, 2 )})
            else:
                record.write({"fe_currency_rate": 1})
    
    def _compute_total_serv_merc(self):
        _logger.info(f"  Computing Services and Products in: {self}\n")
        for record in self:
            total_serv_gravado = total_serv_exento = total_serv_exonerado = 0
            total_merc_gravado = total_merc_exento = total_merc_exonerado = 0
            total_venta = 0            
            total_gravado = total_exento = total_exonerado = 0
            total_descuento = 0
            
            total_impuestos = 0
            total_iva_devuelto = 0
            total_otros_cargos = 0
            total_comprobante = 0

            fiscal_position_id = record.fiscal_position_id
            for line_id in record.invoice_line_ids:
                if len(line_id.tax_ids) > 1:
                    raise ValidationError("Alert Einvoice CR: Configured 2 taxes in the line")
                
                if line_id.product_type == False or line_id.cabys_code:
                    line_id._compute_cabys_code()
                
                line_total_venta = line_id.quantity * line_id.price_unit
                
                line_total_descuento = line_total_venta - line_id.price_subtotal
                
                line_total_impuestos = line_id.price_total - line_id.price_subtotal
                
                monto_gravado = monto_exento = monto_exonerado = 0
                
                fiscal_position_tax_id = fiscal_position_id.tax_ids.search([
                    ('position_id','=', fiscal_position_id.id),
                    ('tax_dest_id', '=', line_id.tax_ids.id)
                ])
                
                if len(fiscal_position_tax_id) > 0:
                    monto_exonerado = line_total_venta
                elif line_total_impuestos > 0.00:
                    monto_gravado = line_total_venta
                elif line_total_impuestos == 0.00:
                    monto_exento = line_total_venta
                
                serv_gravado = serv_exento = serv_exonerado = \
                merc_gravado = merc_exento = merc_exonerado = 0
                if line_id.product_type == "service":
                    serv_gravado = monto_gravado
                    serv_exento = monto_exento
                    serv_exonerado = monto_exonerado
                elif line_id.product_type == "product":
                    merc_gravado = monto_gravado
                    merc_exento = monto_exento
                    merc_exonerado = monto_exonerado
                else:
                    raise ValidationError("Error Einvoice Unknown Invoice Product Type")
                
                line_total_gravado = serv_gravado + merc_gravado
                line_total_exento = serv_exento + merc_exento
                line_total_exonerado = serv_exonerado + merc_exonerado
                
                line_total_comprobante = line_total_venta - line_total_descuento + line_total_impuestos

                total_serv_gravado += serv_gravado
                total_serv_exento += serv_exento
                total_serv_exonerado += serv_exonerado

                total_merc_gravado += merc_gravado
                total_merc_exento += merc_exento
                total_merc_exonerado += merc_exonerado
                
                total_venta += line_total_venta
                total_descuento += line_total_descuento
                total_impuestos += line_total_impuestos
            
            total_gravado   = total_serv_gravado + total_merc_gravado
            total_exento    = total_serv_exento + total_merc_exento
            total_exonerado = total_serv_exonerado + total_merc_exonerado
            total_comprobante = ( total_venta \
                                          - total_descuento \
                                          + total_impuestos \
                                          + total_otros_cargos
                                 )
            
            record.fe_total_servicio_gravados = total_serv_gravado
            record.fe_total_servicio_exentos  = total_serv_exento
            record.TotalServExonerado         = total_serv_exonerado
            
            record.fe_total_mercancias_gravadas = total_merc_gravado
            record.fe_total_mercancias_exentas  = total_merc_exento
            record.TotalMercExonerada           = total_merc_exonerado

            record.fe_total_gravado = total_gravado
            record.fe_total_exento  = total_exento
            record.TotalExonerado   = total_exonerado
            
            record.fe_total_venta = total_venta
            record.fe_total_descuento = total_descuento
