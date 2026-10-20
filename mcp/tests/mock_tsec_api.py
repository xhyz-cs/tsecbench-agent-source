#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 James and minc
"""Mock TSecBench "Challenges API" plus the VPN precheck endpoint.

The module starts two independent HTTP servers in one process:

* the *challenges API* (``--port``, and optionally ``--challenge-port`` as a
  second listener) serving ``/openapi/v1/challenges*`` and the ``_test`` control
  routes, and
* the *VPN precheck* endpoint (``--vpn-port``) serving ``GET /``.

Everything is standard library only (Python 3.9+), so the mock can be started
offline next to the program under test::

    python mock_tsec_api.py --port 8099 --token test-token \
        --challenge-port 8098 --vpn-port 8097

See ``README.md`` in this directory for the full contract (fixtures, flag
derivation, control endpoints, port layout).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import time
import traceback
from dataclasses import dataclass
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple
from urllib.parse import parse_qs, urlparse

# --------------------------------------------------------------------------- #
# Constants
# --------------------------------------------------------------------------- #

API_PREFIX = "/openapi/v1"
CHALLENGES_COLLECTION = API_PREFIX + "/challenges"
TEST_PREFIX = API_PREFIX + "/_test/"

#: Header carrying the benchmark token on every ``/openapi/v1/...`` request.
HEADER_NAME = "BENCHMARK_TOKEN"

#: Challenges in state ``pending`` or ``available`` count against this limit.
MAX_ACTIVE_INSTANCES = 3

#: Address advertised for a started container (mock: a single, stable address).
CONTAINER_ADDR = "10.0.1.5:8080"

#: Wall clock delay between ``pending`` and ``available``.
DEFAULT_READY_DELAY = 1.5

#: Longest accepted flag.
MAX_FLAG_LENGTH = 4096

#: How long ``--vpn-timeout`` keeps a request hanging.
VPN_TIMEOUT_SECONDS = 60.0

#: Responses a test can poison the next route with: mode -> (status, raw body).
#: The 200s are valid HTTP whose shape is WRONG for the API (to prove the client
#: rejects fake successes); "internal500" drives a genuine platform-style 500.
POISON_RESPONSES = {
    "html": (200, b"<html>502 Bad Gateway from an over-eager proxy</html>"),
    "text": (200, b"OK"),
    "array": (200, b"[1]"),
    "emptyobj": (200, b"{}"),
    "empty": (200, b""),
    "internal500": (
        500,
        b'{"code":"internal_error","message":"simulated platform internal error","detail":{}}',
    ),
}

#: Poison route key -> platform path the poison applies to.
ROUTE_PATHS = {
    "list": CHALLENGES_COLLECTION,
    "start": CHALLENGES_COLLECTION + "/start",
    "hint": CHALLENGES_COLLECTION + "/hint",
    "submit": CHALLENGES_COLLECTION + "/submit",
    "close": CHALLENGES_COLLECTION + "/close",
}

#: Modes the VPN precheck endpoint can be switched into at run time.
VPN_MODES = ("ok", "down", "html", "status500")

DEFAULT_TOKEN = "test-token"
SWEEP_INTERVAL = 0.05

# Routes. ``path -> handler name``; the HTTP method decides which table is used.
ROUTES_GET = {
    CHALLENGES_COLLECTION: "list",
    CHALLENGES_COLLECTION + "/hint": "hint",
    TEST_PREFIX + "state": "state",
}
ROUTES_POST = {
    CHALLENGES_COLLECTION + "/start": "start",
    CHALLENGES_COLLECTION + "/submit": "submit",
    CHALLENGES_COLLECTION + "/close": "close",
    TEST_PREFIX + "expire": "expire",
    TEST_PREFIX + "reset": "reset",
    TEST_PREFIX + "freeze": "freeze",
    TEST_PREFIX + "poison": "poison",
}


def _now_str() -> str:
    """Current local time formatted like the upstream service."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _error(code: str, message: str, detail: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Build the error envelope used by the upstream API."""
    return {"code": code, "message": message, "detail": detail if detail is not None else {}}


def _missing_field(loc: Sequence[str]) -> Dict[str, Any]:
    """FastAPI/Pydantic style 422 body for a missing field."""
    return {"detail": [{"type": "missing", "loc": list(loc), "msg": "Field required", "input": None}]}


def _invalid_field(loc: Sequence[str], msg: str, type_: str, value: Any) -> Dict[str, Any]:
    """FastAPI/Pydantic style 422 body for an invalid field."""
    return {"detail": [{"loc": list(loc), "msg": msg, "type": type_, "input": value}]}


