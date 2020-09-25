from odoo import api, exceptions, fields, models, _
from odoo.exceptions import ValidationError
from lxml.etree import Element, fromstring, parse, tostring, XMLParser
import lxml.etree as ET
import xmltodict
import logging
import base64

from io import BytesIO

log = logging.getLogger(__name__)

class email(models.Model):
    _name = 'email'
    _inherit = ['mail.thread']
    _rec_name = 'display_name'
    message_id = fields.Char()
    date = fields.Char()
    email_from = fields.Char()
    to = fields.Char()
    subject = fields.Char()
    body = fields.Html()
    attachments = fields.One2many('email.attach',
                                  'email_id',
                                  string='Archivos adjuntos')
    display_name = fields.Char(
        string='Name',
        compute='_compute_display_name',
    )
        
    @api.depends('email_from', 'date')
    def _compute_display_name(self):
        self.display_name = '{0} {1}'.format(self.email_from, self.date)
        
    def create_email(self, msg_dict):

        id = msg_dict.get('message_id', '')
        if id or id != '':
            email_from = msg_dict.get('email_from', '')
            date = msg_dict.get('date', '')

            "OK UC12"
            if (not self.env['email'].search([('message_id', '=', id)])):
                subject = msg_dict.get('subject', '')
                body = msg_dict.get('body', '')
                to = msg_dict.get('to', '')

                'Desactived auto commit for use transactions'
                self._cr.autocommit(False)
                try:

                    Mail = self.env['email'].create({
                        'subject': subject,
                        'message_id': id,
                        'date': date,
                        'email_from': email_from,
                        'body': body,
                        'to': to,
                    })

                    attach_model = self.env['email.attach']
                    list_attachments = msg_dict.get('attachments', '')

                    for item in list_attachments:
                        doc = base64.b64encode(item.content)
                        "UC03"
                        if ('.xml' in item.fname):
                            dic = self.env['electronic.doc'].convert_xml_to_dic(
                                doc)
                            doc_type = self.env['electronic.doc'].get_doc_type(dic)
                        else:
                            doc_type = 'OT'

                        attach_model.create({
                            'email_id': Mail.id,
                            'name': item.fname,
                            'doc': doc,
                            'doc_type': doc_type,
                        })

                    self._cr.commit()

                except Exception as e:
                    log.info('\n "Error al guardar email %s"\n', e)
                    self._cr.rollback()
            else:
                "UC11"
                log.info(
                    '\n "Message Id: %s enviado por: %s el dia %s ya existe en Odoo" \n',
                    id, email_from, date)