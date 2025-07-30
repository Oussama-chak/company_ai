from mistral_wrapper import run_mistral
from db_connector import execute_sql

schema_hint = """
The database contains a table called 'sales_data' with the following columns:
- id (int)
- date (DATE)
- region (TEXT)
- product (TEXT)
- revenue (FLOAT)
"""

def handle_sql_request(request: str):
    prompt = f"""{schema_hint}

User request: {request}
Write the appropriate SQL query."""
    
    sql_query = run_mistral(prompt)

    print(f"\n🤖 Generated SQL:\n{sql_query}\n")

    result = execute_sql(sql_query)
    return {
        "sql_query": sql_query,
        "result": result
    }

if __name__ == "__main__":
    user_query = "Show me the total revenue per region for 2023."
    response = handle_sql_request(user_query)
    print("\n📊 SQL Agent Output:")
    print(response)
