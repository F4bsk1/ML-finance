from newsapi import NewsApiClient
import pandas as pd
from google.cloud import bigquery
import time
from datetime import datetime, timedelta
from google.oauth2 import service_account


# Initialize NewsAPI client with your API key
newsapi = NewsApiClient(api_key="f77b5dc02b0a478494bcfefad14059ba")

# Define the companies and their tickers
Companies = [
    {"ticker": "AAPL", "name": "Apple"},
    {"ticker": "GOOGL", "name": "Google"},
    {"ticker": "AMZN", "name": "Amazon"},
    {"ticker": "TSLA", "name": "Tesla"},
    {"ticker": "MSFT", "name": "Microsoft"}
]

def fetch_news(ticker, company, requests=2):  # Increased to 2 requests per company
    articles = []
    for page in range(1, requests + 1):
        try:
            all_articles = newsapi.get_everything(
                q=f"{company} stock OR {company} financial news",  # Improved query
                language='en',
                sort_by='relevancy',
                page=page,
                page_size=20  # Increased to gather more articles at once
            )
            
            if 'articles' in all_articles and all_articles['articles']:
                for article in all_articles['articles']:
                    articles.append({
                        "ticker": ticker,
                        "title": article.get('title'),
                        "published_at": article.get("publishedAt"),
                        "source": article.get("source", {}).get("name", "Unknown")
                    })
            else:
                print(f"⚠️ No articles found for company {company} on page {page}")
        except Exception as e:
            print(f"❌ Error fetching articles for {company} on page {page}: {e}")
        
        time.sleep(1)  # Avoid hitting rate limits
    return articles

def upload_to_bigquery(news_data, table_id):
    if os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        client = bigquery.Client()  # Automatically uses the key file specified by GOOGLE_APPLICATION_CREDENTIALS
    else:
        client = bigquery.Client.from_service_account_json("ml-finance-454213-70b2a4ca823a.json")
    df = pd.DataFrame(news_data)

    if df.empty:
        print("⚠️ No data to upload.")
        return
    
    df['published_at'] = pd.to_datetime(df['published_at'], errors='coerce')

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
        print(f"✅ Data successfully uploaded to BigQuery table {table_id}!")
    except Exception as e:
        print(f"❌ Error uploading data to BigQuery: {e}")


def test_fetch_and_upload():
    news_data = []
    for company in Companies:
        company_data = fetch_news(company["ticker"], company["name"])
        news_data.extend(company_data)
    
    # Upload data to BigQuery
    upload_to_bigquery(news_data, "ml-finance-454213.news_analysis.newsAPI")

# Run the function
test_fetch_and_upload()
