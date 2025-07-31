# app.py
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import uuid
from graph import app
from data_ingestion.loader_main import ingest_all_csvs

def run_workflow():
    """Main workflow execution"""
    
    # Step 1: Data ingestion
    print("--- 1. Starting Data Ingestion ---")
    try:
        ingest_all_csvs(folder_path="data")
        print("✅ Data ingestion complete\n")
    except Exception as e:
        print(f"❌ Data ingestion failed: {e}\n")
        return

    # Step 2: Run agent workflow
    print("--- 2. Starting Agent Workflow ---")
    session_id = str(uuid.uuid4())
    print(f"🚀 Session ID: {session_id}")

    initial_state = {
        "messages": [{"role": "user", "content": "Generate a strategic business report."}],
        "report_path": None
    }

    try:
        # Execute workflow
        final_state = None
        for state in app.stream(initial_state, stream_mode="values"):
            final_state = state
            
            if state.get("messages"):
                last_message = state["messages"][-1]
                print(f"📝 {last_message['role']}: {last_message['content'][:100]}...")
        
        # Check final result
        if final_state and final_state.get("report_path"):
            print(f"\n✅ SUCCESS: Report saved at {final_state['report_path']}")
            
            # Verify file exists
            if os.path.exists(final_state['report_path']):
                file_size = os.path.getsize(final_state['report_path'])
                print(f"📄 File size: {file_size} bytes")
            else:
                print("❌ WARNING: Report file not found on disk")
        else:
            print("\n❌ FAILED: No report path returned")
            
    except Exception as e:
        print(f"\n❌ Workflow failed: {e}")

    print("\n--- Workflow Finished ---")

if __name__ == "__main__":
    run_workflow()