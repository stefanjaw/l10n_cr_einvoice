from odoo import api, exceptions, fields, models, _
from odoo.exceptions import ValidationError
from lxml.etree import Element, fromstring, parse, tostring, XMLParser
import lxml.etree as ET
import xmltodict
import logging
import base64
import re

from io import BytesIO

log = logging.getLogger(__name__)

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
        name_field = RecordModel._rec_name or 'name'
        if name_field in fields and not data.get('name'):
            data[name_field] = msg_dict.get('subject', '')
        if msg_dict:
            if msg_dict.get('message_id', ''):
                self.env['email'].create_email(msg_dict)
                docs = self.order_documents(msg_dict.get('attachments', ''))
                mail_to = msg_dict.get('to', '') 
                m = re.search('<(.+?)>', mail_to)
                if m:
                    email = m.group(1)
                log.info(email)
                fetch = self.env['fetchmail.server'].search([('user','=',email)])
                company = self.env['res.company'].search([('fecth_server','=',fetch)])
                self.env['electronic.doc'].automatic_bill_creation(docs,company)

        return RecordModel.create(data)

    def order_documents(self, attachments):
        electronic_doc = self.env['electronic.doc']
        bills = []
        acceptance = []
        others = []

        for item in attachments:
            if ('.xml' in item.fname):
                doc = base64.b64encode(item.content)
                dic = self.env['electronic.doc'].convert_xml_to_dic(doc)
                doc_type = electronic_doc.get_doc_type(dic)
                if (doc_type == 'FE' or doc_type == 'TE'):
                    bills.append(item)

                elif (doc_type == 'MH'):
                    acceptance.append(item)
            else:
                others.append(item)

        doc_tuple = (bills, acceptance, others)
        return doc_tuple
