# layout.py
from dash import html, dcc
import dash_bootstrap_components as dbc

def create_summary_row(summary_items):
    """
    Create a responsive row of summary cards.

    Parameters:
        summary_items (list): List of dictionaries with keys:
            - icon (str): Emoji or icon
            - label (str): Description text
            - value (str): Value text
            - color (str, optional): Bootstrap text color (e.g., 'success', 'danger')

    Returns:
        dbc.Row: Row of summary cards
    """

    return dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.Div([
                        html.Span(item["icon"], style={"fontSize": "1.5rem", "marginRight": "0.5rem"}),
                        html.Span(item["label"], className="text-muted small"),
                    ], className="d-flex align-items-center mb-1"),
                    html.H5(item["value"], className=f"text-{item.get('color', 'dark')} fw-bold mb-0")
                ])
            ], className="shadow-sm h-100")
        ], md=4, sm=12) for item in summary_items
    ], className="mb-4 g-3")

def create_layout():
    """
    Define the main layout of the app using Dash Bootstrap components and Tabs.

    Returns:
        dbc.Container: The main container layout
    """
    return dbc.Container([
        html.H1("🔥 Comdirect - Depot Tracker 🔥", className="text-center text-primary my-4", style={
            "fontFamily": "Inter, sans-serif"
        }),
        html.Div([
            dbc.Button("Authenticate", id="auth-button", color="primary", className="mb-4"),
            html.Div(id="auth-status", className="text-muted")
        ], className="text-center"),
        dcc.Tabs([
            dcc.Tab(label="📈 Assets", children=[
                dcc.RadioItems(
                    id="table-switch",
                    options=[
                        {"label": "Combined", "value": "combined"},
                        {"label": "Separated Depots", "value": "single"}
                    ],
                    value="combined",
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

            # dcc.Tab(label="🥧 Asset Allocation", children=[
            #     html.Div(id="asset-piechart", className="mt-4")
            # ], className="custom-tab", selected_className="custom-tab--selected"),

        ], className="mb-4", parent_className="custom-tabs"),
    ], fluid=True, className="p-4")