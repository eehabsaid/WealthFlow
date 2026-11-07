"""Attachments: validation, excerpts, budget, vision rules, and how images reach each provider's request. No real model is used."""

import base64

import pytest

from ..engine import attachments as att
from ..engine.attachments import AttachmentError, Attachments
from ..providers import adapters, vision
from ..settings.store import DEFAULTS

PNG = base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"0" * 20).decode()


def prep(repo, items, vision_ok=False):
    return att.prepare(repo, items, DEFAULTS, vision_ok)


def f(name, text, **kw):
    return {"kind": "file", "name": name, "text": text, **kw}


def img(name="shot.png", **kw):
    return {"kind": "image", "name": name, "mime": "image/png", "data": PNG, **kw}


def test_small_file_is_included_whole(repo):
    rec = prep(repo, [f("notes.txt", "hello")])[0]
    assert rec["text"] == "hello" and rec["omitted"] == 0 and rec["chars"] == 5


def test_oversized_file_becomes_a_marked_excerpt_never_a_silent_cut(repo):
    rec = prep(repo, [f("big.log", "x" * 90_000)])[0]
    assert rec["omitted"] > 0 and rec["chars"] == 90_000
    assert f"{rec['omitted']} characters omitted" in rec["text"] and len(rec["text"]) < 41_000
    msg = Attachments([{**rec, "path": ""}], []).message("TASK", False)["content"]
    assert "[EXCERPT" in msg and "of 90000 characters omitted" in msg


def test_attachments_that_do_not_fit_the_budget_refuse_the_task_with_numbers(repo):
    with pytest.raises(AttachmentError, match=r"too large: about \d+ tokens against a budget of 30500"):
        prep(repo, [f(f"{n}.txt", "y" * 40_000) for n in range(4)])
    assert len(prep(repo, [f(f"{n}.txt", "y" * 40_000) for n in range(3)])) == 3


def test_secret_files_private_keys_and_bad_input_are_refused(repo):
    for bad in (f(".env", "A=1"), f("id.txt", "-----BEGIN RSA PRIVATE KEY-----\nabc"), {"kind": "file", "name": "x"}, {"kind": "other"}, f("db.sqlite3", "x")):
        with pytest.raises(AttachmentError):
            prep(repo, [bad])
    with pytest.raises(AttachmentError, match="at most"):
        prep(repo, [f(f"{n}.txt", "a") for n in range(11)])


def test_attached_project_path_is_kept_only_when_real(repo):
    assert prep(repo, [f("calc.py", "x", path="app/calc.py")])[0]["path"] == "app/calc.py"
    assert prep(repo, [f("calc.py", "x", path="../outside.py")])[0]["path"] == ""
    with pytest.raises(AttachmentError, match="secret"):
        prep(repo, [f("whatever.txt", "x", path=".env")])


def test_images_need_a_vision_model_and_valid_data(repo):
    with pytest.raises(AttachmentError, match="does not accept images"):
        prep(repo, [img()], vision_ok=False)
    assert prep(repo, [img()], vision_ok=True)[0]["data"].startswith(b"\x89PNG")
    for bad in (img(mime="image/svg+xml"), img(data="not base64!!"), img(data="")):
        with pytest.raises(AttachmentError):
            prep(repo, [bad], vision_ok=True)
    with pytest.raises(AttachmentError, match="MB"):
        prep(repo, [img(data=base64.b64encode(b"0" * 3_100_000).decode())], vision_ok=True)


def test_a_task_with_images_cannot_run_on_a_model_without_vision(repo):
    recs = prep(repo, [img()], vision_ok=True)
    loaded = Attachments([], [{"mime": "image/png", "data": PNG, "name": recs[0]["name"]}])
    assert loaded.message("T", True)["images"] == [{"mime": "image/png", "data": PNG}]
    with pytest.raises(AttachmentError, match="does not accept images"):
        loaded.message("T", False)


def test_vision_by_provider_and_model():
    yes = [("anthropic", "claude-sonnet-4"), ("openai", "gpt-4o-mini"), ("openai", "o3"), ("gemini", "gemini-2.5-pro")]
    no = [("anthropic", "claude-2.1"), ("openai", "gpt-3.5-turbo"), ("openai", "o1-mini"), ("gemini", "gemini-pro"), ("anthropic", ""), ("nobody", "x")]
    assert all(vision.supports_images(p, m) for p, m in yes) and not any(vision.supports_images(p, m) for p, m in no)


def test_ollama_vision_is_asked_from_the_server(monkeypatch):
    seen = []

    def fake(base, model, timeout):
        seen.append(model)
        return ("vision" in model), ""
    monkeypatch.setattr(vision, "_ollama", fake)
    vision._cache.clear()
    assert vision.check("ollama", "llava-vision", "http://a")[0] and not vision.check("ollama", "qwen", "http://a")[0]
    vision.check("ollama", "llava-vision", "http://a")
    assert seen.count("llava-vision") == 1   # cached for a minute


@pytest.fixture
def captured(monkeypatch):
    box = {}

    def post(url, headers, body, *a, **k):
        box.update(url=url, body=body)
        return {"message": {"content": "{}"}, "content": [{"type": "text", "text": "{}"}], "choices": [{"message": {"content": "{}"}}],
                "candidates": [{"content": {"parts": [{"text": "{}"}]}}]}
    monkeypatch.setattr(adapters, "post_json", post)
    return box


MESSAGES = [{"role": "user", "content": "look", "images": [{"mime": "image/png", "data": PNG}]}]


def test_each_provider_gets_the_image_in_its_own_format(captured):
    adapters.Anthropic("claude-x", "http://a", "k").complete("s", MESSAGES)
    assert captured["body"]["messages"][0]["content"][0] == {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": PNG}}
    adapters.OpenAI("gpt-4o", "http://a", "k").complete("s", MESSAGES)
    assert captured["body"]["messages"][1]["content"][1] == {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{PNG}"}}
    adapters.Gemini("gemini-2.5", "http://a", "k").complete("s", MESSAGES)
    assert captured["body"]["contents"][0]["parts"][1] == {"inline_data": {"mime_type": "image/png", "data": PNG}}
    adapters.Ollama("llava", "http://a").complete("s", MESSAGES)
    assert captured["body"]["messages"][1]["images"] == [PNG]


def test_plain_messages_are_unchanged_by_the_image_support(captured):
    plain = [{"role": "user", "content": "hi"}]
    adapters.Anthropic("claude-x", "http://a", "k").complete("s", plain)
    assert captured["body"]["messages"] == plain
    adapters.OpenAI("gpt-4o", "http://a", "k").complete("s", plain)
    assert captured["body"]["messages"][1] == {"role": "user", "content": "hi"}
    adapters.Ollama("m", "http://a").complete("s", plain)
    assert captured["body"]["messages"][1] == {"role": "user", "content": "hi"}
