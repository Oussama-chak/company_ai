import os
import uuid
from typing import List
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from data_ingestion.loader_main import ingest_all_csvs
from graph import app as langgraph_app

# Ensure data and reports directories exist
os.makedirs('data', exist_ok=True)
os.makedirs('reports', exist_ok=True)

fastapi_app = FastAPI(
    title="Business Intelligence API",
    description="API for CSV data ingestion and strategic report generation.",
    version="1.0.0",
)

# Configure CORS for your React frontend
fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@fastapi_app.post("/upload-csv")
async def upload_csv(files: List[UploadFile] = File(...)):
    """
    Uploads multiple CSV files and ingests their data into the database.
    """
    uploaded_filenames = []
    for file in files:
        if not file.filename.endswith('.csv'):
            raise HTTPException(status_code=400, detail=f"Only CSV files are allowed. '{file.filename}' is not a CSV.")

        file_path = os.path.join("data", file.filename)
        try:
            with open(file_path, "wb") as buffer:
                buffer.write(await file.read())
            uploaded_filenames.append(file.filename)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to save file '{file.filename}': {e}")
    
    try:
        ingest_all_csvs(folder_path="data")
        return {"message": f"Files {uploaded_filenames} uploaded and ingested successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to ingest data into database: {e}")

@fastapi_app.get("/run-workflow")
async def run_workflow():
    """
    Triggers the strategic business report generation workflow.
    Returns the path to the generated PDF report and the judge's analysis.
    """
    session_id = str(uuid.uuid4())
    initial_state = {
        "messages": [{"role": "user", "content": "Generate a strategic business report."}],
        "report_path": None,
        "report_text_content": None, # Initialize new field
        "judge_analysis": None # Initialize new field
    }

    try:
        final_state = None
        for state in langgraph_app.stream(initial_state, stream_mode="values"):
            final_state = state
        
        if final_state and final_state.get("report_path"):
            report_path = final_state['report_path']
            report_filename = os.path.basename(report_path) if os.path.exists(report_path) else None
            
            # Extract judge analysis from final state
            judge_analysis = final_state.get("judge_analysis")

            if report_filename:
                return {
                    "message": "Workflow completed successfully",
                    "report_filename": report_filename,
                    "report_url": f"/reports/{report_filename}", # Provide full URL for convenience
                    "judge_analysis": judge_analysis # <--- RETURN JUDGE ANALYSIS
                }
            else:
                raise HTTPException(status_code=500, detail="Report file not found after generation.")
        else:
            raise HTTPException(status_code=500, detail="Workflow failed: No report path returned.")
    except Exception as e:
        print(f"Workflow execution failed: {e}")
        raise HTTPException(status_code=500, detail=f"Workflow execution failed: {e}")

@fastapi_app.get("/reports/{filename}")
async def get_report(filename: str):
    """
    Serves a generated PDF report by its filename.
    """
    report_path = os.path.join("reports", filename)
    if not os.path.exists(report_path):
        raise HTTPException(status_code=404, detail="Report not found.")
    
    return FileResponse(report_path, media_type="application/pdf", filename=filename)
