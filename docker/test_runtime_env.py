#!/usr/bin/env python3
"""Runtime environment compatibility tests used by the hosted image."""

import os
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]


def python_constant(module: str, expression: str, env: dict[str, str]) -> str:
    code = (
        "import sys; "
        f"sys.path.insert(0, {str(ROOT / 'docker')!r}); "
        f"sys.path.insert(0, {str(ROOT / 'mcp')!r}); "
        f"import {module}; print({expression})"
    )
    proc = subprocess.run([sys.executable, "-c", code], env=env,
                          capture_output=True, text=True, check=False)
    if proc.returncode:
        raise AssertionError(proc.stderr)
    return proc.stdout.strip()


class RuntimeEnvironmentTests(unittest.TestCase):
    def test_keepalive_honors_20_second_interval(self):
        env = os.environ.copy()
        env["TSEC_KEEPALIVE_INTERVAL"] = "20"
        self.assertEqual(python_constant("keepalive", "keepalive.INTERVAL_S", env), "20")

    def test_worker_alias_and_explicit_override(self):
        env = os.environ.copy()
        env.pop("TSEC_WORKERS", None)
        env["TSEC_FLEET_WORKERS"] = "1"
        self.assertEqual(python_constant("fleet", "fleet.MAX_WORKERS", env), "1")
        env["TSEC_WORKERS"] = "32"
        self.assertEqual(python_constant("fleet", "fleet.MAX_WORKERS", env), "32")

    def test_model_url_is_passed_through_without_classification(self):
        source = (ROOT / "docker" / "entrypoint.sh").read_text(encoding="utf-8")
        start = source.index("# 3. Model endpoint: pass the caller-supplied URL through unchanged.")
        end = source.index("# 4. Auth + model env.", start)
        snippet = source[start:end]
        self.assertNotIn("tsec_gw.py", snippet)
        env = os.environ.copy()
        env["LLM_API_BASE_URL"] = "custom+scheme://caller-controlled.invalid/path"
        proc = subprocess.run(
            ["bash", "-c", "log(){ printf '%s\\n' \"$*\"; };\n" + snippet],
            env=env, capture_output=True, text=True, check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn(env["LLM_API_BASE_URL"], proc.stdout)


if __name__ == "__main__":
    unittest.main()
