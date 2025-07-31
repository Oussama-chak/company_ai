# graph.py
from typing import List, TypedDict, Annotated
from langgraph.graph import StateGraph, END
from recommendation_agent.recommendation_agent import RecommendationAgent
from sql_agent.agent import SQLAgent

class AgentState(TypedDict):
    messages: List[dict]
    report_path: Annotated[str, None]

# Initialize agents
sql_agent = SQLAgent()
recommendation_agent = RecommendationAgent()

def data_request_node(state: AgentState):
    """Request data from SQL agent"""
    data_requests = [
        "Get total sales, quarterly growth rate, top-selling region, and best product category.",
        "Get total social media engagement, total followers, leads generated, and the best-performing platform.",
        "Get the average customer satisfaction score, total support tickets, and customer retention rate.",
        "Get total marketing spend, overall conversion rate, cost per lead, and marketing ROI."
    ]
    request_content = "|||".join(data_requests)
    
    return {
        "messages": state['messages'] + [{
            "role": "data_requester",
            "content": request_content
        }],
        "report_path": state.get("report_path")
    }

def sql_node(state: AgentState):
    """Execute SQL queries"""
    print("🔍 Executing SQL queries...")
    result = sql_agent.process_request(state)
    return {
        "messages": result["messages"],
        "report_path": state.get("report_path")
    }

def report_generation_node(state: AgentState):
    """Generate PDF report"""
    print("📊 Generating report...")
    sql_results = state['messages'][-1]['content']
    
    try:
        pdf_path = recommendation_agent.generate_report(sql_results)
        success_message = f"Report generated successfully: {pdf_path}"
        print(f"✅ {success_message}")
        
        return {
            "messages": state['messages'] + [{
                "role": "assistant", 
                "content": success_message,
            }],
            "report_path": pdf_path
        }
    except Exception as e:
        error_message = f"Report generation failed: {str(e)}"
        print(f"❌ {error_message}")
        return {
            "messages": state['messages'] + [{
                "role": "assistant", 
                "content": error_message,
            }],
            "report_path": None
        }

# Build the workflow
workflow = StateGraph(AgentState)

workflow.add_node("data_requester", data_request_node)
workflow.add_node("sql_agent", sql_node)
workflow.add_node("report_generator", report_generation_node)

workflow.set_entry_point("data_requester")
workflow.add_edge("data_requester", "sql_agent")
workflow.add_edge("sql_agent", "report_generator")
workflow.add_edge("report_generator", END)

app = workflow.compile()
print("✅ Workflow compiled successfully.")