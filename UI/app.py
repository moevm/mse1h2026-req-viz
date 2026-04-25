import streamlit as st
import pandas as pd

from config import NODE_TYPE_FILTERS, EDGE_TYPES, EDGE_TYPE_NAMES, WEIGHTED_EDGE_TYPES, BINARY_EDGE_TYPES
from services import BackendClient, NotFoundError, BackendError
from report_generator import ReportGenerator
from streamlit_agraph import agraph, Node, Edge, Config

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
    """Толщина ребра по весу."""
    if weight is None:
        return 2
    return max(1, weight * 5)

#логика расширения графв
def merge_graphs(base_nodes, base_edges, expanded_ids, subgraphs):
    nodes = list(base_nodes)
    edges = list(base_edges)

    label_to_id = {n["label"]: n["id"] for n in nodes}

    seen_edges = {
        (e["source"], e["target"], e.get("type"))
        for e in edges
    }

    for nid in expanded_ids:
        sub = subgraphs.get(nid)
        if not sub:
            continue

        for n in sub["nodes"]:
            label = n["label"]

            if label not in label_to_id:
                nodes.append(n)
                label_to_id[label] = n["id"]

        for e in sub["edges"]:
            src_label = next(
                n["label"]
                for n in sub["nodes"]
                if n["id"] == e["source"]
            )

            tgt_label = next(
                n["label"]
                for n in sub["nodes"]
                if n["id"] == e["target"]
            )

            new_source = label_to_id[src_label]
            new_target = label_to_id[tgt_label]

            key = (
                new_source,
                new_target,
                e.get("type")
            )

            if key not in seen_edges:
                new_edge = e.copy()
                new_edge["source"] = new_source
                new_edge["target"] = new_target

                edges.append(new_edge)
                seen_edges.add(key)

    return {"nodes": nodes, "edges": edges}

def toggle_node(node_id, clean_label):
    """Переключает состояние узла: добавляет/удаляет подграф."""
    backend = BackendClient()

    if node_id in st.session_state.expanded_nodes:
        # сворачиваем
        st.session_state.expanded_nodes.discard(node_id)
        st.session_state.subgraphs.pop(node_id, None)
        st.info(f"Узел '{clean_label}' свернут.")
    else:
        # раскрываем
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
            st.error(f"Ошибка: {e}")



