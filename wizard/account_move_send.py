from odoo import models, fields, api
from odoo.exceptions import ValidationError

import logging

_logger = _logging = logging.getLogger(__name__)

class AccountMoveSendInherit(models.TransientModel): # 1707799931
    _inherit = 'account.move.send'
    
    def _compute_mail_attachments_widget(self):
        original = super()._compute_mail_attachments_widget()
        _logger.info(f"l10n_cr_einvoice_attachments")        
        if len(self.move_ids) > 1:
            msg = f"Many Records Detected: {self.move_ids}"
            raise ValidationError(msg)
        else:
            move_id = self.move_ids

        if move_id.fe_xml_sign in [None, False, ""]     \
        and move_id.fe_xml_hacienda in [None, False, ""]:
            
            return original
        
        
        attachment_ids = self.mail_attachments_widget.copy()
        
        fe_xml_name = move_id.fe_name_xml_sign
        attachment_id = self.env['ir.attachment'].search([(
            "name", "=", fe_xml_name
        )])
        
        if len(attachment_id) == 0 and move_id.fe_xml_sign not in [None, False, ""]:
            attachment_id = self.create_attachment(
                move_id, fe_xml_name, "binary",
                "application/xml", move_id.fe_xml_sign
            )
        
        if len(attachment_id) > 0:
            attachment_ids.extend([{
               'id': attachment_id.id,
               'name': attachment_id.name,
               'mimetype': attachment_id.mimetype,
               'placeholder': False,
               'protect_from_deletion': True
            }])
        
        fe_xml_name = move_id.fe_name_xml_hacienda
        attachment_id = self.env['ir.attachment'].search([(
            "name", "=", fe_xml_name
        )])
        if len(attachment_id) == 0 and move_id.fe_xml_hacienda not in [None, False, ""]:
            attachment_id = self.create_attachment(
                move_id, fe_xml_name, "binary",
                "application/xml", move_id.fe_xml_hacienda
            )
        if len(attachment_id) > 0:
            attachment_ids.extend([{
                'id': attachment_id.id,
                'name': attachment_id.name,
                'mimetype': 'application/xml',
                'placeholder': False,
                'protect_from_deletion': True
            }])

        self.write({
            "mail_attachments_widget": attachment_ids
        })
        return

    def create_attachment(self, record_id, filename, type, mimetype, datas):
        attachment_id = self.env['ir.attachment'].search([(
            "name", "=", filename
        )])
        
        if len(attachment_id) == 1:
            pass
        else:
            attachment_id = attachment_id.sudo().create({
                "res_model": record_id._name,
                "res_id": record_id.id,
                "res_name": record_id.name,
                "name": filename,
                "type": type,
                "mimetype": mimetype,
                "datas": datas
            })
        return attachment_id
