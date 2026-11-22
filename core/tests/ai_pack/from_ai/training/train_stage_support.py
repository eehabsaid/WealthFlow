"""Shared base for the training stage tests."""


import json
import os
import tempfile
from unittest.mock import patch

from django.test import TestCase

from ai.training.services import config, preflight, train_stage, wsl
from ai.models import AISetting
from core.tests.ai_pack.investigation.support import make_user



MODEL = "qwen3.8:27b-150k"


class StageBase(TestCase):
    def setUp(self):
        self.user = make_user("train_user", sysadmin=True)
        folder = tempfile.mkdtemp()
        self.base = os.path.join(folder, "model")
        os.makedirs(self.base)
        for name in ("config.json", "model-00001.safetensors"):
            open(os.path.join(self.base, name), "w").write("x")
        self.cfg = config.load(base_model_dir=self.base, work_dir=os.path.join(folder, "work"), min_free_gb=0, min_traces=3)
        self.streams = []
        AISetting.set("ai_model", MODEL, user=None)

    def stream(self, cmd_log, fail_on=None, make_result=True):
        def fake(cfg, script, log):
            self.streams.append(script)
            log(f"running: {script[:40]}")
            if fail_on and fail_on in script:
                return 1
            if make_result and "trainer.train" in script:
                out = os.path.join(train_stage.run_dir(self.cfg), "out")
                os.makedirs(out, exist_ok=True)
                gguf = os.path.join(out, "gguf", "m.gguf")
                mmproj = os.path.join(out, "gguf", "mmproj-F16.gguf")
                vision = os.path.join(out, "vision")
                os.makedirs(os.path.dirname(gguf), exist_ok=True)
                os.makedirs(vision, exist_ok=True)
                open(gguf, "w").write("x")
                open(mmproj, "w").write("x")
                json.dump({"vision_config": {"model_type": "test"}}, open(os.path.join(vision, "config.json"), "w"))
                open(os.path.join(vision, "preprocessor_config.json"), "w").write("{}")
                open(os.path.join(vision, "tokenizer.json"), "w").write("{}")
                json.dump({"gguf": gguf, "gguf_files": [gguf], "mmproj": mmproj, "vision_assets": vision}, open(os.path.join(out, "result.json"), "w"))
            return 0
        return fake

    def patches(self, **kw):
        ready = [preflight.Check("GPU inside WSL", True, "ok")]
        return (patch.object(preflight, "_ollama_has", return_value=True), patch.object(preflight, "wsl_checks", return_value=kw.get("wsl", ready)),
                patch.object(wsl, "stream", side_effect=self.stream(None, kw.get("fail_on"), kw.get("make_result", True))))
