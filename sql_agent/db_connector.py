# shared/db_connector.py
from sqlalchemy import create_engine, text, inspect
from dotenv import load_dotenv
import os

load_dotenv()
DB_URI = os.getenv("DB_URI")
if not DB_URI:
    raise ValueError("DB_URI not found in environment variables. Please check your .env file.")
    
# Add pool_recycle to prevent connections from timing out
engine = create_engine(DB_URI, pool_recycle=3600)

def get_engine():
    """Returns the SQLAlchemy engine instance."""
    return engine

def execute_sql(query: str):
    """
    Executes a SQL query and returns the result as a list of dictionaries.
    This version ensures all results are fetched to prevent 'Commands out of sync' errors.
    """
    try:
        with engine.connect() as conn:
            # Use a transaction block for safety
            with conn.begin():
                result_proxy = conn.execute(text(query))
                
                # Check if the query is expected to return rows
                if result_proxy.returns_rows:
                    # EAGERLY FETCH ALL RESULTS into a list of dictionaries.
                    # This is the key fix: it consumes the full result set.
                    results = [dict(row._mapping) for row in result_proxy.fetchall()]
                    return results
                else:
                    # For non-row-returning statements (INSERT, UPDATE)
                    return {"status": "success", "rows_affected": result_proxy.rowcount}

    except Exception as e:
        # The error message from the traceback indicates this happens during connection reset,
        # which means the primary operation might have appeared to succeed.
        # We log the specific error for debugging.
        print(f"--- SQL Execution or Connection Reset Error ---")
        print(f"Query: {query}")
        print(f"Error: {e}")
        print(f"-------------------------------------------------")
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