"""
Placeholder substitution and plain-text/HTML email body construction.
"""

import re


def replace_placeholders(text: str, context: dict) -> str:
    out = str(text or "")
    for key, value in (context or {}).items():
        out = out.replace(f"{{{{{key}}}}}", str(value or ""))
    return out


def build_email_bodies(raw_body: str) -> tuple[str, str]:
    text = str(raw_body or "").strip()
    has_html_tags = bool(re.search(r"<(html|body|div|p|a|br|table|span)[^>]*>", text, re.IGNORECASE))

    if has_html_tags:
        html_body = text
        plain_body = re.sub(r"<[^>]+>", "", text).strip()
    else:
        plain_body = text
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        html_parts = []

        for p in paragraphs:
            formatted_p = p.replace("\n", "<br>")
            url_match = re.search(r"https?://[^\s<]+", formatted_p)
            if url_match:
                url = url_match.group(0)
                button_html = (
                    f'<div style="margin: 16px 0;">'
                    f'<a href="{url}" target="_blank" style="background-color: #1a6ef5; color: #ffffff; '
                    f'padding: 12px 24px; text-decoration: none; border-radius: 8px; font-weight: bold; '
                    f'display: inline-block;">Confirm / Verify</a>'
                    f'</div>'
                    f'<p style="font-size: 12px; color: #666666;">Or copy and paste this link into your browser:<br>'
                    f'<a href="{url}" style="color: #1a6ef5; word-break: break-all;">{url}</a></p>'
                )
                formatted_p = re.sub(r"https?://[^\s<]+", button_html, formatted_p, count=1)

            html_parts.append(f'<p style="margin: 0 0 16px 0;">{formatted_p}</p>')

        content_html = "\n".join(html_parts)

        html_body = (
            f'<!DOCTYPE html>'
            f'<html>'
            f'<head><meta charset="utf-8"></head>'
            f'<body style="font-family: -apple-system, BlinkMacSystemFont, \'Segoe UI\', Roboto, Helvetica, Arial, sans-serif; '
            f'font-size: 15px; line-height: 1.6; color: #1e293b; background-color: #f8fafc; margin: 0; padding: 24px;">'
            f'<div style="max-width: 560px; margin: 0 auto; background: #ffffff; border: 1px solid #e2e8f0; '
            f'border-radius: 12px; padding: 32px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);">'
            f'{content_html}'
            f'</div>'
            f'</body>'
            f'</html>'
        )

    return plain_body, html_body
