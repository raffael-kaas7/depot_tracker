#!/usr/bin/env python3
"""
Main entry point for the Depot Tracker application.

This module serves as the application launcher, setting up the Python path,
loading configuration from environment variables, and starting the Dash server.
The application tracks investment depot performance using real-time data from
various financial APIs.
"""
import os
import sys
from pathlib import Path

# Add src directory to Python path to enable imports from our custom modules
src_path = Path(__file__).parent / 'src'
sys.path.insert(0, str(src_path))

from src.app.app_factory import create_app


def main() -> None:
    """
    Main application entry point.
    
    Loads configuration from environment variables, creates the Dash application
    instance, and starts the development server. The server configuration
    (host, port, debug mode) can be controlled via environment variables.
    """
    # Determine configuration based on environment variable
    # Defaults to 'development' for local development with debug features
    config_name: str = os.getenv('FLASK_ENV', 'development')
    
    # Create the Dash application instance with specified configuration
    app = create_app(config_name)
    
    # Server configuration from environment variables with sensible defaults
    port: int = int(os.getenv('PORT', 8000))  # Default port for local development
    host: str = str(os.getenv('HOST', 'localhost'))  # Bind to localhost by default
    debug: bool = config_name == 'development'  # Enable debug mode in development
    
    # Display startup information for debugging and monitoring
    print(f"🚀 Starting Depot Tracker on http://{host}:{port}")
    print(f"📊 Environment: {config_name}")
    print(f"🔧 Debug mode: {debug}")
    
    # Start the Dash development server
    # In production, this should be replaced with a proper WSGI server
    app.run(
        host=host,
        port=port,
        debug=False
    )


if __name__ == '__main__':
    main()
