#   TO DO
#    [ ] dynamic handlers for the various FHIR REST call variants and arguments (a la JS client)
#    [ ] add in Pascal's parser for FHIR profiles
#    [ ] ability to dynamically register the app if not present in the auth server
#    [ ] exception handlers and assert unit testing
#    [ ] documentation and tutorial

import urllib
import urlparse
import requests
from uuid import uuid4
from generate_api import augment

class FHIRClient():

    def __init__(self, state=None, app_id=None, app_url=None, api_base=None,
                 scope=None, launch_token=None, security_mode=None, secret=''):

        if state:
            self._settings = state
        else:
            assert app_id and app_url and api_base and scope and launch_token
            
            self._settings = {
                'client': {
                    'app_id': app_id,
                    'app_url': app_url,
                    'scope': ' '.join(( scope, ':'.join(( 'launch',launch_token)) )),
                    'uuid': str(uuid4())
                }, 
                'provider': {
                    'oauth2': {
                      'registration_uri': None,
                      'authorize_uri': None,
                      'token_uri': None
                    },
                    'api_base': api_base,
                    'authorize_url': '',
                    'security_mode': security_mode,
                    'access_token_type': '',
                    'access_token': '',
                    'pid': '',
                    'types': []
                }
            }
            
            self._loadProvider()

        self._secret = secret
            
        types = self._settings['provider']['types']
        augment(self, types)
        
    def _loadProvider (self):
        c = self._settings['client']
        p = self._settings['provider']

        headers = {'Accept': 'application/json'}
        url = p['api_base'] + '/metadata'
        r = requests.get(url, headers=headers)
        result = r.json()
        
        for r in result['rest'][0]['resource']:
            if r['type'] != 'Patient':    # TO DO: get rid of this
                p['types'].append(r['type'])
        
        extensions = result['rest'][0]['security']['extension']
        
        for e in extensions:
            if e['url'] == "http://fhir-registry.smartplatforms.org/Profile/oauth-uris#register":
                p['oauth2']['registration_uri'] = e['valueUri']
            elif e['url'] == "http://fhir-registry.smartplatforms.org/Profile/oauth-uris#authorize":
                p['oauth2']['authorize_uri'] = e['valueUri']
            elif e['url'] == "http://fhir-registry.smartplatforms.org/Profile/oauth-uris#token":
                p['oauth2']['token_uri'] = e['valueUri']

        if p['security_mode'] and p['security_mode'] == 'oauth':
            url = p['oauth2']['authorize_uri']
            params = {
                'client_id': c['app_id'],
                'response_type': "code",
                'scope': c['scope'],
                'redirect_uri': c['app_url'],
                'state': c['uuid']
            }
            
            url_parts = list(urlparse.urlparse(url))
            query = dict(urlparse.parse_qsl(url_parts[4]))
            query.update(params)
            url_parts[4] = urllib.urlencode(query)
            p['authorize_url'] = urlparse.urlunparse(url_parts)

    @property
    def authorize_url(self):
        return self._settings['provider']['authorize_url']
        
    @property
    def state(self):
        c = self._settings['client']
        s = self._settings
        return c['uuid'], s

    @property
    def access_token(self):
        p = self._settings['provider']
        return p['access_token']
        
    @property
    def patient_id(self):
        return self._settings['provider']['pid']
        
        
    def update_access_token (self, authorization_code):
        c = self._settings['client']
        p = self._settings['provider']
        url = p['oauth2']['token_uri']
        auth = (c['app_id'], self._secret)
        params = {
          'code': authorization_code,
          'grant_type': 'authorization_code',
          'redirect_uri': c['app_url'],
          'client_id': c['app_id']
        }
        
        r = requests.get(url, params=params, auth=auth)
        res = r.json()

        p['access_token_type'] = res['token_type']
        p['access_token'] = res['access_token']
        p['pid'] = res['patient']

    # TO DO: generate this convenience method on the fly
    def Patient (self):
        p = self._settings['provider']
        url = p['api_base'] + "/Patient/" + self.patient_id

        # TODO: There may be a better way to specify non-basic authorization header in requests
        headers = {
            'Authorization': ' '.join((p['access_token_type'], p['access_token'])),
            'Accept': 'application/json'
        }

        r = requests.get(url, headers=headers)
        return r.json()
       
    def get(self, type):
        p = self._settings['provider']
        url = p['api_base'] + "/" + type + "/_search?patient:Patient=" + p['pid']

        # TODO: There may be a better way to specify non-basic authorization header in requests
        headers = {
            'Authorization': ' '.join((p['access_token_type'], p['access_token'])),
            'Accept': 'application/json'
        }

        r = requests.get(url, headers=headers)
        dt = r.json()
        res = []
        for e in dt['entry']:
            res.append(e['content'])
        return res
