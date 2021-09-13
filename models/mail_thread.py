from odoo import api, exceptions, fields, models, _
from odoo.exceptions import ValidationError
from lxml.etree import Element, fromstring, parse, tostring, XMLParser
import lxml.etree as ET
import xmltodict
import logging
import base64
import re

from io import BytesIO

log = _logger = logging.getLogger(__name__)

class mailThread(models.AbstractModel):

    _inherit = 'mail.thread'

    @api.model
    def message_new(self, msg_dict, custom_values=None):
        "OK UC01"
        "(['to', 'message_type', 'date', 'email_from', 'message_id', 'attachments', 'cc', 'author_id', 'from', 'subject', 'body'])"
        data = {}
        if isinstance(custom_values, dict):
            data = custom_values.copy()
        model = self._context.get('thread_model') or self._name
        RecordModel = self.env[model]
        fields = RecordModel.fields_get()
        _logger.info("28DEB====FIELDS: \n%s", fields)
        name_field = RecordModel._rec_name or 'name'
        fetchmail_server_int = self._context.get('default_fetchmail_server_id')
        company = self.env['res.company'].sudo().search([('fecth_server.id','=', fetchmail_server_int)])
        if name_field in fields and not data.get('name'):
            data[name_field] = msg_dict.get('subject', '')
        if msg_dict:
            if msg_dict.get('message_id', ''):
                mail_to = msg_dict.get('to', '')
                log.info("=====mail_to===={}".format(mail_to))
                
                mail_to_lst = mail_to.split(",")

                self.env['email'].create_email(msg_dict,company)
                docs = self.order_documents(msg_dict.get('attachments', ''))
                self.env['electronic.doc'].automatic_bill_creation(docs,company)
        _logger.info("43DEB====DATA: \n%s", data)
        return RecordModel.create(data)

    def order_documents(self, attachments):
        electronic_doc = self.env['electronic.doc']
        bills = []
        acceptance = []
        others = []

        for item in attachments:
            if ('.xml' in str(item.fname).lower()):
                doc = base64.b64encode(item.content)
                dic = self.env['electronic.doc'].convert_xml_to_dic(doc)
                doc_type = electronic_doc.get_doc_type(dic)
                if (doc_type == 'FE' or doc_type == 'TE' or doc_type == 'NC'):
                    bills.append(item)

                elif (doc_type == 'MH'):
                    acceptance.append(item)
            else:
                others.append(item)

        doc_tuple = (bills, acceptance, others)
        return doc_tuple
