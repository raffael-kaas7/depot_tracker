# app.py (fixed)
from dash import Dash, Output, Input, dcc, html, dash_table, callback_context
import dash_bootstrap_components as dbc
import os, json, yaml, locale, numpy as np
import pandas as pd
import plotly.express as px
import datetime as dt
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler
import tempfile
import atexit

from frontend.layout import create_layout, create_summary_row
from backend.api.comdirect_api import ComdirectAPI
from backend.data.data_manager import DataManager
from backend.logic.depot_service import DepotService
from backend.data.yfinance_support import wkn_to_name, wkn_to_name_lookup



from dotenv import load_dotenv
load_dotenv()

# German formatting if available
try:
    locale.setlocale(locale.LC_ALL, 'de_DE.UTF-8')
except Exception:
    pass

app = Dash(
    __name__,
    external_stylesheets=[
        "https://cdn.jsdelivr.net/npm/bootswatch@5.3.3/dist/darkly/bootstrap.min.css",
        "https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap",
    ],
    suppress_callback_exceptions=True,
)
server = app.server

DEPOT_1_NAME = os.getenv("DEPOT_1_NAME")
DEPOT_2_NAME = os.getenv("DEPOT_2_NAME")

api_cd_1 = ComdirectAPI(
    username=os.getenv("USERNAME_1"),
    pw=os.getenv("PASSWORD_1"),
    depot_name=DEPOT_1_NAME,
    session_id="comdirect-active-depot",
    request_id="000001",
)
api_cd_2 = ComdirectAPI(
    username=os.getenv("USERNAME_2"),
    pw=os.getenv("PASSWORD_2"),
    depot_name=DEPOT_2_NAME,
    session_id="comdirect-dividend-depot",
    request_id="000002",
)

data_cd_1 = DataManager(depot_name=api_cd_1.get_name())
data_cd_2 = DataManager(depot_name=api_cd_2.get_name())

service_cd_1 = DepotService(data_cd_1)
service_cd_2 = DepotService(data_cd_2)

SNAPSHOT_FILE = "data/snapshot.json"
BERLIN_TZ = ZoneInfo("Europe/Berlin")

# Pick your dividends file
dividends_file = (
    "./mock/generated_mock_data/dividends_mock.yaml"
    if os.getenv("USE_GENERATED_MOCK_DATA", "false").lower() == "true"
    else "data/dividends.yaml"
)

app.layout = create_layout()

scheduler = BackgroundScheduler()
scheduler_started = False  # Guard, damit er nur einmal startet

def save_daily_snapshot():
    """
    Writes exactly ONE snapshot per calendar day (Europe/Berlin) for each depot into separate files:
    - data/DEPOT_1_NAME/snapshot.json
    - data/DEPOT_2_NAME/snapshot.json
    Format: - date: YYYY-MM-DD; current_value: float; invested_capital: float
    """
    today = dt.datetime.now(BERLIN_TZ).date().isoformat()

    # Compute summaries for both depots
    total_pos1 = service_cd_1.compute_summary()
    total_pos2 = service_cd_2.compute_summary()

    # Prepare snapshots for each depot
    depot_snapshots = {
        f"{DEPOT_1_NAME}": {
            "path": os.path.join("data", f"{DEPOT_1_NAME}", "snapshot.json"),
            "data": {
                "date": today,
                "current_value": round(total_pos1["total_value"], 2),
                "invested_capital": round(total_pos1["total_cost"], 2),
            },
        },
        "f{DEPOT_2_NAME}": {
            "path": os.path.join("data", f"{DEPOT_2_NAME}", "snapshot.json"),
            "data": {
                "date": today,
                "current_value": round(total_pos2["total_value"], 2),
                "invested_capital": round(total_pos2["total_cost"], 2),
            },
        },
    }

    for depot_name, snapshot_info in depot_snapshots.items():
        snapshot_file = snapshot_info["path"]
        snap = snapshot_info["data"]

        # Ensure the directory exists
        os.makedirs(os.path.dirname(snapshot_file), exist_ok=True)

        # Check if the file exists
        if not os.path.exists(snapshot_file):
            # Create an empty file with default content (empty list)
            with open(snapshot_file, "w") as f:
                json.dump([], f)  # Default to an empty list
            print(f"📂 Datei erstellt: {snapshot_file}")

        # Write or update the snapshot
        try:
            with open(snapshot_file, "r") as f:
                snapshots = json.load(f)

            # Check if today's snapshot already exists
            existing_snapshot = next((s for s in snapshots if s["date"] == today), None)
            if existing_snapshot:
                # Update existing snapshot
                existing_snapshot["current_value"] = snap["current_value"]
                existing_snapshot["invested_capital"] = snap["invested_capital"]
            else:
                # Append new snapshot
                snapshots.append(snap)

            # Write updated snapshots back to file
            with open(snapshot_file, "w") as f:
                json.dump(snapshots, f, indent=4)

        except Exception as e:
            print(f"❌ Error saving snapshot for {depot_name}: {e}")
            

