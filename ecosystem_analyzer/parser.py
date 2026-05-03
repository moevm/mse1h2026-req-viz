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
        self, technologies: List[str], relationships: List[str]
    ) -> Optional[GraphResponse]:
        """Получить граф для заданной технологии и списка отношений."""
        raw_graph: Dict[str, Any]
        relationships =[x.lower().replace("_", " ") for x in relationships]

        try:
            raw_graph = self._parser.graph(
                technologies=technologies, relationships=relationships
            )
        except Exception as e:
            logger.error(f"Parser error for '{technologies}': {e}", exc_info=True)
            return None

        return self._to_api_format(raw_graph)

    @staticmethod
    def _to_api_format(raw_graph: dict) -> GraphResponse:
        """Преобразует граф от парсера (parser/parser) → GraphResponse (ecosystem_analyzer.models).
        Результат является унифицированным форматом для взаимодействия всех 4 модулей системы."""
        nodes = [
            Node(
                id=node["id"],
                label=node["name"],
                type=node["type"].replace("_", " ").title().replace(" ", ""),
            )
            for node in raw_graph.get("nodes", [])
        ]

        edges = [
            Edge(
                source=edge["source"],
                target=edge["target"],
                type=edge["predicate"].upper().replace(" ", "_"),
                weight=1.0,  # Парсер не возвращает веса, ставим дефолт
            )
            for edge in raw_graph.get("edges", [])
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