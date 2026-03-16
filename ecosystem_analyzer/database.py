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
        total_edges=subgraph.total_relationships
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

        subgraph = self._service.get_subgraph(
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
        nodes = self._service.find_nodes(
            NodeFilter(name_contains=name)
        )
        if not nodes:
            return None
        return nodes[0]

    def save_graph(
            self,
            graph: GraphResponse,
            source: str = "manual"
    ) -> bool:
        """ Сохраняет граф в Neo4j. """
        # Для каждого узла: проверить дубликат по (label, name) → создать или пропустить.
        # Для каждого ребра: создать связь с указанным типом и весом
        # ... вызов service.create_nodes_batch() и service.create_relationships_batch()
        if not self.is_connected():
            raise RuntimeError("Database not connected. Call connect() first.")

        nodes_to_create = []
        for node in graph.nodes:
            node_create = NodeCreate(
                label=node.type,
                name=node.label,
                description="",
                properties={"frontend_id": node.id},
                source=source
            )
            nodes_to_create.append(node_create)

        created_nodes = self._service.create_nodes_batch(nodes_to_create)

        # created_nodes — это список NodeResponse в том же порядке, что и nodes_to_create
        id_map = {}
        for i, node in enumerate(graph.nodes):
            id_map[node.id] = created_nodes[i].uid
        relationships_to_create = []
        for edge in graph.edges:
            rel_create = RelationshipCreate(
                source_uid=id_map[edge.source],
                target_uid=id_map[edge.target],
                rel_type=edge.type,
                weight=edge.weight,
                source=source
            )
            relationships_to_create.append(rel_create)

        self._service.create_relationships_batch(relationships_to_create)

        return True
