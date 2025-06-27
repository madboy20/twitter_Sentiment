"""
Enhanced Twitter Scraper using Selenium
Integrated with the existing sentiment analysis system
"""

import os
import sys
import pandas as pd
from datetime import datetime
from fake_headers import Headers
from time import sleep
import random

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
    WebDriverException,
)
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.firefox.service import Service as FirefoxService

from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager

from logger import setup_logger

logger = setup_logger(__name__)

TWITTER_LOGIN_URL = "https://twitter.com/i/flow/login"

class Progress:
    """Progress tracking for scraping operations."""
    
    def __init__(self, current, total) -> None:
        self.current = current
        self.total = total

    def print_progress(self, current, waiting=False, retry_cnt=0, no_tweets_limit=False) -> None:
        self.current = current
        if no_tweets_limit:
            if waiting:
                sys.stdout.write(
                    f"\rTweets scraped: {current} - waiting to access older tweets {retry_cnt} min on 15 min"
                )
            else:
                sys.stdout.write(f"\rTweets scraped: {current}                                                  ")
        else:
            progress = current / self.total
            bar_length = 40
            progress_bar = (
                "["
                + "=" * int(bar_length * progress)
                + "-" * (bar_length - int(bar_length * progress))
                + "]"
            )
            if waiting:
                sys.stdout.write(
                    f"\rProgress: [{progress_bar:<40}] {progress:.2%} {current} of {self.total} - waiting to access older tweets {retry_cnt} min on 15 min"
                )
            else:
                sys.stdout.write(
                    f"\rProgress: [{progress_bar:<40}] {progress:.2%} {current} of {self.total}                                                  "
                )
        sys.stdout.flush()

class Scroller:
    """Scroll management for infinite scroll pages."""
    
    def __init__(self, driver) -> None:
        self.driver = driver
        self.current_position = 0
        self.last_position = driver.execute_script("return window.pageYOffset;")
        self.scrolling = True
        self.scroll_count = 0

    def reset(self) -> None:
        self.current_position = 0
        self.last_position = self.driver.execute_script("return window.pageYOffset;")
        self.scroll_count = 0

    def scroll_to_top(self) -> None:
        self.driver.execute_script("window.scrollTo(0, 0);")

    def scroll_to_bottom(self) -> None:
        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

    def update_scroll_position(self) -> None:
        self.current_position = self.driver.execute_script("return window.pageYOffset;")

class Tweet:
    """Tweet data extraction and processing."""
    
    def __init__(self, card, driver, actions, scrape_poster_details=False) -> None:
        self.card = card
        self.error = False
        self.tweet = None
        self.is_ad = False

        try:
            self.user = card.find_element(
                "xpath", './/div[@data-testid="User-Name"]//span'
            ).text
        except NoSuchElementException:
            self.error = True
            self.user = "skip"

        try:
            self.handle = card.find_element(
                "xpath", './/span[contains(text(), "@")]'
            ).text
        except NoSuchElementException:
            self.error = True
            self.handle = "skip"

        try:
            self.date_time = card.find_element("xpath", ".//time").get_attribute("datetime")
            if self.date_time is not None:
                self.is_ad = False
        except NoSuchElementException:
            self.is_ad = True
            self.error = True
            self.date_time = "skip"

        if self.error:
            return

        try:
            card.find_element(
                "xpath", './/*[local-name()="svg" and @data-testid="icon-verified"]'
            )
            self.verified = True
        except NoSuchElementException:
            self.verified = False

        # Extract tweet content
        self.content = ""
        contents = card.find_elements(
            "xpath",
            '(.//div[@data-testid="tweetText"])[1]/span | (.//div[@data-testid="tweetText"])[1]/a',
        )

        for content in contents:
            self.content += content.text

        # Extract engagement metrics
        try:
            self.reply_cnt = card.find_element(
                "xpath", './/button[@data-testid="reply"]//span'
            ).text
            if self.reply_cnt == "":
                self.reply_cnt = "0"
        except NoSuchElementException:
            self.reply_cnt = "0"

        try:
            self.retweet_cnt = card.find_element(
                "xpath", './/button[@data-testid="retweet"]//span'
            ).text
            if self.retweet_cnt == "":
                self.retweet_cnt = "0"
        except NoSuchElementException:
            self.retweet_cnt = "0"

        try:
            self.like_cnt = card.find_element(
                "xpath", './/button[@data-testid="like"]//span'
            ).text
            if self.like_cnt == "":
                self.like_cnt = "0"
        except NoSuchElementException:
            self.like_cnt = "0"

        # Extract additional metadata
        try:
            self.tags = card.find_elements(
                "xpath", './/a[contains(@href, "src=hashtag_click")]'
            )
            self.tags = [tag.text for tag in self.tags]
        except NoSuchElementException:
            self.tags = []

        try:
            self.mentions = card.find_elements(
                "xpath", '(.//div[@data-testid="tweetText"])[1]//a[contains(text(), "@")]'
            )
            self.mentions = [mention.text for mention in self.mentions]
        except NoSuchElementException:
            self.mentions = []

        try:
            self.tweet_link = self.card.find_element(
                "xpath", ".//a[contains(@href, '/status/')]"
            ).get_attribute("href")
            self.tweet_id = str(self.tweet_link.split("/")[-1])
        except NoSuchElementException:
            self.tweet_link = ""
            self.tweet_id = ""

        # Convert to our expected format
        self.tweet = {
            'username': self.handle.lstrip('@') if self.handle != "skip" else "unknown",
            'text': self.content,
            'timestamp': self._parse_timestamp(self.date_time),
            'retweets': self._parse_count(self.retweet_cnt),
            'likes': self._parse_count(self.like_cnt),
            'replies': self._parse_count(self.reply_cnt),
            'url': self.tweet_link,
            'tweet_id': self.tweet_id,
            'verified': self.verified,
            'tags': self.tags,
            'mentions': self.mentions
        }

    def _parse_timestamp(self, timestamp_str):
        """Parse timestamp string to datetime object."""
        if timestamp_str == "skip":
            return datetime.now()
        try:
            return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        except:
            return datetime.now()

    def _parse_count(self, count_str):
        """Parse engagement count strings (handles K, M suffixes)."""
        if not count_str or count_str == "0":
            return 0
        try:
            if 'K' in count_str:
                return int(float(count_str.replace('K', '')) * 1000)
            elif 'M' in count_str:
                return int(float(count_str.replace('M', '')) * 1000000)
            else:
                return int(count_str.replace(',', ''))
        except:
            return 0

