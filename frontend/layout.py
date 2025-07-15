# layout.py
from dash import html, dcc
import dash_bootstrap_components as dbc

def create_layout():
    return dbc.Container([
        html.H1("🔥 Comdirect - Depot Tracker 🔥", className="text-center text-primary my-4", style={
            "fontFamily": "Inter, sans-serif"
        }),

        dcc.Tabs([
            dcc.Tab(label="📈 Assets", children=[
                dcc.RadioItems(
                    id="table-switch",
                    options=[
                        {"label": "Separated Depots", "value": "single"},
                        {"label": "Combined", "value": "combined"}
                    ],
                    value="single",
                    inline=True,
                    style={
                        "display": "flex",
                        "gap": "10px",  # distance between the buttons
                        "alignItems": "center",
                        "padding": "5px"
                    } 
                ),
                html.Div(id="depot-table", className="mt-4")
            ], className="custom-tab", selected_className="custom-tab--selected"),

            dcc.Tab(label="💸 Dividends", children=[
                html.Div([
                    html.H5("📅 Show allocated dividends of: ", className="mb-2"),
                    dcc.Checklist(
                        id="year-selector",
                        inline=True,
                        labelStyle={"marginRight": "10px"},
                        style={"marginBottom": "20px"}
                    ),
                    dcc.Graph(id="dividend-chart"),
                    html.Div(id="dividend-summary", className="mt-4"),
                    html.Button("Show Details", id="toggle-table-btn"),
                    html.Div(id="dividend-table-container", style={"display": "none"}),  # not shown by default
                ])
            ]),

            dcc.Tab(label="🥧 Asset Allocation", children=[
                html.Div(id="asset-piechart", className="mt-4")
            ], className="custom-tab", selected_className="custom-tab--selected"),

        ], className="mb-4", parent_className="custom-tabs"),
    ], fluid=True, className="p-4")