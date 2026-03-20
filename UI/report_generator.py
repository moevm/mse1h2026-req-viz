from typing import Dict, List, Any
from datetime import datetime
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os
from config import NODE_TYPE_TRANSLATIONS, EDGE_TYPE_TRANSLATIONS, BINARY_EDGE_TYPES


class ReportGenerator:
    """Генератор PDF-отчетов на основе данных графа с поддержкой русской локализации."""
    
    @staticmethod
    def _setup_fonts():
        """Инициализирует поддержку шрифтов Cyrillic для PDF."""
        try:
            font_paths = [
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
                "/System/Library/Fonts/Arial.ttf",  
            ]
            
            for font_path in font_paths:
                if os.path.exists(font_path):
                    try:
                        pdfmetrics.registerFont(TTFont('CustomFont', font_path))
                        return 'CustomFont'
                    except Exception:
                        continue
        except Exception:
            pass
        
        return 'Helvetica'
    
    def __init__(self, title: str = "Отчет по технологическим зависимостям"):
        self.title = title
        self.font_name = self._setup_fonts()
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Создаёт пользовательские стили для заголовков и текста в PDF."""
        self.styles.add(ParagraphStyle(
            name='Title_Custom',
            parent=self.styles['Heading1'],
            fontSize=24,
            fontName=self.font_name,
            spaceAfter=20,
            alignment=1  
        ))
        self.styles.add(ParagraphStyle(
            name='Heading_Custom',
            parent=self.styles['Heading2'],
            fontSize=14,
            fontName=self.font_name,
            spaceAfter=12,
            spaceBefore=12
        ))
        try:
            self.styles['Normal'].fontName = self.font_name
        except Exception:
            pass
    
    def generate_pdf(
        self,
        nodes: List[Dict[str, Any]],
        edges: List[Dict[str, Any]],
        selected_nodes: List[str] | None = None,
        selected_edge_types: List[str] | None = None,
        technology_name: str = "Unknown"
    ) -> BytesIO:
        """Генерирует PDF-отчет с таблицами узлов, связей и статистики."""
        filtered_nodes = self._filter_nodes(nodes, selected_nodes)
        filtered_edges = self._filter_edges(edges, selected_edge_types, filtered_nodes)
        
        pdf_buffer = BytesIO()
        doc = SimpleDocTemplate(
            pdf_buffer,
            pagesize=A4,
            rightMargin=0.5 * inch,
            leftMargin=0.5 * inch,
            topMargin=0.5 * inch,
            bottomMargin=0.5 * inch
        )
        
        story = []
        
        title = Paragraph(f"Анализ: {technology_name}", self.styles['Title_Custom'])
        story.append(title)
        
        timestamp = Paragraph(
            f"Дата: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}",
            self.styles['Normal']
        )
        story.append(timestamp)
        story.append(Spacer(1, 0.3 * inch))
        
        story.append(Paragraph("Узлы", self.styles['Heading_Custom']))
        nodes_table = self._create_nodes_table(filtered_nodes)
        story.append(nodes_table)
        story.append(Spacer(1, 0.2 * inch))
        
        story.append(Paragraph("Связи", self.styles['Heading_Custom']))
        edges_table = self._create_edges_table(filtered_edges, filtered_nodes)
        story.append(edges_table)
        story.append(Spacer(1, 0.2 * inch))
        
        story.append(Paragraph("Статистика", self.styles['Heading_Custom']))
        stats_table = self._create_stats_table(filtered_nodes, filtered_edges)
        story.append(stats_table)
        
        doc.build(story)
        pdf_buffer.seek(0)
        return pdf_buffer
    
    def _filter_nodes(
        self,
        nodes: List[Dict[str, Any]],
        selected_node_ids: List[str] | None
    ) -> List[Dict[str, Any]]:
        """Фильтрует узлы по выбранным ID."""
        if selected_node_ids is None:
            return nodes
        selected_set = set(selected_node_ids)
        return [n for n in nodes if n.get('id') in selected_set]
    
    def _filter_edges(
        self,
        edges: List[Dict[str, Any]],
        selected_types: List[str] | None,
        filtered_nodes: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Фильтрует связи по типам и наличию узлов в графе."""
        node_ids = {n.get('id') for n in filtered_nodes}
        result = []
        
        for edge in edges:
            if edge.get('source') not in node_ids or edge.get('target') not in node_ids:
                continue
            
            if selected_types is not None:
                if edge.get('type') not in selected_types:
                    continue
            
            result.append(edge)
        
        return result
    
    def _create_nodes_table(self, nodes: List[Dict[str, Any]]) -> Table:
        """Создаёт таблицу узлов с названиями и типами."""
        data = [["Название", "Тип"]]
        
        for node in nodes:
            node_type = node.get('type', 'N/A')
            translated_type = NODE_TYPE_TRANSLATIONS.get(node_type, node_type)
            data.append([
                node.get('label', 'N/A')[:40],
                translated_type
            ])
        
        table = Table(data, colWidths=[4*inch, 2*inch])
        table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), self.font_name),
            ('FONTNAME', (0, 1), (-1, -1), self.font_name),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
        ]))
        
        return table
    
    def _create_edges_table(
        self,
        edges: List[Dict[str, Any]],
        nodes: List[Dict[str, Any]]
    ) -> Table:
        """Создаёт таблицу связей с источником, целью, типом и весом/статусом."""
        node_map = {n.get('id'): n for n in nodes}
        
        data = [["Источник", "Цель", "Тип связи", "Статус"]]
        
        for edge in edges:
            source_node = node_map.get(edge.get('source'), {})
            target_node = node_map.get(edge.get('target'), {})
            edge_type = edge.get('type', 'N/A')
            translated_edge_type = EDGE_TYPE_TRANSLATIONS.get(edge_type, edge_type)
            
            if edge_type in BINARY_EDGE_TYPES:
                status = "Да"
            else:
                status = f"{edge.get('weight', 0):.2f}"
            
            data.append([
                source_node.get('label', edge.get('source', 'N/A'))[:25],
                target_node.get('label', edge.get('target', 'N/A'))[:25],
                translated_edge_type,
                status
            ])
        
        table = Table(data, colWidths=[1.8*inch, 1.5*inch, 2.2*inch, 0.8*inch])
        table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (3, 0), (3, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), self.font_name),
            ('FONTNAME', (0, 1), (-1, -1), self.font_name),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
        ]))
        
        return table
    
    def _create_stats_table(
        self,
        nodes: List[Dict[str, Any]],
        edges: List[Dict[str, Any]]
    ) -> Table:
        """Создаёт таблицу статистики с количеством и типами узлов и связей."""
        node_types = {}
        for node in nodes:
            node_type = node.get('type', 'Unknown')
            node_types[node_type] = node_types.get(node_type, 0) + 1
        
        edge_types = {}
        for edge in edges:
            edge_type = edge.get('type', 'Unknown')
            edge_types[edge_type] = edge_types.get(edge_type, 0) + 1
        
        data = [
            ["Метрика", "Значение"],
            ["Всего узлов", str(len(nodes))],
            ["Всего связей", str(len(edges))],
            ["Типы узлов", ", ".join([NODE_TYPE_TRANSLATIONS.get(t, t) for t in node_types.keys()])],
            ["Типы связей", ", ".join([EDGE_TYPE_TRANSLATIONS.get(t, t) for t in edge_types.keys()])],
        ]
        
        for node_type, count in node_types.items():
            translated_type = NODE_TYPE_TRANSLATIONS.get(node_type, node_type)
            data.append([f"  {translated_type}", str(count)])
        
        for edge_type, count in edge_types.items():
            translated_type = EDGE_TYPE_TRANSLATIONS.get(edge_type, edge_type)
            data.append([f"  {translated_type}", str(count)])
        
        table = Table(data, colWidths=[2.5*inch, 3.5*inch])
        table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, -1), self.font_name),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
        ]))
        
        return table
