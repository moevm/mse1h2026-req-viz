from typing import Optional, List
from .models import Node, Edge, Statistics, GraphResponse
from parser.parser import Parser

class ParserWrapper:
    """ Parser wrapper """
    def __init__(self):
        self._parser =  Parser()
    def parse_graph(
            self,
            technology: str,
            relationships: Optional[List[str]] = None
    ) -> Optional[GraphResponse]:
        try:
            raw_graph = self._parser.graph(
                technologies=[technology],
                relationships=relationships
            )
        except ValueError as e:
            # Технология не найдена в Wikidata
            if "Неизвестные технологии" in str(e):
                return None
            raise

        return self._convert_to_graph_response(raw_graph)

    def _convert_to_graph_response(self, raw_graph: dict) -> GraphResponse:
        nodes = [
            Node(
                id=node["id"],
                label=node["name"],
            )
            for node in raw_graph.get("nodes", [])
        ]

        edges = [
            Edge(
                source=edge["source"],
                target=edge["target"],
                type=edge["predicate"],
                weight=1.0  # Парсер не возвращает веса, ставим дефолт
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
                truncated=False
            )
        )

MOCK_GRAPH = GraphResponse(
    nodes=[
        {"id": "tech_001", "label": "Apache Kafka", "type": "Technology"},
        {"id": "tech_002", "label": "RabbitMQ", "type": "Technology"},
        {"id": "comp_001", "label": "Confluent", "type": "Company"},
        {"id": "lic_001", "label": "Apache 2.0", "type": "License"}
    ],
    edges=[
        {"source": "tech_001", "target": "tech_002", "type": "ALTERNATIVE_TO", "weight": 0.9},
        {"source": "tech_001", "target": "comp_001", "type": "DEVELOPED_BY", "weight": 1.0},
        {"source": "tech_001", "target": "lic_001", "type": "LICENSED_UNDER", "weight": 1.0}
    ],
    statistics=Statistics(
        total_nodes=4,
        total_edges=3,
        max_depth=2
    )
)

