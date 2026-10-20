#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 James and minc
"""Tests for tsecbench_mcp._task_state — the supervisor's stop/go verdict.

`_task_state` decides whether the container works or idles, and it is the one place
where "the platform said stop" and "we could not ask" must not be confused. The
container never exits, so a wrong "stop" leaves an idle container for the rest of the
window while a wrong "work" only costs one wasted session. Both directions are pinned
here, plus the CLI wiring, because a flag dropped from argparse would be silent.

    python -m unittest discover -s mcp/tests -t mcp/tests

Stdlib only, and no ports: the platform is stubbed in-process.
"""

from __future__ import annotations

import contextlib
import io
import os
import subprocess
import sys
import unittest
from pathlib import Path

MCP_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(MCP_DIR))
import tsecbench_mcp as mcp  # noqa: E402


def verdict(token, status) -> str:
    """``_task_state``'s one-word answer, with the platform stubbed out."""
    real_token, real_status = mcp.token, mcp.tool_task_status
    mcp.token = lambda: token
    mcp.tool_task_status = lambda: status
    buffer = io.StringIO()
    try:
        with contextlib.redirect_stdout(buffer):
            mcp._task_state()
    finally:
        mcp.token, mcp.tool_task_status = real_token, real_status
    return buffer.getvalue().strip()


class TaskStateVerdict(unittest.TestCase):
    def test_no_token_keeps_working(self):
        # A missing token cannot be fixed by stopping, and a park is a last resort, so
        # the supervisor stays in the working state and lets its other guards decide.
        self.assertEqual(verdict(None, {}), "work")

    def test_platform_refusing_fatally_stops(self):
        self.assertEqual(verdict("t", {"ok": False, "fatal": True}), "stop")

    def test_transient_failure_keeps_working(self):
        for status in (
            {"ok": False, "fatal": False, "code": "local_connection_error"},
            {"ok": False, "fatal": False, "code": "local_timeout"},
            {
                "ok": False,
                "fatal": False,
                "code": "invalid_state",
                "message": "max active instances reached",
            },
        ):
            with self.subTest(code=status.get("code")):
                self.assertEqual(verdict("t", status), "work")

    def test_every_challenge_solved_stops(self):
        self.assertEqual(
            verdict("t", {"ok": True, "total_challenges": 3, "completed": 3}), "stop"
        )

    def test_work_remaining_keeps_working(self):
        self.assertEqual(
            verdict("t", {"ok": True, "total_challenges": 3, "completed": 2}), "work"
        )

    def test_empty_challenge_list_keeps_working(self):
        # "the list is empty" is not "there is no work": a task whose fixtures have not
        # populated yet must not park the container.
        self.assertEqual(
            verdict("t", {"ok": True, "total_challenges": 0, "completed": 0}), "work"
        )

    def test_more_completed_than_total_still_stops(self):
        # The platform is the authority; the comparison is >=, not ==.
        self.assertEqual(
            verdict("t", {"ok": True, "total_challenges": 2, "completed": 3}), "stop"
        )

    def test_answer_is_always_exactly_one_word(self):
        for status in (
            {"ok": True, "total_challenges": 1, "completed": 0},
            {"ok": False, "fatal": True},
            {"ok": False, "fatal": False},
        ):
            with self.subTest(status=status):
                self.assertIn(verdict("t", status), ("stop", "work"))


class TaskStateCli(unittest.TestCase):
    def test_cli_flag_prints_a_verdict_and_exits_zero(self):
        env = dict(os.environ)
        # Another module in this suite sets these for its own mock; without them this
        # subprocess would try to reach the real platform.
        env.pop("BENCHMARK_TOKEN", None)
        env.pop("TSEC_TOKEN", None)
        done = subprocess.run(
            [sys.executable, str(MCP_DIR / "tsecbench_mcp.py"), "--task-state"],
            capture_output=True,
            text=True,
            env=env,
            timeout=60,
        )
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(done.stdout.strip(), "work")


if __name__ == "__main__":
    unittest.main(verbosity=2)
