# Social media scraper
# saves raw collected data as json files to data/raw/crowdsourced

import tweepy
from typing import Any, List, Dict, Optional
import praw
import json
import requests
import os
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta


# Creating a class for collecting data from X, REDDIT, RELIEF WEB, GDACS
# Saves raw data and JSON timestamps


class SocialMediaScraper:
    """Helper that wraps several social media APIs and other open feeds.

    The class maintains authenticated clients for Twitter (X) and Reddit and
    provides methods to query each service as well as a few external alert
    providers.  The results are returned as plain Python structures and may be
    persisted with :meth:`save_raw_data`.
    """
    def __init__(self, twitter_token_reddit_config: Dict[str, str]) -> None:
        """Initialise API clients once.

        Parameters
        ----------
        twitter_token_reddit_config : Dict[str, str]
            Dictionary holding the necessary bearer/token strings for Twitter and
            Reddit authentication.
        """
        self.twitter_client = tweepy.Client(bearer_token=twitter_token_reddit_config['twitter_bearer_token'])

        self.reddit_client = praw.Reddit(
            client_id=twitter_token_reddit_config['reddit_client_id'],
            client_secret=twitter_token_reddit_config['reddit_client_secret'],
            user_agent=twitter_token_reddit_config['reddit_user_agent']
        )


# Creating a class for collecting data from X, REDDIT, RELIEF WEB, GDACS
# Saves raw data and JSON timestamps


