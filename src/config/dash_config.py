"""
Dash-specific configuration
"""


class DashConfig:
    """Configuration for Dash application"""
    
    @staticmethod
    def init_app(app, settings):
        """Initialize Dash app with settings"""
        
        # Set server configuration
        server = app.server
        server.secret_key = 'your-secret-key-here'  # In production, use a secure secret
        
        # Apply configuration
        app.title = "Depot Tracker"
        
        # Store settings for use in callbacks
        server.config.update(vars(settings))
        
        return app
