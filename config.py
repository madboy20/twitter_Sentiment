import os
from dotenv import load_dotenv
from typing import Dict, Any

load_dotenv()

class Config:
    """Configuration management for the sentiment analysis system."""
    
    # Nitter Configuration
    NITTER_BASE_URL = os.getenv('NITTER_BASE_URL', 'https://nitter.net')
    NITTER_USERNAME = os.getenv('NITTER_USERNAME')
    NITTER_PASSWORD = os.getenv('NITTER_PASSWORD')
    
    # InfluxDB Configuration
    INFLUXDB_URL = os.getenv('INFLUXDB_URL', 'http://localhost:8086')
    INFLUXDB_TOKEN = os.getenv('INFLUXDB_TOKEN')
    INFLUXDB_ORG = os.getenv('INFLUXDB_ORG')
    INFLUXDB_BUCKET = os.getenv('INFLUXDB_BUCKET')
    
    # Email Configuration
    SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
    SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
    EMAIL_USERNAME = os.getenv('EMAIL_USERNAME')
    EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')
    RECIPIENT_EMAIL = os.getenv('RECIPIENT_EMAIL')
    
    # File Paths
    FOLLOWED_ACCOUNTS_FILE = os.getenv('FOLLOWED_ACCOUNTS_FILE', 'followed_accounts.txt')
    LOG_FILE = os.getenv('LOG_FILE', 'sentiment_analysis.log')
    
    # Analysis Configuration
    REPORT_TIME = os.getenv('REPORT_TIME', '08:00')
    TIMEZONE = os.getenv('TIMEZONE', 'UTC')
    DAYS_HISTORY = int(os.getenv('DAYS_HISTORY', '30'))
    MIN_TWEETS_FOR_ANALYSIS = int(os.getenv('MIN_TWEETS_FOR_ANALYSIS', '5'))
    
    # Keywords for price correlation
    OIL_KEYWORDS = ['WTI', 'Brent', 'crude oil', 'OPEC', 'oil price', 'petroleum', 'barrel']
    ELECTRICITY_KEYWORDS = ['Strompreis', 'Energiekosten', 'kWh', 'electricity price', 'power price', 'energy cost']
    
    @classmethod
    def validate_config(cls) -> bool:
        """Validate that all required configuration values are present."""
        required_vars = [
            'INFLUXDB_TOKEN', 'INFLUXDB_ORG', 'INFLUXDB_BUCKET',
            'EMAIL_USERNAME', 'EMAIL_PASSWORD', 'RECIPIENT_EMAIL'
        ]
        
        missing_vars = [var for var in required_vars if not getattr(cls, var)]
        
        if missing_vars:
            raise ValueError(f"Missing required configuration variables: {', '.join(missing_vars)}")
        
        return True