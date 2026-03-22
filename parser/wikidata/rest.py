import requests
from typing import List, Dict, Any, Optional


class WikidataRestClient:
    """Клиент для выполнения запросов к REST API Wikidata."""

    def __init__(self, endpoint: str, config: Dict[str, Any]):
        self.base_url = endpoint
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "User-Agent": "parser/1.0"
        })

    def search_technology(self, tech_name: str) -> Optional[Dict[str, str]]:
        """
        Ищет технологию по названию и возвращает QID и основную информацию.
        Выбирает наиболее релевантный результат, отдавая предпочтение ПО.
        """
        try:
            language = self.config.get('search', {}).get('language', 'en')
            response = self.session.get(
                f"{self.base_url}/search/items",
                params={"q": tech_name, "language": language, "limit": 5}
            )
            response.raise_for_status()
            data = response.json()
            results = data.get("results", [])
            if not results:
                return None

            keywords = self.config.get('search', {}).get('keywords', {}).get(language, [])
            best = None
            for res in results:
                desc = res.get("description", {}).get("value", "").lower()
                if any(kw.lower() in desc for kw in keywords):
                    best = res
                    break

            if best is None:
                best = results[0]

            return {
                "id": best["id"],
                "name": best.get("display-label", {}).get("value", tech_name),
                "description": best.get("description", {}).get("value") if best.get("description") else None,
            }
        except Exception as e:
            print(f"Ошибка поиска {tech_name}: {e}")
            return None

    def get_technology_info(self, tech_name: str) -> Optional[Dict[str, Any]]:
        """Получает полную информацию о технологии по её названию."""
        search_result = self.search_technology(tech_name)
        if not search_result:
            return None
        try:
            item = self.get_item(search_result["id"])
            item["_search"] = search_result
            return item
        except Exception as e:
            print(f"Ошибка получения деталей {tech_name}: {e}")
            return None

    def get_related_entities(self, prop_pid: str, tech_qid: str) -> List[Dict[str, str]]:
        """Находит сущности, связанные с технологией через указанное свойство."""
        entities = []
        try:
            item = self.get_item(tech_qid)
            if "statements" in item and prop_pid in item["statements"]:
                for stmt in item["statements"][prop_pid]:
                    if stmt.get("value", {}).get("type") == "value":
                        entity_qid = stmt["value"].get("content")
                        if entity_qid:
                            try:
                                entity_item = self.get_item(entity_qid)
                                entity_name = entity_item.get("labels", {}).get("en", entity_qid)
                                entities.append({
                                    "id": entity_qid,
                                    "name": entity_name,
                                    "type": "entity"
                                })
                            except Exception as e:
                                print(f"Ошибка получения сущности {entity_qid}: {e}")
                                entities.append({
                                    "id": entity_qid,
                                    "name": entity_qid,
                                    "type": "entity"
                                })
        except Exception as e:
            print(f"Ошибка получения данных для {tech_qid}: {e}")
        return entities

    def get_item(self, item_id: str) -> Dict[str, Any]:
        """Получает полную информацию о сущности по QID."""
        response = self.session.get(f"{self.base_url}/entities/items/{item_id}")
        response.raise_for_status()
        return response.json()
