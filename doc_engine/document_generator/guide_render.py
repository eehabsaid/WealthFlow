"""GuideRenderMixin: renders a single guide across all supported output
formats (Markdown, HTML, PDF, DOCX), including title translation and
progress-status updates. See this package's __init__.py for the sibling
list and composition conventions."""
import os
import time
from datetime import datetime

from ..config import SUPPORTED_FORMATS
from .labels import fixed_labels, guide_type_label


class GuideRenderMixin:
    def _generate_guide(self, guide):
        filtered_nodes = guide.filter_model()
        if not filtered_nodes:
            return
            
        guide_type = guide.get_guide_type()
        guide_dir = self._create_folders(guide_type)
        
        md_path = os.path.join(guide_dir, "markdown", self._get_filename(guide_type, "md"))
        html_path = os.path.join(guide_dir, "html", self._get_filename(guide_type, "html"))
        pdf_path = os.path.join(guide_dir, "pdf", self._get_filename(guide_type, "pdf"))
        docx_path = os.path.join(guide_dir, "docx", self._get_filename(guide_type, "docx"))

        flat_model = self._flatten_tree(filtered_nodes)
        
        # Translate node titles
        for node in flat_model:
            node.title = self._t_title(node.title)
            node.navigation = [self._t_title(x) for x in node.navigation]
            
        translations = getattr(self, "translations", {}) or {}
        app_name = self.manifest.get('application', 'WealthFlow')
        type_label = guide_type_label(translations, guide_type)
        context = {
            **fixed_labels(translations),
            "app_name": app_name,
            "guide_type": type_label,
            "title": f"{app_name} - {type_label}",
            "date": datetime.now().strftime('%Y-%m-%d'),
            "language": self.metadata.get('language', 'EN').upper() if self.metadata else 'EN',
            "theme": self.metadata.get('theme', 'Dark').capitalize() if self.metadata else 'Dark',
            "device": self.metadata.get('device', 'Desktop').capitalize() if self.metadata else 'Desktop',
            "version": self.manifest.get('version', '1.0'),
            "page_title": type_label,
            "is_technical": guide.is_technical()
        }

        self._update_status({
            "status": "RUNNING",
            "current_guide": guide_type.capitalize(),
            "current_page": "Markdown",
            "current_output_format": "Markdown",
            "validation_stage": "Generating Markdown",
            "progress_percent": int(((self.current_guide_idx - 1) / self.total_guides) * 100) + 0,
            "elapsed": int(time.time() - self.start_time)
        })
        if "markdown" in SUPPORTED_FORMATS:
            self.renderers["markdown"].render(flat_model, md_path, context)
            
        self._update_status({
            "current_page": "HTML",
            "current_output_format": "HTML",
            "validation_stage": "Generating HTML",
            "progress_percent": int(((self.current_guide_idx - 1) / self.total_guides) * 100) + 6,
            "elapsed": int(time.time() - self.start_time)
        })
        if "html" in SUPPORTED_FORMATS:
            self.renderers["html"].render(md_path, html_path, context)
            
        self._update_status({
            "current_page": "PDF",
            "current_output_format": "PDF",
            "validation_stage": "Generating PDF",
            "progress_percent": int(((self.current_guide_idx - 1) / self.total_guides) * 100) + 12,
            "elapsed": int(time.time() - self.start_time)
        })
        if "pdf" in SUPPORTED_FORMATS:
            self.renderers["pdf"].render(html_path, pdf_path)
            
        self._update_status({
            "current_page": "DOCX",
            "current_output_format": "DOCX",
            "validation_stage": "Generating DOCX",
            "progress_percent": int(((self.current_guide_idx - 1) / self.total_guides) * 100) + 18,
            "elapsed": int(time.time() - self.start_time)
        })
        if "docx" in SUPPORTED_FORMATS:
            self.renderers["docx"].render(flat_model, docx_path, context)

