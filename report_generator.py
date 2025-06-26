import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import io
import base64
from datetime import datetime
from typing import Dict, List
from logger import setup_logger

logger = setup_logger(__name__)

class ReportGenerator:
    """Generate and send daily sentiment analysis reports."""
    
    def __init__(self, smtp_server: str, smtp_port: int, username: str, password: str):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        logger.info("Report generator initialized")
    
    def generate_daily_report(self, analysis_results: Dict) -> str:
        """Generate HTML report from analysis results."""
        try:
            html_content = self._create_html_template()
            
            # Insert summary data
            html_content = html_content.replace('{{DATE}}', datetime.now().strftime('%Y-%m-%d'))
            html_content = html_content.replace('{{TOTAL_ACCOUNTS}}', str(len(analysis_results.get('account_analyses', []))))
            html_content = html_content.replace('{{TOTAL_TWEETS}}', str(sum(acc.get('total_tweets', 0) for acc in analysis_results.get('account_analyses', []))))
            
            # Generate top accounts sections
            top_positive, top_negative = self._get_top_accounts(analysis_results.get('account_analyses', []))
            html_content = html_content.replace('{{TOP_POSITIVE}}', self._format_account_list(top_positive))
            html_content = html_content.replace('{{TOP_NEGATIVE}}', self._format_account_list(top_negative))
            
            # Add sentiment shifts
            shifts_html = self._format_sentiment_shifts(analysis_results.get('sentiment_shifts', {}))
            html_content = html_content.replace('{{SENTIMENT_SHIFTS}}', shifts_html)
            
            # Add correlation analysis
            correlation_html = self._format_correlation_analysis(analysis_results.get('correlations', {}))
            html_content = html_content.replace('{{CORRELATIONS}}', correlation_html)
            
            # Add trending topics
            trending_html = self._format_trending_topics(analysis_results.get('trending_topics', []))
            html_content = html_content.replace('{{TRENDING_TOPICS}}', trending_html)
            
            # Generate and embed charts
            charts_html = self._generate_charts(analysis_results)
            html_content = html_content.replace('{{CHARTS}}', charts_html)
            
            logger.info("Daily report generated successfully")
            return html_content
            
        except Exception as e:
            logger.error(f"Error generating daily report: {e}")
            return self._create_error_report(str(e))
    
    def send_report(self, recipient: str, subject: str, html_content: str) -> bool:
        """Send email report."""
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.username
            msg['To'] = recipient
            
            # Create HTML part
            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.send_message(msg)
            
            logger.info(f"Report sent successfully to {recipient}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending report: {e}")
            return False
    
    def _get_top_accounts(self, account_analyses: List[Dict]) -> tuple:
        """Get top 5 positive and negative sentiment accounts."""
        if not account_analyses:
            return [], []
        
        # Sort by average sentiment
        sorted_accounts = sorted(account_analyses, key=lambda x: x.get('average_sentiment', 0))
        
        # Get top 5 negative and positive
        top_negative = sorted_accounts[:5]
        top_positive = sorted_accounts[-5:][::-1]  # Reverse to get highest first
        
        return top_positive, top_negative
    
    def _format_account_list(self, accounts: List[Dict]) -> str:
        """Format account list for HTML display."""
        if not accounts:
            return "<li>No data available</li>"
        
        html_items = []
        for account in accounts:
            username = account.get('username', 'Unknown')
            sentiment = account.get('average_sentiment', 0)
            tweet_count = account.get('total_tweets', 0)
            sentiment_label = account.get('sentiment_label', 'neutral')
            
            color = {'positive': '#28a745', 'negative': '#dc3545', 'neutral': '#6c757d'}[sentiment_label]
            
            html_items.append(f"""
                <li style="margin-bottom: 10px;">
                    <strong>@{username}</strong> 
                    <span style="color: {color};">({sentiment:.3f})</span>
                    <br><small>{tweet_count} tweets analyzed</small>
                </li>
            """)
        
        return ''.join(html_items)
    
    def _format_sentiment_shifts(self, shifts_data: Dict) -> str:
        """Format sentiment shifts for HTML display."""
        shifts = shifts_data.get('shifts', [])
        
        if not shifts:
            return "<p>No significant sentiment shifts detected.</p>"
        
        html_items = []
        for shift in shifts:
            direction_color = '#28a745' if shift['direction'] == 'positive' else '#dc3545'
            html_items.append(f"""
                <div style="margin-bottom: 15px; padding: 10px; border-left: 4px solid {direction_color};">
                    <strong>{shift['type'].replace('_', ' ').title()}</strong><br>
                    Direction: <span style="color: {direction_color};">{shift['direction'].title()}</span><br>
                    Magnitude: {shift['magnitude']:.3f}<br>
                    Significance: {shift['significance'].title()}
                </div>
            """)
        
        return ''.join(html_items)
    
    def _format_correlation_analysis(self, correlations: Dict) -> str:
        """Format correlation analysis for HTML display."""
        if not correlations:
            return "<p>No correlation data available.</p>"
        
        html_content = []
        
        # Oil correlations
        oil_corr = correlations.get('oil_correlation', {})
        if oil_corr.get('correlations'):
            html_content.append("<h4>Oil Price Correlations</h4>")
            for price_type, corr_data in oil_corr['correlations'].items():
                pearson = corr_data.get('pearson_correlation', 0)
                significance = "Significant" if corr_data.get('pearson_p_value', 1) < 0.05 else "Not significant"
                html_content.append(f"""
                    <p><strong>{price_type.replace('_', ' ').title()}:</strong> 
                    {pearson:.3f} ({significance})</p>
                """)
        
        # Electricity correlations
        elec_corr = correlations.get('electricity_correlation', {})
        if elec_corr.get('correlations'):
            html_content.append("<h4>Electricity Price Correlations</h4>")
            for price_type, corr_data in elec_corr['correlations'].items():
                pearson = corr_data.get('pearson_correlation', 0)
                significance = "Significant" if corr_data.get('pearson_p_value', 1) < 0.05 else "Not significant"
                html_content.append(f"""
                    <p><strong>{price_type.replace('_', ' ').title()}:</strong> 
                    {pearson:.3f} ({significance})</p>
                """)
        
        return ''.join(html_content) if html_content else "<p>No significant correlations found.</p>"
    
    def _format_trending_topics(self, trending_topics: List[str]) -> str:
        """Format trending topics for HTML display."""
        if not trending_topics:
            return "<p>No trending topics identified.</p>"
        
        topics_html = []
        for topic in trending_topics[:10]:  # Show top 10
            topics_html.append(f"<span class='topic-tag'>#{topic}</span>")
        
        return ' '.join(topics_html)
    
    def _generate_charts(self, analysis_results: Dict) -> str:
        """Generate charts and return as base64 encoded images."""
        try:
            charts_html = []
            
            # Sentiment distribution chart
            sentiment_chart = self._create_sentiment_distribution_chart(analysis_results.get('account_analyses', []))
            if sentiment_chart:
                charts_html.append(f'<img src="data:image/png;base64,{sentiment_chart}" style="max-width: 100%; margin: 20px 0;">')
            
            return ''.join(charts_html)
            
        except Exception as e:
            logger.error(f"Error generating charts: {e}")
            return "<p>Charts could not be generated.</p>"
    
    def _create_sentiment_distribution_chart(self, account_analyses: List[Dict]) -> str:
        """Create sentiment distribution chart."""
        try:
            if not account_analyses:
                return ""
            
            # Prepare data
            sentiments = [acc.get('average_sentiment', 0) for acc in account_analyses]
            usernames = [acc.get('username', 'Unknown') for acc in account_analyses]
            
            # Create plot
            plt.figure(figsize=(12, 6))
            colors = ['red' if s < -0.1 else 'green' if s > 0.1 else 'gray' for s in sentiments]
            
            plt.bar(range(len(sentiments)), sentiments, color=colors, alpha=0.7)
            plt.axhline(y=0, color='black', linestyle='-', alpha=0.3)
            plt.xlabel('Accounts')
            plt.ylabel('Average Sentiment Score')
            plt.title('Daily Sentiment Analysis by Account')
            plt.xticks(range(len(usernames)), [f'@{u}' for u in usernames], rotation=45, ha='right')
            plt.tight_layout()
            
            # Convert to base64
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
            buffer.seek(0)
            chart_base64 = base64.b64encode(buffer.getvalue()).decode()
            plt.close()
            
            return chart_base64
            
        except Exception as e:
            logger.error(f"Error creating sentiment distribution chart: {e}")
            return ""
    
    def _create_html_template(self) -> str:
        """Create HTML email template."""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Daily Sentiment Analysis Report</title>
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 800px; margin: 0 auto; padding: 20px; }
                .header { background: #f8f9fa; padding: 20px; border-radius: 5px; margin-bottom: 20px; }
                .section { margin-bottom: 30px; }
                .positive { color: #28a745; }
                .negative { color: #dc3545; }
                .neutral { color: #6c757d; }
                .topic-tag { background: #e9ecef; padding: 3px 8px; border-radius: 3px; margin: 2px; display: inline-block; font-size: 0.9em; }
                table { width: 100%; border-collapse: collapse; margin: 10px 0; }
                th, td { padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }
                th { background-color: #f8f9fa; }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Daily Sentiment Analysis Report</h1>
                <p><strong>Date:</strong> {{DATE}}</p>
                <p><strong>Accounts Analyzed:</strong> {{TOTAL_ACCOUNTS}} | <strong>Total Tweets:</strong> {{TOTAL_TWEETS}}</p>
            </div>
            
            <div class="section">
                <h2>Top Positive Sentiment Accounts</h2>
                <ul>{{TOP_POSITIVE}}</ul>
            </div>
            
            <div class="section">
                <h2>Top Negative Sentiment Accounts</h2>
                <ul>{{TOP_NEGATIVE}}</ul>
            </div>
            
            <div class="section">
                <h2>Notable Sentiment Shifts</h2>
                {{SENTIMENT_SHIFTS}}
            </div>
            
            <div class="section">
                <h2>Price Correlation Analysis</h2>
                {{CORRELATIONS}}
            </div>
            
            <div class="section">
                <h2>Trending Topics</h2>
                {{TRENDING_TOPICS}}
            </div>
            
            <div class="section">
                <h2>Data Visualizations</h2>
                {{CHARTS}}
            </div>
            
            <div style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; font-size: 0.9em; color: #666;">
                <p>This report was generated automatically by the Twitter Sentiment Analysis System.</p>
                <p>For questions or issues, please check the system logs.</p>
            </div>
        </body>
        </html>
        """
    
    def _create_error_report(self, error_message: str) -> str:
        """Create error report HTML."""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Sentiment Analysis Report - Error</title>
        </head>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <h1 style="color: #dc3545;">Sentiment Analysis Report - Error</h1>
            <p><strong>Date:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p><strong>Error:</strong> {error_message}</p>
            <p>Please check the system logs for more details.</p>
        </body>
        </html>
        """