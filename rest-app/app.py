from flask import Flask, request, redirect, session, url_for
from uuid import uuid4
import requests
import urllib
import urlparse

endpoint = {
    'url': '',
    'client_id': 'my_web_app',
    'secret': '',  # TODO: assign secret to client in authorization server
    'scope':  'patient/*.read'
}

application = app = Flask(
    'wsgi',
    template_folder='templates',
    static_folder='static',
    static_url_path='/static'
)
app.debug = True
app.secret_key = 'khsathdnsthjre'

def getProvider (fhirServiceUrl):
    res = {
        'url': fhirServiceUrl,
        'oauth2': {
          'registration_uri': None,
          'authorize_uri': None,
          'token_uri': None
        }
    }

    headers = {'Accept': 'application/json'}
    url = fhirServiceUrl + '/metadata'
    r = requests.get(url, headers=headers)
    result = r.json()
    
    extensions = result['rest'][0]['security']['extension']
    
    for e in extensions:
        if e['url'] == "http://fhir-registry.smartplatforms.org/Profile/oauth-uris#register":
            res['oauth2']['registration_uri'] = e['valueUri']
        elif e['url'] == "http://fhir-registry.smartplatforms.org/Profile/oauth-uris#authorize":
            res['oauth2']['authorize_uri'] = e['valueUri']
        elif e['url'] == "http://fhir-registry.smartplatforms.org/Profile/oauth-uris#token":
            res['oauth2']['token_uri'] = e['valueUri']
        
    return res

@app.route('/fhir-app/launch.html')
def launch():
    iss = request.args.get('iss', '')
    fhirServiceUrl = request.args.get('fhirServiceUrl', '')
    launch = request.args.get('launch', '')
    endpoint['url'] = request.url.split('/fhir-app')[0] + url_for('index')
    state = str(uuid4())
    scope = ' '.join(( endpoint['scope'], ':'.join(( 'launch',launch )) ))
    url = ''
    params = {}

    if iss:
        # OAuth required
        provider = getProvider(iss)
        url = provider['oauth2']['authorize_uri']
        params = {
            'client_id': endpoint['client_id'],
            'response_type': "code",
            'scope': scope,
            'redirect_uri': endpoint['url'],
            'state': state
        }
    elif fhirServiceUrl:
        # no authorization required
        url = endpoint['url']
        params = {'state': state}

    url_parts = list(urlparse.urlparse(url))
    query = dict(urlparse.parse_qsl(url_parts[4]))
    query.update(params)
    url_parts[4] = urllib.urlencode(query)
    url = urlparse.urlunparse(url_parts)

    session[state] = {'provider': provider, 'client': endpoint}
    
    return redirect(url)

@app.route('/fhir-app/')
def index():
    code = request.args.get('code', '')
    state = request.args.get('state', '')

    endpoint = session[state]['client']
    provider = session[state]['provider']
    
    url = provider['oauth2']['token_uri']
    auth=(endpoint['client_id'], endpoint['secret'])
    params = {
      'code': code,
      'grant_type': 'authorization_code',
      'redirect_uri': endpoint['url'],
      'client_id': endpoint['client_id']
    }
    
    r = requests.get(url, params=params, auth=auth)
    res = r.json()

    # TODO: this is probably insecure since Flask supposedly makes the session visible in a client cookie
    # need to revisit...
    #session[state]['context'] = res
    
    url = session[state]['provider']['url'] + "/Patient/" + res['patient']
    auth=(res['token_type'], res['access_token'])
    # TODO: There may be a better way to specify non-basic authorization header in requests
    headers = {'Authorization': res['token_type'] + " " + res['access_token'], 'Accept': 'application/json'}
    r = requests.get(url, headers=headers)
    res = r.json()
    
    return res['name'][0]['given'][0] + " " + res['name'][0]['family'][0] + " " + res['birthDate']
    
if __name__ == '__main__':
    app.run(port=8000)
