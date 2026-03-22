from datetime import datetime
from unittest.mock import Mock

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
)
from graph.repository import GraphRepository


class TestGraphRepositoryInit:
    def test_init(self):
        mock_connection = Mock(spec=Neo4jConnection)

        repo = GraphRepository(mock_connection)

        assert repo._conn == mock_connection


class TestGraphRepositoryInitSchema:
    def test_init_schema(self):
        mock_connection = Mock(spec=Neo4jConnection)
        mock_connection.execute_write = Mock()

        repo = GraphRepository(mock_connection)
        repo.init_schema()

        expected_queries = [
            "CREATE CONSTRAINT node_uid_unique IF NOT EXISTS "
            "FOR (n:_Node) REQUIRE n.uid IS UNIQUE",
            "CREATE INDEX node_name_index IF NOT EXISTS FOR (n:_Node) ON (n.name)",
            "CREATE INDEX node_source_index IF NOT EXISTS FOR (n:_Node) ON (n.source)",
        ]

        assert mock_connection.execute_write.call_count == 3
        for _i, query in enumerate(expected_queries):
            mock_connection.execute_write.assert_any_call(query)


class TestGraphRepositoryClearAll:
    def test_clear_all(self):
        mock_connection = Mock(spec=Neo4jConnection)
        mock_connection.execute_write = Mock()

        repo = GraphRepository(mock_connection)
        repo.clear_all()

        mock_connection.execute_write.assert_called_once_with(
            "MATCH (n) DETACH DELETE n"
        )


class TestGraphRepositoryGetStats:
    def test_get_stats_success(self):
        mock_connection = Mock(spec=Neo4jConnection)

        mock_connection.execute_read.side_effect = [
            [{"count": 10}],
            [{"count": 5}],
            [{"label": "Person", "count": 7}, {"label": "Organization", "count": 3}],
        ]

        repo = GraphRepository(mock_connection)
        stats = repo.get_stats()

        expected_stats = {
            "total_nodes": 10,
            "total_relationships": 5,
            "labels": {"Person": 7, "Organization": 3},
        }

        assert stats == expected_stats
        assert mock_connection.execute_read.call_count == 3


class TestGraphRepositoryCreateNode:
    def test_create_node_success(self):
        mock_connection = Mock(spec=Neo4jConnection)

        mock_record = {
            "n": {
                "uid": "test-uid",
                "name": "Test Node",
                "description": "A test node",
                "source": "test-source",
                "created_at": Mock(to_native=Mock(return_value=datetime.now())),
                "updated_at": Mock(to_native=Mock(return_value=datetime.now())),
                "custom_prop": "value",
            },
            "labels": ["_Node", "TestLabel"],
        }
        mock_connection.execute_write.return_value = [mock_record]

        repo = GraphRepository(mock_connection)

        node_create = NodeCreate(
            label="TestLabel",
            name="Test Node",
            description="A test node",
            source="test-source",
            properties={"custom_prop": "value"},
        )

        result = repo.create_node(node_create)

        mock_connection.execute_write.assert_called_once()
        call_args = mock_connection.execute_write.call_args
        query, params = call_args[0]

        assert "CREATE (n:_Node:`TestLabel`" in query
        assert params["name"] == "Test Node"
        assert params["description"] == "A test node"
        assert params["source"] == "test-source"
        assert params["properties"] == {"custom_prop": "value"}

        assert isinstance(result, NodeResponse)
        assert result.uid == "test-uid"
        assert result.label == "TestLabel"
        assert result.name == "Test Node"
        assert result.description == "A test node"
        assert result.source == "test-source"
        assert result.properties == {"custom_prop": "value"}


class TestGraphRepositoryGetNode:
    def test_get_node_success(self):
        mock_connection = Mock(spec=Neo4jConnection)

        mock_record = {
            "n": {
                "uid": "test-uid",
                "name": "Test Node",
                "description": "A test node",
                "source": "test-source",
                "created_at": Mock(to_native=Mock(return_value=datetime.now())),
                "updated_at": Mock(to_native=Mock(return_value=datetime.now())),
            },
            "labels": ["_Node", "TestLabel"],
        }
        mock_connection.execute_read.return_value = [mock_record]

        repo = GraphRepository(mock_connection)
        result = repo.get_node("test-uid")

        assert isinstance(result, NodeResponse)
        assert result.uid == "test-uid"
        assert result.label == "TestLabel"
        assert result.name == "Test Node"

    def test_get_node_not_found(self):
        mock_connection = Mock(spec=Neo4jConnection)
        mock_connection.execute_read.return_value = []

        repo = GraphRepository(mock_connection)
        result = repo.get_node("non-existent-uid")

        assert result is None
        mock_connection.execute_read.assert_called_once()


