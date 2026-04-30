import yaml
from pathlib import Path
from typing import List, Dict, Any, Optional
from .sparql import WikidataSPARQLClient
from .rest import WikidataRestClient


class WikidataClient:
    """Клиент для выполнения запросов к Wikidata через SPARQL и REST API."""

    def __init__(
        self,
        relationships_path: Optional[Path] = None,
        config_path: Optional[Path] = None,
        parsing_type: Optional[str] = "rest",
    ):
        base = Path(__file__).parent.parent
        self.relationships_path = relationships_path or base / "relationships.yml"
        self.config_path = config_path or base / "config.yml"
        self.parsing_type = parsing_type

        self.relationship_types = self._load_relationships()
        self.config = self._load_config()

        self.sparql = WikidataSPARQLClient(
            self.config.get("links", {}).get("wikidata_sparql_endpoint")
        )
        self.rest = WikidataRestClient(
            self.config.get("links", {}).get("wikidata_rest_endpoint"), self.config
        )

    def _load_config(self) -> Dict[str, Any]:
        with open(self.config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    def _load_relationships(self) -> List[Dict[str, Any]]:
        with open(self.relationships_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data.get("relationship_types", [])

    def get_technology_info(self, tech_name: str) -> Optional[Dict[str, Any]]:
        """Получает полную информацию о технологии по её названию."""
        return self.rest.get_technology_info(tech_name)

    def get_sitelink(self, item_id: str) -> Optional[str]:
        """Получает название статьи English Wikipedia по QID."""
        return self.rest.get_sitelink(item_id)

    def get_data(self, tech_name: str, relationship_name: str) -> List[Dict[str, str]]:
        """Возвращает список сущностей по указанному отношению."""
        tech_info = self.get_technology_info(tech_name)
        if not tech_info:
            return []
        tech_qid = tech_info["id"]

        rel_conf = None
        for rel in self.relationship_types:
            if rel["predicate"] == relationship_name:
                rel_conf = rel
                break
        if not rel_conf:
            raise ValueError(f"Неизвестное отношение: {relationship_name}")

        if relationship_name == "used by":
            return self.sparql.get_using_technology(tech_qid)

        prop_pid = rel_conf["wikidata_property"]
        if self.parsing_type == "rest":
            return self.rest.get_related_entities(prop_pid, tech_qid)
        else:
            return self.sparql.get_related_entities(prop_pid, tech_qid)
