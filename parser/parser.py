import yaml
from pathlib import Path
from typing import List, Dict, Any, Optional
from .wikidata.wikidata import WikidataClient


class Parser:
    """Основной класс для построения графа отношений между технологиями."""

    def __init__(self, relationships_path: Optional[Path] = None, config_path: Optional[Path] = None):
        base = Path(__file__).parent
        relationships_path = relationships_path or base / "relationships.yml"
        config_path = config_path or base / "config.yml"
        
        self.wikidata_client = WikidataClient(relationships_path, config_path)

    def graph(self, technologies: List[str], relationships: List[str]) -> Dict[str, Any]:
        """Строит граф для указанных технологий и отношений."""
        nodes = []
        edges = []
        node_ids = set()
        
        for tech_name in technologies:
            tech_info = self.wikidata_client.get_technology_info(tech_name)
            if not tech_info:
                print(f"Предупреждение: технология '{tech_name}' не найдена")
                continue
            
            tech_qid = tech_info["id"]
            
            node_ids.add(tech_qid)
            nodes.append({
                "id": tech_qid,
                "name": tech_name,
                "type": "technology"
            })
            
            for rel_name in relationships:
                data = self.wikidata_client.get_data(tech_name, rel_name)
                
                for item in data:
                    if item["id"] not in node_ids:
                        node_ids.add(item["id"])
                        nodes.append(item)
                    
                    edges.append({
                        "source": item["id"],
                        "target": tech_qid,
                        "predicate": rel_name,
                        "source_id": "wikidata"
                    })
        
        return {
            "nodes": nodes,
            "edges": edges
        }
