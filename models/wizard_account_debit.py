from odoo import api, fields, models, _

import datetime, pytz

class accountMoveDebit(models.TransientModel):
    _name = "account.move.debit"
    _description = "Debit Note"
    
    fe_reason = fields.Char(string="reason", )
    
    fe_informacion_referencia_codigo = fields.Selection([
        ('01', 'Anula Documento de Referencia'),
        ('02', 'Corrige monto'),
        ('04', 'Referencia a otro documento'),
        ('05', 'Sustituye comprobante provisional por contingencia.'),
        ('99', 'Otros'),
    ], string="Codigo de Referencia", track_visibility='onchange',)
    
    def add_note(self):

        source_id_int = self.env.context.get('active_id')
        source_move_id = self.env['account.move'].browse(source_id_int)
        
        fe_fecha_emision_str = source_move_id.fe_fecha_emision
        fe_fecha_emision_utc = datetime.datetime.fromisoformat( fe_fecha_emision_str + '-06:00').astimezone( pytz.timezone('UTC') )
        
        if source_move_id.name[8:10] == "01":
            fe_tipo_documento_referencia = "01"
        elif source_move_id.name[8:10] == "02":
            fe_tipo_documento_referencia = "02"
        elif source_move_id.name[8:10] == "03":
            fe_tipo_documento_referencia = "03"
        elif source_move_id.name[8:10] == "04":
            fe_tipo_documento_referencia = "04"
        else:
            fe_tipo_documento_referencia = False
        
        move_id = source_move_id.copy({'debit_note':True,
                     'ref':self.fe_reason,
                     'fe_doc_ref':source_move_id.name,
                     'fe_informacion_referencia_fecha': fe_fecha_emision_utc.strftime('%Y-%m-%d %H:%M:%S'),
                     'fe_informacion_referencia_codigo':self.fe_informacion_referencia_codigo,
                     'fe_tipo_documento_referencia': fe_tipo_documento_referencia,
                     'fe_in_invoice_type':'ND',
                     'fe_doc_type': 'NotaDebitoElectronica'
                    })
        
        return {
            'name':         _("Debit Notes"),
            'type':         'ir.actions.act_window',
            'res_model':    'account.move',
            'res_id':       move_id.id,
            'view_type':    'form',
            'view_mode':    'form',
        }
