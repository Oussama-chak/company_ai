from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

load_dotenv()
DB_URI = os.getenv("DB_URI")
engine = create_engine(DB_URI)

def execute_sql(query: str):
    try:
        with engine.connect() as conn:
            result = conn.execute(text(query))
            return [dict(row._mapping) for row in result]
    except Exception as e:
        return {"error": str(e), "query": query}
