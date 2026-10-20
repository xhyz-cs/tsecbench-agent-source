#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 James and minc
"""Tests for the keep_working Stop/SessionStart hook.

The hook is pure logic over stdin JSON plus two files, so all of it is pinned here —
no model, no container. What matters is that it keeps a session going without ever
hot-looping, and that it lets a session finish once the platform says there is
nothing left.

    python docker/claude/hooks/test_keep_working.py
    python -m unittest discover -s docker/claude/hooks -p 'test_*.py'

Stdlib only.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

HOOK = Path(__file__).resolve().parent / "keep_working.py"
LOOP_TEXT = "KEEP GOING: there is still work on the table."


class KeepWorkingHook(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="keep-working-")
        self.root = Path(self._tmp.name)
        self.prompt = self.root / "LOOP_PROMPT.md"
        self.prompt.write_text(
            "<!-- operator note, not for the model -->\n\n" + LOOP_TEXT + "\n",
            encoding="utf-8",
        )
        self.empty_prompt = self.root / "EMPTY.md"
        self.empty_prompt.write_text("<!-- only a comment -->\n", encoding="utf-8")
        self.state = self.root / "state"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def run_hook(self, payload, prompt=None, raw=None, env_extra=None):
        env = dict(os.environ)
        env["TSEC_STATE_DIR"] = str(self.state)
        env["TSEC_LOOP_PROMPT_FILE"] = str(
            prompt if prompt is not None else self.prompt
        )
        if env_extra:
            env.update(env_extra)
        done = subprocess.run(
            [sys.executable, str(HOOK)],
            input=raw if raw is not None else json.dumps(payload),
            capture_output=True,
            text=True,
            env=env,
            timeout=30,
        )
        return done.returncode, done.stdout.strip()

    def answer(self, payload, **kwargs):
        _, out = self.run_hook(payload, **kwargs)
        return json.loads(out)

    # -- SessionStart ---------------------------------------------------------- #

    def test_session_start_injects_the_loop_prompt(self):
        answer = self.answer({"hook_event_name": "SessionStart"})
        self.assertEqual(
            answer["hookSpecificOutput"]["additionalContext"], LOOP_TEXT
        )

    def test_operator_comment_never_reaches_the_model(self):
        _, out = self.run_hook({"hook_event_name": "SessionStart"})
        self.assertNotIn("operator note", out)

    # -- Stop ------------------------------------------------------------------ #

    def test_stop_is_blocked_with_the_loop_prompt(self):
        self.assertEqual(
            self.answer({"hook_event_name": "Stop"}),
            {"decision": "block", "reason": LOOP_TEXT},
        )

    def test_blocked_stop_writes_the_nudge_marker_and_an_audit_line(self):
        self.run_hook({"hook_event_name": "Stop"})
        self.assertTrue((self.state / "LAST_NUDGE").exists())
        self.assertTrue((self.state / "stop-hook.jsonl").exists())

    def test_a_second_stop_is_blocked_too_by_default(self):
        # "It cannot be stopped" is the point: there is no escape hatch unless an
        # operator switches one on.
        self.run_hook({"hook_event_name": "Stop"})
        self.assertEqual(self.answer({"hook_event_name": "Stop"})["decision"], "block")

    def test_stop_is_still_blocked_however_long_the_session_has_run(self):
        self.run_hook({"hook_event_name": "Stop"})
        (self.state / "LAST_NUDGE").write_text(str(time.time() - 3600), encoding="utf-8")
        self.assertEqual(self.answer({"hook_event_name": "Stop"})["decision"], "block")

    def test_platform_done_marker_lets_the_session_finish(self):
        self.state.mkdir(parents=True, exist_ok=True)
        (self.state / "STOP").write_text("no work left\n", encoding="utf-8")
        self.assertEqual(self.answer({"hook_event_name": "Stop"}), {})

    def test_escape_hatch_allows_a_repeat_stop_when_switched_on(self):
        # Off by default. An operator who decides a hot stop-loop costs more than an
        # idle session can switch it on.
        extra = {"TSEC_NUDGE_MIN_SECONDS": "3600"}
        self.run_hook({"hook_event_name": "Stop"}, env_extra=extra)
        self.assertEqual(self.answer({"hook_event_name": "Stop"}, env_extra=extra), {})

    # -- never block without a usable prompt ----------------------------------- #

    def test_comment_only_prompt_never_blocks(self):
        self.assertEqual(self.answer({"hook_event_name": "Stop"}, prompt=self.empty_prompt), {})

    def test_missing_prompt_never_blocks(self):
        self.assertEqual(
            self.answer({"hook_event_name": "Stop"}, prompt=self.root / "nope.md"), {}
        )

    # -- fail open ------------------------------------------------------------- #

    def test_non_json_stdin_still_exits_zero_and_answers_nothing(self):
        code, out = self.run_hook({}, raw="not json at all")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out), {})

    def test_unknown_event_answers_nothing(self):
        self.assertEqual(self.answer({"hook_event_name": "PreToolUse"}), {})

    def test_missing_event_field_answers_nothing(self):
        self.assertEqual(self.answer({}), {})

    def test_non_object_payload_answers_nothing(self):
        code, out = self.run_hook({}, raw='["not", "an", "object"]')
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out), {})


if __name__ == "__main__":
    unittest.main(verbosity=2)
