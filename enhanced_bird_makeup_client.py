"""
Enhanced Bird.makeup client with Selenium fallback
Combines ActivityPub scraping with Selenium-based Twitter scraping
"""

import requests
import json
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import time
import re
from urllib.parse import urljoin, quote

from logger import setup_logger
from twitter_scraper import TwitterScraper

logger = setup_logger(__name__)

class EnhancedBirdMakeupClient:
    """Enhanced client with Bird.makeup primary and Selenium fallback."""
    
    def __init__(self, base_url: str, username: Optional[str] = None, password: Optional[str] = None, 
                 twitter_username: Optional[str] = None, twitter_password: Optional[str] = None):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'SentimentAnalyzer/1.0 (ActivityPub Client)',
            'Accept': 'application/activity+json, application/ld+json; profile="https://www.w3.org/ns/activitystreams"',
            'Content-Type': 'application/activity+json'
        })
        
        # Bird.makeup credentials
        self.username = username
        self.password = password
        
        # Twitter credentials for Selenium fallback
        self.twitter_username = twitter_username
        self.twitter_password = twitter_password
        self.selenium_scraper = None
        
        if username and password:
            self._authenticate(username, password)
        
        logger.info(f"Enhanced Bird.makeup client initialized for {self.base_url}")
    
    def _authenticate(self, username: str, password: str) -> bool:
        """Authenticate with Bird.makeup instance if required."""
        try:
            logger.info("Authentication configured (Bird.makeup typically doesn't require auth for public data)")
            return True
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            return False
    
    def get_user_tweets(self, username: str, days_back: int = 1) -> List[Dict]:
        """Fetch tweets using Bird.makeup first, fallback to Selenium if needed."""
        username = username.lstrip('@')
        
        # Try Bird.makeup first
        tweets = self._get_tweets_bird_makeup(username, days_back)
        
        # If Bird.makeup fails or returns insufficient data, try Selenium
        if len(tweets) < 5 and self.twitter_username and self.twitter_password:
            logger.info(f"Bird.makeup returned {len(tweets)} tweets, trying Selenium fallback")
            selenium_tweets = self._get_tweets_selenium(username, days_back)
            if selenium_tweets:
                tweets.extend(selenium_tweets)
                logger.info(f"Selenium fallback added {len(selenium_tweets)} tweets")
        
        return tweets
    
    def _get_tweets_bird_makeup(self, username: str, days_back: int) -> List[Dict]:
        """Get tweets using Bird.makeup ActivityPub."""
        tweets = []
        
        try:
            user_url = f"{self.base_url}/@{username}"
            outbox_url = f"{user_url}/outbox"
            
            logger.info(f"Fetching ActivityPub data for @{username} from {outbox_url}")
            
            response = self.session.get(outbox_url, timeout=30)
            
            if response.status_code == 404:
                logger.warning(f"User @{username} not found on Bird.makeup")
                return tweets
            elif response.status_code != 200:
                logger.error(f"Failed to fetch data for @{username}: HTTP {response.status_code}")
                return tweets
            
            try:
                data = response.json()
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON response for @{username}: {e}")
                return tweets
            
            tweets = self._parse_activitypub_collection(data, username, days_back)
            logger.info(f"Bird.makeup fetched {len(tweets)} tweets for @{username}")
            time.sleep(2)
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error fetching tweets for @{username}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error fetching tweets for @{username}: {e}")
        
        return tweets
    
    def _get_tweets_selenium(self, username: str, days_back: int) -> List[Dict]:
        """Get tweets using Selenium scraper."""
        try:
            if not self.selenium_scraper:
                self.selenium_scraper = TwitterScraper(
                    username=self.twitter_username,
                    password=self.twitter_password,
                    headless=True
                )
                
                if not self.selenium_scraper.login():
                    logger.error("Failed to login with Selenium scraper")
                    return []
            
            tweets = self.selenium_scraper.scrape_user_tweets(
                username=username,
                max_tweets=50,
                days_back=days_back
            )
            
            return tweets
            
        except Exception as e:
            logger.error(f"Error with Selenium scraper for @{username}: {e}")
            return []
    
    def _parse_activitypub_collection(self, data: Dict, username: str, days_back: int) -> List[Dict]:
        """Parse ActivityPub collection to extract tweets."""
        tweets = []
        cutoff_date = datetime.now() - timedelta(days=days_back)
        
        try:
            items = []
            
            if 'orderedItems' in data:
                items = data['orderedItems']
            elif 'items' in data:
                items = data['items']
            elif 'first' in data:
                first_page_url = data['first']
                if isinstance(first_page_url, str):
                    first_page = self._fetch_collection_page(first_page_url)
                    if first_page:
                        items = first_page.get('orderedItems', first_page.get('items', []))
                elif isinstance(first_page_url, dict):
                    items = first_page_url.get('orderedItems', first_page_url.get('items', []))
            
            for item in items:
                try:
                    tweet_data = self._parse_activitypub_note(item, username)
                    if tweet_data and tweet_data['timestamp'] >= cutoff_date:
                        tweets.append(tweet_data)
                except Exception as e:
                    logger.warning(f"Error parsing ActivityPub item: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"Error parsing ActivityPub collection: {e}")
        
        return tweets
    
    def _fetch_collection_page(self, page_url: str) -> Optional[Dict]:
        """Fetch a paginated collection page."""
        try:
            response = self.session.get(page_url, timeout=30)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.warning(f"Error fetching collection page {page_url}: {e}")
        return None
    
    def _parse_activitypub_note(self, item: Dict, username: str) -> Optional[Dict]:
        """Parse individual ActivityPub Note (tweet) object."""
        try:
            note = item
            if item.get('type') == 'Create' and 'object' in item:
                note = item['object']
            
            if note.get('type') != 'Note':
                return None
            
            content = note.get('content', '')
            if not content:
                return None
            
            text = self._clean_html_content(content)
            published = note.get('published')
            timestamp = self._parse_activitypub_timestamp(published) if published else datetime.now()
            
            replies_count = 0
            reblogs_count = 0
            favourites_count = 0
            
            if 'replies' in note:
                replies_count = self._get_collection_count(note['replies'])
            if 'shares' in note:
                reblogs_count = self._get_collection_count(note['shares'])
            if 'likes' in note:
                favourites_count = self._get_collection_count(note['likes'])
            
            note_url = note.get('url', note.get('id', f"{self.base_url}/@{username}/status/{int(timestamp.timestamp())}"))
            
            return {
                'username': username,
                'text': text,
                'timestamp': timestamp,
                'retweets': reblogs_count,
                'likes': favourites_count,
                'replies': replies_count,
                'url': note_url
            }
            
        except Exception as e:
            logger.warning(f"Error parsing ActivityPub note: {e}")
            return None
    
    def _clean_html_content(self, html_content: str) -> str:
        """Clean HTML content to extract plain text."""
        try:
            import re
            text = re.sub(r'<[^>]+>', '', html_content)
            import html
            text = html.unescape(text)
            text = ' '.join(text.split())
            return text.strip()
        except Exception as e:
            logger.warning(f"Error cleaning HTML content: {e}")
            return html_content
    
    def _parse_activitypub_timestamp(self, timestamp_str: str) -> datetime:
        """Parse ActivityPub timestamp string."""
        try:
            formats = [
                '%Y-%m-%dT%H:%M:%SZ',
                '%Y-%m-%dT%H:%M:%S.%fZ',
                '%Y-%m-%dT%H:%M:%S%z',
                '%Y-%m-%dT%H:%M:%S.%f%z'
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(timestamp_str, fmt)
                except ValueError:
                    continue
            
            try:
                from dateutil import parser
                return parser.parse(timestamp_str)
            except ImportError:
                logger.warning("dateutil not available for timestamp parsing")
            
            logger.warning(f"Could not parse timestamp: {timestamp_str}")
            return datetime.now()
            
        except Exception as e:
            logger.warning(f"Error parsing timestamp {timestamp_str}: {e}")
            return datetime.now()
    
    def _get_collection_count(self, collection) -> int:
        """Get count from ActivityPub collection."""
        try:
            if isinstance(collection, dict):
                return collection.get('totalItems', 0)
            elif isinstance(collection, str):
                return 0
            return 0
        except Exception:
            return 0
    
    def test_connection(self) -> bool:
        """Test connection to Bird.makeup instance."""
        try:
            response = self.session.get(f"{self.base_url}/.well-known/nodeinfo", timeout=10)
            if response.status_code == 200:
                logger.info("Successfully connected to Bird.makeup instance")
                return True
            else:
                logger.warning(f"Bird.makeup instance responded with status {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Failed to connect to Bird.makeup instance: {e}")
            return False
    
    def close(self):
        """Close connections and cleanup."""
        if self.selenium_scraper:
            self.selenium_scraper.close()
            self.selenium_scraper = None
        logger.info("Enhanced Bird.makeup client closed")

# Backward compatibility
BirdMakeupClient = EnhancedBirdMakeupClient