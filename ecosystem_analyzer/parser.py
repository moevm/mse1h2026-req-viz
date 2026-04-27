from typing import Optional, List, Dict, Any
from .models import Node, Edge, Statistics, GraphResponse
from parser.parser import Parser
import logging
logger = logging.getLogger(__name__)


class ParserWrapper:
    """Обертка над классом Parser из модуля parser."""

    def __init__(self):
        self._parser = Parser()

    def parse_graph(
        self, technology: str, relationships: List[str]
    ) -> Optional[GraphResponse]:
        """Получить граф для заданной технологии и списка отношений."""
        raw_graph: Dict[str, Any]
        try:
            logger.info(f"[PARSER] Start parsing: {technology}, types: {relationships}")
            raw_graph = self._parser.graph(
                technologies=[technology], relationships=relationships
            )
        except ValueError:
            logger.warning(f"[PARSER] Returning None for {technology}. Reason: ValueError")
            return None

        return self._to_api_format(raw_graph)

    @staticmethod
    def _to_api_format(raw_graph: dict) -> GraphResponse:
        """Преобразует граф от парсера (parser/parser) → GraphResponse (ecosystem_analyzer.models).
        Результат является унифицированным форматом для взаимодействия всех 4 модулей системы."""
        raw_nodes = raw_graph.get("nodes", [])
        raw_edges = raw_graph.get("edges", [])
        logger.info(f"Converting graph: get {len(raw_nodes)} nodes and {len(raw_edges)} edges from parser.")

        nodes = [
            Node(
                id=node["id"],
                label=node["name"].lower(),
                type=node["type"].replace("_", " ").title().replace(" ", ""),
            )
            for node in raw_nodes
        ]

        edges = [
            Edge(
                source=edge["source"],
                target=edge["target"],
                type=edge["predicate"].upper().replace(" ", "_"),
                weight=1.0,  # Парсер не возвращает веса, ставим дефолт
            )
            for edge in raw_edges
        ]

        return GraphResponse(
            nodes=nodes,
            edges=edges,
            statistics=Statistics(
                total_nodes=len(nodes),
                total_edges=len(edges),
                max_depth=None,
                truncated=False,
            ),
        )
