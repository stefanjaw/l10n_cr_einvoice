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
                mail_to = msg_dict.get('to', '')
                if '<' in mail_to and '>' in mail_to:
                    result = re.search('<(.*)>', mail_to)
                    mail_to = result.group(1)

                mail_to = mail_to.replace(" ", "").split(",")
                log.info("=====mail_to===={}".format(mail_to))
                
                company = False
                for email1 in mail_to:
                    try:
                        email1_domain = email1.split("@")[1]
                    except:
                        continue

                    company = self.env['res.company'].search([('fecth_server.user','ilike', email1_domain )], limit=1)
                    if company:
                        break

                self.env['email'].create_email(msg_dict,company)
                docs = self.order_documents(msg_dict.get('attachments', ''))
                self.env['electronic.doc'].automatic_bill_creation(docs,company)

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
