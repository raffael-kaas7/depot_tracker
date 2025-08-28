"""
Basic tests for the Depot Tracker application structure
"""
import unittest
import sys
import os
from pathlib import Path

# Add src to path for testing
project_root = Path(__file__).parent.parent
src_path = project_root / 'src'
sys.path.insert(0, str(src_path))


class TestApplicationStructure(unittest.TestCase):
    """Test that the application structure is correct"""
    
    def test_can_import_app_factory(self):
        """Test that we can import the app factory"""
        try:
            from src.app import create_app
            self.assertTrue(callable(create_app))
        except ImportError as e:
            self.fail(f"Failed to import create_app: {e}")
    
    def test_can_import_config(self):
        """Test that we can import configuration"""
        try:
            from src.config import get_settings
            settings = get_settings('testing')
            self.assertIsNotNone(settings)
        except ImportError as e:
            self.fail(f"Failed to import config: {e}")
    
    def test_required_directories_exist(self):
        """Test that required directories exist"""
        required_dirs = [
            'src/app',
            'src/app/api',
            'src/app/services', 
            'src/app/ui',
            'src/config',
            'src/utils',
            'static',
            'tests'
        ]
        
        for dir_path in required_dirs:
            full_path = project_root / dir_path
            self.assertTrue(full_path.exists(), f"Required directory {dir_path} does not exist")


if __name__ == '__main__':
    unittest.main()
