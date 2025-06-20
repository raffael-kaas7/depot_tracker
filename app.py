from dash import Dash, html, dcc
import pandas as pd
from comdirect_api import *


# 1. get initial token
initial = get_initial_token()
access_token = initial["access_token"]

# 2. get session info needed for authentication
session_obj = get_session_info(access_token)

# 3. call for tan authentication (Photo Push Tan)
challenge = validate_tan(access_token, session_obj)
print("🔐 Activate photo TAN")
input("↵ Press Enter after activating the TAN: ...")
#tan = input() # if we want to give a TAN number and not using photo tan

# 4. activate tan
activate_tan(access_token, session_obj, json.loads(challenge)["id"])

# 5. check authentication and retrieve secondary token for full comdirect access
try:
    final = get_secondary_token(access_token)
    final_token = final["access_token"]
    print("final_token", final_token)
    print("authentication fully completed")

except requests.exceptions.HTTPError as e:
    print(f"HTTP error occurred: {e}")

except Exception as e:
    print(f"An unexpected error occurred: {e}")


# 6. Depot abrufen
depot_id = get_depot_id(final_token)
positions = get_positions(final_token, depot_id)

# 7. Dash App anzeigen
df = pd.json_normalize(positions)


app = Dash(__name__)

app.layout = html.Div([
    html.H1("📊 Comdirect Depotübersicht"),
    dcc.Graph(
        figure={
            "data": [{
                "x": df["wkn"],
                "y": df["currentValue.value"],
                "type": "bar",
                "name": "Depotpositionen"
            }],
            "layout": {
                "title": "Depotpositionen nach aktuellem Wert"
            }
        }
    )
])

if __name__ == "__main__":

    app.run(debug=False)
