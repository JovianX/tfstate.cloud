#!/usr/bin/python3
#
import flask
import flask_restful
import requests
import logging
import json
import os
import re
from flask import jsonify
from functools import wraps
from authentication import auth
from datetime import datetime
from google.cloud import firestore

app = flask.Flask(__name__)
api = flask_restful.Api(app)

db = firestore.Client(project='tfstatecloud')
mimetype = ""
@app.before_request
def log_request_info():
    headers = []
    for header in flask.request.headers:
        headers.append('%s = %s' % (header[0], header[1]))
    body = flask.request.get_data().decode('utf-8').split('\n')
    app.logger.debug(('%(method)s for %(url)s...\n'
                      '    Header -- %(headers)s\n'
                      '    Body -- %(body)s\n')
                     % {
        'method': flask.request.method,
        'url': flask.request.url,
        'headers': '\n    Header -- '.join(headers),
        'body': '\n           '.join(body),
    })
class Root(flask_restful.Resource):
    def get(self):
        state._log(flask.request.environ.get("HTTP_X_FORWARDED_FOR", flask.request.remote_addr), 'configs_get', {})
        resp = flask.Response(
        "\033[36;1m"
        "\n"
        " ▛▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▜\n"
        " ▌ TFstate☁️ CLOUD ▐ Store Terraform State \n"
        " ▙▃▃▃▃▃▃▃▃▃▃▃▃▃▃▃▃▟   and Terraform Locks in the cloud.\n"
        "\033[m"
        "\n"
        "- Create a new account and get the backend configuration \033[31;1m(replace with your email and password)\033[m:\n"
        f'curl https://{ flask.request.host} -F email=\033[31;1mmy@email.com\033[m -F password=\033[31;1mMyPassword\033[m -F action=create \n'
        "\n"
        "- Retrieve the backend configuration (default: -F action=get): \n"
        f'curl https://{ flask.request.host} -F email=\033[31;1mmy@email.com\033[m -F password=\033[31;1mMyPassword\033[m \n'
        "\n"
        "\n"
        "- Run `terraform init` and `terraform apply` after `backend.tf` backend configuration file is created. \n"
        "\n"
        ,mimetype='text/plain')
        resp.status_code = 200
        return resp

    def post(self):
        action          = flask.request.form.get("action") or "get"
        organization    = flask.request.form.get("organization") or re.sub(r'\W+', '', flask.request.form.get("email"))
        state._log( flask.request.environ.get("HTTP_X_FORWARDED_FOR",flask.request.remote_addr),
                    f'{action}',
                    flask.request.form.to_dict())

        match action:
            case "get":
                response_firebase = self.firebase()
                if not response_firebase.ok:
                    return flask.Response(
                        self.show_error("Login failed."),
                        mimetype = 'application/json',
                        status   = 405)
                firebase_jwt=response_firebase.json().get("idToken")
                account_secret_response = self.jovianx(action="getKey", jwt_token=firebase_jwt)
                if not account_secret_response.ok:
                    return flask.Response(
                        self.show_error("Failed to get API Secret."),
                        mimetype = 'application/json',
                        status   = 405)
                account_secret = account_secret_response.json().get("end_company_data").get("api_key")

            case "create":
                response_firebase = self.firebase()
                if response_firebase.ok:
                    firebase_jwt=response_firebase.json().get("idToken")
                    account_secret_response = self.jovianx(action="getKey", jwt_token=firebase_jwt)
                    if not account_secret_response.ok:
                        return flask.Response(
                            self.show_error("Failed to get API Secret."),
                            mimetype = 'application/json',
                            status   = 405)
                    account_secret = account_secret_response.json().get("end_company_data").get("api_key")
                    return flask.Response(
                    self.get_backend_tf(organization, account_secret)
                    ,mimetype='application/json', status = 200)

                if response_firebase.json().get("error").get("message") == "INVALID_PASSWORD":
                    return flask.Response(
                        self.show_error("This email already exists."),
                        mimetype = 'application/json',
                        status   = 405)

                if self.jovianx(organization=organization).status_code != 404:
                    return flask.Response(
                        self.show_error("Account name already exists."),
                        mimetype = 'application/json',
                        status   = 405)

                state._log( flask.request.environ.get("HTTP_X_FORWARDED_FOR",flask.request.remote_addr),
                    f'Creating new account {organization}',
                    flask.request.form.to_dict())

                response_firebase_signup = self.firebase(action="signupNewUser")
                if not response_firebase_signup.ok:
                    return flask.Response(
                        self.show_error("Failed to register user."),
                        mimetype = 'application/json',
                        status   = 405)

                firebase_jwt=response_firebase_signup.json().get("idToken")
                response_jovianx_signup = self.jovianx(action="register", organization=organization, jwt_token=firebase_jwt)
                if response_jovianx_signup.status_code != 200:
                    return flask.Response(
                        self.show_error("Failed to register account."),
                        mimetype = 'application/json',
                        status   = 405)

                account_secret_response = self.jovianx(action="getKey", jwt_token=firebase_jwt)
                if not account_secret_response.ok:
                    return flask.Response(
                        self.show_error("Failed to get API Secret."),
                        mimetype = 'application/json',
                        status   = 405)
                else:
                    account_secret = account_secret_response.json().get("end_company_data").get("api_key")

        return flask.Response(
        self.get_backend_tf(organization, account_secret)
        ,mimetype='application/json', status = 200)

    def firebase(self,action="verifyPassword"):
        firebase_url    = "https://www.googleapis.com/identitytoolkit/v3/relyingparty"
        key             = os.getenv("FIREBASE_KEY", "")
        tenant_id       = os.getenv("FIREBASE_TENANT_ID","")
        header          = {"content-type": "application/json"}
        email           = flask.request.form.get("email")
        password        = flask.request.form.get("password")
        data            = { "email":email,
                            "password":password,
                            "tenantId":tenant_id,
                            "returnSecureToken":"true"}
        url             = f'{firebase_url}/{action}?key={key}'
        response        = requests.post(url,headers=header,data=json.dumps(data))
        return response

    def jovianx(self, action="verifyAccount",organization=None,jwt_token=None):
        jovianx_vendor_id   = os.getenv("JOVIANX_VENDOR_ID","")
        base_url            = f'https://{jovianx_vendor_id}.jovianx.app/api/v1'

        match action:
            case "verifyAccount":
                url            = f'{base_url}/application/endpoints?vendor_company={jovianx_vendor_id}&end_company={organization}'
                header              = {"content-type": "application/json"}
                response       = requests.get(url,headers=header)

            case "register":
                url            = f'{base_url}/end-company/user-management/members/register'
                header         = {  "content-type": "application/json",
                                    "Jx-Vendor": jovianx_vendor_id,
                                    "Authorization": "Bearer " + jwt_token}
                data = {"firstname":"first",
                        "lastname":"last",
                        "end_company":organization,
                        "end_company_display_name":organization,
                        "additional_information":[
                            {"name":"agreeToTermsOfUse","value":{
                                "name":"true","display":"true"},
                                "label":""}]}
                response       = requests.post(url,headers=header,data=json.dumps(data))
                if not response.ok:
                    return response
                url            = f'{base_url}/signup-flow/save-launch-settings'
                data = {"admin_email":flask.request.form.get("email"),
                        "admin_password":flask.request.form.get("password"),
                        "settings":
                            {"launchSecondNodeComponent":"true"}
                            ,"blueprint_version":"1.0.0"}
                response       = requests.post(url,headers=header,data=json.dumps(data))
            case "getKey":
                url            = f'{base_url}/end_company_meta'
                header         = {  "content-type": "application/json",
                                    "Jx-Vendor": jovianx_vendor_id,
                                    "Authorization": "Bearer " + jwt_token}
                response       = requests.get(url,headers=header)
        return response

    def get_backend_tf(self,account_id, account_secret):
        backend_tf = (
        "# \033[36;1m \n"
        '# Terraform state managed at https://tfstate.cloud \033[33;1m \n'
        '# Save to file `backend.tf` in your terraform configuration directory. \033[m \n'
        "# \n"
        f'# Account_ID={account_id}\n'
        f'# Account_Secret={account_secret}\n'
        "# \n"
        'terraform {\n'
        'backend "http" {\n'
        f'    username       = "{account_id}"\n'
        f'    password       = "{account_secret}"\n'
        '    address        = "https://get.tfstate.cloud/terraform_state/space1"\n'
        '    lock_address   = "https://get.tfstate.cloud/terraform_lock/space1"\n'
        '    unlock_address = "https://get.tfstate.cloud/terraform_lock/space1"\n'
        '    lock_method    = "PUT"\n'
        '    unlock_method  = "DELETE"\n'
        '    }\n'
        '}\n'
        )
        return backend_tf

    def show_error(slef, error):
        return (
            "#  \n"
            f'# 🌧️\033[31;1m  {error} \033[m\n'
            "# \n"
            )

