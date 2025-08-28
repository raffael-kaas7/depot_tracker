"""
Configuration settings for Depot Tracker.

This module defines configuration classes that manage application settings,
including API credentials, file paths, and environment-specific configurations.
All sensitive data is loaded from environment variables using the dotenv library
to prevent hardcoding secrets in the codebase.
"""
import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
# This enables local development with secrets stored in .env
load_dotenv()


class Config:
    """
    Base configuration class containing common settings for all environments.
    
    This class defines default values and common configuration options that
    are shared across development, testing, and production environments.
    Sensitive values like API credentials are loaded from environment variables.
    """
    
    # Application debug and testing flags
    DEBUG: bool = False
    TESTING: bool = False
    
    # File system paths - calculated relative to this configuration file
    BASE_DIR: Path = Path(__file__).parent.parent.parent  # Go up 3 levels: config -> src -> depot_tracker
    DATA_DIR: Path = BASE_DIR / 'data'  # Directory for storing JSON/YAML data files
    STATIC_DIR: Path = BASE_DIR / 'static'  # Directory for static web assets
    ASSETS_FOLDER: str = str(BASE_DIR / 'assets')  # Dash assets folder for CSS/JS
    
    # Depot configuration - names for the two tracked investment depots
    DEPOT_1_NAME: str = os.getenv("DEPOT_1_NAME", "Depot 1")  # Primary depot name
    DEPOT_2_NAME: str = os.getenv("DEPOT_2_NAME", "Depot 2")  # Secondary depot name
    
    # Comdirect API credentials - loaded from environment variables
    # These credentials are required to authenticate with the Comdirect banking API
    USERNAME_1: Optional[str] = os.getenv("USERNAME_1")  # First account username
    PASSWORD_1: Optional[str] = os.getenv("PASSWORD_1")  # First account password
    USERNAME_2: Optional[str] = os.getenv("USERNAME_2")  # Second account username
    PASSWORD_2: Optional[str] = os.getenv("PASSWORD_2")  # Second account password
    
    # Background task scheduler configuration
    SCHEDULER_API_ENABLED: bool = True  # Enable background price updates and snapshots
    SCHEDULER_TIMEZONE: str = 'Europe/Berlin'  # Timezone for scheduled tasks
    
    # Caching configuration for improved performance
    CACHE_DEFAULT_TIMEOUT: int = 300  # Default cache timeout in seconds (5 minutes)
    
    @classmethod
    def init_app(cls, app) -> None:
        """
        Initialize application with this configuration.
        
        This method can be overridden in subclasses to perform environment-specific
        initialization tasks such as setting up logging, database connections, etc.
        
        Args:
            app: The Dash application instance to initialize
        """
        pass


class DevelopmentConfig(Config):
    """
    Development environment configuration.
    
    This configuration is used during local development and includes debug features,
    verbose logging, and other developer-friendly settings that should not be
    enabled in production environments.
    """
    DEBUG: bool = True  # Enable debug mode for detailed error pages and auto-reload


class ProductionConfig(Config):
    """
    Production environment configuration.
    
    This configuration is used in production deployments and includes security-focused
    settings, performance optimizations, and proper error handling for live systems.
    """
    DEBUG: bool = False


class TestingConfig(Config):
    """
    Testing environment configuration.
    
    This configuration is used during automated testing and includes settings
    that make tests run faster and more reliably, such as disabled external
    API calls and in-memory data storage.
    """
    TESTING: bool = True
    WTF_CSRF_ENABLED: bool = False  # Disable CSRF protection for easier testing


# Configuration mapping for easy lookup by environment name
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}


def get_settings(config_name: str = 'default') -> Config:
    """
    Get configuration settings for the specified environment.
    
    This factory function returns the appropriate configuration class instance
    based on the provided environment name. It provides a clean interface
    for accessing configuration settings throughout the application.
    
    Args:
        config_name: The name of the configuration environment ('development', 
                    'testing', 'production', or 'default')
    
    Returns:
        An instance of the appropriate configuration class
        
    Raises:
        KeyError: If the specified config_name is not found in the config mapping
    """
    return config.get(config_name, DevelopmentConfig)
