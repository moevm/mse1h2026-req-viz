import streamlit as st
import pandas as pd

from config import NODE_TYPE_FILTERS, EDGE_TYPES, EDGE_TYPE_NAMES, WEIGHTED_EDGE_TYPES, BINARY_EDGE_TYPES
from services import BackendClient, NotFoundError, BackendError
from report_generator import ReportGenerator
from streamlit_agraph import agraph
from visualization import create_graph_visualization
from concurrent.futures import ThreadPoolExecutor, as_completed

executor = ThreadPoolExecutor(max_workers=10)

#логика расширения графа
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



def fetch_single_graph(backend, tech_name: str):
    """Функция для выполнения в отдельном потоке"""
    try:
        graph = backend.get_graph(tech_name.strip())
        return {"name": tech_name.strip(), "data": graph, "error": None}
    except NotFoundError:
        return {"name": tech_name.strip(), "data": None, "error": "not_found"}
    except Exception as e:
        return {"name": tech_name.strip(), "data": None, "error": str(e)}

def main():
    st.set_page_config(page_title="Tech Graph Analyzer", layout="wide")
    st.title("Визуализация технологических зависимостей")
    
    if 'loaded_graphs' not in st.loaded_graphs:
        st.session_state.loaded_graphs = {} # Ключ: имя технологии, Значение: данные графа
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
        technologies = [t.strip() for t in search_query.split(",") if t.strip()]
        # Удаляем дубликаты. Будет использовано последнее вхождение слова
        technologies = list({t.lower(): t for t in technologies}.values())
        
        if not search_query.strip():
            st.warning("Пожалуйста, введите название технологии")
            st.session_state.graph_data = None
        else:
            backend = BackendClient()
            progress_bar = st.progress(0)
            status_text = st.empty()
            
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


            agraph_nodes, agraph_edges, config = create_graph_visualization(
                nodes=st.session_state.display_graph["nodes"],
                edges=st.session_state.display_graph["edges"],
                node_filters=node_filters,
                edge_weight_thresholds=edge_weight_thresholds,
                binary_edge_filters=binary_edge_filters
            )

            selected = agraph(
                nodes=agraph_nodes,
                edges=agraph_edges,
                config=config
            )
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
                            st.session_state.graph_data["edges"],
                            st.session_state.expanded_nodes,
                            st.session_state.subgraphs
                        )

                        st.rerun()
            else:
                st.session_state.last_click = None
        # отчет
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
                        selected_node_set = {n.get('id') for n in nodes_for_report}
                    else:
                        nodes_for_report = st.session_state.graph_data["nodes"]
                        node_ids_for_report = selected_node_ids
                        selected_node_set = set(selected_node_ids)

                    all_edges = st.session_state.graph_data.get("edges", [])
                    edge_types_for_report = selected_edge_types if selected_edge_types else None
                    edges_for_report = []
                    for e in all_edges:
                        if e.get('source') not in selected_node_set and e.get('target') not in selected_node_set:
                            continue
                        if edge_types_for_report and e.get('type') not in edge_types_for_report:
                            continue
                        edges_for_report.append(e)

                    backend = BackendClient()
                    payload = {
                        "nodes": nodes_for_report,
                        "edges": edges_for_report,
                        "meta": {"technology": st.session_state.search_query}
                    }

                    try:
                        resp = backend.generate_report(payload)
                    except Exception as be:
                        st.warning(f"Не удалось обратиться к backend: {str(be)} — сгенерируем отчет локально.")
                        pdf_buffer = report_gen.generate_pdf(
                            nodes=nodes_for_report,
                            edges=edges_for_report,
                            selected_nodes=node_ids_for_report,
                            selected_edge_types=edge_types_for_report,
                            technology_name=st.session_state.search_query
                        )
                        st.download_button(
                            label="Скачать PDF",
                            data=pdf_buffer,
                            file_name=f"report_{st.session_state.search_query.lower().replace(' ', '_')}.pdf",
                            mime="application/pdf",
                            key="download_report_local"
                        )
                        st.success("Отчет готов")
                   
                    content_type = resp.headers.get('content-type', '') if resp is not None else ''
                    if resp.status_code == 200 and content_type.startswith('application/json'):
                        try:
                            resp_json = resp.json()
                        except Exception:
                            st.error("Backend вернул некорректный JSON. Выполняю локальную генерацию.")
                            resp_json = None

                        if resp_json and isinstance(resp_json, dict) and 'nodes' in resp_json and 'edges' in resp_json:
                            pdf_buffer = report_gen.generate_pdf(
                                nodes=resp_json['nodes'],
                                edges=resp_json['edges'],
                                selected_nodes=node_ids_for_report,
                                selected_edge_types=edge_types_for_report,
                                technology_name=st.session_state.search_query
                            )
                            st.download_button(
                                label="Скачать PDF",
                                data=pdf_buffer,
                                file_name=f"report_{st.session_state.search_query.lower().replace(' ', '_')}.pdf",
                                mime="application/pdf",
                                key="download_report_backend_json"
                            )
                            st.success("Отчет готов")
                        elif 'report_markdown' in resp_json:
                            pdf_buffer = report_gen.generate_pdf(
                                nodes=nodes_for_report,
                                edges=edges_for_report,
                                selected_nodes=node_ids_for_report,
                                selected_edge_types=edge_types_for_report,
                                technology_name=st.session_state.search_query,
                                additional_content=resp_json['report_markdown']
                            )
                            st.download_button(
                                label="Скачать PDF",
                                data=pdf_buffer,
                                file_name=f"report_{st.session_state.search_query.lower().replace(' ', '_')}.pdf",
                                mime="application/pdf",
                                key="download_report_with_backend_content"
                            )
                            st.success("Отчет готов")
                        else:
                            st.error("Backend вернул неожиданный формат ответа. Отображаю содержимое ответа в отчете.")
                            st.markdown("### Ответ от Backend")
                            st.markdown(f"```json\n{resp.text}\n```")

                            pdf_buffer = report_gen.generate_pdf(
                                nodes=nodes_for_report,
                                edges=edges_for_report,
                                selected_nodes=node_ids_for_report,
                                selected_edge_types=edge_types_for_report,
                                technology_name=st.session_state.search_query
                            )
                            st.download_button(
                                label="Скачать PDF",
                                data=pdf_buffer,
                                file_name=f"report_{st.session_state.search_query.lower().replace(' ', '_')}.pdf",
                                mime="application/pdf",
                                key="download_report_unexpected"
                            )
                    else:
                        st.warning(f"Backend вернул статус {resp.status_code}. Выполняю локальную генерацию.")
                        pdf_buffer = report_gen.generate_pdf(
                            nodes=nodes_for_report,
                            edges=edges_for_report,
                            selected_nodes=node_ids_for_report,
                            selected_edge_types=edge_types_for_report,
                            technology_name=st.session_state.search_query
                        )
                        st.download_button(
                            label="Скачать PDF",
                            data=pdf_buffer,
                            file_name=f"report_{st.session_state.search_query.lower().replace(' ', '_')}.pdf",
                            mime="application/pdf",
                            key="download_report_error_fallback"
                        )

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