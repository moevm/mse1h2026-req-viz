from datetime import datetime
from typing import Dict, Optional
from .models import GraphResponse
import uuid

""" DB stub """
class SimpleDB:
    def __init__(self):
        self.storage = {}  # {source: GraphResponse}

    def get_graph_by_source(self, source: str):
        return self.storage.get(source)

    def save_graph(self, source: str, graph: GraphResponse)-> bool:
        self.storage[source] = graph
        return True

db = SimpleDB()
