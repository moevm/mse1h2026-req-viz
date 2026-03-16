import logging

from .models import *
from graph.service import GraphService
from graph.connection import Neo4jConnection
from graph.models import (NodeCreate, RelationshipCreate, NodeFilter,
                          SubgraphFilter, SubgraphResponse)
from graph.exceptions import NodeNotFoundError, GraphConnectionError


def _to_graph_response(subgraph: SubgraphResponse) -> GraphResponse:
    nodes = [
        Node(
            id=node.uid,
            label=node.name,
            type=node.label
        )
        for node in subgraph.nodes
    ]

    edges = [
        Edge(
            source=rel.source_uid,
            target=rel.target_uid,
            type=rel.rel_type,
            weight=rel.weight
        )
        for rel in subgraph.relationships
    ]

    statistics = Statistics(
        total_nodes=subgraph.total_nodes,
        total_edges=subgraph.total_relationships,
        max_depth=None
    )

    return GraphResponse(
        nodes=nodes,
        edges=edges,
        statistics=statistics
    )


class Database:
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
        """
        Открывает соединение с Neo4j и инициализирует схему.
        """
        if self._conn is not None:
            return  # Уже подключено

        self._conn = Neo4jConnection(
            uri=self._uri,
            user=self._user,
            password=self._password,
            database=self._database
        )
        self._conn.connect()
        self._service = GraphService(self._conn)
        self._service.init_schema()

    def disconnect(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None
            self._service = None

    def is_connected(self) -> bool:
        return self._conn is not None

    def _to_graph_create(self, graph: GraphResponse) -> tuple[list[NodeCreate], list[RelationshipCreate]]:
        """
        Конвертирует GraphResponse → NodeCreate + RelationshipCreate (для сохранения в Neo4j)
        """
        # Вернёт списки для пакетного создания

    def get_graph_by_technology(
            self,
            tech_name: str,
            depth: int = 2,
            limit: int = 100,
            rel_types: Optional[List[str]] = None
    ) -> GraphResponse | None:
        """ Получает подграф технологии из Neo4j. """

        center_node = self._find_technology_node(tech_name)
        if center_node is None:
            return None

        subgraph = self.service.get_subgraph(
            SubgraphFilter(
                center_uid=center_node.uid,
                depth=depth,
                limit=limit,
                rel_filter={"rel_types": rel_types} if rel_types else None
            )
        )

        return _to_graph_response(subgraph)

    def _find_technology_node(self, name: str) -> Optional[object]:
        """ Ищет узел по имени и возвращает NodeResponse из graph.models. """
        nodes = self.service.find_nodes(
            NodeFilter(name_contains=name)
        )
        if not nodes:
            return None
        return nodes[0]

    def save_graph(
            self,
            tech_name: str,
            graph: GraphResponse
    ) -> bool:
        """ Сохраняет граф в Neo4j. """
        # Для каждого узла: проверить дубликат по (label, name) → создать или пропустить.
        # Для каждого ребра: создать связь с указанным типом и весом
        nodes_create, rels_create = self._to_graph_create(graph)
    # ... вызов service.create_nodes_batch() и service.create_relationships_batch()
        return True


    def get_graph_by_source(self, source: str):
        return self.storage.get(source)

    def save_graph(self, source: str, graph: GraphResponse)-> bool:
        self.storage[source] = graph
        return True