def start_scheduler_once():
    global scheduler_started
    if scheduler_started:
        return
    # Jobs definieren (dein Intervall: hier 1 Minute)
    scheduler.add_job(func=data_cd_1.update_prices, trigger="interval", minutes=0.1, id="prices1", max_instances=1, coalesce=True)
    scheduler.add_job(func=data_cd_2.update_prices, trigger="interval", minutes=0.1, id="prices2", max_instances=1, coalesce=True)
    scheduler.add_job(func=save_daily_snapshot, trigger="interval", minutes=0.1, id="snapshot", max_instances=1, coalesce=True)
    scheduler.start()
    atexit.register(lambda: scheduler.shutdown(wait=False))
    scheduler_started = True
    print("✅ Scheduler gestartet")

# ---------------------------
# Sidebar section switching
# ---------------------------
@app.callback(
    Output("assets-section", "style"),
    Output("dividends-section", "style"),
    Output("nav-assets", "active"),
    Output("nav-dividends", "active"),
    Input("nav-assets", "n_clicks"),
    Input("nav-dividends", "n_clicks"),
)
def switch_sections(n_assets, n_divs):
    # default to assets on initial load
    ctx = callback_context
    which = "assets"
    if ctx.triggered:
        which = "assets" if ctx.triggered[0]["prop_id"].startswith("nav-assets") else "dividends"
    if which == "assets":
        return {"display": "block"}, {"display": "none"}, True, False
    return {"display": "none"}, {"display": "block"}, False, True

# ---------------------------
# Sync buttons (separate fns)
# ---------------------------
@app.callback(
    Output("auth-status-cd1", "children"),
    Input("auth-button-cd1", "n_clicks"),
    prevent_initial_call=True,
)
def sync_depot_1(n_clicks):
    try:
        # Adapt to your API methods as needed
        api_cd_1.authenticate()
        data_cd_1.update_data()
        return dbc.Alert("Depot 1: Authentication & sync successful.", color="success", className="mt-2 py-2")
    except Exception as e:
        return dbc.Alert(f"Depot 1: Authentication failed — {e}", color="danger", className="mt-2 py-2")

@app.callback(
    Output("auth-status-cd2", "children"),
    Input("auth-button-cd2", "n_clicks"),
    prevent_initial_call=True,
)
def sync_depot_2(n_clicks):
    try:
        api_cd_2.authenticate()
        data_cd_2.update_data()
        return dbc.Alert("Depot 2: Authentication & sync successful.", color="success", className="mt-2 py-2")
    except Exception as e:
        return dbc.Alert(f"Depot 2: Authentication failed — {e}", color="danger", className="mt-2 py-2")

# ---------------------------
# Assets: positions table(s)
# ---------------------------
def momentum_display(x: float) -> str:
    if x is None or pd.isna(x): return "—"
    if x >= 0.10: arrow = "▲"
    elif x >= 0.03: arrow = "↗"
    elif x <= -0.10: arrow = "▼"
    elif x <= -0.03: arrow = "↘"
    else: arrow = "→"
    return f"{arrow}"
    #return f"{arrow} {x*100:.1f}%"