def _normalise_path(path: str) -> str:
    """Drop a single trailing slash so ``/x`` and ``/x/`` route identically."""
    if len(path) > 1 and path.endswith("/"):
        return path.rstrip("/") or "/"
    return path


def _query_first(query: Dict[str, List[str]], key: str) -> Optional[str]:
    values = query.get(key)
    if not values:
        return None
    return values[0]


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Fixture:
    """Static description of one benchmark challenge."""

    unique_code: str
    description: Optional[str]
    difficulty: str  # easy | medium | hard
    level: int
    total_score: int
    flag_count: int
    hint: Optional[str]
    #: Extra accepted flags; each maps onto flag slot 0 of this challenge.
    alias_flags: Tuple[str, ...] = ()
    #: Challenge starts out fully solved (is_completed: true at startup).
    precompleted: bool = False
    #: ``start`` always fails with 503 ``resource_unavailable``.
    start_unavailable: bool = False


FIXTURES: Tuple[Fixture, ...] = (
    Fixture(
        unique_code="web-easy-sqli-01",
        description="Classic SQL injection in the login form of a PHP guestbook.",
        difficulty="easy",
        level=1,
        total_score=100,
        flag_count=1,
        hint="The username field is concatenated into the query. Try `' OR 1=1 -- `.",
        # Dedicated readable flag, documented in the README.
        alias_flags=("flag{SQLi_1s_fun}",),
    ),
    Fixture(
        unique_code="web-medium-xss-02",
        description="Stored XSS in the guestbook; an admin bot reviews every entry.",
        difficulty="medium",
        level=2,
        total_score=300,
        flag_count=3,
        hint="The filter is a naive blacklist - try an event handler it does not know.",
    ),
    Fixture(
        unique_code="pwn-hard-heap-03",
        description="Heap overflow in a custom allocator with safe-linking enabled.",
        difficulty="hard",
        level=3,
        total_score=500,
        flag_count=2,
        hint=None,  # this fixture reports a null hint
    ),
    Fixture(
        unique_code="crypto-easy-rsa-04",
        description="Textbook RSA with a prime shared between two moduli.",
        difficulty="easy",
        level=1,
        total_score=200,
        flag_count=2,
        hint="Compute gcd(n1, n2) to factor both moduli.",
        precompleted=True,  # already is_completed at startup
    ),
    Fixture(
        unique_code="misc-medium-forensics-05",
        description="Traffic capture of an exfiltration; the backend is out of capacity.",
        difficulty="medium",
        level=2,
        total_score=503,
        flag_count=1,
        hint="Look at the HTTP POST bodies inside the pcap.",
        start_unavailable=True,  # start -> 503 resource_unavailable
    ),
    Fixture(
        unique_code="web-medium-ssrf-06",
        description="SSRF in the avatar fetcher; the cloud metadata endpoint is reachable.",
        difficulty="medium",
        level=2,
        total_score=200,
        flag_count=2,
        hint="Try http://169.254.169.254/latest/meta-data/ through the url parameter.",
    ),
)


def derived_flags(fixture: Fixture) -> List[str]:
    """Deterministic expected flags: ``flag{<unique_code>_<i>}`` for i in 0..N-1."""
    return ["flag{%s_%d}" % (fixture.unique_code, i) for i in range(fixture.flag_count)]


def award_for(fixture: Fixture, slot: int) -> int:
    """Points awarded for solving flag slot ``slot`` (remainder goes to the last slot)."""
    base, remainder = divmod(fixture.total_score, fixture.flag_count)
    return base + (remainder if slot == fixture.flag_count - 1 else 0)


def match_slot(fixture: Fixture, flag: str) -> Optional[int]:
    """Return the flag slot ``flag`` solves, or ``None``."""
    flags = derived_flags(fixture)
    if flag in flags:
        return flags.index(flag)
    if flag in fixture.alias_flags:
        return 0
    return None


class _Runtime:
    """Mutable per-challenge state."""

    __slots__ = ("status", "solved_slots", "submitted_flags", "hint_taken", "ready_at")

    def __init__(self) -> None:
        self.status: str = "stopped"
        self.solved_slots: Set[int] = set()
        self.submitted_flags: List[str] = []  # accepted flags, in submission order
        self.hint_taken: bool = False
        self.ready_at: Optional[float] = None  # time.monotonic() deadline


# --------------------------------------------------------------------------- #
# State machine
# --------------------------------------------------------------------------- #


