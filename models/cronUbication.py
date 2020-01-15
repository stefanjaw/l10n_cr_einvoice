from odoo import models, fields, api
import json
import requests
import logging

log = logging.getLogger(__name__)

class cronUbication(models.AbstractModel):
    _name = "cron.ubication"
    
    def update_ubication(self):
        self._update_provincia()
        self._update_canton()
        self._update_distrito()
        self._update_barrio()
        
    def _update_provincia(self):
        url = self.env.user.company_id.fe_url_server+'state'
        header = {'Content-Type':'application/json'}
        r = requests.get(url, headers = header, data=json.dumps({}))
        log.info('---> %s request',r)
        data = r.json()
        log.info('---> %s',data)

        if not data.get('result').get('error'):
            for i in data['result']:
                model = self.env['res.country.state']
                var = model.search([('code','=',i)])
                if var:
                    if var.name != data['result'][i]['name']:
                        var.update({'name':data['result'][i]['name']})
                    if var.fe_code != data['result'][i]['fe_code']:
                        var.update({'fe_code':data['result'][i]['fe_code']})
                        
                elif not var:
                    country_id = self.env['res.country'].search([('code','=',data['result'][i]['country_code'])])
                    if country_id:
                        model.create({'code':i,'name':data['result'][i]['name'],'fe_code':data['result'][i]['fe_code'],'country_id':country_id.id})
                    else:
                        log.info('---> no se encuentra el pais id : %s',data['result'][i]['country_code'])
                        
        else:
            log.info('---> error state %s',data)            
            '''if data.get('result').get('error'):
               self.write_chatter(data['result']['error'])'''
               
               
    def _update_canton(self):
        states = self.env['res.country.state'].search([("country_id.code","=","CR")])
        for st in states:
            url = self.env.user.company_id.fe_url_server+'canton/{0}'.format(st.code)
            header = {'Content-Type':'application/json'}
            r = requests.get(url, headers = header, data=json.dumps({}))

            data = r.json()
            log.info('---> %s',data)

            if not data.get('result').get('error'):
                for i in data['result']:
                    model = self.env['client.canton']
                    var = model.search([('code','=',i),('state_id','=',st.id)])
                    if var:
                        log.info('--> indice %s',i)
                        if var.name != data['result'][i]['name']:
                            var.update({'name':data['result'][i]['name']})                            
                    elif not var:
                        model.create({'code':i,'name':data['result'][i]['name'],'state_id':st.id})
            else:
                log.info('---> error canton %s',data)            
                '''if data.get('result').get('error'):
                   self.write_chatter(data['result']['error'])'''
                   
    def _update_distrito(self):
        states = self.env['res.country.state'].search([("country_id.code","=","CR")])
        for st in states:
            cantones = self.env['client.canton'].search([("state_id","=",st.id)])
            for can in cantones:
                url = self.env.user.company_id.fe_url_server+'distrito/{0}/{1}'.format(can.code,st.code)
                header = {'Content-Type':'application/json'}
                r = requests.get(url, headers = header, data=json.dumps({}))

                data = r.json()
                log.info('---> %s',data)

                if not data.get('result').get('error'):
                    for i in data['result']:
                        model = self.env['client.district']
                        var = model.search([('code','=',i),('canton_id','=',can.id)])
                        if var:
                            log.info('--> indice %s',i)
                            if var.name != data['result'][i]['name']:
                                var.update({'name':data['result'][i]['name']})                            
                        elif not var:
                            model.create({'code':i,'name':data['result'][i]['name'],'canton_id':can.id})
                else:
                    log.info('---> error canton %s',data)            
                    '''if data.get('result').get('error'):
                       self.write_chatter(data['result']['error'])'''
                       
    def _update_barrio(self):
        states = self.env['res.country.state'].search([("country_id.code","=","CR")])
        for st in states:
            cantones = self.env['client.canton'].search([("state_id","=",st.id)])
            for can in cantones:
                distritos = self.env['client.district'].search([("canton_id","=",can.id)])
                for dis in distritos:
                    url = self.env.user.company_id.fe_url_server+'barrio/{0}/{1}/{2}'.format(dis.code,can.code,st.code)
                    header = {'Content-Type':'application/json'}
                    r = requests.get(url, headers = header, data=json.dumps({}))

                    data = r.json()
                    log.info('---> %s',data)

                    if not data.get('result').get('error'):
                        for i in data['result']:
                            model = self.env['client.neighborhood']
                            var = model.search([('code','=',i),('district_id','=',dis.id)])
                            if var:
                                log.info('--> indice %s',i)
                                if var.name != data['result'][i]['name']:
                                    var.update({'name':data['result'][i]['name']})                            
                            elif not var:
                                model.create({'code':i,'name':data['result'][i]['name'],'district_id':dis.id})
                    else:
                        log.info('---> error canton %s',data)            
                        '''if data.get('result').get('error'):
                           self.write_chatter(data['result']['error'])'''    