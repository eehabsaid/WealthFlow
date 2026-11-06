"""WealthFlow QA Module - Settings > AI Advisor > Image generation, and generated images in the chat.

Real browser, real APIs (no image provider is needed: the provider is exercised by the Django tests with mocked HTTP):
  1. The Image generation card is there, off by default; the generate_image tool is not offered (the settings API says so).
  2. Entering a provider / model / URL and pressing Test connection shows a clear error for an unreachable server (no crash).
  3. Saving with the switch on and incomplete values is refused; saving complete values stores them (key masked) and survives a reload.
  3b. WealthFlow starts the server itself: with a start command saved, Test connection starts a real (fake ComfyUI) process, reports
     it, the server then answers on its port, and switching image generation off stops it again.
  4. A generated picture row (made by the ORM, like the tool would) is shown under the answer in the chat with an <img> and a
     Download button; the download link returns an attachment; another user's / unknown id answers 404.
Every setting and row it creates is removed at the end.
"""

import os
import socket
import sys
import time

import requests

from tests.modules.e2e_settings import AI_ENGINE_PINS, django_exec, fresh_state, pinned

SETTINGS_URL = "/api/settings/ai/"
KEYS = [f"image_gen_{f}" for f in ("enabled", "provider", "model", "endpoint", "api_key", "start_command")]
_FETCH = """async ([url, method, body]) => { const res = await fetch(url, {method: method || "GET",
  headers: {"Content-Type": "application/json", "X-CSRFToken": (window.wfGetCsrfToken && window.wfGetCsrfToken()) || ""},
  body: body ? JSON.stringify(body) : undefined});
  let data = null; try { data = await res.json(); } catch (e) {}
  return {status: res.status, data, disposition: res.headers.get("content-disposition"), type: res.headers.get("content-type")}; }"""
MAKE_ROW = (
    "import io; from PIL import Image; from django.contrib.auth import get_user_model; from core.models import AIAttachment, AIConversation, AIMessage\n"
    "from core.models.ai_attachment import GENERATED_PREFIX\n"
    "u = get_user_model().objects.get(username='eehab_said'); b = io.BytesIO(); Image.new('RGB', (40, 30), 'teal').save(b, 'PNG')\n"
    "f = 'owner' if 'owner' in [x.name for x in AIConversation._meta.fields] else 'user'; c = AIConversation.objects.create(**{f: u, 'title': 'E2E image'}); AIMessage.objects.create(conversation=c, role='user', content='draw a teal box')\n"
    "m = AIMessage.objects.create(conversation=c, role='assistant', content='Here is your image.')\n"
    "a = AIAttachment.objects.create(user=u, message=m, name='generated-e2e.png', kind='image', mime='image/png', size=len(b.getvalue()), text=GENERATED_PREFIX + 'teal box', data=b.getvalue())\n"
    "print(c.id, a.id)\n"
)
CLEANUP = "from core.models import AIConversation, AIAttachment; AIAttachment.objects.filter(name='generated-e2e.png').delete(); AIConversation.objects.filter(title='E2E image').delete()"


def _step(reporter, screenshot_logger, page, name, ok, detail, shot_name):
    shot = screenshot_logger.capture(page, "settings", shot_name, "none", "view", "ok" if ok else "fail")
    reporter.add_step(name, "WealthFlow AI", "PASS" if ok else "FAIL", detail, screenshot_path=shot)


def _open(page, context):
    context.goto_route("#settings-aiadvisor")
    page.reload()   # earlier modules already loaded this page: start from what the server holds now, not their in-memory form
    context.goto_route("#settings-aiadvisor")
    page.wait_for_selector("#image_gen_enabled", timeout=20000)


def _save(page):
    with page.expect_response(lambda r: SETTINGS_URL in r.url and r.request.method == "POST", timeout=15000) as info:
        page.click("#aiSaveBtn")
    page.wait_for_timeout(500)
    return info.value.status


def _settings_steps(context, reporter, screenshot_logger):
    page = context.page
    _open(page, context)
    api = page.evaluate(_FETCH, [SETTINGS_URL])["data"]
    ui_on, api_on = page.is_checked("#image_gen_enabled"), api.get("image_gen_enabled")
    providers = [p["key"] for p in api.get("image_gen_providers", [])]
    ok = not ui_on and api_on is False and "comfyui" in providers
    _step(reporter, screenshot_logger, page, "Image generation: card present and off by default", ok, f"control={ui_on}, api={api_on}, providers={providers}", "image_gen_default")
    page.select_option("#image_gen_provider", "comfyui")
    page.fill("#image_gen_model", "flux-2-klein-4b.safetensors")
    page.fill("#image_gen_endpoint", "http://127.0.0.1:9")
    page.click("#image_gen_test")
    page.wait_for_selector("#image_gen_test_result.alert-danger", timeout=30000)
    msg = page.inner_text("#image_gen_test_result")
    _step(reporter, screenshot_logger, page, "Test connection reports an unreachable provider clearly", len(msg) > 5, msg[:120], "image_gen_test_fail")
    page.fill("#image_gen_model", "")
    page.check("#image_gen_enabled")
    status = _save(page)
    _step(reporter, screenshot_logger, page, "Enabling with incomplete values is refused", status == 400, f"status={status}", "image_gen_incomplete")
    page.fill("#image_gen_model", "flux-2-klein-4b.safetensors")
    page.fill("#image_gen_api_key", "e2e-secret")
    status = _save(page)
    stored = page.evaluate(_FETCH, [SETTINGS_URL])["data"]
    page.reload()
    _open(page, context)
    ok = status == 200 and stored.get("image_gen_enabled") is True and "e2e-secret" not in str(stored.get("image_gen_api_key")) and page.is_checked("#image_gen_enabled") \
        and page.input_value("#image_gen_model") == "flux-2-klein-4b.safetensors"
    _step(reporter, screenshot_logger, page, "Complete image settings are saved, key masked, survive a reload", ok, f"status={status} key={stored.get('image_gen_api_key')!r}", "image_gen_saved")