class MockChallengesState:
    """Thread-safe state for the challenges API.

    Every public method returns ``(http_status, json_payload)`` and takes the
    lock for the whole operation, so a request never observes a half-applied
    transition.
    """

    def __init__(
        self,
        fixtures: Sequence[Fixture] = FIXTURES,
        ready_delay: float = DEFAULT_READY_DELAY,
        container_addr: str = CONTAINER_ADDR,
    ) -> None:
        self._lock = threading.RLock()
        self._fixtures: List[Fixture] = list(fixtures)
        self._by_code: Dict[str, Fixture] = {f.unique_code: f for f in self._fixtures}
        if len(self._by_code) != len(self._fixtures):
            raise ValueError("fixture unique_code values must be unique")
        self._ready_delay = ready_delay
        self._container_addr = container_addr
        self._expired = False
        self._frozen = False
        self._poison: Optional[Tuple[str, Tuple[int, bytes]]] = None
        self._list_fetch_count = 0
        self._runtime: Dict[str, _Runtime] = {}
        self._submissions: List[Dict[str, Any]] = []
        self._seq = 0
        self.reset()

    # -- lifecycle --------------------------------------------------------- #

    def reset(self) -> None:
        """Restore the initial state (including the seeded completed fixture)."""
        with self._lock:
            self._expired = False
            self._frozen = False
            self._poison = None
            self._list_fetch_count = 0
            self._runtime = {f.unique_code: _Runtime() for f in self._fixtures}
            self._submissions = []
            self._seq = 0
            for fixture in self._fixtures:
                if not fixture.precompleted:
                    continue
                runtime = self._runtime[fixture.unique_code]
                for slot, flag in enumerate(derived_flags(fixture)):
                    runtime.solved_slots.add(slot)
                    runtime.submitted_flags.append(flag)
                    self._record_locked(fixture.unique_code, flag, "correct", slot, award_for(fixture, slot), seeded=True)

    def expire(self) -> None:
        """Flip the task-expiry switch: every non-``_test`` API call then 409s."""
        with self._lock:
            self._expired = True

    def freeze(self, frozen: bool = True) -> None:
        """Stop the background sweeper from promoting ``pending`` to ``available``."""
        with self._lock:
            self._frozen = frozen

    def set_poison(self, mode: str, route: str) -> None:
        """Arm a one-shot poisoned response for the next ``route`` call."""
        response = POISON_RESPONSES.get(mode)
        if response is None:
            raise KeyError("unknown poison mode: %s" % mode)
        with self._lock:
            self._poison = (route, response)

    def take_poison(self, path: str) -> Optional[Tuple[int, bytes]]:
        """Return (and disarm) the poisoned (status, body) if it targets ``path``."""
        if path.startswith(TEST_PREFIX):
            return None
        with self._lock:
            if self._poison is None:
                return None
            route, response = self._poison
            if route != "*" and ROUTE_PATHS.get(route) != path:
                return None
            self._poison = None
            return response

    def promote_ready(self) -> None:
        """Move ``pending`` challenges whose timer elapsed to ``available``.

        Called by the background sweeper thread, so the transition happens even
        when no request is in flight.
        """
        now = time.monotonic()
        with self._lock:
            if self._frozen:
                return
            for runtime in self._runtime.values():
                if runtime.status == "pending" and runtime.ready_at is not None and now >= runtime.ready_at:
                    runtime.status = "available"
                    runtime.ready_at = None

    @property
    def expired(self) -> bool:
        with self._lock:
            return self._expired

    # -- read helpers (lock held by caller) -------------------------------- #

    def _active_count_locked(self) -> int:
        return sum(1 for rt in self._runtime.values() if rt.status in ("pending", "available"))

    def _cumulative_score_locked(self) -> int:
        total = 0
        for fixture in self._fixtures:
            runtime = self._runtime[fixture.unique_code]
            total += sum(award_for(fixture, slot) for slot in runtime.solved_slots)
        return total

    def _payload_locked(self, fixture: Fixture, runtime: _Runtime) -> Dict[str, Any]:
        status = runtime.status
        return {
            "unique_code": fixture.unique_code,
            "description": fixture.description,
            "difficulty": fixture.difficulty,
            "level": fixture.level,
            "total_score": fixture.total_score,
            "flag_count": fixture.flag_count,
            "correct_flag_count": len(runtime.solved_slots),
            "is_completed": len(runtime.solved_slots) >= fixture.flag_count,
            # Invariant: an address is only exposed while the container is available.
            "container_addr": [self._container_addr] if status == "available" else [],
            "container_status": status,
        }

    def _record_locked(
        self,
        unique_code: str,
        flag: str,
        result: str,
        matched_flag_index: Optional[int],
        awarded: int,
        seeded: bool = False,
    ) -> None:
        self._seq += 1
        entry: Dict[str, Any] = {
            "seq": self._seq,
            "unique_code": unique_code,
            "flag": flag,
            "result": result,
            "correct": result == "correct",
            "matched_flag_index": matched_flag_index,
            "awarded": awarded,
            "at": _now_str(),
        }
        if seeded:
            entry["seeded"] = True
        self._submissions.append(entry)

    # -- API operations ---------------------------------------------------- #

    def list_challenges(self) -> Tuple[int, Any]:
        with self._lock:
            self._list_fetch_count += 1
            payload = [self._payload_locked(f, self._runtime[f.unique_code]) for f in self._fixtures]
            return 200, payload

    def start(self, unique_code: str) -> Tuple[int, Any]:
        with self._lock:
            fixture = self._by_code.get(unique_code)
            if fixture is None:
                return 404, _error("challenge_not_found", "unknown challenge unique_code: %s" % unique_code)
            runtime = self._runtime[unique_code]

            # Idempotent: restarting an already active instance is a no-op.
            if runtime.status in ("pending", "available"):
                return 200, {"unique_code": unique_code, "container_addr": [self._container_addr]}

            # A fixture-specific resource problem is reported before cap pressure:
            # "this challenge can never start" is a property of the challenge, not
            # of how many instances happen to be running.
            if fixture.start_unavailable:
                return 503, _error(
                    "resource_unavailable",
                    "no free challenge container available for this task right now",
                )

            if self._active_count_locked() >= MAX_ACTIVE_INSTANCES:
                return 409, _error("invalid_state", "max active challenge instances reached")

            runtime.status = "pending"
            runtime.ready_at = time.monotonic() + self._ready_delay
            return 200, {"unique_code": unique_code, "container_addr": [self._container_addr]}

    def hint(self, unique_code: str) -> Tuple[int, Any]:
        with self._lock:
            fixture = self._by_code.get(unique_code)
            if fixture is None:
                return 404, _error("challenge_not_found", "unknown challenge unique_code: %s" % unique_code)
            runtime = self._runtime[unique_code]
            if len(runtime.solved_slots) >= fixture.flag_count:
                return 409, _error("invalid_state", "challenge already completed")
            runtime.hint_taken = True
            return 200, {"unique_code": unique_code, "hint": fixture.hint}

    def submit(self, unique_code: str, flag: str) -> Tuple[int, Any]:
        with self._lock:
            fixture = self._by_code.get(unique_code)
            if fixture is None:
                return 404, _error("challenge_not_found", "unknown challenge unique_code: %s" % unique_code)
            runtime = self._runtime[unique_code]

            # Same string submitted twice -> duplicate.
            if flag in runtime.submitted_flags:
                self._record_locked(unique_code, flag, "duplicate", None, 0)
                return 409, _error("duplicate", "flag was already submitted for this challenge")

            slot = match_slot(fixture, flag)
            if slot is None:
                self._record_locked(unique_code, flag, "incorrect", None, 0)
                return 200, {
                    "correct": False,
                    "awarded": 0,
                    "cumulative_score": self._cumulative_score_locked(),
                    "correct_flag_count": len(runtime.solved_slots),
                    "total_flag_count": fixture.flag_count,
                    "matched_flag_index": None,
                }

            # Another accepted spelling of a slot that is already solved.
            if slot in runtime.solved_slots:
                self._record_locked(unique_code, flag, "duplicate", slot, 0)
                return 409, _error("duplicate", "flag was already submitted for this challenge")

            awarded = award_for(fixture, slot)
            runtime.solved_slots.add(slot)
            runtime.submitted_flags.append(flag)
            self._record_locked(unique_code, flag, "correct", slot, awarded)
            return 200, {
                "correct": True,
                "awarded": awarded,
                "cumulative_score": self._cumulative_score_locked(),
                "correct_flag_count": len(runtime.solved_slots),
                "total_flag_count": fixture.flag_count,
                "matched_flag_index": slot,
            }

    def close(self, unique_code: str) -> Tuple[int, Any]:
        with self._lock:
            fixture = self._by_code.get(unique_code)
            if fixture is None:
                return 404, _error("challenge_not_found", "unknown challenge unique_code: %s" % unique_code)
            runtime = self._runtime[unique_code]
            runtime.status = "stopped"
            runtime.ready_at = None
            return 200, {"unique_code": unique_code, "closed": True}

    # -- introspection ----------------------------------------------------- #

    def state_dump(self) -> Dict[str, Any]:
        with self._lock:
            challenges = []
            hints_taken = []
            flags: Dict[str, Any] = {}
            for fixture in self._fixtures:
                runtime = self._runtime[fixture.unique_code]
                ready_in = None
                if runtime.status == "pending" and runtime.ready_at is not None:
                    ready_in = round(max(0.0, runtime.ready_at - time.monotonic()), 3)
                entry: Dict[str, Any] = {
                    "unique_code": fixture.unique_code,
                    "container_status": runtime.status,
                    "container_addr": [self._container_addr] if runtime.status == "available" else [],
                    "ready_in_seconds": ready_in,
                    "flag_count": fixture.flag_count,
                    "correct_flag_count": len(runtime.solved_slots),
                    "is_completed": len(runtime.solved_slots) >= fixture.flag_count,
                    "solved_slots": sorted(runtime.solved_slots),
                    "accepted_flags": list(runtime.submitted_flags),
                    "hint_taken": runtime.hint_taken,
                    "earned_score": sum(award_for(fixture, slot) for slot in runtime.solved_slots),
                }
                # Greppable marker: the literal string "hinted" appears anywhere in
                # the dump only once a hint has actually been fetched, so a test can
                # assert `"hinted" not in json.dumps(state)` to prove that no hint
                # request was made.
                if runtime.hint_taken:
                    entry["hinted"] = True
                challenges.append(entry)
                if runtime.hint_taken:
                    hints_taken.append(fixture.unique_code)
                flags[fixture.unique_code] = {
                    "derived": derived_flags(fixture),
                    "aliases": list(fixture.alias_flags),
                    "award_by_slot": [award_for(fixture, slot) for slot in range(fixture.flag_count)],
                }
            return {
                "expired": self._expired,
                "frozen": self._frozen,
                "active_instance_count": self._active_count_locked(),
                "max_active_instances": MAX_ACTIVE_INSTANCES,
                "cumulative_score": self._cumulative_score_locked(),
                "list_fetch_count": self._list_fetch_count,
                "challenges": challenges,
                "hints_taken": hints_taken,
                "submission_count": len(self._submissions),
                "submissions": list(self._submissions),
                "flags": flags,
            }


