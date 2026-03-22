from datetime import datetime

import pytest
from pydantic import ValidationError

from graph.models import (
    NodeCreate,
    NodeFilter,
    NodeUpdate,
    RelationshipCreate,
    RelationshipFilter,
    RelationshipUpdate,
    SubgraphFilter,
)


class TestNodeCreate:
    def test_valid_node_create(self):
        node_data = {
            "label": "Technology",
            "name": "Python",
            "description": "Programming language",
            "properties": {"version": "3.12", "type": "interpreted"},
            "source": "wikidata",
        }
        node = NodeCreate(**node_data)
        assert node.label == "Technology"
        assert node.name == "Python"
        assert node.description == "Programming language"
        assert node.properties == {"version": "3.12", "type": "interpreted"}
        assert node.source == "wikidata"

    def test_node_create_validator(self):
        valid_labels = ["Technology", "Company", "TestLabel"]
        for label in valid_labels:
            node_data = {"label": label, "name": "Test"}
            node = NodeCreate(**node_data)
            assert node.label == label

        invalid_labels = ["technology", "company", "test-label"]
        for label in invalid_labels:
            node_data = {"label": label, "name": "Test"}
            with pytest.raises(ValidationError) as exc_info:
                NodeCreate(**node_data)
            assert "Label must start with uppercase letter" in str(exc_info.value)

        node_data = {"label": "", "name": "Test"}
        with pytest.raises(ValidationError):
            NodeCreate(**node_data)

        node_data = {"label": None, "name": "Test"}
        with pytest.raises(ValidationError):
            NodeCreate(**node_data)

        long_label = "A" * 101
        node_data = {"label": long_label, "name": "Test"}
        with pytest.raises(ValidationError):
            NodeCreate(**node_data)

        node_data = {"label": "Test", "name": ""}
        with pytest.raises(ValidationError):
            NodeCreate(**node_data)

        node_data = {"label": "Test", "name": None}
        with pytest.raises(ValidationError):
            NodeCreate(**node_data)

        long_name = "A" * 501
        node_data = {"label": "Test", "name": long_name}
        with pytest.raises(ValidationError):
            NodeCreate(**node_data)

        long_desc = "A" * 5001
        node_data = {"label": "Test", "name": "Test Node", "description": long_desc}
        with pytest.raises(ValidationError):
            NodeCreate(**node_data)

        long_source = "A" * 201
        node_data = {"label": "Test", "name": "Test Node", "source": long_source}
        with pytest.raises(ValidationError):
            NodeCreate(**node_data)


class TestNodeUpdate:
    def test_valid_node_update_all_fields(self):
        update_data = {
            "name": "Updated Name",
            "description": "Updated description",
            "properties": {"new_prop": "value"},
            "source": "updated_source",
        }
        update = NodeUpdate(**update_data)
        assert update.name == "Updated Name"
        assert update.description == "Updated description"
        assert update.properties == {"new_prop": "value"}
        assert update.source == "updated_source"

    def test_node_update_partial_fields(self):
        update_data = {"name": "Updated Name"}
        update = NodeUpdate(**update_data)
        assert update.name == "Updated Name"
        assert update.description is None
        assert update.properties is None
        assert update.source is None

    def test_node_update_empty_name(self):
        update_data = {"name": ""}
        with pytest.raises(ValidationError):
            NodeUpdate(**update_data)

    def test_node_update_none_fields(self):
        update_data = {
            "name": None,
            "description": None,
            "properties": None,
            "source": None,
        }
        update = NodeUpdate(**update_data)
        assert update.name is None
        assert update.description is None
        assert update.properties is None
        assert update.source is None