def process_depot(positions: pd.DataFrame, title: str, summary=True):
    if positions is None or positions.empty:
        return html.Div([html.H4(title), dbc.Alert("No positions to display.", color="secondary")])

    # totals
    total_purchase_value = positions["purchase_value"].sum()
    total_value = positions["current_value"].sum()
    capital_gain = total_value - total_purchase_value
    performance = ((total_value - total_purchase_value) / total_purchase_value) * 100 if total_purchase_value else 0

    # momentum
    if "momentum_3m" not in positions.columns:
        positions["momentum_3m"] = np.nan
    positions["momentum_3m_disp"] = positions["momentum_3m"].map(momentum_display)

    # render table
    show_cols = [
        ("name","Name"), ("count","Count"),
        ("purchase_price","Purchase Price (€)"), ("current_price","Current Price (€)"),
        ("purchase_value","Purchase Value (€)"), ("current_value","Current Value (€)"),
        ("performance_%","Performance (%)"), ("percentage_in_depot","Allocation (%)"),
        ("total_dividends","Total Dividends (€)"), ("momentum_3m_disp","3-M-Momentum")
    ]
    cols = [c for c,_ in show_cols if c in positions.columns]
    table = dash_table.DataTable(
        columns=[{"name": n, "id": c} for c,n in show_cols if c in positions.columns],
        data=positions[cols].to_dict("records"),
        sort_action="native",
        sort_by=[{"column_id": "percentage_in_depot", "direction": "desc"}] if "percentage_in_depot" in cols else [],
        style_table={"overflowX": "auto", "borderRadius": "5px"},
        style_data_conditional=[
            {"if": {"column_id": "performance_%", "filter_query": "{performance_%} < 0"}, "color": "#ff6b6b"},
            {"if": {"column_id": "performance_%", "filter_query": "{performance_%} >= 0"}, "color": "#1dd1a1"},
            {"if": {"column_id": "momentum_3m_disp", "filter_query": "{momentum_3m} >= 0.10"}, "color": "#1dd1a1"},
            {"if": {"column_id": "momentum_3m_disp", "filter_query": "{momentum_3m} >= 0.03 && {momentum_3m} < 0.10"}, "color": "#10ac84"},
            {"if": {"column_id": "momentum_3m_disp", "filter_query": "{momentum_3m} > -0.03 && {momentum_3m} < 0.03"}, "color": "#c8d6e5"},
            {"if": {"column_id": "momentum_3m_disp", "filter_query": "{momentum_3m} <= -0.03 && {momentum_3m} > -0.10"}, "color": "#ff9f43"},
            {"if": {"column_id": "momentum_3m_disp", "filter_query": "{momentum_3m} <= -0.10"}, "color": "#ff6b6b"},
        ],
        #page_size=50,
    )

    if not summary:
        return html.Div([html.H4(title), table])

    summary_div = create_summary_row([
        {"icon": "💰", "label": "Current Value", "value": f"{total_value:,.0f} €", "color": "light"},
        {"icon": "💲", "label": "Capital Gain", "value": f"{capital_gain:,.0f} €", "color": "#1dd1a1" if performance > 0 else "#ff6b6b"},
        {"icon": "📈", "label": "Performance", "value": f"{performance:.1f} %", "color": "#1dd1a1" if performance > 0 else "#ff6b6b"},
        {"icon": "🏷️", "label": "Invested Capital", "value": f"{total_purchase_value:,.0f} €", "color": "light"},
    ])

    return html.Div([html.H4(title), summary_div, table, html.Br()])

@app.callback(
    Output("depot-table", "children"),
    Input("table-switch", "value"),
)
def render_depot_table(table_mode):
    try:
        pos1 = service_cd_1.get_positions()
    except Exception:
        pos1 = pd.DataFrame()
    try:
        pos2 = service_cd_2.get_positions()
    except Exception:
        pos2 = pd.DataFrame()

    if pos1 is None: pos1 = pd.DataFrame()
    if pos2 is None: pos2 = pd.DataFrame()

    # allocation for combined
    all_pos = pd.concat([pos1, pos2], ignore_index=True) if not pos1.empty or not pos2.empty else pd.DataFrame()
    if not all_pos.empty and "current_value" in all_pos.columns:
        total_current_value = all_pos["current_value"].sum()
        if total_current_value:
            all_pos["percentage_in_depot"] = (all_pos["current_value"] / total_current_value * 100).round(2)

    if table_mode == True: # separated
        return html.Div([
            process_depot(pos1, DEPOT_1_NAME or "Depot 1"),
            process_depot(pos2, DEPOT_2_NAME or "Depot 2"),
        ])
    else:
        return html.Div([
            #summary_div,
            process_depot(all_pos, f"{DEPOT_1_NAME} + {DEPOT_2_NAME}", summary=True)
        ])

