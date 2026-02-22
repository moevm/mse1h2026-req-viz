# visualization.py
from pyvis.network import Network
from config import NODE_COLORS, EDGE_COLORS, DASHED_EDGE_TYPES


def get_node_color(node_type: str) -> str:
    """Возвращает цвет узла по типу"""
    return NODE_COLORS.get(node_type, "#9E9E9E")


def get_edge_color(edge_type: str) -> str:
    """Возвращает цвет связи по типу"""
    return EDGE_COLORS.get(edge_type, "#9E9E9E")


def create_graph_visualization(
    nodes: list, 
    edges: list, 
    node_filters: list, 
    edge_filters: list,
    edge_weights: dict
) -> str:

    # Фильтрация узлов
    filtered_nodes = [n for n in nodes if n["type"] in node_filters]
    filtered_node_ids = {n["id"] for n in filtered_nodes}
    
    # Фильтрация связей
    filtered_edges = []
    for e in edges:
        if (e["type"] in edge_filters and 
            e["source"] in filtered_node_ids and 
            e["target"] in filtered_node_ids):
            filtered_edges.append(e)
    
    # Создание сети PyVis
    net = Network(
        height="500px", 
        width="100%", 
        bgcolor="#222222", 
        font_color="white"
    )
    
    # Добавление узлов
    for node in filtered_nodes:
        net.add_node(
            node["id"], 
            label=node["label"], 
            title=f"{node['type']}: {node['label']}",
            color=get_node_color(node["type"]),
            size=25
        )
    
    # Добавление связей
    for edge in filtered_edges:
        weight = edge_weights.get(edge["type"], 1.0) * edge.get("weight", 1.0)
        net.add_edge(
            edge["source"], 
            edge["target"],
            title=edge["type"],
            width=weight * 3,
            color=get_edge_color(edge["type"]),
            dashes=edge["type"] in DASHED_EDGE_TYPES
        )
    
    # Настройка физики графа
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
        }
    }
    """)
    
    html_path = "temp_graph.html"
    net.save_graph(html_path)
    
    with open(html_path, "r", encoding="utf-8") as f:
        return f.read()