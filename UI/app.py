import streamlit as st
import pandas as pd
from config import NODE_TYPE_FILTERS, EDGE_TYPES, EDGE_TYPE_NAMES, WEIGHTED_EDGE_TYPES, BINARY_EDGE_TYPES
from services import BackendClient, NotFoundError, BackendError
from visualization import create_graph_visualization
from report_generator import ReportGenerator
from concurrent.futures import ThreadPoolExecutor, as_completed

executor = ThreadPoolExecutor(max_workers=10)

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
    """Главная функция Streamlit приложения для визуализации графов технологий."""
    st.set_page_config(
        page_title="Tech Graph Analyzer",
        layout="wide"
    )
    
    st.title("Визуализация технологических зависимостей")

    if 'loaded_graphs' not in st.session_state:
        st.session_state.loaded_graphs = {} # Ключ: имя технологии, Значение: данные графа
    if 'search_query' not in st.session_state:
        st.session_state.search_query = ""
    
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
        button_container = st.container()
        with button_container:
            search_button = st.button(
                "Построить граф", 
                use_container_width=True, 
                type="primary",
                key="search_btn"
            )
    
    if search_button or (search_query and st.session_state.search_query != search_query):
        st.session_state.search_query = search_query
        technologies = [t.strip() for t in search_query.split(",") if t.strip()]
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
                    future_to_tech = {executor.submit(fetch_single_graph, backend, tech): tech for tech in technologies}

                    completed_count = 0
                    total_count = len(technologies)

                    for future in as_completed(future_to_tech):
                        tech_name = future_to_tech[future]
                        try:
                            result = future.result()

                            if result["error"]:
                                if result["error"] == "not_found":
                                    st.error(f"Технология '{result['name']}' не найдена.")
                                else:
                                    st.error(f"Ошибка при загрузке '{result['name']}': {result['error']}")
                            else:
                                # Сохраняем успешный результат в состояние
                                st.session_state.loaded_graphs[result["name"]] = result["data"]
                                st.success(f"Граф для '{result['name']}' загружен!")

                        except Exception as exc:
                            st.error(f"Критическая ошибка для {tech_name}: {exc}")

                        completed_count += 1
                        progress_bar.progress(completed_count / total_count)
                        status_text.text(f"Загружено {completed_count} из {total_count}")
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

    if st.session_state.loaded_graphs:
        st.divider()

        for tech_name, graph_data in st.session_state.loaded_graphs.items():
            if not graph_data:
                continue

            # Виртуальная рамка для каждого графа, чтобы отделить их друг от друга
            with st.container(border=True):
                st.subheader(f"Граф: {tech_name}")

                col_filters, col_graph = st.columns([1, 3], gap="large")

                safe_tech_name = tech_name.replace(" ", "_").replace("-", "_").lower()

                with col_filters:
                    st.markdown("**Фильтры связей**")

                    edge_weight_thresholds = {}
                    binary_edge_filters = {}

                    if WEIGHTED_EDGE_TYPES:
                        for edge_type in WEIGHTED_EDGE_TYPES:
                            display_name = EDGE_TYPE_NAMES.get(edge_type, edge_type)
                            threshold = st.slider(
                                f"{display_name}",
                                min_value=0.0,
                                max_value=1.0,
                                value=1.0,
                                step=0.1,
                                key=f"thr_{edge_type}_{safe_tech_name}",
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
                                key=f"bin_{edge_type}_{safe_tech_name}"
                            )
                            binary_edge_filters[edge_type] = is_checked
                    st.divider()

                    st.markdown("**Типы узлов:**")
                    node_filters = []
                    for node_type, label in NODE_TYPE_FILTERS:
                        if st.checkbox(label, value=True, key=f"node_{node_type}_{safe_tech_name}"):
                            node_filters.append(node_type)

                with col_graph:
                    st.markdown("**Визуализация**")
                    try:
                        html_viz = create_graph_visualization(
                            nodes=graph_data["nodes"],
                            edges=graph_data["edges"],
                            node_filters=node_filters,
                            edge_weight_thresholds=edge_weight_thresholds,
                            binary_edge_filters=binary_edge_filters
                        )
                        st.components.v1.html(html_viz, height=550, scrolling=False)
                    except Exception as e:
                        st.error(f"Ошибка визуализации: {str(e)}")


                st.divider()
                st.subheader("Параметры отчёта")

                col_report1, col_report2, col_report3 = st.columns([1, 1, 1], gap="medium")

                available_nodes = graph_data.get("nodes", [])
                node_options = {n.get("id"): f"{n.get('label')} ({n.get('type')})" for n in available_nodes}

                with col_report1:
                    selected_node_ids = st.multiselect(
                        "Узлы для отчета",
                        options=list(node_options.keys()),
                        format_func=lambda x: node_options.get(x, x),
                        key=f"rep_nodes_{safe_tech_name}",
                        help="Оставьте пусто = все узлы"
                    )

                with col_report2:
                    selected_edge_types = st.multiselect(
                        "Типы связей для отчета",
                        options=EDGE_TYPES,
                        format_func=lambda x: EDGE_TYPE_NAMES.get(x, x),
                        key=f"rep_edges_{safe_tech_name}",
                        help="Оставьте пусто = все типы"
                    )

                with col_report3:
                    st.write("")
                    gen_btn_key = f"btn_gen_{safe_tech_name}"
                    if st.button("Скачать отчет (PDF)", use_container_width=True, type="primary", key=gen_btn_key):
                        try:
                            report_gen = ReportGenerator()

                            if not selected_node_ids:
                                nodes_for_report = [n for n in available_nodes if n.get("type") in node_filters]
                                node_ids_for_report = None
                            else:
                                nodes_for_report = available_nodes
                                node_ids_for_report = selected_node_ids

                            edge_types_for_report = selected_edge_types if selected_edge_types else None

                            pdf_buffer = report_gen.generate_pdf(
                                nodes=nodes_for_report,
                                edges=graph_data.get("edges", []),
                                selected_nodes=node_ids_for_report,
                                selected_edge_types=edge_types_for_report,
                                technology_name=tech_name # Используем конкретное имя технологии
                            )

                            st.download_button(
                                label="Скачать PDF",
                                data=pdf_buffer,
                                file_name=f"report_{tech_name.lower().replace(' ', '_')}.pdf",
                                mime="application/pdf",
                                key=f"dl_{safe_tech_name}"
                            )
                            st.success(" Отчет готов!")
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