# data_ingestion/loader_main.py
import os
from data_ingestion.csv_loader import load_csv_to_sql

def ingest_all_csvs(folder_path="data"):
    if not os.path.exists(folder_path):
        print(f"⚠️ Data folder '{folder_path}' not found. Skipping ingestion.")
        return

    for file in os.listdir(folder_path):
        if file.endswith(".csv"):
            table_name = os.path.splitext(file)[0].lower()
            csv_path = os.path.join(folder_path, file)
            try:
                load_csv_to_sql(csv_path, table_name)
            except Exception as e:
                print(f"❌ Failed to load {csv_path}: {e}")