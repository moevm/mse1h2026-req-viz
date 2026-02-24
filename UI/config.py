# config.py
from typing import Dict, List, Tuple

# Цвета узлов по типу
NODE_COLORS: Dict[str, str] = {
    "Technology": "#4CAF50",  
    "Company": "#2196F3",     
}

# Цвета связей по типу
EDGE_COLORS: Dict[str, str] = {
    "USED_WITH": "#4CAF50",      
    "ALTERNATIVE_TO": "#F44336", 
    "DEPENDS_ON": "#9C27B0",    
    "DEVELOPED_BY": "#2196F3",   
}

# Типы связей для фильтров
EDGE_TYPES: List[str] = [
    "USED_WITH",
    "ALTERNATIVE_TO", 
    "DEPENDS_ON",
    "DEVELOPED_BY"
]

# Человеко-читаемые названия связей
EDGE_TYPE_NAMES: Dict[str, str] = {
    "USED_WITH": "Используется с",
    "ALTERNATIVE_TO": "Альтернатива для",
    "DEPENDS_ON": "Зависит от",
    "DEVELOPED_BY": "Разработано компанией"
}

# Типы узлов для чекбоксов фильтрации
NODE_TYPE_FILTERS: List[Tuple[str, str]] = [
    ("Technology", "🟢 Технологии"),
    ("Company", "🔵 Компании"),
]

# Связи, которые отображаются пунктиром
DASHED_EDGE_TYPES: List[str] = ["ALTERNATIVE_TO", "LICENSED_UNDER"]