class TestGraphRepositoryFindNodes:
    def test_find_nodes_with_no_filters(self):
        mock_connection = Mock(spec=Neo4jConnection)

        mock_records = [
            {
                "n": {
                    "uid": "test-uid-1",
                    "name": "Test Node 1",
                    "description": "First test node",
                    "source": "test-source",
                    "created_at": Mock(to_native=Mock(return_value=datetime.now())),
                    "updated_at": Mock(to_native=Mock(return_value=datetime.now())),
                },
                "labels": ["_Node", "TestLabel"],
            },
            {
                "n": {
                    "uid": "test-uid-2",
                    "name": "Test Node 2",
                    "description": "Second test node",
                    "source": "test-source",
                    "created_at": Mock(to_native=Mock(return_value=datetime.now())),
                    "updated_at": Mock(to_native=Mock(return_value=datetime.now())),
                },
                "labels": ["_Node", "TestLabel"],
            },
        ]
        mock_connection.execute_read.return_value = mock_records

        repo = GraphRepository(mock_connection)

        node_filter = NodeFilter()
        result = repo.find_nodes(node_filter)

        mock_connection.execute_read.assert_called_once()
        call_args = mock_connection.execute_read.call_args
        query, params = call_args[0]

        assert "MATCH (n:_Node)" in query
        assert "ORDER BY n.name" in query
        assert params["offset"] == 0
        assert params["limit"] == 100

        assert len(result) == 2
        assert all(isinstance(node, NodeResponse) for node in result)
        assert result[0].uid == "test-uid-1"
        assert result[1].uid == "test-uid-2"

    def test_find_nodes_with_label_filter(self):
        mock_connection = Mock(spec=Neo4jConnection)
        mock_connection.execute_read.return_value = []

        repo = GraphRepository(mock_connection)

        node_filter = NodeFilter(labels=["Person", "Employee"])
        result = repo.find_nodes(node_filter)

        mock_connection.execute_read.assert_called_once()
        call_args = mock_connection.execute_read.call_args
        query, params = call_args[0]

        assert "(n:`Person` OR n:`Employee`)" in query
        assert params["offset"] == 0
        assert params["limit"] == 100

        assert result == []

    def test_find_nodes_with_name_filter(self):
        mock_connection = Mock(spec=Neo4jConnection)
        mock_connection.execute_read.return_value = []

        repo = GraphRepository(mock_connection)

        node_filter = NodeFilter(name_contains="test")
        result = repo.find_nodes(node_filter)

        mock_connection.execute_read.assert_called_once()
        call_args = mock_connection.execute_read.call_args
        query, params = call_args[0]

        assert "toLower(n.name) CONTAINS toLower($name_contains)" in query
        assert params["name_contains"] == "test"
        assert params["offset"] == 0
        assert params["limit"] == 100

        assert result == []

    def test_find_nodes_with_properties_filter(self):
        mock_connection = Mock(spec=Neo4jConnection)
        mock_connection.execute_read.return_value = []

        repo = GraphRepository(mock_connection)

        node_filter = NodeFilter(
            properties_match={"status": "active", "type": "premium"}
        )
        result = repo.find_nodes(node_filter)

        mock_connection.execute_read.assert_called_once()
        call_args = mock_connection.execute_read.call_args
        query, params = call_args[0]

        assert "n.`status` = $prop_0" in query
        assert "n.`type` = $prop_1" in query
        assert params["prop_0"] == "active"
        assert params["prop_1"] == "premium"
        assert params["offset"] == 0
        assert params["limit"] == 100

        assert result == []

    def test_find_nodes_with_source_filter(self):
        mock_connection = Mock(spec=Neo4jConnection)
        mock_connection.execute_read.return_value = []

        repo = GraphRepository(mock_connection)

        node_filter = NodeFilter(source="wikidata")
        result = repo.find_nodes(node_filter)

        mock_connection.execute_read.assert_called_once()
        call_args = mock_connection.execute_read.call_args
        query, params = call_args[0]

        assert "n.source = $source" in query
        assert params["source"] == "wikidata"
        assert params["offset"] == 0
        assert params["limit"] == 100

        assert result == []

    def test_find_nodes_with_date_filters(self):
        from datetime import datetime

        mock_connection = Mock(spec=Neo4jConnection)
        mock_connection.execute_read.return_value = []

        repo = GraphRepository(mock_connection)

        created_after = datetime.now()
        created_before = datetime.now()
        node_filter = NodeFilter(
            created_after=created_after, created_before=created_before
        )
        result = repo.find_nodes(node_filter)

        mock_connection.execute_read.assert_called_once()
        call_args = mock_connection.execute_read.call_args
        query, params = call_args[0]

        assert "n.created_at >= datetime($created_after)" in query
        assert "n.created_at <= datetime($created_before)" in query
        assert params["created_after"] == created_after.isoformat()
        assert params["created_before"] == created_before.isoformat()
        assert params["offset"] == 0
        assert params["limit"] == 100

        assert result == []

    def test_find_nodes_with_pagination(self):
        mock_connection = Mock(spec=Neo4jConnection)
        mock_connection.execute_read.return_value = []

        repo = GraphRepository(mock_connection)

        node_filter = NodeFilter(offset=50, limit=25)
        result = repo.find_nodes(node_filter)

        mock_connection.execute_read.assert_called_once()
        call_args = mock_connection.execute_read.call_args
        _query, params = call_args[0]

        assert params["offset"] == 50
        assert params["limit"] == 25

        assert result == []