class StateStore(object):
    def __init__(self, path):
        self.path = path
        os.makedirs(self.path, exist_ok=True)

    def _log(self, id, op, data):
        if type(data) is not dict:
            data = json.loads(data)
        doc_ref = db.collection("logs").document(id)
        doc_ref.set({
            datetime.now().strftime("%m/%d/%Y, %H:%M:%S"): {
                'call': op,
                'source': flask.request.environ.get("HTTP_X_FORWARDED_FOR", flask.request.remote_addr),
                'data': data
            }
        }, merge=True)

    def get(self, id):
        doc_ref = db.collection("states").document(id)
        doc = doc_ref.get()
        if doc.exists:
            self._log(id, 'state_read', {})
            return doc.to_dict()
        return None

    def put(self, id, info):
        data = json.dumps(info, indent=4, sort_keys=True)
        doc_ref = db.collection("states").document(id)
        doc_ref.set(info)
        self._log(id, 'state_write', data)

    def lock(self, id, info):
        doc_ref = db.collection("locks").document(id)
        doc = doc_ref.get()
        if doc.exists:
            return False, doc.to_dict()
        doc_ref = db.collection("locks").document(id)
        doc_ref.set(info)
        data = json.dumps(info, indent=4, sort_keys=True)
        self._log(id, 'lock', data)
        return True, {}

    def unlock(self, id, info):
        doc_ref = db.collection("locks").document(id)
        doc = doc_ref.get()
        if doc.exists:
            db.collection("locks").document(id).delete()
            self._log(id, 'unlock', json.dumps(info, indent=4, sort_keys=True))
            return True
        return False

