# report_generator.py
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


def _setup_fonts():
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


class ReportGenerator:
    
    def __init__(self, title: str = "Отчет по технологическим зависимостям"):
        self.title = title
        self.font_name = _setup_fonts()
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        self.styles.add(ParagraphStyle(
            name='Title_Custom',
            parent=self.styles['Heading1'],
            fontSize=24,
            fontName=self.font_name,
            textColor=colors.HexColor('#1f77b4'),
            spaceAfter=20,
            alignment=1  
        ))
        self.styles.add(ParagraphStyle(
            name='Heading_Custom',
            parent=self.styles['Heading2'],
            fontSize=14,
            fontName=self.font_name,
            textColor=colors.HexColor('#2ca02c'),
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
        
        # Дата создания
        timestamp = Paragraph(
            f"Дата: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}",
            self.styles['Normal']
        )
        story.append(timestamp)
        story.append(Spacer(1, 0.3 * inch))
        
        # Таблица узлов
        story.append(Paragraph("Узлы (Вершины)", self.styles['Heading_Custom']))
        nodes_table = self._create_nodes_table(filtered_nodes)
        story.append(nodes_table)
        story.append(Spacer(1, 0.2 * inch))
        
        # Таблица связей
        story.append(Paragraph("Связи (Рёбра)", self.styles['Heading_Custom']))
        edges_table = self._create_edges_table(filtered_edges, filtered_nodes)
        story.append(edges_table)
        story.append(Spacer(1, 0.2 * inch))
        
        # Статистика
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
        """Создаёт таблицу узлов"""
        data = [["Название", "Тип"]]
        
        for node in nodes:
            data.append([
                node.get('label', 'N/A')[:40],
                node.get('type', 'N/A')
            ])
        
        table = Table(data, colWidths=[4*inch, 2*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2ca02c')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), self.font_name),
            ('FONTNAME', (0, 1), (-1, -1), self.font_name),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
        ]))
        
        return table
    
    def _create_edges_table(
        self,
        edges: List[Dict[str, Any]],
        nodes: List[Dict[str, Any]]
    ) -> Table:
        node_map = {n.get('id'): n for n in nodes}
        
        data = [["Источник", "Цель", "Тип связи", "Вес"]]
        
        for edge in edges:
            source_node = node_map.get(edge.get('source'), {})
            target_node = node_map.get(edge.get('target'), {})
            
            data.append([
                source_node.get('label', edge.get('source', 'N/A'))[:25],
                target_node.get('label', edge.get('target', 'N/A'))[:25],
                edge.get('type', 'N/A'),
                f"{edge.get('weight', 0):.2f}"
            ])
        
        table = Table(data, colWidths=[2*inch, 2*inch, 1.5*inch, 1*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f77b4')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (3, 0), (3, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), self.font_name),
            ('FONTNAME', (0, 1), (-1, -1), self.font_name),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.lightblue),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightcyan])
        ]))
        
        return table
    
    def _create_stats_table(
        self,
        nodes: List[Dict[str, Any]],
        edges: List[Dict[str, Any]]
    ) -> Table:
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
            ["Типы узлов", ", ".join(node_types.keys())],
            ["Типы связей", ", ".join(edge_types.keys())],
        ]
        
        for node_type, count in node_types.items():
            data.append([f"  Узлов типа '{node_type}'", str(count)])
        
        for edge_type, count in edge_types.items():
            data.append([f"  Связей типа '{edge_type}'", str(count)])
        
        table = Table(data, colWidths=[3.5*inch, 2.5*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#ff7f0e')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, -1), self.font_name),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.lightyellow),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightyellow])
        ]))
        
        return table
