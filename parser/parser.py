from pathlib import Path
from typing import List, Dict, Any, Optional
from .wikidata.wikidata import WikidataClient
from .dbpedia.dbpedia import DBpediaClient


class Parser:
    """Основной класс для построения графа отношений между технологиями."""

    def __init__(
        self,
        relationships_path: Optional[Path] = None,
        config_path: Optional[Path] = None,
    ):
        base = Path(__file__).parent
        relationships_path = relationships_path or base / "relationships.yml"
        config_path = config_path or base / "config.yml"

        self.wikidata_client = WikidataClient(relationships_path, config_path)
        self.dbpedia_client = DBpediaClient(relationships_path, config_path)

        self._sitelink_cache: Dict[str, Optional[str]] = {}

    def graph(
        self, technologies: List[str], relationships: List[str]
    ) -> Dict[str, Any]:
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

            if tech_qid not in node_ids:
                node_ids.add(tech_qid)
                nodes.append({"id": tech_qid, "name": tech_name, "type": "technology"})

            dbpedia_local_name = self._resolve_dbpedia_name(tech_qid)
            if not dbpedia_local_name:
                print(f"Предупреждение: sitelink для '{tech_name}' ({tech_qid}) не найден")

            for rel_name in relationships:
                wikidata_data = self.wikidata_client.get_data(tech_name, rel_name)
                self._add_to_graph(
                    wikidata_data, "wikidata", tech_qid, rel_name,
                    nodes, edges, node_ids,
                )

                if dbpedia_local_name:
                    try:
                        dbpedia_data = self.dbpedia_client.get_data(
                            dbpedia_local_name, rel_name
                        )
                        self._add_to_graph(
                            dbpedia_data, "dbpedia", tech_qid, rel_name,
                            nodes, edges, node_ids,
                        )
                    except ValueError:
                        pass

        return {"nodes": nodes, "edges": edges}

    def _resolve_dbpedia_name(self, tech_qid: str) -> Optional[str]:
        """Получает DBpedia local name через sitelink из Wikidata."""
        if tech_qid in self._sitelink_cache:
            return self._sitelink_cache[tech_qid]

        sitelink = self.wikidata_client.get_sitelink(tech_qid)
        if sitelink:
            local_name = sitelink.replace(" ", "_")
            self._sitelink_cache[tech_qid] = local_name
            return local_name

        self._sitelink_cache[tech_qid] = None
        return None

    def _add_to_graph(
        self,
        data: List[Dict[str, str]],
        source_id: str,
        tech_qid: str,
        rel_name: str,
        nodes: List[Dict[str, Any]],
        edges: List[Dict[str, Any]],
        node_ids: set,
    ):
        """Добавляет узлы и рёбра из источника в граф."""
        for item in data:
            if item["id"] not in node_ids:
                node_ids.add(item["id"])
                nodes.append(item)

            edges.append(
                {
                    "source": item["id"],
                    "target": tech_qid,
                    "predicate": rel_name,
                    "source_id": source_id,
                }
            )
