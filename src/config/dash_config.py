"""
Dash-specific configuration.

This module contains configuration utilities specifically for the Dash web framework.
Dash is a Python web framework that allows building interactive web applications
with pure Python, without requiring HTML, CSS, or JavaScript knowledge.
The configuration here sets up the Dash app's server properties and integrates
our custom settings with Dash's internal configuration system.
"""
import os
from typing import Any
from dash import Dash


class DashConfig:
    """
    Configuration manager for Dash application setup.
    
    This class provides static methods to initialize and configure a Dash application
    instance with our custom settings. It handles server configuration, security
    settings, and integration between our config system and Dash's requirements.
    """
    
    @staticmethod
    def init_app(app: Dash, settings: Any) -> Dash:
        """
        Initialize Dash application with custom settings.
        
        This method configures the underlying Flask server that powers the Dash app,
        sets up security configurations, and transfers our custom settings into
        the Dash/Flask configuration system for use throughout the application.
        
        Args:
            app: The Dash application instance to configure
            settings: Configuration object containing application settings
            
        Returns:
            The configured Dash application instance
            
        Note:
            The secret key is critical for session security in Flask. In production,
            this should always be loaded from an environment variable and never
            hardcoded in the source code.
        """
        
        # Get the underlying Flask server instance from Dash
        # Dash runs on top of Flask, so we configure the Flask server directly
        server = app.server
        
        # Configure Flask server security settings
        # The secret key is used for session management and CSRF protection
        secret_key = os.getenv('SECRET_KEY', 'dev-key-change-in-production')
        server.secret_key = secret_key
        
        # Set application metadata that appears in browser tabs and bookmarks
        app.title = "Depot Tracker - Investment Portfolio Dashboard"
        
        # Transfer our custom settings to Flask's config system
        # This makes settings accessible in Flask contexts and Dash callbacks
        server.config.update(vars(settings))
        
        return app
