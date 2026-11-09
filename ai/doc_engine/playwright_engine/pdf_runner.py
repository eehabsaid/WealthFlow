import os
import logging
from pathlib import Path
from playwright.sync_api import sync_playwright

logger = logging.getLogger(__name__)

def run_python_pdf_render(input_html_path: str, output_pdf_path: str) -> bool:
    """
    Renders an HTML file to PDF using Playwright Python sync API.
    Produces output identical to html_to_pdf.js.
    """
    abs_input = os.path.abspath(input_html_path)
    abs_output = os.path.abspath(output_pdf_path)

    if not os.path.exists(abs_input):
        logger.error(f"Input file not found for PDF rendering: {abs_input}")
        return False

    os.makedirs(os.path.dirname(abs_output), exist_ok=True)
    file_url = Path(abs_input).as_uri()

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()

            page.goto(file_url, wait_until='networkidle')

            # Wait for fonts to be ready
            page.evaluate("() => document.fonts.ready")

            # Ensure all images are loaded
            page.evaluate("""async () => {
                const images = Array.from(document.querySelectorAll('img'));
                await Promise.all(images.map(img => {
                    if (img.complete) return;
                    return new Promise((resolve) => {
                        img.addEventListener('load', resolve);
                        img.addEventListener('error', resolve);
                    });
                }));
            }""")

            # Emulate screen media type so dark mode styling prints cleanly
            page.emulate_media(media='screen')

            page.pdf(
                path=abs_output,
                format='A4',
                print_background=True,
                margin={
                    'top': '20mm',
                    'right': '20mm',
                    'bottom': '20mm',
                    'left': '20mm'
                },
                display_header_footer=True,
                header_template='<div style="font-size: 10px; width: 100%; text-align: center; color: #6c757d;">WealthFlow Documentation</div>',
                footer_template='<div style="font-size: 10px; width: 100%; text-align: center; color: #6c757d;">Page <span class="pageNumber"></span> of <span class="totalPages"></span></div>'
            )
            browser.close()

        logger.info(f"Generated PDF (Python Playwright): {abs_output}")
        return True
    except Exception as e:
        logger.error(f"PDF Generation failed (Python Playwright): {e}")
        return False
