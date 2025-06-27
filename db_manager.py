from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import pandas as pd
from logger import setup_logger

logger = setup_logger(__name__)

class InfluxDBManager:
    """Manager for InfluxDB operations."""
    
    def __init__(self, url: str, token: str, org: str, bucket: str):
        self.client = InfluxDBClient(url=url, token=token, org=org)
        self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
        self.query_api = self.client.query_api()
        self.org = org
        self.bucket = bucket
        logger.info("InfluxDB client initialized")
    
    def write_sentiment_data(self, username: str, sentiment_data: Dict, timestamp: datetime = None):
        """Write sentiment analysis results to InfluxDB."""
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        try:
            point = Point("sentiment_analysis") \
                .tag("username", username) \
                .field("average_sentiment", sentiment_data['average_sentiment']) \
                .field("total_tweets", sentiment_data['total_tweets']) \
                .field("positive_count", sentiment_data['sentiment_distribution']['positive']) \
                .field("negative_count", sentiment_data['sentiment_distribution']['negative']) \
                .field("neutral_count", sentiment_data['sentiment_distribution']['neutral']) \
                .field("sentiment_label", sentiment_data['sentiment_label']) \
                .time(timestamp, WritePrecision.NS)
            
            self.write_api.write(bucket=self.bucket, org=self.org, record=point)
            logger.info(f"Sentiment data written for @{username}")
            
        except Exception as e:
            logger.error(f"Error writing sentiment data for @{username}: {e}")
    
    def write_price_correlation(self, correlation_data: Dict, timestamp: datetime = None):
        """Write price correlation analysis to InfluxDB."""
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        try:
            point = Point("price_correlation") \
                .field("oil_sentiment_correlation", correlation_data.get('oil_correlation', 0.0)) \
                .field("electricity_sentiment_correlation", correlation_data.get('electricity_correlation', 0.0)) \
                .field("oil_tweets_count", correlation_data.get('oil_tweets_count', 0)) \
                .field("electricity_tweets_count", correlation_data.get('electricity_tweets_count', 0)) \
                .time(timestamp, WritePrecision.NS)
            
            self.write_api.write(bucket=self.bucket, org=self.org, record=point)
            logger.info("Price correlation data written")
            
        except Exception as e:
            logger.error(f"Error writing price correlation data: {e}")
    
    def get_oil_prices(self, days_back: int = 30) -> pd.DataFrame:
        """Query oil price data from InfluxDB using new schema."""
        try:
            query = f'''
            from(bucket: "{self.bucket}")
                |> range(start: -{days_back}d)
                |> filter(fn: (r) => r["_measurement"] == "crude_oil_prices")
                |> filter(fn: (r) => r["_field"] == "price_usd")
                |> filter(fn: (r) => r["type"] == "wti_price" or r["type"] == "brent_price")
                |> pivot(rowKey:["_time"], columnKey: ["type"], valueColumn: "_value")
            '''
            
            result = self.query_api.query_data_frame(query, org=self.org)
            
            if not result.empty:
                result['_time'] = pd.to_datetime(result['_time'])
                result = result.set_index('_time')
                
                # Rename columns to match expected format
                if 'wti_price' in result.columns:
                    result = result.rename(columns={'wti_price': 'wti_price'})
                if 'brent_price' in result.columns:
                    result = result.rename(columns={'brent_price': 'brent_price'})
                
                logger.info(f"Retrieved {len(result)} oil price records")
            else:
                logger.warning("No oil price data found")
            
            return result
            
        except Exception as e:
            logger.error(f"Error querying oil prices: {e}")
            return pd.DataFrame()
    
    def get_electricity_prices(self, days_back: int = 30) -> pd.DataFrame:
        """Query German electricity price data from InfluxDB using new schema."""
        try:
            query = f'''
            from(bucket: "{self.bucket}")
                |> range(start: -{days_back}d)
                |> filter(fn: (r) => r["_measurement"] == "energy_data")
                |> filter(fn: (r) => r["_field"] == "value")
                |> filter(fn: (r) => r["county"] == "DE-LU")
                |> filter(fn: (r) => r["data_type"] == "actual")
                |> filter(fn: (r) => r["metric"] == "day_ahead_price_actual")
                |> pivot(rowKey:["_time"], columnKey: ["metric"], valueColumn: "_value")
            '''
            
            result = self.query_api.query_data_frame(query, org=self.org)
            
            if not result.empty:
                result['_time'] = pd.to_datetime(result['_time'])
                result = result.set_index('_time')
                
                # Rename column to match expected format
                if 'day_ahead_price_actual' in result.columns:
                    result = result.rename(columns={'day_ahead_price_actual': 'german_price'})
                
                logger.info(f"Retrieved {len(result)} electricity price records")
            else:
                logger.warning("No electricity price data found")
            
            return result
            
        except Exception as e:
            logger.error(f"Error querying electricity prices: {e}")
            return pd.DataFrame()
    
    def get_historical_sentiment(self, username: str = None, days_back: int = 30) -> pd.DataFrame:
        """Query historical sentiment data."""
        try:
            username_filter = f'|> filter(fn: (r) => r["username"] == "{username}")' if username else ''
            
            query = f'''
            from(bucket: "{self.bucket}")
                |> range(start: -{days_back}d)
                |> filter(fn: (r) => r["_measurement"] == "sentiment_analysis")
                {username_filter}
                |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
            '''
            
            result = self.query_api.query_data_frame(query, org=self.org)
            
            if not result.empty:
                result['_time'] = pd.to_datetime(result['_time'])
                result = result.set_index('_time')
                logger.info(f"Retrieved {len(result)} sentiment records")
            
            return result
            
        except Exception as e:
            logger.error(f"Error querying sentiment data: {e}")
            return pd.DataFrame()
    
    def close(self):
        """Close InfluxDB client connection."""
        self.client.close()
        logger.info("InfluxDB client connection closed")