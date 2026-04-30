import yaml
from pathlib import Path
from typing import List, Dict, Any, Optional
from .sparql import DBpediaSPARQLClient


class DBpediaClient:
    """Клиент для выполнения запросов к DBpedia через SPARQL."""

    def __init__(
        self,
        relationships_path: Optional[Path] = None,
        config_path: Optional[Path] = None,
    ):
        base = Path(__file__).parent.parent
        self.relationships_path = relationships_path or base / "relationships.yml"
        self.config_path = config_path or base / "config.yml"

        self.relationship_types = self._load_relationships()
        self.config = self._load_config()

        self.sparql = DBpediaSPARQLClient(
            self.config.get("links", {}).get("dbpedia_sparql_endpoint"),
            self.config.get("links", {}).get("dbpedia_resource_base"),
        )

    def _load_config(self) -> Dict[str, Any]:
        with open(self.config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    def _load_relationships(self) -> List[Dict[str, Any]]:
        with open(self.relationships_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data.get("relationship_types", [])

    def get_data(
        self, local_name: str, relationship_name: str
    ) -> List[Dict[str, str]]:
        """Возвращает список сущностей по указанному отношению через DBpedia."""
        rel_conf = None
        for rel in self.relationship_types:
            if rel["predicate"] == relationship_name:
                rel_conf = rel
                break
        if not rel_conf:
            raise ValueError(f"Неизвестное отношение: {relationship_name}")

        dbpedia_mappings = rel_conf.get("dbpedia", [])
        if not dbpedia_mappings:
            return []

        all_entities = []
        seen = set()
        for mapping in dbpedia_mappings:
            dbo_property = mapping.get("property")
            direction = mapping.get("direction", "forward")
            if not dbo_property:
                continue

            if direction == "reverse":
                entities = self.sparql.get_related_entities_reverse(
                    dbo_property, local_name
                )
            else:
                entities = self.sparql.get_related_entities_forward(
                    dbo_property, local_name
                )

            for entity in entities:
                if entity["id"] not in seen:
                    seen.add(entity["id"])
                    all_entities.append(entity)

        return all_entities
