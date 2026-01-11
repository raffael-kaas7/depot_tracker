"""
Application Factory for Depot Tracker.

This module implements the application factory pattern for creating and configuring
Dash applications. The factory pattern allows for flexible application creation
with different configurations for development, testing, and production environments.

The factory handles:
- Dash app instantiation with Bootstrap CSS theming
- Configuration loading and application
- Callback registration for interactive components
- Layout setup for the main dashboard interface
- Background scheduler initialization for data updates
"""

from src.app.ui.callbacks.callbacks import register_callbacks
from app.services.scheduler_service import scheduler_service
from app.ui.layout import get_main_layout

from config.settings import get_settings, Config
from config.dash_config import DashConfig

from dash import Dash
import locale

def create_app(config_name: str = 'default') -> Dash:
    """
    Create and configure the Dash application instance.
    
    This factory function creates a Dash application with the specified configuration,
    sets up theming, registers all interactive callbacks, and initializes background
    services. The resulting app is ready to run and serve the depot tracking dashboard.
    
    Args:
        config_name: The configuration environment to use ('development', 'testing', 
                    'production', or 'default')
    
    Returns:
        A fully configured Dash application instance ready to serve requests
        
    Note:
        The function attempts to set German locale for proper number formatting
        in financial displays, but gracefully falls back if the locale is not available.
    """
    # Configure system locale for German number formatting (e.g., "1.234,56 €")
    # This is important for displaying financial amounts in the expected format
    try:
        locale.setlocale(locale.LC_ALL, 'de_DE.UTF-8')
    except locale.Error:
        # If German locale is not available, continue with system default
        # This prevents the app from crashing on systems without German locale
        pass
    
    # Load configuration settings for the specified environment
    settings: Config = get_settings(config_name)
    
    # Create Dash application instance with Bootstrap CSS framework
    # We use the Darkly theme from Bootswatch for a professional dark appearance
    # The Inter font provides excellent readability for financial data
    app = Dash(
        __name__,
        external_stylesheets=[
            # Darkly theme provides a dark, professional appearance suitable for dashboards
            "https://cdn.jsdelivr.net/npm/bootswatch@5.3.3/dist/darkly/bootstrap.min.css",
            # Inter font is optimized for UI and provides excellent readability for numbers
            "https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap",
        ],
        # Suppress callback exceptions during development to allow dynamic component creation
        suppress_callback_exceptions=True,
        # Set assets folder for custom CSS and JavaScript files
        assets_folder=settings.ASSETS_FOLDER
    )
    
    # Apply custom configuration to the Dash app and underlying Flask server
    DashConfig.init_app(app, settings)
    
    # Register all interactive callbacks that handle user interactions
    # Callbacks are functions that update the dashboard when users interact with components
    register_callbacks(app)
    
    # Set the main dashboard layout that defines the overall page structure
    app.layout = get_main_layout()
    
    # Initialize background scheduler for automated data updates after callbacks are registered
    # This ensures that the service registry is populated before the scheduler tries to use it
    scheduler_service.start_scheduler()
    
    return app
