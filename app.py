from dash import Dash, Output, Input, dcc, html, dash_table

from frontend.layout import create_layout, create_summary_row
from backend.api.comdirect_api import ComdirectAPI
from backend.data.data_manager import DataManager
from backend.logic.depot_service import DepotService
from backend.data.yfinance_support import wkn_to_name, wkn_to_name_lookup
from apscheduler.schedulers.background import BackgroundScheduler
import os
import pandas as pd
import plotly.express as px
import yaml
import atexit
import dash_bootstrap_components as dbc

import locale

from dotenv import load_dotenv
load_dotenv()

# Set locale for formatting (German style: decimal as comma, thousands as point)
locale.setlocale(locale.LC_ALL, 'de_DE.UTF-8')

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
api_cd_1 = ComdirectAPI(username=os.getenv("USERNAME_1"), pw=os.getenv("PASSWORD_1"), depot_name=DEPOT_1_NAME, session_id="comdirect-active-depot", request_id="000001")

# init api and authenticate
api_cd_2 = ComdirectAPI(username=os.getenv("USERNAME_2"), pw=os.getenv("PASSWORD_2"), depot_name=DEPOT_2_NAME, session_id="comdirect-dividend-depot", request_id="000002")

# data manager object to handle data base
data_cd_1 = DataManager(depot_name=api_cd_1.get_name())
data_cd_2 = DataManager(depot_name=api_cd_2.get_name())

# use service object to analyze depot data 
service_cd_1 = DepotService(data_cd_1)
service_cd_2 = DepotService(data_cd_2)

# TODO: remove and use service_cd_1.get_dividends() and service_cd_2.get_dividends() instead
dividends_file = ""
if os.getenv("USE_GENERATED_MOCK_DATA", "false").lower() == "true":
    dividends_file = "./mock/generated_mock_data/dividends_mock.yaml"
else:
    dividends_file = "data/dividends.yaml"

app.layout = create_layout()


scheduler = BackgroundScheduler()
scheduler_started = False  # Guard, damit er nur einmal startet

def start_scheduler_once():
    global scheduler_started
    if scheduler_started:
        return
    # Jobs definieren (dein Intervall: hier 1 Minute)
    scheduler.add_job(func=data_cd_1.update_prices, trigger="interval", minutes=1, id="prices1", max_instances=1, coalesce=True)
    scheduler.add_job(func=data_cd_2.update_prices, trigger="interval", minutes=1, id="prices2", max_instances=1, coalesce=True)
    scheduler.start()
    atexit.register(lambda: scheduler.shutdown(wait=False))
    scheduler_started = True
    print("✅ Scheduler gestartet")

@app.callback(
    Output("auth-status", "children"),
    Input("auth-button", "n_clicks"),
    prevent_initial_call=True
)
def authenticate_user(n_clicks):
    """
    Trigger authentication for both APIs when the button is clicked.

    Parameters:
        n_clicks (int): Number of times the button has been clicked.

    Returns:
        str: Status message indicating success or failure.
    """
    try:
        # authenticate and update local data
        api_cd_1.authenticate()
        api_cd_2.authenticate()
        data_cd_1.update_data()
        data_cd_2.update_data()

        return dbc.Alert("Authentication successful!", color="success", className="mt-3")
    except Exception as e:
        return dbc.Alert(f"Authentication failed: {str(e)}", color="danger", className="mt-3")


