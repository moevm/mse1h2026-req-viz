from typing import Optional, List, Dict, Any
from .models import Node, Edge, Statistics, GraphResponse
from parser.parser import Parser


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
            raw_graph = self._parser.graph(
                technologies=[technology], relationships=relationships
            )
        except ValueError:
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


MOCK_GRAPH = GraphResponse(
    nodes=[
        {"id": "tech_001", "label": "Apache Kafka", "type": "Technology"},
        {"id": "tech_002", "label": "RabbitMQ", "type": "Technology"},
        {"id": "comp_001", "label": "Confluent", "type": "Company"},
        {"id": "lic_001", "label": "Apache 2.0", "type": "License"},
    ],
    edges=[
        {
            "source": "tech_001",
            "target": "tech_002",
            "type": "ALTERNATIVE_TO",
            "weight": 0.9,
        },
        {
            "source": "tech_001",
            "target": "comp_001",
            "type": "DEVELOPED_BY",
            "weight": 1.0,
        },
        {
            "source": "tech_001",
            "target": "lic_001",
            "type": "LICENSED_UNDER",
            "weight": 1.0,
        },
    ],
    statistics=Statistics(total_nodes=4, total_edges=3, max_depth=2),
)
