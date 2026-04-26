import requests
from typing import List, Dict, Any


class DBpediaSPARQLClient:
    """Клиент для выполнения SPARQL-запросов к DBpedia."""

    def __init__(self, endpoint: str, resource_base: str):
        """Инициализирует клиент с адресом SPARQL-эндпоинта и базовым URL ресурсов."""
        self.endpoint = endpoint
        self.resource_base = resource_base
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Accept": "application/sparql-results+json",
                "User-Agent": "parser/1.0",
            }
        )

    def get_related_entities_forward(
        self, dbo_property: str, local_name: str
    ) -> List[Dict[str, str]]:
        """Возвращает сущности, на которые ссылается данный ресурс через указанное свойство."""
        resource_uri = f"{self.resource_base}/{local_name}"
        query = f"""
        SELECT DISTINCT ?item ?itemLabel WHERE {{
          <{resource_uri}> {dbo_property} ?item .
          ?item rdfs:label ?itemLabel .
          FILTER (lang(?itemLabel) = 'en')
          FILTER (isIRI(?item))
        }}
        LIMIT 50
        """
        return self._parse_entity_results(query)

    def get_related_entities_reverse(
        self, dbo_property: str, local_name: str
    ) -> List[Dict[str, str]]:
        """Возвращает сущности, которые ссылаются на данный ресурс через указанное свойство."""
        resource_uri = f"{self.resource_base}/{local_name}"
        query = f"""
        SELECT DISTINCT ?item ?itemLabel WHERE {{
          ?item {dbo_property} <{resource_uri}> .
          ?item rdfs:label ?itemLabel .
          FILTER (lang(?itemLabel) = 'en')
          FILTER (isIRI(?item))
        }}
        LIMIT 50
        """
        return self._parse_entity_results(query)

    def _parse_entity_results(self, query: str) -> List[Dict[str, str]]:
        """Выполняет запрос и преобразует результаты в список сущностей"""
        results = self._execute_query(query)
        entities = []
        seen = set()
        for result in results:
            uri = result.get("item", "")
            if not uri or "/resource/" not in uri:
                continue
            local_name = uri.rsplit("/", 1)[-1]
            if local_name.startswith("Category:") or local_name.startswith("List_of"):
                continue
            entity_id = f"dbpedia:{local_name}"
            if entity_id in seen:
                continue
            seen.add(entity_id)
            entities.append(
                {
                    "id": entity_id,
                    "name": result.get("itemLabel", local_name.replace("_", " ")),
                    "type": "entity",
                }
            )
        return entities

    def _execute_query(self, query: str) -> List[Dict[str, Any]]:
        """Выполняет SPARQL-запрос и возвращает список словарей с результатами."""
        try:
            response = self.session.get(
                self.endpoint,
                params={"query": query, "format": "json"},
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
            bindings = data.get("results", {}).get("bindings", [])
            results = []
            for binding in bindings:
                result = {}
                for key, value in binding.items():
                    result[key] = value["value"]
                results.append(result)
            return results
        except requests.exceptions.RequestException as e:
            print(f"Ошибка при выполнении DBpedia SPARQL-запроса: {e}")
            return []