class TestGraphRepositoryUpdateNode:
    def test_update_node_success(self):
        mock_connection = Mock(spec=Neo4jConnection)

        mock_record = {
            "n": {
                "uid": "test-uid",
                "name": "Updated Node",
                "description": "An updated node",
                "source": "updated-source",
                "created_at": Mock(to_native=Mock(return_value=datetime.now())),
                "updated_at": Mock(to_native=Mock(return_value=datetime.now())),
            },
            "labels": ["_Node", "TestLabel"],
        }
        mock_connection.execute_write.return_value = [mock_record]

        repo = GraphRepository(mock_connection)

        node_update = NodeUpdate(
            name="Updated Node",
            description="An updated node",
            source="updated-source",
            properties={"updated_prop": "value"},
        )

        result = repo.update_node("test-uid", node_update)

        mock_connection.execute_write.assert_called_once()
        call_args = mock_connection.execute_write.call_args
        query, params = call_args[0]

        assert "MATCH (n:_Node {uid: $uid})" in query
        assert "n.name = $name" in query
        assert "n.description = $description" in query
        assert "n.source = $source" in query
        assert "n += $properties" in query
        assert "n.updated_at = datetime()" in query

        assert params["uid"] == "test-uid"
        assert params["name"] == "Updated Node"
        assert params["description"] == "An updated node"
        assert params["source"] == "updated-source"
        assert params["properties"] == {"updated_prop": "value"}

        assert isinstance(result, NodeResponse)
        assert result.uid == "test-uid"
        assert result.name == "Updated Node"

    def test_update_node_not_found(self):
        mock_connection = Mock(spec=Neo4jConnection)
        mock_connection.execute_write.return_value = []

        repo = GraphRepository(mock_connection)

        node_update = NodeUpdate(name="Updated Node")

        result = repo.update_node("non-existent-uid", node_update)

        assert result is None
        mock_connection.execute_write.assert_called_once()


class TestGraphRepositoryDeleteNode:
    def test_delete_node_success(self):
        mock_connection = Mock(spec=Neo4jConnection)
        mock_connection.execute_write.return_value = [{"deleted": 1}]

        repo = GraphRepository(mock_connection)
        result = repo.delete_node("test-uid")

        mock_connection.execute_write.assert_called_once()
        call_args = mock_connection.execute_write.call_args
        query, params = call_args[0]

        assert "MATCH (n:_Node {uid: $uid})" in query
        assert "DETACH DELETE n" in query
        assert "RETURN count(n) AS deleted" in query
        assert params["uid"] == "test-uid"

        assert result is True

    def test_delete_node_not_found(self):
        mock_connection = Mock(spec=Neo4jConnection)
        mock_connection.execute_write.return_value = [{"deleted": 0}]

        repo = GraphRepository(mock_connection)
        result = repo.delete_node("non-existent-uid")

        assert result is False
        mock_connection.execute_write.assert_called_once()


