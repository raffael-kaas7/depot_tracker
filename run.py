#!/usr/bin/env python3
"""
Main entry point for the Depot Tracker application
"""
import os
import sys
from pathlib import Path

# Add src directory to Python path
src_path = Path(__file__).parent / 'src'
sys.path.insert(0, str(src_path))

from src.app import create_app

if __name__ == '__main__':
    # Determine configuration based on environment
    config_name = os.getenv('FLASK_ENV', 'development')
    
    # Create the application
    app = create_app(config_name)
    
    # Run the application
    port = int(os.getenv('PORT', 8000))
    debug = config_name == 'development'
    
    print(f"🚀 Starting Depot Tracker on http://localhost:{port}")
    print(f"📊 Environment: {config_name}")
    print(f"🔧 Debug mode: {debug}")
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug
    )
