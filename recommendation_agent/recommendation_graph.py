# recommendation_graph.py
from langgraph.graph import StateGraph, END
from typing import Dict, Any
from recommendation_agent import RecommendationAgent

class RecommendationGraph:
    def __init__(self):
        self.recommendation_agent = RecommendationAgent()
        self.sql_node_handler = self._sql_node  # Default dummy logic
        self.graph = self._build_graph()

    def _build_graph(self):
        workflow = StateGraph(Dict[str, Any])

        workflow.add_node("recommendation_agent", self._recommendation_node)
        workflow.add_node("sql_agent", lambda state: self.sql_node_handler(state))  # Dynamic SQL node

        workflow.add_edge("recommendation_agent", "sql_agent")
        workflow.add_conditional_edges(
            "sql_agent",
            self._should_continue,
            {
                "continue": "recommendation_agent",
                "end": END
            }
        )

        workflow.set_entry_point("recommendation_agent")
        return workflow.compile()

    def _recommendation_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        return self.recommendation_agent.process_request(state)

    def _sql_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Default SQL handler: stub. Will be overridden in integration."""
        return {
            **state,
            "sql_data_collected": True,
            "data_complete": True
        }

    def override_sql_node(self, func):
        """Allows injection of real SQL logic."""
        self.sql_node_handler = func

    def _should_continue(self, state: Dict[str, Any]) -> str:
        return "end" if state.get("data_complete", False) else "continue"

    def run_analysis(self, initial_request: str) -> Dict[str, Any]:
        initial_state = {
            "messages": [{"role": "user", "content": initial_request}],
            "data_complete": False
        }
        return self.graph.invoke(initial_state)
