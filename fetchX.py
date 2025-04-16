import os
import requests
from dotenv import load_dotenv
from google.cloud import bigquery
from datetime import datetime, timedelta

load_dotenv()

# Load Google Cloud credentials
GOOGLE_CREDENTIALS_PATH = "credentials.json"
if os.path.exists(GOOGLE_CREDENTIALS_PATH):
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = GOOGLE_CREDENTIALS_PATH
else:
    raise ValueError("❌ Google Cloud credentials file not found!")

client = bigquery.Client()
dataset_id = "ml-finance-454213.x_analysis"
x_tweets = f"{dataset_id}.x_tweets"

# Set query date
QUERY_DATE = (datetime.utcnow() - timedelta(hours=12)).strftime("%Y-%m-%d_%H:%M:%S_UTC")
BASE_URL = "https://api.twitterapi.io/twitter/"
HEADERS = {
    "X-API-Key": os.getenv("NEW_TWITTER_API_KEY"),
}
COMPANIES = {
    "Apple": ["AAPL", "Apple", "Apple Inc"],
    "Tesla": ["TSLA", "Tesla", "Elon Musk"],
    "Google": ["GOOGL", "Google", "Alphabet"],
    "Amazon": ["AMZN", "Amazon"],
    "Microsoft": ["MSFT", "Microsoft"],
}

def fetchQueryTweets(query, queryType, cursor=""):
    url = f"{BASE_URL}tweet/advanced_search"
    params = {
        "query": query,
        "queryType": queryType,
        "cursor": cursor,
    }

    response = requests.get(url, headers=HEADERS, params=params)
    if response.status_code == 200:
        response = response.json()
        if response.get("has_next_page"):
            return {
                "tweets": response.get("tweets"),
                "next_cursor": response.get("next_cursor"),
            }
        else:
            return {
                "tweets": response.get("tweets"),
                "next_cursor": None,
            }
    else:
        raise Exception(f"Error fetching tweets: {response.status_code} - {response.text}")

def filterTweets(tweets, ticker):
    filtered_tweets = []
    for tweet in tweets:
        filtered_tweet = {
            "id": tweet.get("id"),
            "created_utc": datetime.strptime(tweet.get("createdAt"), "%a %b %d %H:%M:%S +0000 %Y").strftime("%Y-%m-%d %H:%M:%S UTC"),
            "text": tweet.get("text"),
            "likes": tweet.get("likeCount"),
            "retweets": tweet.get("retweetCount"),
            "replies": tweet.get("replyCount"),
            "views": tweet.get("viewCount"),
            "ticker": ticker
        }
        filtered_tweets.append(filtered_tweet)
    return filtered_tweets

def postToBigQuery(filtered_tweets):
    try:
        job = client.insert_rows_json(x_tweets, filtered_tweets)
        if job == []:
            print("✅ Tweets Saved to BigQuery!")
        else:
            print("❌ Error inserting tweets:", job)
    except Exception as e:
        print("❌ Error inserting tweets:", e)

# New Methods (company-specific)
def build_stock_queries(company_keywords):
    return " OR ".join([f'"{word}"' for word in company_keywords])

def automateCompanyTweets():
    for company_name, keywords in COMPANIES.items():
        query = f"since:{QUERY_DATE} {build_stock_queries(keywords)}"
        ticker_symbol = keywords[0]
        pages = 0
        cursor = ""
        while cursor is not None and pages < 15:
            response = fetchQueryTweets(query, "Top", cursor)
            tweets = response.get("tweets")
            cursor = response.get("next_cursor")

            if tweets:
                filtered_tweets = filterTweets(tweets, ticker_symbol)
                postToBigQuery(filtered_tweets)
            else:
                print(f"❌ No tweets found for {company_name} ({query})")
                break
            pages += 1

        print(f"✅ Completed fetching tweets for {company_name} ({ticker_symbol}), {pages} page(s) fetched.")

# MAIN
if __name__ == "__main__":
    automateCompanyTweets()
