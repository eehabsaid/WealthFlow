"""Test doubles for the training stage: a ChatML tokenizer (Qwen-style quirks), fake unsloth/trl deps, and kept traces."""

from __future__ import annotations

import json
from types import SimpleNamespace

from ai_training.models import AgentTrace


class FakeTokenizer:
    """ChatML like Qwen: history assistant turns have no think block; the generation prompt adds one (empty when thinking is off)."""

    def __init__(self, broken: bool = False):
        self.broken = broken

    def apply_chat_template(self, messages, tools=None, tokenize=False, add_generation_prompt=False, enable_thinking=True):
        out = "<|im_start|>system\nTOOLS " + json.dumps(tools) + "<|im_end|>\n" if tools else ""
        for m in messages:
            role = "user" if m["role"] == "tool" else m["role"]
            if self.broken:
                body = m.get("content", "")
                out += f"[{m['role']}] {body}\n"
                continue
            if m["role"] == "assistant" and m.get("tool_calls"):
                body = "".join(f"<tool_call>{c['function']['name']} {json.dumps(c['function']['arguments'])}</tool_call>" for c in m["tool_calls"])
            elif m["role"] == "tool":
                body = f"<tool_response>{m['content']}</tool_response>"
            else:
                body = m.get("content", "")
            out += f"<|im_start|>{role}\n{body}<|im_end|>\n"
        if add_generation_prompt:
            out += "<|im_start|>assistant\n" + ("<think>\n" if enable_thinking else "<think>\n\n</think>\n\n")
        return out

    def __call__(self, text, add_special_tokens=False):
        return {"input_ids": text.split()}

    def save_pretrained(self, path):
        pass


def messages(question="How many goal records do I have?", answer="You have 6 goal records.", result='{"count":6}'):
    return [{"role": "system", "content": "SYSTEM RULES"}, {"role": "user", "content": question},
            {"role": "assistant", "content": "", "tool_calls": [{"id": "call_1", "type": "function", "function": {"name": "app_data_query", "arguments": {"model": "Goal"}}}]},
            {"role": "tool", "tool_call_id": "call_1", "name": "app_data_query", "content": result},
            {"role": "assistant", "content": answer}]


def write_jsonl(path, rows):
    with open(path, "w", encoding="utf-8") as fh:
        for row in rows:
            fh.write((row if isinstance(row, str) else json.dumps(row)) + "\n")


def make_kept(user, n: int):
    for i in range(n):
        AgentTrace.objects.create(owner=user, case_key=f"K{i}", attempt=1, question=f"q{i}", system_prompt="SYS", tools=[{"type": "function"}],
                                  steps=[{"tool": "app_data_query", "arguments": {"model": "Goal"}, "result": '{"count":6}'}], answer="6", verdict="kept")


class FakeModel:
    def __init__(self, log):
        self.log = log

    def save_pretrained(self, path):
        self.log.append(("save_pretrained", path))

    def save_pretrained_gguf(self, path, tokenizer, quantization_method):
        import os
        os.makedirs(path, exist_ok=True)
        for name, size in (("model.Q4_K_M.gguf", 50), ("mmproj-F16.gguf", 90)):
            with open(os.path.join(path, name), "wb") as fh:
                fh.write(b"x" * size)
        self.log.append(("gguf", quantization_method))


def fake_deps(log, trl_key="max_length", tok=None):
    """A stand-in for unsloth / trl / datasets that records every call."""
    tok = tok or FakeTokenizer()
    processor = type("Processor", (), {"tokenizer": tok, "save_pretrained": lambda self, path: None})()
    config_cls = type("SFTConfig", (), {"__dataclass_fields__": {trl_key: 1}, "__init__": lambda self, **kw: log.append(("sft_config", kw)) or setattr(self, "kw", kw)})

    class FastModel:
        @staticmethod
        def from_pretrained(**kw):
            log.append(("load", kw))
            return FakeModel(log), processor

        @staticmethod
        def get_peft_model(model, **kw):
            log.append(("peft", kw))
            return model

    class Trainer:
        def __init__(self, **kw):
            log.append(("trainer", len(kw["train_dataset"])))

        def train(self):
            log.append(("train",))
            return SimpleNamespace(training_loss=0.5)

    dataset = SimpleNamespace(from_list=lambda rows: rows)
    only = lambda trainer, instruction_part, response_part: log.append(("masks", instruction_part, response_part)) or trainer
    return SimpleNamespace(Dataset=dataset, SFTConfig=config_cls, SFTTrainer=Trainer, FastModel=FastModel, train_on_responses_only=only)
