# TO DO
#    [ ] encrypt the state to protect app secrets
#    [ ] add logic to trim the session object when it gets too big before werkzeug crashes instead of
#        clearing the session object on each run
#    [ ] enable client secret between auth server and sample app
#    [ ] add intermediary 'authorize' page to handle the transition to final page
#    [ ] add configuration options and suggestions for session storage mechanism

from flask import Flask, request, redirect, session, url_for
from fhirclient import Client as FHIRClient

settings = {
    'app_id': 'my_web_app',
    'scope':  'patient/*.read',
    'secret': ''
}

application = app = Flask('wsgi')
app.debug = True
app.secret_key = 'khsathdnsthjre'  # CHANGE ME

@app.route('/fhir-app/launch.html')
def launch():
    iss = request.args.get('iss', '')
    fhirServiceUrl = request.args.get('fhirServiceUrl', '')

    if iss:
        api_base = iss
        security_mode = 'oauth'
    elif fhirServiceUrl:
        api_base = fhirServiceUrl
        security_mode = None
    
    client = FHIRClient(app_id=settings['app_id'], 
                 app_url=request.url.split('/fhir-app')[0] + url_for('authorize'),
                 api_base=api_base,
                 scope=settings['scope'],
                 launch_token=request.args.get('launch', ''), 
                 security_mode=security_mode,
                 secret=settings['secret'])

    session['client_state'] = client.state
    
    return redirect(client.authorize_url)

@app.route('/fhir-app/authorize.html')
def authorize():
    client = FHIRClient(state=session['client_state'], secret=settings['secret'])
    client.update_access_token(request.args.get('code', ''))
    session['client_state'] = client.state
    return redirect(url_for('index'))
    
@app.route('/fhir-app/')
def index():
    client = FHIRClient(state=session['client_state'], secret=settings['secret'])
    patient = client.Patient()
    prescriptions = client.MedicationPrescription()
    
    out = """<!DOCTYPE html>
        <html>
          <head><title>Sample REST App</title></head>
          <body>
    """
    
    h = ' '.join((patient['name'][0]['given'][0], patient['name'][0]['family'][0], patient['birthDate']))
    out += "<h1>Medications for <span id='name'>%s</span></h1>\n" % h
    out += "<ul id='med_list'>\n"
    
    # medication may only be present as a reference in the prescription -> in a complete implementation
    # would need to implement a more flexible/adaptive mechanism for retrieval
    
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
