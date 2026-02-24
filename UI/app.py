# app.py
import streamlit as st
import pandas as pd
from config import NODE_TYPE_FILTERS, EDGE_TYPES, EDGE_TYPE_NAMES
from services import MockBackendService
from visualization import create_graph_visualization


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
    
    # СЕКЦИЯ ПОИСКА
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
        backend = MockBackendService()
        
        tech_info = backend.search_technology(search_query)
        
        if tech_info:
            st.success(f"Найдено: **{tech_info['name']}** ({tech_info['category']})")
            with st.spinner("Построение графа зависимостей..."):
                st.session_state.graph_data = backend.build_graph(search_query)
                st.rerun()
        else:
            st.error(f"Технология '{search_query}' не найдена. Попробуйте: Kafka, RabbitMQ, PostgreSQL, Docker, Kubernetes")
            st.session_state.graph_data = None
    
    if st.session_state.graph_data:
        st.divider()
        col_filters, col_graph = st.columns([1, 3])
        
        # ПАНЕЛЬ ФИЛЬТРАЦИИ
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
            
            # Фильтры по типам узлов
            st.markdown("**Типы узлов:**")
            node_filters = []
            for node_type, label in NODE_TYPE_FILTERS:
                if st.checkbox(label, value=True, key=f"node_{node_type}"):
                    node_filters.append(node_type)
            
        
        # ВИЗУАЛИЗАЦИЯ ГРАФА
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
        
        
        col_export1, col_export2, col_export3 = st.columns([1, 2, 1])
        with col_export2:
            if st.button("Загрузить отчет (PDF)", use_container_width=True, type="secondary"):
                st.info("Отчет успешно загружен.")
    
    
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