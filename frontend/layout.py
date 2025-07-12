# layout.py
from dash import html, dcc
import dash_bootstrap_components as dbc

def create_layout():
    return dbc.Container([
        html.H1("📊 Depot Tracker", className="text-center text-primary my-4", style={
            "fontFamily": "Inter, sans-serif"
        }),

        dcc.Tabs([
            dcc.Tab(label="📄 Depotpositionen", children=[
                dcc.RadioItems(
                    id="table-switch",
                    options=[
                        {"label": "Depots", "value": "single"},
                        {"label": "Combined Positions", "value": "combined"}
                    ],
                    value="single",
                    inline=True
                ),
                html.Div(id="depot-table", className="mt-4")
            ], className="custom-tab", selected_className="custom-tab--selected"),

            dcc.Tab(label="📊 Dividenden", children=[
                html.Div([
                    html.H5("📅 Jahre auswählen:", className="mb-2"),
                    dcc.Checklist(
                        id="year-selector",
                        inline=True,
                        labelStyle={"marginRight": "10px"},
                        style={"marginBottom": "20px"}
                    ),
                    dcc.Graph(id="dividenden-chart"),
                    html.Div(id="dividenden-summary", className="mt-4"),
                    html.Button("Tabelle ein-/ausblenden", id="toggle-table-btn"),
                    html.Div(id="dividenden-table-container", style={"display": "none"}),  # Tabelle standardmäßig ausgeblendet
                ])
            ]),

            dcc.Tab(label="🥧 Asset Allocation", children=[
                html.Div(id="asset-piechart", className="mt-4")
            ], className="custom-tab", selected_className="custom-tab--selected"),

        ], className="mb-4", parent_className="custom-tabs"),
    ], fluid=True, className="p-4")