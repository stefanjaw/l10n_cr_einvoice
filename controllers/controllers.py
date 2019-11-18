# -*- coding: utf-8 -*-
from odoo import http

# class L10nCrEinvoice/(http.Controller):
#     @http.route('/l10n_cr_einvoice//l10n_cr_einvoice//', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/l10n_cr_einvoice//l10n_cr_einvoice//objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('l10n_cr_einvoice/.listing', {
#             'root': '/l10n_cr_einvoice//l10n_cr_einvoice/',
#             'objects': http.request.env['l10n_cr_einvoice/.l10n_cr_einvoice/'].search([]),
#         })

#     @http.route('/l10n_cr_einvoice//l10n_cr_einvoice//objects/<model("l10n_cr_einvoice/.l10n_cr_einvoice/"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('l10n_cr_einvoice/.object', {
#             'object': obj
#         })