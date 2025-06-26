from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from textblob import TextBlob
from typing import Dict, List, Tuple
import re
from logger import setup_logger

logger = setup_logger(__name__)

class SentimentAnalyzer:
    """Sentiment analysis using VADER and TextBlob."""
    
    def __init__(self):
        self.vader_analyzer = SentimentIntensityAnalyzer()
        logger.info("Sentiment analyzer initialized")
    
    def analyze_tweet(self, text: str) -> Dict[str, float]:
        """Analyze sentiment of a single tweet."""
        # Clean the text
        cleaned_text = self._clean_text(text)
        
        # VADER analysis
        vader_scores = self.vader_analyzer.polarity_scores(cleaned_text)
        
        # TextBlob analysis
        blob = TextBlob(cleaned_text)
        textblob_polarity = blob.sentiment.polarity
        textblob_subjectivity = blob.sentiment.subjectivity
        
        # Combined score (weighted average)
        combined_score = (vader_scores['compound'] + textblob_polarity) / 2
        
        return {
            'vader_compound': vader_scores['compound'],
            'vader_positive': vader_scores['pos'],
            'vader_negative': vader_scores['neg'],
            'vader_neutral': vader_scores['neu'],
            'textblob_polarity': textblob_polarity,
            'textblob_subjectivity': textblob_subjectivity,
            'combined_score': combined_score,
            'sentiment_label': self._get_sentiment_label(combined_score)
        }
    
    def analyze_tweets_batch(self, tweets: List[Dict]) -> Dict[str, any]:
        """Analyze sentiment for a batch of tweets."""
        if not tweets:
            return self._empty_analysis()
        
        sentiments = []
        oil_related_tweets = []
        electricity_related_tweets = []
        
        for tweet in tweets:
            sentiment = self.analyze_tweet(tweet['text'])
            sentiment['tweet_data'] = tweet
            sentiments.append(sentiment)
            
            # Check for oil-related content
            if self._contains_keywords(tweet['text'], ['WTI', 'Brent', 'crude oil', 'OPEC']):
                oil_related_tweets.append({**sentiment, 'tweet': tweet})
            
            # Check for electricity-related content
            if self._contains_keywords(tweet['text'], ['Strompreis', 'Energiekosten', 'kWh']):
                electricity_related_tweets.append({**sentiment, 'tweet': tweet})
        
        # Calculate aggregate metrics
        avg_sentiment = sum(s['combined_score'] for s in sentiments) / len(sentiments)
        positive_count = sum(1 for s in sentiments if s['sentiment_label'] == 'positive')
        negative_count = sum(1 for s in sentiments if s['sentiment_label'] == 'negative')
        neutral_count = len(sentiments) - positive_count - negative_count
        
        return {
            'total_tweets': len(tweets),
            'average_sentiment': avg_sentiment,
            'sentiment_distribution': {
                'positive': positive_count,
                'negative': negative_count,
                'neutral': neutral_count
            },
            'individual_sentiments': sentiments,
            'oil_related_tweets': oil_related_tweets,
            'electricity_related_tweets': electricity_related_tweets,
            'sentiment_label': self._get_sentiment_label(avg_sentiment)
        }
    
    def _clean_text(self, text: str) -> str:
        """Clean tweet text for better sentiment analysis."""
        # Remove URLs
        text = re.sub(r'http\S+|www\S+|https\S+', '', text, flags=re.MULTILINE)
        
        # Remove user mentions and hashtags for cleaner analysis
        text = re.sub(r'@\w+|#\w+', '', text)
        
        # Remove extra whitespace
        text = ' '.join(text.split())
        
        return text.strip()
    
    def _get_sentiment_label(self, score: float) -> str:
        """Convert numerical sentiment score to label."""
        if score >= 0.1:
            return 'positive'
        elif score <= -0.1:
            return 'negative'
        else:
            return 'neutral'
    
    def _contains_keywords(self, text: str, keywords: List[str]) -> bool:
        """Check if text contains any of the specified keywords."""
        text_lower = text.lower()
        return any(keyword.lower() in text_lower for keyword in keywords)
    
    def _empty_analysis(self) -> Dict[str, any]:
        """Return empty analysis structure."""
        return {
            'total_tweets': 0,
            'average_sentiment': 0.0,
            'sentiment_distribution': {'positive': 0, 'negative': 0, 'neutral': 0},
            'individual_sentiments': [],
            'oil_related_tweets': [],
            'electricity_related_tweets': [],
            'sentiment_label': 'neutral'
        }