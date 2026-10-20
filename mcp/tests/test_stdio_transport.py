#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 James and minc
"""End-to-end tests over the REAL stdio transport.

The other suite calls ``handle_request()`` directly, which cannot see framing bugs,
flushing bugs, a polluted stdout, or a loop that dies on bad input. This file spawns the
actual server as a subprocess and speaks JSON-RPC to it over stdin/stdout, backed by the
mock platform so the calls are real HTTP.

    python mcp/tests/test_stdio_transport.py
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.request
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
MCP_DIR = TESTS_DIR.parent
sys.path.insert(0, str(MCP_DIR))
import tsecbench_mcp as mcp  # noqa: E402  (path set up above on purpose)

MOCK_SCRIPT = TESTS_DIR / "mock_tsec_api.py"

# Loopback ports far from the defaults so a concurrent suite run in another worktree
# can never hijack or collide with this mock.
API_PORT = 18599
CHALLENGE_PORT = 18598
VPN_PORT = 18597
TOKEN = "stdio-token"
API_BASE = f"http://127.0.0.1:{API_PORT}"
VPN_BASE = f"http://127.0.0.1:{VPN_PORT}"

_mock: subprocess.Popen | None = None
_server: subprocess.Popen | None = None
_mock_stderr = None
_server_stderr_lines: list[str] = []
_stderr_thread: threading.Thread | None = None


# --------------------------------------------------------------------------------------
# Harness: bring up the mock platform, then the MCP server under test.
# --------------------------------------------------------------------------------------

def _wait_for_port(port: int, timeout: float = 20.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.3):
                return True
        except OSError:
            time.sleep(0.1)
    return False


def _drain(stream) -> None:
    """Consume the server's stderr so it can never block on a full pipe."""
    try:
        for line in stream:
            _server_stderr_lines.append(line)
    except (ValueError, OSError):
        pass  # stream closed during teardown


def setUpModule() -> None:
    global _mock, _server, _mock_stderr, _stderr_thread
    if not MOCK_SCRIPT.exists():
        raise unittest.SkipTest(f"mock server not found at {MOCK_SCRIPT}")

    os.environ.update(
        BENCHMARK_BASE_URL=API_BASE,
        BENCHMARK_TOKEN=TOKEN,
        TSEC_VPN_CHECK_URL=VPN_BASE,
        TSEC_MAX_ACTIVE="3",
        TSEC_TIMEOUT="15",
    )

    # 1) The mock platform. It must be serving before the server under test is driven.
    _mock_stderr = tempfile.TemporaryFile()
    _mock = subprocess.Popen(
        [sys.executable, str(MOCK_SCRIPT),
         "--port", str(API_PORT),
         "--token", TOKEN,
         "--challenge-port", str(CHALLENGE_PORT),
         "--vpn-port", str(VPN_PORT)],
        stdout=subprocess.DEVNULL,
        stderr=_mock_stderr,
    )
    if not (_wait_for_port(API_PORT) and _wait_for_port(VPN_PORT)):
        _mock_stderr.seek(0)
        detail = _mock_stderr.read().decode("utf-8", "replace")
        _mock.kill()
        raise RuntimeError(f"mock platform did not come up\n--- mock stderr ---\n{detail or '(empty)'}")
    if _mock.poll() is not None:
        # The port answered, but OUR process is already dead: some other process owns
        # it (e.g. a leaked mock from an earlier crashed run). Fail loudly with the
        # mock's own stderr instead of silently testing against a stranger's server.
        _mock.wait(timeout=5)
        detail = _mock_stderr.read().decode("utf-8", "replace")
        raise RuntimeError(
            f"mock exited during startup (rc={_mock.returncode}): "
            f"something else is already listening on {API_PORT}/{VPN_PORT}"
            f"\n--- mock stderr ---\n{detail or '(empty)'}"
        )

    _reset_mock()

    # 2) The MCP server under test, over a real stdio pipe.
    _server = subprocess.Popen(
        [sys.executable, str(MCP_DIR / "tsecbench_mcp.py")],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        bufsize=1,
    )
    _stderr_thread = threading.Thread(target=_drain, args=(_server.stderr,), daemon=True)
    _stderr_thread.start()

    deadline = time.monotonic() + 15
    while time.monotonic() < deadline and _server.poll() is None and not _server_stderr_lines:
        time.sleep(0.05)
    if _server.poll() is not None:
        raise RuntimeError(
            f"MCP server exited immediately with code {_server.returncode}\n"
            f"--- stderr ---\n{''.join(_server_stderr_lines)}"
        )


