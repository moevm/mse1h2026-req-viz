import requests
from typing import List, Dict, Any, Optional


class WikidataRestClient:
    """Клиент для выполнения запросов к REST API Wikidata."""
 
    def __init__(self, endpoint: str):
        self.base_url = endpoint
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "User-Agent": "parser/1.0"
        })

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
                                print(f"Ошибка при получении компании {company_qid}: {e}")
                                companies.append({
                                    "id": company_qid,
                                    "name": company_qid,
                                    "type": "company"
                                })
        except Exception as e:
            print(f"Ошибка при получении данных для {tech_qid}: {e}")
        
        return companies

    def get_item(self, item_id: str) -> Dict[str, Any]:
        """Получает полную информацию о сущности по QID."""
        response = self.session.get(
            f"{self.base_url}/entities/items/{item_id}"
        )
        response.raise_for_status()
        return response.json()
