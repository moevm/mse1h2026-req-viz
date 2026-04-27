from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List, Dict, Tuple
import os
import logging
from concurrent.futures import ThreadPoolExecutor
import asyncio
import requests
import json
from datetime import datetime

from ecosystem_analyzer.models import GraphResponse, Node, Edge, Statistics
from ecosystem_analyzer.database import Database
from ecosystem_analyzer.parser import ParserWrapper

MAX_DEPTH = 10 # Max depth of graph response
MAX_NODES = 100 # Max nodes to return
ALLOWED_REL_TYPES = [
    "uses", "used by", "based on", "inspired by", "creator", "developer", "programmed in", "owned by"
]

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

logger = logging.getLogger(__name__)

executor = ThreadPoolExecutor(max_workers=5)

app = FastAPI()

""" CORS for Streamlit """
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501"],
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

parser: Optional[ParserWrapper] = None


@app.on_event("startup")
def startup_event():
    global parser
    logger.info("Connecting to Database...")
    db.connect()
    logger.info("Connecting to Parser...")
    try:
        parser = ParserWrapper()
    except Exception as e:
        logger.error(f"Failed to initialize ParserWrapper: {e}", exc_info=True)


@app.on_event("shutdown")
def shutdown_event():
    logger.info("Disconnecting from Neo4j...")
    db.disconnect()
    logger.info("Disconnected")
    executor.shutdown(wait=True)


@app.get("/api/health")
def health_check():
    return {"status": "ok", "connected": db.is_connected()}

def merge_graphs(graphs: List[GraphResponse]) -> GraphResponse:
    """ Combines multiple graph responses into a single graph. """
    unique_nodes: Dict[str, Node] = {}
    unique_edges: Dict[Tuple[str, str, str], Edge] = {}

    for g in graphs:
        if not g:
            continue

        for node in g.nodes:
            if node.id not in unique_nodes:
                unique_nodes[node.id] = node

        for edge in g.edges:
            edge_key = (edge.source, edge.target, edge.type)
            if edge_key not in unique_edges:
                unique_edges[edge_key] = edge

    final_nodes = list(unique_nodes.values())
    final_edges = list(unique_edges.values())

    return GraphResponse(
        nodes=final_nodes,
        edges=final_edges,
        statistics=Statistics(
            total_nodes=len(final_nodes),
            total_edges=len(final_edges),
            max_depth = max(
                (g.statistics.max_depth for g in graphs if g.statistics and g.statistics.max_depth is not None),
                default=1
            ),
            truncated=False
        )
    )

async def check_cache_for_technologies(
        tech_list: List[str],
        depth: int,
        limit: int,
        rel_types_upper: List[str],
        loop: asyncio.AbstractEventLoop
) -> Tuple[List[GraphResponse], List[str]]:
    """ For each technology in the provided list, checks the database cache for an existing graph. """
    cached_graphs: List[GraphResponse] = []
    to_parse_list: List[str] = []

    for tech in tech_list:
        logger.info(f"Checking cache for '{tech}'...")
        try:
            db_graph = await loop.run_in_executor(
                executor,
                db.get_graph_by_technology,
                tech,
                depth,
                limit,
                rel_types_upper
            )

            if db_graph and db_graph.nodes:
                logger.info(f"Cache HIT for '{tech}' ({len(db_graph.nodes)} nodes)")
                cached_graphs.append(db_graph)
            else:
                logger.info(f"Cache MISS for '{tech}'")
                to_parse_list.append(tech)

        except Exception as e:
            logger.warning(f"Error checking cache for '{tech}': {e}. Adding to parse list.")
            to_parse_list.append(tech)

    return cached_graphs, to_parse_list

async def parse_and_save_missing(
        to_parse_list: List[str],
        rel_types: List[str],
        loop: asyncio.AbstractEventLoop
) -> List[GraphResponse]:
    """ Parses a graph for the list of missing technologies. Saves the resulting graph to the database. """
    if not to_parse_list:
        return []

    logger.info(f"Parsing missing technologies: {to_parse_list}")
    if parser is None:
        raise HTTPException(status_code=503, detail="Parser service unavailable")

    parsed_graphs = []
    labels_parsed_graphs = set()
    max_retries = 3

    for retry in range(max_retries):
        if len(labels_parsed_graphs) >= len(to_parse_list):
            break

        # Wait before retrying to allow Wikidata rate limit to reset
        if retry > 0:
            await asyncio.sleep(60)

        for tech_name in to_parse_list:

            if tech_name.lower() in labels_parsed_graphs :
                continue

            new_graph = None
            await asyncio.sleep(15)

            try:
                new_graph = await loop.run_in_executor(
                    executor,
                    parser.parse_graph,
                    [tech_name],
                    rel_types
                )
            except Exception as e:
                logger.error(f"Parser error for {to_parse_list}: {e}", exc_info=True)

            if new_graph and new_graph.nodes:
                logger.info(f"Parser returned graph with {len(new_graph.nodes)} nodes")
                labels_parsed_graphs.add(tech_name.lower())
                parsed_graphs.append(new_graph)
                try:
                    await loop.run_in_executor(
                        executor,
                        db.save_graph,
                        new_graph,
                        tech_name
                    )
                    logger.info(f"Saved graph for '{tech_name}'")
                except Exception as e:
                    logger.error(f"Failed to save graph for '{tech_name}': {e}")
            else:
                logger.warning(f"Parser returned empty result for {tech_name}")

    return parsed_graphs