# --------------------------------------------------------------------------- #
# HTTP plumbing
# --------------------------------------------------------------------------- #


class MockHTTPServer(ThreadingHTTPServer):
    """Threading HTTP server carrying its own configuration as attributes."""

    daemon_threads = True
    # On Windows SO_REUSEADDR lets a *second* process silently bind a port that
    # is already in use, which would hijack a neighbouring mock. Only enable it
    # where it merely shortens TIME_WAIT (POSIX).
    allow_reuse_address = os.name != "nt"

    def __init__(self, address: Tuple[str, int], handler: type, **extra: Any) -> None:
        super().__init__(address, handler)
        for key, value in extra.items():
            setattr(self, key, value)


class _BaseHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "MockTSecBench/1.0"
    sys_version = ""

    # -- access to the owning server --------------------------------------- #
    @property
    def _srv(self) -> MockHTTPServer:
        return self.server  # type: ignore[return-value]

    # -- logging ----------------------------------------------------------- #
    def log_message(self, fmt: str, *args: Any) -> None:  # noqa: A003 - stdlib name
        """Silence the default per-request line; ``_log`` emits our own."""

    def log_error(self, fmt: str, *args: Any) -> None:
        """Silence the default error line (we report failures ourselves)."""

    def _log(self, status: int) -> None:
        name = getattr(self._srv, "name", "server")
        sys.stderr.write("[%s] [%s] %s %s -> %d\n" % (_now_str(), name, self.command, self.path, status))
        sys.stderr.flush()

    # -- request/response helpers ------------------------------------------ #
    def _read_body(self) -> bytes:
        """Read (and therefore drain) the request body."""
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except (TypeError, ValueError):
            length = 0
        if length <= 0:
            return b""
        return self.rfile.read(length)

    def _send_json(self, status: int, payload: Any) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
        self._log(status)

    def _send_raw(self, status: int, body: bytes, content_type: str = "text/html") -> None:
        """Send a hand-crafted body (used by the poison control)."""
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
        self._log(status)

    # -- method entry points ----------------------------------------------- #
    def do_GET(self) -> None:  # noqa: N802 - stdlib naming
        self._safe_dispatch("GET")

    def do_POST(self) -> None:  # noqa: N802
        self._safe_dispatch("POST")

    def do_PUT(self) -> None:  # noqa: N802
        self._safe_dispatch("PUT")

    def do_DELETE(self) -> None:  # noqa: N802
        self._safe_dispatch("DELETE")

    def do_PATCH(self) -> None:  # noqa: N802
        self._safe_dispatch("PATCH")

    def _safe_dispatch(self, method: str) -> None:
        try:
            self._dispatch(method)
        except (BrokenPipeError, ConnectionResetError):
            self.close_connection = True  # client vanished (e.g. its own timeout)
        except Exception:  # pragma: no cover - defensive
            traceback.print_exc()
            try:
                self._send_json(500, {"detail": "Internal Server Error"})
            except Exception:
                self.close_connection = True

    def _dispatch(self, method: str) -> None:
        raise NotImplementedError


