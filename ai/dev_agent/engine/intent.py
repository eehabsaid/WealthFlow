"""Is a task a request to CHANGE files, or only a question? Decided from the owner's own words and from what the model claims (no model judgement), so a model that
says "done" without planning or editing cannot turn a change request into an answer. A task that says "Answer only; do not plan ..." or asks a question stays read-only.

The one honest exception: a change task that is really already satisfied. The model may then answer
  NO CHANGE NEEDED: <why> | EVIDENCE: <path>: <exact text that is in that file now>
and the answer is accepted only when that text is really in that file (checked here, not believed)."""

from __future__ import annotations

import re

VERBS = ("add|write|fix|rename|remove|delete|create|implement|refactor|update|change|replace|move|convert|rewrite|extract|insert|make|annotate|document|set|introduce|apply|enable|"
         "disable|handle|support|adjust|modify|tidy|clean|split|merge|wrap|guard|validate|log|patch|correct|improve|optimi[sz]e|simplify|reorder|drop|deprecate|migrate|port|bump|"
         "inline|comment|translate|locali[sz]e|cache|expose|hide|reformat|sort|dedupe|deduplicate|standardi[sz]e|harden|cover|test|install|upgrade|revert|restore|append|prepend|fill|complete")
READ_ONLY = re.compile(r"answer only|do not plan|don't plan|read[- ]only", re.I)
QUESTION = re.compile(r"^\s*(?:what|where|which|who|why|how|when|does|do|is|are|can|explain|describe|summari[sz]e|list|show|tell|find|check)\b", re.I)
CHANGE = re.compile(rf"(?:^|[.:;!,]\s+|\b(?:and|then|also|first|next)\s+)(?:please\s+)?(?:{VERBS})\b", re.I)
WANTED = re.compile(r"\b(?:has no|have no|is missing|are missing|lacks?|needs? (?:to|a|an)|should (?:be|have|use|return)|must (?:be|have)|is not|isn't|is wrong|is broken|fails?|does not (?:work|handle))\b", re.I)
CLAIM = re.compile(r"^\W*(?:added|updated|changed|fixed|created|implemented|modified|replaced|renamed|removed|deleted|wrote|written)\b|"
                   r"\b(?:i|we)(?:'ve| have)?\s+(?:just\s+)?(?:added|updated|changed|fixed|created|implemented|modified|replaced|renamed|removed|deleted|wrote|written)\b|"
                   r"\bhas been (?:added|updated|changed|fixed|created|implemented|modified|replaced|renamed|removed|deleted)\b", re.I)
ESCAPE = re.compile(r"^\W*NO CHANGE NEEDED\b.*?\bEVIDENCE:\s*(?P<path>[^\s:]+(?:\\[^\s:]+)*)\s*:\s*(?P<text>.{8,})$", re.I | re.S)


STUB = re.compile(r"^\W*(?:ok(?:ay)?[,.]?\s+)?(?:i(?:'ll| will|'m going to| am going to)|let me|let's|first,? i|now i|going to)\b[^.?!:]{0,60}\b(?:read|look|check|open|inspect|investigate|search|examine)\b", re.I)


def is_stub(answer: str) -> bool:
    """A promise instead of an answer ("I'll read the file to answer."): the trained model sometimes ends a question this way without having read anything."""
    text = (answer or "").strip()
    return len(text) <= 240 and "\n" not in text and bool(STUB.match(text))


def needs_changes(task: str) -> bool:
    text = (task or "").strip()
    if READ_ONLY.search(text) or QUESTION.match(text):
        return False
    return bool(CHANGE.search(text) or WANTED.search(text))


def claims_change(answer: str) -> bool:
    """The model says it changed something (in the read-only planning phase nothing can have been changed)."""
    return bool(CLAIM.search(answer or ""))


def evidence_ok(project, answer: str) -> bool:
    """`NO CHANGE NEEDED ... EVIDENCE: path: exact text`, and that text really is in that file (inside the project) right now."""
    m = ESCAPE.match((answer or "").strip())
    if not m:
        return False
    path = (project.root / m["path"].replace("\\", "/")).resolve()
    try:
        path.relative_to(project.root.resolve())
        return m["text"].strip() in path.read_text(encoding="utf-8", errors="replace")
    except (ValueError, OSError):
        return False


def refuse(project, task: str, answer: str) -> str:
    """The reason (the text sent back to the model) when a `final` answer in the planning phase must not count, else "". A promise to read is never an answer;
    a change task (or a claim of having changed something) with no plan and no real evidence is not finished."""
    if is_stub(answer):
        return NO_READ
    return NO_PLAN if (needs_changes(task) or claims_change(answer)) and not evidence_ok(project, answer) else ""


def wrote_files(ledger) -> bool:
    """True when this task really changed a file on disk (written, deleted or left half-rolled-back)."""
    return any(f["state"] in ("written", "deleted", "rollback_failed") for f in ledger.data["files"].values())


NO_PLAN = ("You answered, but the TASK asks you to change files, and no change was made. A change task is never finished by words: submit a plan (submit_plan, or {\"plan\": ...}) "
           "naming the file to edit. Do not say it is done. Only if the file already satisfies the task, answer "
           "`NO CHANGE NEEDED: <why> | EVIDENCE: <path>: <exact text copied from that file>`; the text is checked against the file.")

NO_CHANGE = ("You answered, but the TASK asks you to change files and no file was changed. A change task is never finished by words: make the change now with edit_file, edit_files or "
             "write_file, then answer. Only if the file already satisfies the task, answer "
             "`NO CHANGE NEEDED: <why> | EVIDENCE: <path>: <exact text copied from that file>`; the text is checked against the file.")

NO_READ = ("Your answer was only a promise to read, not an answer. Use read_file, grep or search_index now to look at the code, then answer for real "
           "and cite the files you read.")

FAILED = {NO_PLAN: "FAILED: the model claimed the task was done without a plan or an edit (nothing was changed)",
          NO_CHANGE: "FAILED: the model claimed the task was done without changing any file (nothing was changed)",
          NO_READ: "FAILED: the model answered with a promise to read instead of reading the code and answering"}
