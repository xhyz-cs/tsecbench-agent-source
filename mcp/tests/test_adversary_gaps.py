#!/usr/bin/env python3
"""对质 gap tests for tsecbench_mcp — 29 green tests (was 28 + 1 documented RED).

Produced by the mutation-testing review (64 semantic mutants; the original
36-test suite killed 38/59 non-equivalent; adding these raises it to 58/59).

PLACEMENT
---------
Lives at ``mcp/tests/test_adversary_gaps.py`` (next to
``test_tsecbench_mcp.py``) and runs as usual::

    python -m unittest discover -s mcp/tests -t mcp/tests

It only imports the repo's own harness (``test_tsecbench_mcp`` -> boots
``mock_tsec_api.py``) and the standard library. No new dependencies.

COMPATIBILITY
-------------
* Every test pins CURRENT, correct behaviour. The former RED test
  (TestChallengePayloadShape, ``challenges.nonlist passthrough``) is now green:
  ``_challenges()`` raises ``bad_body`` on a malformed 200 body, so its
  ``@unittest.skip`` decorator was removed when that fix landed.
* Tests that bypass the platform and monkeypatch ``mcp._challenges`` /
  ``mcp.http_json`` / ``mcp.time`` / ``mcp.socket`` restore everything in a
  ``finally`` block, so they cannot leak state into neighbouring tests.
* TestHintTable pins the exact action strings of ERROR_TABLE / hint_for. Those
  strings are the run's contract; rewording them SHOULD fail these tests.
* Each test names the mutant id(s) it kills (ids match the review report).

MERGE NOTES (adaptations made while merging, mutant ids preserved)
------------------------------------------------------------------
* ``err.hint.completed.case``: after the confirmed M8 fix, the "completed"
  heuristic applies ONLY to the hint endpoint, so the case-insensitivity is
  now asserted with ``endpoint=API_HINT`` (a "completed"-worded 409 on any
  other endpoint is fatal by design; see TestErrorClassification in
  test_tsecbench_mcp.py for the fatal-side pin).
* ``challenges.nonlist passthrough``: skip removed; the test now guards the
  fix permanently.
"""

from __future__ import annotations

import os
import socket
import tempfile
import types
import unittest
from pathlib import Path

import test_tsecbench_mcp as harness  # repo harness: mock boot, fixtures, _control
import tsecbench_mcp as mcp

_control = harness._control
MockBackedTest = harness.MockBackedTest

# Module fixtures: unittest looks these up in *this* module, so re-export the
# harness's boot/teardown or no mock is ever started for these tests.
setUpModule = harness.setUpModule
tearDownModule = harness.tearDownModule


# ======================================================================================
# Pure logic - no mock, no network. The error table is the run's decision procedure.
# ======================================================================================

