"""Dataset validation and export for the Recovery profile."""

from __future__ import annotations

import json
import os
from collections import Counter

from .recovery_profile import SYSTEM_PROMPT, dataset_path, report_paths, resolve_path


def validate_dataset(profile: dict, *, write_report: bool = True) -> dict:
    path = dataset_path(profile)
    required_topics = set(profile["required_topics"])
    report = {"dataset": path, "valid": False, "examples": 0, "topics": {}, "errors": []}
    seen_questions: set[str] = set()
    topic_counts: Counter[str] = Counter()
    try:
        with open(path, encoding="utf-8") as fh:
            for line_number, line in enumerate(fh, 1):
                if not line.strip():
                    continue
                report["examples"] += 1
                try:
                    item = json.loads(line)
                except json.JSONDecodeError as exc:
                    report["errors"].append(f"line {line_number}: invalid JSON ({exc.msg})")
                    continue
                if not isinstance(item, dict):
                    report["errors"].append(f"line {line_number}: each example must be a JSON object")
                    continue
                question, answer, topic = item.get("question"), item.get("answer"), item.get("topic")
                if not isinstance(question, str) or not question.strip():
                    report["errors"].append(f"line {line_number}: question must be a non-empty string")
                if not isinstance(answer, str) or len(answer.strip()) < 20:
                    report["errors"].append(f"line {line_number}: answer must contain at least 20 non-whitespace characters")
                if not isinstance(topic, str) or topic not in required_topics:
                    report["errors"].append(f"line {line_number}: topic must be one of the configured Recovery topics")
                else:
                    topic_counts[topic] += 1
                if isinstance(question, str) and question.strip():
                    normalized = " ".join(question.casefold().split())
                    if normalized in seen_questions:
                        report["errors"].append(f"line {line_number}: duplicate question")
                    seen_questions.add(normalized)
    except FileNotFoundError:
        raise FileNotFoundError(f"Recovery dataset not found: {path}") from None

    missing_topics = sorted(required_topics - topic_counts.keys())
    report["topics"] = dict(sorted(topic_counts.items()))
    if not report["examples"]:
        report["errors"].append("dataset contains no examples")
    if report["examples"] < int(profile["minimum_examples"]):
        report["errors"].append(
            f"dataset has {report['examples']} examples; at least {profile['minimum_examples']} are required"
        )
    if missing_topics:
        report["errors"].append(f"missing required topics: {', '.join(missing_topics)}")
    report["valid"] = not report["errors"]
    if write_report:
        paths = report_paths(profile)
        os.makedirs(os.path.dirname(paths["json"]), exist_ok=True)
        with open(paths["json"], "w", encoding="utf-8") as fh:
            json.dump(report, fh, ensure_ascii=False, indent=2)
        with open(paths["text"], "w", encoding="utf-8") as fh:
            fh.write(format_report(report) + "\n")
    return report


def format_report(report: dict) -> str:
    lines = [f"Recovery dataset: {report['examples']} examples; {'VALID' if report['valid'] else 'INVALID'}"]
    lines.extend(f"  {topic}: {count}" for topic, count in report["topics"].items())
    lines.extend(f"  ERROR: {error}" for error in report["errors"])
    return "\n".join(lines)


def export_dataset(profile: dict) -> tuple[str, dict]:
    report = validate_dataset(profile)
    if not report["valid"]:
        raise ValueError(format_report(report))
    target = resolve_path(profile["exported_dataset_path"])
    os.makedirs(os.path.dirname(target), exist_ok=True)
    source = dataset_path(profile)
    temporary = target + ".tmp"
    with open(source, encoding="utf-8") as input_file, open(temporary, "w", encoding="utf-8") as output_file:
        for line in input_file:
            if not line.strip():
                continue
            item = json.loads(line)
            messages = [
                {"role": "system", "content": profile.get("system_prompt") or SYSTEM_PROMPT},
                {"role": "user", "content": item["question"].strip()},
                {"role": "assistant", "content": item["answer"].strip()},
            ]
            output_file.write(json.dumps({"messages": messages}, ensure_ascii=False) + "\n")
        report["replay"] = _append_replay(profile, output_file)
    os.replace(temporary, target)
    return target, report


def _append_replay(profile: dict, output_file) -> int:
    """Copy earlier chat-format training lines (e.g. the agent-loop traces) so the new stage does not unlearn them."""
    copied = 0
    for path in profile.get("replay_files", []):
        if not os.path.isfile(path):
            raise FileNotFoundError(f"replay file not found: {path}")
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    json.loads(line)
                    output_file.write(line if line.endswith("\n") else line + "\n")
                    copied += 1
    return copied
