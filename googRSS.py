from google.oauth2 import service_account
from google.cloud import bigquery

def upload_to_bigquery(news_data, table_id):
    credentials = service_account.Credentials.from_service_account_file("gcp_key.json")
    client = bigquery.Client(credentials=credentials, project=credentials.project_id)
    
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
        job.result()
        print(f"✅ Successfully uploaded {len(df)} new articles to BigQuery!")
    except Exception as e:
        print(f"❌ Error uploading data to BigQuery: {e}")
