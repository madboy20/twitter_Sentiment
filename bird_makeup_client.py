import requests
import json
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import time
import re
from urllib.parse import urljoin, quote
from logger import setup_logger

logger = setup_logger(__name__)

class BirdMakeupClient:
    """Client for fetching tweets from Bird.makeup using ActivityPub protocol."""
    
    def __init__(self, base_url: str, username: Optional[str] = None, password: Optional[str] = None):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'SentimentAnalyzer/1.0 (ActivityPub Client)',
            'Accept': 'application/activity+json, application/ld+json; profile="https://www.w3.org/ns/activitystreams"',
            'Content-Type': 'application/activity+json'
        })
        
        if username and password:
            self._authenticate(username, password)
        
        logger.info(f"Bird.makeup client initialized for {self.base_url}")
    
    def _authenticate(self, username: str, password: str) -> bool:
        """Authenticate with Bird.makeup instance if required."""
        try:
            # Bird.makeup typically doesn't require authentication for public data
            # This is a placeholder for potential future authentication needs
            logger.info("Authentication configured (Bird.makeup typically doesn't require auth for public data)")
            return True
                
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            return False
    
    def get_user_tweets(self, username: str, days_back: int = 1) -> List[Dict]:
        """Fetch tweets from a specific user for the last N days using ActivityPub."""
        tweets = []
        username = username.lstrip('@')
        
        try:
            # Try to get user's outbox (collection of posts)
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
            
            # Parse ActivityPub collection
            tweets = self._parse_activitypub_collection(data, username, days_back)
            
            logger.info(f"Fetched {len(tweets)} tweets for @{username}")
            time.sleep(2)  # Rate limiting - be respectful
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error fetching tweets for @{username}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error fetching tweets for @{username}: {e}")
        
        return tweets
    
    def _parse_activitypub_collection(self, data: Dict, username: str, days_back: int) -> List[Dict]:
        """Parse ActivityPub collection to extract tweets."""
        tweets = []
        cutoff_date = datetime.now() - timedelta(days=days_back)
        
        try:
            # Handle different ActivityPub collection formats
            items = []
            
            if 'orderedItems' in data:
                items = data['orderedItems']
            elif 'items' in data:
                items = data['items']
            elif 'first' in data:
                # Collection might be paginated, get first page
                first_page_url = data['first']
                if isinstance(first_page_url, str):
                    first_page = self._fetch_collection_page(first_page_url)
                    if first_page:
                        items = first_page.get('orderedItems', first_page.get('items', []))
                elif isinstance(first_page_url, dict):
                    items = first_page_url.get('orderedItems', first_page_url.get('items', []))
            
            # Process each item
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
            # Handle different ActivityPub object structures
            note = item
            if item.get('type') == 'Create' and 'object' in item:
                note = item['object']
            
            # Skip if not a Note type
            if note.get('type') != 'Note':
                return None
            
            # Extract content
            content = note.get('content', '')
            if not content:
                return None
            
            # Clean HTML content
            text = self._clean_html_content(content)
            
            # Extract timestamp
            published = note.get('published')
            timestamp = self._parse_activitypub_timestamp(published) if published else datetime.now()
            
            # Extract engagement metrics (if available)
            # ActivityPub doesn't always include these, so we default to 0
            replies_count = 0
            reblogs_count = 0
            favourites_count = 0
            
            # Some instances include these in replies/shares/likes collections
            if 'replies' in note:
                replies_count = self._get_collection_count(note['replies'])
            if 'shares' in note:
                reblogs_count = self._get_collection_count(note['shares'])
            if 'likes' in note:
                favourites_count = self._get_collection_count(note['likes'])
            
            # Generate URL
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
            # Remove HTML tags
            import re
            text = re.sub(r'<[^>]+>', '', html_content)
            
            # Decode HTML entities
            import html
            text = html.unescape(text)
            
            # Clean up whitespace
            text = ' '.join(text.split())
            
            return text.strip()
            
        except Exception as e:
            logger.warning(f"Error cleaning HTML content: {e}")
            return html_content
    
    def _parse_activitypub_timestamp(self, timestamp_str: str) -> datetime:
        """Parse ActivityPub timestamp string."""
        try:
            # ActivityPub uses ISO 8601 format
            # Handle different formats
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
            
            # If all formats fail, try parsing with dateutil if available
            try:
                from dateutil import parser
                return parser.parse(timestamp_str)
            except ImportError:
                logger.warning("dateutil not available for timestamp parsing")
            
            # Fallback to current time
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
                # Collection URL - we could fetch it, but for now return 0
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

# Backward compatibility alias
NitterClient = BirdMakeupClient