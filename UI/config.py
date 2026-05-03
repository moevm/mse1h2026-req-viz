import os
from typing import Dict, List, Tuple


BACKEND_BASE_URL = os.getenv("BACKEND_BASE_URL", "http://localhost:8000")
BACKEND_TIMEOUT = int(os.getenv("BACKEND_TIMEOUT", "120"))


EDGE_TYPES: List[str] = [
    "USES",
    "USED_BY",
    "DEPENDS_ON_SOFTWARE",
    "BASED_ON",
    "INSPIRED_BY",
    "CREATOR",
    "DEVELOPER",
    "PROGRAMMED_IN",
    "OWNED_BY",
]


NODE_COLORS: Dict[str, str] = {
    "Technology": "#3572CE",
    "Company": "#318B1E",
    "Entity": "#3572CE",
    "License": "#FF9800",
    "Person": "#9C27B0",
    "Organization": "#607D8B",
}

EDGE_COLORS: Dict[str, str] = {
    "USES": "#1A581C",
    "USED_BY": "#8DFC0F",
    "DEPENDS_ON_SOFTWARE": "#9C27B0",
    "BASED_ON": "#3F51B5",
    "INSPIRED_BY": "#E91E63",
    "CREATOR": "#2196F3",
    "DEVELOPER": "#00BCD4",
    "PROGRAMMED_IN": "#FF5722",
    "OWNED_BY": "#795548",
}

EDGE_TYPE_NAMES: Dict[str, str] = {
    "USES": "Использует",
    "USED_BY": "Находится в пользовании у",
    "DEPENDS_ON_SOFTWARE": "Зависит от ПО",
    "BASED_ON": "Создано на основе",
    "INSPIRED_BY": "Вдохновлено",
    "CREATOR": "Создатель",
    "DEVELOPER": "Разработчик",
    "PROGRAMMED_IN": "Написано на",
    "OWNED_BY": "Принадлежит"
}

NODE_TYPE_NAMES: Dict[str, str] = {
    "Technology": "Технология",
    "Company": "Компания",
    "Entity": "Сущность",
    "License": "Лицензия",
    "Person": "Человек",
    "Organization": "Организация"
}

NODE_TYPE_FILTERS: List[Tuple[str, str]] = [
    ("Technology", "🟢 Технология"),
    ("Company", "🔵 Компания"),
    ("License", "🟠 Лицензия"),
    ("Person", "🟣 Человек"),
    ("Organization", "⚫ Организация"),
    ("Entity", "🟢 Сущность"),
]


NODE_TYPE_TRANSLATIONS: Dict[str, str] = {
    "Technology": "Технология",
    "Company": "Компания",
    "Entity": "Сущность",
    "License": "Лицензия",
    "Person": "Человек",
    "Organization": "Организация",
    "Unknown": "Неизвестно"
}

EDGE_TYPE_TRANSLATIONS: Dict[str, str] = {
    "USES": "Использует",
    "USED_BY": "Находится в пользовании у",
    "DEPENDS_ON_SOFTWARE": "Зависит от программного обеспечения",
    "BASED_ON": "Создано на основе",
    "INSPIRED_BY": "Вдохновлено",
    "CREATOR": "Создатель",
    "DEVELOPER": "Разработчик",
    "PROGRAMMED_IN": "Написано на языке программирования",
    "OWNED_BY": "Принадлежит"
}

WEIGHTED_EDGE_TYPES: List[str] = [
    "USES",
    "USED_BY",
    "DEPENDS_ON_SOFTWARE"
]

BINARY_EDGE_TYPES: List[str] = [
    "CREATOR",
    "DEVELOPER",
    "OWNED_BY",
    "PROGRAMMED_IN",
    "BASED_ON",
    "INSPIRED_BY"
]

DASHED_EDGE_TYPES: List[str] = [
    "INSPIRED_BY",
    "BASED_ON"
]


MAX_DEPTH: int = int(os.getenv("MAX_DEPTH", "3"))
MAX_NODES: int = int(os.getenv("MAX_NODES", "100"))
DEFAULT_EDGE_WEIGHT: float = 0.7


NODE_SIZES: Dict[str, int] = {
    "Technology": 30,
    "Company": 25,
    "Entity": 22,
    "License": 20,
    "Person": 22,
    "Organization": 24,
}

NODE_FONT_COLORS: Dict[str, str] = {
    "Technology": "#FFFFFF",
    "Company": "#FFFFFF",
    "Entity": "#000000",
    "License": "#000000",
    "Person": "#FFFFFF",
    "Organization": "#FFFFFF",
}

SEARCH_FIELDS: List[str] = ["name", "label", "description"]
MIN_SEARCH_LENGTH: int = 2
EXPORT_FORMATS: List[str] = ["pdf", "json", "csv"]
DEFAULT_EXPORT_FORMAT: str = "pdf"
REPORT_FOOTER: str = "Ecosystem Graph Viz • mse1h2026-req-viz"