class TestRelationshipCreate:
    def test_valid_relationship_create(self):
        rel_data = {
            "source_uid": "source123",
            "target_uid": "target456",
            "rel_type": "USED_WITH",
            "weight": 0.8,
            "properties": {"confidence": 0.9},
            "source": "wikidata",
        }
        rel = RelationshipCreate(**rel_data)
        assert rel.source_uid == "source123"
        assert rel.target_uid == "target456"
        assert rel.rel_type == "USED_WITH"
        assert rel.weight == 0.8
        assert rel.properties == {"confidence": 0.9}
        assert rel.source == "wikidata"

    def test_relationship_create_validator(self):
        valid_types = ["USED_WITH", "RELATED_TO", "DEPENDS_ON"]
        for rel_type in valid_types:
            rel_data = {
                "source_uid": "source123",
                "target_uid": "target456",
                "rel_type": rel_type,
            }
            rel = RelationshipCreate(**rel_data)
            assert rel.rel_type == rel_type

        invalid_types = ["used_with", "Used_With", "related-to", "Related_To"]
        for rel_type in invalid_types:
            rel_data = {
                "source_uid": "source123",
                "target_uid": "target456",
                "rel_type": rel_type,
            }
            with pytest.raises(ValidationError) as exc_info:
                RelationshipCreate(**rel_data)
            assert "Relationship type must be UPPER_SNAKE_CASE" in str(exc_info.value)

        invalid_types = ["USED WITH", "RELATED TO"]
        for rel_type in invalid_types:
            rel_data = {
                "source_uid": "source123",
                "target_uid": "target456",
                "rel_type": rel_type,
            }
            with pytest.raises(ValidationError) as exc_info:
                RelationshipCreate(**rel_data)
            assert "Relationship type must not contain spaces" in str(exc_info.value)

        rel_data = {
            "source_uid": "",
            "target_uid": "target456",
            "rel_type": "RELATED_TO",
        }
        with pytest.raises(ValidationError):
            RelationshipCreate(**rel_data)

        rel_data = {
            "source_uid": None,
            "target_uid": "target456",
            "rel_type": "RELATED_TO",
        }
        with pytest.raises(ValidationError):
            RelationshipCreate(**rel_data)

        rel_data = {
            "source_uid": "source123",
            "target_uid": "",
            "rel_type": "RELATED_TO",
        }
        with pytest.raises(ValidationError):
            RelationshipCreate(**rel_data)

        rel_data = {
            "source_uid": "source123",
            "target_uid": None,
            "rel_type": "RELATED_TO",
        }
        with pytest.raises(ValidationError):
            RelationshipCreate(**rel_data)

        rel_data = {
            "source_uid": "source123",
            "target_uid": "target456",
            "rel_type": "",
        }
        with pytest.raises(ValidationError):
            RelationshipCreate(**rel_data)

        rel_data = {
            "source_uid": "source123",
            "target_uid": "target456",
            "rel_type": None,
        }
        with pytest.raises(ValidationError):
            RelationshipCreate(**rel_data)

        long_type = "A" * 101
        rel_data = {
            "source_uid": "source123",
            "target_uid": "target456",
            "rel_type": long_type,
        }
        with pytest.raises(ValidationError):
            RelationshipCreate(**rel_data)

        rel_data = {
            "source_uid": "source123",
            "target_uid": "target456",
            "rel_type": "RELATED_TO",
            "weight": -0.5,
        }
        with pytest.raises(ValidationError):
            RelationshipCreate(**rel_data)

        rel_data = {
            "source_uid": "source123",
            "target_uid": "target456",
            "rel_type": "RELATED_TO",
            "weight": 0.0,
        }
        rel = RelationshipCreate(**rel_data)
        assert rel.weight == 0.0

        long_source = "A" * 201
        rel_data = {
            "source_uid": "source123",
            "target_uid": "target456",
            "rel_type": "RELATED_TO",
            "source": long_source,
        }
        with pytest.raises(ValidationError):
            RelationshipCreate(**rel_data)


class TestRelationshipUpdate:
    def test_valid_relationship_update_all_fields(self):
        update_data = {
            "weight": 0.9,
            "properties": {"updated": "value"},
            "source": "updated_source",
        }
        update = RelationshipUpdate(**update_data)
        assert update.weight == 0.9
        assert update.properties == {"updated": "value"}
        assert update.source == "updated_source"

    def test_relationship_update_partial_fields(self):
        update_data = {"weight": 0.75}
        update = RelationshipUpdate(**update_data)
        assert update.weight == 0.75
        assert update.properties is None
        assert update.source is None

    def test_relationship_update_negative_weight(self):
        update_data = {"weight": -0.5}
        with pytest.raises(ValidationError):
            RelationshipUpdate(**update_data)

    def test_relationship_update_zero_weight(self):
        update_data = {"weight": 0.0}
        update = RelationshipUpdate(**update_data)
        assert update.weight == 0.0

    def test_relationship_update_none_fields(self):
        update_data = {"weight": None, "properties": None, "source": None}
        update = RelationshipUpdate(**update_data)
        assert update.weight is None
        assert update.properties is None
        assert update.source is None


