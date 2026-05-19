import math
import streamlit as st

def merge_graphs(base_nodes, expanded_ids, subgraphs):
    """
    Сливает базовый граф и раскрытые подграфы в единую структуру,
    исключая дубликаты по названиям (label) и рассчитывая координаты.
    """
    nodes_map = {n["id"]: n.copy() for n in base_nodes}
    label_to_id = {n["label"]: n["id"] for n in base_nodes}
    all_edges = []
    seen_edges = set()

    if st.session_state.graph_data:
        for e in st.session_state.graph_data.get("edges", []):
            edge = e.copy()
            key = (edge["source"], edge["target"], edge.get("type"))
            all_edges.append(edge)
            seen_edges.add(key)

    for parent_id in expanded_ids:
        sub = subgraphs.get(parent_id)
        if not sub:
            continue

        parent_node = nodes_map.get(parent_id)
        if not parent_node:
            continue

        px = parent_node.get("x", 400)
        py = parent_node.get("y", 300)

        id_mapping = {}
        new_nodes = []

        for n in sub.get("nodes", []):
            node = n.copy()
            label = node["label"]

            if label in label_to_id:
                id_mapping[node["id"]] = label_to_id[label]
                continue

            label_to_id[label] = node["id"]
            id_mapping[node["id"]] = node["id"]
            new_nodes.append(node)

        radius = 150
        num_new = len(new_nodes)

        for i, node in enumerate(new_nodes):
            angle = (2 * math.pi * i) / num_new if num_new > 0 else 0
            node["x"] = px + radius * math.cos(angle)
            node["y"] = py + radius * math.sin(angle)
            nodes_map[node["id"]] = node

        for e in sub.get("edges", []):
            source = id_mapping.get(e["source"])
            target = id_mapping.get(e["target"])

            if not source or not target:
                continue

            edge = {**e, "source": source, "target": target}
            key = (source, target, edge.get("type"))

            if key not in seen_edges:
                all_edges.append(edge)
                seen_edges.add(key)

    return {
        "nodes": list(nodes_map.values()),
        "edges": all_edges
    }

def assign_initial_positions(nodes, center_x=400, center_y=300, radius=250):
    """Располагает первый узел в центре, а остальные — вокруг него по кругу."""
    if not nodes:
        return nodes

    nodes[0]["x"] = center_x
    nodes[0]["y"] = center_y

    other_nodes = nodes[1:]
    num_others = len(other_nodes)
    
    for i, node in enumerate(other_nodes):
        if "x" not in node or "y" not in node:
            angle = (2 * math.pi * i) / num_others if num_others > 0 else 0
            node["x"] = center_x + radius * math.cos(angle)
            node["y"] = center_y + radius * math.sin(angle)
            
    return nodes