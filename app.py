# app.py
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import os
import sys
from datetime import datetime
from recommendation_agent import RecommendationAgent
from sql_agent import SQLAgent

class EnhancedBusinessAnalyzer:
    """Main application for enhanced business analysis with PDF generation."""
    
    def __init__(self):
        self.recommendation_agent = RecommendationAgent()
        self.sql_agent = SQLAgent()
        
    def run_analysis(self, user_query: str = "Generate comprehensive strategic business analysis"):
        """Run the complete business analysis workflow."""
        print("🚀 Starting Enhanced Business Analysis")
        print("=" * 60)
        print(f"Query: {user_query}")
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        
        # Initialize state
        state = {
            "messages": [{"role": "user", "content": user_query}],
            "next": "recommendation_agent",
            "report_path": None
        }
        
        try:
            # Step 1: Recommendation agent requests data
            print("\n📊 Step 1: Analyzing requirements and requesting data...")
            state = self.recommendation_agent.process_request(state)
            
            if state.get("next") == "sql_agent":
                # Step 2: SQL agent processes data requests
                print("\n🔍 Step 2: Extracting data from database...")
                state = self.sql_agent.process_request(state)
                
                # Step 3: Generate final report
                print("\n📝 Step 3: Generating strategic analysis report...")
                state = self.recommendation_agent.process_request(state)
            
            # Results
            print("\n" + "=" * 60)
            print("✅ ANALYSIS COMPLETE")
            print("=" * 60)
            
            if state.get("report_path"):
                report_path = os.path.abspath(state["report_path"])
                print(f"📄 Report Generated: {report_path}")
                print(f"📁 File Size: {os.path.getsize(report_path) / 1024:.1f} KB")
                return report_path
            else:
                print("❌ Report generation failed")
                return None
                
        except Exception as e:
            print(f"\n❌ Analysis failed: {e}")
            return None

def main():
    """Main entry point."""
    # Check environment
    if not os.getenv("GEMINI_API_KEY"):
        print("❌ GEMINI_API_KEY environment variable required!")
        print("Set it with: export GEMINI_API_KEY='your_api_key'")
        return
    
    # Run analysis
    analyzer = EnhancedBusinessAnalyzer()
    report_path = analyzer.run_analysis(
        "Generate an expert-level strategic business analysis with actionable recommendations"
    )
    
    if report_path:
        print(f"\n🎯 Success! Your strategic analysis report is ready:")
        print(f"📍 {report_path}")
    else:
        print("\n💥 Analysis failed. Check the logs above.")

if __name__ == "__main__":
    main()