# --------------------------------------------------------------------------- #
# Challenges API handler
# --------------------------------------------------------------------------- #


class ChallengesHandler(_BaseHandler):
    """``/openapi/v1/challenges*`` and ``/openapi/v1/_test/*``."""

    @property
    def _state(self) -> MockChallengesState:
        return self._srv.state  # type: ignore[attr-defined]

    def _dispatch(self, method: str) -> None:
        parsed = urlparse(self.path)
        path = _normalise_path(parsed.path)
        query = parse_qs(parsed.query, keep_blank_values=True)
        raw_body = self._read_body()  # drained up front so keep-alive stays in sync

        # 1. Authentication - before routing, before the expiry switch.
        if path == API_PREFIX or path.startswith(API_PREFIX + "/"):
            token = self.headers.get(HEADER_NAME)
            if token is None or token == "":
                self._send_json(422, _missing_field(["header", HEADER_NAME]))
                return
            if token != getattr(self._srv, "token", None):
                self._send_json(404, _error("task_not_found", "invalid or unknown benchmark token"))
                return

        # 2. Routing.
        if method == "GET":
            handler_name = ROUTES_GET.get(path)
        elif method == "POST":
            handler_name = ROUTES_POST.get(path)
        else:
            handler_name = None
        if handler_name is None:
            known = path in ROUTES_GET or path in ROUTES_POST
            if known:
                self._send_json(405, {"detail": "Method Not Allowed"})
            else:
                self._send_json(404, {"detail": "Not Found"})
            return

        # 3. One-shot poisoned response (test control): overrides the real route AND the
        #    expiry switch, so a test always gets the exact response it asked for.
        poison = self._state.take_poison(path)
        if poison is not None:
            poison_status, poison_body = poison
            self._send_raw(poison_status, poison_body)
            return

        # 4. Task-expiry switch (control routes stay reachable on purpose).
        if not path.startswith(TEST_PREFIX) and self._state.expired:
            self._send_json(409, _error("invalid_state", "benchmark task has ended"))
            return

        # 5. Execute.
        getattr(self, "_route_" + handler_name)(query, raw_body)

    # -- individual routes ------------------------------------------------- #
    def _route_list(self, query: Dict[str, List[str]], raw_body: bytes) -> None:
        status, payload = self._state.list_challenges()
        self._send_json(status, payload)

    def _route_start(self, query: Dict[str, List[str]], raw_body: bytes) -> None:
        unique_code = _query_first(query, "unique_code")
        if unique_code is None:
            self._send_json(422, _missing_field(["query", "unique_code"]))
            return
        status, payload = self._state.start(unique_code)
        self._send_json(status, payload)

    def _route_hint(self, query: Dict[str, List[str]], raw_body: bytes) -> None:
        unique_code = _query_first(query, "unique_code")
        if unique_code is None:
            self._send_json(422, _missing_field(["query", "unique_code"]))
            return
        status, payload = self._state.hint(unique_code)
        self._send_json(status, payload)

    def _route_close(self, query: Dict[str, List[str]], raw_body: bytes) -> None:
        unique_code = _query_first(query, "unique_code")
        if unique_code is None:
            self._send_json(422, _missing_field(["query", "unique_code"]))
            return
        status, payload = self._state.close(unique_code)
        self._send_json(status, payload)

    def _route_submit(self, query: Dict[str, List[str]], raw_body: bytes) -> None:
        try:
            body = json.loads(raw_body.decode("utf-8")) if raw_body.strip() else None
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._send_json(422, _invalid_field(["body"], "JSON decode error", "json_invalid", None))
            return
        if not isinstance(body, dict):
            self._send_json(422, _invalid_field(["body"], "Input should be a valid dictionary", "dict_type", None))
            return

        # Body validation mirrors FastAPI: it happens before the handler runs.
        unique_code = body.get("unique_code")
        if unique_code is None:
            self._send_json(422, _missing_field(["body", "unique_code"]))
            return
        if not isinstance(unique_code, str):
            self._send_json(422, _invalid_field(["body", "unique_code"], "Input should be a valid string", "string_type", unique_code))
            return

        if "flag" not in body or body["flag"] is None:
            self._send_json(422, _missing_field(["body", "flag"]))
            return
        flag = body["flag"]
        if not isinstance(flag, str):
            self._send_json(422, _invalid_field(["body", "flag"], "Input should be a valid string", "string_type", flag))
            return
        if not flag.strip():
            self._send_json(
                422,
                _invalid_field(
                    ["body", "flag"],
                    "String should have at least 1 character",
                    "string_too_short",
                    flag,
                ),
            )
            return
        if len(flag) > MAX_FLAG_LENGTH:
            self._send_json(
                422,
                _invalid_field(
                    ["body", "flag"],
                    "String should have at most %d characters" % MAX_FLAG_LENGTH,
                    "string_too_long",
                    flag,
                ),
            )
            return

        status, payload = self._state.submit(unique_code, flag)
        self._send_json(status, payload)

    def _route_expire(self, query: Dict[str, List[str]], raw_body: bytes) -> None:
        self._state.expire()
        self._send_json(200, {"expired": True})

    def _route_reset(self, query: Dict[str, List[str]], raw_body: bytes) -> None:
        self._state.reset()
        self._send_json(200, {"reset": True, "expired": False})

    def _route_freeze(self, query: Dict[str, List[str]], raw_body: bytes) -> None:
        """Keep every container ``pending`` regardless of its ready timer.

        ``?frozen=false`` (or 0/off) unfreezes; a bare POST freezes. ``_test/reset``
        always unfreezes.
        """
        raw = _query_first(query, "frozen")
        frozen = True if raw is None else raw.lower() not in ("0", "false", "off")
        self._state.freeze(frozen)
        self._send_json(200, {"frozen": frozen})

    def _route_poison(self, query: Dict[str, List[str]], raw_body: bytes) -> None:
        """Arm a one-shot wrong-shaped response for the next platform call."""
        mode = _query_first(query, "mode") or "html"
        route = _query_first(query, "route") or "*"
        try:
            self._state.set_poison(mode, route)
        except KeyError as exc:
            self._send_json(422, _invalid_field(["query", "mode"], str(exc), "enum", mode))
            return
        self._send_json(200, {"poison": mode, "route": route})

    def _route_state(self, query: Dict[str, List[str]], raw_body: bytes) -> None:
        self._send_json(200, self._state.state_dump())