class TestGraphRepositoryNodeExists:
    def test_node_exists_true(self):
        mock_connection = Mock(spec=Neo4jConnection)
        mock_connection.execute_read.return_value = [{"exists": True}]

        repo = GraphRepository(mock_connection)
        result = repo.node_exists("Technology", "Existent")

        mock_connection.execute_read.assert_called_once()
        call_args = mock_connection.execute_read.call_args
        query, params = call_args[0]

        assert "MATCH (n:_Node:`Technology` {name: $name})" in query
        assert "RETURN count(n) > 0 AS exists" in query
        assert params["name"] == "Existent"

        assert result is True

    def test_node_exists_false(self):
        mock_connection = Mock(spec=Neo4jConnection)
        mock_connection.execute_read.return_value = [{"exists": False}]

        repo = GraphRepository(mock_connection)
        result = repo.node_exists("Technology", "Non Existent")

        assert result is False
        mock_connection.execute_read.assert_called_once()


class TestGraphRepositoryCreateRelationship:
    def test_create_relationship_success(self):
        mock_connection = Mock(spec=Neo4jConnection)

        mock_record = {
            "source_uid": "source-uid",
            "target_uid": "target-uid",
            "rel_type": "CONNECTED_TO",
            "rel": {
                "weight": 0.8,
                "source": "test-source",
                "created_at": Mock(to_native=Mock(return_value=datetime.now())),
                "updated_at": Mock(to_native=Mock(return_value=datetime.now())),
                "custom_prop": "value",
            },
        }
        mock_connection.execute_write.return_value = [mock_record]

        repo = GraphRepository(mock_connection)

        rel_create = RelationshipCreate(
            source_uid="source-uid",
            target_uid="target-uid",
            rel_type="CONNECTED_TO",
            weight=0.8,
            source="test-source",
            properties={"custom_prop": "value"},
        )

        result = repo.create_relationship(rel_create)

        mock_connection.execute_write.assert_called_once()
        call_args = mock_connection.execute_write.call_args
        query, params = call_args[0]

        assert "CREATE (source)-[r:`CONNECTED_TO`" in query
        assert params["source_uid"] == "source-uid"
        assert params["target_uid"] == "target-uid"
        assert params["weight"] == 0.8
        assert params["source"] == "test-source"
        assert params["properties"] == {"custom_prop": "value"}

        assert isinstance(result, RelationshipResponse)
        assert result.source_uid == "source-uid"
        assert result.target_uid == "target-uid"
        assert result.rel_type == "CONNECTED_TO"
        assert result.weight == 0.8
        assert result.source == "test-source"
        assert result.properties == {"custom_prop": "value"}

    def test_create_relationship_not_found(self):
        mock_connection = Mock(spec=Neo4jConnection)
        mock_connection.execute_write.return_value = []

        repo = GraphRepository(mock_connection)

        rel_create = RelationshipCreate(
            source_uid="source-uid",
            target_uid="target-uid",
            rel_type="CONNECTED_TO",
            weight=0.8,
        )

        result = repo.create_relationship(rel_create)

        assert result is None
        mock_connection.execute_write.assert_called_once()


class TestGraphRepositoryGetRelationships:
    def test_get_relationships_success(self):
        mock_connection = Mock(spec=Neo4jConnection)

        mock_records = [
            {
                "source_uid": "source-uid",
                "target_uid": "target-uid",
                "rel_type": "CONNECTED_TO",
                "rel": {
                    "weight": 0.8,
                    "source": "test-source",
                    "created_at": Mock(to_native=Mock(return_value=datetime.now())),
                    "updated_at": Mock(to_native=Mock(return_value=datetime.now())),
                },
            }
        ]
        mock_connection.execute_read.return_value = mock_records

        repo = GraphRepository(mock_connection)
        result = repo.get_relationships("source-uid")

        mock_connection.execute_read.assert_called_once()
        call_args = mock_connection.execute_read.call_args
        query, params = call_args[0]

        assert "MATCH (source:_Node {uid: $uid})-[r]-(target:_Node)" in query
        assert "ORDER BY r.weight DESC" in query
        assert params["uid"] == "source-uid"
        assert params["offset"] == 0
        assert params["limit"] == 100

        assert len(result) == 1
        assert isinstance(result[0], RelationshipResponse)
        assert result[0].source_uid == "source-uid"
        assert result[0].target_uid == "target-uid"
        assert result[0].rel_type == "CONNECTED_TO"

    def test_get_relationships_with_filter(self):
        mock_connection = Mock(spec=Neo4jConnection)
        mock_connection.execute_read.return_value = []

        repo = GraphRepository(mock_connection)

        rel_filter = RelationshipFilter(
            rel_types=["CONNECTED_TO", "RELATED_TO"],
            weight_min=0.5,
            weight_max=1.0,
            source="test-source",
            offset=10,
            limit=5,
        )

        result = repo.get_relationships("source-uid", rel_filter)

        mock_connection.execute_read.assert_called_once()
        call_args = mock_connection.execute_read.call_args
        query, params = call_args[0]

        assert ":`CONNECTED_TO`|`RELATED_TO`" in query
        assert "r.weight >= $weight_min" in query
        assert "r.weight <= $weight_max" in query
        assert "r.source = $rel_source" in query
        assert params["weight_min"] == 0.5
        assert params["weight_max"] == 1.0
        assert params["rel_source"] == "test-source"
        assert params["offset"] == 10
        assert params["limit"] == 5

        assert result == []

    def test_get_relationships_no_result(self):
        mock_connection = Mock(spec=Neo4jConnection)
        mock_connection.execute_read.return_value = []

        repo = GraphRepository(mock_connection)
        result = repo.get_relationships("source-uid")

        assert result == []
        mock_connection.execute_read.assert_called_once()


