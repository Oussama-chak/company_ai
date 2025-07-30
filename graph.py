# graph.py
from typing import List, TypedDict, Annotated, Optional
from langgraph.graph import StateGraph, END
import os

# Import agent classes from their respective modules
from recommendation_agent.recommendation_agent import RecommendationAgent
from sql_agent.agent import SQLAgent

# Define the state for our graph
class AgentState(TypedDict):
    messages: List[dict]
    next: str
    report_path: Optional[str]
    user_query: Optional[str]

def create_workflow():
    """Create and return the compiled workflow."""
    
    # Instantiate agents with error handling
    try:
        recommendation_agent = RecommendationAgent()
        print("✅ Recommendation Agent initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize Recommendation Agent: {e}")
        raise
    
    try:
        sql_agent = SQLAgent()
        print("✅ SQL Agent initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize SQL Agent: {e}")
        raise

    # Define node functions that call the agent methods
    def recommendation_node(state: AgentState):
        """Process requests through the recommendation agent."""
        try:
            result = recommendation_agent.process_request(state)
            return {
                "messages": result.get("messages", state['messages']), 
                "next": result.get("next", END), 
                "report_path": result.get("report_path", state.get("report_path")),
                "user_query": state.get("user_query")
            }
        except Exception as e:
            error_msg = f"Recommendation agent error: {str(e)}"
            print(f"❌ {error_msg}")
            messages = state.get('messages', [])
            messages.append({
                'role': 'assistant',
                'content': error_msg
            })
            return {
                "messages": messages,
                "next": END,
                "report_path": state.get("report_path"),
                "user_query": state.get("user_query")
            }

    def sql_node(state: AgentState):
        """Process requests through the SQL agent."""
        try:
            result = sql_agent.process_request(state)
            return {
                "messages": result.get("messages", state['messages']), 
                "next": result.get("next", "recommendation_agent"),
                "report_path": state.get("report_path"),
                "user_query": state.get("user_query")
            }
        except Exception as e:
            error_msg = f"SQL agent error: {str(e)}"
            print(f"❌ {error_msg}")
            messages = state.get('messages', [])
            messages.append({
                'role': 'assistant',
                'content': error_msg
            })
            return {
                "messages": messages,
                "next": END,
                "report_path": state.get("report_path"),
                "user_query": state.get("user_query")
            }

    # Define the conditional edge to control the flow
    def router(state: AgentState):
        """Route the workflow based on the next field."""
        next_step = state.get("next", END)
        print(f"🔀 Router: Next step is '{next_step}'")
        return next_step

    # Build the graph
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("recommendation_agent", recommendation_node)
    workflow.add_node("sql_agent", sql_node)

    # Set entry point
    workflow.set_entry_point("recommendation_agent")

    # Add conditional edges
    workflow.add_conditional_edges(
        "recommendation_agent",
        router,
        {
            "sql_agent": "sql_agent",
            "END": END
        }
    )

    # After the SQL agent, it always goes back to the recommendation agent
    workflow.add_edge("sql_agent", "recommendation_agent")

    # Compile the graph into a runnable app
    app = workflow.compile()
    print("✅ LangGraph workflow compiled successfully.")
    
    return app

# Create the workflow
try:
    app = create_workflow()
except Exception as e:
    print(f"❌ Failed to create workflow: {e}")
    raise

def run_business_analysis(user_query: str = "Generate a comprehensive business analysis report"):
    """
    Main function to run the business analysis workflow.
    
    Args:
        user_query: The user's request for analysis
        
    Returns:
        dict: The final state with report path and messages
    """
    print(f"🚀 Starting business analysis workflow...")
    print(f"📝 User Query: {user_query}")
    
    # Initialize the state
    initial_state = {
        "messages": [
            {
                "role": "user", 
                "content": user_query
            }
        ],
        "next": "recommendation_agent",
        "report_path": None,
        "user_query": user_query
    }
    
    try:
        # Run the workflow
        final_state = app.invoke(initial_state)
        
        print("\n" + "="*60)
        print("📊 BUSINESS ANALYSIS COMPLETED")
        print("="*60)
        
        if final_state.get("report_path"):
            print(f"✅ Report Generated: {final_state['report_path']}")
            print(f"📍 Report Location: {os.path.abspath(final_state['report_path'])}")
        else:
            print("⚠️ No report was generated")
            
        # Print final messages
        messages = final_state.get("messages", [])
        if messages:
            last_message = messages[-1]
            print(f"💬 Final Status: {last_message.get('content', 'No status message')}")
        
        return final_state
        
    except Exception as e:
        error_msg = f"Workflow execution failed: {str(e)}"
        print(f"❌ {error_msg}")
        return {
            "messages": [{"role": "assistant", "content": error_msg}],
            "next": END,
            "report_path": None,
            "user_query": user_query
        }

if __name__ == "__main__":
    # Example usage
    print("🔧 Testing Business Analysis Workflow")
    print("-" * 50)
    
    # Check if GEMINI_API_KEY is set
    if not os.getenv("GEMINI_API_KEY"):
        print("❌ GEMINI_API_KEY environment variable is not set!")
        print("Please set your Gemini API key:")
        print("export GEMINI_API_KEY='your_api_key_here'")
        exit(1)
    
    # Run the analysis
    result = run_business_analysis(
        "Generate a comprehensive strategic business analysis report with actionable recommendations"
    )
    
    print("\n🎯 Analysis Complete!")
    if result.get("report_path"):
        print(f"📄 Your report is ready: {result['report_path']}")
    else:
        print("⚠️ Report generation failed. Check the logs above for details.")