import streamlit as st

def initialize_session_state():
    """Инициализирует все необходимые переменные в session_state."""
    if 'graph_data' not in st.session_state:
        st.session_state.graph_data = None
    if 'search_query' not in st.session_state:
        st.session_state.search_query = ""
    if 'display_graph' not in st.session_state:
        st.session_state.display_graph = {"nodes": [], "edges": []}
    if 'expanded_nodes' not in st.session_state:
        st.session_state.expanded_nodes = set()
    if 'subgraphs' not in st.session_state:
        st.session_state.subgraphs = {}
    if "last_click" not in st.session_state:
        st.session_state.last_click = None

def reset_graph_state(new_graph_data):
    """Сбрасывает состояние раскрытий и записывает новые данные базового графа."""
    st.session_state.graph_data = new_graph_data
    st.session_state.display_graph = new_graph_data
    st.session_state.expanded_nodes = set()
    st.session_state.subgraphs = {}
    st.session_state.last_click = None