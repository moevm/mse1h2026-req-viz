from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class Node(BaseModel):
    id: str
    label: str
    type: str  # Technology, Company, License etc

class Edge(BaseModel):
    source: str
    target: str
    type: str  # ALTERNATIVE_TO, DEVELOPED_BY, LICENSED_UNDER
    weight: float

class Statistics(BaseModel):
    total_nodes: int
    total_edges: int
    max_depth: int

class GraphResponse(BaseModel):
    nodes: List[Node]
    edges: List[Edge]
    statistics: Statistics