def main():
    st.set_page_config(page_title="Tech Graph Analyzer", layout="wide")
    st.title("Визуализация технологических зависимостей")
    
    if 'graph_data' not in st.session_state:
        st.session_state.graph_data = None
    if 'search_query' not in st.session_state:
        st.session_state.search_query = ""
    # для расширения графа
    if 'display_graph' not in st.session_state:
        st.session_state.display_graph = {"nodes": [], "edges": []}
    if 'expanded_nodes' not in st.session_state:
        st.session_state.expanded_nodes = set()
    if 'subgraphs' not in st.session_state:
        st.session_state.subgraphs = {}
    if "last_click" not in st.session_state:
        st.session_state.last_click = None
    
    st.subheader("Поиск технологии")

    search_col1, search_col2 = st.columns([5, 1.5], gap="small")

    with search_col1:
        search_query = st.text_input(
            "Введите название технологии",
            placeholder="Например: Kafka, RabbitMQ, PostgreSQL...",
            key="search_input",
            label_visibility="collapsed"
        )

    with search_col2:
        search_button = st.button(
            "Построить граф", 
            use_container_width=True, 
            type="primary",
            key="search_btn"
        )
    
    # обработка поиска 
    if search_button or (search_query and st.session_state.search_query != search_query):
        st.session_state.search_query = search_query
        
        if not search_query.strip():
            st.warning("Пожалуйста, введите название технологии")
            st.session_state.graph_data = None
        else:
            backend = BackendClient()
            
            try:
                with st.spinner("Построение графа зависимостей..."):
                    graph = backend.get_graph(search_query)
                    st.session_state.graph_data = graph
                    # сброс состояния для нового графа
                    st.session_state.display_graph = graph
                    st.session_state.expanded_nodes = set()
                    st.session_state.subgraphs = {}
                    st.success(f"Граф успешно получен для '{search_query}'")
                    st.rerun()
            except NotFoundError:
                st.error(f"Технология '{search_query}' не найдена")
                st.info("Попробуйте другую технологию или проверьте правописание")
                st.session_state.graph_data = None
            except BackendError as e:
                st.error(f"Ошибка подключения к серверу: {str(e)}")
                st.warning("Убедитесь, что бэкенд запущен на http://localhost:8000")
                if st.button("Повторить запрос"):
                    st.rerun()
                st.session_state.graph_data = None
            except ValueError as e:
                st.error(f"Неверный запрос: {str(e)}")
                st.session_state.graph_data = None
    
    # отображение графа
    if st.session_state.graph_data:
        st.divider()
        col_filters, col_graph = st.columns([1, 3])
        
        with col_filters:
            st.subheader("Фильтры")
            
            edge_weight_thresholds = {}
            binary_edge_filters = {}
            
            if WEIGHTED_EDGE_TYPES:
                st.markdown("**Минимальный вес связей:**")
                for edge_type in WEIGHTED_EDGE_TYPES:
                    display_name = EDGE_TYPE_NAMES.get(edge_type, edge_type)
                    threshold = st.slider(
                        f"{display_name}",
                        min_value=0.0,
                        max_value=1.0,
                        value=1.0,
                        step=0.1,
                        key=f"threshold_{edge_type}",
                        format="%.1f"
                    )
                    edge_weight_thresholds[edge_type] = threshold
                st.divider()
            
            if BINARY_EDGE_TYPES:
                st.markdown("**Показывать связи:**")
                for edge_type in BINARY_EDGE_TYPES:
                    display_name = EDGE_TYPE_NAMES.get(edge_type, edge_type)
                    is_checked = st.checkbox(
                        display_name,
                        value=True,
                        key=f"binary_{edge_type}"
                    )
                    binary_edge_filters[edge_type] = is_checked
                st.divider()
            
            st.markdown("**Типы узлов:**")
            node_filters = []
            for node_type, label in NODE_TYPE_FILTERS:
                if st.checkbox(label, value=True, key=f"node_{node_type}"):
                    node_filters.append(node_type)
        
        with col_graph:
            st.subheader("Визуализация графа")
            filtered_nodes = [
                n for n in st.session_state.display_graph["nodes"]
                if n["type"] in node_filters
            ]

            filtered_node_ids = {n["id"] for n in filtered_nodes}

            filtered_edges = []

            for e in st.session_state.display_graph["edges"]:

                edge_type = e.get("type")

                if edge_type in binary_edge_filters:
                    if not binary_edge_filters[edge_type]:
                        continue

                if e["source"] not in filtered_node_ids:
                    continue

                if e["target"] not in filtered_node_ids:
                    continue

                min_weight = edge_weight_thresholds.get(edge_type, 0.0)

                weight = e.get("weight", 1)

                if weight < min_weight:
                    continue

                filtered_edges.append(e)


            agraph_nodes = []

            for n in filtered_nodes:

                node_color = get_node_color(n["type"])

                agraph_nodes.append(
                    Node(
                        id=n["id"],
                        label=n["label"],
                        size=25,
                        color=node_color,
                        font={"color": "white"}
                    )
                )


            agraph_edges = []

            for e in filtered_edges:

                edge_type = e.get("type")

                weight = e.get("weight", 1)

                edge_color = get_edge_color(edge_type)

                width = get_edge_width(weight)

                is_dashed = edge_type in DASHED_EDGE_TYPES

                agraph_edges.append(
                    Edge(
                        source=e["source"],
                        target=e["target"],
                        color=edge_color,
                        width=width,
                        dashes=is_dashed,
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
            selected = agraph(
                nodes=agraph_nodes,
                edges=agraph_edges,
                config=config
            )

            if selected:
                # Извлекаем ID (agraph может вернуть строку или словарь в зависимости от версии)
                node_id = selected["id"] if isinstance(selected, dict) else selected

                # ПРОВЕРКА: Если этот узел был нажат в прошлый раз, ничего не делаем
                if st.session_state.get("last_click") != node_id:
                    node_map = {
                        n["id"]: n["label"]
                        for n in st.session_state.display_graph["nodes"]
                    }

                    if node_id in node_map:
                        # Сохраняем ID текущего клика, чтобы не обрабатывать его повторно при rerun
                        st.session_state.last_click = node_id
                        
                        toggle_node(node_id, node_map[node_id])

                        st.session_state.display_graph = merge_graphs(
                            st.session_state.graph_data["nodes"],
                            st.session_state.graph_data["edges"],
                            st.session_state.expanded_nodes,
                            st.session_state.subgraphs
                        )

                        st.rerun()
            else:
                # Если клика нет (например, нажали на пустое место), сбрасываем last_click
                st.session_state.last_click = None
        # отчет
        st.divider()
        st.subheader("Параметры отчёта")
        
        col_report1, col_report2, col_report3 = st.columns([1, 1, 1], gap="medium")
        
        available_nodes = st.session_state.graph_data.get("nodes", [])
        node_options = {n.get("id"): f"{n.get('label')} ({n.get('type')})" for n in available_nodes}
        
        with col_report1:
            selected_node_ids = st.multiselect(
                "Узлы для отчета",
                options=list(node_options.keys()),
                format_func=lambda x: node_options.get(x, x),
                key="report_nodes",
                help="Оставьте пусто = все узлы"
            )
        
        with col_report2:
            selected_edge_types = st.multiselect(
                "Типы связей для отчета",
                options=EDGE_TYPES,
                format_func=lambda x: EDGE_TYPE_NAMES.get(x, x),
                key="report_edges",
                help="Оставьте пусто = все типы"
            )
        
        with col_report3:
            st.write("")  
            if st.button("Скачать отчет (PDF)", use_container_width=True, type="primary"):
                try:
                    report_gen = ReportGenerator()
                    
                    if not selected_node_ids:
                        nodes_for_report = [n for n in st.session_state.graph_data["nodes"] if n.get("type") in node_filters]
                        node_ids_for_report = None
                    else:
                        nodes_for_report = st.session_state.graph_data["nodes"]
                        node_ids_for_report = selected_node_ids
                    
                    edge_types_for_report = selected_edge_types if selected_edge_types else None
                    
                    pdf_buffer = report_gen.generate_pdf(
                        nodes=nodes_for_report,
                        edges=st.session_state.graph_data.get("edges", []),
                        selected_nodes=node_ids_for_report,
                        selected_edge_types=edge_types_for_report,
                        technology_name=st.session_state.search_query
                    )
                    
                    st.download_button(
                        label="Скачать PDF",
                        data=pdf_buffer,
                        file_name=f"report_{st.session_state.search_query.lower().replace(' ', '_')}.pdf",
                        mime="application/pdf",
                        key="download_report"
                    )
                    st.success("Отчет готов!")
                except Exception as e:
                    st.error(f"Ошибка при формировании отчета: {str(e)}")
                    st.info("Убедитесь, что установлен пакет reportlab: pip install reportlab")
    
    else:
        st.divider()
        st.subheader("Как использовать")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.info("**1. Введите технологию**\n\nНачните с ввода названия технологии в поле поиска выше.\n\n*Примеры:* Kafka, RabbitMQ, PostgreSQL")
        with col2:
            st.info("**2. Настройте фильтры**\n\nИспользуйте ползунки для настройки видимости типов связей.\n\n*0 = скрыть, 1 = показать полностью*")
        with col3:
            st.info("**3. Анализируйте граф**\n\nИзучите связи между технологиями, компаниями и лицензиями.\n\n*Толщина линии = вес связи*")


if __name__ == "__main__":
    main()