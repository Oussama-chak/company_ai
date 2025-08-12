import os
from typing import List, TypedDict, Annotated
from langgraph.graph import StateGraph, END
from recommendation_agent.recommendation_agent import RecommendationAgent
from sql_agent.agent import SQLAgent
from judge_agent.judge_agent import LLMJudge, ComparisonResult

class AgentState(TypedDict):
    messages: List[dict]
    report_path: Annotated[str, None]
    report_text_content: Annotated[str, None]
    judge_analysis: Annotated[dict, None]
    iteration_count: Annotated[int, 0]  # Track feedback iterations
    judge_feedback: Annotated[str, None]  # Store judge's improvement suggestions
    improvement_history: Annotated[List[dict], []]  # Track all iterations
    final_quality_score: Annotated[float, 0.0]  # Final quality assessment

# Instantiate agents
sql_agent = SQLAgent()
recommendation_agent = RecommendationAgent()

judge_llm = LLMJudge(
    mistral_key=os.getenv("MISTRAL_API_KEY")
)

# Configuration for iterative improvement
MAX_ITERATIONS = 3  # Maximum feedback loops
QUALITY_THRESHOLD = 0.8  # Stop if quality score reaches this level

def data_request_node(state: AgentState):
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

def sql_node(state: AgentState):
    result = sql_agent.process_request(state)
    return {"messages": result["messages"]}

def report_generation_node(state: AgentState):
    sql_results_string = state['messages'][-1]['content']
    iteration_count = state.get('iteration_count', 0)
    judge_feedback = state.get('judge_feedback', None)
    
    print(f"📝 Report Generator: Starting iteration {iteration_count + 1}")
    
    # Generate or improve report based on feedback
    if iteration_count == 0:
        # First iteration - generate initial report
        pdf_path, report_text_content = recommendation_agent.generate_report(sql_results_string)
    else:
        # Subsequent iterations - improve based on judge feedback
        pdf_path, report_text_content = recommendation_agent.improve_report_with_feedback(
            sql_results_string, judge_feedback, iteration_count
        )
    
    return {
        "messages": state['messages'] + [{
            "role": "assistant", 
            "content": f"Strategic analysis iteration {iteration_count + 1} complete. Report generated at: {pdf_path}",
        }],
        "report_path": pdf_path,
        "report_text_content": report_text_content,
        "iteration_count": iteration_count + 1
    }

def judge_node(state: AgentState):
    iteration_count = state.get('iteration_count', 1)
    print(f"⚖️ Judge Agent: Analyzing report iteration {iteration_count}...")
    
    report_text = state.get("report_text_content")
    improvement_history = state.get('improvement_history', [])
    
    # Get comparison data from SQL results
    comparison_data = ""
    for msg in state['messages']:
        if msg.get("role") == "sql_agent_response":
            comparison_data = msg.get("content", "")
            break

    if not report_text or not comparison_data:
        return {"judge_analysis": {"error": "Missing data for analysis."}}

    try:
        judge_result: ComparisonResult = judge_llm.analyze_report_with_feedback(
            report_text, comparison_data, iteration_count, improvement_history
        )
        
        # Convert to dictionary
        judge_result_dict = {
            "anomalies": judge_result.anomalies,
            "similarities": judge_result.similarities,
            "confidence_score": judge_result.confidence_score,
            "detailed_analysis": judge_result.detailed_analysis,
            "authenticity_score": judge_result.authenticity_score,
            "data_integration_score": judge_result.data_integration_score,
            "personalization_evidence": judge_result.personalization_evidence,
            "generic_indicators": judge_result.generic_indicators,
            "key_inconsistencies": judge_result.key_inconsistencies,
            "overall_assessment": judge_result.overall_assessment,
            "improvement_suggestions": getattr(judge_result, 'improvement_suggestions', []),
            "quality_score": getattr(judge_result, 'quality_score', 0.0),
            "iteration": iteration_count
        }
        
        # Store this iteration's results
        current_iteration = {
            "iteration": iteration_count,
            "quality_score": judge_result_dict.get('quality_score', 0.0),
            "main_issues": judge_result.anomalies[:3],  # Top 3 issues
            "improvements_made": judge_result.similarities[:3] if iteration_count > 1 else []
        }
        
        updated_history = improvement_history + [current_iteration]
        
        print(f"✅ Judge Agent: Analysis complete. Quality score: {judge_result_dict.get('quality_score', 0.0):.2f}")
        
        return {
            "judge_analysis": judge_result_dict,
            "judge_feedback": judge_result.detailed_analysis,  # Feedback for next iteration
            "improvement_history": updated_history,
            "final_quality_score": judge_result_dict.get('quality_score', 0.0)
        }
        
    except Exception as e:
        print(f"❌ Judge Agent: Analysis failed: {e}")
        return {"judge_analysis": {"error": f"Judge analysis failed: {str(e)}"}}

