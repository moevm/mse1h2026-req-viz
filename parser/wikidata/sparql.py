import requests
from typing import List, Dict, Any


class WikidataSPARQLClient:
    """Клиент для выполнения SPARQL-запросов к Wikidata."""

    def __init__(self, endpoint: str):
        self.endpoint = endpoint
        self.session = requests.Session()
        self.session.headers.update(
            {"Accept": "application/json", "User-Agent": "parser/1.0"}
        )

    def get_related_entities(
        self, prop_pid: str, tech_qid: str
    ) -> List[Dict[str, str]]:
        """Универсальный метод для получения сущностей через прямое свойство."""
        query = f"""
        SELECT DISTINCT ?item ?itemLabel WHERE {{
          SERVICE wikibase:label {{ bd:serviceParam wikibase:language "[AUTO_LANGUAGE],mul,en". }}
          wd:{tech_qid} wdt:{prop_pid} ?item.
        }}
        """
        results = self._execute_query(query, labels=True)
        entities = []
        for result in results:
            entities.append(
                {
                    "id": result["item"]["value"].split("/")[-1],
                    "name": result.get("itemLabel", {}).get("value", "Unknown"),
                    "type": "entity",
                }
            )
        return entities

    def get_using_technology(self, tech_qid: str) -> List[Dict[str, str]]:
        """Находит сущности, которые используют данную технологию (обратное отношение uses)."""
        query = f"""
        SELECT DISTINCT ?item ?itemLabel WHERE {{
          SERVICE wikibase:label {{ bd:serviceParam wikibase:language "[AUTO_LANGUAGE],mul,en". }}
          ?item wdt:P2283 wd:{tech_qid}.
        }}
        """
        results = self._execute_query(query, labels=True)
        entities = []
        for result in results:
            entities.append(
                {
                    "id": result["item"]["value"].split("/")[-1],
                    "name": result.get("itemLabel", {}).get("value", "Unknown"),
                    "type": "entity",
                }
            )
        return entities

    def _execute_query(self, query: str, labels: bool = False) -> List[Dict[str, Any]]:
        """Выполняет SPARQL-запрос и возвращает результат."""
        try:
            response = self.session.get(
                self.endpoint, params={"query": query, "format": "json"}, timeout=30
            )
            response.raise_for_status()
            data = response.json()
            bindings = data.get("results", {}).get("bindings", [])
            if labels:
                return bindings
            results = []
            for binding in bindings:
                result = {}
                for key, value in binding.items():
                    result[key] = value["value"]
                results.append(result)
            return results
        except requests.exceptions.RequestException as e:
            print(f"Ошибка при выполнении SPARQL-запроса: {e}")
            return []
