"""Server-sent events for a task's event log (id = sequence number, so a reconnecting client resumes with Last-Event-ID)."""

from __future__ import annotations

import json

from ai.dev_agent.server.http import Stream


def stream_events(log, after: int, stopping) -> Stream:
    def run(write):
        seq = after
        write("retry: 2000\n\n")
        while not stopping.is_set():
            events = log.wait(seq, 10)
            for event in events:
                write(f"id: {event['seq']}\nevent: {event['type']}\ndata: {json.dumps(event, ensure_ascii=False)}\n\n")
                seq = event["seq"]
            if not events:
                if log.closed:
                    return
                write(": keepalive\n\n")
    return Stream(run)
