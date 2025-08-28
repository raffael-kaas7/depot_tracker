"""
Configuration settings for Depot Tracker
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Base configuration class"""
    
    # App settings
    DEBUG = False
    TESTING = False
    
    # Paths
    BASE_DIR = Path(__file__).parent.parent.parent  # Go up 3 levels: config -> src -> depot_tracker
    DATA_DIR = BASE_DIR / 'data'
    STATIC_DIR = BASE_DIR / 'static'
    ASSETS_FOLDER = str(BASE_DIR / 'assets')
    
    # API Configuration
    DEPOT_1_NAME = os.getenv("DEPOT_1_NAME", "Depot 1")
    DEPOT_2_NAME = os.getenv("DEPOT_2_NAME", "Depot 2")
    
    USERNAME_1 = os.getenv("USERNAME_1")
    PASSWORD_1 = os.getenv("PASSWORD_1")
    USERNAME_2 = os.getenv("USERNAME_2") 
    PASSWORD_2 = os.getenv("PASSWORD_2")
    
    # Scheduler settings
    SCHEDULER_API_ENABLED = True
    SCHEDULER_TIMEZONE = 'Europe/Berlin'
    
    # Cache settings
    CACHE_DEFAULT_TIMEOUT = 300
    
    @classmethod
    def init_app(cls, app):
        """Initialize application with this config"""
        pass


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False


class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    WTF_CSRF_ENABLED = False


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}


def get_settings(config_name='default'):
    """Get configuration settings"""
    return config.get(config_name, DevelopmentConfig)
