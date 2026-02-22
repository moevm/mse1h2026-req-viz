from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
import time

from .models import GraphResponse
from .database import db
from .parser import parser

app = FastAPI()

""" CORS for Streamlit """
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  #TODO: change to real address Streamlit
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

"""
Get graph by source
    Main endpoint containing business logic:
    1. Check if graph exists in DB for the given source
    2. If exists — return cached graph
    3. If not exists — invoke parser
    4. Save result to database
    5. Return result to client
"""
@app.get("/api/graph", response_model=GraphResponse)
async def get_graph(
    source: str = Query(..., description="Source of data (URL, name project etc.)")
):
    start_time = time.time()
    
    # Search in DB
    existing_graph = db.get_graph_by_source(source)

    if existing_graph:
        return existing_graph
    
    # Parse
    try:
        parsed_graph = parser.parse_graph(source)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Parser error: {str(e)}")
    
    if not parsed_graph:
        raise HTTPException(status_code=404, detail="Could not parse source")
    
    # Save in DB
    saved = db.save_graph(source, parsed_graph)
    if not saved:
        raise HTTPException(status_code=500, detail="Graph was not saved properly")
    
    return parsed_graph

""" Entry point to the API """
@app.get("/")
async def root():
    return {
        "name": "Ecosystem Graph API",
        "endpoints": [
            {"path": "/api/graph", "method": "GET", "description": "Get graph by source"},
            {"path": "/api/graph/{graph_id}", "method": "GET", "description": "Get graph by ID"},
            {"path": "/api/cache/info", "method": "GET", "description": "Cache information"}
        ]
    }
