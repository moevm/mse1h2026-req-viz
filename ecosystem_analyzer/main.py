from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
import time
import os

from ecosystem_analyzer.models import GraphResponse
from ecosystem_analyzer.database import Database
from ecosystem_analyzer.parser import parser

app = FastAPI()

""" CORS for Streamlit """
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  #TODO: change to real address Streamlit
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Создаём экземпляр БД (конфиги берём из переменных окружения)
db = Database(
    uri=os.getenv("NEO4J_URI", "bolt://neo4j:7687"),
    user=os.getenv("NEO4J_USER", "neo4j"),
    password=os.getenv("NEO4J_PASSWORD", "test1234"),
    database=os.getenv("NEO4J_DATABASE", "neo4j")
)

# 4. Подключение при старте приложения
@app.on_event("startup")
def startup_event():
    print("🔌 Connecting to Neo4j...")
    db.connect()
    print("✅ Connected to Neo4j")

# 5. Отключение при остановке приложения
@app.on_event("shutdown")
def shutdown_event():
    print("🔌 Disconnecting from Neo4j...")
    db.disconnect()
    print("✅ Disconnected")

# 6. Тестовый эндпоинт: проверка подключения
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
    source: str = Query(..., description="Source of data (URL, name project etc.)"),
    depth: int = 2,
    limit: int = 100
):
    start_time = time.time()
    
    # Search in DB
    result = db.get_graph_by_technology(source, depth=depth, limit=limit)

    if result is None:
        # Если не найдено — пока просто возвращаем 404
        # Позже здесь будет логика вызова парсера
        raise HTTPException(status_code=404, detail=f"Technology '{source}' not found in database")

    return result

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
