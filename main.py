#!/usr/bin/env python3
"""
Twitter Sentiment Analysis with Price Correlation
Main execution script for daily sentiment analysis and reporting.
"""

import os
import sys
import schedule
import time
from datetime import datetime, timedelta
from typing import List, Dict

# Import custom modules
from config import Config
from logger import setup_logger
from bird_makeup_client import BirdMakeupClient
from sentiment_analyzer import SentimentAnalyzer
from influxdb_client import InfluxDBManager
from correlation_analyzer import CorrelationAnalyzer
from report_generator import ReportGenerator

# Setup logging
logger = setup_logger(__name__)

class SentimentAnalysisSystem:
    """Main system orchestrator for sentiment analysis."""
    
    def __init__(self):
        """Initialize the sentiment analysis system."""
        try:
            # Validate configuration
            Config.validate_config()
            
            # Initialize components
            self.bird_makeup_client = BirdMakeupClient(
                Config.get_base_url(),
                Config.get_username(),
                Config.get_password()
            )
            
            self.sentiment_analyzer = SentimentAnalyzer()
            
            self.influx_manager = InfluxDBManager(
                Config.INFLUXDB_URL,
                Config.INFLUXDB_TOKEN,
                Config.INFLUXDB_ORG,
                Config.INFLUXDB_BUCKET
            )
            
            self.correlation_analyzer = CorrelationAnalyzer()
            
            self.report_generator = ReportGenerator(
                Config.SMTP_SERVER,
                Config.SMTP_PORT,
                Config.EMAIL_USERNAME,
                Config.EMAIL_PASSWORD
            )
            
            # Test connection
            if not self.bird_makeup_client.test_connection():
                logger.warning("Could not verify connection to Bird.makeup instance")
            
            logger.info("Sentiment analysis system initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize system: {e}")
            raise
    
    def load_followed_accounts(self) -> List[str]:
        """Load the list of followed Twitter accounts."""
        try:
            if not os.path.exists(Config.FOLLOWED_ACCOUNTS_FILE):
                logger.error(f"Followed accounts file not found: {Config.FOLLOWED_ACCOUNTS_FILE}")
                return []
            
            with open(Config.FOLLOWED_ACCOUNTS_FILE, 'r', encoding='utf-8') as f:
                accounts = [line.strip().lstrip('@') for line in f if line.strip() and not line.startswith('#')]
            
            logger.info(f"Loaded {len(accounts)} followed accounts")
            return accounts
            
        except Exception as e:
            logger.error(f"Error loading followed accounts: {e}")
            return []
    
    def analyze_account_sentiment(self, username: str) -> Dict:
        """Analyze sentiment for a single account."""
        try:
            logger.info(f"Analyzing sentiment for @{username}")
            
            # Fetch tweets from the last day
            tweets = self.bird_makeup_client.get_user_tweets(username, days_back=1)
            
            if len(tweets) < Config.MIN_TWEETS_FOR_ANALYSIS:
                logger.warning(f"Insufficient tweets for @{username}: {len(tweets)} (minimum: {Config.MIN_TWEETS_FOR_ANALYSIS})")
                return None
            
            # Analyze sentiment
            sentiment_analysis = self.sentiment_analyzer.analyze_tweets_batch(tweets)
            sentiment_analysis['username'] = username
            
            # Store in InfluxDB
            self.influx_manager.write_sentiment_data(username, sentiment_analysis)
            
            logger.info(f"Completed sentiment analysis for @{username}: {sentiment_analysis['average_sentiment']:.3f}")
            return sentiment_analysis
            
        except Exception as e:
            logger.error(f"Error analyzing sentiment for @{username}: {e}")
            return None
    
    def run_daily_analysis(self):
        """Run the complete daily sentiment analysis."""
        try:
            logger.info("Starting daily sentiment analysis")
            start_time = datetime.now()
            
            # Load followed accounts
            accounts = self.load_followed_accounts()
            if not accounts:
                logger.error("No accounts to analyze")
                return
            
            # Analyze sentiment for each account
            account_analyses = []
            for username in accounts:
                analysis = self.analyze_account_sentiment(username)
                if analysis:
                    account_analyses.append(analysis)
                
                # Rate limiting
                time.sleep(2)
            
            if not account_analyses:
                logger.error("No successful sentiment analyses completed")
                return
            
            logger.info(f"Completed sentiment analysis for {len(account_analyses)} accounts")
            
            # Get price data for correlation analysis
            oil_prices = self.influx_manager.get_oil_prices(days_back=Config.DAYS_HISTORY)
            electricity_prices = self.influx_manager.get_electricity_prices(days_back=Config.DAYS_HISTORY)
            
            # Perform correlation analysis
            oil_correlation = self.correlation_analyzer.analyze_oil_sentiment_correlation(
                account_analyses, oil_prices
            )
            
            electricity_correlation = self.correlation_analyzer.analyze_electricity_sentiment_correlation(
                account_analyses, electricity_prices
            )
            
            # Store correlation results
            correlation_data = {
                'oil_correlation': oil_correlation.get('correlations', {}).get('wti_price', {}).get('pearson_correlation', 0),
                'electricity_correlation': electricity_correlation.get('correlations', {}).get('german_electricity', {}).get('pearson_correlation', 0),
                'oil_tweets_count': oil_correlation.get('total_oil_tweets', 0),
                'electricity_tweets_count': electricity_correlation.get('total_electricity_tweets', 0)
            }
            
            self.influx_manager.write_price_correlation(correlation_data)
            
            # Analyze sentiment shifts
            historical_sentiment = self.influx_manager.get_historical_sentiment(days_back=Config.DAYS_HISTORY)
            overall_sentiment = {
                'average_sentiment': sum(acc['average_sentiment'] for acc in account_analyses) / len(account_analyses)
            }
            sentiment_shifts = self.correlation_analyzer.identify_sentiment_shifts(
                overall_sentiment, historical_sentiment
            )
            
            # Extract trending topics (simplified implementation)
            trending_topics = self._extract_trending_topics(account_analyses)
            
            # Compile results for reporting
            analysis_results = {
                'account_analyses': account_analyses,
                'correlations': {
                    'oil_correlation': oil_correlation,
                    'electricity_correlation': electricity_correlation
                },
                'sentiment_shifts': sentiment_shifts,
                'trending_topics': trending_topics,
                'execution_time': (datetime.now() - start_time).total_seconds()
            }
            
            # Generate and send report
            self._send_daily_report(analysis_results)
            
            logger.info(f"Daily analysis completed successfully in {analysis_results['execution_time']:.2f} seconds")
            
        except Exception as e:
            logger.error(f"Error in daily analysis: {e}")
            self._send_error_notification(str(e))
    
    def _extract_trending_topics(self, account_analyses: List[Dict]) -> List[str]:
        """Extract trending topics from tweets (simplified implementation)."""
        try:
            import re
            from collections import Counter
            
            # Extract hashtags and keywords
            all_text = []
            for analysis in account_analyses:
                for sentiment in analysis.get('individual_sentiments', []):
                    tweet_text = sentiment.get('tweet_data', {}).get('text', '')
                    all_text.append(tweet_text)
            
            # Find hashtags
            hashtags = []
            for text in all_text:
                hashtags.extend(re.findall(r'#(\w+)', text.lower()))
            
            # Get most common hashtags
            hashtag_counts = Counter(hashtags)
            trending = [tag for tag, count in hashtag_counts.most_common(20) if count > 1]
            
            return trending
            
        except Exception as e:
            logger.error(f"Error extracting trending topics: {e}")
            return []
    
    def _send_daily_report(self, analysis_results: Dict):
        """Generate and send the daily report."""
        try:
            logger.info("Generating daily report")
            
            # Generate report HTML
            report_html = self.report_generator.generate_daily_report(analysis_results)
            
            # Send report
            subject = f"Daily Sentiment Analysis Report - {datetime.now().strftime('%Y-%m-%d')}"
            success = self.report_generator.send_report(
                Config.RECIPIENT_EMAIL,
                subject,
                report_html
            )
            
            if success:
                logger.info("Daily report sent successfully")
            else:
                logger.error("Failed to send daily report")
                
        except Exception as e:
            logger.error(f"Error sending daily report: {e}")
    
    def _send_error_notification(self, error_message: str):
        """Send error notification email."""
        try:
            subject = f"Sentiment Analysis System Error - {datetime.now().strftime('%Y-%m-%d')}"
            error_html = f"""
            <html>
            <body>
                <h2>Sentiment Analysis System Error</h2>
                <p><strong>Time:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                <p><strong>Error:</strong> {error_message}</p>
                <p>Please check the system logs for more details.</p>
            </body>
            </html>
            """
            
            self.report_generator.send_report(Config.RECIPIENT_EMAIL, subject, error_html)
            logger.info("Error notification sent")
            
        except Exception as e:
            logger.error(f"Failed to send error notification: {e}")
    
    def start_scheduler(self):
        """Start the scheduled daily analysis."""
        logger.info(f"Starting scheduler - daily analysis at {Config.REPORT_TIME}")
        
        # Schedule daily analysis
        schedule.every().day.at(Config.REPORT_TIME).do(self.run_daily_analysis)
        
        # Run immediately if requested
        if len(sys.argv) > 1 and sys.argv[1] == '--run-now':
            logger.info("Running analysis immediately")
            self.run_daily_analysis()
        
        # Keep the scheduler running
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    
    def cleanup(self):
        """Cleanup resources."""
        try:
            self.influx_manager.close()
            logger.info("System cleanup completed")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

def main():
    """Main entry point."""
    system = None
    try:
        logger.info("Starting Twitter Sentiment Analysis System with Bird.makeup")
        
        # Initialize system
        system = SentimentAnalysisSystem()
        
        # Start scheduler
        system.start_scheduler()
        
    except KeyboardInterrupt:
        logger.info("System shutdown requested")
    except Exception as e:
        logger.error(f"System error: {e}")
    finally:
        if system:
            system.cleanup()

if __name__ == "__main__":
    main()