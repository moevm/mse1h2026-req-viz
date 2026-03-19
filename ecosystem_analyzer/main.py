from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
import os
import logging

from ecosystem_analyzer.models import GraphResponse
from ecosystem_analyzer.database import Database
from ecosystem_analyzer.parser import ParserWrapper

MAX_DEPTH = 10 # Max depth of graph response TODO: remove or replace to env file
MAX_NODES = 100 # Max nodes to return
ALLOWED_REL_TYPES = {
    "USED_WITH", "ALTERNATIVE_FOR", "DEPENDS_ON",
    "DEVELOPED_BY", "USES_LICENSE"
}

app = FastAPI()

logger = logging.getLogger(__name__)

""" CORS for Streamlit """
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  #TODO: change to real address Streamlit
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

db = Database(
    uri=os.getenv("NEO4J_URI", "bolt://neo4j:7687"),
    user=os.getenv("NEO4J_USER", "neo4j"),
    password=os.getenv("NEO4J_PASSWORD", "test1234"),
    database=os.getenv("NEO4J_DATABASE", "neo4j")
)

parser = ParserWrapper()

@app.on_event("startup")
def startup_event():
    logger.info("Connecting to Database...")
    db.connect()
    logger.info("Connected to Data")

@app.on_event("shutdown")
def shutdown_event():
    logger.info("Disconnecting from Neo4j...")
    db.disconnect()
    logger.info("Disconnected")

@app.get("/api/health")
def health_check():
    return {"status": "ok", "connected": db.is_connected()}

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
    technology: str = Query(..., description="Technology name (e.g., 'Kafka', 'PostgreSQL')"),
    depth: int = Query(1, ge=1, le=MAX_DEPTH, description="Graph traversal depth"),
    limit: int = Query(MAX_NODES, ge=1, description="Max nodes to return"),
    rel_types: Optional[str] = Query(None, description="Comma-separated relationship types (e.g., 'USED_WITH,DEPENDS_ON')")
):
    logger.info(f"Requesting graph for: {technology} (depth={depth}, limit={limit})")

    rel_types_list = ALLOWED_REL_TYPES
    if rel_types:
        rel_types_list = rel_types.split(",")
    
    # Search in DB
    graph = db.get_graph_by_technology(
        technology,
        depth=depth,
        limit=limit,
        rel_types=rel_types_list
    )

    if graph:
        return graph
    
    # Parse
    try:
        graph = parser.parse_graph(technology, rel_types)
    except Exception as e:
        logger.error(f"Parser error for '{technology}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Parser error: {str(e)}")
    
    if not graph:
        logger.info(f"Could not parse source")
        raise HTTPException(status_code=404, detail="Could not parse source")
    
    # Save in DB
    try:
        db.save_graph(graph, source=technology)
    except Exception as e:
        logger.error(f"Failed to save graph for '{technology}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    
    return db.get_graph_by_technology(technology, depth=depth, limit=limit)

""" Entry point to the API """
@app.get("/")
async def root():
    return {
        "name": "Ecosystem Graph API",
        "endpoints": [
            {"path": "/api/graph", "method": "GET", "description": "Get graph by source"}
        ]
    }
