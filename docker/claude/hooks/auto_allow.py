#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 James and minc
"""Auto-approve every Claude Code hook decision point.

Second layer of autonomy (the first is `--dangerously-skip-permissions`). This hook
answers the two events that can stop an unattended run — `PreToolUse` (tool gating)
and `PermissionRequest` (an explicit permission prompt) — with "allow", and marks
notifications as suppressed so nothing waits on a human.

Loaded via the `hooks` block of settings.json, so it only applies to this container's runs.

Fails OPEN by design: a hook that raises, or feeds back an unparseable payload, must
never wedge an 8-hour run. Always exits 0.
"""

from __future__ import annotations

import json
import sys

# Hook payloads use snake_case (hook_event_name); decisions use hookSpecificOutput.
DECISION_EVENTS = {"PreToolUse", "PermissionRequest"}


def decision_for(event: str) -> dict:
    if event == "PermissionRequest":
        return {
            "hookSpecificOutput": {
                "hookEventName": "PermissionRequest",
                "decision": {"behavior": "allow"},
            }
        }
    if event == "Notification":
        return {"suppressOutput": True}
    return {
        "hookSpecificOutput": {
            "hookEventName": event or "PreToolUse",
            "permissionDecision": "allow",
            "permissionDecisionReason": "tsecbench autonomous run: pre-approved by policy",
        }
    }


def main() -> int:
    raw = sys.stdin.read() or "{}"
    try:
        payload = json.loads(raw)
    except ValueError:
        payload = {}
    event = str(payload.get("hook_event_name") or "")

    try:
        decision = decision_for(event)
    except Exception:  # noqa: BLE001 - never let the hook break the run
        decision = {}
    print(json.dumps(decision, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:  # noqa: BLE001 - fail open, always
        print("{}")
        raise SystemExit(0)
