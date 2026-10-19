#!/usr/bin/env python3
"""Integration tests for tsecbench_mcp against the mock TSecBench API.

Stdlib only (``unittest``), so it also runs inside the evaluation sandbox where
installing pytest is not an option.

    python -m unittest discover -s mcp/tests -v
    python mcp/tests/test_tsecbench_mcp.py

The suite boots ``mock_tsec_api.py`` as a subprocess and drives the real MCP tool
functions over real HTTP, plus the JSON-RPC dispatch layer. Fixtures are *discovered*
from the API rather than hard-coded, so the tests survive fixture reshuffles.
"""

from __future__ import annotations

import ast
import json
import os
import socket
import subprocess
import sys
import time
import unittest
import urllib.request
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
MCP_DIR = TESTS_DIR.parent
REPO_ROOT = MCP_DIR.parent

sys.path.insert(0, str(MCP_DIR))
import tsecbench_mcp as mcp  # noqa: E402  (path set up above on purpose)

MOCK_SCRIPT = TESTS_DIR / "mock_tsec_api.py"

# Loopback ports far from the defaults so a concurrent suite run in another worktree
# can never hijack or collide with this mock.
API_PORT = 18499
CHALLENGE_PORT = 18498
VPN_PORT = 18497
TOKEN = "test-token"

API_BASE = f"http://127.0.0.1:{API_PORT}"
VPN_BASE = f"http://127.0.0.1:{VPN_PORT}"

_process: subprocess.Popen | None = None


# --------------------------------------------------------------------------------------
# Harness
# --------------------------------------------------------------------------------------

def _port_open(port: int, timeout: float = 0.3) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=timeout):
            return True
    except OSError:
        return False


