from dash import Dash, Output, Input, dcc, html, dash_table

from frontend.layout import create_layout
from backend.api.comdirect_api import ComdirectAPI
from backend.data.data_manager import DataManager
from backend.logic.depot_service import DepotService
from backend.logic.yfinance_support import wkn_to_name, wkn_to_name_lookup

import os
from dotenv import load_dotenv
import pandas as pd
import plotly.express as px
import yaml

from dotenv import load_dotenv


app = Dash(
    __name__,
    external_stylesheets=[
        "https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css",
        "https://fonts.googleapis.com/css2?family=Inter&display=swap"
    ]
)

server = app.server

DEPOT_1_NAME = os.getenv("DEPOT_1_NAME")
DEPOT_2_NAME = os.getenv("DEPOT_2_NAME")

# hard init two comdirect depots (uncomment if only one needed, setup in .env)

# init api and authenticate
api_cd_1 = ComdirectAPI(username=os.getenv("USERNAME_1"), pw=os.getenv("PASSWORD_1"), depot_name=DEPOT_1_NAME, account_id=os.getenv("ACCOUNT_ID_1"), session_id="comdirect-active-depot", request_id="000001")
api_cd_1.authenticate()

# update offline data
api_cd_1.save_mock_positions(normalize=False)
api_cd_1.save_mock_statements()
api_cd_1.save_mock_depot_id()

# init api and authenticate
api_cd_2 = ComdirectAPI(username=os.getenv("USERNAME_2"), pw=os.getenv("PASSWORD_2"), depot_name=DEPOT_2_NAME, account_id=os.getenv("ACCOUNT_ID_2"), session_id="comdirect-dividend-depot", request_id="000002")
api_cd_2.authenticate()

# update offline data
api_cd_2.save_mock_positions(normalize=False)
api_cd_2.save_mock_statements()
api_cd_2.save_mock_depot_id()

# data manager object to handle data base
data_cd_1 = DataManager(backend="yaml")
data_cd_2 = DataManager(backend="yaml")

# use service object to analyze depot data 
service_cd_1 = DepotService(api_cd_1, data_cd_1)
service_cd_2 = DepotService(api_cd_2, data_cd_2)

service_cd_1.extract_dividends_from_statements()
service_cd_2.extract_dividends_from_statements()

dividends_file = ""
if os.getenv("USE_MOCK", "false").lower() == "true" and os.getenv("USE_GENERATED_MOCK_DATA", "false").lower() == "true":
    dividends_file = "./mock/generated_mock_data/dividends_mock.yaml"
else:
    dividends_file = "data/dividends.yaml"

app.layout = create_layout()

