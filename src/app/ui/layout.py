"""
Main layout for the Depot Tracker application
"""
from dash import html, dcc

from app.ui.components.layout import create_layout


def get_main_layout():
    """
    Returns the main layout for the Dash application
    """
    return html.Div([
        dcc.Location(id='url', refresh=False),
        html.Div(id='page-content', children=create_layout())
    ])
