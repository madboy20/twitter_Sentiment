import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import time
import re
from logger import setup_logger

logger = setup_logger(__name__)

class NitterClient:
    """Client for scraping tweets from Nitter instance."""
    
    def __init__(self, base_url: str, username: Optional[str] = None, password: Optional[str] = None):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        if username and password:
            self._authenticate(username, password)
    
    def _authenticate(self, username: str, password: str) -> bool:
        """Authenticate with Nitter instance if required."""
        try:
            # This is a placeholder - actual authentication depends on your Nitter setup
            login_url = f"{self.base_url}/login"
            response = self.session.get(login_url)
            
            if response.status_code == 200:
                logger.info("Successfully connected to Nitter instance")
                return True
            else:
                logger.warning("Authentication may be required but endpoint not available")
                return False
                
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            return False
    
    def get_user_tweets(self, username: str, days_back: int = 1) -> List[Dict]:
        """Fetch tweets from a specific user for the last N days."""
        tweets = []
        username = username.lstrip('@')
        
        try:
            url = f"{self.base_url}/{username}"
            response = self.session.get(url, timeout=30)
            
            if response.status_code != 200:
                logger.error(f"Failed to fetch tweets for @{username}: HTTP {response.status_code}")
                return tweets
            
            soup = BeautifulSoup(response.content, 'html.parser')
            tweet_containers = soup.find_all('div', class_='timeline-item')
            
            cutoff_date = datetime.now() - timedelta(days=days_back)
            
            for container in tweet_containers:
                try:
                    tweet_data = self._parse_tweet(container, username)
                    if tweet_data and tweet_data['timestamp'] >= cutoff_date:
                        tweets.append(tweet_data)
                except Exception as e:
                    logger.warning(f"Error parsing tweet: {e}")
                    continue
            
            logger.info(f"Fetched {len(tweets)} tweets for @{username}")
            time.sleep(1)  # Rate limiting
            
        except Exception as e:
            logger.error(f"Error fetching tweets for @{username}: {e}")
        
        return tweets
    
    def _parse_tweet(self, container, username: str) -> Optional[Dict]:
        """Parse individual tweet from HTML container."""
        try:
            # Extract tweet text
            tweet_content = container.find('div', class_='tweet-content')
            if not tweet_content:
                return None
            
            text = tweet_content.get_text(strip=True)
            
            # Extract timestamp
            time_element = container.find('span', class_='tweet-date')
            if time_element:
                time_str = time_element.get('title', '')
                timestamp = self._parse_timestamp(time_str)
            else:
                timestamp = datetime.now()
            
            # Extract engagement metrics
            stats = container.find('div', class_='tweet-stats')
            retweets = self._extract_stat(stats, 'retweet') if stats else 0
            likes = self._extract_stat(stats, 'like') if stats else 0
            replies = self._extract_stat(stats, 'reply') if stats else 0
            
            return {
                'username': username,
                'text': text,
                'timestamp': timestamp,
                'retweets': retweets,
                'likes': likes,
                'replies': replies,
                'url': f"https://twitter.com/{username}/status/{int(timestamp.timestamp())}"
            }
            
        except Exception as e:
            logger.warning(f"Error parsing tweet: {e}")
            return None
    
    def _parse_timestamp(self, time_str: str) -> datetime:
        """Parse timestamp from various formats."""
        try:
            # Try different timestamp formats
            formats = [
                '%b %d, %Y · %I:%M %p',
                '%Y-%m-%d %H:%M:%S',
                '%m/%d/%Y %H:%M:%S'
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(time_str, fmt)
                except ValueError:
                    continue
            
            # If all formats fail, return current time
            return datetime.now()
            
        except Exception:
            return datetime.now()
    
    def _extract_stat(self, stats_container, stat_type: str) -> int:
        """Extract engagement statistics from tweet."""
        try:
            stat_element = stats_container.find('span', class_=f'tweet-stat-{stat_type}')
            if stat_element:
                stat_text = stat_element.get_text(strip=True)
                # Extract number from text like "1.2K" or "500"
                number_match = re.search(r'([\d.]+)([KMB]?)', stat_text)
                if number_match:
                    number, suffix = number_match.groups()
                    multiplier = {'K': 1000, 'M': 1000000, 'B': 1000000000}.get(suffix, 1)
                    return int(float(number) * multiplier)
            return 0
        except Exception:
            return 0