from odoo import api, exceptions, fields, models, _
from odoo.exceptions import ValidationError
from lxml.etree import Element, fromstring, parse, tostring, XMLParser
import lxml.etree as ET
import xmltodict
import logging
import base64

from io import BytesIO

log = logging.getLogger(__name__)

class attachments(models.Model):
    _name = 'email.attach'
    email_id = fields.Many2one(comodel_name='email',ondelete='cascade',required = True)
    name = fields.Char()
    doc = fields.Binary(string="Attachment")
    doc_type = fields.Selection(string='Tipo',
                                selection=[
                                    ('TE', 'Tiquete Electrónico'),
                                    ('FE', 'Factura Electrónica'),
                                    ('NC', 'Nota Crédito Electrónica'),
                                    ('MH', 'Aceptación Ministerio Hacienda'),
                                    ('OT', 'Otro'),
                                ])
