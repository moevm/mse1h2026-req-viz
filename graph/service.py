import logging

from graph.connection import Neo4jConnection
from graph.exceptions import (
    DuplicateNodeError,
    NodeNotFoundError,
    RelationshipNotFoundError,
)
from graph.models import (
    NodeCreate,
    NodeFilter,
    NodeResponse,
    NodeUpdate,
    RelationshipCreate,
    RelationshipFilter,
    RelationshipResponse,
    RelationshipUpdate,
    SubgraphFilter,
    SubgraphResponse,
)
from graph.repository import GraphRepository

logger = logging.getLogger(__name__)


class GraphService:
    def __init__(self, connection: Neo4jConnection) -> None:
        self._repo = GraphRepository(connection)

    def init_schema(self) -> None:
        self._repo.init_schema()
        logger.info("Schema initialized.")

    def create_node(self, data: NodeCreate) -> NodeResponse:
        if self._repo.node_exists(data.label, data.name):
            msg = (
                f"Node with label '{data.label}' and name '{data.name}' already exists"
            )
            raise DuplicateNodeError(msg)

        node = self._repo.create_node(data)
        logger.info(
            "Created node: uid=%s, label=%s, name=%s", node.uid, node.label, node.name
        )
        return node

    def get_node(self, uid: str) -> NodeResponse:
        node = self._repo.get_node(uid)
        if node is None:
            msg = f"Node with uid '{uid}' not found"
            raise NodeNotFoundError(msg)
        return node

    def find_nodes(self, node_filter: NodeFilter | None = None) -> list[NodeResponse]:
        if node_filter is None:
            node_filter = NodeFilter()
        return self._repo.find_nodes(node_filter)

    def update_node(self, uid: str, data: NodeUpdate) -> NodeResponse:
        node = self._repo.update_node(uid, data)
        if node is None:
            msg = f"Node with uid '{uid}' not found"
            raise NodeNotFoundError(msg)
        logger.info("Updated node: uid=%s", uid)
        return node

    def delete_node(self, uid: str) -> bool:
        deleted = self._repo.delete_node(uid)
        if not deleted:
            msg = f"Node with uid '{uid}' not found"
            raise NodeNotFoundError(msg)
        logger.info("Deleted node: uid=%s (with all relationships)", uid)
        return True

    def create_relationship(self, data: RelationshipCreate) -> RelationshipResponse:
        source_node = self._repo.get_node(data.source_uid)
        if source_node is None:
            msg = f"Source node with uid '{data.source_uid}' not found"
            raise NodeNotFoundError(msg)

        target_node = self._repo.get_node(data.target_uid)
        if target_node is None:
            msg = f"Target node with uid '{data.target_uid}' not found"
            raise NodeNotFoundError(msg)

        rel = self._repo.create_relationship(data)
        if rel is None:
            msg = (
                f"Failed to create relationship {data.rel_type} "
                f"between '{data.source_uid}' and '{data.target_uid}'"
            )
            raise NodeNotFoundError(msg)

        logger.info(
            "Created relationship: %s -[%s]-> %s",
            data.source_uid,
            data.rel_type,
            data.target_uid,
        )
        return rel

    def get_relationships(
        self,
        uid: str,
        rel_filter: RelationshipFilter | None = None,
    ) -> list[RelationshipResponse]:
        node = self._repo.get_node(uid)
        if node is None:
            msg = f"Node with uid '{uid}' not found"
            raise NodeNotFoundError(msg)

        return self._repo.get_relationships(uid, rel_filter)

    def update_relationship(
        self,
        source_uid: str,
        target_uid: str,
        rel_type: str,
        data: RelationshipUpdate,
    ) -> RelationshipResponse:
        rel = self._repo.update_relationship(source_uid, target_uid, rel_type, data)
        if rel is None:
            msg = (
                f"Relationship {rel_type} from '{source_uid}' "
                f"to '{target_uid}' not found"
            )
            raise RelationshipNotFoundError(msg)

        logger.info(
            "Updated relationship: %s -[%s]-> %s",
            source_uid,
            rel_type,
            target_uid,
        )
        return rel

    def delete_relationship(
        self,
        source_uid: str,
        target_uid: str,
        rel_type: str,
    ) -> bool:
        deleted = self._repo.delete_relationship(source_uid, target_uid, rel_type)
        if not deleted:
            msg = (
                f"Relationship {rel_type} from '{source_uid}' "
                f"to '{target_uid}' not found"
            )
            raise RelationshipNotFoundError(msg)

        logger.info(
            "Deleted relationship: %s -[%s]-> %s",
            source_uid,
            rel_type,
            target_uid,
        )
        return True

    def get_subgraph(self, sg_filter: SubgraphFilter | None = None) -> SubgraphResponse:
        if sg_filter is None:
            sg_filter = SubgraphFilter()

        if sg_filter.center_uid:
            center = self._repo.get_node(sg_filter.center_uid)
            if center is None:
                msg = f"Center node with uid '{sg_filter.center_uid}' not found"
                raise NodeNotFoundError(msg)

        subgraph = self._repo.get_subgraph(sg_filter)
        logger.info(
            "Extracted subgraph: %d nodes, %d relationships",
            subgraph.total_nodes,
            subgraph.total_relationships,
        )
        return subgraph

    def create_nodes_batch(self, nodes: list[NodeCreate]) -> list[NodeResponse]:
        created: list[NodeResponse] = []
        for node_data in nodes:
            try:
                node = self.create_node(node_data)
                created.append(node)
            except DuplicateNodeError:
                logger.warning(
                    "Skipping duplicate node: label=%s, name=%s",
                    node_data.label,
                    node_data.name,
                )
        logger.info("Batch created %d/%d nodes", len(created), len(nodes))
        return created

    def create_relationships_batch(
        self,
        relationships: list[RelationshipCreate],
    ) -> list[RelationshipResponse]:
        created: list[RelationshipResponse] = []
        for rel_data in relationships:
            try:
                rel = self.create_relationship(rel_data)
                created.append(rel)
            except (NodeNotFoundError, RelationshipNotFoundError) as exc:
                logger.warning(
                    "Skipping relationship %s -> %s [%s]: %s",
                    rel_data.source_uid,
                    rel_data.target_uid,
                    rel_data.rel_type,
                    exc,
                )
        logger.info(
            "Batch created %d/%d relationships",
            len(created),
            len(relationships),
        )
        return created

    def clear_all(self) -> None:
        self._repo._conn.execute_write("MATCH (n) DETACH DELETE n")
        logger.warning("Cleared all data from the database.")

    def get_stats(self) -> dict[str, int]:
        node_count_records = self._repo._conn.execute_read(
            "MATCH (n:_Node) RETURN count(n) AS count"
        )
        rel_count_records = self._repo._conn.execute_read(
            "MATCH (:_Node)-[r]-(:_Node) RETURN count(r) AS count"
        )
        label_records = self._repo._conn.execute_read(
            """
            MATCH (n:_Node)
            WITH labels(n) AS node_labels
            UNWIND node_labels AS label
            WITH label WHERE label <> '_Node'
            RETURN label, count(*) AS count
            ORDER BY count DESC
            """
        )

        return {
            "total_nodes": node_count_records[0]["count"] if node_count_records else 0,
            "total_relationships": rel_count_records[0]["count"]
            if rel_count_records
            else 0,
            "labels": {r["label"]: r["count"] for r in label_records},
        }
