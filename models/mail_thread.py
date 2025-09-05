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
        _logger.info(f"DEF20 message_new self: {self}" )
        "OK UC01"
        "(['to', 'message_type', 'date', 'email_from', 'message_id', 'attachments', 'cc', 'author_id', 'from', 'subject', 'body'])"
        _logger.info(f"DEF23 self._context: {self._context}" )
        data = {}
        if isinstance(custom_values, dict):
            data = custom_values.copy()
        model = self._context.get('thread_model') or self._name
        RecordModel = self.env[model]
        fields = RecordModel.fields_get()
        name_field = RecordModel._rec_name or 'name'
        fetchmail_server_int = self._context.get('default_fetchmail_server_id')
        company = self.env['res.company'].sudo().search([('fecth_server.id','=', fetchmail_server_int)])
        _logger.info(f"DEF32 company_id: {company}\n")
        
        if name_field in fields and not data.get('name'):
            data[name_field] = msg_dict.get('subject', '')

        if data.get('company_id'):
            data['company_id'] = company.id
        _logger.info(f"DEF40 data: {data}")
        if msg_dict:
            if msg_dict.get('message_id', ''):
                mail_to = msg_dict.get('to', '')
                if mail_to:
                    mail_to = mail_to.lower()
                
                _logger.info("    =====mail_to==== {}".format(mail_to))

                company_id = False
                company_ids = self.env['res.company'].search([])
                for company_id in company_ids:
                    if company_id.fe_email in mail_to:
                        _logger.info(f"    Found company_id: {company_id} for: { company_id.fe_email }")
                        break
                
                mail_to_lst = mail_to.split(",")
                _logger.info(f"DEF46 company: {company_id}")
                self.env['email'].create_email(msg_dict,company_id)
                docs = self.order_documents(msg_dict.get('attachments', ''), company_id)
                
                self.env['electronic.doc'].automatic_bill_creation(docs,company_id)
        
        return RecordModel.create(data)

    def order_documents(self, attachments, company_id=False):
        _logger.info(f"DEF65 order_documents self: {self}")
        electronic_doc = self.env['electronic.doc']
        bills = []
        acceptance = []
        others = []
        _logger.info(f"DEF70 company_id: {company_id}")
        if company_id:
            pass
        else:
            msg1 = f"74 No company_id found: {company_id} for self: {self}"
            raise ValidationError( msg1 )
        
        for item in attachments:
            if ('.xml' in str(item.fname).lower()):
                item_content = item.content
                if type(item_content) == str:
                    item_content = item_content.encode("utf-8")
                    
                doc = base64.b64encode(item_content)
                type_dest = "dict"
                try:
                    dic = self.env['electronic.doc'].convert_xml_to_other( doc,type_dest = type_dest, company_id=company_id )
                except Exception as e:
                    _logger.info(f"    88 Error: Can't convert XML {item.fname} to:{type_dest} - Content: \n{item.content}\nError: {e}")
                    continue
                _logger.info(f"    ==== dic converted ====\ndic: {dic}")
                doc_type = electronic_doc.get_doc_type(dic)
                _logger.info(f"    ==== doc_type: {doc_type} =====")
                if (doc_type == 'FE' or doc_type == 'TE' or doc_type == 'NC'):
                    bills.append(item)

                elif (doc_type == 'MH'):
                    acceptance.append(item)
            else:
                others.append(item)

        doc_tuple = (bills, acceptance, others)
        _logger.info(f"DEF102 doc_tuple")
        
        return doc_tuple
