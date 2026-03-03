# Social media scraper
# saves raw collected data as json files to data/raw/crowdsourced

import tweepy
from typing import List, Dict, Optional
import praw
import json
import requests
import os
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta


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

    def collect_tweets(self, keywords: str, location_bbox: Optional[str], since_date: str, max_results: int, bearer_token: str) -> List[Dict]:
        """
        Collect recent tweets using Twitter API based on keywords, location and date

        Parameters:
        - keywords (str): Search keywords like flood or earthquake
        - location_bbox (str): Bounding box coordinates
        - since_date (str): Start date
        - max_results (int): Maximum number of tweets
        - bearer_token (str): X API bearer token

        Returns:
        - List[Dict]: List of tweets with metadata
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

    def collect_reddit_posts(self, subreddits, keywords, since_timestamp):
        """Collect posts from specified subreddits based on keywords and timestamp"""
        posts = []

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

    def collect_relief_alerts(self, since_date):
        """Collect alerts from ReliefWeb API based on date"""
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

    def collect_gdacs_alerts(self):
        """Collect alerts from GDACS (Global Disaster Alert and Coordination System) RSS feed"""
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

    def save_raw_data(self, data, source_name, event_name):
        """Save raw collected data as JSON files"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

        folder = f"data/raw/crowdsourced/{event_name}/{source_name}"
        os.makedirs(folder, exist_ok=True)

        file_path = f"{folder}/data_{timestamp}.json"

        with open(file_path, "w") as f:
            json.dump(data, f, default=str, indent=4)

        return file_path

    def run_collection(self, event_name, keywords, bbox, since_date, since_timestamp):
        """Orchestrate all collection methods"""
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