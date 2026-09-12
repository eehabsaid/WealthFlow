"""PdfRenderer: delegates HTML-to-PDF rendering to the active Playwright
backend strategy. See this package's __init__.py for the sibling list."""
import logging

logger = logging.getLogger(__name__)


class PdfRenderer:
    """
    Renders HTML documentation into PDF format.
    Delegates PDF rendering to the active PlaywrightBackend strategy.
    """
    def render(self, html_path, pdf_path):
        from ..playwright_engine import get_playwright_backend
        backend = get_playwright_backend()
        success = backend.render_pdf(html_path, pdf_path)
        if not success:
            logger.error(f"PDF generation failed using {backend.__class__.__name__}")



