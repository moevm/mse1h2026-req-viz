import logging
from typing import List, Optional
from .models import GraphResponse
from graph.service import GraphService
from graph.connection import Neo4jConnection
from graph.models import (NodeCreate, RelationshipCreate, NodeFilter,
                          SubgraphFilter, SubgraphResponse, NodeResponse)
from graph.exceptions import NodeNotFoundError, GraphConnectionError


class Database:
    """ Обёртка над GraphService для управления подключением к Neo4j. """

    def __init__(self, uri: str, user: str, password: str, database: str = "neo4j"):
        """ Сохраняет параметры подключения. Соединение не открывается. """
        self._uri = uri
        self._user = user
        self._password = password
        self._database = database

        self._conn: Optional[Neo4jConnection] = None
        self._service: Optional[GraphService] = None

    def connect(self) -> None:
        """ Открывает соединение с Neo4j и инициализирует схему. """
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

    def get_graph_by_technology(
            self,
            tech_name: str,
            depth: Optional[int],
            limit: Optional[int],
            rel_types: Optional[List[str]] = None
    ) -> GraphResponse | None:
        """ Получает подграф технологии из Neo4j. """

        center_nodes = self._find_nodes(name_contains=tech_name, limit=1)
        if not center_nodes:
            return None
        center_node = center_nodes[0]

        subgraph = self._service.get_subgraph(
            SubgraphFilter(
                center_uid=center_node.uid,
                depth=depth,
                limit=limit,
                rel_filter={"rel_types": rel_types} if rel_types else None
            )
        )

        return self._to_api_format(subgraph)

    def save_graph(
            self,
            graph: GraphResponse,
            source: str = "manual"
    ) -> bool:
        """ Сохраняет граф в Neo4j. """
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
        id_map = {}
        for node in graph.nodes:
            found = self._find_nodes(
                labels=[node.type],
                name_contains=node.label,
                limit=1
            )
            if not found:
                raise RuntimeError(f"Node not found: {node.type} / '{node.label}'")
            id_map[node.id] = found[0].uid


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

        if relationships_to_create:
            self._service.create_relationships_batch(relationships_to_create)

        return True

    def _find_nodes(
            self,
            labels: Optional[List[str]] = None,
            name_contains: Optional[str] = None,
            properties_match: Optional[Dict[str, Any]] = None,
            source: Optional[str] = None,
            created_after: Optional[datetime] = None,
            created_before: Optional[datetime] = None,
            limit: Optional[int] = 1,
            offset: Optional[int] = 0
    ) -> List[NodeResponse]:
        """ Ищет узлы и возвращает список NodeResponse из graph.models. """
        if not self.is_connected():
            raise RuntimeError("Database not connected. Call connect() first.")

        node_filter = NodeFilter(
            labels=labels,
            name_contains=name_contains,
            properties_match=properties_match,
            source=source,
            created_after=created_after,
            created_before=created_before,
            limit=limit,
            offset=offset
        )

        nodes = self._service.find_nodes(node_filter)

        return nodes
    @staticmethod
    def _to_api_format(subgraph: SubgraphResponse) -> GraphResponse:
        """ Преобразует SubgraphResponse (graph.models) → GraphResponse (ecosystem_analyzer.models).
        Результат является унифицированным форматом для взаимодействия всех 4 модулей системы. """
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