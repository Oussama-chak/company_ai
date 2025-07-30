# sql_agent/agent.py
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))
# sql_agent/agent.py
from typing import Dict, Any
import re
from mistral_wrapper import run_mistral
from db_connector import execute_sql, get_db_schema

class SQLAgent:
    def __init__(self):
        self.db_schema = get_db_schema()
        if not self.db_schema:
            print("⚠️ SQL Agent Warning: Database schema is empty. Make sure data has been ingested.")

    def _clean_sql(self, sql_string: str) -> str:
        """Cleans a single SQL query."""
        sql_string = re.sub(r"```sql\n?", "", sql_string)
        sql_string = re.sub(r"```", "", sql_string)
        return sql_string.strip().rstrip(';')

    def process_request(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processes multiple natural language queries by generating all SQL in a
        single LLM call, then executing them sequentially.
        """
        print("🤖 SQL Agent: Received data requests. Optimizing for a single API call...")
        requests_content = state["messages"][-1]["content"]
        nl_queries = [q.strip() for q in requests_content.split("|||") if q.strip()]

        # ---- NEW EFFICIENT PROMPT ----
        # Combine all requests into a single prompt for the LLM
        formatted_requests = "\n".join([f"{i+1}. {query}" for i, query in enumerate(nl_queries)])

        prompt = f"""
        Given the following database schema:
        {self.db_schema}

        You must generate one valid SQLite query for each of the following requests.
        Requests:
        {formatted_requests}

        RULES:
        - You MUST provide a query for EACH request.
        - Separate each individual SQL query with the special delimiter '--;;--'.
        - ONLY return the SQL queries and the delimiter.
        - Do not include any other text, explanations, or markdown formatting.
        - Ensure queries are compatible with SQLite.

        Example format:
        SELECT ... FROM ... WHERE ...;
        --;;--
        SELECT ... FROM ...;
        --;;--
        SELECT ... FROM ...;
        """

        aggregated_results = []
        try:
            # --- SINGLE API CALL ---
            print("  - Generating all SQL queries in one go...")
            llm_response = run_mistral(prompt)
            
            # Split the response into individual SQL queries
            generated_sql_queries = llm_response.split('--;;--')

            if len(generated_sql_queries) != len(nl_queries):
                raise ValueError(f"LLM did not return the expected number of queries. Expected {len(nl_queries)}, got {len(generated_sql_queries)}")

            # --- LOCAL EXECUTION LOOP (NO MORE API CALLS) ---
            print("  - Executing generated queries...")
            for i, sql_query in enumerate(generated_sql_queries):
                cleaned_sql = self._clean_sql(sql_query)
                if not cleaned_sql:
                    continue
                
                nl_request = nl_queries[i]
                print(f"    - Executing for '{nl_request[:50]}...': {cleaned_sql}")
                query_result = execute_sql(cleaned_sql)
                
                result_str = f"--- Result for '{nl_request}' ---\n"
                if isinstance(query_result, dict) and "error" in query_result:
                    result_str += f"Error: {query_result['error']}"
                elif not query_result:
                    result_str += "No data returned."
                else:
                    for row in query_result:
                        result_str += ", ".join([f"{k}: {v}" for k, v in row.items()]) + "\n"
                aggregated_results.append(result_str)

        except Exception as e:
            error_message = f"--- An error occurred in the SQL Agent ---\n{str(e)}"
            aggregated_results.append(error_message)
            print(f"  - ❌ Error in SQL Agent: {e}")

        final_response_content = "\n\n".join(aggregated_results)

        return {
            "messages": state["messages"] + [{
                "role": "sql_agent_response",
                "content": final_response_content
            }],
            "next": "recommendation_agent"
        }