class TestHintTable(unittest.TestCase):
    DOCUMENTED_CODES = {"task_not_found", "challenge_not_found", "duplicate",
                        "resource_unavailable", "internal_error"}

    # pins: ERROR_TABLE contract (exact code set + no copy-paste-stub advice)
    def test_every_documented_code_has_an_entry_with_distinct_advice(self) -> None:
        self.assertEqual(set(mcp.ERROR_TABLE), self.DOCUMENTED_CODES,
                         "ERROR_TABLE must cover exactly the documented business codes")
        advices = {advice for advice, _ in mcp.ERROR_TABLE.values()}
        self.assertEqual(len(advices), len(mcp.ERROR_TABLE),
                         "two codes sharing one advice string is a copy-paste stub")
        for advice, fatal in mcp.ERROR_TABLE.values():
            self.assertTrue(advice.strip())
            self.assertIsInstance(fatal, bool)

    # kills: err.table.resource_unavailable.fatal, err.table.internal_error.fatal
    #        (re-kills task_not_found / challenge_not_found / duplicate flips)
    def test_fatal_flags_match_the_runbook(self) -> None:
        expected = {
            "task_not_found": True,        # token/task gone: stop everything
            "challenge_not_found": False,  # skip this challenge
            "duplicate": False,            # idempotent, never retry
            "resource_unavailable": False, # retry later or swap challenge
            "internal_error": False,       # retry once
        }
        for code, fatal in expected.items():
            advice, is_fatal = mcp.hint_for(code, "mock message", 500)
            with self.subTest(code=code):
                self.assertIs(is_fatal, fatal, f"{code} fatality is part of the contract")
                self.assertTrue(advice.strip())

    # kills: err.hint.maxactive.case
    def test_invalid_state_max_active_is_recoverable_and_case_insensitive(self) -> None:
        for message in ("max active challenge instances reached",
                        "MAX ACTIVE challenge instances reached",
                        "Max Active reached"):
            advice, fatal = mcp.hint_for("invalid_state", message, 409)
            with self.subTest(message=message):
                self.assertFalse(fatal, "cap pressure must never abort the run")
                self.assertIn("close_challenge", advice)

    # kills: err.hint.completed.case
    # (M8: the completed heuristic is scoped to the hint endpoint, so the
    # case-insensitivity is asserted there; other endpoints stay fatal.)
    def test_invalid_state_completed_is_recoverable_on_the_hint_endpoint(self) -> None:
        for message in ("challenge already completed", "Challenge Already COMPLETED"):
            advice, fatal = mcp.hint_for("invalid_state", message, 409, endpoint=mcp.API_HINT)
            with self.subTest(message=message):
                self.assertFalse(fatal)
                self.assertIn("通关", advice)

    # re-pins: err.hint.fallback.recoverable (suite only caught this via 6 subTests)
    def test_invalid_state_task_ended_is_fatal(self) -> None:
        for message in ("benchmark task has ended", "BENCHMARK TASK HAS ENDED"):
            advice, fatal = mcp.hint_for("invalid_state", message, 409)
            with self.subTest(message=message):
                self.assertTrue(fatal, "an ended task must stop the whole run")
                self.assertIn("停止", advice)

    # pins: fail-closed default for an unrecognised invalid_state message
    def test_invalid_state_with_unknown_message_fails_closed(self) -> None:
        advice, fatal = mcp.hint_for("invalid_state", "something entirely new", 409)
        self.assertTrue(fatal, "an unrecognised invalid_state must stop the run, not loop")
        self.assertTrue(advice.strip())

    # kills: err.hint.422.dropped
    def test_framework_422_is_a_parameter_fix(self) -> None:
        advice, fatal = mcp.hint_for(None, "框架校验错误: []", 422)
        self.assertFalse(fatal)
        self.assertIn("修正参数", advice)

    # pins: generic fallback stays recoverable and names the status code
    def test_unknown_code_gets_generic_recoverable_advice(self) -> None:
        advice, fatal = mcp.hint_for(None, "", 418)
        self.assertFalse(fatal)
        self.assertIn("418", advice)


class TestProtocolContract(unittest.TestCase):
    # kills: dispatch.unknown_tool.code
    def test_unknown_tool_is_invalid_params(self) -> None:
        response = mcp.handle_request({
            "jsonrpc": "2.0", "id": 90, "method": "tools/call",
            "params": {"name": "definitely_not_a_tool"},
        })
        self.assertIn("error", response)
        self.assertEqual(response["error"]["code"], -32602,
                         "an unknown tool is a bad request (-32602), not a missing method")

    # kills: cap.max_active.default4
    def test_max_active_defaults_to_three(self) -> None:
        saved = os.environ.pop("TSEC_MAX_ACTIVE", None)
        try:
            self.assertEqual(mcp.max_active(), 3,
                             "the documented default must match the platform cap")
        finally:
            if saved is not None:
                os.environ["TSEC_MAX_ACTIVE"] = saved

    # kills: vpn.bad_body.guard.dropped
    def test_vpn_check_with_a_non_json_body_is_a_hard_no(self) -> None:
        real = mcp.http_json
        mcp.http_json = lambda *a, **k: "<html>gateway error page</html>"
        try:
            result = mcp.tool_vpn_check()
        finally:
            mcp.http_json = real
        self.assertFalse(result["ok"], result)
        self.assertEqual(result["code"], "bad_body")

    # kills: vpn.bad_body.guard.dropped (list-body branch)
    def test_vpn_check_with_a_non_dict_body_is_a_hard_no(self) -> None:
        real = mcp.http_json
        mcp.http_json = lambda *a, **k: ["unexpected", "array"]
        try:
            result = mcp.tool_vpn_check()
        finally:
            mcp.http_json = real
        self.assertFalse(result["ok"], result)
        self.assertEqual(result["code"], "bad_body")


