from .base_bank import BaseBankAPI
from backend.api.mock_helper import MockHelper

import requests
import json
import csv
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv() # private data setup from .env file 

class ComdirectAPI(BaseBankAPI):
    def __init__(self, username, pw, depot_name, session_id, request_id):
        super().__init__(name=depot_name)

        self.base_url = "https://api.comdirect.de"
        self.oauth_url = f"{self.base_url}/oauth/token"
        self.session_url = f"{self.base_url}/api/session/clients/user/v1/sessions"
        self.client_id = os.getenv("CLIENT_ID")
        self.client_secret = os.getenv("CLIENT_SECRET")

        self.init_token = None
        self.final_token = None
        self.depot_id = None

        self.username = username
        self.pw = pw
        self.session_id = session_id
        self.request_id = request_id

    def authenticate(self):

        if self.use_mock:
            print(f"{self.name}: [{self.session_id}]: Authentifizierung übersprungen (MOCK)")
            self.depot_id = self.mock.load_mock_depot_id()
        else: 
            # 1. get initial token
            self._collect_initial_token()

            # 2. get session info needed for authentication
            session_data = self._get_session_info()

            # 3. call for tan authentication (Photo Push Tan)
            challenge = self._raise_challenge_to_validate_tan(session_data)
            print("🔐 Activate photo TAN")
            input("↵ Press Enter after activating the TAN: ...")
            
            # tan = input() # if we want to give a TAN number and not using photo tan

            # 4. activate tan
            self._activate_tan(session_data, challenge)

            # 5. check authentication and retrieve secondary token for full comdirect access
            try:
                self._collect_final_token()
                print("authentication fully completed")

            except requests.exceptions.HTTPError as e:
                print(f"HTTP error occurred: {e}")

            except Exception as e:
                print(f"An unexpected error occurred: {e}")
                    
            # set depot it
            self._retrieve_depot_id()

    def get_positions(self):
        positions_list =[]
        
        if self.use_mock:
            positions_list = self.mock.load_mock_positions()

        else:
            url = f"{self.base_url}/api/brokerage/v3/depots/{self.depot_id}/positions"
            headers = {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.final_token}",
                "x-http-request-info": json.dumps({
                    "clientRequestId": {"sessionId": self.session_id, "requestId": self.request_id}
                })
            }
            r = requests.get(url, headers=headers)
            r.raise_for_status()
            positions_list = r.json()["values"]
        
        return self._sanitize_numbers(positions_list)


    def get_statements(self):
        # collect the account id connected to the depot (Girokonto or Verrechnungskonto)
        self.account_id = self._collect_account_id()

        transactions = []

        # TODO: this currently does not work to retrieve full two year statements. 
        if not self.use_mock:
            # get statements from last two years
            from_date = datetime.today() - timedelta(days=2 * 365)
            to_date = datetime.today()

            url = f"{self.base_url}/api/banking/v1/accounts/{self.account_id}/transactions"
            headers = {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.final_token}",
                "x-http-request-info": json.dumps({
                    "clientRequestId": {"sessionId": self.session_id, "requestId": "txn-1"}
                })
            }
            params = {
                "fromDate": from_date.strftime("%Y-%m-%d"),
                "toDate": to_date.strftime("%Y-%m-%d")
            }

            r = requests.get(url, headers=headers, params=params)
            r.raise_for_status()

            transactions = r.json().get("values", [])

        if self.use_mock:
            transactions = self.mock.load_mock_statements()

        return self._sanitize_numbers(transactions)
        
    def get_depot_id(self): 
        return self.depot_id

    def _collect_account_id(self):
        transactions = []
        account_id = None
        
        if not self.use_mock:

            url = f"{self.base_url}/api/banking/clients/user/v1/accounts/balances"
            headers = {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.final_token}",
                "x-http-request-info": json.dumps({
                    "clientRequestId": {"sessionId": self.session_id, "requestId": "txn-1"}
                })
            }

            r = requests.get(url, headers=headers)
            r.raise_for_status()

            account_ids = r.json().get("values", []) # includes e.g. credit card, Tagesgeld, ...
            
            # check which one is connected to depot (Griokonto or Verrechnungskonto)
            for account in account_ids:
                account_type = account['account']['accountType']['text']
                if account_type in ['Girokonto', 'Verrechnungskonto']:
                    account_id = account['account']['accountId']
                    print(account_id)
                
        return account_id


    def _collect_initial_token(self):
        
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "password",
            "username": self.username,
            "password": self.pw
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        r = requests.post(self.oauth_url, data=data, headers=headers)
        r.raise_for_status()
        token = r.json()
        self.init_token = token["access_token"]


    def _get_session_info(self):

        headers = {
            "Authorization": f"Bearer {self.init_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "x-http-request-info": json.dumps({
                "clientRequestId": {"sessionId": self.session_id, "requestId": self.request_id}
            })
        }
        r = requests.get(self.session_url, headers=headers)
        r.raise_for_status()
        return r.json()[0] # return session data


    def _raise_challenge_to_validate_tan(self, session_data):
    
        headers = {
            "Authorization": f"Bearer {self.init_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "x-http-request-info": json.dumps({
                "clientRequestId": {"sessionId": self.session_id, "requestId": self.request_id}
            })
        }

        # change sessionTanActive and 2FA to true: 
        session_data['sessionTanActive'] = True
        session_data['activated2FA'] = True 

        # Verwende die Session-Infos 1:1 wie empfangen
        r = requests.post(
            f"{self.session_url}/{session_data['identifier']}/validate",
            headers=headers,
            json=session_data  # ← korrektes Session-Objekt als Body
        )

        r.raise_for_status()
        return r.headers["x-once-authentication-info"]

    def _activate_tan(self, session_data, challenge):

        challenge_id = json.loads(challenge)["id"]

        headers = {
            "Authorization": f"Bearer {self.init_token}",
            "x-http-request-info": json.dumps({
                "clientRequestId": {"sessionId": self.session_id, "requestId": self.request_id}
            }),
            "Accept": "application/json",
            "Content-Type": "application/json",
            #"x-once-authentication": tan, # not needed for Photo Push Tan
            "x-once-authentication-info": json.dumps({"id": challenge_id})
        }

        # change sessionTanActive and 2FA to true: 
        session_data['sessionTanActive'] = True
        session_data['activated2FA'] = True 

        r = requests.patch(
            f"{self.session_url}/{session_data['identifier']}",
            json=session_data,
            headers=headers
        )
        r.raise_for_status()

    def _collect_final_token(self):
        headers = {"Accept": "application/json", "Content-Type": "application/x-www-form-urlencoded"}

        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "cd_secondary",
            "token": self.init_token,
        }

        r = requests.post(self.oauth_url, headers=headers, data=data)
        r.raise_for_status()

        token = r.json()

        self.final_token = token["access_token"] 


    def _retrieve_depot_id(self):
        url = f"{self.base_url}/api/brokerage/clients/user/v3/depots"
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.final_token}",
            "x-http-request-info": json.dumps({
                "clientRequestId": {"sessionId": self.session_id, "requestId": self.request_id}
            })
        }
        r = requests.get(url, headers=headers)
        r.raise_for_status()
        self.depot_id = r.json()["values"][0]["depotId"]