def should_continue_iteration(state: AgentState) -> str:
    iteration_count = state.get('iteration_count', 0)
    final_quality_score = state.get('final_quality_score', 0.0)
    
    # Stop conditions
    if iteration_count >= MAX_ITERATIONS:
        print(f"🔄 Iteration Controller: Maximum iterations ({MAX_ITERATIONS}) reached. Finalizing.")
        return "finalize"
    
    if final_quality_score >= QUALITY_THRESHOLD:
        print(f"🎯 Iteration Controller: Quality threshold ({QUALITY_THRESHOLD}) achieved. Score: {final_quality_score:.2f}")
        return "finalize"
    
    if iteration_count == 0:
        print(f"🔄 Iteration Controller: Starting feedback loop. Current score: {final_quality_score:.2f}")
        return "continue"
    
    # Check if we're making progress
    improvement_history = state.get('improvement_history', [])
    if len(improvement_history) >= 2:
        current_score = improvement_history[-1]['quality_score']
        previous_score = improvement_history[-2]['quality_score']
        if current_score <= previous_score + 0.05:  # Minimal improvement
            print(f"📊 Iteration Controller: Minimal improvement detected. Finalizing.")
            return "finalize"
    
    print(f"🔄 Iteration Controller: Continuing iteration. Score: {final_quality_score:.2f}")
    return "continue"

def finalize_results_node(state: AgentState):
    iteration_count = state.get('iteration_count', 0)
    final_quality_score = state.get('final_quality_score', 0.0)
    improvement_history = state.get('improvement_history', [])
    
    print(f"🏁 Finalizing results after {iteration_count} iterations. Final quality score: {final_quality_score:.2f}")
    
    # Add summary to judge analysis
    judge_analysis = state.get('judge_analysis', {})
    judge_analysis['iteration_summary'] = {
        "total_iterations": iteration_count,
        "final_quality_score": final_quality_score,
        "improvement_trajectory": [h['quality_score'] for h in improvement_history],
        "key_improvements_made": [h.get('improvements_made', []) for h in improvement_history if h.get('improvements_made')]
    }
    
    return {
        "judge_analysis": judge_analysis,
        "messages": state['messages'] + [{
            "role": "system",
            "content": f"Iterative improvement process completed. {iteration_count} iterations performed with final quality score of {final_quality_score:.2f}"
        }]
    }

# Build the iterative feedback graph
workflow = StateGraph(AgentState)

workflow.add_node("data_requester", data_request_node)
workflow.add_node("sql_agent", sql_node)
workflow.add_node("report_generator", report_generation_node)
workflow.add_node("judge_node", judge_node)
workflow.add_node("finalize_results", finalize_results_node)

# Define the iterative flow
workflow.set_entry_point("data_requester")
workflow.add_edge("data_requester", "sql_agent")
workflow.add_edge("sql_agent", "report_generator")
workflow.add_edge("report_generator", "judge_node")

workflow.add_conditional_edges(
    "judge_node",
    should_continue_iteration,
    {
        "continue": "report_generator",  # Loop back for improvement
        "finalize": "finalize_results"   # End the process
    }
)

workflow.add_edge("finalize_results", END)

# Compile the graph
app = workflow.compile()
print("✅ LangGraph iterative feedback workflow compiled successfully.")
