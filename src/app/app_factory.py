"""
Application Factory for Depot Tracker
"""
from dash import Dash
import dash_bootstrap_components as dbc
from flask import Flask
import locale

from config.settings import get_settings
from config.dash_config import DashConfig


def create_app(config_name='default'):
    """
    Create and configure the Dash application
    """
    # German formatting if available
    try:
        locale.setlocale(locale.LC_ALL, 'de_DE.UTF-8')
    except Exception:
        pass
    
    settings = get_settings(config_name)
    
    # Create Dash app with Bootstrap theme
    app = Dash(
        __name__,
        external_stylesheets=[
            "https://cdn.jsdelivr.net/npm/bootswatch@5.3.3/dist/darkly/bootstrap.min.css",
            "https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap",
        ],
        suppress_callback_exceptions=True,
        assets_folder=settings.ASSETS_FOLDER
    )
    
    # Configure the app
    DashConfig.init_app(app, settings)
    
    # Import and register callbacks
    from app.ui.callbacks import register_callbacks
    register_callbacks(app)
    
    # Set layout
    from app.ui.layout import get_main_layout
    app.layout = get_main_layout()
    
    # Initialize scheduler after callbacks are registered
    from app.services.scheduler_service import scheduler_service
    scheduler_service.start_scheduler()
    
    return app
