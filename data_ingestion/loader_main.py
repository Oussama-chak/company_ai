import os
from csv_loader import load_csv_to_sql

def ingest_all_csvs(folder_path="../data"):
    for file in os.listdir(folder_path):
        if file.endswith(".csv"):
            table_name = file.replace(".csv", "").lower()
            csv_path = os.path.join(folder_path, file)
            load_csv_to_sql(csv_path, table_name)

if __name__ == "__main__":
    ingest_all_csvs()
