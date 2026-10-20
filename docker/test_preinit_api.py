#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 James and minc
"""Offline tests for the entrypoint's pre-MCP platform API burst."""

from pathlib import Path
import os
import subprocess
import tempfile
import unittest


ENTRYPOINT = Path(__file__).with_name("entrypoint.sh")


class PreinitPlatformApiTests(unittest.TestCase):
    def run_preinit(self, calls=None, fail=False):
        source = ENTRYPOINT.read_text(encoding="utf-8")
        start = source.index('PREINIT_API_CALLS="${TSEC_PREINIT_API_CALLS:-3}"')
        end = source.index('\n\nlog "preflight:', start)
        snippet = source[start:end]
        with tempfile.TemporaryDirectory() as temp:
            temp = Path(temp)
            counter = temp / "calls"
            fake_curl = temp / "curl"
            fake_curl.write_text(
                "#!/bin/sh\n"
                f"echo call >> '{counter.as_posix()}'\n"
                + ("echo 503; exit 22\n" if fail else "echo 200\n"),
                encoding="utf-8",
            )
            fake_curl.chmod(0o755)
            env = os.environ.copy()
            env.update({"PATH": f"{temp}{os.pathsep}{env['PATH']}",
                        "BENCHMARK_TOKEN": "test-token",
                        "BENCHMARK_BASE_URL": "https://platform.invalid"})
            if calls is not None:
                env["TSEC_PREINIT_API_CALLS"] = str(calls)
            proc = subprocess.run(
                ["bash", "-c", "log(){ echo \"$*\"; }; warn(){ echo \"$*\" >&2; };\n" + snippet],
                env=env, capture_output=True, text=True, check=False,
            )
            count = len(counter.read_text(encoding="utf-8").splitlines()) if counter.exists() else 0
            return proc, count

    def test_default_is_three_platform_api_calls(self):
        proc, count = self.run_preinit()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(count, 3)

    def test_configured_count_is_honored_and_failure_is_warn_only(self):
        proc, count = self.run_preinit(calls=4, fail=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(count, 4)

    def test_zero_disables_calls_and_invalid_count_uses_default(self):
        proc, count = self.run_preinit(calls=0)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(count, 0)
        proc, count = self.run_preinit(calls="08")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(count, 3)

    def test_calls_precede_mcp_initialize_handshake(self):
        source = ENTRYPOINT.read_text(encoding="utf-8")
        self.assertLess(source.index('PREINIT_API_CALLS="${TSEC_PREINIT_API_CALLS:-3}"'),
                        source.index("--required tsecbench --prune"))


if __name__ == "__main__":
    unittest.main()
