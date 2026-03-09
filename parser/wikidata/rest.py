import requests
from typing import List, Dict, Any, Optional


class WikidataRestClient:
    """Клиент для выполнения запросов к REST API Wikidata."""

    # ключевые слова, указывающие на программное обеспечение
    SOFTWARE_KEYWORDS = {
        "software", "program", "application", "framework", "library",
        "platform", "tool", "utility", "package", "module", "system",
        "engine", "runtime", "virtualization", "container", "operating system",
        "os", "kernel", "driver", "middleware", "api", "sdk", "ide",
        "compiler", "interpreter", "database", "server", "client"
    }

    def __init__(self, endpoint: str):
        self.base_url = endpoint
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "User-Agent": "parser/1.0"
        })

    def search_technology(self, tech_name: str, language: str = "en") -> Optional[Dict[str, str]]:
        """
        Ищет технологию по названию и возвращает QID и основную информацию.
        Выбирает наиболее релевантный результат, отдавая предпочтение ПО.
        """
        try:
            response = self.session.get(
                f"{self.base_url}/search/items",
                params={"q": tech_name, "language": language, "limit": 5}
            )
            response.raise_for_status()
            data = response.json()
            results = data.get("results", [])
            if not results:
                return None

            # ищем результат, который похож на программное обеспечение
            best = None
            for res in results:
                desc = res.get("description", {}).get("value", "").lower()
                if any(kw in desc for kw in self.SOFTWARE_KEYWORDS):
                    best = res
                    break

            # если не нашли, берём первый
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

    def get_companies_using_technology(self, prop_pid: str, tech_qid: str) -> List[Dict[str, str]]:
        """Находит компании, использующие указанную технологию."""
        companies = []
        try:
            item = self.get_item(tech_qid)
            if "statements" in item and prop_pid in item["statements"]:
                for stmt in item["statements"][prop_pid]:
                    if stmt.get("value", {}).get("type") == "value":
                        company_qid = stmt["value"].get("content")
                        if company_qid:
                            try:
                                company_item = self.get_item(company_qid)
                                company_name = company_item.get("labels", {}).get("en", company_qid)
                                companies.append({
                                    "id": company_qid,
                                    "name": company_name,
                                    "type": "company"
                                })
                            except Exception as e:
                                print(f"Ошибка получения компании {company_qid}: {e}")
                                companies.append({
                                    "id": company_qid,
                                    "name": company_qid,
                                    "type": "company"
                                })
        except Exception as e:
            print(f"Ошибка получения данных для {tech_qid}: {e}")
        return companies

    def get_item(self, item_id: str) -> Dict[str, Any]:
        """Получает полную информацию о сущности по QID."""
        response = self.session.get(f"{self.base_url}/entities/items/{item_id}")
        response.raise_for_status()
        return response.json()
