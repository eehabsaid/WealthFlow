"""Turns a Markdown answer into plain, speakable chunks for a TTS endpoint (structural only, no word lists)."""

import re

from ai.services.exports.document import parse_markdown, plain

CHUNK_CHARS = 3500   # below the 4096-character input limit of common cloud TTS APIs
MAX_CHUNKS = 12      # longer answers are spoken up to this many chunks


def _arabic_letter_count(text):
    return sum("\u0600" <= char <= "\u06ff" for char in text if char.isalpha())


def normalize_spoken_text(text):
    """Remove redundant English glosses from Arabic and verbalize separators."""
    value = str(text or "")
    if _arabic_letter_count(value):
        value = re.sub(
            r"\s*[（(]\s*[^()（）]*[A-Za-z][^()（）]*[）)]",
            "",
            value,
        )
        value = re.sub(r"\s*/\s*", " أو ", value)
    value = value.replace("\\", " ")
    return re.sub(r"\s+", " ", value).strip()


def _table_lines(block):
    header = [plain(c) for c in block.header]
    lines = []
    for row in block.rows:
        cells = [plain(c) for c in row]
        pairs = [f"{h}: {c}" if h and c else c for h, c in zip(header, cells)] if header else cells
        line = normalize_spoken_text(", ".join(p for p in pairs if p))
        if line:
            lines.append(line + ".")
    return lines


def speakable_text(markdown):
    """Plain text, one line per heading / paragraph / bullet / table row; Markdown symbols removed."""
    lines = []
    for block in parse_markdown(str(markdown or "")):
        if block.kind == "table":
            lines.extend(_table_lines(block))
        elif block.kind == "heading":
            text = normalize_spoken_text(block.text.rstrip(".:"))
            if text:
                lines.append(text + ".")
        else:
            text = normalize_spoken_text(plain(block.text))
            if text:
                lines.append(text)
    return "\n".join(lines)


def _split_long(line, limit):
    parts = []
    while len(line) > limit:
        cut = max(line.rfind(". ", 0, limit), line.rfind(" ", 0, limit))
        cut = cut + 1 if cut > 0 else limit
        parts.append(line[:cut].strip())
        line = line[cut:].strip()
    if line:
        parts.append(line)
    return parts


def speech_chunks(markdown, limit=CHUNK_CHARS, max_chunks=MAX_CHUNKS):
    """Speakable text split on line boundaries into chunks of at most `limit` characters."""
    chunks, current = [], ""
    for line in speakable_text(markdown).splitlines():
        for piece in _split_long(re.sub(r"\s+", " ", line).strip(), limit):
            if current and len(current) + 1 + len(piece) > limit:
                chunks.append(current)
                current = ""
            current = f"{current}\n{piece}" if current else piece
    if current:
        chunks.append(current)
    return chunks[:max_chunks]