# ======================================================================================
# task_status accounting
# ======================================================================================

class TestTaskStatusAccounting(MockBackedTest):
    # kills: cap.free_slots.ignored
    def test_free_slots_accounts_for_running_containers(self) -> None:
        # list_challenges sorts by level, so the 503 fixture can sit anywhere:
        # classify first (never skipTest on it), then start what is startable.
        codes = []
        for item in self.challenges:
            if item["is_completed"]:
                continue
            started = mcp.tool_start_challenge(item["unique_code"])
            if started.get("code") == "resource_unavailable":
                continue
            self.assertTrue(started["ok"], started)
            codes.append(item["unique_code"])
            if len(codes) == 2:
                break
        self.assertGreaterEqual(len(codes), 2, "need two startable fixtures")

        status = mcp.tool_task_status()
        self.assertEqual(status["max_active"] - len(codes), status["free_slots"],
                         "free_slots must subtract the containers actually running")
        self.assertEqual(sorted(status["active_containers"]), sorted(codes))
        for code in codes:
            self.assertTrue(mcp.tool_close_challenge(code)["ok"])

    # kills: cap.next_candidates.unbounded
    def test_next_candidates_are_untouched_and_bounded(self) -> None:
        status = mcp.tool_task_status()
        self.assertTrue(status["next_candidates"])
        self.assertLessEqual(len(status["next_candidates"]), status["max_active"],
                             "next_candidates must not suggest more work than slots allow")
        listed = {c["unique_code"]: c for c in mcp.tool_list_challenges()["challenges"]}
        for code in status["next_candidates"]:
            item = listed[code]
            self.assertFalse(item["is_completed"])
            self.assertEqual(item["correct_flag_count"], 0)

    # kills: as_int.neg1
    def test_task_status_survives_non_numeric_platform_fields(self) -> None:
        real = mcp._challenges
        mcp._challenges = lambda: [{
            "unique_code": "odd-fixture", "description": None, "difficulty": "easy",
            "level": "not-a-number", "total_score": None, "flag_count": None,
            "correct_flag_count": None, "is_completed": False,
            "container_status": "stopped", "container_addr": [],
        }]
        try:
            status = mcp.tool_task_status()
        finally:
            mcp._challenges = real
        self.assertTrue(status["ok"], status)
        self.assertEqual(status["total_challenges"], 1)
        self.assertGreaterEqual(status["flags"]["correct"], 0)
        self.assertGreaterEqual(status["flags"]["total"], 0)
        self.assertGreaterEqual(status["total_score_possible"], 0)
        self.assertEqual(status["not_started"], 1)


# ======================================================================================
# wait_for_ready edge cases (deterministic: the platform is bypassed, the clock is faked)
# ======================================================================================

def _fixture(code: str, status: str, addr: list) -> list:
    return [{
        "unique_code": code, "description": "x", "difficulty": "easy", "level": 1,
        "total_score": 100, "flag_count": 1, "correct_flag_count": 0,
        "is_completed": False, "container_status": status, "container_addr": addr,
    }]


class TestWaitForReadyEdges(MockBackedTest):
    def _run_with_fake_clock(self, code: str, status: str, addr: list,
                             timeout_s: int = 2) -> dict:
        real_challenges, real_time = mcp._challenges, mcp.time
        clock = {"t": 0.0}
        mcp._challenges = lambda: _fixture(code, status, addr)
        mcp.time = types.SimpleNamespace(
            monotonic=lambda: clock["t"],
            sleep=lambda s: clock.__setitem__("t", clock["t"] + s),
        )
        try:
            return mcp.tool_wait_for_ready(code, timeout_s=timeout_s, interval_s=1)
        finally:
            mcp._challenges, mcp.time = real_challenges, real_time

    # kills: wait.timeout.returns_success
    def test_timeout_is_reported_as_a_failure_not_as_ready(self) -> None:
        result = self._run_with_fake_clock("stuck-challenge", "pending", [])
        self.assertFalse(result["ok"], "a timeout must never be reported as ok:True")
        self.assertEqual(result["code"], "local_timeout")
        self.assertEqual(result["container_status"], "pending")

    # kills: wait.available.empty_addr_ok
    def test_available_without_an_address_is_not_ready(self) -> None:
        result = self._run_with_fake_clock("addrless-challenge", "available", [])
        self.assertFalse(result["ok"],
                         "available with an empty container_addr is not actionable")
        self.assertEqual(result["code"], "local_timeout")
        self.assertEqual(result["container_status"], "available")


