import os
import uuid
from typing import List # Import List
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from data_ingestion.loader_main import ingest_all_csvs
from graph import app1 

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
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@fastapi_app.post("/upload-csv")
async def upload_csv(files: List[UploadFile] = File(...)): # <--- CHANGED HERE: 'file' to 'files', 'UploadFile' to 'List[UploadFile]'
    """
    Uploads multiple CSV files and ingests their data into the database.
    """
    uploaded_filenames = []
    for file in files: # <--- Iterate over each file
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
        ingest_all_csvs(folder_path="data") # This function already processes all CSVs in the 'data' folder
        return {"message": f"Files {uploaded_filenames} uploaded and ingested successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to ingest data into database: {e}")

@fastapi_app.get("/run-workflow")
async def run_workflow():
    """
    Triggers the strategic business report generation workflow.
    Returns the path to the generated PDF report.
    """
    session_id = str(uuid.uuid4())
    initial_state = {
        "messages": [{"role": "user", "content": "Generate a strategic business report."}],
        "report_path": None
    }

    try:
        final_state = None
        for state in app1.stream(initial_state, stream_mode="values"):
            final_state = state
        
        if final_state and final_state.get("report_path"):
            report_path = final_state['report_path']
            if os.path.exists(report_path):
                report_filename = os.path.basename(report_path)
                return {"message": "Workflow completed successfully", "report_filename": report_filename}
            else:
                raise HTTPException(status_code=500, detail="Report file not found after generation.")
        else:
            raise HTTPException(status_code=500, detail="Workflow failed: No report path returned.")
    except Exception as e:
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
