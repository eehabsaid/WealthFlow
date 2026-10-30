"""Scores, the verdict and the report files of a model comparison. The verdict is a recommendation only: nothing is switched."""

from __future__ import annotations

import json
import os
from collections import Counter
from statistics import median

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font

MIN_QUESTIONS = 10


def stats(rows: list[dict]) -> dict:
    """rows = one dict per question: passed, seconds, reasons. Seconds are the counted questions only (the warm-up is not in rows)."""
    passed = sum(1 for r in rows if r["passed"])
    times = [r["seconds"] for r in rows]
    reasons = Counter(x.split(":")[0] for r in rows for x in r["reasons"])
    return {"questions": len(rows), "passed": passed, "rate": round(100 * passed / len(rows), 1) if rows else 0.0,
            "median_s": round(median(times), 1) if times else 0.0, "mean_s": round(sum(times) / len(times), 1) if times else 0.0,
            "reasons": dict(reasons.most_common())}


def verdict(old: dict, new: dict, min_gain: int, max_slower: int) -> tuple[str, str]:
    """(short verdict, one plain sentence why). Rule: new wins only if it scores >= min_gain points higher AND is not > max_slower % slower (median)."""
    if min(old["questions"], new["questions"]) < MIN_QUESTIONS:
        return "NOT ENOUGH QUESTIONS", f"Fewer than {MIN_QUESTIONS} test questions could be built from your data, so no fair decision is possible."
    gain = round(new["rate"] - old["rate"], 1)
    slower = round(100 * (new["median_s"] / old["median_s"] - 1), 1) if old["median_s"] else 0.0
    facts = f"correct answers {old['rate']}% -> {new['rate']}% ({gain:+} points); median time {old['median_s']}s -> {new['median_s']}s ({slower:+}%)"
    if gain >= min_gain and slower <= max_slower:
        return "NEW MODEL WINS", facts
    if gain >= min_gain:
        return "NEW MODEL IS MORE CORRECT BUT TOO SLOW", facts + f" - more than {max_slower}% slower, so not a win by your rule"
    if gain <= -min_gain:
        return "OLD MODEL IS BETTER", facts
    return "NO REAL DIFFERENCE", facts + f" - less than {min_gain} points apart"


def format_text(info: dict) -> str:
    old, new = info["old"], info["new"]
    lines = [f"MODEL TEST   {info['when']}", f"Old: {old['name']}    New: {new['name']}",
             f"Questions per model: {old['stats']['questions']} (the same for both, built from your data, never used in training)",
             f"Ollama before each model: {info['reset']}; one warm-up question per model, not counted.", "",
             f"VERDICT: {info['verdict']}", info["why"],
             "Nothing was switched. Your model in Settings is unchanged; you decide.", "", f"{'':22}{'OLD':>12}{'NEW':>12}"]
    for label, key in (("Correct answers", "passed"), ("Correct %", "rate"), ("Median seconds", "median_s"), ("Mean seconds", "mean_s")):
        lines.append(f"{label:22}{old['stats'][key]:>12}{new['stats'][key]:>12}")
    for title, side in (("OLD", old), ("NEW", new)):
        if side["stats"]["reasons"]:
            lines.append(f"{title} failed because: " + ", ".join(f"{k} x{v}" for k, v in side["stats"]["reasons"].items()))
    step = round(100 / max(old["stats"]["questions"], 1), 1)
    lines += ["", f"Reading it: one question = {step} points, so small differences can be luck.",
              "Same tables and tools as in training, only other kinds of questions (highest, lowest, average, last 5, count in a year)."]
    return "\n".join(lines)


def write_files(out_dir: str, info: dict) -> dict:
    os.makedirs(out_dir, exist_ok=True)
    paths = {"report": os.path.join(out_dir, "eval_report.txt"), "json": os.path.join(out_dir, "eval_results.json"),
             "excel": os.path.join(out_dir, "eval_runs.xlsx")}
    with open(paths["report"], "w", encoding="utf-8") as fh:
        fh.write(format_text(info) + "\n")
    with open(paths["json"], "w", encoding="utf-8") as fh:
        json.dump(info, fh, ensure_ascii=False, indent=2, default=str)
    wb = Workbook()
    ws = wb.active
    ws.title = "Model test"
    ws.append(["Question key", "Question", "Expected figures", "Old: correct", "Old: seconds", "Old: why wrong", "Old: answer",
               "New: correct", "New: seconds", "New: why wrong", "New: answer"])
    for a, b in zip(info["old"]["rows"], info["new"]["rows"]):
        ws.append([a["key"], a["question"], json.dumps(a["expected"], ensure_ascii=False), "yes" if a["passed"] else "NO", a["seconds"],
                   "; ".join(a["reasons"]), a["answer"], "yes" if b["passed"] else "NO", b["seconds"], "; ".join(b["reasons"]), b["answer"]])
    for cell in ws[1]:
        cell.font = Font(bold=True)
    for col, width in zip("ABCDEFGHIJK", (34, 50, 20, 9, 9, 30, 60, 9, 9, 30, 60)):
        ws.column_dimensions[col].width = width
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = Alignment(wrap_text=True, vertical="top")
    ws.freeze_panes = "A2"
    wb.save(paths["excel"])
    return paths
