# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

class FetchEmail(models.Model):
    _inherit = 'fetchmail.server'


    @api.constrains('user')
    def _constrains_user(self):
        #Probar validacion se dispara aun que exista solo un fetch email
        record = self.env['fetchmail.server'].search([('user','=',self.user),('id','!=',self.id)])
        if record:
           raise ValidationError('La direccion de correo {} no se puede utilizar ya que se configuro en otro Servidores de correo entrante'.format(self.user))

    
