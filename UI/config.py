# config.py
import os
from typing import Dict, List, Tuple

BACKEND_BASE_URL = os.getenv("BACKEND_BASE_URL", "http://localhost:8000")
BACKEND_TIMEOUT = 10 

NODE_COLORS: Dict[str, str] = {
    "Technology": "#4CAF50",  
    "Company": "#2196F3",     
}

EDGE_COLORS: Dict[str, str] = {
    "USED_WITH": "#4CAF50",      
    "ALTERNATIVE_TO": "#F44336", 
    "DEPENDS_ON": "#9C27B0",    
    "DEVELOPED_BY": "#2196F3",   
}

EDGE_TYPES: List[str] = [
    "USED_WITH",
    "ALTERNATIVE_TO", 
    "DEPENDS_ON",
    "DEVELOPED_BY"
]

EDGE_TYPE_NAMES: Dict[str, str] = {
    "USED_WITH": "Используется с",
    "ALTERNATIVE_TO": "Альтернатива для",
    "DEPENDS_ON": "Зависит от",
    "DEVELOPED_BY": "Разработано компанией"
}

NODE_TYPE_FILTERS: List[Tuple[str, str]] = [
    ("Technology", "🟢 Технологии"),
    ("Company", "🔵 Компании"),
]

DASHED_EDGE_TYPES: List[str] = ["ALTERNATIVE_TO", "LICENSED_UNDER"]


NODE_TYPE_TRANSLATIONS: Dict[str, str] = {
    "Technology": "Технология",
    "Company": "Компания",
}

EDGE_TYPE_TRANSLATIONS: Dict[str, str] = {
    "USED_WITH": "Используется вместе",
    "ALTERNATIVE_TO": "Альтернатива",
    "DEPENDS_ON": "Зависит от",
    "DEVELOPED_BY": "Разработано компанией",
}

WEIGHTED_EDGE_TYPES: List[str] = [
    "USED_WITH",
    "DEPENDS_ON"
]

BINARY_EDGE_TYPES: List[str] = [
    "ALTERNATIVE_TO",
    "DEVELOPED_BY"
]