@app.get("/api/graph", response_model=GraphResponse)
async def get_graph(
    technology: str = Query(
        ..., description="Comma-separated technology names (e.g., 'python, pandas')"
    ),
    depth: int = Query(1, ge=1, le=MAX_DEPTH, description="Graph traversal depth"),
    limit: int = Query(MAX_NODES, ge=1, le=MAX_NODES, description="Max nodes to return"),
    rel_types: Optional[str] = Query(
        None,
        description="Comma-separated relationship types (e.g., 'USED_WITH,DEPENDS_ON')",
    ),
):
    """
    Get graph by source
        Main endpoint containing business logic:
        1. Check if graph exists in DB for the given source
        2. If exists — return cached graph
        3. If not exists — invoke parser
        4. Save result to database
        5. Return result to client
    """

    rel_types_list = ALLOWED_REL_TYPES
    if rel_types:
        rel_types_list = rel_types.split(",")

    tech_list = [t.strip() for t in technology.split(",") if t.strip()]
    if not tech_list:
        raise HTTPException(status_code=400, detail="No technologies provided")

    logger.info(f"Requesting graph for: {tech_list} (depth={depth}, limit={limit})")

    loop = asyncio.get_running_loop() # for async

    # Search in DB
    cached_graphs, to_parse_list = await check_cache_for_technologies(
        tech_list, depth, limit, rel_types_list, loop
    )

    # Parse and saving
    missed_graphs = await parse_and_save_missing(
        to_parse_list, rel_types_list, loop
    )

    if len(missed_graphs) > 0:
        cached_graphs.extend(missed_graphs)

    if not cached_graphs:
        raise HTTPException(status_code=404, detail="No data found for any of the requested technologies")

    final_graph = merge_graphs(cached_graphs)
    if not final_graph.nodes:
        raise HTTPException(status_code=404, detail="Merged graph is empty")
    logger.info(f"Returning merged graph: {len(final_graph.nodes)} nodes, {len(final_graph.edges)} edges")
    # Save in DB
    logger.info(f"Saving graph for '{technology}' to database...")
    try:
        db.save_graph(graph, source=technology)
        logger.info(f"Graph saved ({len(graph.nodes)} nodes, {len(graph.edges)} edges)")
    except Exception as e:
        logger.error(f"Failed to save graph for '{technology}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

    return db.get_graph_by_technology(technology, depth=depth, limit=limit)


""" Entry point to the API """
@app.post("/api/report")
async def generate_report(request: Request):
    try:
        graph_data = await request.json()
        logger.info("Received graph data for report generation")
        logger.debug(f"Graph data: {graph_data}")

        ollama_url = os.getenv("OLLAMA_URL", "http://ollama:11434/api/generate")

        tech_name = graph_data.get("meta", {}).get("technology", "Unknown")
        first_node_label = next((node.get("label") for node in graph_data.get("nodes", []) if node.get("label")), "Unknown")
        if tech_name == "Unknown" and first_node_label != "Unknown":
            tech_name = first_node_label

        prompt = f"""
        Ты - эксперт по анализу технологических экосистем и зависимостей.
        Проведи профессиональный анализ графа зависимостей технологии "{tech_name}".

        Структура графа:

        {json.dumps(graph_data, ensure_ascii=False, indent=2)}

        Типы узлов:
        - Technology: Технологии и программные решения
        - Company: Компании и организации
        - Person: Персоны (разработчики, создатели)
        - License: Лицензии и условия использования
        - Organization: Организации и сообщества

        Типы связей:
        - USES: Использует
        - USED_BY: Используется
        - DEPENDS_ON_SOFTWARE: Зависит от ПО
        - BASED_ON: Основан на
        - INSPIRED_BY: Вдохновлен
        - CREATOR: Создатель
        - DEVELOPER: Разработчик
        - PROGRAMMED_IN: Написан на языке
        - OWNED_BY: Принадлежит

        Пожалуйста, предоставь анализ в следующем формате на русском языке:

        ## Обзор технологии "{tech_name}"
        Краткое описание технологии и её роль в экосистеме.

        ## Архитектурные зависимости
        Основные зависимости и взаимосвязи. Какие технологии использует "{tech_name}", от чего зависит.

        ## Экосистема и связи
        Кто создал технологию, кто поддерживает, какие компании используют.

        ## Потенциальные риски
        Возможные риски, связанные с зависимостями и использованием технологии.

        ## Рекомендации
        Практические рекомендации по использованию и мониторингу технологии.

        Используй технические термины на английском языке где это уместно (например, названия технологий), но объясняй их на русском.
        Не включай JSON или технические детали в ответ, только аналитическую информацию в формате Markdown.
        """

        ollama_request = {
            "model": "gemma:2b",
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.7,
                "top_p": 0.9
            }
        }

        response = requests.post(ollama_url, json=ollama_request, timeout=120)

        if response.status_code == 200:
            ollama_response = response.json()
            llm_response = ollama_response.get("response", "")

            frontend_response = {
                "status": "success",
                "report_markdown": llm_response,
                "generated_at": datetime.utcnow().isoformat() + "Z",
            }

            logger.info("Generated report successfully")
            return frontend_response
        else:
            logger.error(f"Ollama service error: {response.status_code} - {response.text}")
            raise HTTPException(status_code=500, detail="Failed to generate report with LLM")

    except Exception as e:
        logger.error(f"Error generating report: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error generating report: {str(e)}")

    return final_graph

@app.get("/")
async def root():
    """ Entry point to the API """
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