# ======================================================================================
# probe_target validation and diagnosis
# ======================================================================================

class TestProbeTargetValidation(MockBackedTest):
    # kills: guard.port_range.dropped
    def test_port_out_of_range_is_rejected(self) -> None:
        for port in (0, -1, 65536, 100000):
            with self.subTest(port=port):
                result = mcp.tool_probe_target("127.0.0.1", port, timeout_s=0.5)
                self.assertFalse(result["ok"], result)
                self.assertEqual(result["code"], "invalid_argument")

    # kills: guard.host_empty.dropped
    def test_empty_host_is_rejected(self) -> None:
        for host in ("", "   "):
            with self.subTest(host=host):
                result = mcp.tool_probe_target(host, 80, timeout_s=0.5)
                self.assertFalse(result["ok"], result)
                self.assertEqual(result["code"], "invalid_argument")


class TestProbeTargetDiagnostics(MockBackedTest):
    """The tool exists to tell 'VPN is down' from 'this service is down'."""

    # re-pins: probe.timeout_refused.swapped (refused direction: action must name
    # wait_for_ready, not the VPN). Injected rather than dialled: on Windows a closed
    # localhost port TIMES OUT, so dialling cannot reliably reach the refused branch.
    def test_connection_refused_points_at_the_container(self) -> None:
        real_connect = mcp.socket.create_connection

        def refuse(*args, **kwargs):
            raise ConnectionRefusedError("[WinError 10061] target actively refused")

        mcp.socket.create_connection = refuse
        try:
            result = mcp.tool_probe_target("10.0.1.5", 8080, timeout_s=1)
        finally:
            mcp.socket.create_connection = real_connect
        self.assertFalse(result["ok"])
        self.assertEqual(result["reason"], "refused_or_unresolved")
        self.assertIn("wait_for_ready", result["action"],
                      "a refused connection must suggest wait_for_ready, not the VPN")

    # re-pins: probe.timeout_refused.swapped (timeout direction: action must name
    # vpn_check and must NOT name wait_for_ready) + pins the reason field
    def test_connect_timeout_points_at_the_vpn(self) -> None:
        real_connect = mcp.socket.create_connection

        def hang(*args, **kwargs):
            raise socket.timeout("timed out")

        mcp.socket.create_connection = hang
        try:
            result = mcp.tool_probe_target("10.0.1.5", 8080, timeout_s=0.5)
        finally:
            mcp.socket.create_connection = real_connect
        self.assertFalse(result["ok"])
        self.assertEqual(result["reason"], "timeout")
        self.assertIn("vpn_check", result["action"])
        self.assertNotIn("wait_for_ready", result["action"],
                         "a timeout must suggest the VPN first, not a container restart")


# ======================================================================================
# submit_flag local validation
# ======================================================================================

class TestSubmitValidation(MockBackedTest):
    # kills: guard.flag_length.dropped
    def test_oversized_flag_is_rejected_before_the_platform_sees_it(self) -> None:
        code = self.fresh()["unique_code"]
        before = _control("/openapi/v1/_test/state", "GET")["submission_count"]
        result = mcp.tool_submit_flag(code, "x" * 4097)
        self.assertFalse(result["ok"], result)
        self.assertEqual(result["code"], "invalid_argument")
        after = _control("/openapi/v1/_test/state", "GET")["submission_count"]
        self.assertEqual(before, after, "an oversized flag must never reach the platform")

    # pins: guard.flag_length exact upper bound (4096 accepted)
    def test_flag_of_exactly_4096_chars_is_accepted(self) -> None:
        code = self.fresh()["unique_code"]
        result = mcp.tool_submit_flag(code, "x" * 4096)
        self.assertTrue(result["ok"], result)
        self.assertFalse(result["correct"], "a 4096-char non-flag is simply incorrect")


