# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import Response, request
import json

import logging
_logging = _logger = logging.getLogger(__name__)

class L10ncrEinvoice(http.Controller):
    @http.route('/api/callbackurl/v43', auth='public',methods=['POST'], type='json',website=True)
    def callbackpost(self, **kw):
        data_str = request.httprequest.data

        data_json = json.loads( data_str.decode() )
        clave = data_json.get('clave')
        estado = data_json.get('ind-estado')
        fe_xml_hacienda = data_json.get('respuesta-xml')
        fe_name_xml_hacienda = "MH-" + str( clave ) + ".xml"
        
        _logging.info("    Respuesta Hacienda para Clave: {0}: {1}".format( clave, estado ) )

        account_move = http.request.env['account.move'].sudo()
        move_id = account_move.search([('fe_clave','=', clave)])
        if move_id:
            move_id.write({
                'fe_name_xml_hacienda': fe_name_xml_hacienda,
                'fe_xml_hacienda': fe_xml_hacienda,
                'fe_fromhacienda_json': json.dumps( data_json ),
                'fe_server_state': estado,
            })
        
        Response.status = "200"
        return
        