def tearDownModule() -> None:
    global _server, _mock
    if _server is not None:
        try:
            if _server.stdin:
                _server.stdin.close()
            _server.wait(timeout=15)
        except (subprocess.TimeoutExpired, ValueError, OSError):
            _server.kill()
            _server.wait(timeout=10)
    if _stderr_thread is not None:
        _stderr_thread.join(timeout=5)
    if _mock is not None:
        _mock.terminate()
        try:
            _mock.wait(timeout=10)
        except subprocess.TimeoutExpired:
            _mock.kill()
    if _mock_stderr is not None:
        _mock_stderr.close()


def _reset_mock() -> None:
    request = urllib.request.Request(
        f"{API_BASE}/openapi/v1/_test/reset", method="POST", headers={"BENCHMARK_TOKEN": TOKEN}
    )
    urllib.request.urlopen(request, timeout=10).read()


class StdioTransportTest(unittest.TestCase):
    """One server process for the whole class, so loop state is exercised for real."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.send({
            "jsonrpc": "2.0", "id": "init", "method": "initialize",
            "params": {"protocolVersion": "2025-06-18", "capabilities": {}},
        })
        cls.reply = cls.recv()
        cls.send({"jsonrpc": "2.0", "method": "notifications/initialized"})

    @staticmethod
    def send(message: dict) -> None:
        assert _server is not None and _server.stdin is not None
        _server.stdin.write(json.dumps(message, ensure_ascii=False) + "\n")
        _server.stdin.flush()

    @staticmethod
    def recv() -> dict:
        assert _server is not None and _server.stdout is not None
        line = _server.stdout.readline()
        if not line:
            raise AssertionError("server closed stdout without replying")
        return json.loads(line)

    def rpc(self, method: str, params: dict | None = None, msg_id: object = None) -> dict:
        payload: dict = {"jsonrpc": "2.0", "id": msg_id, "method": method}
        if params is not None:
            payload["params"] = params
        self.send(payload)
        return self.recv()

    def call(self, name: str, arguments: dict, msg_id: str = "c") -> dict:
        """Invoke a tool and return the decoded payload."""
        reply = self.rpc("tools/call", {"name": name, "arguments": arguments}, msg_id=msg_id)
        self.assertIn("result", reply, f"expected a result for {name}, got {reply}")
        return json.loads(reply["result"]["content"][0]["text"])

    # -- protocol --

    def test_01_initialize_handshake(self) -> None:
        self.assertEqual(self.reply["jsonrpc"], "2.0")
        self.assertEqual(self.reply["id"], "init")
        result = self.reply["result"]
        self.assertEqual(result["protocolVersion"], "2025-06-18")
        self.assertEqual(result["serverInfo"], {"name": "tsecbench", "version": "1.0.0"})
        self.assertIn("tools", result["capabilities"])
        self.assertIn("resources", result["capabilities"])
        self.assertIn("prompts", result["capabilities"])

    def test_02_notification_produces_no_reply(self) -> None:
        # The initialized notification was already sent in setUpClass. Had it produced a
        # reply, this ping would have returned that reply instead of the ping result.
        reply = self.rpc("ping", msg_id="ping1")
        self.assertEqual(reply["id"], "ping1")
        self.assertEqual(reply["result"], {})

    def test_03_tools_list_over_the_wire(self) -> None:
        reply = self.rpc("tools/list", msg_id="tl")
        tools = reply["result"]["tools"]
        self.assertEqual(len(tools), len(mcp.TOOLS))
        self.assertEqual(tools[0]["name"], "vpn_check")
        for tool in tools:
            with self.subTest(tool=tool["name"]):
                self.assertTrue(tool["description"])
                self.assertEqual(tool["inputSchema"]["type"], "object")
                self.assertIn("annotations", tool)

    # -- real calls through the mock platform --

    def test_04_vpn_precheck(self) -> None:
        payload = self.call("vpn_check", {})
        self.assertTrue(payload["ok"], payload)
        self.assertEqual(payload["status"], "ok")

    def test_05_tool_call_roundtrip(self) -> None:
        payload = self.call("task_status", {})
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["max_active"], 3)
        self.assertEqual(payload["active_containers"], [])

    def test_06_start_then_wait_then_close(self) -> None:
        challenges = self.call("list_challenges", {"only_incomplete": True})["challenges"]
        code = challenges[0]["unique_code"]

        started = self.call("start_challenge", {"unique_code": code})
        if started.get("code") == "resource_unavailable":
            self.skipTest("first fixture is the resource-unavailable one")
        self.assertTrue(started["ok"], started)

        ready = self.call("wait_for_ready", {"unique_code": code, "timeout_s": 20, "interval_s": 1})
        self.assertTrue(ready["ok"], ready)
        self.assertTrue(ready["container_addr"])

        closed = self.call("close_challenge", {"unique_code": code})
        self.assertTrue(closed["ok"], closed)
        self.assertTrue(closed["closed"])

    def test_07_platform_error_sets_isError_true(self) -> None:
        reply = self.rpc(
            "tools/call",
            {"name": "submit_flag", "arguments": {"unique_code": "no_such_challenge", "flag": "flag{x}"}},
            msg_id="err",
        )
        self.assertTrue(reply["result"]["isError"], "a platform rejection must set isError")
        payload = json.loads(reply["result"]["content"][0]["text"])
        self.assertEqual(payload["code"], "challenge_not_found")
        self.assertFalse(payload["fatal"])
        self.assertIn("action", payload)

    def test_08_local_validation_error_sets_isError_true(self) -> None:
        reply = self.rpc(
            "tools/call",
            {"name": "close_challenge", "arguments": {"unique_code": ""}},
            msg_id="err2",
        )
        self.assertTrue(reply["result"]["isError"])
        payload = json.loads(reply["result"]["content"][0]["text"])
        self.assertEqual(payload["code"], "invalid_argument")

    def test_09_unknown_tool_is_jsonrpc_error(self) -> None:
        reply = self.rpc("tools/call", {"name": "nope", "arguments": {}}, msg_id="bad")
        self.assertEqual(reply["error"]["code"], -32602)

    # -- framing --

    def test_10_newline_in_payload_stays_on_one_line(self) -> None:
        """A value with embedded newlines must not split the JSON-RPC line."""
        value = "line one\nline two\n\ttabbed"
        saved = self.call("note_save", {"key": "framing", "value": value}, msg_id="ns")
        self.assertTrue(saved["ok"], saved)

        back = self.call("note_list", {"key": "framing"}, msg_id="nl")
        self.assertEqual(back["notes"][-1]["value"], value)

    def test_11_unicode_roundtrips(self) -> None:
        marker = "通关 · flag{دخول} · 🚩"
        self.call("note_save", {"key": "unicode", "value": marker}, msg_id="u1")
        back = self.call("note_list", {"key": "unicode"}, msg_id="u2")
        self.assertEqual(back["notes"][-1]["value"], marker)

    def test_12_garbage_input_gets_jsonrpc_errors_and_loop_survives(self) -> None:
        assert _server is not None and _server.stdin is not None
        # JSON-RPC 2.0: a parse error must be ANSWERED (-32700, id: null), not just logged.
        _server.stdin.write("this is not json at all\n")
        _server.stdin.flush()
        reply = self.recv()
        self.assertEqual(reply["jsonrpc"], "2.0")
        self.assertIsNone(reply["id"])
        self.assertEqual(reply["error"]["code"], -32700)

        # A JSON array is a batch — only legal under 2025-03-26, which we never offer.
        _server.stdin.write("[1,2,3]\n")
        _server.stdin.flush()
        reply = self.recv()
        self.assertIsNone(reply["id"])
        self.assertEqual(reply["error"]["code"], -32600)

        # An explicit null id is an invalid request, not a notification.
        _server.stdin.write('{"jsonrpc": "2.0", "id": null, "method": "ping"}\n')
        _server.stdin.flush()
        reply = self.recv()
        self.assertEqual(reply["error"]["code"], -32600)
        self.assertIsNone(reply["id"])

        # The loop must survive all of that and still answer the next valid request.
        reply = self.rpc("ping", msg_id="still-alive")
        self.assertEqual(reply["id"], "still-alive")

    def test_13_resources_and_prompts_over_the_wire(self) -> None:
        listed = self.rpc("resources/list", msg_id="rl")
        uris = {res["uri"] for res in listed["result"]["resources"]}
        self.assertEqual(
            uris,
            {"tsecbench://docs/challenges-api", "tsecbench://docs/agent-prompt", "tsecbench://task/state"},
        )

        read = self.rpc("resources/read", {"uri": "tsecbench://task/state"}, msg_id="rr")
        payload = json.loads(read["result"]["contents"][0]["text"])
        self.assertTrue(payload["ok"])
        self.assertIn("total_challenges", payload)

        # -32002 is the resources-spec code for an unknown URI.
        missing = self.rpc("resources/read", {"uri": "tsecbench://nope"}, msg_id="rx")
        self.assertEqual(missing["error"]["code"], -32002)

        prompts = self.rpc("prompts/list", msg_id="pl")
        self.assertEqual([p["name"] for p in prompts["result"]["prompts"]], ["tsecbench_solve_flow"])

        got = self.rpc("prompts/get", {"name": "tsecbench_solve_flow", "arguments": {"focus": "web-01"}}, msg_id="pg")
        text = got["result"]["messages"][0]["content"]["text"]
        self.assertEqual(got["result"]["messages"][0]["role"], "user")
        self.assertIn("web-01", text)
        self.assertIn("vpn_check", text)

    def test_14_tool_text_results_are_compact(self) -> None:
        # The text lands in the client's LLM context on every call; pretty-printing
        # costs ~1/3 more tokens for zero information.
        reply = self.rpc("tools/call", {"name": "task_status", "arguments": {}}, msg_id="compact")
        text = reply["result"]["content"][0]["text"]
        self.assertNotIn("\n", text, "tool text results must be single-line compact JSON")
        self.assertTrue(json.loads(text)["ok"])

    def test_15_unrequested_protocol_falls_back_to_newest(self) -> None:
        # A second initialize is unusual but legal to probe; 2025-03-26 (batch-legal)
        # is no longer offered, so the fallback must be the NEWEST supported revision.
        reply = self.rpc("initialize", {"protocolVersion": "2025-03-26", "capabilities": {}}, msg_id="re-init")
        self.assertEqual(reply["result"]["protocolVersion"], "2025-06-18")

    def test_99_stdout_carried_no_protocol_traffic_on_stderr(self) -> None:
        """Logging must never leak protocol framing onto stderr, and vice versa."""
        stderr_text = "".join(_server_stderr_lines)
        self.assertNotIn('"jsonrpc"', stderr_text, "protocol traffic leaked to stderr")
        self.assertIn("[tsecbench-mcp]", stderr_text, "expected the server's log lines on stderr")


class Utf8PinnedTransportTest(unittest.TestCase):
    """S3: the server must pin stdio to UTF-8 itself, with no env help.

    The main class spawns the server with encoding="utf-8" in the HARNESS, which masks
    a server that actually speaks the host's ANSI codepage. This test spawns one with
    raw byte pipes (and without PYTHONIOENCODING/PYTHONUTF8), so a legacy-codepage host
    reproduces the original UnicodeEncodeError crash.
    """

    def test_emoji_note_roundtrips_without_env_help(self) -> None:
        env = {
            k: v
            for k, v in os.environ.items()
            if k not in ("PYTHONIOENCODING", "PYTHONUTF8", "PYTHONLEGACYWINDOWSSTDIO")
        }
        proc = subprocess.Popen(
            [sys.executable, str(MCP_DIR / "tsecbench_mcp.py")],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            env=env,
        )

        def send(message: dict) -> None:
            assert proc.stdin is not None
            proc.stdin.write(json.dumps(message, ensure_ascii=False).encode("utf-8") + b"\n")
            proc.stdin.flush()

        def recv() -> dict:
            assert proc.stdout is not None
            line = proc.stdout.readline()
            if not line:
                raise AssertionError("server closed stdout without replying")
            return json.loads(line.decode("utf-8"))

        try:
            send({"jsonrpc": "2.0", "id": "i", "method": "initialize",
                  "params": {"protocolVersion": "2025-06-18"}})
            self.assertEqual(recv()["result"]["serverInfo"]["name"], "tsecbench")
            send({"jsonrpc": "2.0", "method": "notifications/initialized"})

            marker = "通关 · 🚩 · flag{دخول}"
            send({"jsonrpc": "2.0", "id": "u1", "method": "tools/call",
                  "params": {"name": "note_save", "arguments": {"key": "utf8", "value": marker}}})
            saved = json.loads(recv()["result"]["content"][0]["text"])
            self.assertTrue(saved["ok"], saved)

            send({"jsonrpc": "2.0", "id": "u2", "method": "tools/call",
                  "params": {"name": "note_list", "arguments": {"key": "utf8"}}})
            back = json.loads(recv()["result"]["content"][0]["text"])
            self.assertEqual(back["notes"][-1]["value"], marker)
        finally:
            try:
                if proc.stdin:
                    proc.stdin.close()
                proc.wait(timeout=15)
            except (subprocess.TimeoutExpired, ValueError, OSError):
                proc.kill()
                proc.wait(timeout=10)


if __name__ == "__main__":
    unittest.main(verbosity=2)