def _wait_for_port(port: int, timeout: float = 20.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if _port_open(port):
            return True
        time.sleep(0.1)
    return False


def _control(path: str, method: str = "POST") -> dict:
    """Call a mock ``_test`` control endpoint."""
    request = urllib.request.Request(
        f"{API_BASE}{path}", method=method, headers={"BENCHMARK_TOKEN": TOKEN}
    )
    with urllib.request.urlopen(request, timeout=10) as resp:
        raw = resp.read()
    return json.loads(raw) if raw else {}


def setUpModule() -> None:
    global _process
    if not MOCK_SCRIPT.exists():
        raise unittest.SkipTest(f"mock server not found at {MOCK_SCRIPT}")

    os.environ["BENCHMARK_BASE_URL"] = API_BASE
    os.environ["BENCHMARK_TOKEN"] = TOKEN
    os.environ["TSEC_VPN_CHECK_URL"] = VPN_BASE
    os.environ["TSEC_MAX_ACTIVE"] = "3"
    os.environ["TSEC_TIMEOUT"] = "15"

    _process = subprocess.Popen(
        [sys.executable, str(MOCK_SCRIPT),
         "--port", str(API_PORT),
         "--token", TOKEN,
         "--challenge-port", str(CHALLENGE_PORT),
         "--vpn-port", str(VPN_PORT)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if not _wait_for_port(API_PORT) or not _wait_for_port(VPN_PORT):
        _process.kill()
        raise RuntimeError("mock server did not come up")
    if _process.poll() is not None:
        # The port answered, but OUR process is already dead: some other process owns
        # it (e.g. a leaked mock from an earlier crashed run). Fail loudly instead of
        # silently testing against a stranger's server.
        _process.wait(timeout=5)
        raise RuntimeError(
            f"mock exited during startup (rc={_process.returncode}): "
            f"something else is already listening on {API_PORT}/{VPN_PORT}"
        )


def tearDownModule() -> None:
    if _process is not None:
        _process.terminate()
        try:
            _process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            _process.kill()


class MockBackedTest(unittest.TestCase):
    """Base class: reset mock state before every test for isolation."""

    def setUp(self) -> None:
        _control("/openapi/v1/_test/reset")
        self.challenges = mcp.tool_list_challenges()["challenges"]
        self.assertGreater(len(self.challenges), 0, "mock returned no fixtures")

    # -- fixture discovery (never hard-code unique_codes) --

    def fresh(self, **filters) -> dict:
        """A not-completed challenge, optionally filtered (e.g. flag_count=3)."""
        for item in self.challenges:
            if item.get("is_completed"):
                continue
            if all(item.get(key) == value for key, value in filters.items()):
                return item
        self.skipTest(f"no fresh fixture matching {filters}")

    def expected_flag(self, code: str, index: int) -> str:
        """Mock convention: the i-th correct flag is ``flag{<code>_<i>}``."""
        return f"flag{{{code}_{index}}}"

    def startable(self, **filters) -> dict:
        """A not-completed challenge matching ``filters`` that can REALLY start.

        Unlike ``fresh()`` + a skip-on-503, this scans past the resource-unavailable
        fixture instead of skipping the test, so a fixture reshuffle can never make
        tests silently vanish while the suite still prints OK. The returned challenge
        is left with its container started.
        """
        for item in self.challenges:
            if item.get("is_completed"):
                continue
            if not all(item.get(key) == value for key, value in filters.items()):
                continue
            result = mcp.tool_start_challenge(item["unique_code"])
            if result.get("ok"):
                return item
        self.skipTest(f"no startable fixture matching {filters}")


# --------------------------------------------------------------------------------------
# Transport / contract
# --------------------------------------------------------------------------------------

class TestStdlibOnlyContract(unittest.TestCase):
    """The in-sandbox promise: zero third-party imports. Enforced, not documented."""

    def test_no_third_party_imports(self) -> None:
        source = (MCP_DIR / "tsecbench_mcp.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported.add(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                if node.level == 0 and node.module:
                    imported.add(node.module.split(".")[0])

        allowed = set(sys.stdlib_module_names)
        third_party = sorted(name for name in imported if name not in allowed)
        self.assertEqual(
            third_party, [],
            f"tsecbench_mcp.py must stay stdlib-only; found third-party imports: {third_party}",
        )


class TestJsonRpcTransport(unittest.TestCase):
    def setUp(self) -> None:
        # Not a MockBackedTest subclass, but these tests DO read live platform state
        # (task_status counts); reset keeps them order-independent instead of
        # alphabetically lucky.
        _control("/openapi/v1/_test/reset")

    def test_initialize_handshake(self) -> None:
        response = mcp.handle_request({
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {"protocolVersion": "2025-06-18", "capabilities": {}},
        })
        self.assertEqual(response["jsonrpc"], "2.0")
        self.assertEqual(response["result"]["protocolVersion"], "2025-06-18")
        self.assertEqual(response["result"]["serverInfo"]["name"], "tsecbench")

    def test_tools_call_roundtrip(self) -> None:
        response = mcp.handle_request({
            "jsonrpc": "2.0", "id": 2, "method": "tools/call",
            "params": {"name": "task_status", "arguments": {}},
        })
        payload = json.loads(response["result"]["content"][0]["text"])
        self.assertTrue(payload["ok"])
        self.assertIn("free_slots", payload)
        # The accounting must be real, not just present (kills cap.free_slots.ignored).
        self.assertEqual(payload["free_slots"], payload["max_active"] - len(payload["active_containers"]))
        self.assertEqual(payload["completed"] + payload["partial"] + payload["not_started"],
                         payload["total_challenges"])
        self.assertGreater(payload["total_challenges"], 0, "a reset task still has its fixtures")

    def test_tools_call_error_sets_isError(self) -> None:
        response = mcp.handle_request({
            "jsonrpc": "2.0", "id": 3, "method": "tools/call",
            "params": {"name": "close_challenge", "arguments": {"unique_code": ""}},
        })
        self.assertTrue(response["result"]["isError"])

    def test_resource_read_task_state(self) -> None:
        response = mcp.handle_request({
            "jsonrpc": "2.0", "id": 4, "method": "resources/read",
            "params": {"uri": "tsecbench://task/state"},
        })
        payload = json.loads(response["result"]["contents"][0]["text"])
        self.assertTrue(payload["ok"])
        self.assertIn("total_challenges", payload)

    def test_unknown_resource_is_an_error(self) -> None:
        response = mcp.handle_request({
            "jsonrpc": "2.0", "id": 5, "method": "resources/read",
            "params": {"uri": "tsecbench://nope"},
        })
        # -32002 is the resources-spec code for an unknown URI (not a params problem).
        self.assertEqual(response["error"]["code"], -32002)

    def test_explicit_null_id_is_invalid_request_not_notification(self) -> None:
        response = mcp.handle_request({"jsonrpc": "2.0", "id": None, "method": "ping"})
        self.assertEqual(response["error"]["code"], -32600)
        self.assertIsNone(response["id"])
        # And the no-id form must still be treated as a silent notification.
        self.assertIsNone(mcp.handle_request({"jsonrpc": "2.0", "method": "ping"}))

    def test_parse_error_line_gets_minus_32700(self) -> None:
        response = mcp._handle_line("this is not json at all")
        self.assertEqual(response["jsonrpc"], "2.0")
        self.assertIsNone(response["id"])
        self.assertEqual(response["error"]["code"], -32700)
        self.assertIn("Parse error", response["error"]["message"])

    def test_batch_array_is_rejected_with_minus_32600(self) -> None:
        # Batches are only legal under 2025-03-26, which the server never offers, so a
        # batch is answered as an invalid request instead of being silently dropped.
        response = mcp._handle_line("[1, 2, 3]")
        self.assertEqual(response["error"]["code"], -32600)
        self.assertIsNone(response["id"])

    def test_non_object_message_is_rejected_with_minus_32600(self) -> None:
        response = mcp._handle_line('"just a string"')
        self.assertEqual(response["error"]["code"], -32600)

    def test_2025_03_26_is_no_longer_supported(self) -> None:
        self.assertNotIn("2025-03-26", mcp.SUPPORTED_PROTOCOLS)
        response = mcp.handle_request({
            "jsonrpc": "2.0", "id": 9, "method": "initialize",
            "params": {"protocolVersion": "2025-03-26"},
        })
        self.assertEqual(response["result"]["protocolVersion"], "2025-06-18")

    def test_unsupported_protocol_falls_back_to_the_newest(self) -> None:
        self.assertEqual(mcp.DEFAULT_PROTOCOL, max(mcp.SUPPORTED_PROTOCOLS))
        response = mcp.handle_request({
            "jsonrpc": "2.0", "id": 10, "method": "initialize",
            "params": {"protocolVersion": "1999-01-01"},
        })
        self.assertEqual(response["result"]["protocolVersion"], "2025-06-18")

    def test_tool_results_are_compact_json(self) -> None:
        response = mcp.handle_request({
            "jsonrpc": "2.0", "id": 11, "method": "tools/call",
            "params": {"name": "task_status", "arguments": {}},
        })
        text = response["result"]["content"][0]["text"]
        # Compact JSON: no pretty-printing newlines paid for in LLM context tokens.
        self.assertNotIn("\n", text)
        self.assertTrue(json.loads(text)["ok"])


# --------------------------------------------------------------------------------------
# Reads
# --------------------------------------------------------------------------------------

class TestReads(MockBackedTest):
    def test_vpn_check_passes(self) -> None:
        result = mcp.tool_vpn_check()
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["client_ip"], "10.0.0.1")

    def test_list_challenges_shape(self) -> None:
        result = mcp.tool_list_challenges()
        self.assertTrue(result["ok"])
        required = {
            "unique_code", "description", "difficulty", "level", "total_score",
            "flag_count", "correct_flag_count", "is_completed",
            "container_status", "container_addr",
        }
        for item in result["challenges"]:
            self.assertTrue(required.issubset(item), f"missing keys in {item}")
            # Contract from docs §5.1: addr is empty unless the container is available.
            if item["container_status"] != "available":
                self.assertEqual(item["container_addr"], [])

    def test_only_incomplete_filter(self) -> None:
        everything = mcp.tool_list_challenges()["challenges"]
        self.assertTrue(any(c["is_completed"] for c in everything), "need a completed fixture")
        incomplete = mcp.tool_list_challenges(only_incomplete=True)["challenges"]
        self.assertTrue(all(not c["is_completed"] for c in incomplete))
        self.assertLess(len(incomplete), len(everything))

    def test_difficulty_filter(self) -> None:
        result = mcp.tool_list_challenges(difficulty="easy")["challenges"]
        self.assertTrue(result)
        self.assertTrue(all(c["difficulty"] == "easy" for c in result))

    def test_sort_by_level_is_ascending(self) -> None:
        levels = [c["level"] for c in mcp.tool_list_challenges(sort_by="level")["challenges"]]
        self.assertEqual(levels, sorted(levels))

    def test_unknown_sort_key_falls_back(self) -> None:
        result = mcp.tool_list_challenges(sort_by="; DROP TABLE")
        self.assertTrue(result["ok"])
        self.assertEqual(result["sort_by"], "level")

    def test_task_status_counts(self) -> None:
        result = mcp.tool_task_status()
        self.assertTrue(result["ok"])
        self.assertEqual(
            result["total_challenges"],
            result["completed"] + result["partial"] + result["not_started"],
        )
        self.assertEqual(len(result["active_containers"]) + result["free_slots"], result["max_active"])

    def test_start_challenge_happy_path(self) -> None:
        target = self.startable()
        # startable() already started it; a repeat start is idempotent on the platform.
        result = mcp.tool_start_challenge(target["unique_code"])
        self.assertTrue(result["ok"], result)
        self.assertTrue(result["container_addr"])

    def test_wait_for_ready_reaches_available(self) -> None:
        code = self.startable()["unique_code"]
        result = mcp.tool_wait_for_ready(code, timeout_s=20, interval_s=1)
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["container_status"], "available")
        self.assertTrue(result["container_addr"])


# --------------------------------------------------------------------------------------
# Write paths and the platform's error semantics
# --------------------------------------------------------------------------------------

class TestSubmissions(MockBackedTest):
    def test_correct_flag_awards_and_advances(self) -> None:
        target = self.startable(flag_count=1) if any(
            c["flag_count"] == 1 and not c["is_completed"] for c in self.challenges
        ) else self.startable()
        code = target["unique_code"]

        result = mcp.tool_submit_flag(code, self.expected_flag(code, 0))
        self.assertTrue(result["ok"], result)
        self.assertTrue(result["correct"])
        self.assertEqual(result["correct_flag_count"], 1)
        self.assertGreater(result["awarded"], 0)

    def test_wrong_flag_is_200_not_an_error(self) -> None:
        code = self.startable()["unique_code"]
        result = mcp.tool_submit_flag(code, "flag{definitely_not_it}")
        self.assertTrue(result["ok"], "a wrong flag must not surface as an error")
        self.assertFalse(result["correct"])
        self.assertEqual(result["awarded"], 0)
        self.assertIsNone(result["matched_flag_index"])

    def test_duplicate_flag_is_reported_not_retried(self) -> None:
        code = self.startable()["unique_code"]
        flag = self.expected_flag(code, 0)
        first = mcp.tool_submit_flag(code, flag)
        self.assertTrue(first["correct"])

        second = mcp.tool_submit_flag(code, flag)
        self.assertFalse(second["ok"])
        self.assertEqual(second["code"], "duplicate")
        self.assertFalse(second["fatal"], "duplicate must never abort the run")

    def test_multi_flag_challenge_completes(self) -> None:
        code = self.startable(flag_count=3)["unique_code"]

        for index in range(3):
            result = mcp.tool_submit_flag(code, self.expected_flag(code, index))
            self.assertTrue(result["correct"], result)
        self.assertTrue(result["is_completed"])
        self.assertIn("close_challenge", result["note"])

        # And the platform now agrees it is complete.
        listed = {c["unique_code"]: c for c in mcp.tool_list_challenges()["challenges"]}
        self.assertTrue(listed[code]["is_completed"])
        self.assertEqual(listed[code]["correct_flag_count"], listed[code]["flag_count"])

    def test_partial_progress_persists_across_calls(self) -> None:
        code = self.startable(flag_count=3)["unique_code"]
        mcp.tool_submit_flag(code, self.expected_flag(code, 0))

        listed = {c["unique_code"]: c for c in mcp.tool_list_challenges()["challenges"]}
        self.assertEqual(listed[code]["correct_flag_count"], 1)
        self.assertFalse(listed[code]["is_completed"])

    def test_unknown_unique_code_is_skippable(self) -> None:
        result = mcp.tool_submit_flag("no_such_challenge", "flag{x}")
        self.assertFalse(result["ok"])
        self.assertEqual(result["code"], "challenge_not_found")
        self.assertFalse(result["fatal"], "an unknown code must not abort the run")


class TestHints(MockBackedTest):
    def test_hint_requires_explicit_confirmation(self) -> None:
        code = self.startable()["unique_code"]

        gated = mcp.tool_get_hint(code)
        self.assertFalse(gated["ok"])
        self.assertEqual(gated["code"], "confirmation_required")
        self.assertIn("confirm_deduction=true", gated["action"])

        # The gate must be real: the mock records whether a hint was ever fetched.
        state = _control("/openapi/v1/_test/state", "GET")
        self.assertEqual(state["hints_taken"], [], "the confirmation gate let a hint request through")
        self.assertNotIn("hinted", json.dumps(state).lower())

    def test_hint_after_confirmation(self) -> None:
        code = self.startable()["unique_code"]
        result = mcp.tool_get_hint(code, confirm_deduction=True)
        self.assertTrue(result["ok"], result)
        self.assertIn("hint", result)
        # A hint with text means a configured hint; the warning must talk about the
        # conditional cost ratio, not claim a deduction already happened.
        self.assertIn("hint_cost_radio", result["warning"])

    def test_hint_null_means_no_deduction_warning(self) -> None:
        # Mock fixture pwn-hard-heap-03 is the documented hint-less challenge (hint: null).
        code = "pwn-hard-heap-03"
        if not any(c["unique_code"] == code for c in self.challenges):
            self.skipTest("mock has no hint-less fixture")
        started = mcp.tool_start_challenge(code)
        self.assertTrue(started["ok"], started)
        result = mcp.tool_get_hint(code, confirm_deduction=True)
        self.assertTrue(result["ok"], result)
        self.assertIsNone(result["hint"])
        self.assertIn("null", result["warning"])
        self.assertIn("不扣分", result["warning"])

    def test_hint_on_completed_challenge_is_skippable(self) -> None:
        completed = next(c for c in self.challenges if c["is_completed"])
        result = mcp.tool_get_hint(completed["unique_code"], confirm_deduction=True)
        self.assertFalse(result["ok"])
        self.assertEqual(result["code"], "invalid_state")
        self.assertFalse(result["fatal"])
        self.assertIn("通关", result["action"])


class TestContainerLifecycle(MockBackedTest):
    def test_max_active_limit_is_recoverable(self) -> None:
        fresh = [c["unique_code"] for c in self.challenges if not c["is_completed"]]

        # Classify fixtures with the cap FREE. Doing it here keeps the test independent of
        # the mock's internal check order: while the cap is full, a resource-starved
        # challenge also reports `max active`, so probing under load would misclassify it.
        startable: list[str] = []
        for code in fresh:
            result = mcp.tool_start_challenge(code)
            if result.get("code") == "resource_unavailable":
                continue
            self.assertTrue(result["ok"], result)
            startable.append(code)
            self.assertTrue(mcp.tool_close_challenge(code)["ok"], "cleanup must release the slot")
        self.assertGreaterEqual(len(startable), 4, "need 3 to fill the cap plus 1 overflow")

        started = startable[:3]
        overflow = startable[3]
        for code in started:
            self.assertTrue(mcp.tool_start_challenge(code)["ok"])
        self.assertEqual(sorted(mcp.tool_task_status()["active_containers"]), sorted(started))

        # The cap must refuse the fourth, and refuse it recoverably.
        refused = mcp.tool_start_challenge(overflow)
        self.assertFalse(refused["ok"], refused)
        self.assertEqual(refused["code"], "invalid_state")
        self.assertFalse(refused["fatal"], "hitting the cap must not abort the run")
        self.assertIn("max active", refused["message"].lower())
        self.assertEqual(sorted(refused["active_containers"]), sorted(started))

        # The documented recovery: close one, then the start succeeds.
        self.assertTrue(mcp.tool_close_challenge(started[0])["ok"])
        retried = mcp.tool_start_challenge(overflow)
        self.assertTrue(retried["ok"], retried)

    def test_close_releases_the_slot(self) -> None:
        code = self.startable()["unique_code"]
        self.assertIn(code, mcp.tool_task_status()["active_containers"])

        result = mcp.tool_close_challenge(code)
        self.assertTrue(result["ok"])
        self.assertTrue(result["closed"])
        self.assertNotIn(code, mcp.tool_task_status()["active_containers"])

    def test_close_all_is_gated_then_works(self) -> None:
        codes = []
        for item in self.challenges:
            if item["is_completed"]:
                continue
            result = mcp.tool_start_challenge(item["unique_code"])
            if result.get("ok"):
                codes.append(item["unique_code"])
            if len(codes) == 2:
                break

        gated = mcp.tool_close_all_challenges()
        self.assertFalse(gated["ok"])
        self.assertEqual(gated["code"], "confirmation_required")
        self.assertEqual(sorted(gated["active_containers"]), sorted(codes))
        # Still running, because the gate held.
        self.assertEqual(sorted(mcp.tool_task_status()["active_containers"]), sorted(codes))

        confirmed = mcp.tool_close_all_challenges(confirm=True)
        self.assertTrue(confirmed["ok"], confirmed)
        self.assertEqual(sorted(confirmed["closed"]), sorted(codes))
        self.assertEqual(mcp.tool_task_status()["active_containers"], [])

    def test_close_all_on_idle_task_is_a_noop(self) -> None:
        result = mcp.tool_close_all_challenges(confirm=True)
        self.assertTrue(result["ok"])
        self.assertEqual(result["closed"], [])

    def test_wait_for_ready_on_stopped_container_guides_restart(self) -> None:
        code = self.fresh()["unique_code"]
        result = mcp.tool_wait_for_ready(code, timeout_s=2, interval_s=1)
        self.assertFalse(result["ok"])
        # NOT invalid_state: the platform's runbook tells agents a non-"max active"
        # invalid_state means "task over, stop everything". A merely-stopped container
        # is a different, recoverable situation and must carry its own code.
        self.assertEqual(result["code"], "container_not_running")
        self.assertFalse(result["fatal"])
        self.assertIn("start_challenge", result["action"])

    def test_wait_for_ready_unknown_code(self) -> None:
        result = mcp.tool_wait_for_ready("no_such_challenge", timeout_s=2, interval_s=1)
        self.assertFalse(result["ok"])
        self.assertEqual(result["code"], "challenge_not_found")


class TestFatalStates(MockBackedTest):
    def test_expired_task_is_fatal_everywhere(self) -> None:
        _control("/openapi/v1/_test/expire")

        for label, result in (
            ("task_status", mcp.tool_task_status()),
            ("list_challenges", mcp.tool_list_challenges()),
            ("start_challenge", mcp.tool_start_challenge(self.fresh()["unique_code"])),
            ("submit_flag", mcp.tool_submit_flag(self.fresh()["unique_code"], "flag{x}")),
            ("get_hint", mcp.tool_get_hint(self.fresh()["unique_code"], confirm_deduction=True)),
            ("close_challenge", mcp.tool_close_challenge(self.fresh()["unique_code"])),
            ("wait_for_ready", mcp.tool_wait_for_ready(self.fresh()["unique_code"], timeout_s=2, interval_s=1)),
        ):
            with self.subTest(tool=label):
                self.assertFalse(result["ok"], result)
                self.assertEqual(result["code"], "invalid_state")
                self.assertTrue(result["fatal"], f"{label} must be fatal once the task has ended")
                self.assertIn("任务已结束", result["action"])

    def test_bad_token_is_fatal(self) -> None:
        original = os.environ["BENCHMARK_TOKEN"]
        os.environ["BENCHMARK_TOKEN"] = "00000000-0000-0000-0000-000000000000"
        try:
            result = mcp.tool_list_challenges()
            self.assertFalse(result["ok"])
            self.assertEqual(result["code"], "task_not_found")
            self.assertTrue(result["fatal"])
            self.assertEqual(result["http_status"], 404)
        finally:
            os.environ["BENCHMARK_TOKEN"] = original

    def test_missing_token_gives_setup_guidance(self) -> None:
        original = os.environ.pop("BENCHMARK_TOKEN")
        try:
            result = mcp.tool_list_challenges()
            self.assertFalse(result["ok"])
            self.assertEqual(result["code"], "missing_local_config")
            self.assertTrue(result["fatal"])
            self.assertIn("本地模式", result["action"])
        finally:
            os.environ["BENCHMARK_TOKEN"] = original


class TestProbeTarget(MockBackedTest):
    def test_open_port_is_reachable(self) -> None:
        result = mcp.tool_probe_target("127.0.0.1", CHALLENGE_PORT, timeout_s=3)
        self.assertTrue(result["ok"], result)
        self.assertTrue(result["reachable"])

    def test_closed_port_is_unreachable_and_actionable(self) -> None:
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            free_port = probe.getsockname()[1]

        result = mcp.tool_probe_target("127.0.0.1", free_port, timeout_s=1)
        self.assertFalse(result["ok"])
        self.assertEqual(result["code"], "unreachable")
        self.assertFalse(result["fatal"])
        self.assertIn("vpn_check", result["action"])


class TestNotesLedger(MockBackedTest):
    def setUp(self) -> None:
        super().setUp()
        import tempfile
        self._tmp = tempfile.TemporaryDirectory()
        self._previous = os.environ.get("TSEC_STATE_DIR")
        os.environ["TSEC_STATE_DIR"] = self._tmp.name

    def tearDown(self) -> None:
        if self._previous is None:
            os.environ.pop("TSEC_STATE_DIR", None)
        else:
            os.environ["TSEC_STATE_DIR"] = self._previous
        self._tmp.cleanup()

    def test_notes_survive_a_simulated_restart(self) -> None:
        mcp.tool_note_save("web_01", "found /admin; creds admin:admin")
        mcp.tool_note_save("web_01", "flag submitted")

        # A restart is a fresh process reading the same plain-text ledger.
        script = (
            "import sys, json;"
            f"sys.path.insert(0, r'{MCP_DIR}');"
            "import tsecbench_mcp as m;"
            "print(json.dumps(m.tool_note_list(key='web_01'), ensure_ascii=False))"
        )
        env = dict(os.environ)
        out = subprocess.run(
            [sys.executable, "-c", script], capture_output=True, text=True, env=env, timeout=30
        )
        self.assertEqual(out.returncode, 0, out.stderr)
        payload = json.loads(out.stdout.strip().splitlines()[-1])
        self.assertEqual(payload["count"], 2)
        self.assertEqual(payload["notes"][0]["key"], "web_01")


class TestWireTypeSafety(MockBackedTest):
    """Wire values must be validated, never coerced (string booleans, nulls, numerics)."""

    def test_string_boolean_confirm_is_rejected_and_closes_nothing(self) -> None:
        code = self.startable()["unique_code"]

        result = mcp.tool_close_all_challenges(confirm="false")
        self.assertFalse(result["ok"])
        self.assertEqual(result["code"], "invalid_argument")
        # The old bool(wire_value) coercion treated "false" as True and closed containers.
        self.assertIn(code, mcp.tool_task_status()["active_containers"])

    def test_int_confirm_is_rejected(self) -> None:
        result = mcp.tool_close_all_challenges(confirm=1)
        self.assertFalse(result["ok"])
        self.assertEqual(result["code"], "invalid_argument")

    def test_string_confirm_deduction_is_rejected_and_fetches_nothing(self) -> None:
        code = self.startable()["unique_code"]

        result = mcp.tool_get_hint(code, confirm_deduction="true")
        self.assertFalse(result["ok"])
        self.assertEqual(result["code"], "invalid_argument")

        state = _control("/openapi/v1/_test/state", "GET")
        self.assertEqual(state["hints_taken"], [], "a string boolean slipped past the gate")

    def test_string_only_incomplete_is_rejected(self) -> None:
        result = mcp.tool_list_challenges(only_incomplete="false")
        self.assertFalse(result["ok"])
        self.assertEqual(result["code"], "invalid_argument")

    def test_null_flag_is_rejected_not_stringified(self) -> None:
        code = self.startable()["unique_code"]
        result = mcp.tool_submit_flag(code, None)
        self.assertFalse(result["ok"])
        self.assertEqual(result["code"], "invalid_argument")
        # And nothing was submitted: the submission ledger must not contain "None".
        state = _control("/openapi/v1/_test/state", "GET")
        submitted = [s["flag"] for s in state["submissions"] if s["unique_code"] == code]
        self.assertEqual(submitted, [])

    def test_string_wait_timeout_is_rejected(self) -> None:
        result = mcp.tool_wait_for_ready("whatever", timeout_s="abc", interval_s=1)
        self.assertFalse(result["ok"])
        self.assertEqual(result["code"], "invalid_argument")

    def test_bool_wait_timeout_is_rejected(self) -> None:
        # bool is an int subclass in Python; a JSON true is not a timeout.
        result = mcp.tool_wait_for_ready("whatever", timeout_s=True, interval_s=1)
        self.assertFalse(result["ok"])
        self.assertEqual(result["code"], "invalid_argument")

    def test_int_note_list_key_is_rejected(self) -> None:
        result = mcp.tool_note_list(key=123)
        self.assertFalse(result["ok"])
        self.assertEqual(result["code"], "invalid_argument")

    def test_null_note_value_is_rejected(self) -> None:
        result = mcp.tool_note_save("k", None)
        self.assertFalse(result["ok"])
        self.assertEqual(result["code"], "invalid_argument")

    def test_string_probe_timeout_is_rejected(self) -> None:
        result = mcp.tool_probe_target("127.0.0.1", 80, timeout_s="abc")
        self.assertFalse(result["ok"])
        self.assertEqual(result["code"], "invalid_argument")

    def test_non_string_unique_code_is_rejected(self) -> None:
        result = mcp.tool_start_challenge(123)
        self.assertFalse(result["ok"])
        self.assertEqual(result["code"], "invalid_argument")


class TestBadBodies(MockBackedTest):
    """A 200 with the wrong body shape must become bad_body, never a fake success."""

    def poison(self, mode: str, route: str) -> None:
        """Make the mock answer the NEXT `route` call with a 200 carrying `mode` body."""
        request = urllib.request.Request(
            f"{API_BASE}/openapi/v1/_test/poison?mode={mode}&route={route}",
            method="POST",
            headers={"BENCHMARK_TOKEN": TOKEN},
        )
        urllib.request.urlopen(request, timeout=10).read()

    def test_html_challenge_list_is_bad_body(self) -> None:
        self.poison("html", "list")
        result = mcp.tool_list_challenges()
        self.assertFalse(result["ok"])
        self.assertEqual(result["code"], "bad_body")
        self.assertFalse(result["fatal"])
        self.assertTrue(result["action"])

    def test_garbage_array_list_body_is_bad_body_not_a_crash(self) -> None:
        # 200 with "[1]": a list, but not a list of challenge objects. task_status used
        # to die on AttributeError; now it is one uniform bad_body payload.
        self.poison("array", "list")
        result = mcp.tool_task_status()
        self.assertFalse(result["ok"])
        self.assertEqual(result["code"], "bad_body")
        self.assertNotIn("total_challenges", result)

    def test_empty_object_list_body_is_bad_body(self) -> None:
        self.poison("emptyobj", "list")
        result = mcp.tool_list_challenges()
        self.assertFalse(result["ok"])
        self.assertEqual(result["code"], "bad_body")

    def test_text_submit_body_is_bad_body(self) -> None:
        code = self.startable()["unique_code"]
        self.poison("text", "submit")
        result = mcp.tool_submit_flag(code, self.expected_flag(code, 0))
        self.assertFalse(result["ok"])
        self.assertEqual(result["code"], "bad_body")

    def test_empty_object_submit_is_bad_body_not_fake_incorrect(self) -> None:
        code = self.startable()["unique_code"]
        self.poison("emptyobj", "submit")
        result = mcp.tool_submit_flag(code, self.expected_flag(code, 0))
        self.assertFalse(result["ok"])
        self.assertEqual(result["code"], "bad_body")
        self.assertNotIn("correct", result)

    def test_empty_object_close_is_bad_body_not_null_closed(self) -> None:
        code = self.startable()["unique_code"]
        self.poison("emptyobj", "close")
        result = mcp.tool_close_challenge(code)
        self.assertFalse(result["ok"])
        self.assertEqual(result["code"], "bad_body")
        self.assertNotIn("closed", result)

    def test_array_start_body_is_bad_body(self) -> None:
        code = self.fresh()["unique_code"]
        self.poison("array", "start")
        result = mcp.tool_start_challenge(code)
        self.assertFalse(result["ok"])
        self.assertEqual(result["code"], "bad_body")
        self.assertNotIn("container_addr", result)

    def test_array_hint_body_is_bad_body(self) -> None:
        code = self.fresh()["unique_code"]
        self.poison("array", "hint")
        result = mcp.tool_get_hint(code, confirm_deduction=True)
        self.assertFalse(result["ok"])
        self.assertEqual(result["code"], "bad_body")

    def test_empty_body_close_is_bad_body(self) -> None:
        code = self.startable()["unique_code"]
        self.poison("empty", "close")
        result = mcp.tool_close_challenge(code)
        self.assertFalse(result["ok"])
        self.assertEqual(result["code"], "bad_body")

    def test_platform_500_internal_error_is_recoverable_not_fatal(self) -> None:
        # Drive a REAL HTTP 500 through the full path (poison mode "internal500"),
        # not just hint_for: the runbook contract says internal_error means
        # "retry once", so it must never be fatal.
        self.poison("internal500", "list")
        result = mcp.tool_list_challenges()
        self.assertFalse(result["ok"])
        self.assertEqual(result["code"], "internal_error")
        self.assertIs(result["fatal"], False)
        self.assertTrue(result["action"])

    def test_real_422_through_the_full_http_path_names_the_fix(self) -> None:
        # hint_for(422) is covered purely elsewhere; this drives a genuine platform
        # 422 (empty flag) over HTTP and checks the whole translation pipeline.
        try:
            mcp._api("POST", mcp.API_SUBMIT, json_body={"unique_code": "whatever", "flag": ""})
            self.fail("expected the platform to reject an empty flag with 422")
        except mcp.TsecApiError as exc:
            payload = exc.payload
        self.assertEqual(payload["http_status"], 422)
        self.assertIsNone(payload["code"])
        self.assertIn("框架校验", payload["message"])
        self.assertIn("修正参数", payload["action"])
        self.assertIs(payload["fatal"], False)


class TestCloseAllRobustness(MockBackedTest):
    def _start_two(self) -> list[str]:
        codes: list[str] = []
        for item in self.challenges:
            if item["is_completed"]:
                continue
            result = mcp.tool_start_challenge(item["unique_code"])
            if result.get("ok"):
                codes.append(item["unique_code"])
            if len(codes) == 2:
                break
        self.assertEqual(len(codes), 2, "need two startable fixtures")
        return codes

    def test_transport_error_in_loop_is_recorded_not_raised(self) -> None:
        codes = self._start_two()
        original = mcp._api
        calls = {"n": 0}

        def flaky(method: str, path: str, **kwargs):
            if path == mcp.API_CLOSE:
                calls["n"] += 1
                if calls["n"] == 1:
                    raise ConnectionResetError("connection reset by peer")
            return original(method, path, **kwargs)

        mcp._api = flaky
        try:
            result = mcp.tool_close_all_challenges(confirm=True)
        finally:
            mcp._api = original

        # The first close failed, but the loop must continue and keep both lists.
        self.assertFalse(result["ok"])
        self.assertEqual(set(result["closed"]), {codes[1]})
        self.assertEqual([f["unique_code"] for f in result["failed"]], [codes[0]])
        # Contract uniformity: every ok:false payload carries action/fatal.
        self.assertIn("action", result)
        self.assertIn("fatal", result)
        self.assertFalse(result["fatal"])

    def test_urlopen_oserror_is_translated_to_uniform_payload(self) -> None:
        real_build_opener = mcp.urllib.request.build_opener

        class ExplodingOpener:
            def open(self, *args, **kwargs):
                raise ConnectionResetError("connection reset by peer")

        def build_exploding_opener(*handlers):
            return ExplodingOpener()

        mcp.urllib.request.build_opener = build_exploding_opener
        try:
            result = mcp.tool_list_challenges()
        finally:
            mcp.urllib.request.build_opener = real_build_opener
        self.assertFalse(result["ok"])
        self.assertEqual(result["code"], "local_connection_error")

    def test_authenticated_api_redirects_are_not_followed(self) -> None:
        handler = mcp._NoRedirectHandler()
        request = mcp.urllib.request.Request("https://tsecbench.zc.tencent.com/api")
        self.assertIsNone(handler.redirect_request(
            request, None, 302, "Found", {}, "https://attacker.example/collect"
        ))

    def test_benchmark_base_url_rejects_nonofficial_public_hosts(self) -> None:
        original = os.environ["BENCHMARK_BASE_URL"]
        try:
            os.environ["BENCHMARK_BASE_URL"] = "https://attacker.example"
            with self.assertRaises(ValueError):
                mcp.base_url()
            os.environ["BENCHMARK_BASE_URL"] = "https://tsecbench.zc.tencent.com"
            self.assertEqual(mcp.base_url(), "https://tsecbench.zc.tencent.com")
            os.environ["BENCHMARK_BASE_URL"] = "http://tsecbench.zc.tencent.com.tsecbench.gw"
            self.assertEqual(mcp.base_url(), "http://tsecbench.zc.tencent.com.tsecbench.gw")
            os.environ["BENCHMARK_BASE_URL"] = "http://api.deepseek.com.tsecbench.gw/anthropic"
            self.assertEqual(mcp.base_url(), "http://api.deepseek.com.tsecbench.gw/anthropic")
            os.environ["BENCHMARK_BASE_URL"] = "http://fake.tsecbench.gw.attacker.example"
            with self.assertRaises(ValueError):
                mcp.base_url()
        finally:
            os.environ["BENCHMARK_BASE_URL"] = original

    def test_nothing_active_payload_carries_uniform_keys(self) -> None:
        result = mcp.tool_close_all_challenges(confirm=True)
        self.assertTrue(result["ok"])
        self.assertEqual(result["closed"], [])
        self.assertEqual(result["failed"], [])
        self.assertIn("action", result)
        self.assertIn("fatal", result)


class TestErrorClassification(unittest.TestCase):
    """Pure error-shape and classification rules (no mock, no network)."""

    def test_string_detail_is_not_framework_error(self) -> None:
        payload = mcp.error_payload(404, {"detail": "Not Found"}, '{"detail": "Not Found"}')
        self.assertIsNone(payload["code"])
        self.assertIsNone(payload["detail"])
        self.assertNotIn("框架校验", payload["message"])

    def test_detail_list_is_still_framework_error(self) -> None:
        payload = mcp.error_payload(422, {"detail": [{"loc": ["body", "flag"]}]}, "")
        self.assertIsNone(payload["code"])
        self.assertIn("框架校验", payload["message"])

    def test_completed_heuristic_is_scoped_to_the_hint_endpoint(self) -> None:
        # Elsewhere, a "completed" 409 is a task-over signal and must stay fatal.
        self.assertTrue(mcp.hint_for("invalid_state", "challenge already completed", 409)[1])
        self.assertFalse(
            mcp.hint_for("invalid_state", "challenge already completed", 409, endpoint=mcp.API_HINT)[1]
        )
        # "max active" stays globally recoverable.
        self.assertFalse(mcp.hint_for("invalid_state", "max active instances reached", 409)[1])

    def test_wait_params_are_clamped(self) -> None:
        self.assertEqual(
            mcp._clamp_wait_params(10 ** 6, 10 ** 6),
            (mcp.MAX_WAIT_TIMEOUT_S, mcp.MAX_POLL_INTERVAL_S),
        )
        self.assertEqual(mcp._clamp_wait_params(0, 0), (1, 1))
        self.assertEqual(mcp._clamp_wait_params(5, 60), (5, 60))


class TestVpnReasons(MockBackedTest):
    """vpn_check failures must always carry a documented SDK reason string."""

    def set_mode(self, mode: str) -> None:
        request = urllib.request.Request(f"{VPN_BASE}/_test/mode?mode={mode}", method="POST")
        urllib.request.urlopen(request, timeout=10).read()

    def tearDown(self) -> None:
        try:
            self.set_mode("ok")
        except OSError:
            pass

    def test_status_down_maps_to_status_not_ok(self) -> None:
        self.set_mode("down")
        result = mcp.tool_vpn_check()
        self.assertFalse(result["ok"])
        self.assertEqual(result["reason"], "status_not_ok")
        self.assertIn("action", result)

    def test_html_body_maps_to_bad_body(self) -> None:
        self.set_mode("html")
        result = mcp.tool_vpn_check()
        self.assertFalse(result["ok"])
        self.assertEqual(result["reason"], "bad_body")

    def test_http_500_maps_to_bad_status(self) -> None:
        self.set_mode("status500")
        result = mcp.tool_vpn_check()
        self.assertFalse(result["ok"])
        self.assertEqual(result["reason"], "bad_status")

    def test_connection_refused_maps_to_network_error(self) -> None:
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            free_port = probe.getsockname()[1]
        original = os.environ["TSEC_VPN_CHECK_URL"]
        os.environ["TSEC_VPN_CHECK_URL"] = f"http://127.0.0.1:{free_port}"
        try:
            result = mcp.tool_vpn_check()
        finally:
            os.environ["TSEC_VPN_CHECK_URL"] = original
        self.assertFalse(result["ok"])
        self.assertEqual(result["reason"], "network_error")


class TestWaitForReadyTiming(MockBackedTest):
    """The poll loop must honour its deadline and bound its fetch count."""

    def test_interval_cannot_oversleep_the_deadline(self) -> None:
        code = self.startable()["unique_code"]  # mock: pending -> available after ~1.5s

        started = time.monotonic()
        result = mcp.tool_wait_for_ready(code, timeout_s=5, interval_s=60)
        elapsed = time.monotonic() - started

        self.assertTrue(result["ok"], result)
        # With fixed interval_s sleeps this blocked for the full 60s (10x the contract).
        self.assertLess(elapsed, 20.0, "sleeps must be clamped to the deadline, not interval_s")

    def test_backoff_bounds_fetch_count_when_stuck(self) -> None:
        code = self.startable()["unique_code"]
        _control("/openapi/v1/_test/freeze")  # keep the container pending forever
        try:
            before = _control("/openapi/v1/_test/state", "GET")["list_fetch_count"]
            result = mcp.tool_wait_for_ready(code, timeout_s=8, interval_s=1)
            after = _control("/openapi/v1/_test/state", "GET")["list_fetch_count"]
        finally:
            _control("/openapi/v1/_test/reset")

        self.assertFalse(result["ok"])
        self.assertEqual(result["code"], "local_timeout")
        fetches = after - before
        # Fixed 1s polling makes 9-10 fetches in 8s; exponential backoff makes 5-6.
        self.assertLessEqual(fetches, 6, f"backoff must bound fetches; got {fetches}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
