# TO DO
#    [ ] encrypt the state to protect app secrets
#    [ ] add logic to trim the session object when it gets too big before werkzeug crashes instead of
#        clearing the session object on each run
#    [ ] enable client secret between auth server and sa

import pickle
from flask import Flask, request, redirect, session, url_for
from client import FHIRClient

settings = {
    'app_id': 'my_web_app',
    'scope':  'patient/*.read',
    'security_mode': None,
    'secret': ''
}

application = app = Flask('wsgi')
app.debug = True
app.secret_key = 'khsathdnsthjre'  # CHANGE ME

@app.route('/fhir-app/launch.html')
def launch():
    s = settings
    api_base = None
    security_mode = None
    iss = request.args.get('iss', '')
    fhirServiceUrl = request.args.get('fhirServiceUrl', '')
    launch_token = request.args.get('launch', '')
    app_url = request.url.split('/fhir-app')[0] + url_for('index')
    
    if iss:
        # OAuth required
        api_base = iss
        security_mode = 'oauth'
    elif fhirServiceUrl:
        # no authorization required
        api_base = fhirServiceUrl
    
    client = FHIRClient (app_id=s['app_id'], app_url=app_url, api_base=api_base,
                 scope=s['scope'], launch_token=launch_token, 
                 security_mode=security_mode, secret=s['secret'])

    session.clear()
    state_id, state = client.state
    session[state_id] = state
    
    if client.authorize_url:
        return redirect(client.authorize_url)
    else:
        return redirect(app_url + "?state=" + state_id)

@app.route('/fhir-app/')
def index():
    authorization_code = request.args.get('code', '')
    state_id = request.args.get('state', '')

    client = FHIRClient (state=session[state_id])
    if not client.access_token and authorization_code:
        client.update_access_token (authorization_code)
        
    session.clear()
    state_id, state = client.state
    session[state_id] = state

    out = """<!DOCTYPE html>
        <html>
          <head><title>Sample REST App</title></head>
          <body>
    """
    
    patient = client.Patient()
    name = patient['name'][0]['given'][0] + " " + patient['name'][0]['family'][0] + " " + patient['birthDate']
    out += "<h1>Medications for <span id='name'>%s</span></h1>\n" % name
    out += "<ul id='med_list'>\n"
    
    prescriptions = client.MedicationPrescription()
    
    for prescription in prescriptions:
        meds = prescription['contained']
        for med in meds:
            out += "<li>%s</li>" % med['name']
    
    out += """
        </ul>
       </body>
      </html>"""
    
    return out
    
if __name__ == '__main__':
    app.run(port=8000)
