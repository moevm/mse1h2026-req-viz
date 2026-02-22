import time
import random
from models import GraphResponse, Node, Edge, Statistics
from typing import Optional

""" Parser stub """
class SimpleParser:
    def parse_graph(self, source_key: str) -> Optional[GraphResponse]:
        time.sleep(5)
        return MOCK_GRAPH

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

parser = SimpleParser()