class SocialMediaScraper:
    def __init__(self, twitter_token_reddit_config):
        """Initialise API clients once"""
        self.twitter_client = tweepy.Client(bearer_token=twitter_token_reddit_config['twitter_bearer_token'])

        self.reddit_client = praw.Reddit(
            client_id=twitter_token_reddit_config['reddit_client_id'],
            client_secret=twitter_token_reddit_config['reddit_client_secret'],
            user_agent=twitter_token_reddit_config['reddit_user_agent']
        )

    def collect_tweets(self, keywords: str, location_bbox: Optional[str], since_date: str, max_results: int, bearer_token: Optional[str]) -> List[Dict[str, Any]]:
        """Collect recent tweets using Twitter API based on keywords, location and date.

        Parameters
        ----------
        keywords : str
            Search keywords like "flood" or "earthquake".
        location_bbox : Optional[str]
            Bounding box coordinates in the form "lon,lat radius" for the
            point_radius search operator.
        since_date : str
            ISO formatted start date/time for the search.
        max_results : int
            Maximum number of tweets to return (API limit applies).
        bearer_token : Optional[str]
            (Currently unused; retained for backwards compatibility.)

        Returns
        -------
        List[Dict[str, Any]]
            List of tweets with relevant metadata fields extracted.
        """
        query = keywords
        if location_bbox:
            query += f" point_radius:[{location_bbox}]"
        response = self.twitter_client.search_recent_tweets(
            query=query,
            start_time=since_date,
            max_results=max_results,
            tweet_fields=['created_at', 'geo', 'author_id']
        )
        tweets_data = []

        if response.data:
            for tweet in response.data:
                tweets_data.append({
                    'id': tweet.id,
                    'text': tweet.text,
                    'created_at': tweet.created_at.isoformat(),
                    'author_id': tweet.author_id,
                    'geo': tweet.geo
                })
        return tweets_data

    def collect_reddit_posts(self, subreddits: List[str], keywords: str, since_timestamp: float) -> List[Dict[str, Any]]:
        """Collect posts from specified subreddits based on keywords and timestamp.

        Parameters
        ----------
        subreddits : List[str]
            Names of the subreddits to search (e.g. ['earthquake', 'news']).
        keywords : str
            Keyword string used for the subreddit search API.
        since_timestamp : float
            Unix timestamp; only posts created after this point are included.

        Returns
        -------
        List[Dict[str, Any]]
            A list of simplified post dictionaries.
        """
        posts: List[Dict[str, Any]] = []

        for sub_name in subreddits:
            subreddit = self.reddit_client.subreddit(sub_name)

            for submission in subreddit.search(keywords, sort="new"):
                if submission.created_utc >= since_timestamp:
                    posts.append({
                        'id': submission.id,
                        'title': submission.title,
                        'selftext': submission.selftext,
                        'created_utc': datetime.utcfromtimestamp(submission.created_utc).isoformat(),
                        'author': str(submission.author),
                        'subreddit': str(submission.subreddit)
                    })

        return posts

    def collect_relief_alerts(self, since_date: str) -> List[Dict[str, Any]]:
        """Collect alerts from ReliefWeb API based on date.

        Parameters
        ----------
        since_date : str
            ISO formatted date string; the API will return reports created on or
            after this date.

        Returns
        -------
        List[Dict[str, Any]]
            A list of alert dictionaries with details such as source, country,
            and disaster type.
        """
        url = f"https://api.reliefweb.int/v1/reports?filter[operator]=and&filter[field]=date.created&filter[value][operator]=gte&filter[value][value]={since_date}&limit=100"
        response = requests.get(url)
        alerts = []
        if response.status_code == 200:
            data = response.json()

            for item in data.get("data", []):
                fields = item.get("fields", {})
                alerts.append({
                    "source": fields.get("source", {}).get("name"),
                    "date": fields.get("date", {}).get("created"),
                    "country": fields.get("country", {}).get("name"),
                    "disaster_type": fields.get("disaster", {}).get("name"),
                    "title": fields.get("title")
                })

        return alerts

    def collect_gdacs_alerts(self) -> List[Dict[str, Any]]:
        """Collect alerts from GDACS (Global Disaster Alert and Coordination System) RSS feed.

        Returns
        -------
        List[Dict[str, Any]]
            Each alert contains keys such as ``source``, ``title``, ``link`` and
            ``pubDate``.
        """
        rss_url = "https://www.gdacs.org/xml/rss.xml"

        response = requests.get(rss_url)
        alerts = []

        if response.status_code == 200:
            root = ET.fromstring(response.content)

            for item in root.findall(".//item"):
                alerts.append({
                    "source": "gdacs",
                    "title": item.find("title").text,
                    "link": item.find("link").text,
                    "description": item.find("description").text,
                    "pubDate": item.find("pubDate").text
                })

        return alerts

    def save_raw_data(self, data: Any, source_name: str, event_name: str) -> str:
        """Save raw collected data as JSON files.

        Parameters
        ----------
        data : Any
            Arbitrary JSON-serializable object returned by one of the collector
            methods.
        source_name : str
            Short identifier for the data source (e.g. ``'twitter'``).
        event_name : str
            Name of the current event/folder under ``data/raw/crowdsourced``.

        Returns
        -------
        str
            Path to the file that was written.
        """
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

        folder = f"data/raw/crowdsourced/{event_name}/{source_name}"
        os.makedirs(folder, exist_ok=True)

        file_path = f"{folder}/data_{timestamp}.json"

        with open(file_path, "w") as f:
            json.dump(data, f, default=str, indent=4)

        return file_path

    def run_collection(self, event_name: str, keywords: str, bbox: Optional[str], since_date: str, since_timestamp: float) -> Dict[str, Any]:
        """Orchestrate all collection methods and persist results.

        The method runs each of the individual collectors and saves the raw JSON
        output to disk.  It returns a dictionary containing the in-memory data
        for further processing.
        """
        twitter_data = self.collect_tweets(keywords, bbox, since_date, max_results=100, bearer_token=None)
        reddit_data = self.collect_reddit_posts(
            ["earthquake", "flooding", "disastermanagement", "earthquakealerts", "weather", "news"],
            keywords,
            since_timestamp
        )

        relief_data = self.collect_relief_alerts(since_date)
        gdacs_data = self.collect_gdacs_alerts()

        self.save_raw_data(twitter_data, "twitter", event_name)
        self.save_raw_data(reddit_data, "reddit", event_name)
        self.save_raw_data(relief_data, "reliefweb", event_name)
        self.save_raw_data(gdacs_data, "gdacs", event_name)

        return {
            "twitter": twitter_data,
            "reddit": reddit_data,
            "reliefweb": relief_data,
            "gdacs": gdacs_data
        }