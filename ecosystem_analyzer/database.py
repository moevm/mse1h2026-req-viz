import logging

from .models import GraphResponse
from graph.service import GraphService
from graph.connection import Neo4jConnection
from graph.models import NodeCreate, RelationshipCreate, NodeFilter, SubgraphFilter
from graph.exceptions import NodeNotFoundError, GraphConnectionError

class DataBase:
    """
    Обёртка над GraphService для управления подключением к Neo4j.
    """

    def __init__(self, uri: str, user: str, password: str, database: str = "neo4j"):
        """ Сохраняет параметры подключения. Соединение не открывается. """
        conn = Neo4jConnection(uri, user, password, database)
        self.service = GraphService(conn)
        self.service.init_schema()

        self._uri = uri
        self._user = user
        self._password = password
        self._database = database

        self._conn: Optional[Neo4jConnection] = None
        self._service: Optional[GraphService] = None

    def connect(self) -> None:
        pass

    def disconnect(self) -> None:
        pass

    def get_graph_by_technology(
            self,
            tech_name: str,
            depth: int = 2,
            allowed_rel_types: list[str] | None = None
    ) -> GraphResponse | None:
        # will eject with GraphService.get_subgraph() and covert it to format for front
        pass

    def save_graph(
            self,
            tech_name: str,
            graph: GraphResponse
    ) -> bool:
        # Для каждого узла: проверить дубликат по (label, name) → создать или пропустить.
        # Для каждого ребра: создать связь с указанным типом и весом
        pass


    def get_graph_by_source(self, source: str):
        return self.storage.get(source)

    def save_graph(self, source: str, graph: GraphResponse)-> bool:
        self.storage[source] = graph
        return True
