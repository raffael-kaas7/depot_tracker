from dash import Dash, Output, Input
from frontend.layout import create_layout
from backend.api.comdirect_api import ComdirectAPI
from backend.data.data_manager import DataManager
from backend.logic.depot_service import DepotService

import os
from dotenv import load_dotenv
import pandas as pd

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
api_cd_1 = ComdirectAPI(username=os.getenv("USERNAME_1"), pw=os.getenv("PASSWORD_1"), depot_name="comdirect-active", session_id="comdirect-active-depot", request_id="000001")
api_cd_1.authenticate()
api_cd_1.save_mock_positions(target_value=100000)
#api_cd_1.save_mock_statements()
api_cd_1.save_mock_depot_id()

# init api and authenticate
api_cd_2 = ComdirectAPI(username=os.getenv("USERNAME_2"), pw=os.getenv("PASSWORD_2"), depot_name="comdirect-dividends", session_id="comdirect-dividend-depot", request_id="000002")
api_cd_2.authenticate()
api_cd_2.save_mock_positions(target_value=30000)
#api_cd_1.save_mock_statements()
api_cd_2.save_mock_depot_id()

# data manager object to handle data base
data_cd_1 = DataManager(backend="yaml")
data_cd_2 = DataManager(backend="yaml")

# use service object to analyze depot data 
service_cd_1 = DepotService(api_cd_1, data_cd_1)
service_cd_2 = DepotService(api_cd_2, data_cd_2)

app.layout = create_layout()

@app.callback(
    Output("depot-table", "children"),
    Input("depot-table", "id")
)
def render_depot_table(_):
    import pandas as pd
    from dash import html

    def process_positions(positions):
        df = pd.json_normalize(positions)

        df["wkn"] = df.get("instrument.wkn", df.get("wkn"))
        df["stueck"] = pd.to_numeric(df["quantity.value"], errors="coerce")
        df["kaufpreis"] = pd.to_numeric(df["purchasePrice.value"], errors="coerce")
        df["kaufwert"] = pd.to_numeric(df["purchaseValue.value"], errors="coerce")
        df["aktuell_preis"] = pd.to_numeric(df["currentPrice.price.value"], errors="coerce")
        df["aktuell_wert"] = pd.to_numeric(df["currentValue.value"], errors="coerce")
        df["performance_%"] = round(((df["aktuell_wert"] - df["kaufwert"]) / df["kaufwert"]) * 100, 2)

        return df

    def make_table(df, title):
        from dash import html

        table_header = html.Thead(html.Tr([
            html.Th("📄 WKN"), html.Th("📌 Stück"),
            html.Th("💰 Kaufpreis"), html.Th("🧾 Kaufwert"),
            html.Th("📈 Akt. Preis"), html.Th("💼 Akt. Wert"),
            html.Th("📊 Veränderung")
        ]))

        table_rows = []
        for _, row in df.iterrows():
            performance = row["performance_%"]
            perf_icon = "⬆️" if performance > 0 else ("⬇️" if performance < 0 else "➡️")
            perf_color = "green" if performance > 0 else ("red" if performance < 0 else "gray")

            table_rows.append(html.Tr([
                html.Td(row["wkn"]),
                html.Td(f"{row['stueck']:.2f}"),
                html.Td(f"{row['kaufpreis']:.2f} €"),
                html.Td(f"{row['kaufwert']:.2f} €"),
                html.Td(f"{row['aktuell_preis']:.2f} €"),
                html.Td(f"{row['aktuell_wert']:.2f} €"),
                html.Td([
                    html.Span(perf_icon + f" {performance:.2f} %",
                            style={"color": perf_color, "fontWeight": "bold"})
                ])
            ]))

        return html.Div([
            html.H4(title, className="mb-3 mt-4"),
            html.Div([
                html.Table(
                    children=[table_header, html.Tbody(table_rows)],
                    className="table table-hover table-sm border rounded shadow-sm"
                )
            ], className="table-responsive")
        ], className="p-3 bg-light rounded shadow-sm")


    # → Daten abrufen und verarbeiten
    df1 = process_positions(service_cd_1.fetch_positions())
    df2 = process_positions(service_cd_2.fetch_positions())

    # → Rückgabe: beide Tabellen untereinander
    return html.Div([
        make_table(df1, "📁 Aktiv-Depot"),
        make_table(df2, "💸 Dividenden-Depot")
    ])



if __name__ == "__main__":
    app.run(debug=False)
