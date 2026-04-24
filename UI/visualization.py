from pyvis.network import Network
from config import NODE_COLORS, EDGE_COLORS, DASHED_EDGE_TYPES

def get_node_color(node_type: str) -> str:
    return NODE_COLORS.get(node_type, "#9E9E9E")

def get_edge_color(edge_type: str) -> str:
    return EDGE_COLORS.get(edge_type, "#9E9E9E")

def create_graph_visualization(
    nodes: list, 
    edges: list, 
    node_filters: list, 
    edge_weight_thresholds: dict,
    binary_edge_filters: dict = None
) -> str:
    """Создаёт HTML-визуализацию графа с фильтрацией."""
    if binary_edge_filters is None:
        binary_edge_filters = {}

    filtered_nodes = [n for n in nodes if n["type"] in node_filters]
    filtered_node_ids = {n["id"] for n in filtered_nodes}
    
    filtered_edges = []
    for e in edges:
        if e["type"] in binary_edge_filters and not binary_edge_filters[e["type"]]:
            continue
        if e["source"] not in filtered_node_ids or e["target"] not in filtered_node_ids:
            continue
        min_weight = edge_weight_thresholds.get(e["type"], 0.0)
        if e["weight"] >= min_weight:
            filtered_edges.append(e)
    
    net = Network(
        height="550px", 
        width="100%", 
        bgcolor="#222222", 
        font_color="white",
        notebook=False
    )
    
    for node in filtered_nodes:
        net.add_node(
            node["id"], 
            label=node["label"], 
            title=f"{node['type']}: {node['label']}",
            color=get_node_color(node["type"]),
            size=25
        )
    
    for edge in filtered_edges:
        net.add_edge(
            edge["source"], 
            edge["target"],
            title=f"{edge['type']} (вес: {edge['weight']})",
            width=edge["weight"] * 4,  
            color=get_edge_color(edge["type"]),
            dashes=edge["type"] in DASHED_EDGE_TYPES
        )
    
    net.set_options("""
    {
        "physics": {
            "forceAtlas2Based": {
                "gravitationalConstant": -50,
                "centralGravity": 0.01,
                "springLength": 100,
                "springConstant": 0.08
            },
            "maxVelocity": 146,
            "solver": "forceAtlas2Based",
            "timestep": 0.35,
            "stabilization": {"enabled": true, "iterations": 100}
        },
        "interaction": {"hover": true}
    }
    """)
    
    return net.generate_html()