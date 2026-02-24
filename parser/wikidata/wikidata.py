import yaml
from pathlib import Path
from typing import List, Dict, Any, Optional
from .sparql import WikidataSPARQLClient
from .rest import WikidataRestClient


class WikidataClient:
    """Клиент для выполнения запросов к Wikidata через SPARQL и REST API."""
    
    def __init__(self, relationships_path: Optional[Path] = None,
                 technologies_path: Optional[Path] = None,
                 config_path: Optional[Path] = None,
                 parsing_type: Optional[str] = "sparql"):
        base = Path(__file__).parent.parent
        self.relationships_path = relationships_path or base / "relationships.yml"
        self.technologies_path = technologies_path or base / "technologies.yml"
        self.config_path = config_path or base / "config.yml"
        self.parsing_type = parsing_type
        
        self.relationship_types = self._load_relationships()
        self.tech_map = self._load_technologies()
        self.config = self._load_config()
        
        self.sparql = WikidataSPARQLClient(self.config.get('links', {}).get('wikidata_sparql_endpoint'))
        self.rest = WikidataRestClient(self.config.get('links', {}).get('wikidata_rest_endpoint'))

    def _load_config(self) -> Dict[str, Any]:
        with open(self.config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    
    def _load_relationships(self) -> List[Dict[str, Any]]:
        with open(self.relationships_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        return data.get('relationship_types', [])
    
    def _load_technologies(self) -> Dict[str, str]:
        with open(self.technologies_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        return data.get('technologies', {})

    def get_data(self, tech_name: str, relationship_name: str) -> List[Dict[str, str]]:
        if relationship_name in ["used by", "uses"]:
            return self._get_companies_using_technology(tech_name, relationship_name)

    def _get_companies_using_technology(self, tech_name: str, relationship_name: str) -> List[Dict[str, str]]:
        """Находит компании, использующие технологию по заданному отношению."""
        if tech_name not in self.tech_map:
            raise ValueError(f"Неизвестная технология: {tech_name}")
        
        tech_qid = self.tech_map[tech_name]
        
        rel_conf = None
        for rel in self.relationship_types:
            if rel['predicate'] == relationship_name:
                rel_conf = rel
                break
        
        if not rel_conf:
            raise ValueError(f"Неизвестное отношение: {relationship_name}")
        
        prop_pid = rel_conf['wikidata_property']
        
        if self.parsing_type == "rest":
            return self.rest.get_companies_using_technology(prop_pid, tech_qid)
        else:
            return self.sparql.get_companies_using_technology(prop_pid, tech_qid)
