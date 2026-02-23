import logging
import uuid
from typing import Any

from graph.connection import Neo4jConnection
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

logger = logging.getLogger(__name__)


class GraphRepository:
    def __init__(self, connection: Neo4jConnection) -> None:
        self._conn = connection

    def init_schema(self) -> None:
        constraints = [
            (
                "CREATE CONSTRAINT node_uid_unique IF NOT EXISTS "
                "FOR (n:_Node) REQUIRE n.uid IS UNIQUE"
            ),
        ]
        indexes = [
            "CREATE INDEX node_name_index IF NOT EXISTS FOR (n:_Node) ON (n.name)",
            "CREATE INDEX node_source_index IF NOT EXISTS FOR (n:_Node) ON (n.source)",
        ]
        for query in constraints + indexes:
            self._conn.execute_write(query)
            logger.info("Schema: %s", query)

    def clear_all(self) -> None:
        self._conn.execute_write("MATCH (n) DETACH DELETE n")

    def get_stats(self) -> dict[str, int]:
        node_count_records = self._conn.execute_read(
            "MATCH (n:_Node) RETURN count(n) AS count"
        )
        rel_count_records = self._conn.execute_read(
            "MATCH (:_Node)-[r]-(:_Node) RETURN count(r) AS count"
        )
        label_records = self._conn.execute_read(
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
            "total_nodes": (
                node_count_records[0]["count"] if node_count_records else 0
            ),
            "total_relationships": (
                rel_count_records[0]["count"] if rel_count_records else 0
            ),
            "labels": {r["label"]: r["count"] for r in label_records},
        }

    def create_node(self, data: NodeCreate) -> NodeResponse:
        uid = str(uuid.uuid4())
        now = "datetime()"

        query = f"""
            CREATE (n:_Node:`{data.label}` {{
                uid: $uid,
                name: $name,
                description: $description,
                source: $source,
                created_at: {now},
                updated_at: {now}
            }})
            SET n += $properties
            RETURN n, labels(n) AS labels
        """
        params: dict[str, Any] = {
            "uid": uid,
            "name": data.name,
            "description": data.description,
            "source": data.source,
            "properties": data.properties,
        }

        records = self._conn.execute_write(query, params)
        return self._map_node(records[0])

    def get_node(self, uid: str) -> NodeResponse | None:
        query = """
            MATCH (n:_Node {uid: $uid})
            RETURN n, labels(n) AS labels
        """
        records = self._conn.execute_read(query, {"uid": uid})
        if not records:
            return None
        return self._map_node(records[0])

    def find_nodes(self, node_filter: NodeFilter) -> list[NodeResponse]:
        where_clauses: list[str] = []
        params: dict[str, Any] = {}

        if node_filter.labels:
            label_checks = [f"n:`{label}`" for label in node_filter.labels]
            where_clauses.append(f"({' OR '.join(label_checks)})")

        if node_filter.name_contains:
            where_clauses.append("toLower(n.name) CONTAINS toLower($name_contains)")
            params["name_contains"] = node_filter.name_contains

        if node_filter.properties_match:
            for i, (key, value) in enumerate(node_filter.properties_match.items()):
                param_name = f"prop_{i}"
                where_clauses.append(f"n.`{key}` = ${param_name}")
                params[param_name] = value

        if node_filter.source:
            where_clauses.append("n.source = $source")
            params["source"] = node_filter.source

        if node_filter.created_after:
            where_clauses.append("n.created_at >= datetime($created_after)")
            params["created_after"] = node_filter.created_after.isoformat()

        if node_filter.created_before:
            where_clauses.append("n.created_at <= datetime($created_before)")
            params["created_before"] = node_filter.created_before.isoformat()

        where = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

        query = f"""
            MATCH (n:_Node)
            {where}
            RETURN n, labels(n) AS labels
            ORDER BY n.name
            SKIP $offset
            LIMIT $limit
        """
        params["offset"] = node_filter.offset
        params["limit"] = node_filter.limit

        records = self._conn.execute_read(query, params)
        return [self._map_node(r) for r in records]

    def update_node(self, uid: str, data: NodeUpdate) -> NodeResponse | None:
        set_clauses: list[str] = ["n.updated_at = datetime()"]
        params: dict[str, Any] = {"uid": uid}

        if data.name is not None:
            set_clauses.append("n.name = $name")
            params["name"] = data.name

        if data.description is not None:
            set_clauses.append("n.description = $description")
            params["description"] = data.description

        if data.source is not None:
            set_clauses.append("n.source = $source")
            params["source"] = data.source

        if data.properties is not None:
            set_clauses.append("n += $properties")
            params["properties"] = data.properties

        query = f"""
            MATCH (n:_Node {{uid: $uid}})
            SET {", ".join(set_clauses)}
            RETURN n, labels(n) AS labels
        """

        records = self._conn.execute_write(query, params)
        if not records:
            return None
        return self._map_node(records[0])

    def delete_node(self, uid: str) -> bool:
        query = """
            MATCH (n:_Node {uid: $uid})
            DETACH DELETE n
            RETURN count(n) AS deleted
        """
        records = self._conn.execute_write(query, {"uid": uid})
        return records[0]["deleted"] > 0 if records else False

    def node_exists(self, label: str, name: str) -> bool:
        query = f"""
            MATCH (n:_Node:`{label}` {{name: $name}})
            RETURN count(n) > 0 AS exists
        """
        records = self._conn.execute_read(query, {"name": name})
        return records[0]["exists"] if records else False

    def create_relationship(
        self, data: RelationshipCreate
    ) -> RelationshipResponse | None:
        now = "datetime()"

        query = f"""
            MATCH (source:_Node {{uid: $source_uid}})
            MATCH (target:_Node {{uid: $target_uid}})
            CREATE (source)-[r:`{data.rel_type}` {{
                weight: $weight,
                source: $source,
                created_at: {now},
                updated_at: {now}
            }}]->(target)
            SET r += $properties
            RETURN
                source.uid AS source_uid,
                target.uid AS target_uid,
                type(r) AS rel_type,
                properties(r) AS rel
        """
        params: dict[str, Any] = {
            "source_uid": data.source_uid,
            "target_uid": data.target_uid,
            "weight": data.weight,
            "source": data.source,
            "properties": data.properties,
        }

        records = self._conn.execute_write(query, params)
        if not records:
            return None
        return self._map_relationship(records[0])

    def get_relationships(
        self,
        uid: str,
        rel_filter: RelationshipFilter | None = None,
    ) -> list[RelationshipResponse] | None:
        where_clauses: list[str] = []
        params: dict[str, Any] = {"uid": uid}

        rel_type_match = ""
        if rel_filter and rel_filter.rel_types:
            rel_type_parts = [f":`{rt}`" for rt in rel_filter.rel_types]
            rel_type_match = "|".join(rt.strip(":") for rt in rel_type_parts)
            rel_type_match = f":{rel_type_match}"

        if rel_filter and rel_filter.weight_min is not None:
            where_clauses.append("r.weight >= $weight_min")
            params["weight_min"] = rel_filter.weight_min

        if rel_filter and rel_filter.weight_max is not None:
            where_clauses.append("r.weight <= $weight_max")
            params["weight_max"] = rel_filter.weight_max

        if rel_filter and rel_filter.source:
            where_clauses.append("r.source = $rel_source")
            params["rel_source"] = rel_filter.source

        where = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

        limit = rel_filter.limit if rel_filter else 100
        offset = rel_filter.offset if rel_filter else 0

        query = f"""
                MATCH (source:_Node {{uid: $uid}})-[r{rel_type_match}]-(target:_Node)
                {where}
                RETURN
                    source.uid AS source_uid,
                    target.uid AS target_uid,
                    type(r) AS rel_type,
                    properties(r) AS rel
                ORDER BY r.weight DESC
                SKIP $offset
                LIMIT $limit
            """
        params["offset"] = offset
        params["limit"] = limit

        records = self._conn.execute_read(query, params)
        return [self._map_relationship(r) for r in records]

    def update_relationship(
        self,
        source_uid: str,
        target_uid: str,
        rel_type: str,
        data: RelationshipUpdate,
    ) -> RelationshipResponse | None:
        set_clauses: list[str] = ["r.updated_at = datetime()"]
        params: dict[str, Any] = {
            "source_uid": source_uid,
            "target_uid": target_uid,
        }

        if data.weight is not None:
            set_clauses.append("r.weight = $weight")
            params["weight"] = data.weight

        if data.source is not None:
            set_clauses.append("r.source = $source")
            params["source"] = data.source

        if data.properties is not None:
            set_clauses.append("r += $properties")
            params["properties"] = data.properties

        query = f"""
                MATCH (source:_Node {{uid: $source_uid}})
                      -[r:`{rel_type}`]->
                      (target:_Node {{uid: $target_uid}})
                SET {", ".join(set_clauses)}
                RETURN
                    source.uid AS source_uid,
                    target.uid AS target_uid,
                    type(r) AS rel_type,
                    properties(r) AS rel
            """

        records = self._conn.execute_write(query, params)
        if not records:
            return None
        return self._map_relationship(records[0])

    def delete_relationship(
        self,
        source_uid: str,
        target_uid: str,
        rel_type: str,
    ) -> bool:
        query = f"""
                MATCH (source:_Node {{uid: $source_uid}})
                      -[r:`{rel_type}`]->
                      (target:_Node {{uid: $target_uid}})
                DELETE r
                RETURN count(r) AS deleted
            """
        params = {
            "source_uid": source_uid,
            "target_uid": target_uid,
        }

        records = self._conn.execute_write(query, params)
        return records[0]["deleted"] > 0 if records else False

    def get_subgraph(self, sg_filter: SubgraphFilter) -> SubgraphResponse:
        if sg_filter.center_uid:
            return self._get_neighborhood(sg_filter)
        return self._get_filtered_subgraph(sg_filter)

    def _get_neighborhood(self, sg_filter: SubgraphFilter) -> SubgraphResponse:
        node_where_clauses: list[str] = []
        params: dict[str, Any] = {
            "center_uid": sg_filter.center_uid,
            "limit": sg_filter.limit,
        }

        if sg_filter.node_filter:
            nf = sg_filter.node_filter
            node_conditions = []

            if nf.labels:
                label_conditions = [f"node:`{label}`" for label in nf.labels]
                node_conditions.append(f"({' OR '.join(label_conditions)})")

            if nf.name_contains:
                node_conditions.append(
                    "toLower(node.name) CONTAINS toLower($name_contains)"
                )
                params["name_contains"] = nf.name_contains

            if nf.source:
                node_conditions.append("node.source = $node_source")
                params["node_source"] = nf.source

            if node_conditions:
                node_where_clauses.append(f"({' AND '.join(node_conditions)})")

            if nf.properties_match:
                for i, (key, value) in enumerate(nf.properties_match.items()):
                    param_name = f"prop_{i}"
                    node_conditions.append(f"node.`{key}` = ${param_name}")
                    params[param_name] = value

        rel_type_filter = ""
        rel_where_clauses: list[str] = []

        if sg_filter.rel_filter:
            rf = sg_filter.rel_filter
            if rf.rel_types:
                rel_type_filter = ":" + "|".join(rf.rel_types)
            if rf.weight_min is not None:
                rel_where_clauses.append("rel.weight >= $weight_min")
                params["weight_min"] = rf.weight_min
            if rf.weight_max is not None:
                rel_where_clauses.append("rel.weight <= $weight_max")
                params["weight_max"] = rf.weight_max
            if rf.source:
                rel_where_clauses.append("rel.source = $rel_source")
                params["rel_source"] = rf.source

        path_conditions = []
        if node_where_clauses:
            conditions = " AND ".join(node_where_clauses)
            path_conditions.append(f"ALL(node IN nodes(path)[1..] WHERE {conditions})")
        if rel_where_clauses:
            conditions = " AND ".join(rel_where_clauses)
            path_conditions.append(
                f"ALL(rel IN relationships(path) WHERE {conditions})"
            )

        where = f"WHERE {' AND '.join(path_conditions)}" if path_conditions else ""
        depth = sg_filter.depth

        query = f"""
            MATCH (center:_Node {{uid: $center_uid}})
            MATCH path = (center)-[{rel_type_filter}*1..{depth}]-(m:_Node)
            {where}
            WITH DISTINCT m, path, center
            LIMIT $limit

            WITH collect(DISTINCT center) + collect(DISTINCT m) AS all_nodes,
            collect(path) AS paths

            UNWIND all_nodes AS node
            WITH collect(DISTINCT {{
                uid: node.uid,
                name: node.name,
                description: node.description,
                source: node.source,
                created_at: node.created_at,
                updated_at: node.updated_at,
                labels: [l IN labels(node) WHERE l <> '_Node'],
                props: properties(node)
            }}) AS unique_nodes, paths

            UNWIND paths AS p
            UNWIND relationships(p) AS r
            WITH unique_nodes,
                 collect(DISTINCT {{
                     source_uid: startNode(r).uid,
                     target_uid: endNode(r).uid,
                     rel_type: type(r),
                     rel: properties(r)
                 }}) AS unique_rels
            RETURN unique_nodes, unique_rels
        """

        records = self._conn.execute_read(query, params)
        return self._build_subgraph_response(records)

    def _get_filtered_subgraph(self, sg_filter: SubgraphFilter) -> SubgraphResponse:
        node_where: list[str] = []
        rel_where: list[str] = []
        params: dict[str, Any] = {"limit": sg_filter.limit}

        if sg_filter.node_filter:
            nf = sg_filter.node_filter
            if nf.labels:
                label_checks = [f"n:`{label}`" for label in nf.labels]
                node_where.append(f"({' OR '.join(label_checks)})")
            if nf.name_contains:
                node_where.append("toLower(n.name) CONTAINS toLower($name_contains)")
                params["name_contains"] = nf.name_contains
            if nf.source:
                node_where.append("n.source = $node_source")
                params["node_source"] = nf.source

        rel_type_filter = ""
        if sg_filter.rel_filter:
            rf = sg_filter.rel_filter
            if rf.rel_types:
                rel_type_filter = ":" + "|".join(rf.rel_types)
            if rf.weight_min is not None:
                rel_where.append("r.weight >= $weight_min")
                params["weight_min"] = rf.weight_min
            if rf.weight_max is not None:
                rel_where.append("r.weight <= $weight_max")
                params["weight_max"] = rf.weight_max

        node_where_str = f"WHERE {' AND '.join(node_where)}" if node_where else ""

        optional_match_where_parts = ["m IN filtered_nodes"]
        optional_match_where_parts.extend(rel_where)
        optional_match_where_str = f"WHERE {' AND '.join(optional_match_where_parts)}"

        query = f"""
            MATCH (n:_Node)
            {node_where_str}
            WITH collect(DISTINCT n)[..$limit] AS filtered_nodes

            UNWIND filtered_nodes AS n
            OPTIONAL MATCH (n)-[r{rel_type_filter}]-(m:_Node)
            {optional_match_where_str}
            WITH filtered_nodes,
                 collect(DISTINCT {{
                     source_uid: startNode(r).uid,
                     target_uid: endNode(r).uid,
                     rel_type: type(r),
                     rel: properties(r)
                 }}) AS rels

            UNWIND filtered_nodes AS n
            WITH collect(DISTINCT {{
                uid: n.uid,
                name: n.name,
                description: n.description,
                source: n.source,
                created_at: n.created_at,
                updated_at: n.updated_at,
                labels: [l IN labels(n) WHERE l <> '_Node'],
                props: properties(n)
            }}) AS unique_nodes,
            [r IN rels WHERE r.rel_type IS NOT NULL] AS unique_rels

            RETURN unique_nodes, unique_rels
        """

        records = self._conn.execute_read(query, params)
        return self._build_subgraph_response(records)

    @staticmethod
    def _map_node(record: dict[str, Any]) -> NodeResponse:
        node = record["n"]
        labels = [label for label in record["labels"] if label != "_Node"]
        label = labels[0] if labels else "Unknown"

        system_keys = {
            "uid",
            "name",
            "description",
            "source",
            "created_at",
            "updated_at",
        }
        properties = {k: v for k, v in node.items() if k not in system_keys}

        return NodeResponse(
            uid=node["uid"],
            label=label,
            name=node["name"],
            description=node.get("description"),
            properties=properties,
            source=node.get("source"),
            created_at=node["created_at"].to_native(),
            updated_at=node["updated_at"].to_native(),
        )

    @staticmethod
    def _map_relationship(record: dict[str, Any]) -> RelationshipResponse:
        rel = record["rel"]

        system_keys = {"weight", "source", "created_at", "updated_at"}
        properties = {k: v for k, v in rel.items() if k not in system_keys}

        return RelationshipResponse(
            source_uid=record["source_uid"],
            target_uid=record["target_uid"],
            rel_type=record["rel_type"],
            weight=rel.get("weight", 1.0),
            properties=properties,
            source=rel.get("source"),
            created_at=rel["created_at"].to_native(),
            updated_at=rel["updated_at"].to_native(),
        )

    @staticmethod
    def _build_subgraph_response(records: list[dict[str, Any]]) -> SubgraphResponse:
        if not records:
            return SubgraphResponse()

        record = records[0]
        raw_nodes = record.get("unique_nodes", [])
        raw_rels = record.get("unique_rels", [])

        nodes: list[NodeResponse] = []
        for node_data in raw_nodes:
            if isinstance(node_data, dict):
                node_labels = node_data.get("labels", [])
                clean_labels = [label for label in node_labels if label != "_Node"]
                label = clean_labels[0] if clean_labels else "Unknown"

                props = node_data.get("props", {})
                system_keys = {
                    "uid",
                    "name",
                    "description",
                    "source",
                    "created_at",
                    "updated_at",
                }
                properties = {k: v for k, v in props.items() if k not in system_keys}

                nodes.append(
                    NodeResponse(
                        uid=node_data["uid"],
                        label=label,
                        name=node_data["name"],
                        description=node_data.get("description"),
                        properties=properties,
                        source=node_data.get("source"),
                        created_at=node_data["created_at"].to_native(),
                        updated_at=node_data["updated_at"].to_native(),
                    )
                )

        relationships: list[RelationshipResponse] = []
        for rel_data in raw_rels:
            if isinstance(rel_data, dict) and rel_data.get("rel_type") is not None:
                rel = rel_data.get("rel", {})
                system_keys = {"weight", "source", "created_at", "updated_at"}
                properties = {k: v for k, v in rel.items() if k not in system_keys}

                relationships.append(
                    RelationshipResponse(
                        source_uid=rel_data["source_uid"],
                        target_uid=rel_data["target_uid"],
                        rel_type=rel_data["rel_type"],
                        weight=rel.get("weight", 1.0),
                        properties=properties,
                        source=rel.get("source"),
                        created_at=rel["created_at"].to_native(),
                        updated_at=rel["updated_at"].to_native(),
                    )
                )

        return SubgraphResponse(
            nodes=nodes,
            relationships=relationships,
            total_nodes=len(nodes),
            total_relationships=len(relationships),
        )