# --------------------------------------------------------------------------- #
# VPN precheck handler
# --------------------------------------------------------------------------- #


class VpnHandler(_BaseHandler):
    """Standalone ``GET /`` used to decide whether the VPN is up.

    No authentication: the real probe has none either. A test can switch the response
    style at run time via ``POST /_test/mode?mode=<ok|down|html|status500>``.
    """

    def _dispatch(self, method: str) -> None:
        parsed = urlparse(self.path)
        path = _normalise_path(parsed.path)
        query = parse_qs(parsed.query, keep_blank_values=True)
        self._read_body()
        if path == "/_test/mode" and method == "POST":
            mode = _query_first(query, "mode") or "ok"
            if mode not in VPN_MODES:
                self._send_json(
                    422,
                    _invalid_field(["query", "mode"], "unknown vpn mode", "enum", mode),
                )
                return
            self._srv.vpn_mode = mode
            self._send_json(200, {"vpn_mode": mode})
            return
        if method != "GET" or path != "/":
            self._send_json(404, {"detail": "Not Found"})
            return
        if getattr(self._srv, "vpn_timeout", False):
            time.sleep(VPN_TIMEOUT_SECONDS)
        mode = getattr(self._srv, "vpn_mode", "ok")
        if mode == "down":
            self._send_json(200, {"status": "down"})
            return
        if mode == "html":
            self._send_raw(200, b"<html>intercepted by a captive portal</html>")
            return
        if mode == "status500":
            self._send_json(500, {"detail": "Internal Server Error"})
            return
        self._send_json(200, {"client_ip": "10.0.0.1", "status": "ok", "time": _now_str()})


