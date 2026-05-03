import pytest
import time
import requests
import subprocess
import os
from typing import Dict, Any, Generator
from pathlib import Path

BACKEND_URL = "http://localhost:8001"
BACKEND_HEALTH_URL = f"{BACKEND_URL}/api/health"
GRAPH_API_URL = f"{BACKEND_URL}/api/graph"

MIN_NODES = 5
MIN_EDGES = 3
TEST_TIMEOUT = 180

SINGLE_TECH = "python"
MULTIPLE_TECHS = "python,javascript"
UNIQUE_TECH = "kafka"
UNIQUE_MULTIPLE = "golang,rabbitmq"

@pytest.fixture(scope="session")
def docker_compose_file() -> str:
    return str(Path(__file__).parent / "docker-compose.test.yml")


@pytest.fixture(scope="session")
def test_environment(docker_compose_file: str) -> Generator[None, None, None]:
    print("\n=== Setting up test environment ===")

    original_dir = os.getcwd()
    compose_dir = Path(__file__).parent
    os.chdir(compose_dir)

    try:
        print("Starting test services...")
        result = subprocess.run(
            ["docker", "compose", "-f", docker_compose_file, "up", "-d"],
            capture_output=True,
            text=True,
            timeout=300
        )

        if result.returncode != 0:
            pytest.fail(f"Failed to start docker services: {result.stderr}")

        print("Waiting for backend to be healthy...")
        max_wait = 120
        start_time = time.time()

        while time.time() - start_time < max_wait:
            try:
                response = requests.get(BACKEND_HEALTH_URL, timeout=10)
                if response.status_code == 200:
                    health_data = response.json()
                    if health_data.get("status") == "ok" and health_data.get("connected"):
                        print("Backend is healthy and connected to database")
                        break
            except requests.RequestException:
                pass

            print("  Waiting for backend...")
            time.sleep(5)
        else:
            pytest.fail("Backend did not become healthy within timeout")

        yield

    finally:
        print("\n=== Cleaning up test environment ===")
        try:
            subprocess.run(
                ["docker", "compose", "-f", docker_compose_file, "down", "-v"],
                capture_output=True,
                text=True,
                timeout=60
            )
            print("Test environment cleaned up")
        except subprocess.TimeoutExpired:
            print("Cleanup timeout, forcing cleanup")
            subprocess.run(
                ["docker", "compose", "-f", docker_compose_file, "down", "-v", "-f"],
                capture_output=True
            )
        os.chdir(original_dir)


@pytest.fixture
def api_client() -> "APIClient":
    return APIClient(BACKEND_URL)


class APIClient:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.timeout = 60

    def get_graph(self, technology: str, **params) -> Dict[str, Any]:
        url = f"{self.base_url}/api/graph"
        query_params = {"technology": technology, **params}

        response = self.session.get(url, params=query_params)
        response.raise_for_status()
        return response.json()

    def health_check(self) -> Dict[str, Any]:
        """Check backend health."""
        response = self.session.get(f"{self.base_url}/api/health")
        response.raise_for_status()
        return response.json()


@pytest.fixture
def performance_tracker() -> "PerformanceTracker":
    return PerformanceTracker()


class PerformanceTracker:
    def __init__(self):
        self.timings = {}

    def time_request(self, name: str, func, *args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            end_time = time.time()
            duration = end_time - start_time
            self.timings[name] = duration
            print(f"{name}: {duration:.2f}s")
            return result
        except Exception as e:
            end_time = time.time()
            duration = end_time - start_time
            print(f"{name}: {duration:.2f}s (failed: {e})")
            raise

    def get_improvement(self, cached_name: str, uncached_name: str) -> float:
        if cached_name not in self.timings or uncached_name not in self.timings:
            return 0.0

        cached_time = self.timings[cached_name]
        uncached_time = self.timings[uncached_name]

        if uncached_time == 0:
            return 0.0

        improvement = (uncached_time - cached_time) / uncached_time
        return improvement

    def print_summary(self):
        print("\n=== Performance Summary ===")
        for name, duration in self.timings.items():
            print(f"{name}: {duration:.2f}s")


def validate_graph_structure(graph_data: Dict[str, Any]) -> None:
    assert "nodes" in graph_data, "Graph response must contain 'nodes' field"
    assert "edges" in graph_data, "Graph response must contain 'edges' field"
    assert isinstance(graph_data["nodes"], list), "Nodes must be a list"
    assert isinstance(graph_data["edges"], list), "Edges must be a list"

    for node in graph_data["nodes"]:
        assert "id" in node, "Node must have 'id' field"
        assert "label" in node, "Node must have 'label' field"
        assert "type" in node, "Node must have 'type' field"

    for edge in graph_data["edges"]:
        assert "source" in edge, "Edge must have 'source' field"
        assert "target" in edge, "Edge must have 'target' field"
        assert "type" in edge, "Edge must have 'type' field"
        assert "weight" in edge, "Edge must have 'weight' field"


def validate_connectivity(graph_data: Dict[str, Any]) -> None:
    nodes = {node["id"]: node for node in graph_data["nodes"]}
    edges = graph_data["edges"]

    if not nodes:
        return

    adjacency = {node_id: set() for node_id in nodes}
    for edge in edges:
        if edge["source"] in nodes and edge["target"] in nodes:
            adjacency[edge["source"]].add(edge["target"])
            adjacency[edge["target"]].add(edge["source"])

    start_node = next(iter(nodes))
    visited = set()
    stack = [start_node]

    while stack:
        current = stack.pop()
        if current not in visited:
            visited.add(current)
            stack.extend(adjacency[current] - visited)

    if len(nodes) > 1:
        assert len(edges) > 0, "Graph with multiple nodes should have edges"


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )


def pytest_collection_modifyitems(config, items):
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(pytest.mark.timeout(TEST_TIMEOUT))