state = StateStore('stateserver')

class TerraformState(flask_restful.Resource):
    @auth.login_required
    def get(self, tf_id):
        tf_id = flask.request.authorization["username"] + "--" + re.sub(r'[\W_]+', '', tf_id)
        s = state.get(tf_id)
        if not s:
            flask.abort(404)
        return s

    @auth.login_required
    def post(self, tf_id):
        tf_id = flask.request.authorization["username"] + "--" + re.sub(r'[\W_]+', '', tf_id)
        s = state.put(tf_id, flask.request.json)
        return {}

class TerraformLock(flask_restful.Resource):
    @auth.login_required
    def put(self, tf_id):
        tf_id = flask.request.authorization["username"] + "--" + re.sub(r'[\W_]+', '', tf_id)
        success, info = state.lock(tf_id, flask.request.json)
        if not success:
            flask.abort(423, info)
        return info

    @auth.login_required
    def delete(self, tf_id):
        tf_id = flask.request.authorization["username"] + "--" + re.sub(r'[\W_]+', '', tf_id)
        if not state.unlock(tf_id, flask.request.json):
            flask.abort(404)
        return {}

api.add_resource(Root, '/')
api.add_resource(TerraformState,'/terraform_state/<string:tf_id>')
api.add_resource(TerraformLock, '/terraform_lock/<string:tf_id>')

if __name__ == '__main__':
    app.log = logging.getLogger('werkzeug')
    app.log.setLevel(logging.DEBUG)
    app.run(host='0.0.0.0', debug=True)