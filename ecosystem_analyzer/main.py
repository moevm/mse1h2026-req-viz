from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from concurrent.futures import ThreadPoolExecutor
import os
import logging
import asyncio

from ecosystem_analyzer.models import GraphResponse
from ecosystem_analyzer.database import Database
from ecosystem_analyzer.parser import ParserWrapper

MAX_DEPTH = 10 # Max depth of graph response TODO: remove or replace to env file
MAX_NODES = 100 # Max nodes to return
ALLOWED_REL_TYPES = [ #TODO: replace to env file, for parser/parser also or remove from everywhere
    "uses", "used by", "based on", "inspired by", "creator", "developer", "programmed in", "owned by"
]
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

logger = logging.getLogger(__name__)

app = FastAPI()

logger = logging.getLogger(__name__)

executor = ThreadPoolExecutor(max_workers=10)

""" CORS for Streamlit """
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: change to real address Streamlit
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

db = Database(
    uri=os.getenv("NEO4J_URI", "bolt://neo4j:7687"),
    user=os.getenv("NEO4J_USER", "neo4j"),
    password=os.getenv("NEO4J_PASSWORD", "test1234"),
    database=os.getenv("NEO4J_DATABASE", "neo4j"),
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
    technology: str = Query(
        ..., description="Technology name (e.g., 'Kafka', 'PostgreSQL')"
    ),
    depth: int = Query(1, ge=1, le=MAX_DEPTH, description="Graph traversal depth"),
    limit: int = Query(MAX_NODES, ge=1, description="Max nodes to return"),
    rel_types: Optional[str] = Query(
        None,
        description="Comma-separated relationship types (e.g., 'USED_WITH,DEPENDS_ON')",
    ),
):
    logger.info(f"Requesting graph for: {technology} (depth={depth}, limit={limit})")
    loop = asyncio.get_event_loop()

    # TODO: delete that
    rel_types_lower = ALLOWED_REL_TYPES
    rel_types_upper=[x.upper().replace(" ", "_") for x in rel_types_lower]

    # Search in DB
    graph = await loop.run_in_executor(executor,
                                       db.get_graph_by_technology,
                                       technology,
                                       depth,
                                       limit,
                                       rel_types_upper)

    if graph:
        logger.info(f"Found '{technology}' in database ({len(graph.nodes)} nodes)")
        return graph

    # Parse
    logger.info(f"'{technology}' not found in database, calling parser...")
    try:
        graph = await loop.run_in_executor(executor,
                                           parser.parse_graph,
                                           technology,
                                           rel_types_lower)
    except Exception as e:
        logger.error(f"Parser error for '{technology}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Parser error: {str(e)}")

    if not graph:
        logger.info("Could not parse source")
        raise HTTPException(status_code=404, detail="Could not parse source")

    # Save in DB
    logger.info(f"Saving graph for '{technology}' to database...")
    try:
        await loop.run_in_executor(executor,
                                   db.save_graph,
                                   graph,
                                   technology)
        logger.info(f"Graph saved ({len(graph.nodes)} nodes, {len(graph.edges)} edges)")
    except Exception as e:
        logger.error(f"Failed to save graph for '{technology}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

    # Возвращаем именно тот граф, который сохранили в бд
    final_graph = await loop.run_in_executor(
        executor,
        db.get_graph_by_technology,
        technology, depth, limit, rel_types_upper
    )

    return final_graph


""" Entry point to the API """
@app.get("/")
async def root():
    return {
        "name": "Ecosystem Graph API",
        "endpoints": [
            {
                "path": "/api/graph",
                "method": "GET",
                "description": "Get graph by source",
            }
        ],
    }
