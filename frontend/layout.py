from dash import dcc, html
import dash_bootstrap_components as dbc

def create_layout():
    return dbc.Container([
        html.H1("Depot Tracker", className="text-center text-primary mb-4"),
        dcc.Tabs([
            dcc.Tab(label="📄 Depotpositionen", children=[
                html.Div(id="depot-table")
            ]),
            dcc.Tab(label="🥧 Asset Allocation", children=[
                html.Div(id="asset-piechart")
            ]),
            dcc.Tab(label="📊 Dividenden", children=[
                html.Div(id="dividenden-chart")
            ])
        ])
    ], fluid=True)
