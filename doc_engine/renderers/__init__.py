"""Documentation output renderers, split one-class-per-file to stay under
the 200-line-per-file ceiling. Structural split only - no logic changes.

Siblings:
- markdown_renderer.py: MarkdownRenderer
- html_renderer.py: HtmlRenderer
- pdf_renderer.py: PdfRenderer
- docx_renderer.py: DocxRenderer

This __init__.py re-exports all four so external callers keep importing
from `doc_engine.renderers` exactly as before - never import a sibling
module directly.
"""
from .markdown_renderer import MarkdownRenderer
from .html_renderer import HtmlRenderer
from .pdf_renderer import PdfRenderer
from .docx_renderer import DocxRenderer

__all__ = ["MarkdownRenderer", "HtmlRenderer", "PdfRenderer", "DocxRenderer"]