class TwitterScraper:
    """Enhanced Twitter scraper using Selenium."""
    
    def __init__(self, username=None, password=None, headless=True, browser='firefox'):
        self.username = username
        self.password = password
        self.headless = headless
        self.browser = browser
        self.interrupted = False
        self.tweet_ids = set()
        self.data = []
        self.tweet_cards = []
        self.driver = None
        self.actions = None
        self.scroller = None
        
        logger.info("Twitter scraper initialized")

    def _get_driver(self, proxy=None):
        """Initialize WebDriver with appropriate options."""
        logger.info("Setting up WebDriver...")
        
        # Use mobile user agent for better compatibility
        header = "Mozilla/5.0 (Linux; Android 11; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.5414.87 Mobile Safari/537.36"

        if self.browser.lower() == 'chrome':
            options = ChromeOptions()
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--ignore-certificate-errors")
            options.add_argument("--disable-gpu")
            options.add_argument("--log-level=3")
            options.add_argument("--disable-notifications")
            options.add_argument("--disable-popup-blocking")
            options.add_argument(f"--user-agent={header}")
            
            if proxy:
                options.add_argument(f"--proxy-server={proxy}")
            
            if self.headless:
                options.add_argument("--headless")

            try:
                driver = webdriver.Chrome(options=options)
            except WebDriverException:
                chromedriver_path = ChromeDriverManager().install()
                service = ChromeService(executable_path=chromedriver_path)
                driver = webdriver.Chrome(service=service, options=options)
        
        else:  # Firefox
            options = FirefoxOptions()
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--ignore-certificate-errors")
            options.add_argument("--disable-gpu")
            options.add_argument("--log-level=3")
            options.add_argument("--disable-notifications")
            options.add_argument("--disable-popup-blocking")
            options.add_argument(f"--user-agent={header}")
            
            if self.headless:
                options.add_argument("--headless")

            try:
                driver = webdriver.Firefox(options=options)
            except WebDriverException:
                firefoxdriver_path = GeckoDriverManager().install()
                service = FirefoxService(executable_path=firefoxdriver_path)
                driver = webdriver.Firefox(service=service, options=options)

        logger.info("WebDriver setup complete")
        return driver

    def login(self):
        """Login to Twitter."""
        if not self.username or not self.password:
            logger.error("Username and password required for login")
            return False

        logger.info("Logging in to Twitter...")
        
        try:
            self.driver = self._get_driver()
            self.actions = ActionChains(self.driver)
            self.scroller = Scroller(self.driver)
            
            self.driver.maximize_window()
            self.driver.execute_script("document.body.style.zoom='150%'")
            self.driver.get(TWITTER_LOGIN_URL)
            sleep(3)

            self._input_username()
            self._input_unusual_activity()
            self._input_password()

            # Verify login success
            cookies = self.driver.get_cookies()
            auth_token = None
            for cookie in cookies:
                if cookie["name"] == "auth_token":
                    auth_token = cookie["value"]
                    break

            if auth_token is None:
                raise ValueError("Login failed - no auth token found")

            logger.info("Login successful")
            return True

        except Exception as e:
            logger.error(f"Login failed: {e}")
            if self.driver:
                self.driver.quit()
            return False

    def _input_username(self):
        """Input username with retry logic."""
        input_attempt = 0
        while True:
            try:
                username_field = self.driver.find_element(
                    "xpath", "//input[@autocomplete='username']"
                )
                username_field.send_keys(self.username)
                username_field.send_keys(Keys.RETURN)
                sleep(3)
                break
            except NoSuchElementException:
                input_attempt += 1
                if input_attempt >= 3:
                    raise Exception("Could not find username input field")
                logger.warning("Retrying username input...")
                sleep(2)

    def _input_unusual_activity(self):
        """Handle unusual activity check if present."""
        try:
            unusual_activity = self.driver.find_element(
                "xpath", "//input[@data-testid='ocfEnterTextTextInput']"
            )
            unusual_activity.send_keys(self.username)
            unusual_activity.send_keys(Keys.RETURN)
            sleep(3)
        except NoSuchElementException:
            pass  # No unusual activity check

    def _input_password(self):
        """Input password with retry logic."""
        input_attempt = 0
        while True:
            try:
                password_field = self.driver.find_element(
                    "xpath", "//input[@autocomplete='current-password']"
                )
                password_field.send_keys(self.password)
                password_field.send_keys(Keys.RETURN)
                sleep(3)
                break
            except NoSuchElementException:
                input_attempt += 1
                if input_attempt >= 3:
                    raise Exception("Could not find password input field")
                logger.warning("Retrying password input...")
                sleep(2)

    def scrape_user_tweets(self, username, max_tweets=50, days_back=1):
        """Scrape tweets from a specific user."""
        if not self.driver:
            logger.error("Driver not initialized. Please login first.")
            return []

        username = username.lstrip('@')
        logger.info(f"Scraping tweets from @{username}")

        try:
            # Navigate to user profile
            self.driver.get(f"https://twitter.com/{username}")
            sleep(3)

            # Accept cookies if banner appears
            try:
                accept_cookies_btn = self.driver.find_element(
                    "xpath", "//span[text()='Refuse non-essential cookies']/../../.."
                )
                accept_cookies_btn.click()
                sleep(2)
            except NoSuchElementException:
                pass

            # Initialize scraping variables
            self.tweet_ids = set()
            self.data = []
            progress = Progress(0, max_tweets)
            progress.print_progress(0)

            refresh_count = 0
            added_tweets = 0
            empty_count = 0
            retry_cnt = 0

            while self.scroller.scrolling:
                try:
                    # Get tweet cards
                    tweet_cards = self.driver.find_elements(
                        "xpath", '//article[@data-testid="tweet" and not(@disabled)]'
                    )

                    added_tweets = 0

                    for card in tweet_cards[-15:]:
                        try:
                            tweet_id = str(card)

                            if tweet_id not in self.tweet_ids:
                                self.tweet_ids.add(tweet_id)

                                # Scroll card into view
                                self.driver.execute_script("arguments[0].scrollIntoView();", card)

                                tweet = Tweet(
                                    card=card,
                                    driver=self.driver,
                                    actions=self.actions,
                                    scrape_poster_details=False
                                )

                                if tweet and not tweet.error and tweet.tweet and not tweet.is_ad:
                                    # Check if tweet is within time range
                                    tweet_age = datetime.now() - tweet.tweet['timestamp']
                                    if tweet_age.days <= days_back:
                                        self.data.append(tweet.tweet)
                                        added_tweets += 1
                                        progress.print_progress(len(self.data))

                                        if len(self.data) >= max_tweets:
                                            self.scroller.scrolling = False
                                            break

                        except NoSuchElementException:
                            continue

                    if len(self.data) >= max_tweets:
                        break

                    if added_tweets == 0:
                        # Handle rate limiting
                        try:
                            while retry_cnt < 15:
                                retry_button = self.driver.find_element(
                                    "xpath", "//span[text()='Retry']/../../.."
                                )
                                progress.print_progress(len(self.data), True, retry_cnt)
                                sleep(60)  # Wait 1 minute instead of 10
                                retry_button.click()
                                retry_cnt += 1
                                sleep(2)
                        except NoSuchElementException:
                            retry_cnt = 0
                            progress.print_progress(len(self.data))

                        if empty_count >= 5:
                            if refresh_count >= 3:
                                logger.info("No more tweets to scrape")
                                break
                            refresh_count += 1
                        empty_count += 1
                        sleep(1)
                    else:
                        empty_count = 0
                        refresh_count = 0

                except StaleElementReferenceException:
                    sleep(2)
                    continue
                except KeyboardInterrupt:
                    logger.info("Scraping interrupted by user")
                    self.interrupted = True
                    break
                except Exception as e:
                    logger.error(f"Error during scraping: {e}")
                    break

            logger.info(f"Scraping completed. Collected {len(self.data)} tweets from @{username}")
            return self.data

        except Exception as e:
            logger.error(f"Error scraping user @{username}: {e}")
            return []

    def close(self):
        """Close the browser driver."""
        if self.driver:
            self.driver.quit()
            logger.info("Browser driver closed")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()