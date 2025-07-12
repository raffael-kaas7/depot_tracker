from dash import Dash, Output, Input, dcc, html

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

# hard init two comdirect depots (uncomment if only one needed, setup in .env)

# init api and authenticate
api_cd_1 = ComdirectAPI(username=os.getenv("USERNAME_1"), pw=os.getenv("PASSWORD_1"), depot_name=os.getenv("DEPOT_1_NAME"), account_id=os.getenv("ACCOUNT_ID_1"), session_id="comdirect-active-depot", request_id="000001")
api_cd_1.authenticate()

# update offline data
api_cd_1.save_mock_positions(init_value=10000)
api_cd_1.save_mock_statements()
api_cd_1.save_mock_depot_id()

# init api and authenticate
api_cd_2 = ComdirectAPI(username=os.getenv("USERNAME_2"), pw=os.getenv("PASSWORD_2"), depot_name=os.getenv("DEPOT_2_NAME"), account_id=os.getenv("ACCOUNT_ID_2"), session_id="comdirect-dividend-depot", request_id="000002")
api_cd_2.authenticate()

# update offline data
api_cd_2.save_mock_positions(init_value=5000)
api_cd_1.save_mock_statements()
api_cd_2.save_mock_depot_id()

# data manager object to handle data base
data_cd_1 = DataManager(backend="yaml")
data_cd_2 = DataManager(backend="yaml")

# use service object to analyze depot data 
service_cd_1 = DepotService(api_cd_1, data_cd_1)
service_cd_2 = DepotService(api_cd_2, data_cd_2)

service_cd_1.extract_dividends_from_statements()
service_cd_2.extract_dividends_from_statements()

app.layout = create_layout()

@app.callback(
    Output("depot-table", "children"),
    Input("depot-table", "id")
)
def render_depot_table(_):

    def process_depot(positions, title):
        df = pd.json_normalize(positions)

        df["wkn"] = df["wkn"]
        df["count"] = pd.to_numeric(df["quantity.value"], errors="coerce")
        df["purchase_price"] = pd.to_numeric(df["purchasePrice.value"], errors="coerce")
        df["purchase_value"] = pd.to_numeric(df["purchaseValue.value"], errors="coerce")
        df["current_price"] = pd.to_numeric(df["currentPrice.price.value"], errors="coerce")
        df["current_value"] = pd.to_numeric(df["currentValue.value"], errors="coerce")
        df["performance_%"] = round(((df["current_value"] - df["purchase_value"]) / df["purchase_value"]) * 100, 2)

        # get name from wkn via yfinance
        df["name"] = df["wkn"].apply(wkn_to_name_lookup)

        # sum
        total_purchase_value = df["purchase_value"].sum()
        total_value = df["current_value"].sum()
        performance = ((total_value - total_purchase_value) / total_purchase_value) * 100 if total_purchase_value else 0

        table_header = html.Thead(html.Tr([
            html.Th("WKN"), html.Th("Name"), html.Th("Count"),
            html.Th("Purchase Price (€)"), html.Th("Purchase Value (€)"),
            html.Th("Current Price (€)"), html.Th("Current Value (€)"),
            html.Th("Performance (%)")
        ]))

        table_rows = []
        for _, row in df.iterrows():
            color = "green" if row["performance_%"] > 0 else "red" if row["performance_%"] < 0 else "gray"
            icon = "🚀" if row["performance_%"] > 60 else "💥" if row["performance_%"] < -45 else ""

            table_rows.append(html.Tr([
                html.Td(row["wkn"]),
                html.Td(row["name"]),
                html.Td(f"{row['count']:.2f}"),
                html.Td(f"{row['purchase_price']:.2f}"),
                html.Td(f"{row['purchase_value']:.2f}"),
                html.Td(f"{row['current_price']:.2f}"),
                html.Td(f"{row['current_value']:.2f}"),
                html.Td(f"{icon} {row['performance_%']:.2f}%", style={"color": color, "fontWeight": "bold"})
            ]))

        # End line
        summary_row = html.Tr([
            html.Td("Total", colSpan=4, style={"fontWeight": "bold"}),
            html.Td(f"{total_purchase_value:.2f} €", style={"fontWeight": "bold"}),
            html.Td(),
            html.Td(f"{total_value:.2f} €", style={"fontWeight": "bold"}),
            html.Td(f"{performance:.2f} %", style={
                "fontWeight": "bold",
                "color": "green" if performance > 0 else "red" if performance < 0 else "gray"
            })
        ])

        table = html.Table(
            children=[table_header, html.Tbody(table_rows + [summary_row])],
            className="table table-hover table-striped table-bordered shadow-sm rounded"
        )

        return html.Div([
            html.H4(title, className="mt-4 mb-3"),
            table
        ])

    # Hole Positionen beider Depots
    pos1 = service_cd_1.fetch_positions()
    pos2 = service_cd_2.fetch_positions()

    table1 = process_depot(pos1, "📁 Aktiv-Depot")
    table2 = process_depot(pos2, "💸 Dividenden-Depot")

    return html.Div([table1, table2])


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
            "layout": {"title": "Aktiv-Depot"}
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
            "layout": {"title": "Dividenden-Depot"}
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
    with open("data/dividends.yaml", "r") as f:
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
        height=450
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
    with open("data/dividends.yaml", "r") as f:
        dividends = yaml.safe_load(f) or []

    df = pd.DataFrame(dividends)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])

    years = sorted(df["date"].dt.year.unique())
    options = [{"label": str(y), "value": y} for y in years]

    print("📅 Verfügbare Jahre:", years)
    return options, years

if __name__ == "__main__":
    app.run(debug=False)