# ======================================================================================
# the notes ledger, beyond "one key round-trips"
# ======================================================================================

class TempNotesDir(MockBackedTest):
    """MockBackedTest isolation plus a throwaway ledger directory."""

    def setUp(self) -> None:
        super().setUp()
        self._tmp = tempfile.TemporaryDirectory()
        self._previous = os.environ.get("TSEC_STATE_DIR")
        os.environ["TSEC_STATE_DIR"] = self._tmp.name

    def tearDown(self) -> None:
        if self._previous is None:
            os.environ.pop("TSEC_STATE_DIR", None)
        else:
            os.environ["TSEC_STATE_DIR"] = self._previous
        self._tmp.cleanup()


class TestNotesLedgerSemantics(TempNotesDir):
    # kills: notes.filter.ignored
    def test_key_filter_returns_only_that_keys_notes(self) -> None:
        mcp.tool_note_save("web_01", "first")
        mcp.tool_note_save("crypto_02", "unrelated")
        mcp.tool_note_save("web_01", "second")
        filtered = mcp.tool_note_list(key="web_01")
        self.assertEqual([n["value"] for n in filtered["notes"]], ["first", "second"])
        self.assertEqual(filtered["count"], 2)

    # re-pins: notes.save.overwrite (append-only, order preserved)
    def test_notes_append_and_keep_order(self) -> None:
        for value in ("first", "second", "third"):
            mcp.tool_note_save("web_01", value)
        ledger = mcp.tool_note_list()
        self.assertEqual([n["value"] for n in ledger["notes"]], ["first", "second", "third"])

    # kills: notes.torn_line.fatal
    def test_torn_final_line_is_tolerated(self) -> None:
        mcp.tool_note_save("web_01", "kept")
        path = Path(os.environ["TSEC_STATE_DIR"]) / "notes.jsonl"
        with path.open("a", encoding="utf-8") as handle:
            handle.write('{"ts": "t", "key": "torn"')  # crash mid-write
        ledger = mcp.tool_note_list()
        self.assertEqual([n["value"] for n in ledger["notes"]], ["kept"])

    # kills: notes.limit.clamp.dropped
    def test_limit_returns_the_newest_tail(self) -> None:
        for i in range(5):
            mcp.tool_note_save("k", str(i))
        tail = mcp.tool_note_list(limit=2)
        self.assertEqual([n["value"] for n in tail["notes"]], ["3", "4"])
        self.assertEqual(len(mcp.tool_note_list(limit=-3)["notes"]), 1,
                         "limit is clamped to at least 1")
        self.assertTrue(mcp.tool_note_list(limit=0)["ok"], "limit 0 is clamped, not rejected")


# ======================================================================================
# the uniform-payload contract for the one tool that can still raise
# ======================================================================================

class TestErrorContract(MockBackedTest):
    # kills: decorator.tool_close_all_challenges.removed
    def test_close_all_reports_errors_instead_of_raising(self) -> None:
        _control("/openapi/v1/_test/expire")
        result = mcp.tool_close_all_challenges(confirm=True)
        self.assertIsInstance(result, dict)
        self.assertFalse(result["ok"], result)
        self.assertEqual(result["code"], "invalid_state")
        self.assertTrue(result["fatal"], "an ended task must stop the run")


# ======================================================================================
# Formerly RED: pinned production bug #1 ("challenges.nonlist passthrough").
# The bug is fixed - _challenges() raises bad_body on a malformed 200 body - so the
# @unittest.skip decorator was removed and this is now a permanent guard.
# ======================================================================================

class TestChallengePayloadShape(MockBackedTest):
    # kills: challenges.nonlist passthrough
    def test_a_non_list_challenge_payload_is_not_read_as_zero_challenges(self) -> None:
        real = mcp.http_json
        mcp.http_json = lambda *a, **k: {"detail": "gateway error, not a list"}
        try:
            result = mcp.tool_list_challenges()
        finally:
            mcp.http_json = real
        self.assertFalse(result["ok"], result)
        self.assertNotEqual(result.get("count"), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
