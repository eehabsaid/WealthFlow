"""HtmlRenderer: converts the generated markdown into a themed, standalone
HTML document. See this package's __init__.py for the sibling list."""


class HtmlRenderer:

    def render(self, md_path, html_path, context):
        with open(md_path, "r", encoding="utf-8") as f:
            md_text = f.read()
            
        md_text = md_text.replace("<!-- AUTO-GENERATED START -->\n", "").replace("<!-- AUTO-GENERATED END -->\n", "")
        import markdown
        html_content = markdown.markdown(md_text, extensions=['tables', 'fenced_code', 'toc'])
        
        is_dark = context.get('theme', '').lower() == 'dark'
        
        if is_dark:
            bg_color = "#121212"
            container_bg = "#1e1e1e"
            text_color = "#e0e0e0"
            heading_color = "#ffffff"
            hr_color = "#333333"
            code_bg = "#2d2d2d"
            caption_color = "#aaaaaa"
        else:
            bg_color = "#f4f7f6"
            container_bg = "#ffffff"
            text_color = "#333333"
            heading_color = "#2c3e50"
            hr_color = "#eeeeee"
            code_bg = "#f4f4f4"
            caption_color = "#666666"

        final_html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset='utf-8'>
<title>{context['title']}</title>
<style>
body, html {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; line-height: 1.6; color: {text_color}; background-color: {bg_color}; max-width: 1200px; margin: 0 auto; padding: 2rem; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
h1, h2, h3, h4, h5, h6 {{ color: {heading_color}; }}
img {{ max-width: 100%; height: auto; display: block; margin: 2rem auto; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }}
figcaption {{ text-align: center; font-style: italic; color: {caption_color}; margin-top: 0.5rem; }}
.container {{ background: {container_bg}; padding: 2rem; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
hr {{ border: 0; height: 1px; background: {hr_color}; margin: 2rem 0; }}
code {{ background: {code_bg}; padding: 0.2rem 0.4rem; border-radius: 4px; font-family: monospace; }}
table {{ width: 100%; border-collapse: collapse; margin: 1rem 0; }}
th, td {{ padding: 0.75rem; border: 1px solid {hr_color}; text-align: left; }}
th {{ background-color: {code_bg}; }}
a {{ color: #3498db; text-decoration: none; }}
a:hover {{ text-decoration: underline; }}
</style>
</head>
<body><div class='container'>{html_content}</div></body></html>"""
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(final_html)

