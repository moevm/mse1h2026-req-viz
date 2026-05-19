import streamlit as st

from services import BackendClient, NotFoundError, BackendError
from report_generator import ReportGenerator
from streamlit_agraph import agraph
from visualization import create_graph_visualization

# Импорт наших новых модулей
from state_manager import initialize_session_state, reset_graph_state
from graph_operations import assign_initial_positions
from graph_handler import process_graph_selection
from ui_components import (
    render_search_bar,
    render_filters,
    render_report_selectors,
    render_welcome_screen
)

def main():
    st.set_page_config(page_title="Tech Graph Analyzer", layout="wide")
    st.title("Визуализация технологических зависимостей")
    
    initialize_session_state()
    
    search_query, search_button = render_search_bar()
    
    # Обработка поисковых запросов к API бэкенда
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
                    graph["nodes"] = assign_initial_positions(graph["nodes"])
                    # Сбрасываем старое дерево и устанавливаем новые данные
                    reset_graph_state(graph)
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
    
    # основной блок отрисовки (если данные загружены)
    if st.session_state.graph_data:
        st.divider()
        col_filters, col_graph = st.columns([1, 3])
        
        with col_filters:
            edge_weight_thresholds, binary_edge_filters, node_filters = render_filters()
        
        with col_graph:
            st.subheader("Визуализация графа")
            
            agraph_nodes, agraph_edges, config = create_graph_visualization(
                nodes=st.session_state.display_graph["nodes"],
                edges=st.session_state.display_graph["edges"],
                node_filters=node_filters,
                edge_weight_thresholds=edge_weight_thresholds,
                binary_edge_filters=binary_edge_filters
            )

            selected = agraph(nodes=agraph_nodes, edges=agraph_edges, config=config)
            
            process_graph_selection(selected)
            
        available_nodes = st.session_state.graph_data.get("nodes", [])
        selected_node_ids, selected_edge_types, generate_clicked = render_report_selectors(available_nodes)
        
        if generate_clicked:
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
                        nodes=nodes_for_report, edges=edges_for_report,
                        selected_nodes=node_ids_for_report, selected_edge_types=edge_types_for_report,
                        technology_name=st.session_state.search_query
                    )
                    st.download_button(
                        label="Скачать PDF", data=pdf_buffer,
                        file_name=f"report_{st.session_state.search_query.lower().replace(' ', '_')}.pdf",
                        mime="application/pdf", key="download_report_local"
                    )
                    st.success("Отчет готов")
                    return
               
                content_type = resp.headers.get('content-type', '') if resp is not None else ''
                if resp.status_code == 200 and content_type.startswith('application/json'):
                    try:
                        resp_json = resp.json()
                    except Exception:
                        st.error("Backend вернул некорректный JSON. Выполняю локальную генерацию.")
                        resp_json = None

                    if resp_json and isinstance(resp_json, dict) and 'nodes' in resp_json and 'edges' in resp_json:
                        pdf_buffer = report_gen.generate_pdf(
                            nodes=resp_json['nodes'], edges=resp_json['edges'],
                            selected_nodes=node_ids_for_report, selected_edge_types=edge_types_for_report,
                            technology_name=st.session_state.search_query
                        )
                        st.download_button(
                            label="Скачать PDF", data=pdf_buffer,
                            file_name=f"report_{st.session_state.search_query.lower().replace(' ', '_')}.pdf",
                            mime="application/pdf", key="download_report_backend_json"
                        )
                        st.success("Отчет готов")
                    elif 'report_markdown' in resp_json:
                        pdf_buffer = report_gen.generate_pdf(
                            nodes=nodes_for_report, edges=edges_for_report,
                            selected_nodes=node_ids_for_report, selected_edge_types=edge_types_for_report,
                            technology_name=st.session_state.search_query,
                            additional_content=resp_json['report_markdown']
                        )
                        st.download_button(
                            label="Скачать PDF", data=pdf_buffer,
                            file_name=f"report_{st.session_state.search_query.lower().replace(' ', '_')}.pdf",
                            mime="application/pdf", key="download_report_with_backend_content"
                        )
                        st.success("Отчет готов")
                    else:
                        st.error("Backend вернул неожиданный формат ответа. Отображаю содержимое ответа в отчете.")
                        st.markdown("### Ответ от Backend")
                        st.markdown(f"```json\n{resp.text}\n```")

                        pdf_buffer = report_gen.generate_pdf(
                            nodes=nodes_for_report, edges=edges_for_report,
                            selected_nodes=node_ids_for_report, selected_edge_types=edge_types_for_report,
                            technology_name=st.session_state.search_query
                        )
                        st.download_button(
                            label="Скачать PDF", data=pdf_buffer,
                            file_name=f"report_{st.session_state.search_query.lower().replace(' ', '_')}.pdf",
                            mime="application/pdf", key="download_report_unexpected"
                        )
                else:
                    st.warning(f"Backend вернул статус {resp.status_code}. Выполняю локальную генерацию.")
                    pdf_buffer = report_gen.generate_pdf(
                        nodes=nodes_for_report, edges=edges_for_report,
                        selected_nodes=node_ids_for_report, selected_edge_types=edge_types_for_report,
                        technology_name=st.session_state.search_query
                    )
                    st.download_button(
                        label="Скачать PDF", data=pdf_buffer,
                        file_name=f"report_{st.session_state.search_query.lower().replace(' ', '_')}.pdf",
                        mime="application/pdf", key="download_report_error_fallback"
                    )

            except Exception as e:
                st.error(f"Ошибка при формировании отчета: {str(e)}")
                st.info("Убедитесь, что установлен пакет reportlab: pip install reportlab")
    else:
        render_welcome_screen()

if __name__ == "__main__":
    main()