@app.callback(
    Output("depot-table", "children"),
    Input("table-switch", "value")
)
def render_depot_table(table_mode):
    
    def process_depot(positions, title, summary=True):
        
        # sum
        total_purchase_value = positions["purchase_value"].sum()
        total_value = positions["current_value"].sum()
        performance = ((total_value - total_purchase_value) / total_purchase_value) * 100 if total_purchase_value else 0

        # Main table
        main_table = dash_table.DataTable(
            columns=[
                {"name": "WKN", "id": "wkn", "type": "text"},
                {"name": "Name", "id": "name", "type": "text"},
                {"name": "Count", "id": "count", "type": "numeric"},
                {"name": "Purchase Price (€)", "id": "purchase_price", "type": "numeric"},
                {"name": "Current Price (€)", "id": "current_price", "type": "numeric"},
                {"name": "Purchase Value (€)", "id": "purchase_value", "type": "numeric"},
                {"name": "Current Value (€)", "id": "current_value", "type": "numeric"},
                {"name": "Performance (%)", "id": "performance_%", "type": "numeric"},
                {"name": "Allocation (%)", "id": "percentage_in_depot", "type": "numeric"},
            ],
            data=positions.to_dict("records"),
            sort_action="native",  # Enables sorting
            sort_by=[
                {"column_id": "percentage_in_depot", "direction": "desc"}
            ],
            style_table={"overflowX": "auto", "borderRadius": "5px"},
            style_cell={
                "textAlign": "center",
                "padding": "10px",
                "fontFamily": "Arial, sans-serif",
                "fontSize": "18px",
                "minWidth": "120px",  
                "maxWidth": "120px", 
                "width": "120px",  
            },
            style_header={
                "backgroundColor": "#007bff",
                "color": "white",
                "fontWeight": "bold",
                "border": "1px solid #007bff",
            },
            style_data={
                "border": "1px solid #ddd",
            },
            style_data_conditional=[
                {
                    "if": {"row_index": "odd"},
                    "backgroundColor": "#f9f9f9",
                },
                {
                    "if": {"row_index": "even"},
                    "backgroundColor": "#ffffff",
                },
                {
                    "if": {
                        "column_id": "performance_%",
                        "filter_query": "{performance_%} < 0", 
                    },
                    "color": "red",
                    "fontWeight": "bold",
                },
                {
                    "if": {
                        "column_id": "performance_%",  # Nur die Performance-Spalte
                        "filter_query": "{performance_%} >= 0",  # Positive Werte
                    },
                    "color": "green",
                    "fontWeight": "bold",
                },
            ],
        )

        if summary is False:
            return html.Div([html.H4(title), main_table])


        summary_div = create_summary_row([
            {"icon": "💰", "label": "Current Value", "value": f"{total_value:,.0f} €", "color": "dark"},
            {"icon": "📈", "label": "Performance", "value": f"{performance:.1f} %", "color": "success" if performance > 0 else "danger"},
            {"icon": "🏷️", "label": "Invested Capital", "value": f"{total_purchase_value:,.0f} €", "color": "secondary"},
        ])

        # Combine both tables
        return html.Div([
            html.H4(title),
            summary_div,
            main_table,
            html.Br(),
        ])
        
    # Fetch positions from both depots
    pos1 = service_cd_1.get_positions()
    pos2 = service_cd_2.get_positions()
    
    all_pos = pd.concat([pos1, pos2], ignore_index=True)
    # update allocation
    total_current_value = all_pos["current_value"].sum()
    all_pos["percentage_in_depot"] = round((all_pos["current_value"] / total_current_value) * 100, 2)


    total_pos1 = service_cd_1.compute_summary()
    total_pos2 = service_cd_2.compute_summary()

    total_cost = total_pos1["total_cost"] + total_pos2["total_cost"]
    total_value = total_pos1["total_value"] + total_pos2["total_value"]

    relative_diff = ((total_value - total_cost) / total_cost) * 100 if total_cost else 0

    summary_div = create_summary_row([
        {"icon": "💰", "label": "Current Value", "value": f"{total_value:,.0f} €", "color": "dark"},
        {"icon": "📈", "label": "Performance", "value": f"{relative_diff:.1f} %", "color": "success" if relative_diff > 0 else "danger"},
        {"icon": "🏷️", "label": "Invested Capital", "value": f"{total_cost:,.0f} €", "color": "secondary"},
    ])
    
    if table_mode == "single":
        return html.Div([process_depot(pos1, DEPOT_1_NAME), process_depot(pos2, DEPOT_2_NAME)])
    else:
        return html.Div([summary_div, process_depot(all_pos, "All positions", summary=False)])
        

@app.callback(
    Output("asset-piechart", "children"),
    Input("asset-piechart", "id")
)
def render_pie_charts(_):
    df1 = service_cd_1.get_asset_pie_data(service_cd_1.get_positions())
    df2 = service_cd_2.get_asset_pie_data(service_cd_2.get_positions())

    if df1.empty and df2.empty:
        return html.Div("No data available for asset allocation.")

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
    Output("dividend-chart", "figure"),
    Output("dividend-summary", "children"),
    Input("year-selector", "value")
)
def show_dividend_chart(selected_years):    
    with open(dividends_file, "r") as f:
        dividends = yaml.safe_load(f) or []

    df = pd.DataFrame(dividends)
    df["date"] = pd.to_datetime(df["date"])
    df["year"] = df["date"].dt.year
    df["month"] = df["date"].dt.month
    df["month_name"] = df["date"].dt.strftime("%b")
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce")

    all_years = sorted(df["year"].unique())

    # show all by default
    if not selected_years:
        selected_years = all_years

    df = df[df["year"].isin(selected_years)]

    monthly = df.groupby(["year", "month", "month_name"])["amount"].sum().reset_index()
    month_order = ["Jan", "Feb", "Mär", "Apr", "Mai", "Jun",
                   "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    monthly["month_name"] = pd.Categorical(monthly["month_name"], categories=month_order, ordered=True)
    monthly = monthly.sort_values(["year", "month"])

    fig = px.bar(
        monthly,
        x="month_name",
        y="amount",
        color="year",
        barmode="group",
        title="",
        labels={"amount": "Dividends in €", "month_name": "Month", "year": "Year"},
        height=450,
    )

    # --- Summary ---
    total = df["amount"].sum()
    summary_per_year = df.groupby("year")["amount"].sum()

    summary = html.Ul([
        html.Li(f"👑 All time Dividends: {total:.0f} €"),
        *[html.Li(f"📅 {year}: {amount:.0f} €") for year, amount in summary_per_year.items()]
    ])

    return fig, summary

@app.callback(
    Output("year-selector", "options"),
    Output("year-selector", "value"),
    Input("year-selector", "id") 
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
    Output("dividend-table-container", "style"),
    Output("dividend-table-container", "children"),
    Input("toggle-table-btn", "n_clicks")
    )
def update_dividenden_table(n_clicks):
    print("Update dividends table")
    # display table / hide table
    clicks = n_clicks or 0 # avoid n_clicks being None on first load
    if clicks % 2 == 0:
        return {"display": "none"}, None

    with open(dividends_file, "r") as f:
        dividends = yaml.safe_load(f) or []

    df = pd.DataFrame(dividends)
    df["date"] = pd.to_datetime(df["date"])
    df["year"] = df["date"].dt.year
    df["month"] = df["date"].dt.month
    df["month_name"] = df["date"].dt.strftime("%b")
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
    df["company"] = df["company"]

    table = dash_table.DataTable(
        columns=[
            {"name": "date", "id": "date"},
            {"name": "company", "id": "company"},
            {"name": "net amount", "id": "amount"}
        ],
        data=df.to_dict("records"),
        sort_action="native",  # Enables sorting
        style_table={"overflowX": "auto"},
        page_size=50
    )

    return {"display": "block"}, table

if __name__ == "__main__":
    start_scheduler_once()
    app.run(debug=False)