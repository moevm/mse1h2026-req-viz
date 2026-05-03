import requests
from typing import List, Dict, Any, Optional
import time


class WikidataRestClient:
    """Клиент для выполнения запросов к REST API Wikidata с кэшированием и retry."""

    def __init__(self, endpoint: str, config: Dict[str, Any]):
        self.base_url = endpoint
        self.config = config
        self.session = requests.Session()
        self.session.headers.update(
            {"Accept": "application/json", "User-Agent": "parser/1.0"}
        )

        self._item_cache: Dict[str, Dict[str, Any]] = {}
        self._search_cache: Dict[str, Optional[Dict[str, str]]] = {}
        self._sitelink_cache: Dict[str, Optional[str]] = {}

    def _request(self, method: str, url: str, max_retries: int = 3, **kwargs) -> requests.Response:
        """
        Выполняет HTTP-запрос с задержкой и повторными попытками.
        При ошибке 429 ждёт экспоненциально дольше.
        """
        for attempt in range(max_retries):
            time.sleep(0.1 * (attempt + 1))
            try:
                response = self.session.request(method, url, **kwargs)
                if response.status_code == 429:
                    wait = 2 ** attempt
                    print(f"429 Too Many Requests, waiting {wait}s and retrying...")
                    time.sleep(wait)
                    continue
                response.raise_for_status()
                return response
            except requests.exceptions.RequestException as e:
                if attempt == max_retries - 1:
                    raise
                print(f"Request failed (attempt {attempt+1}/{max_retries}): {e}")
        raise Exception("Max retries exceeded")

    def search_technology(self, tech_name: str) -> Optional[Dict[str, str]]:
        language = self.config.get("search", {}).get("language", "en")
        cache_key = f"{tech_name}_{language}"
        if cache_key in self._search_cache:
            return self._search_cache[cache_key]

        try:
            response = self._request(
                "GET",
                f"{self.base_url}/search/items",
                params={"q": tech_name, "language": language, "limit": 5},
            )
            data = response.json()
            results = data.get("results", [])
            if not results:
                self._search_cache[cache_key] = None
                return None

            keywords = (
                self.config.get("search", {}).get("keywords", {}).get(language, [])
            )
            best = None
            for res in results:
                desc = res.get("description", {}).get("value", "").lower()
                if any(kw.lower() in desc for kw in keywords):
                    best = res
                    break

            if best is None:
                best = results[0]

            result = {
                "id": best["id"],
                "name": best.get("display-label", {}).get("value", tech_name),
                "description": best.get("description", {}).get("value")
                if best.get("description")
                else None,
            }
            self._search_cache[cache_key] = result
            return result
        except Exception as e:
            print(f"Ошибка поиска {tech_name}: {e}")
            self._search_cache[cache_key] = None
            return None

    def get_technology_info(self, tech_name: str) -> Optional[Dict[str, Any]]:
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

    def get_sitelink(self, item_id: str) -> Optional[str]:
        if item_id in self._sitelink_cache:
            return self._sitelink_cache[item_id]

        try:
            response = self._request(
                "GET", f"{self.base_url}/entities/items/{item_id}/sitelinks"
            )
            sitelinks = response.json()
            enwiki = sitelinks.get("enwiki", {})
            title = enwiki.get("title")
            self._sitelink_cache[item_id] = title
            return title
        except Exception as e:
            print(f"Ошибка получения sitelink для {item_id}: {e}")
            self._sitelink_cache[item_id] = None
            return None

    def get_related_entities(
        self, prop_pid: str, item: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        entities = []
        try:
            if "statements" in item and prop_pid in item["statements"]:
                for stmt in item["statements"][prop_pid]:
                    if stmt.get("value", {}).get("type") == "value":
                        entity_qid = stmt["value"].get("content")
                        if entity_qid:
                            try:
                                entity_item = self.get_item(entity_qid)
                                labels = entity_item.get("labels", {})
                                entity_name = labels.get("en") or next(iter(labels.values())) if labels else entity_qid # разные языки
                                entities.append(
                                    {
                                        "id": entity_qid,
                                        "name": entity_name,
                                        "type": "entity",
                                    }
                                )
                            except Exception as e:
                                print(f"Ошибка получения сущности {entity_qid}: {e}")
        except Exception as e:
            print(f"Ошибка получения данных для {item.get('id', 'unknown')}: {e}")
        return entities

    def get_item(self, item_id: str) -> Dict[str, Any]:
        if item_id in self._item_cache:
            return self._item_cache[item_id]

        response = self._request("GET", f"{self.base_url}/entities/items/{item_id}")
        data = response.json()
        self._item_cache[item_id] = data
        return data