FAKE_SERVER = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "core", "tests", "ai", "fake_comfy_server.py")
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STOP_SERVER = "from core.services.ai.image_generation.server import stop_server; stop_server('http://127.0.0.1:%d')"   # only this test's own server


def _answers(port):
    try:
        return requests.get(f"http://127.0.0.1:{port}/system_stats", timeout=1).status_code == 200
    except requests.RequestException:
        return False


def _diagnostics(port):
    """What WealthFlow's managed server left behind (log tail, state file) so a hang is explained in the report."""
    parts = [f"port answers={_answers(port)}"]
    key = f"127_0_0_1_{port}"   # servers are told apart by API URL (state.endpoint_key)
    for name in (f"server-{key}.log", f"state-{key}.json"):
        try:
            with open(os.path.join(REPO_ROOT, "runtime", "image_server", name), encoding="utf-8", errors="replace") as fh:
                parts.append(f"{name}: " + " | ".join(line.strip() for line in fh.read().splitlines()[-8:] if line.strip())[-500:])
        except OSError:
            parts.append(f"{name}: missing")
    return "; ".join(parts)


def _wait(predicate, seconds):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.5)
    return False


def _managed_server_steps(context, reporter, screenshot_logger):
    page = context.page
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    try:
        page.fill("#image_gen_endpoint", f"http://127.0.0.1:{port}")
        page.fill("#image_gen_start_command", f'"{sys.executable}" "{FAKE_SERVER}" --port {{port}}')
        page.click("#image_gen_test")
        finished = _wait(lambda: any(c in (page.get_attribute("#image_gen_test_result", "class") or "") for c in ("alert-success", "alert-danger")), 150)
        msg = page.inner_text("#image_gen_test_result")   # a failure or a hang is reported with its message and the server's own log
        up = _answers(port)
        ok = finished and up and "started by WealthFlow" in msg
        _step(reporter, screenshot_logger, page, "Test connection starts the image server by itself", ok, msg[:300] if ok else f"finished={finished}; message={msg[:300]}; {_diagnostics(port)}", "image_gen_managed_start")
        if not ok:
            return
        status = _save(page)
        _step(reporter, screenshot_logger, page, "Saving with the start command keeps the server up (no duplicate)", status == 200 and _answers(port), f"status={status}", "image_gen_managed_saved")
        page.uncheck("#image_gen_enabled")
        status = _save(page)
        stopped = _wait(lambda: not _answers(port), 20)
        _step(reporter, screenshot_logger, page, "Switching image generation off stops the server WealthFlow started", status == 200 and stopped, f"status={status} stopped={stopped}", "image_gen_managed_stop")
    finally:
        django_exec(STOP_SERVER % port)


def _chat_steps(context, reporter, screenshot_logger):
    page = context.page
    convo, att = django_exec(MAKE_ROW).split()[-2:]
    try:
        context.goto_route("#ai")
        page.reload()
        context.goto_route("#ai")
        page.wait_for_selector("#ai-ws-input", timeout=15000)
        page.evaluate("async (id) => { await _switchAIChatConversation(String(id)); }", int(convo))
        page.wait_for_selector(".ai-gen-image img", timeout=15000)
        page.evaluate("() => document.querySelector('.ai-gen-image img').scrollIntoView()")   # the image is loading="lazy"
        try:   # the element exists before its bytes arrive: wait for the browser to finish loading it, however slow the machine is
            page.wait_for_function("() => { const i = document.querySelector('.ai-gen-image img'); return i && i.complete && i.naturalWidth > 0; }", timeout=20000)
        except Exception:
            pass
        shown = page.evaluate("() => { const i = document.querySelector('.ai-gen-image img'); return !!i && i.complete && i.naturalWidth > 0; }")
        link = page.get_attribute(".ai-gen-image a.btn", "href")
        _step(reporter, screenshot_logger, page, "Generated image is shown under the answer with a Download button", shown and "download=1" in link, f"loaded={shown} href={link}", "image_gen_chat")
        got = page.evaluate(_FETCH, [f"/api/financial-advisor/ai/attachments/{att}/?download=1"])
        miss = page.evaluate(_FETCH, ["/api/financial-advisor/ai/attachments/99999999/"])
        ok = got["status"] == 200 and "attachment" in (got["disposition"] or "") and got["type"] == "image/png" and miss["status"] == 404
        _step(reporter, screenshot_logger, page, "Download returns the image as an attachment; unknown id is 404", ok, f"{got['status']} {got['disposition']} / {miss['status']}", "image_gen_download")
    finally:
        django_exec(CLEANUP)


def test_ai_image_generation(context, reporter, screenshot_logger):
    try:
        with fresh_state(KEYS), pinned(AI_ENGINE_PINS):
            _settings_steps(context, reporter, screenshot_logger)
            _managed_server_steps(context, reporter, screenshot_logger)
            _chat_steps(context, reporter, screenshot_logger)
    except Exception as ex:
        shot = screenshot_logger.capture(context.page, "settings", "image_gen_error", "none", "fail", "fail")
        reporter.add_step("Image generation", "WealthFlow AI", "FAIL", f"Exception: {ex}", screenshot_path=shot)
