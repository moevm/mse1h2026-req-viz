import streamlit as st
from services import BackendClient
from graph_operations import merge_graphs

def toggle_node(node_id, clean_label):
    """Переключает состояние узла: добавляет/удаляет подграф."""
    backend = BackendClient()

    if node_id in st.session_state.expanded_nodes:
        st.session_state.expanded_nodes.discard(node_id)
        st.session_state.subgraphs.pop(node_id, None)
        st.info(f"Узел '{clean_label}' свернут.")
    else:
        try:
            with st.spinner(f"Загрузка соседей для '{clean_label}'..."):
                sub = backend.get_graph(clean_label)
                
                if not sub or not sub.get("nodes"):
                    st.warning(f"Бэкенд вернул пустой граф для '{clean_label}'.")
                    return

                st.session_state.subgraphs[node_id] = {
                    "nodes": sub.get("nodes", []),
                    "edges": sub.get("edges", [])
                }
                st.session_state.expanded_nodes.add(node_id)
        except Exception as e:
            st.error(f"Ошибка при раскрытии узла: {e}")

def process_graph_selection(selected):
    """Обрабатывает сырое событие выбора элемента из agraph."""
    if selected:
        node_id = selected["id"] if isinstance(selected, dict) else selected

        if st.session_state.get("last_click") != node_id:
            node_map = {
                n["id"]: n["label"]
                for n in st.session_state.display_graph["nodes"]
            }

            if node_id in node_map:
                st.session_state.last_click = node_id
                
                toggle_node(node_id, node_map[node_id])

                st.session_state.display_graph = merge_graphs(
                    st.session_state.graph_data["nodes"],
                    st.session_state.expanded_nodes,
                    st.session_state.subgraphs
                )
                st.rerun()
    else:
        st.session_state.last_click = None