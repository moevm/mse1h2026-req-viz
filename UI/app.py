# app.py
import streamlit as st
import pandas as pd
from config import NODE_TYPE_FILTERS, EDGE_TYPES, EDGE_TYPE_NAMES
from services import BackendClient, NotFoundError, BackendError
from visualization import create_graph_visualization
from report_generator import ReportGenerator


def main():
    st.set_page_config(
        page_title="Tech Graph Analyzer",
        layout="wide"
    )
    
    st.title("Визуализация технологических зависимостей")
    
    if 'graph_data' not in st.session_state:
        st.session_state.graph_data = None
    if 'search_query' not in st.session_state:
        st.session_state.search_query = ""
    
    # поиск
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
    
    # Обработка поиска
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
    
    if st.session_state.graph_data:
        st.divider()
        col_filters, col_graph = st.columns([1, 3])
        
        # Панель фильтрации 
        with col_filters:
            st.subheader("Фильтры")
            
            st.markdown("**Минимальный вес связей:**")
            
            edge_weight_thresholds = {}
            for edge_type in EDGE_TYPES:
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
            
            st.markdown("**Типы узлов:**")
            node_filters = []
            for node_type, label in NODE_TYPE_FILTERS:
                if st.checkbox(label, value=True, key=f"node_{node_type}"):
                    node_filters.append(node_type)
        
        # Визуализация графа
        with col_graph:
            st.subheader("Визуализация графа")
            
            try:
                html_viz = create_graph_visualization(
                    nodes=st.session_state.graph_data["nodes"],
                    edges=st.session_state.graph_data["edges"],
                    node_filters=node_filters,
                    edge_weight_thresholds=edge_weight_thresholds  
                )
                st.components.v1.html(html_viz, height=550, scrolling=False)
            except Exception as e:
                st.error(f"Ошибка визуализации: {str(e)}")
                st.warning("Попробуйте нажать 'Обновить визуализацию' или перезагрузить страницу.")
        
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