from django.shortcuts import render

from core.authentication.utils import request_lang as _request_lang


def _render_auth(request, template_name, extra_context=None):
    context = {"lang_code": _request_lang(request)}
    if extra_context:
        context.update(extra_context)
    response = render(request, template_name, context)
    response.set_cookie("wf_lang", context["lang_code"], max_age=31536000, samesite="Lax")
    return response


def _render_auth_status(request, *, title_key, message_key, tone="info", cta_href="", cta_key=""):
    return _render_auth(
        request,
        "authentication/auth_status.html",
        {
            "title_key": title_key,
            "message_key": message_key,
            "tone": tone,
            "cta_href": cta_href,
            "cta_key": cta_key,
        },
    )
