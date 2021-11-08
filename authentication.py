from flask_httpauth import HTTPBasicAuth
import requests

auth = HTTPBasicAuth()

@auth.verify_password
def verify(username, password):
    url = 'https://tfstate.jovianx.app/api/v1/track_event'
    headers = {"Jx-Vendor": "tfstate"}
    auth=(username, password)
    response = requests.post(url,headers=headers,auth=auth)
    if response.status_code == 400:
        return True
    return False
