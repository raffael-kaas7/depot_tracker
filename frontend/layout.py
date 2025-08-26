# layout.py
from dash import html, dcc
import dash_daq as daq
import dash_bootstrap_components as dbc

# ------------------------------
# Reusable bits
# ------------------------------

def create_summary_row(summary_items):
    """
    Create a responsive row of summary cards.
    """
    return dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.Div([
                        html.Span(item["icon"], style={"fontSize": "1.5rem", "marginRight": "0.5rem"}),
                        html.Span(item["label"], className="text-muted small"),
                    ], className="d-flex align-items-center mb-1"),
                    html.H5(
                        item["value"],
                        style={"color": item.get("color", 'light')},  # Use inline style for custom colors
                        className="fw-bold mb-0")
                ])
            ], className="shadow-sm h-100 bg-dark border-0")
        ], md=6, lg=3, sm=12) for item in summary_items
    ], className="mb-4 g-3")


# ------------------------------
# Main layout
# ------------------------------

def create_layout():
    """Define the main layout of the app in dark mode with a left sidebar."""

    sidebar = dbc.Card([
        dbc.CardBody([
            html.H2("Depot Tracker", className="h4 text-light mb-4", style={"fontFamily": "Inter, sans-serif"}),
            dbc.Nav([
                dbc.NavLink("📈 Assets", id="nav-assets", active=True, className="pill px-3 py-2"),
                dbc.NavLink("💸 Dividends", id="nav-dividends", active=False, className="pill px-3 py-2"),
            ], vertical=True, pills=True, className="gap-2"),
            html.Hr(className="border-secondary my-4"),
        ])
    ], className="sidebar")

    # --- Assets section ---
    assets_controls = dbc.Row(
        [
            # Slider on the left
            dbc.Col(
                [
                    daq.ToggleSwitch(
                        id="table-switch",
                        label="Separated Depots",
                        labelPosition="right",
                        value=False,  # Default value corresponds to "Combined Depots"
                        className="text-light",
                        style={"marginBottom": "16px", "width": "150px"},  # Adjust width for alignment
                    )
                ],
                md=6,  # Take half the row width
                align="center",  # Vertically align the slider
            ),
            # Buttons on the right
            dbc.Col(
                [
                    html.Div(
                        [
                            dbc.Button(
                                "Sync Depot 1",
                                id="auth-button-cd1",
                                color="primary",
                                className="me-2",
                            ),
                            dbc.Button(
                                "Sync Depot 2",
                                id="auth-button-cd2",
                                color="secondary",
                            ),
                        ],
                        className="d-flex justify-content-end",  # Right-align buttons
                    )
                ],
                md=6,  # Take the other half of the row width
                align="center",  # Vertically align the buttons
            ),
        ],
        className="align-items-center g-3 mb-3",  # Align items vertically and add spacing
    )

    assets_section = html.Div([
        html.Div(id="auth-status-cd1", className="text-muted mb-2"),
        html.Div(id="auth-status-cd2", className="text-muted mb-3"),
        assets_controls,
        html.Div(id="depot-table", className="mt-3")
    ], id="assets-section")

    # --- Dividends section ---
    dividends_section = html.Div([
        dbc.Row([
            dbc.Col([
                dcc.Graph(id="dividend-chart"),
                html.Div(id="dividend-summary", className="mt-4 text-light"),
                html.Hr(className="border-secondary my-4"),
                html.H5("Raw Dividend Data", className="text-light mb-2"),
                # Always visible raw data table
                html.Div(id="dividend-table-container"),
            ], width=12)
        ])
    ], id="dividends-section", style={"display": "none"})

    content = html.Div([
        html.Header([
            html.H1("Comdirect – Depot Tracker", className="text-light my-3 h1-app"),
        ], className="px-2"),
        html.Main([
            assets_section,
            dividends_section,
        ], className="px-2")
    ])

    return dbc.Container([
        dbc.Row([
            dbc.Col(sidebar, xs=12, sm=4, md=3, lg=2, className="mb-3"),
            dbc.Col(content, xs=12, sm=8, md=9, lg=10)
        ], className="g-3")
    ], fluid=True, className="p-3 bg-app")