@app.callback(
    Output("depot-table", "children"),
    Input("table-switch", "value")
)
def render_depot_table(table_mode):
    
    def process_depot(positions, title, summary=True):
        df = pd.json_normalize(positions)

        df["wkn"] = df["wkn"]
        df["count"] = pd.to_numeric(df["quantity.value"], errors="coerce")
        df["purchase_price"] = pd.to_numeric(df["purchasePrice.value"], errors="coerce")
        df["purchase_value"] = pd.to_numeric(df["purchaseValue.value"], errors="coerce")
        df["current_price"] = pd.to_numeric(df["currentPrice.price.value"], errors="coerce")
        df["current_value"] = pd.to_numeric(df["currentValue.value"], errors="coerce")
        df["performance_%"] = round(((df["current_value"] - df["purchase_value"]) / df["purchase_value"]) * 100, 2)

        total_current_value = df["current_value"].sum()

        df["percentage_in_depot"] = round((df["current_value"] / total_current_value) * 100, 2)

        # get name from wkn via yfinance
        df["name"] = df["wkn"].apply(wkn_to_name_lookup)

        # sum
        total_purchase_value = df["purchase_value"].sum()
        total_value = df["current_value"].sum()
        performance = ((total_value - total_purchase_value) / total_purchase_value) * 100 if total_purchase_value else 0

        # Main table
        main_table = dash_table.DataTable(
            columns=[
                {"name": "WKN", "id": "wkn", "type": "text"},
                {"name": "Name", "id": "name", "type": "text"},
                {"name": "Count", "id": "count", "type": "numeric"},
                {"name": "Purchase Price (€)", "id": "purchase_price", "type": "numeric"},
                {"name": "Purchase Value (€)", "id": "purchase_value", "type": "numeric"},
                {"name": "Current Price (€)", "id": "current_price", "type": "numeric"},
                {"name": "Current Value (€)", "id": "current_value", "type": "numeric"},
                {"name": "Performance (%)", "id": "performance_%", "type": "numeric"},
                {"name": "Percentage in Depot (%)", "id": "percentage_in_depot", "type": "numeric"},
            ],
            data=df.to_dict("records"),
            sort_action="native",  # Enables sorting
            style_table={"overflowX": "auto"},
            style_cell={"textAlign": "left"},
        )

        if summary is False:
            return html.Div([html.H4(title), main_table])

        # Summary table
        summary_table = dash_table.DataTable(
            columns=[
                {"name": "Total Purchase Value (€)", "id": "total_purchase_value", "type": "numeric"},
                {"name": "Total Current Value (€)", "id": "total_value", "type": "numeric"},
                {"name": "Performance (%)", "id": "performance", "type": "numeric"},
            ],
            data=[
                {
                    "total_purchase_value": total_purchase_value,
                    "total_value": total_value,
                    "performance": round(performance, 2),
                }
            ],
            style_table={"overflowX": "auto"},
            style_cell={"textAlign": "left"},
        )

        # Combine both tables
        return html.Div([
            html.H4(title),
            main_table,
            html.Br(),
            html.H4("Summary"),
            summary_table
        ])

    # Hole Positionen beider Depots
    pos1 = service_cd_1.fetch_positions()
    pos2 = service_cd_2.fetch_positions()
    all_pos = pos1 + pos2

    total_pos1 = service_cd_1.compute_summary()
    total_pos2 = service_cd_2.compute_summary()

    total_cost = total_pos1["total_cost"] + total_pos2["total_cost"]
    total_value = total_pos1["total_value"] + total_pos2["total_value"]

    relative_diff = ((total_value - total_cost) / total_cost) * 100 if total_cost else 0

    summary_div = html.Div([
        html.H4("Depot Summary", className="mt-4 mb-3"),
        html.P(f"Total Purchase Value: {total_cost:.2f} €"),
        html.P(f"Total Current Value: {total_value:.2f} €"),
        html.P(f"Relative Difference: {relative_diff:.2f} %")
    ])
    
    if table_mode == "single":
        return html.Div([summary_div, process_depot(pos1, DEPOT_1_NAME), process_depot(pos2, DEPOT_2_NAME)])
    else:
        return html.Div([summary_div, process_depot(all_pos, "Combined Depots", summary=False)])
        

@app.callback(
    Output("asset-piechart", "children"),
    Input("asset-piechart", "id")
)
def render_pie_charts(_):
    df1 = service_cd_1.get_asset_pie_data(service_cd_1.fetch_positions())
    df2 = service_cd_2.get_asset_pie_data(service_cd_2.fetch_positions())

    pie1 = dcc.Graph(
        figure={
            "type": "pie",
            "data": [{
                "labels": df1["name"],
                "values": df1["wert"],
                "type": "pie",
                "hole": 0.3,
            }],
            "layout": {"title": DEPOT_1_NAME}
        }
    )

    pie2 = dcc.Graph(
        figure={
            "type": "pie",
            "data": [{
                "labels": df2["name"],
                "values": df2["wert"],
                "type": "pie",
                "hole": 0.3,
            }],
            "layout": {"title": DEPOT_2_NAME}
        }
    )

    return html.Div([
        html.Div(pie1, className="col-md-6"),
        html.Div(pie2, className="col-md-6"),
    ], className="row")


