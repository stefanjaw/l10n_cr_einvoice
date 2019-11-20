# -*- coding: utf-8 -*-

from odoo import models, fields, api

class Tax(models.Model):
    _inherit = "account.tax"

    codigo_impuesto = fields.Selection(
        string="Código Impuesto",
        selection=[
                ('01', 'Impuesto al Valor Agregado'),
                ('02' , 'Impuesto Selectivo de Consumo'),
                ('03' , 'Impuesto Único a los Combustibles'),
                ('04' , 'Impuesto específico de Bebidas Alcohólicas'),
                ('05' , 'Impuesto Específico sobre las bebidas envasadas sin contenido alcohólico y jabones de tocador'),
                ('06' , 'Impuesto a los Productos de Tabaco'),
                ('07' , 'IVA (cálculo especial)'),
                ('08' , 'IVA Régimen de Bienes Usados (Factor)'),
                ('12' ,'Impuesto Específico al Cemento'),
                ('99' , 'Otros')
        ],
    )

    tarifa_impuesto = fields.Selection(
        string="Tarifa del impuesto",
        selection=[
                ('01' , 'Tarifa 0% (Exento)'),
                ('02' , 'Tarifa reducida 1%'),
                ('03' , 'Tarifa reducida 2%'),
                ('04' , 'Tarifa reducida 4%'),
                ('05' , 'Transitorio 0%'),
                ('06' , 'Transitorio 4%'),
                ('07' , 'Transitorio 8%'),
                ('08' , 'Tarifa general 13%')
        ],
    )


    tipo_documento = fields.Selection(
        string="Tipo de documento",
        selection=[
                ('01', 'Contribución parafiscal'),
                ('02','Timbre de la Cruz Roja'),
                ('03', 'Timbre de Benemérito Cuerpo de Bomberos de Costa Rica.'),
                ('04' , 'Cobro de un tercero'),
                ('05' , 'Costos de Exportación'),
                ('06' , 'Impuesto de servicio 10%'),
                ('07' , 'Timbre de Colegios Profesionales'),
                ('99' , 'Otros Cargos')
        ],
    )

    type = fields.Selection(
        string="Tipo",
        selection=[
                ('TAX', 'Impuesto'),
                ('OTHER', 'Otro cargos'),
        ],
    )
