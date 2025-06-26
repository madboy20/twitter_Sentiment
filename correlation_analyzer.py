import pandas as pd
import numpy as np
from scipy.stats import pearsonr, spearmanr
from typing import Dict, List, Tuple
from datetime import datetime, timedelta
from logger import setup_logger

logger = setup_logger(__name__)

class CorrelationAnalyzer:
    """Analyze correlations between sentiment and price movements."""
    
    def __init__(self):
        logger.info("Correlation analyzer initialized")
    
    def analyze_oil_sentiment_correlation(self, sentiment_data: List[Dict], oil_prices: pd.DataFrame) -> Dict:
        """Analyze correlation between oil-related sentiment and oil prices."""
        try:
            # Extract oil-related tweets and their sentiments
            oil_sentiments = []
            for account_data in sentiment_data:
                for tweet_sentiment in account_data.get('oil_related_tweets', []):
                    oil_sentiments.append({
                        'timestamp': tweet_sentiment['tweet']['timestamp'],
                        'sentiment': tweet_sentiment['combined_score']
                    })
            
            if not oil_sentiments or oil_prices.empty:
                logger.warning("Insufficient data for oil sentiment correlation")
                return self._empty_correlation_result()
            
            # Convert to DataFrame and aggregate by day
            sentiment_df = pd.DataFrame(oil_sentiments)
            sentiment_df['date'] = sentiment_df['timestamp'].dt.date
            daily_sentiment = sentiment_df.groupby('date')['sentiment'].mean().reset_index()
            daily_sentiment['date'] = pd.to_datetime(daily_sentiment['date'])
            
            # Prepare price data
            oil_prices_daily = oil_prices.resample('D').mean()
            
            # Merge data
            merged_data = pd.merge(daily_sentiment.set_index('date'), 
                                 oil_prices_daily, 
                                 left_index=True, right_index=True, how='inner')
            
            if len(merged_data) < 3:
                logger.warning("Insufficient overlapping data for correlation analysis")
                return self._empty_correlation_result()
            
            # Calculate correlations
            correlations = {}
            for price_col in ['wti_price', 'brent_price']:
                if price_col in merged_data.columns:
                    pearson_corr, pearson_p = pearsonr(merged_data['sentiment'], merged_data[price_col])
                    spearman_corr, spearman_p = spearmanr(merged_data['sentiment'], merged_data[price_col])
                    
                    correlations[price_col] = {
                        'pearson_correlation': pearson_corr,
                        'pearson_p_value': pearson_p,
                        'spearman_correlation': spearman_corr,
                        'spearman_p_value': spearman_p,
                        'data_points': len(merged_data)
                    }
            
            return {
                'correlations': correlations,
                'total_oil_tweets': len(oil_sentiments),
                'analysis_period_days': len(merged_data),
                'average_sentiment': merged_data['sentiment'].mean(),
                'sentiment_volatility': merged_data['sentiment'].std()
            }
            
        except Exception as e:
            logger.error(f"Error in oil sentiment correlation analysis: {e}")
            return self._empty_correlation_result()
    
    def analyze_electricity_sentiment_correlation(self, sentiment_data: List[Dict], electricity_prices: pd.DataFrame) -> Dict:
        """Analyze correlation between electricity-related sentiment and electricity prices."""
        try:
            # Extract electricity-related tweets and their sentiments
            electricity_sentiments = []
            for account_data in sentiment_data:
                for tweet_sentiment in account_data.get('electricity_related_tweets', []):
                    electricity_sentiments.append({
                        'timestamp': tweet_sentiment['tweet']['timestamp'],
                        'sentiment': tweet_sentiment['combined_score']
                    })
            
            if not electricity_sentiments or electricity_prices.empty:
                logger.warning("Insufficient data for electricity sentiment correlation")
                return self._empty_correlation_result()
            
            # Convert to DataFrame and aggregate by day
            sentiment_df = pd.DataFrame(electricity_sentiments)
            sentiment_df['date'] = sentiment_df['timestamp'].dt.date
            daily_sentiment = sentiment_df.groupby('date')['sentiment'].mean().reset_index()
            daily_sentiment['date'] = pd.to_datetime(daily_sentiment['date'])
            
            # Prepare price data
            electricity_prices_daily = electricity_prices.resample('D').mean()
            
            # Merge data
            merged_data = pd.merge(daily_sentiment.set_index('date'), 
                                 electricity_prices_daily, 
                                 left_index=True, right_index=True, how='inner')
            
            if len(merged_data) < 3:
                logger.warning("Insufficient overlapping data for correlation analysis")
                return self._empty_correlation_result()
            
            # Calculate correlations
            correlations = {}
            if 'german_price' in merged_data.columns:
                pearson_corr, pearson_p = pearsonr(merged_data['sentiment'], merged_data['german_price'])
                spearman_corr, spearman_p = spearmanr(merged_data['sentiment'], merged_data['german_price'])
                
                correlations['german_electricity'] = {
                    'pearson_correlation': pearson_corr,
                    'pearson_p_value': pearson_p,
                    'spearman_correlation': spearman_corr,
                    'spearman_p_value': spearman_p,
                    'data_points': len(merged_data)
                }
            
            return {
                'correlations': correlations,
                'total_electricity_tweets': len(electricity_sentiments),
                'analysis_period_days': len(merged_data),
                'average_sentiment': merged_data['sentiment'].mean(),
                'sentiment_volatility': merged_data['sentiment'].std()
            }
            
        except Exception as e:
            logger.error(f"Error in electricity sentiment correlation analysis: {e}")
            return self._empty_correlation_result()
    
    def identify_sentiment_shifts(self, current_sentiment: Dict, historical_sentiment: pd.DataFrame) -> Dict:
        """Identify significant sentiment shifts from previous periods."""
        try:
            if historical_sentiment.empty:
                return {'shifts': [], 'analysis': 'No historical data available'}
            
            # Get recent historical data (last 7 days)
            recent_data = historical_sentiment.tail(7)
            
            if len(recent_data) < 2:
                return {'shifts': [], 'analysis': 'Insufficient historical data'}
            
            # Calculate average historical sentiment
            historical_avg = recent_data['average_sentiment'].mean()
            current_avg = current_sentiment.get('average_sentiment', 0)
            
            # Calculate shift magnitude
            shift_magnitude = abs(current_avg - historical_avg)
            shift_direction = 'positive' if current_avg > historical_avg else 'negative'
            
            # Determine if shift is significant (threshold: 0.2)
            is_significant = shift_magnitude > 0.2
            
            shifts = []
            if is_significant:
                shifts.append({
                    'type': 'overall_sentiment',
                    'direction': shift_direction,
                    'magnitude': shift_magnitude,
                    'current_value': current_avg,
                    'historical_average': historical_avg,
                    'significance': 'high' if shift_magnitude > 0.4 else 'moderate'
                })
            
            return {
                'shifts': shifts,
                'analysis': f"Sentiment shift analysis completed. {'Significant' if is_significant else 'No significant'} changes detected.",
                'shift_magnitude': shift_magnitude,
                'shift_direction': shift_direction
            }
            
        except Exception as e:
            logger.error(f"Error in sentiment shift analysis: {e}")
            return {'shifts': [], 'analysis': f'Error in analysis: {str(e)}'}
    
    def _empty_correlation_result(self) -> Dict:
        """Return empty correlation result structure."""
        return {
            'correlations': {},
            'total_oil_tweets': 0,
            'total_electricity_tweets': 0,
            'analysis_period_days': 0,
            'average_sentiment': 0.0,
            'sentiment_volatility': 0.0
        }