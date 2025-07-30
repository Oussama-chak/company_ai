# shared/db_connector.py
from sqlalchemy import create_engine, text, inspect
from dotenv import load_dotenv
import os

load_dotenv()
DB_URI = os.getenv("DB_URI")
if not DB_URI:
    raise ValueError("DB_URI not found in environment variables. Please check your .env file.")
    
engine = create_engine(DB_URI)

def get_engine():
    """Returns the SQLAlchemy engine instance."""
    return engine

def execute_sql(query: str):
    """Executes a SQL query and returns the result as a list of dictionaries."""
    try:
        with engine.connect() as conn:
            result = conn.execute(text(query))
            if result.returns_rows:
                return [dict(row._mapping) for row in result]
            else:
                return {"status": "success", "rows_affected": result.rowcount}
    except Exception as e:
        print(f"SQL Execution Error: {e}")
        return {"error": str(e), "query": query}

def get_db_schema():
    """Inspects the database and returns a string representation of the schema."""
    inspector = inspect(engine)
    schema_info = ""
    for table_name in inspector.get_table_names():
        schema_info += f"Table '{table_name}':\n"
        columns = inspector.get_columns(table_name)
        for column in columns:
            schema_info += f"  - {column['name']} ({column['type']})\n"
        schema_info += "\n"
    return schema_info