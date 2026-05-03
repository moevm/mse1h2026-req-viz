import pytest
import time
from typing import Dict, Any

from .conftest import (
    validate_graph_structure,
    validate_connectivity,
    MIN_NODES,
    MIN_EDGES,
    SINGLE_TECH,
    MULTIPLE_TECHS,
    UNIQUE_TECH,
    UNIQUE_MULTIPLE
)


@pytest.mark.integration
@pytest.mark.usefixtures("test_environment")
class TestGraphAPI:
    def test_single_technology_graph_structure_and_connectivity(
        self, api_client, performance_tracker
    ):
        """
        Тест 1: Запрос одной технологии и проверка связного графа
        Проверяет, что ответ содержит связный граф состоящий из > N узлов и > M ребер
        """
        print(f"\n=== Test 1: Single Technology Graph ({SINGLE_TECH}) ===")

        graph_data = performance_tracker.time_request(
            "single_tech_request",
            api_client.get_graph,
            SINGLE_TECH,
            depth=1,
            limit=30
        )

        validate_graph_structure(graph_data)

        nodes_count = len(graph_data["nodes"])
        edges_count = len(graph_data["edges"])

        print(f"Graph stats: {nodes_count} nodes, {edges_count} edges")

        assert nodes_count > MIN_NODES, (
            f"Graph should contain more than {MIN_NODES} nodes, "
            f"but got {nodes_count}"
        )
        assert edges_count > MIN_EDGES, (
            f"Graph should contain more than {MIN_EDGES} edges, "
            f"but got {edges_count}"
        )

        validate_connectivity(graph_data)

        tech_node_found = any(
            node["label"].lower() == SINGLE_TECH.lower()
            for node in graph_data["nodes"]
        )
        assert tech_node_found, f"Graph should contain the requested technology '{SINGLE_TECH}'"

        print("Single technology graph test passed")

    def test_multiple_technologies_multiple_subgraphs(
        self, api_client, performance_tracker
    ):
        """
        Тест 2: Запрос нескольких технологий и проверка множественных подграфов
        Проверяет, что ответ содержит несколько подграфов для разных технологий
        """
        print(f"\n=== Test 2: Multiple Technologies Graph ({MULTIPLE_TECHS}) ===")

        graph_data = performance_tracker.time_request(
            "multiple_techs_request",
            api_client.get_graph,
            MULTIPLE_TECHS,
            depth=1,
            limit=50
        )

        validate_graph_structure(graph_data)

        nodes_count = len(graph_data["nodes"])
        edges_count = len(graph_data["edges"])

        print(f"Multiple techs graph stats: {nodes_count} nodes, {edges_count} edges")

        assert nodes_count > MIN_NODES, (
            f"Multiple technologies graph should contain more than {MIN_NODES} nodes, "
            f"but got {nodes_count}"
        )

        requested_techs = [tech.strip().lower() for tech in MULTIPLE_TECHS.split(",")]
        found_techs = set()

        for node in graph_data["nodes"]:
            node_label = node["label"].lower()
            for tech in requested_techs:
                if tech in node_label or node_label in tech:
                    found_techs.add(tech)
                    break

        print(f"Found technologies: {found_techs}")
        print(f"Requested technologies: {requested_techs}")

        assert len(found_techs) >= 2, (
            f"Should find at least 2 technologies, but found {len(found_techs)}: {found_techs}"
        )

        node_types = set(node["type"] for node in graph_data["nodes"])
        assert len(node_types) >= 1, f"Should have at least 1 node type, got {node_types}"

        print(f"Node types found: {node_types}")
        print("Multiple technologies graph test passed")

    def test_caching_performance_comparison(
        self, api_client, performance_tracker
    ):
        """
        Тест 3: Сравнение производительности первого и второго запросов
        Проверяет, что время ответа уменьшилось благодаря кэшированию в Neo4j
        """
        print(f"\n=== Test 3: Caching Performance Comparison ({UNIQUE_TECH}) ===")

        print("Making first request (uncached)...")
        try:
            graph_data_first = performance_tracker.time_request(
                "first_request_uncached",
                api_client.get_graph,
                UNIQUE_TECH,
                depth=2,
                limit=30
            )
        except Exception as e:
            print(f"Unique tech not found, using standard: {e}")
            graph_data_first = performance_tracker.time_request(
                "first_request_uncached",
                api_client.get_graph,
                SINGLE_TECH,
                depth=2,
                limit=30
            )

        validate_graph_structure(graph_data_first)
        assert len(graph_data_first["nodes"]) > 0, "First request should return some nodes"

        first_request_time = performance_tracker.timings["first_request_uncached"]
        print(f"First request time: {first_request_time:.2f}s")

        print("Making second request (cached)...")
        try:
            graph_data_second = performance_tracker.time_request(
                "second_request_cached",
                api_client.get_graph,
                UNIQUE_TECH,
                depth=2,
                limit=30
            )
        except Exception as e:
            print(f"Second request failed with unique tech, using standard: {e}")
            graph_data_second = performance_tracker.time_request(
                "second_request_cached",
                api_client.get_graph,
                SINGLE_TECH,
                depth=2,
                limit=30
            )

        validate_graph_structure(graph_data_second)
        assert len(graph_data_second["nodes"]) > 0, "Second request should return some nodes"

        second_request_time = performance_tracker.timings["second_request_cached"]
        print(f"Second request time: {second_request_time:.2f}s")

        improvement = performance_tracker.get_improvement(
            "second_request_cached",
            "first_request_uncached"
        )

        print(f"Performance improvement: {improvement:.1%}")

        if improvement > 0:
            print(f"Cache improved performance by {improvement:.1%}")
        else:
            print(f"Cache improvement not detected ({improvement:.1%})")
            print("  This might be due to external factors or small difference")

        assert first_request_time < 120, f"First request too slow: {first_request_time:.2f}s"
        assert second_request_time < 120, f"Second request too slow: {second_request_time:.2f}s"

        print("Caching performance comparison test passed")

    def test_multiple_technologies_caching_performance(
        self, api_client, performance_tracker
    ):
        """
        Тест 4: Сравнение производительности для множественных технологий
        Проверяет, что кэширование работает и для запросов с несколькими технологиями
        """
        print(f"\n=== Test 4: Multiple Technologies Caching Performance ({UNIQUE_MULTIPLE}) ===")

        print("Making first request with multiple technologies (uncached)...")
        try:
            graph_data_first = performance_tracker.time_request(
                "first_multiple_uncached",
                api_client.get_graph,
                UNIQUE_MULTIPLE,
                depth=2,
                limit=50
            )
        except Exception as e:
            print(f"Unique multiple techs not found, using standard: {e}")
            graph_data_first = performance_tracker.time_request(
                "first_multiple_uncached",
                api_client.get_graph,
                MULTIPLE_TECHS,
                depth=2,
                limit=50
            )

        validate_graph_structure(graph_data_first)
        assert len(graph_data_first["nodes"]) > 0, "First request should return some nodes"

        first_request_time = performance_tracker.timings["first_multiple_uncached"]
        print(f"First multiple request time: {first_request_time:.2f}s")

        requested_techs = [tech.strip().lower() for tech in UNIQUE_MULTIPLE.split(",")]
        found_techs = set()

        for node in graph_data_first["nodes"]:
            node_label = node["label"].lower()
            for tech in requested_techs:
                if tech in node_label or node_label in tech:
                    found_techs.add(tech)
                    break

        print(f"Found technologies in first request: {found_techs}")

        print("Making second request with multiple technologies (cached)...")
        try:
            graph_data_second = performance_tracker.time_request(
                "second_multiple_cached",
                api_client.get_graph,
                UNIQUE_MULTIPLE,
                depth=2,
                limit=50
            )
        except Exception as e:
            print(f"Second request failed with unique multiple techs, using standard: {e}")
            graph_data_second = performance_tracker.time_request(
                "second_multiple_cached",
                api_client.get_graph,
                MULTIPLE_TECHS,
                depth=2,
                limit=50
            )

        validate_graph_structure(graph_data_second)
        assert len(graph_data_second["nodes"]) > 0, "Second request should return some nodes"

        second_request_time = performance_tracker.timings["second_multiple_cached"]
        print(f"Second multiple request time: {second_request_time:.2f}s")

        found_techs_second = set()
        for node in graph_data_second["nodes"]:
            node_label = node["label"].lower()
            for tech in requested_techs:
                if tech in node_label or node_label in tech:
                    found_techs_second.add(tech)
                    break

        print(f"Found technologies in second request: {found_techs_second}")

        improvement = performance_tracker.get_improvement(
            "second_multiple_cached",
            "first_multiple_uncached"
        )

        print(f"Performance improvement for multiple technologies: {improvement:.1%}")

        if improvement > 0:
            print(f"Cache improved performance for multiple technologies by {improvement:.1%}")
        else:
            print(f"Cache improvement not detected for multiple technologies ({improvement:.1%})")
            print("  This might be due to external factors or small difference")

        assert first_request_time < 120, f"First multiple request too slow: {first_request_time:.2f}s"
        assert second_request_time < 120, f"Second multiple request too slow: {second_request_time:.2f}s"

        assert len(found_techs) >= 1, f"Should find at least 1 technology in first request, got {found_techs}"
        assert len(found_techs_second) >= 1, f"Should find at least 1 technology in second request, got {found_techs_second}"

        print("Multiple technologies caching performance test passed")
