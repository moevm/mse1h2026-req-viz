# services.py
from typing import List, Dict, Any
from config import EDGE_TYPES, EDGE_TYPE_NAMES


class MockBackendService:
    """Сервис-заглушка для имитации бэкенда"""
    
    @staticmethod
    def get_available_connection_types() -> List[str]:
        return EDGE_TYPES
    
    @staticmethod
    def get_connection_type_display_name(type_code: str) -> str:
        return EDGE_TYPE_NAMES.get(type_code, type_code)
    
    @staticmethod
    def search_technology(query: str) -> Dict[str, Any]:
        mock_db = {
            "kafka": {
                "id": "tech_001",
                "name": "Apache Kafka",
                "type": "Technology",
                "category": "Message Broker"
            },
            "rabbitmq": {
                "id": "tech_002",
                "name": "RabbitMQ",
                "type": "Technology",
                "category": "Message Broker"
            },
            "postgresql": {
                "id": "tech_003",
                "name": "PostgreSQL",
                "type": "Technology",
                "category": "Database"
            },
            "docker": {
                "id": "tech_004",
                "name": "Docker",
                "type": "Technology",
                "category": "Containerization"
            },
            "kubernetes": {
                "id": "tech_005",
                "name": "Kubernetes",
                "type": "Technology",
                "category": "Orchestration"
            }
        }
        return mock_db.get(query.lower().strip(), None)
    
    @staticmethod
    def build_graph(technology_name: str) -> Dict[str, Any]:
        """Построение графа зависимостей (без лицензий)"""
        mock_graph = {
            "nodes": [
                {"id": "tech_001", "label": "Apache Kafka", "type": "Technology"},
                {"id": "tech_002", "label": "RabbitMQ", "type": "Technology"},
                {"id": "tech_006", "label": "Zookeeper", "type": "Technology"},
                {"id": "tech_007", "label": "Spark", "type": "Technology"},
                {"id": "tech_008", "label": "Flink", "type": "Technology"},
                {"id": "comp_001", "label": "Confluent", "type": "Company"},
                {"id": "comp_002", "label": "Apache Foundation", "type": "Company"},
                {"id": "tech_009", "label": "Python", "type": "Technology"},
                {"id": "tech_010", "label": "Java", "type": "Technology"},
            ],
            "edges": [
                {"source": "tech_001", "target": "tech_002", "type": "ALTERNATIVE_TO", "weight": 0.9},
                {"source": "tech_001", "target": "tech_006", "type": "DEPENDS_ON", "weight": 1.0},
                {"source": "tech_001", "target": "tech_007", "type": "USED_WITH", "weight": 0.85},
                {"source": "tech_001", "target": "tech_008", "type": "USED_WITH", "weight": 0.75},
                {"source": "tech_001", "target": "comp_001", "type": "DEVELOPED_BY", "weight": 1.0},
                {"source": "tech_001", "target": "comp_002", "type": "DEVELOPED_BY", "weight": 1.0},
                {"source": "tech_001", "target": "tech_009", "type": "USED_WITH", "weight": 0.8},
                {"source": "tech_001", "target": "tech_010", "type": "USED_WITH", "weight": 0.95},
                {"source": "tech_007", "target": "tech_009", "type": "USED_WITH", "weight": 0.9},
                {"source": "tech_008", "target": "tech_010", "type": "USED_WITH", "weight": 0.85},
            ],
            "statistics": {
                "total_nodes": 9,
                "total_edges": 10,
                "max_depth": 2
            }
        }
        return mock_graph