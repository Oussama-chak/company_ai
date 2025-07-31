# sql_agent/agent.py
import os
import sys
import json
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

from typing import Dict, Any, List
import re
from mistral_wrapper import run_mistral
from db_connector import execute_sql, get_db_schema

class SQLAgent:
    def __init__(self):
        self.db_schema = get_db_schema()
        if not self.db_schema:
            print("⚠️ SQL Agent Warning: Database schema is empty. Make sure data has been ingested.")
        
        # Define query templates based on actual CSV structure
        self.query_templates = {
            "sales_performance": """
            SELECT 
                SUM(revenue_current_quarter) as total_sales,
                ROUND(AVG((revenue_current_quarter - revenue_previous_quarter) / revenue_previous_quarter * 100), 2) as avg_growth_rate,
                (SELECT product_category FROM commercial_performance ORDER BY revenue_current_quarter DESC LIMIT 1) as top_category
            FROM commercial_performance;
            """,
            
            "marketing_efficiency": """
            SELECT 
                AVG(return_on_ad_spend) as avg_roi,
                SUM(monthly_budget) as total_spend,
                AVG(conversion_to_customer_percent) as avg_conversion,
                SUM(leads_generated) as total_leads,
                (SELECT channel FROM marketing_spend_performance ORDER BY return_on_ad_spend DESC LIMIT 1) as best_channel
            FROM marketing_spend_performance;
            """,
            
            "customer_insights": """
            SELECT 
                AVG(satisfaction_score) as avg_satisfaction,
                AVG(churn_rate_percent) as avg_churn,
                AVG(lifetime_value) as avg_ltv,
                (SELECT segment FROM customer_segments ORDER BY revenue_contribution_percent DESC LIMIT 1) as top_segment
            FROM customer_segments;
            """,
            
            "product_performance": """
            SELECT 
                (SELECT product_line FROM product_performance ORDER BY revenue DESC LIMIT 1) as top_product,
                SUM(revenue) as total_revenue,
                AVG(customer_rating) as avg_rating,
                AVG(profit_margin_percent) as avg_margin
            FROM product_performance;
            """,
            
            "financial_overview": """
            SELECT 
                current_value as total_revenue,
                variance_percent as growth_rate,
                performance_rating as rating
            FROM financial_kpis 
            WHERE metric = 'Total Revenue';
            """
        }

    def _clean_sql(self, sql_string: str) -> str:
        """Cleans a single SQL query."""
        sql_string = re.sub(r"```sql\n?", "", sql_string)
        sql_string = re.sub(r"```", "", sql_string)
        return sql_string.strip().rstrip(';')

    def _identify_query_type(self, request: str) -> str:
        """Identify which template to use based on the request"""
        request_lower = request.lower()
        
        if any(word in request_lower for word in ['sales', 'revenue', 'growth', 'commercial']):
            return "sales_performance"
        elif any(word in request_lower for word in ['marketing', 'roi', 'spend', 'conversion', 'leads']):
            return "marketing_efficiency"
        elif any(word in request_lower for word in ['customer', 'satisfaction', 'churn', 'retention', 'segment']):
            return "customer_insights"
        elif any(word in request_lower for word in ['product', 'rating', 'margin', 'performance']):
            return "product_performance"
        elif any(word in request_lower for word in ['financial', 'kpi', 'overview', 'total']):
            return "financial_overview"
        else:
            return "sales_performance"  # default

    def process_request(self, state: Dict[str, Any]) -> Dict[str, Any]:
        print("🤖 SQL Agent: Processing data requests...")
        requests_content = state["messages"][-1]["content"]
        nl_queries = [q.strip() for q in requests_content.split("|||") if q.strip()]

        results = []
        
        for i, request in enumerate(nl_queries):
            print(f"  - Processing request {i+1}: {request[:50]}...")
            
            # Identify query type and use appropriate template
            query_type = self._identify_query_type(request)
            sql_query = self.query_templates.get(query_type, self.query_templates["sales_performance"])
            
            print(f"    - Using template: {query_type}")
            print(f"    - Executing: {sql_query[:100]}...")
            
            try:
                query_result = execute_sql(sql_query)
                
                if isinstance(query_result, dict) and "error" in query_result:
                    result_entry = {
                        "request": request,
                        "template": query_type,
                        "status": "error",
                        "error": query_result["error"],
                        "sql": sql_query
                    }
                elif not query_result:
                    result_entry = {
                        "request": request,
                        "template": query_type,
                        "status": "no_data",
                        "data": {}
                    }
                else:
                    # Process successful result
                    if isinstance(query_result, list) and len(query_result) > 0:
                        data = query_result[0] if isinstance(query_result[0], dict) else {}
                    else:
                        data = query_result if isinstance(query_result, dict) else {}
                    
                    result_entry = {
                        "request": request,
                        "template": query_type,
                        "status": "success",
                        "data": data
                    }
                
                results.append(result_entry)
                print(f"    - ✅ Success: {len(str(result_entry.get('data', {})))} chars")
                
            except Exception as e:
                result_entry = {
                    "request": request,
                    "template": query_type,
                    "status": "error",
                    "error": str(e),
                    "sql": sql_query
                }
                results.append(result_entry)
                print(f"    - ❌ Error: {e}")

        # Format response for recommendation agent - ensure it's JSON serializable
        structured_response = {
            "type": "structured_data",
            "results": results,
            "summary": f"Processed {len(results)} requests, {sum(1 for r in results if r['status'] == 'success')} successful"
        }

        # Convert to string to avoid serialization issues
        response_content = json.dumps(structured_response, default=str, indent=2)

        return {
            "messages": state["messages"] + [{
                "role": "sql_agent_response",
                "content": response_content
            }]
        }

    def get_available_metrics(self) -> Dict[str, List[str]]:
        """Return available metrics from each table for debugging"""
        return {
            "sales_metrics": ["total_sales", "growth_rate", "top_category", "market_share", "customer_acquisition_cost"],
            "marketing_metrics": ["marketing_roi", "total_spend", "conversion_rate", "total_leads", "best_channel"],
            "customer_metrics": ["satisfaction_score", "churn_rate", "lifetime_value", "top_segment"],
            "product_metrics": ["top_product", "total_revenue", "avg_rating", "profit_margin"],
            "financial_metrics": ["revenue", "growth", "performance_rating"]
        }