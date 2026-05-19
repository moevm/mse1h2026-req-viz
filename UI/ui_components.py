import streamlit as st
from config import NODE_TYPE_FILTERS, EDGE_TYPES, EDGE_TYPE_NAMES, WEIGHTED_EDGE_TYPES, BINARY_EDGE_TYPES

def render_search_bar():
    """Рендерит строку ввода поиска технологии."""
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
    return search_query, search_button

def render_filters():
    """Рендерит сайдбар/колонку фильтрации узлов и ребер графа."""
    st.subheader("Фильтры")
    
    edge_weight_thresholds = {}
    binary_edge_filters = {}
    
    if WEIGHTED_EDGE_TYPES:
        st.markdown("**Минимальный вес связей:**")
        for edge_type in WEIGHTED_EDGE_TYPES:
            display_name = EDGE_TYPE_NAMES.get(edge_type, edge_type)
            threshold = st.slider(
                f"{display_name}",
                min_value=0.0, max_value=1.0, value=1.0, step=0.1,
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
                display_name, value=True, key=f"binary_{edge_type}"
            )
            binary_edge_filters[edge_type] = is_checked
        st.divider()
    
    st.markdown("**Типы узлов:**")
    node_filters = []
    for node_type, label in NODE_TYPE_FILTERS:
        if st.checkbox(label, value=True, key=f"node_{node_type}"):
            node_filters.append(node_type)
            
    return edge_weight_thresholds, binary_edge_filters, node_filters

def render_report_selectors(available_nodes):
    """
    Отображает селекторы параметров отчёта и кнопку генерации в одну строку
    """
    st.subheader("Параметры отчёта")
    
    col_report1, col_report2, col_report3 = st.columns([1, 1, 1], gap="medium")
    
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
        st.markdown("<div style='padding-top: 28px;'></div>", unsafe_allow_html=True)
        generate_clicked = st.button(
            "Сформировать отчет", 
            use_container_width=True, 
            type="primary",
            key="generate_report_btn"
        )
    
    return selected_node_ids, selected_edge_types, generate_clicked

def render_welcome_screen():
    """Рендерит приветственный экран с инструкцией по использованию."""
    st.divider()
    st.subheader("Как использовать")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.info("**1. Введите технологию**\n\nНачните с ввода названия технологии в поле поиска выше.\n\n*Примеры:* Kafka, RabbitMQ, PostgreSQL")
    with col2:
        st.info("**2. Настройте фильтры**\n\nИспользуйте ползунки для настройки видимости типов связей.\n\n*0 = скрыть, 1 = показать полностью*")
    with col3:
        st.info("**3. Анализируйте граф**\n\nИзучите связи между технологиями, компаниями и лицензиями.\n\n*Толщина линии = вес связи*")