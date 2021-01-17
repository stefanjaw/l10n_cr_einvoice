from odoo import models, fields, api
from lxml.etree import Element, fromstring, parse, tostring, XMLParser
from datetime import datetime,timezone
from odoo.exceptions import ValidationError
import lxml.etree as ET
import xmltodict
import logging
import base64
import logging

log = logging.getLogger(__name__)

class wizardAgregarContabilidad(models.TransientModel):
    _name='wizard.agregar.contabilidad'
    
    opciones = fields.Selection([
           ('1', 'Crear nueva factura'),
           ('2', 'Asociar a una factura existente'),
    ], string="Acción",default = '1'
    )
    invoice_id = fields.Many2one('account.move', string='invoice',)
    company_id = fields.Many2one(
        'res.company',
        'Company',
         default=lambda self: self.env.company.id,
    )
    def agregar(self):
        doc = self.env['electronic.doc'].search([("id","=",self._context['doc'])])
        if doc.company_id != self.company_id:
            raise ValidationError("Este documento pertenece a la compañía {} si desea agregarlo a contabilidad por favor cámbiese a esta".format(doc.company_id.name))
        if self.opciones == '1':
                xml = self._context['xml']
                bill_dict = self.env['electronic.doc'].convert_xml_to_dic(xml)
                bill_type =  self.env['electronic.doc'].get_doc_type(bill_dict)
                
                identificacion =  self.env['electronic.doc'].get_provider_identification(bill_dict, bill_type)
                
                contacto =  self.env['res.partner'].search([('vat','=',identificacion)])
                if len(contacto)>1:
                    contacto = contacto[0]

                if not contacto:
                    nombre = self.env['electronic.doc'].get_provider(bill_dict,bill_type)
                    contacto = self.env['res.partner'].create({
                        'vat':identificacion,
                        'name': nombre,
                    })

                root_xml = fromstring(base64.b64decode(xml))
                ds = "http://www.w3.org/2000/09/xmldsig#"
                xades = "http://uri.etsi.org/01903/v1.3.2#"
                ns2 = {"ds": ds, "xades": xades}
                signature = root_xml.xpath("//ds:Signature", namespaces=ns2)[0]
                namespace = self.env['electronic.doc']._get_namespace(root_xml)

                lineasDetalle = root_xml.xpath(
                    "xmlns:DetalleServicio/xmlns:LineaDetalle", namespaces=namespace)

                
                invoice_lines = []   
                
                account_id = self.env['account.account'].search([("code","=","0-511301")])
                for linea in doc.line_ids:
                    if linea.is_selected:
                        taxes = []
                        for tax in linea.tax_ids:
                            taxes.append(tax.id)

                        tax_ids = [(6,0,taxes)]        
                        new_line =  [0, 0, {'name': linea.name,
                                            'tax_ids': tax_ids,
                                            'account_id': linea.account_id.id,
                                            'quantity': linea.quantity,
                                            'price_unit':linea.price_unit,
                                           }]
                        invoice_lines.append(new_line)
                    
                if doc.doc_type == 'FE' or doc.doc_type == 'TE':
                     doc_type = 'in_invoice'
                elif doc.doc_type == 'NC':
                     doc_type = 'in_refund'

                record = self.env['account.move'].create({
                    'partner_id': contacto.id,
                    'currency_id':doc.currency_id.id,
                    'ref': 'Factura consecutivo : {}'.format(doc.consecutivo),
                    'type' : doc_type,
                    'invoice_date':doc.date,
                    'invoice_line_ids':invoice_lines,
                    'electronic_doc_id':doc.id,
                    'company_id':doc.company_id,
                })
                
                doc.update({'invoice_id':record.id})
                
        elif self.opciones == '2':
             self.invoice_id.update({
                    'electronic_doc_id':doc.id,
                    'ref': 'Factura consecutivo : {}'.format(doc.consecutivo),
                })
             doc.update({'invoice_id':self.invoice_id})
        
        
        doc.update({
            'state':'accounting',
        })
        
        
        
