# graph.py
from typing import List, TypedDict, Annotated
from langgraph.graph import StateGraph, END
from recommendation_agent.recommendation_agent import RecommendationAgent
from sql_agent.agent import SQLAgent

# Define the state for our graph
class AgentState(TypedDict):
    messages: List[dict]
    report_path: Annotated[str, None]

# Instantiate agents
# The SQL Agent is now the primary data gatherer
sql_agent = SQLAgent()
# The Recommendation Agent is now a dedicated report generator
recommendation_agent = RecommendationAgent()

# Define node for the initial request to the SQL agent
def data_request_node(state: AgentState):
    """This node crafts the initial request for the SQL Agent."""
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
        }]
    }

# Define node for the SQL agent to process the request
def sql_node(state: AgentState):
    """This node invokes the SQL agent to fetch data."""
    # The SQL agent's process_request is already designed to handle this
    result = sql_agent.process_request(state)
    return {"messages": result["messages"]}

# Define node for the Recommendation agent to generate the report
def report_generation_node(state: AgentState):
    """This node takes the final SQL results and generates a PDF report."""
    sql_results_string = state['messages'][-1]['content']
    
    # Call the new, dedicated report generation method
    pdf_path = recommendation_agent.generate_report(sql_results_string)
    
    return {
        "messages": state['messages'] + [{
            "role": "assistant", 
            "content": f"Strategic analysis complete. Report generated at: {pdf_path}",
        }],
        "report_path": pdf_path
    }

# Build the simplified, linear graph
workflow = StateGraph(AgentState)

workflow.add_node("data_requester", data_request_node)
workflow.add_node("sql_agent", sql_node)
workflow.add_node("report_generator", report_generation_node)

# Define the linear flow
workflow.set_entry_point("data_requester")
workflow.add_edge("data_requester", "sql_agent")
workflow.add_edge("sql_agent", "report_generator")
workflow.add_edge("report_generator", END)

# Compile the graph
app = workflow.compile()
print("✅ Simplified LangGraph workflow compiled successfully.")