# ---------------------------
# Dividends
# ---------------------------
@app.callback(
    Output("dividend-chart", "figure"),
    Output("dividend-summary", "children"),
    Input("dividend-chart", "id"),  # Trigger the callback when the chart is loaded
)
def show_dividend_chart(_):
    # Refresh (if your services write to dividends_file)
    try:
        service_cd_1.get_dividends()
        service_cd_2.get_dividends()
    except Exception:
        pass

    try:
        with open(dividends_file, "r", encoding="utf-8") as f:
            dividends = yaml.safe_load(f) or []
    except Exception:
        dividends = []

    df = pd.DataFrame(dividends)
    if df.empty:
        fig = px.bar(pd.DataFrame({"month_name": [], "amount": [], "year": []}), x="month_name", y="amount", color="year")
        return fig, html.Div("No dividend data yet.", className="text-muted")

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])
    df["year"] = df["date"].dt.year
    df["month"] = df["date"].dt.month
    df["month_name"] = df["date"].dt.strftime("%b")
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0)

    all_years = sorted(df["year"].unique())

    month_order = ["Jan", "Feb", "Mär", "Apr", "Mai", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    all_months = pd.DataFrame([(y, i, m) for y in all_years for i, m in enumerate(month_order, start=1)],
                              columns=["year", "month", "month_name"])
    monthly = df.groupby(["year", "month", "month_name"])["amount"].sum().reset_index()
    monthly = pd.merge(all_months, monthly, on=["year", "month", "month_name"], how="left")
    monthly["amount"] = monthly["amount"].fillna(0)
    monthly["year"] = monthly["year"].astype(str)

    fig = px.bar(monthly, x="month_name", y="amount", color="year", barmode="group",
                 labels={"amount": "Dividends in €", "month_name": "Month", "year": "Year"},
                 height=450)
    fig.update_layout(paper_bgcolor="#0b1e25", plot_bgcolor="#0b1e25", font_color="#e5e5e5", font_size=14,
                      margin=dict(l=20, r=20, t=40, b=20))

    total = df["amount"].sum()
    per_year = df.groupby("year")["amount"].sum()

    summary = html.Div([
        html.Div(f"👑 All time Dividends: {total:.0f} €", style={"margin-bottom": "10px"}),
        *[
            html.Div(
                [
                    html.Span(f"📅 {int(y)}: {amt:.0f} €", style={"margin-right": "30px"})
                    for y, amt in per_year.items()][i:i+5]
                ,
                style={"margin-bottom": "5px"}
            )
            for i in range(0, len(per_year), 5)
        ]
    ], style={"text-align": "left", "list-style-type": "none", "padding": "0"})
    return fig, summary

# RAW dividend table — ALWAYS visible (remove the old toggle callback to avoid duplicate outputs)
@app.callback(
    Output("dividend-table-container", "children"),
    Input("dividend-chart", "id"),  # Trigger the callback when the chart is loaded
)
def render_dividend_table(_):
    try:
        with open(dividends_file, "r", encoding="utf-8") as f:
            dividends = yaml.safe_load(f) or []
    except Exception:
        dividends = []

    df = pd.DataFrame(dividends)
    if df.empty:
        return dbc.Alert("No dividend data yet.", color="secondary")

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"]).sort_values("date", ascending=False)

    table = dash_table.DataTable(
        columns=[{"name":"Date","id":"date"},{"name":"Company","id":"company"},{"name":"Net amount (€)","id":"amount"}],
        data=df.to_dict("records"),
        style_table={"overflowX":"auto"},
        #style_header={"backgroundColor":"#1e1e1e","color":"#fff","border":"0"},
        #style_cell={"backgroundColor":"#121212","color":"#ddd","border":"0","padding":"10px"},
        page_size=12, sort_action="native", filter_action="native",
    )
    return table

if __name__ == "__main__":
    start_scheduler_once()
    app.run(debug=False)