@app.callback(
    Output("dividenden-chart", "figure"),
    Output("dividenden-summary", "children"),
    Input("year-selector", "value")
)
def render_dividenden_chart(selected_years):    
    with open(dividends_file, "r") as f:
        dividends = yaml.safe_load(f) or []

    # --- 📊 In DataFrame umwandeln ---
    df = pd.DataFrame(dividends)
    df["date"] = pd.to_datetime(df["date"])
    df["year"] = df["date"].dt.year
    df["month"] = df["date"].dt.month
    df["month_name"] = df["date"].dt.strftime("%b")
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce")

    all_years = sorted(df["year"].unique())

    # Falls keine Auswahl: alle anzeigen
    if not selected_years:
        selected_years = all_years

    df = df[df["year"].isin(selected_years)]

    # --- 📊 Aggregation ---
    monthly = df.groupby(["year", "month", "month_name"])["amount"].sum().reset_index()

    # 🪄 Monatsnamen sortieren
    month_order = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                   "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    monthly["month_name"] = pd.Categorical(monthly["month_name"], categories=month_order, ordered=True)
    monthly = monthly.sort_values(["year", "month"])

    fig = px.bar(
        monthly,
        x="month_name",
        y="amount",
        color="year",
        barmode="group",
        title="📈 Monatliche Dividenden",
        labels={"amount": "Dividenden in €", "month_name": "Monat", "year": "Jahr"},
        height=450,
    )

    # --- 🧾 Zusammenfassung ---
    total = df["amount"].sum()
    summary_per_year = df.groupby("year")["amount"].sum()

    summary = html.Ul([
        html.Li(f"📦 Gesamtsumme: {total:.2f} €"),
        *[html.Li(f"📅 {year}: {amount:.2f} €") for year, amount in summary_per_year.items()]
    ])

    return fig, summary

@app.callback(
    Output("year-selector", "options"),
    Output("year-selector", "value"),
    Input("year-selector", "id")  # ✅ Wird garantiert beim Rendern gesetzt
)
def init_year_selector(_):
    with open(dividends_file, "r") as f:
        dividends = yaml.safe_load(f) or []

    df = pd.DataFrame(dividends)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])

    years = sorted(df["date"].dt.year.unique())
    options = [{"label": str(y), "value": y} for y in years]

    print("📅 Verfügbare Jahre:", years)
    return options, years

@app.callback(
    Output("dividenden-table-container", "style"),
    Output("dividenden-table-container", "children"),
    Input("toggle-table-btn", "n_clicks")
    )
def update_dividenden_table(n_clicks):
    print("Update dividends table")
    # Tabelle ein-/ausblenden
    if n_clicks % 2 == 0:
        return {"display": "none"}, None

    with open(dividends_file, "r") as f:
        dividends = yaml.safe_load(f) or []

    # --- 📊 In DataFrame umwandeln ---
    df = pd.DataFrame(dividends)
    df["date"] = pd.to_datetime(df["date"])
    df["year"] = df["date"].dt.year
    df["month"] = df["date"].dt.month
    df["month_name"] = df["date"].dt.strftime("%b")
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
    df["company"] = df["company"]

    # Filter anwenden
    filtered_data = df
    # if selected_companies:
    #     filtered_data = df[df["company"].isin(selected_companies)]

    # Tabelle erstellen
    table = dash_table.DataTable(
        columns=[
            {"name": "date", "id": "date"},
            {"name": "company", "id": "company"},
            {"name": "net amount", "id": "amount"}
        ],
        data=filtered_data.to_dict("records"),
        sort_action="native",  # Enables sorting
        style_table={"overflowX": "auto"},
        page_size=50
    )

    return {"display": "block"}, table

if __name__ == "__main__":
    app.run(debug=False)