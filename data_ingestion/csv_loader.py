import pandas as pd
import os
from sqlalchemy import inspect
from db_connector import get_engine

def load_csv_to_sql(csv_path: str, table_name: str):
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"❌ File '{csv_path}' not found.")

    # Read and clean CSV
    df = pd.read_csv(csv_path)
    df.columns = [col.strip().lower().replace(" ", "_") for col in df.columns]

    engine = get_engine()
    inspector = inspect(engine)

    # Optional: check if table exists
    if table_name in inspector.get_table_names():
        print(f"⚠️ Table '{table_name}' exists — it will be replaced.")

    # Load to SQL
    df.to_sql(table_name, con=engine, if_exists="replace", index=False)
    print(f"✅ Table '{table_name}' created with {len(df)} rows from '{csv_path}'.")