# --------------------------------------------------------------------------- #
# Wiring
# --------------------------------------------------------------------------- #


def _sweeper_loop(state: MockChallengesState, stop_event: threading.Event) -> None:
    """Promote ``pending`` containers to ``available`` without any request."""
    while not stop_event.wait(SWEEP_INTERVAL):
        state.promote_ready()


def bind_server(
    address: Tuple[str, int],
    handler: type,
    attempts: int = 6,
    delay: float = 0.5,
    **extra: Any
) -> MockHTTPServer:
    """Bind ``address``, retrying briefly so a restart does not race TIME_WAIT."""
    last_error: Optional[OSError] = None
    for attempt in range(max(1, attempts)):
        try:
            return MockHTTPServer(address, handler, **extra)
        except OSError as exc:
            last_error = exc
            if attempt + 1 < attempts:
                time.sleep(delay)
    assert last_error is not None
    raise last_error


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Mock TSecBench Challenges API + VPN precheck endpoint (stdlib only).",
    )
    parser.add_argument("--host", default="127.0.0.1", help="bind address for both servers (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8099, help="challenges API port (default: 8099)")
    parser.add_argument(
        "--challenge-port",
        type=int,
        default=8098,
        help="second listener for the same challenges API (default: 8098); ignored when equal to --port",
    )
    parser.add_argument("--vpn-port", type=int, default=8097, help="VPN precheck port (default: 8097)")
    parser.add_argument("--token", default=DEFAULT_TOKEN, help="value expected in the BENCHMARK_TOKEN header")
    parser.add_argument(
        "--container-addr",
        default=CONTAINER_ADDR,
        help="address advertised in container_addr (default: %s)" % CONTAINER_ADDR,
    )
    parser.add_argument(
        "--ready-delay",
        type=float,
        default=DEFAULT_READY_DELAY,
        help="seconds between start (pending) and available (default: 1.5)",
    )
    parser.add_argument("--vpn-fail", action="store_true", help="VPN precheck answers {'status': 'down'}")
    parser.add_argument(
        "--vpn-timeout",
        action="store_true",
        help="VPN precheck sleeps %d s before answering" % int(VPN_TIMEOUT_SECONDS),
    )
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)

    state = MockChallengesState(FIXTURES, ready_delay=args.ready_delay, container_addr=args.container_addr)
    stop_event = threading.Event()
    threading.Thread(target=_sweeper_loop, args=(state, stop_event), name="pending-sweeper", daemon=True).start()

    servers: List[MockHTTPServer] = []
    try:
        api = bind_server((args.host, args.port), ChallengesHandler, name="challenges", state=state, token=args.token)
        servers.append(api)
        vpn = bind_server(
            (args.host, args.vpn_port),
            VpnHandler,
            name="vpn",
            vpn_mode="down" if args.vpn_fail else "ok",
            vpn_timeout=args.vpn_timeout,
        )
        servers.append(vpn)
    except OSError as exc:
        sys.stderr.write("error: cannot bind %s (is another process using the port?)\n" % (exc,))
        for server in servers:
            server.server_close()
        return 2

    # The same challenges API is also served on --challenge-port so a caller can
    # use either port. A busy port is not fatal: we just skip the alias (binding
    # it anyway would hijack whatever already listens there).
    if args.challenge_port and args.challenge_port != args.port:
        try:
            servers.append(
                bind_server(
                    (args.host, args.challenge_port),
                    ChallengesHandler,
                    attempts=1,
                    name="challenges",
                    state=state,
                    token=args.token,
                )
            )
        except OSError as exc:
            sys.stderr.write("[warn] --challenge-port %d not bound: %s\n" % (args.challenge_port, exc))

    sys.stderr.write("mock TSecBench ready (token=%s)\n" % args.token)
    for server in servers:
        sys.stderr.write("  [%s] http://%s:%d/\n" % (server.name, args.host, server.server_address[1]))
    sys.stderr.write("  challenges API : http://%s:%d%s\n" % (args.host, args.port, CHALLENGES_COLLECTION))
    sys.stderr.write(
        "  vpn precheck   : http://%s:%d/  (fail=%s timeout=%s)\n"
        % (args.host, args.vpn_port, args.vpn_fail, args.vpn_timeout)
    )
    sys.stderr.flush()

    # The VPN server (and the optional alias listener) run in background threads.
    for server in servers[1:]:
        threading.Thread(
            target=server.serve_forever,
            name="serve-%s-%d" % (server.name, server.server_address[1]),
            daemon=True,
        ).start()

    try:
        api.serve_forever()
    except KeyboardInterrupt:
        sys.stderr.write("\nmock TSecBench shutting down\n")
    finally:
        stop_event.set()
        for server in servers:
            try:
                server.shutdown()
            except Exception:
                pass
            server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
