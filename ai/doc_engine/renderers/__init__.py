"""Documentation output renderers, split one-class-per-file to stay under
the 200-line-per-file ceiling. Structural split only - no logic changes.

Siblings:
- markdown_renderer.py: MarkdownRenderer
- html_renderer.py: HtmlRenderer
- pdf_renderer.py: PdfRenderer
- docx_renderer.py: DocxRenderer

This __init__.py re-exports all four so external callers keep importing
from `ai.doc_engine.renderers` exactly as before - never import a sibling
module directly.
"""
from ai.doc_engine.renderers.markdown_renderer import MarkdownRenderer
from ai.doc_engine.renderers.html_renderer import HtmlRenderer
from ai.doc_engine.renderers.pdf_renderer import PdfRenderer
from ai.doc_engine.renderers.docx_renderer import DocxRenderer

__all__ = ["MarkdownRenderer", "HtmlRenderer", "PdfRenderer", "DocxRenderer"]
