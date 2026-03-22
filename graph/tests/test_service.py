import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

from graph.service import GraphService
from graph.connection import Neo4jConnection
from graph.repository import GraphRepository
from graph.models import (
    NodeCreate, NodeFilter, NodeResponse, NodeUpdate,
    RelationshipCreate, RelationshipFilter, RelationshipResponse, RelationshipUpdate,
    SubgraphFilter, SubgraphResponse,
)
from graph.exceptions import (
    DuplicateNodeError,
    NodeNotFoundError,
    RelationshipNotFoundError,
    GraphConnectionError,
)


class TestGraphServiceInit:
    def test_init(self):
        mock_connection = Mock(spec=Neo4jConnection)

        service = GraphService(mock_connection)

        assert isinstance(service._repo, GraphRepository)


class TestGraphServiceInitSchema:
    def test_init_schema_success(self):
        mock_connection = Mock(spec=Neo4jConnection)
        mock_repo = Mock(spec=GraphRepository)
        mock_repo.init_schema = Mock()

        service = GraphService(mock_connection)
        service._repo = mock_repo

        service.init_schema()

        mock_repo.init_schema.assert_called_once()


class TestGraphServiceCreateNode:
    def test_create_node_success(self):
        mock_connection = Mock(spec=Neo4jConnection)
        mock_repo = Mock(spec=GraphRepository)
        mock_repo.node_exists = Mock(return_value=False)

        expected_node = NodeResponse(
            uid="test-uid",
            label="TestLabel",
            name="Test Node",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        mock_repo.create_node = Mock(return_value=expected_node)

        service = GraphService(mock_connection)
        service._repo = mock_repo

        node_create = NodeCreate(
            label="TestLabel",
            name="Test Node"
        )

        result = service.create_node(node_create)

        mock_repo.node_exists.assert_called_once_with("TestLabel", "Test Node")
        mock_repo.create_node.assert_called_once_with(node_create)
        assert result == expected_node

    def test_create_node_duplicate(self):
        mock_connection = Mock(spec=Neo4jConnection)
        mock_repo = Mock(spec=GraphRepository)
        mock_repo.node_exists = Mock(return_value=True)

        service = GraphService(mock_connection)
        service._repo = mock_repo

        node_create = NodeCreate(
            label="TestLabel",
            name="Test Node"
        )

        with pytest.raises(DuplicateNodeError) as exc_info:
            service.create_node(node_create)

        mock_repo.node_exists.assert_called_once_with("TestLabel", "Test Node")
        mock_repo.create_node.assert_not_called()
        assert "Node with label 'TestLabel' and name 'Test Node' already exists" in str(exc_info.value)


class TestGraphServiceGetNode:
    def test_get_node_success(self):
        mock_connection = Mock(spec=Neo4jConnection)
        mock_repo = Mock(spec=GraphRepository)

        expected_node = NodeResponse(
            uid="test-uid",
            label="TestLabel",
            name="Test Node",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        mock_repo.get_node = Mock(return_value=expected_node)

        service = GraphService(mock_connection)
        service._repo = mock_repo

        result = service.get_node("test-uid")

        mock_repo.get_node.assert_called_once_with("test-uid")
        assert result == expected_node

    def test_get_node_not_found(self):
        mock_connection = Mock(spec=Neo4jConnection)
        mock_repo = Mock(spec=GraphRepository)
        mock_repo.get_node = Mock(return_value=None)

        service = GraphService(mock_connection)
        service._repo = mock_repo

        with pytest.raises(NodeNotFoundError) as exc_info:
            service.get_node("non-existent-uid")

        mock_repo.get_node.assert_called_once_with("non-existent-uid")
        assert "Node with uid 'non-existent-uid' not found" in str(exc_info.value)


class TestGraphServiceFindNodes:
    def test_find_nodes_with_filter(self):
        mock_connection = Mock(spec=Neo4jConnection)
        mock_repo = Mock(spec=GraphRepository)

        expected_nodes = [
            NodeResponse(
                uid="test-uid-1",
                label="TestLabel",
                name="Test Node 1",
                created_at=datetime.now(),
                updated_at=datetime.now()
            ),
            NodeResponse(
                uid="test-uid-2",
                label="TestLabel",
                name="Test Node 2",
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
        ]
        mock_repo.find_nodes = Mock(return_value=expected_nodes)

        service = GraphService(mock_connection)
        service._repo = mock_repo

        node_filter = NodeFilter(labels=["TestLabel"])

        result = service.find_nodes(node_filter)

        mock_repo.find_nodes.assert_called_once_with(node_filter)
        assert result == expected_nodes

    def test_find_nodes_without_filter(self):
        mock_connection = Mock(spec=Neo4jConnection)
        mock_repo = Mock(spec=GraphRepository)

        expected_nodes = [
            NodeResponse(
                uid="test-uid-1",
                label="TestLabel",
                name="Test Node 1",
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
        ]
        mock_repo.find_nodes = Mock(return_value=expected_nodes)

        service = GraphService(mock_connection)
        service._repo = mock_repo

        result = service.find_nodes(None)

        mock_repo.find_nodes.assert_called_once()
        args, _ = mock_repo.find_nodes.call_args
        assert isinstance(args[0], NodeFilter)
        assert result == expected_nodes


class TestGraphServiceUpdateNode:
    def test_update_node_success(self):
        mock_connection = Mock(spec=Neo4jConnection)
        mock_repo = Mock(spec=GraphRepository)

        expected_node = NodeResponse(
            uid="test-uid",
            label="TestLabel",
            name="Updated Test Node",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        mock_repo.update_node = Mock(return_value=expected_node)

        service = GraphService(mock_connection)
        service._repo = mock_repo

        node_update = NodeUpdate(name="Updated Test Node")

        result = service.update_node("test-uid", node_update)

        mock_repo.update_node.assert_called_once_with("test-uid", node_update)
        assert result == expected_node

    def test_update_node_not_found(self):
        mock_connection = Mock(spec=Neo4jConnection)
        mock_repo = Mock(spec=GraphRepository)
        mock_repo.update_node = Mock(return_value=None)

        service = GraphService(mock_connection)
        service._repo = mock_repo

        node_update = NodeUpdate(name="Updated Test Node")

        with pytest.raises(NodeNotFoundError) as exc_info:
            service.update_node("non-existent-uid", node_update)

        mock_repo.update_node.assert_called_once_with("non-existent-uid", node_update)
        assert "Node with uid 'non-existent-uid' not found" in str(exc_info.value)


class TestGraphServiceDeleteNode:
    def test_delete_node_success(self):
        mock_connection = Mock(spec=Neo4jConnection)
        mock_repo = Mock(spec=GraphRepository)
        mock_repo.delete_node = Mock(return_value=True)

        service = GraphService(mock_connection)
        service._repo = mock_repo

        result = service.delete_node("test-uid")

        mock_repo.delete_node.assert_called_once_with("test-uid")
        assert result is True

    def test_delete_node_not_found(self):
        mock_connection = Mock(spec=Neo4jConnection)
        mock_repo = Mock(spec=GraphRepository)
        mock_repo.delete_node = Mock(return_value=False)

        service = GraphService(mock_connection)
        service._repo = mock_repo

        with pytest.raises(NodeNotFoundError) as exc_info:
            service.delete_node("non-existent-uid")

        mock_repo.delete_node.assert_called_once_with("non-existent-uid")
        assert "Node with uid 'non-existent-uid' not found" in str(exc_info.value)


class TestGraphServiceCreateRelationship:
    def test_create_relationship_success(self):
        mock_connection = Mock(spec=Neo4jConnection)
        mock_repo = Mock(spec=GraphRepository)

        source_node = NodeResponse(
            uid="source-uid",
            label="SourceLabel",
            name="Source Node",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        target_node = NodeResponse(
            uid="target-uid",
            label="TargetLabel",
            name="Target Node",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        mock_repo.get_node.side_effect = [source_node, target_node]

        expected_rel = RelationshipResponse(
            source_uid="source-uid",
            target_uid="target-uid",
            rel_type="TEST_RELATIONSHIP",
            weight=1.0,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        mock_repo.create_relationship = Mock(return_value=expected_rel)

        service = GraphService(mock_connection)
        service._repo = mock_repo

        rel_create = RelationshipCreate(
            source_uid="source-uid",
            target_uid="target-uid",
            rel_type="TEST_RELATIONSHIP"
        )

        result = service.create_relationship(rel_create)

        assert mock_repo.get_node.call_count == 2
        mock_repo.get_node.assert_any_call("source-uid")
        mock_repo.get_node.assert_any_call("target-uid")
        mock_repo.create_relationship.assert_called_once_with(rel_create)
        assert result == expected_rel

    def test_create_relationship_source_not_found(self):
        mock_connection = Mock(spec=Neo4jConnection)
        mock_repo = Mock(spec=GraphRepository)
        mock_repo.get_node = Mock(return_value=None)

        service = GraphService(mock_connection)
        service._repo = mock_repo

        rel_create = RelationshipCreate(
            source_uid="non-existent-source-uid",
            target_uid="target-uid",
            rel_type="TEST_RELATIONSHIP"
        )

        with pytest.raises(NodeNotFoundError) as exc_info:
            service.create_relationship(rel_create)

        mock_repo.get_node.assert_called_once_with("non-existent-source-uid")
        mock_repo.create_relationship.assert_not_called()
        assert "Source node with uid 'non-existent-source-uid' not found" in str(exc_info.value)

    def test_create_relationship_target_not_found(self):
        mock_connection = Mock(spec=Neo4jConnection)
        mock_repo = Mock(spec=GraphRepository)

        source_node = NodeResponse(
            uid="source-uid",
            label="SourceLabel",
            name="Source Node",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        mock_repo.get_node.side_effect = [source_node, None]

        service = GraphService(mock_connection)
        service._repo = mock_repo

        rel_create = RelationshipCreate(
            source_uid="source-uid",
            target_uid="non-existent-target-uid",
            rel_type="TEST_RELATIONSHIP"
        )

        with pytest.raises(NodeNotFoundError) as exc_info:
            service.create_relationship(rel_create)

        assert mock_repo.get_node.call_count == 2
        mock_repo.get_node.assert_any_call("source-uid")
        mock_repo.get_node.assert_any_call("non-existent-target-uid")
        mock_repo.create_relationship.assert_not_called()
        assert "Target node with uid 'non-existent-target-uid' not found" in str(exc_info.value)

    def test_create_relationship_creation_failed(self):
        mock_connection = Mock(spec=Neo4jConnection)
        mock_repo = Mock(spec=GraphRepository)

        source_node = NodeResponse(
            uid="source-uid",
            label="SourceLabel",
            name="Source Node",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        target_node = NodeResponse(
            uid="target-uid",
            label="TargetLabel",
            name="Target Node",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        mock_repo.get_node.side_effect = [source_node, target_node]

        mock_repo.create_relationship = Mock(return_value=None)

        service = GraphService(mock_connection)
        service._repo = mock_repo

        rel_create = RelationshipCreate(
            source_uid="source-uid",
            target_uid="target-uid",
            rel_type="TEST_RELATIONSHIP"
        )

        with pytest.raises(NodeNotFoundError) as exc_info:
            service.create_relationship(rel_create)

        assert mock_repo.get_node.call_count == 2
        mock_repo.get_node.assert_any_call("source-uid")
        mock_repo.get_node.assert_any_call("target-uid")
        mock_repo.create_relationship.assert_called_once_with(rel_create)
        assert "Failed to create relationship TEST_RELATIONSHIP between 'source-uid' and 'target-uid'" in str(exc_info.value)


class TestGraphServiceGetRelationships:
    def test_get_relationships_success(self):
        mock_connection = Mock(spec=Neo4jConnection)
        mock_repo = Mock(spec=GraphRepository)

        node = NodeResponse(
            uid="test-uid",
            label="TestLabel",
            name="Test Node",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        mock_repo.get_node = Mock(return_value=node)

        expected_rels = [
            RelationshipResponse(
                source_uid="test-uid",
                target_uid="target-uid-1",
                rel_type="TEST_RELATIONSHIP_1",
                weight=1.0,
                created_at=datetime.now(),
                updated_at=datetime.now()
            ),
            RelationshipResponse(
                source_uid="test-uid",
                target_uid="target-uid-2",
                rel_type="TEST_RELATIONSHIP_2",
                weight=0.5,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
        ]
        mock_repo.get_relationships = Mock(return_value=expected_rels)

        service = GraphService(mock_connection)
        service._repo = mock_repo

        result = service.get_relationships("test-uid")

        mock_repo.get_node.assert_called_once_with("test-uid")
        mock_repo.get_relationships.assert_called_once_with("test-uid", None)
        assert result == expected_rels

    def test_get_relationships_with_filter(self):
        mock_connection = Mock(spec=Neo4jConnection)
        mock_repo = Mock(spec=GraphRepository)

        node = NodeResponse(
            uid="test-uid",
            label="TestLabel",
            name="Test Node",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        mock_repo.get_node = Mock(return_value=node)

        expected_rels = [
            RelationshipResponse(
                source_uid="test-uid",
                target_uid="target-uid-1",
                rel_type="TEST_RELATIONSHIP_1",
                weight=1.0,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
        ]
        mock_repo.get_relationships = Mock(return_value=expected_rels)

        service = GraphService(mock_connection)
        service._repo = mock_repo

        rel_filter = RelationshipFilter(rel_types=["TEST_RELATIONSHIP_1"])

        result = service.get_relationships("test-uid", rel_filter)

        mock_repo.get_node.assert_called_once_with("test-uid")
        mock_repo.get_relationships.assert_called_once_with("test-uid", rel_filter)
        assert result == expected_rels

    def test_get_relationships_node_not_found(self):
        mock_connection = Mock(spec=Neo4jConnection)
        mock_repo = Mock(spec=GraphRepository)
        mock_repo.get_node = Mock(return_value=None)

        service = GraphService(mock_connection)
        service._repo = mock_repo

        with pytest.raises(NodeNotFoundError) as exc_info:
            service.get_relationships("non-existent-uid")

        mock_repo.get_node.assert_called_once_with("non-existent-uid")
        mock_repo.get_relationships.assert_not_called()
        assert "Node with uid 'non-existent-uid' not found" in str(exc_info.value)


class TestGraphServiceUpdateRelationship:
    def test_update_relationship_success(self):
        mock_connection = Mock(spec=Neo4jConnection)
        mock_repo = Mock(spec=GraphRepository)

        expected_rel = RelationshipResponse(
            source_uid="source-uid",
            target_uid="target-uid",
            rel_type="TEST_RELATIONSHIP",
            weight=2.0,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        mock_repo.update_relationship = Mock(return_value=expected_rel)

        service = GraphService(mock_connection)
        service._repo = mock_repo

        rel_update = RelationshipUpdate(weight=2.0)

        result = service.update_relationship("source-uid", "target-uid", "TEST_RELATIONSHIP", rel_update)

        mock_repo.update_relationship.assert_called_once_with("source-uid", "target-uid", "TEST_RELATIONSHIP", rel_update)
        assert result == expected_rel

    def test_update_relationship_not_found(self):
        mock_connection = Mock(spec=Neo4jConnection)
        mock_repo = Mock(spec=GraphRepository)
        mock_repo.update_relationship = Mock(return_value=None)

        service = GraphService(mock_connection)
        service._repo = mock_repo

        rel_update = RelationshipUpdate(weight=2.0)

        with pytest.raises(RelationshipNotFoundError) as exc_info:
            service.update_relationship("source-uid", "target-uid", "NON_EXISTENT_RELATIONSHIP", rel_update)

        mock_repo.update_relationship.assert_called_once_with("source-uid", "target-uid", "NON_EXISTENT_RELATIONSHIP", rel_update)
        assert "Relationship NON_EXISTENT_RELATIONSHIP from 'source-uid' to 'target-uid' not found" in str(exc_info.value)


class TestGraphServiceDeleteRelationship:
    def test_delete_relationship_success(self):
        mock_connection = Mock(spec=Neo4jConnection)
        mock_repo = Mock(spec=GraphRepository)
        mock_repo.delete_relationship = Mock(return_value=True)

        service = GraphService(mock_connection)
        service._repo = mock_repo

        result = service.delete_relationship("source-uid", "target-uid", "TEST_RELATIONSHIP")

        mock_repo.delete_relationship.assert_called_once_with("source-uid", "target-uid", "TEST_RELATIONSHIP")
        assert result is True

    def test_delete_relationship_not_found(self):
        mock_connection = Mock(spec=Neo4jConnection)
        mock_repo = Mock(spec=GraphRepository)
        mock_repo.delete_relationship = Mock(return_value=False)

        service = GraphService(mock_connection)
        service._repo = mock_repo

        with pytest.raises(RelationshipNotFoundError) as exc_info:
            service.delete_relationship("source-uid", "target-uid", "NON_EXISTENT_RELATIONSHIP")

        mock_repo.delete_relationship.assert_called_once_with("source-uid", "target-uid", "NON_EXISTENT_RELATIONSHIP")
        assert "Relationship NON_EXISTENT_RELATIONSHIP from 'source-uid' to 'target-uid' not found" in str(exc_info.value)

class TestGraphServiceCreateNodesBatch:
    def test_create_nodes_batch_success(self):
        mock_connection = Mock(spec=Neo4jConnection)
        mock_repo = Mock(spec=GraphRepository)
        mock_repo.node_exists = Mock(return_value=False)

        node_responses = [
            NodeResponse(
                uid="node-1-uid",
                label="TestLabel",
                name="Test Node 1",
                created_at=datetime.now(),
                updated_at=datetime.now()
            ),
            NodeResponse(
                uid="node-2-uid",
                label="TestLabel",
                name="Test Node 2",
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
        ]
        mock_repo.create_node = Mock(side_effect=node_responses)

        service = GraphService(mock_connection)
        service._repo = mock_repo

        nodes_create = [
            NodeCreate(label="TestLabel", name="Test Node 1"),
            NodeCreate(label="TestLabel", name="Test Node 2")
        ]

        result = service.create_nodes_batch(nodes_create)

        assert mock_repo.node_exists.call_count == 2
        assert mock_repo.create_node.call_count == 2
        assert len(result) == 2
        assert result == node_responses

    def test_create_nodes_batch_with_duplicates(self):
        mock_connection = Mock(spec=Neo4jConnection)
        mock_repo = Mock(spec=GraphRepository)

        mock_repo.node_exists.side_effect = [False, True]

        node_response = NodeResponse(
            uid="node-1-uid",
            label="TestLabel",
            name="Test Node 1",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        mock_repo.create_node = Mock(return_value=node_response)

        service = GraphService(mock_connection)
        service._repo = mock_repo

        nodes_create = [
            NodeCreate(label="TestLabel", name="Test Node 1"),
            NodeCreate(label="TestLabel", name="Test Node 1")
        ]

        result = service.create_nodes_batch(nodes_create)

        assert mock_repo.node_exists.call_count == 2
        mock_repo.create_node.assert_called_once()
        assert len(result) == 1
        assert result[0] == node_response


class TestGraphServiceCreateRelationshipsBatch:
    def test_create_relationships_batch_success(self):
        mock_connection = Mock(spec=Neo4jConnection)
        mock_repo = Mock(spec=GraphRepository)

        rel_responses = [
            RelationshipResponse(
                source_uid="source-uid-1",
                target_uid="target-uid-1",
                rel_type="TEST_RELATIONSHIP_1",
                weight=1.0,
                created_at=datetime.now(),
                updated_at=datetime.now()
            ),
            RelationshipResponse(
                source_uid="source-uid-2",
                target_uid="target-uid-2",
                rel_type="TEST_RELATIONSHIP_2",
                weight=0.5,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
        ]
        mock_repo.create_relationship = Mock(side_effect=rel_responses)

        service = GraphService(mock_connection)
        service._repo = mock_repo

        rels_create = [
            RelationshipCreate(
                source_uid="source-uid-1",
                target_uid="target-uid-1",
                rel_type="TEST_RELATIONSHIP_1"
            ),
            RelationshipCreate(
                source_uid="source-uid-2",
                target_uid="target-uid-2",
                rel_type="TEST_RELATIONSHIP_2",
                weight=0.5
            )
        ]

        result = service.create_relationships_batch(rels_create)

        assert mock_repo.get_node.call_count == 4
        assert mock_repo.create_relationship.call_count == 2
        assert len(result) == 2
        assert result == rel_responses

    def test_create_relationships_batch_with_errors(self):
        mock_connection = Mock(spec=Neo4jConnection)
        mock_repo = Mock(spec=GraphRepository)

        def get_node_side_effect(uid):
            if uid == "source-uid-1":
                return NodeResponse(
                    uid="source-uid-1",
                    label="SourceLabel",
                    name="Source Node 1",
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
            elif uid == "target-uid-1":
                return NodeResponse(
                    uid="target-uid-1",
                    label="TargetLabel",
                    name="Target Node 1",
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
            else:
                return None

        mock_repo.get_node = Mock(side_effect=get_node_side_effect)

        service = GraphService(mock_connection)
        service._repo = mock_repo

        rels_create = [
            RelationshipCreate(
                source_uid="source-uid-1",
                target_uid="target-uid-1",
                rel_type="TEST_RELATIONSHIP_1"
            ),
            RelationshipCreate(
                source_uid="non-existent-source-uid",
                target_uid="target-uid-2",
                rel_type="TEST_RELATIONSHIP_2"
            )
        ]

        result = service.create_relationships_batch(rels_create)

        assert mock_repo.get_node.call_count == 3
        mock_repo.create_relationship.assert_called_once()
        assert len(result) == 1


class TestGraphServiceClearAll:
    def test_clear_all_success(self):
        mock_connection = Mock(spec=Neo4jConnection)
        mock_repo = Mock(spec=GraphRepository)
        mock_repo.clear_all = Mock()

        service = GraphService(mock_connection)
        service._repo = mock_repo

        service.clear_all()

        mock_repo.clear_all.assert_called_once()


class TestGraphServiceGetStats:
    def test_get_stats_success(self):
        mock_connection = Mock(spec=Neo4jConnection)
        mock_repo = Mock(spec=GraphRepository)

        expected_stats = {
            "total_nodes": 10,
            "total_relationships": 5,
            "labels": {
                "Technology": 7,
                "Company": 3
            }
        }
        mock_repo.get_stats = Mock(return_value=expected_stats)

        service = GraphService(mock_connection)
        service._repo = mock_repo

        result = service.get_stats()

        mock_repo.get_stats.assert_called_once()
        assert result == expected_stats
