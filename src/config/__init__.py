"""
Configuration package
"""
from .settings import get_settings, config
from .dash_config import DashConfig

__all__ = ['get_settings', 'config', 'DashConfig']
