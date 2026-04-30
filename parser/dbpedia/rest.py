import requests
from typing import Optional


class DBpediaRestClient:
    """Клиент для разрешения URI ресурсов DBpedia."""

    def __init__(self, resource_base: str) -> None:
        """Инициализирует клиент с базовым URL ресурсов DBpedia."""
        self.resource_base = resource_base
        self.session = requests.Session()
        self.session.headers.update(
            {"Accept": "application/ld+json", "User-Agent": "parser/1.0"}
        )

    def resolve_resource_uri(self, tech_name: str) -> Optional[str]:
        """Возвращает URI ресурса DBpedia по названию сущности или None, если не найден."""
        normalized = tech_name.strip().replace(" ", "_")
        url = f"{self.resource_base}/{normalized}"
        try:
            response = self.session.head(url, allow_redirects=True, timeout=15)
            if response.status_code in (200, 303):
                return f"{self.resource_base}/{normalized}"
        except requests.exceptions.RequestException:
            pass
        return None
