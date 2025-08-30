# -*- coding: utf-8 -*-

from odoo import models, fields, api

class AccountTax(models.Model):
    _inherit = "account.tax"

    codigo_impuesto = fields.Selection(
        string="Código Impuesto",
        selection=[
                ('01',  '01-Impuesto al Valor Agregado'),
                ('02' , '02-Impuesto Selectivo de Consumo'),
                ('03' , '03-Impuesto Único a los Combustibles'),
                ('04' , '04-Impuesto específico de Bebidas Alcohólicas'),
                ('05' , '05-Impuesto Específico sobre las bebidas envasadas sin contenido alcohólico y jabones de tocador'),
                ('06' , '06-Impuesto a los Productos de Tabaco'),
                ('07' , '07-IVA (cálculo especial)'),
                ('08' , '08-IVA Régimen de Bienes Usados (Factor)'),
                ('12' , '12-Impuesto Específico al Cemento'),
                ('99' , '99-Otros')
        ],
    )

    fe_codigo_impuesto_otro = fields.Char(string="Codigo Impuesto Otro")

    fe_factor_calculo_iva = fields.Float(
        string="Factor para Calculo IVA",
        digits=(5, 4)
    )
    
    tarifa_impuesto = fields.Selection(
        string="Tarifa del impuesto",
        selection=[
                ('01' , '01-Tarifa 0% (Artículo 32, num 1, RLIVA)'),
                ('02' , '02-Tarifa reducida 1%'),
                ('03' , '03-Tarifa reducida 2%'),
                ('04' , '04-Tarifa reducida 4%'),
                ('05' , '05-Transitorio 0%'),
                ('06' , '06-Transitorio 4%'),
                ('07' , '07-Tarifa transitoria 8%'),
                ('08' , '08-Tarifa general 13%'),
                ('09' , '09-Tarifa reducida 0.5%'),
                ('10' , '10-Tarifa Exenta'),
                ('11' , '11-Tarifa 0% sin derecho a crédito')
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