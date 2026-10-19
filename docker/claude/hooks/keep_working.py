#!/usr/bin/env python3
"""Keep an unattended session working: answer Claude Code's Stop with "not yet".

Third layer of autonomy, after the two that answer permission questions
(`--dangerously-skip-permissions`, then auto_allow.py). This one answers the
question that actually ends an unattended run: *may I stop now?* On `Stop` the hook
gets the last word, and here the last word is docker/claude/LOOP_PROMPT.md — read
fresh on every stop, so the operator can rewrite it between runs without rebuilding
the image.

Nothing is ever typed into the session from outside: nobody is watching, and a
message pushed in by a wrapper would be indistinguishable from a real user turn.
The nudge comes from inside, from the session's own event loop.

The stop is allowed through only when
  * the platform says there is nothing left to solve — the supervisor writes
    $TSEC_STATE_DIR/STOP for exactly this, or
  * the loop prompt is empty or unreadable, so there is nothing to say.

TSEC_NUDGE_MIN_SECONDS (default 0 = never) can additionally let a stop through when
one was just nudged. It is an escape hatch, not a default: under `claude --bg` an
allowed stop does not end the process, it leaves the session sitting idle with nobody
to wake it, which is a stall until the window closes — strictly worse than a session
that keeps being told to carry on.

`SessionStart` gets the same text as additional context, so a fresh session starts
out knowing what the loop is for.

Loaded via the `hooks` block of settings.json. Fails OPEN and always exits 0: a
broken hook must never wedge the run.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

DEFAULT_LOOP_PROMPT = "/opt/tsecbench/claude/LOOP_PROMPT.md"
DEFAULT_NUDGE_MIN_SECONDS = 0.0


def state_dir() -> Path:
    return Path(os.environ.get("TSEC_STATE_DIR", "/work/state"))


def loop_prompt() -> str:
    """The loop prompt, with the shipped placeholder's ownership comment removed."""
    path = Path(os.environ.get("TSEC_LOOP_PROMPT_FILE", DEFAULT_LOOP_PROMPT))
    try:
        text = path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""
    if text.startswith("<!--"):
        end = text.find("-->")
        if end != -1:
            text = text[end + 3:].lstrip()
    return text


def nudge_min_seconds() -> float:
    try:
        return float(os.environ.get("TSEC_NUDGE_MIN_SECONDS", DEFAULT_NUDGE_MIN_SECONDS))
    except ValueError:
        return DEFAULT_NUDGE_MIN_SECONDS


def task_is_over() -> bool:
    return (state_dir() / "STOP").exists()


def seconds_since_last_nudge() -> float | None:
    try:
        last = float((state_dir() / "LAST_NUDGE").read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return None
    return time.time() - last


def record(event: str, **fields: object) -> None:
    """Append to the audit trail. Never raises: this is diagnostics, not control."""
    try:
        state_dir().mkdir(parents=True, exist_ok=True)
        with (state_dir() / "stop-hook.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(
                {"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "event": event, **fields},
                ensure_ascii=False,
            ) + "\n")
    except OSError:
        pass


def mark_nudge() -> None:
    try:
        state_dir().mkdir(parents=True, exist_ok=True)
        (state_dir() / "LAST_NUDGE").write_text(str(time.time()), encoding="utf-8")
    except OSError:
        pass


def session_start_output() -> dict:
    text = loop_prompt()
    if not text:
        record("session_start", injected=False, reason="loop prompt empty or unreadable")
        return {}
    record("session_start", injected=True, chars=len(text))
    return {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": text,
        }
    }


def stop_output(payload: dict) -> dict:
    if task_is_over():
        record("stop_allowed", reason="platform reports no work left")
        return {}

    since = seconds_since_last_nudge()
    if since is not None and nudge_min_seconds() > 0 and since < nudge_min_seconds():
        # The escape hatch, off by default. See the module docstring: letting a
        # --bg session stop leaves it idle with nobody to wake it, so this exists
        # only for an operator who has decided a hot stop-loop costs more.
        record("stop_allowed", reason="nudged recently", seconds_since=round(since, 1))
        return {}

    text = loop_prompt()
    if not text:
        record("stop_allowed", reason="loop prompt empty or unreadable")
        return {}

    mark_nudge()
    record(
        "stop_blocked",
        chars=len(text),
        stop_hook_active=bool(payload.get("stop_hook_active")),
        seconds_since_previous=None if since is None else round(since, 1),
    )
    return {"decision": "block", "reason": text}


def main() -> int:
    raw = sys.stdin.read() or "{}"
    try:
        payload = json.loads(raw)
    except ValueError:
        payload = {}
    if not isinstance(payload, dict):
        payload = {}

    event = str(payload.get("hook_event_name") or "")
    if event == "SessionStart":
        output = session_start_output()
    elif event == "Stop":
        output = stop_output(payload)
    else:
        output = {}

    print(json.dumps(output, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:  # noqa: BLE001 - fail open, always
        print("{}")
        raise SystemExit(0)