class TestGraphRepositoryUpdateRelationship:
    def test_update_relationship_success(self):
        mock_connection = Mock(spec=Neo4jConnection)

        mock_record = {
            "source_uid": "source-uid",
            "target_uid": "target-uid",
            "rel_type": "CONNECTED_TO",
            "rel": {
                "weight": 0.9,
                "source": "updated-source",
                "created_at": Mock(to_native=Mock(return_value=datetime.now())),
                "updated_at": Mock(to_native=Mock(return_value=datetime.now())),
            },
        }
        mock_connection.execute_write.return_value = [mock_record]

        repo = GraphRepository(mock_connection)

        rel_update = RelationshipUpdate(
            weight=0.9, source="updated-source", properties={"updated_prop": "value"}
        )

        result = repo.update_relationship(
            "source-uid", "target-uid", "CONNECTED_TO", rel_update
        )

        mock_connection.execute_write.assert_called_once()
        call_args = mock_connection.execute_write.call_args
        query, params = call_args[0]

        assert "MATCH (source:_Node {uid: $source_uid})" in query
        assert "[r:`CONNECTED_TO`]" in query
        assert "(target:_Node {uid: $target_uid})" in query
        assert "r.weight = $weight" in query
        assert "r.source = $source" in query
        assert "r += $properties" in query
        assert "r.updated_at = datetime()" in query

        assert params["source_uid"] == "source-uid"
        assert params["target_uid"] == "target-uid"
        assert params["weight"] == 0.9
        assert params["source"] == "updated-source"
        assert params["properties"] == {"updated_prop": "value"}

        assert isinstance(result, RelationshipResponse)
        assert result.source_uid == "source-uid"
        assert result.target_uid == "target-uid"
        assert result.rel_type == "CONNECTED_TO"
        assert result.weight == 0.9

    def test_update_relationship_not_found(self):
        mock_connection = Mock(spec=Neo4jConnection)
        mock_connection.execute_write.return_value = []

        repo = GraphRepository(mock_connection)

        rel_update = RelationshipUpdate(weight=0.9)

        result = repo.update_relationship(
            "source-uid", "target-uid", "CONNECTED_TO", rel_update
        )

        assert result is None
        mock_connection.execute_write.assert_called_once()


class TestGraphRepositoryDeleteRelationship:
    def test_delete_relationship_success(self):
        mock_connection = Mock(spec=Neo4jConnection)
        mock_connection.execute_write.return_value = [{"deleted": 1}]

        repo = GraphRepository(mock_connection)
        result = repo.delete_relationship("source-uid", "target-uid", "CONNECTED_TO")

        mock_connection.execute_write.assert_called_once()
        call_args = mock_connection.execute_write.call_args
        query, params = call_args[0]

        assert "MATCH (source:_Node {uid: $source_uid})" in query
        assert "[r:`CONNECTED_TO`]" in query
        assert "(target:_Node {uid: $target_uid})" in query
        assert "DELETE r" in query
        assert "RETURN count(r) AS deleted" in query

        assert params["source_uid"] == "source-uid"
        assert params["target_uid"] == "target-uid"
        assert result is True

    def test_delete_relationship_not_found(self):
        mock_connection = Mock(spec=Neo4jConnection)
        mock_connection.execute_write.return_value = [{"deleted": 0}]

        repo = GraphRepository(mock_connection)
        result = repo.delete_relationship("source-uid", "target-uid", "CONNECTED_TO")

        assert result is False
        mock_connection.execute_write.assert_called_once()