class TestNodeFilter:
    def test_valid_node_filter_all_fields(self):
        now = datetime.now()
        filter_data = {
            "labels": ["Technology", "Language"],
            "name_contains": "Python",
            "properties_match": {"version": "3.12"},
            "source": "wikidata",
            "created_after": now,
            "created_before": now,
            "limit": 50,
            "offset": 10,
        }
        node_filter = NodeFilter(**filter_data)
        assert node_filter.labels == ["Technology", "Language"]
        assert node_filter.name_contains == "Python"
        assert node_filter.properties_match == {"version": "3.12"}
        assert node_filter.source == "wikidata"
        assert node_filter.created_after == now
        assert node_filter.created_before == now
        assert node_filter.limit == 50
        assert node_filter.offset == 10

    def test_node_filter_default_values(self):
        node_filter = NodeFilter()
        assert node_filter.labels is None
        assert node_filter.name_contains is None
        assert node_filter.properties_match is None
        assert node_filter.source is None
        assert node_filter.created_after is None
        assert node_filter.created_before is None
        assert node_filter.limit == 100
        assert node_filter.offset == 0

    def test_node_filter_validator(self):
        filter_data = {"limit": 0}
        with pytest.raises(ValidationError):
            NodeFilter(**filter_data)

        filter_data = {"limit": -1}
        with pytest.raises(ValidationError):
            NodeFilter(**filter_data)

        filter_data = {"limit": 10001}
        with pytest.raises(ValidationError):
            NodeFilter(**filter_data)

        filter_data = {"offset": -1}
        with pytest.raises(ValidationError):
            NodeFilter(**filter_data)


class TestRelationshipFilter:
    def test_valid_relationship_filter_all_fields(self):
        filter_data = {
            "rel_types": ["USED_WITH", "RELATED_TO"],
            "weight_min": 0.5,
            "weight_max": 0.9,
            "source": "wikidata",
            "limit": 50,
            "offset": 10,
        }
        rel_filter = RelationshipFilter(**filter_data)
        assert rel_filter.rel_types == ["USED_WITH", "RELATED_TO"]
        assert rel_filter.weight_min == 0.5
        assert rel_filter.weight_max == 0.9
        assert rel_filter.source == "wikidata"
        assert rel_filter.limit == 50
        assert rel_filter.offset == 10

    def test_relationship_filter_default_values(self):
        rel_filter = RelationshipFilter()
        assert rel_filter.rel_types is None
        assert rel_filter.weight_min is None
        assert rel_filter.weight_max is None
        assert rel_filter.source is None
        assert rel_filter.limit == 100
        assert rel_filter.offset == 0

    def test_relationship_filter_validator(self):
        filter_data = {"weight_min": -0.1}
        with pytest.raises(ValidationError):
            RelationshipFilter(**filter_data)

        filter_data = {"weight_max": -0.1}
        with pytest.raises(ValidationError):
            RelationshipFilter(**filter_data)

        filter_data = {"limit": 0}
        with pytest.raises(ValidationError):
            RelationshipFilter(**filter_data)

        filter_data = {"limit": 10001}
        with pytest.raises(ValidationError):
            RelationshipFilter(**filter_data)

        filter_data = {"offset": -1}
        with pytest.raises(ValidationError):
            RelationshipFilter(**filter_data)


class TestSubgraphFilter:
    def test_valid_subgraph_filter_all_fields(self):
        node_filter = NodeFilter(labels=["Technology"], name_contains="Python")
        rel_filter = RelationshipFilter(rel_types=["USED_WITH"], weight_min=0.5)

        filter_data = {
            "node_filter": node_filter,
            "rel_filter": rel_filter,
            "center_uid": "center123",
            "depth": 3,
            "limit": 50,
        }
        subgraph_filter = SubgraphFilter(**filter_data)
        assert subgraph_filter.node_filter == node_filter
        assert subgraph_filter.rel_filter == rel_filter
        assert subgraph_filter.center_uid == "center123"
        assert subgraph_filter.depth == 3
        assert subgraph_filter.limit == 50

    def test_subgraph_filter_default_values(self):
        subgraph_filter = SubgraphFilter()
        assert subgraph_filter.node_filter is None
        assert subgraph_filter.rel_filter is None
        assert subgraph_filter.center_uid is None
        assert subgraph_filter.depth == 1
        assert subgraph_filter.limit == 100

    def test_subgraph_filter_validator(self):
        filter_data = {"depth": 0}
        with pytest.raises(ValidationError):
            SubgraphFilter(**filter_data)

        filter_data = {"depth": 11}
        with pytest.raises(ValidationError):
            SubgraphFilter(**filter_data)

        filter_data = {"limit": 0}
        with pytest.raises(ValidationError):
            SubgraphFilter(**filter_data)

        filter_data = {"limit": 10001}
        with pytest.raises(ValidationError):
            SubgraphFilter(**filter_data)
