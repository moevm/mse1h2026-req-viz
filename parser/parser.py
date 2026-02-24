import yaml
from pathlib import Path
from typing import List, Dict, Any, Optional
from .wikidata.wikidata import WikidataClient


class Parser:
    """Основной класс для построения графа отношений между технологиями."""

    def __init__(self, technologies_path: Optional[Path] = None, relationships_path: Optional[Path] = None):
        base = Path(__file__).parent
        technologies_path = technologies_path or base / "technologies.yml"
        relationships_path = relationships_path or base / "relationships.yml"
        
        self.wikidata_client = WikidataClient(relationships_path, technologies_path)

    def graph(self, technologies: List[str], relationships: List[str]) -> Dict[str, Any]:
        """Строит граф для указанных технологий и отношений."""
        unknown = [t for t in technologies if t not in self.wikidata_client.tech_map]
        if unknown:
            raise ValueError(f"Неизвестные технологии: {unknown}")
        
        nodes = []
        edges = []
        node_ids = set()
        
        for tech_name in technologies:
            tech_qid = self.wikidata_client.tech_map[tech_name]
            
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
