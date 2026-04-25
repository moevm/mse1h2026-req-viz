from streamlit_agraph import Node, Edge, Config

from config import (
    NODE_COLORS,
    EDGE_COLORS,
    DASHED_EDGE_TYPES
)


def get_node_color(node_type: str) -> str:
    return NODE_COLORS.get(node_type, "#9E9E9E")


def get_edge_color(edge_type: str) -> str:
    return EDGE_COLORS.get(edge_type, "#9E9E9E")


def get_edge_width(weight: float) -> float:
    if weight is None:
        return 2
    return max(1, weight * 5)


def create_graph_visualization(
    nodes: list,
    edges: list,
    node_filters: list,
    edge_weight_thresholds: dict,
    binary_edge_filters: dict = None
):
    """
    Создаёт структуру для streamlit-agraph (nodes, edges, config)
    """

    if binary_edge_filters is None:
        binary_edge_filters = {}

    filtered_nodes = [
        n for n in nodes
        if n["type"] in node_filters
    ]

    filtered_node_ids = {n["id"] for n in filtered_nodes}

    filtered_edges = []

    for e in edges:

        edge_type = e.get("type")
        weight = e.get("weight", 1)

        if edge_type in binary_edge_filters:
            if not binary_edge_filters[edge_type]:
                continue

        if e["source"] not in filtered_node_ids:
            continue

        if e["target"] not in filtered_node_ids:
            continue

        min_weight = edge_weight_thresholds.get(edge_type, 0.0)

        if weight < min_weight:
            continue

        filtered_edges.append(e)

    agraph_nodes = []

    for n in filtered_nodes:
        agraph_nodes.append(
            Node(
                id=n["id"],
                label=n["label"],
                size=25,
                color=get_node_color(n["type"]),
                font={"color": "white", "size": 12},
                title="Раскрыть"
            )
        )

    agraph_edges = []

    for e in filtered_edges:

        edge_type = e.get("type")
        weight = e.get("weight", 1)

        agraph_edges.append(
            Edge(
                source=e["source"],
                target=e["target"],
                color=get_edge_color(edge_type),
                width=get_edge_width(weight),
                dashes=edge_type in DASHED_EDGE_TYPES,
                title=f"{edge_type} (вес: {weight})"
            )
        )

    config = Config(
        height=550,
        width="100%",
        directed=True,

        nodeHighlightBehavior=True,
        highlightColor="#F7A7A6",

        collapsible=True,
        physics=True,

        node={
            "font": {"size": 12}
        },

        edges={
            "smooth": True
        }
    )

    return agraph_nodes, agraph_edges, config