import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://api.comdirect.de"
OAUTH_URL = f"{BASE_URL}/oauth/token"
SESSION_URL = f"{BASE_URL}/api/session/clients/user/v1/sessions"

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
USERNAME = os.getenv("USERNAME")
PASSWORD = os.getenv("PASSWORD")

session_id = "dash-session"
request_id = "000001"

def get_initial_token():
    
    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "password",
        "username": USERNAME,
        "password": PASSWORD
    }

    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    r = requests.post(OAUTH_URL, data=data, headers=headers)
    r.raise_for_status()
    return r.json()


def get_session_info(token):

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "x-http-request-info": json.dumps({
            "clientRequestId": {"sessionId": session_id, "requestId": request_id}
        })
    }
    r = requests.get(SESSION_URL, headers=headers)
    r.raise_for_status()
    return r.json()


def validate_tan(token, session_obj):
    session_data = session_obj[0]  # hole erstes Element, da es eine Liste ist

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "x-http-request-info": json.dumps({
            "clientRequestId": {"sessionId": session_id, "requestId": request_id}
        })
    }

    # change sessionTanActive and 2FA to true: 
    session_data['sessionTanActive'] = True
    session_data['activated2FA'] = True 

    # Verwende die Session-Infos 1:1 wie empfangen
    r = requests.post(
        f"{SESSION_URL}/{session_data['identifier']}/validate",
        headers=headers,
        json=session_data  # ← korrektes Session-Objekt als Body
    )

    r.raise_for_status()
    return r.headers["x-once-authentication-info"]

# only necessary when we are not using Photo Tan Type
def activate_tan(token, session_obj, challenge_id, tan=0):
    session_data = session_obj[0]  # hole erstes Element, da es eine Liste ist

    headers = {
        "Authorization": f"Bearer {token}",
        "x-http-request-info": json.dumps({
            "clientRequestId": {"sessionId": session_id, "requestId": request_id}
        }),
        "Accept": "application/json",
        "Content-Type": "application/json",
        #"x-once-authentication": tan,
        "x-once-authentication-info": json.dumps({"id": challenge_id})
    }

    # change sessionTanActive and 2FA to true: 
    session_data['sessionTanActive'] = True
    session_data['activated2FA'] = True 

    r = requests.patch(
        f"{SESSION_URL}/{session_data['identifier']}",
        json=session_data,
        headers=headers
    )
    r.raise_for_status()
    return r.json()

def get_secondary_token(primary_token):
    headers = {"Accept": "application/json", "Content-Type": "application/x-www-form-urlencoded"}

    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "cd_secondary",
        "token": primary_token,
    }

    r = requests.post(OAUTH_URL, headers=headers, data=data)
    r.raise_for_status()

    return r.json()

def get_depot_id(token):
    url = f"{BASE_URL}/api/brokerage/clients/user/v3/depots"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
        "x-http-request-info": json.dumps({
            "clientRequestId": {"sessionId": session_id, "requestId": "2"}
        })
    }
    r = requests.get(url, headers=headers)
    r.raise_for_status()
    return r.json()["values"][0]["depotId"]

def get_positions(token, depot_id):
    url = f"{BASE_URL}/api/brokerage/v3/depots/{depot_id}/positions"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
        "x-http-request-info": json.dumps({
            "clientRequestId": {"sessionId": session_id, "requestId": "3"}
        })
    }
    r = requests.get(url, headers=headers)
    r.raise_for_status()
    return r.json()["values"]
