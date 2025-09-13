"""Configuration settings."""

import os

class Config:
    """Application configuration."""
    
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key'
    DATABASE_URL = os.environ.get('DATABASE_URL') or 'sqlite:///app.db'
    DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'
    
    @staticmethod
    def get_database_config():
        """Get database configuration."""
        return {
            'url': Config.DATABASE_URL,
            'echo': Config.DEBUG
        }
