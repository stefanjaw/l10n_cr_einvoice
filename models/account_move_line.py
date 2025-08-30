from odoo import models, fields, api, exceptions
from odoo.exceptions import ValidationError

class AccountMoveLineEinvoice(models.Model):
    _inherit = "account.move.line"

    product_type = fields.Selection([
        ('product', 'Producto'),
        ('service', 'Servicio'),
        ('other', 'Otro')
    ])
    
    cabys_code = fields.Char( )
    partida_arancelaria = fields.Char( )

    fe_tipo_transaccion = fields.Selection(
        [
            ('01', 'Venta Normal de Bienes y Servicios (Transacción General)' ),
            ('02', 'Mercancía de Autoconsumo exento' ),
            ('03', 'Mercancía de Autoconsumo gravado' ),
            ('04', 'Servicio de Autoconsumo exento' ),
            ('05', 'Servicio de Autoconsumo gravado' ),
            ('06', 'Cuota de afiliación' ),
            ('07', 'Cuota de afiliación Exenta' ),
            ('08', 'Bienes de Capital para el emisor' ),
            ('09', 'Bienes de Capital para el receptor.' ),
            ('10', 'Bienes de Capital para para el emisor y el receptor.' ),
            ('11', 'Bienes de capital de autoconsumo exento para el emisor' ),
            ('12', 'Bienes de capital sin contraprestación a terceros exento para el emisor' ),
            ('13', 'Sin contraprestación a terceros' )
        ],
        string="Tipo Transaccion"
    )

    fe_numero_vin_o_serie = fields.Text("Numero Vin o Serie" )
    fe_registro_medicamento = fields.Char("Registro de Medicamento")

    fe_forma_farmaceutica = fields.Many2one("forma.farmaceutica", string="Forma Farmaceutica")

    fe_codigo_descuento = fields.Selection(
        [
            ('01', 'Descuento por Regalía' ),
            ('02', 'Descuento por Regalía o Bonificaciones IVA Cobrado al Cliente' ),
            ('03', 'Descuento por Bonificación' ),
            ('04', 'Descuento por volumen' ),
            ('05', 'Descuento por Temporada (estacional)' ),
            ('06', 'Descuento promocional' ),
            ('07', 'Descuento Comercia' ),
            ('08', 'Descuento por frecuencia' ),
            ('09', 'Descuento sostenido' ),
            ('99', 'Otros descuentos' ),

        ],
        string="Codigo Descuento"
    )
    
    fe_codigo_descuento_otro = fields.Char("Codigo Descuento Otro")
    
    fe_naturaleza_descuento = fields.Char("Naturaleza Descuento")

    fe_iva_cobrado_fabrica = fields.Selection(
        [
            ('01', 'Venta de bienes con IVA según el sistema especial de determinación de IVA a nivel de fábrica (Se utiliza cuando se está cobrando el IVA a nivel de fábrica' ),
            ('02', 'Ventas exentas según el sistema especial de determinación de IVA a nivel de fábrica, mayorista y aduanas (se utiliza cuando el producto se encuentra exento ya que el bien soporto el cobro de impuestos a nivel de fábrica).' ),
        ],
        string="IVA Cobrado Fabrica"
    )
    
    @api.onchange('product_id')
    def _compute_cabys_code(self):
        try:
            if self.product_id.detailed_type == "service":
                product_type = "service"
            elif self.product_id.detailed_type == "consu":
                product_type = "product"
            elif self.product_id.detailed_type == "product":
                product_type = "product"
            else:
                product_type = "other"
            
            self.cabys_code = self.product_id.cabys_code_id.code
            self.partida_arancelaria = self.product_id.cabys_code_id.partida_arancelaria
            
            self.product_type = product_type
        except:
            pass
        
        return

    def create(self, params):
        lines = super().create(params)

        for line in lines:
            if line.product_type in [False, None] or \
            line.cabys_code   in [False, None]:
                line._compute_cabys_code()
        return lines
