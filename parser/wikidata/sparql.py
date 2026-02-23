import requests
from typing import List, Dict, Any, Optional


class WikidataSPARQLClient:
    """Клиент для выполнения SPARQL-запросов к Wikidata."""
    
    WIKIDATA_SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "User-Agent": "parser/1.0"
        })


    def get_companies_using_technology(self, prod_pid: str, tech_qid: str) -> List[Dict[str, str]]:
        """Находит компании, использующие указанную технологию."""
        query = f"""
        SELECT DISTINCT ?item ?itemLabel WHERE {{
          SERVICE wikibase:label {{ bd:serviceParam wikibase:language "[AUTO_LANGUAGE],mul,en". }}
          {{
            SELECT DISTINCT ?item WHERE {{
              ?item p:{prod_pid} ?statement.
              ?statement ps:P2283 wd:{tech_qid}.
            }}
          }}
        }}
        """
        
        results = self._execute_query(query, labels=True)
        
        companies = []
        for result in results:
            companies.append({
                "id": result["item"]["value"].split("/")[-1],
                "name": result.get("itemLabel", {}).get("value", "Unknown"),
                "type": "company"
            })
 
        return companies

    def _execute_query(self, query: str, labels: bool = False) -> List[Dict[str, Any]]:
        """Выполняет SPARQL-запрос и возвращает результат."""
        try:
            response = self.session.get(
                self.WIKIDATA_SPARQL_ENDPOINT,
                params={"query": query, "format": "json"},
                timeout=30
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
