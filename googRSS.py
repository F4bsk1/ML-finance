import feedparser
import pandas as pd
from google.cloud import bigquery
from urllib.parse import quote
from datetime import datetime, timezone
import os

# === Configuration ===
COMPANIES = ["Apple", "Google", "Amazon", "Tesla", "Microsoft"]
TICKERS = ["AAPL", "GOOGL", "AMZN", "TSLA", "MSFT"]
TABLE_ID = "ml-finance-454213.news_analysis.news"  # Replace with your table name
JSON_KEY_PATH = "ml-finance-454213-70b2a4ca823a.json"   # Path to your service account JSON key

def fetch_news():
    news_data = []
    now = datetime.now(timezone.utc)  # Get current UTC time
    for company, ticker in zip(COMPANIES, TICKERS):
        query = quote(f"{company} stock OR {company} financial news")
        url = f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"
        
        feed = feedparser.parse(url)
        
        for entry in feed.entries:
            title = entry.title
            published_at = entry.published_parsed
            if published_at is not None:
                published_at = datetime(*published_at[:6]).replace(tzinfo=timezone.utc)
            
            news_data.append({
                "ticker": ticker,
                "title": title,
                "published_at": published_at,
                "source": entry.source['title'] if 'source' in entry else 'Unknown'
            })
    
    return news_data

def upload_to_bigquery(news_data, table_id):
    if os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        client = bigquery.Client()  # Automatically uses the key file specified by GOOGLE_APPLICATION_CREDENTIALS
    else:
        client = bigquery.Client.from_service_account_json("ml-finance-454213-70b2a4ca823a.json")
    df = pd.DataFrame(news_data)
    
    if df.empty:
        print("⚠️ No new data to upload.")
        return

    # Fetch existing titles in the table to avoid duplicates
    query = f"SELECT title FROM `{table_id}`"
    existing_titles = {row['title'] for row in client.query(query).result()}

    # Filter out duplicates
    df = df[~df['title'].isin(existing_titles)]
    
    if df.empty:
        print("✅ No new articles to upload after filtering duplicates.")
        return

    job_config = bigquery.LoadJobConfig(
        schema=[
            bigquery.SchemaField("ticker", "STRING"),
            bigquery.SchemaField("title", "STRING"),
            bigquery.SchemaField("published_at", "TIMESTAMP"),
            bigquery.SchemaField("source", "STRING")
        ],
        write_disposition="WRITE_APPEND"
    )
    
    try:
        job = client.load_table_from_dataframe(df, table_id, job_config=job_config)
        job.result()  # Wait for the upload to complete
        print(f"✅ Successfully uploaded {len(df)} new articles to BigQuery!")
    except Exception as e:
        print(f"❌ Error uploading data to BigQuery: {e}")

if __name__ == "__main__":
    news_data = fetch_news()
    upload_to_bigquery(news_data, TABLE_ID)
