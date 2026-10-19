# Mock TSecBench API

An offline, dependency-free stand-in for the TSecBench *Challenges API* and its
*VPN precheck* endpoint, so a client/MCP server can be exercised without the real
platform.

* `mock_tsec_api.py` — the whole mock (Python 3.9+ **standard library only**:
  `http.server`/`socketserver`, `json`, `argparse`, `threading`, `urllib.parse`).
* `README.md` — this file.

## Start it

```console
python mock_tsec_api.py --port 8099 --token test-token --challenge-port 8098 --vpn-port 8097
```

That is the canonical invocation; every flag has a default, so
`python mock_tsec_api.py` works too. `Ctrl+C` shuts both servers down.

| Flag | Default | Meaning |
| --- | --- | --- |
| `--host` | `127.0.0.1` | Bind address for both servers. |
| `--port` | `8099` | Challenges API port (the primary listener). |
| `--challenge-port` | `8098` | Second listener serving the *same* challenges API (see below). |
| `--vpn-port` | `8097` | VPN precheck port. |
| `--token` | `test-token` | Expected value of the `BENCHMARK_TOKEN` header. |
| `--container-addr` | `10.0.1.5:8080` | Address advertised in `container_addr`. |
| `--ready-delay` | `1.5` | Seconds between `start` (`pending`) and `available`. |
| `--vpn-fail` | off | VPN precheck answers `{"status": "down"}` (still HTTP 200). |
| `--vpn-timeout` | off | VPN precheck sleeps 60 s before answering. |

### Port layout, and what `--challenge-port` means here

| Port | Serves |
| --- | --- |
| `8099` (`--port`) | Challenges API: `/openapi/v1/challenges*`, `/openapi/v1/_test/*` |
| `8098` (`--challenge-port`) | The **same** challenges API, same token, same state |
| `8097` (`--vpn-port`) | VPN precheck: `GET /` |

The canonical command line names three ports but only two services were
specified. To make the mock usable whichever port a caller was configured with,
the challenges API is bound on **both** `--port` and `--challenge-port` (they
share one `MockChallengesState`, so a `start` on 8098 is visible on 8099 and vice
versa). If `--challenge-port` is already taken the mock logs
`[warn] --challenge-port ... not bound` and keeps serving on `--port`; it never
steals a port that another process holds. `--challenge-port == --port` binds once.
If you need the advertised address to match that port instead of `8080`, pass
`--container-addr 10.0.1.5:8098`.

`container_addr` is a fixed, non-routable placeholder (`10.0.1.5:8080`); nothing
listens there. Only the two HTTP servers above are real.

## Authentication

Evaluated **first**, before routing and before the expiry switch, on every path
under `/openapi/v1/` (including `_test/*`):

| Condition | HTTP | Body |
| --- | --- | --- |
| `BENCHMARK_TOKEN` header absent or empty | `422` | `{"detail":[{"type":"missing","loc":["header","BENCHMARK_TOKEN"],"msg":"Field required","input":null}]}` |
| header present but ≠ `--token` | `404` | `{"code":"task_not_found","message":"invalid or unknown benchmark token","detail":{}}` |

Paths outside `/openapi/v1/` need no token. Any unknown path returns
`404 {"detail":"Not Found"}`; a known path with the wrong method returns
`405 {"detail":"Method Not Allowed"}`.

## Endpoints

### `GET /openapi/v1/challenges`

`200` with a JSON **array** of challenge objects. Each object has exactly these
keys:

| Key | Type | Notes |
| --- | --- | --- |
| `unique_code` | str | Fixture identifier. |
| `description` | str \| null | |
| `difficulty` | str | `easy` \| `medium` \| `hard` |
| `level` | int | |
| `total_score` | int | |
| `flag_count` | int | |
| `correct_flag_count` | int | Solved flags so far (starts at `flag_count` for the pre-completed fixture). |
| `is_completed` | bool | `correct_flag_count >= flag_count` |
| `container_status` | str | `pending` \| `available` \| `stop_pending` \| `stopped` |
| `container_addr` | array of str | **`[]` unless `container_status == "available"`** |

`stop_pending` is part of the enum but no endpoint produces it (see *Deviations*).

### `POST /openapi/v1/challenges/start?unique_code=<code>`

| Case | Result |
| --- | --- |
| unknown code | `404 {"code":"challenge_not_found",...}` |
| challenge already `pending`/`available` | `200` (idempotent no-op, same body as success) |
| fixture with `total_score == 503` | `503 {"code":"resource_unavailable",...}` |
| 3 challenges already `pending`/`available` | `409 {"code":"invalid_state","message":"max active challenge instances reached","detail":{}}` — the message contains `max active` |
| success | `200 {"unique_code": "...", "container_addr": ["10.0.1.5:8080"]}` |

Checks run in that order: `404` → `503` (this fixture can never start) → `409`
(capacity). The resource check deliberately precedes the cap so that a challenge
which is intrinsically unstartable is never mistaken for cap pressure — a
"startable leftover" therefore always reports `invalid_state`/`max active` while
the cap is full. The success response advertises the container address
immediately, while the challenge object itself stays `pending` +
`container_addr: []` for `--ready-delay` seconds (default 1.5 s) and then flips
to `available` with a non-empty `container_addr`. The flip is driven by a
background sweeper thread (50 ms tick), so it happens with no further requests.

### `GET /openapi/v1/challenges/hint?unique_code=<code>`

| Case | Result |
| --- | --- |
| unknown code | `404 {"code":"challenge_not_found",...}` |
| challenge already completed | `409 {"code":"invalid_state","message":"challenge already completed","detail":{}}` |
| success | `200 {"unique_code": "...", "hint": "<text>"}` (or `"hint": null` for `pwn-hard-heap-03`) |

Taking a hint is recorded per challenge and surfaced by `GET /openapi/v1/_test/state`.

### `POST /openapi/v1/challenges/submit`

Body: `{"unique_code": "...", "flag": "..."}`.

| Case | Result |
| --- | --- |
| body not a JSON object | `422 {"detail":[{"loc":["body"],"msg":"JSON decode error","type":"json_invalid","input":null}]}` |
| `unique_code` missing/non-string | `422` with `loc:["body","unique_code"]` |
| `flag` missing/null | `422 {"detail":[{"loc":["body","flag"],"msg":"Field required","type":"missing","input":null}]}` |
| `flag` blank/whitespace-only | `422` … `"type":"string_too_short"` |
| `flag` longer than 4096 chars | `422` … `"type":"string_too_long"` |
| unknown code | `404 {"code":"challenge_not_found",...}` |
| flag was already submitted correctly (or is an alias of an already-solved slot) | `409 {"code":"duplicate","message":"flag was already submitted for this challenge","detail":{}}` |
| flag matches an expected flag | `200 {"correct":true,"awarded":<int>,"cumulative_score":<int>,"correct_flag_count":<int>,"total_flag_count":<int>,"matched_flag_index":<int>}` |
| anything else | `200 {"correct":false,"awarded":0,"cumulative_score":<int>,"correct_flag_count":<int>,"total_flag_count":<int>,"matched_flag_index":null}` |

Body validation happens before the code lookup, mirroring FastAPI. Flags are
compared **byte-exact — no trimming**, so do not append a newline. A flag of
exactly 4096 characters is accepted; 4097 is rejected.

### `POST /openapi/v1/challenges/close?unique_code=<code>`

Unknown code → `404 challenge_not_found`. Otherwise
`200 {"unique_code": "...", "closed": true}` and the challenge becomes `stopped`
with `container_addr: []`. Already-solved flags are kept.

## Fixtures

Six challenges are defined: the five required behaviours plus one extra plain
startable fixture, so a lifecycle test can fill the cap of 3, attempt a 4th and
then succeed after closing one. Any other code is the "unknown challenge" case.

| `unique_code` | difficulty | level | total_score | flags | Special behaviour |
| --- | --- | --- | --- | --- | --- |
| `web-easy-sqli-01` | easy | 1 | 100 | 1 | Also accepts `flag{SQLi_1s_fun}` as flag slot 0. Has a text hint. |
| `web-medium-xss-02` | medium | 2 | 300 | 3 | Partial progress + `duplicate` are exercisable here. Text hint. |
| `pwn-hard-heap-03` | hard | 3 | 500 | 2 | **`hint` is `null`**. |
| `crypto-easy-rsa-04` | easy | 1 | 200 | 2 | **Already `is_completed: true` at startup** (both flags seeded as submitted). |
| `misc-medium-forensics-05` | medium | 2 | **503** | 1 | `start` always returns `503 resource_unavailable`. |
| `web-medium-ssrf-06` | medium | 2 | 200 | 2 | Plain startable fixture (the 4th startable one, for cap/close tests). |

Expected flags — deterministic derivation:

```
flag{<unique_code>_<i>}   for i in 0 .. flag_count-1
```

| Fixture | Expected flags |
| --- | --- |
| `web-easy-sqli-01` | `flag{web-easy-sqli-01_0}` **and** `flag{SQLi_1s_fun}` (alias → slot 0) |
| `web-medium-xss-02` | `flag{web-medium-xss-02_0}`, `flag{web-medium-xss-02_1}`, `flag{web-medium-xss-02_2}` |
| `pwn-hard-heap-03` | `flag{pwn-hard-heap-03_0}`, `flag{pwn-hard-heap-03_1}` |
| `crypto-easy-rsa-04` | `flag{crypto-easy-rsa-04_0}`, `flag{crypto-easy-rsa-04_1}` (both already solved) |
| `misc-medium-forensics-05` | `flag{misc-medium-forensics-05_0}` |
| `web-medium-ssrf-06` | `flag{web-medium-ssrf-06_0}`, `flag{web-medium-ssrf-06_1}` |

Scoring: `award = total_score // flag_count` per flag, with the integer remainder
added to the **last** slot (so `300/3 → 100,100,100`; `500/2 → 250,250`;
`503/1 → 503`).

`cumulative_score` is the **task-wide** total — the sum of every award over every
challenge — not a per-challenge figure. Because `crypto-easy-rsa-04` starts
completed, the baseline at startup is **200**. Per-challenge earned score is
available as `earned_score` in `_test/state`. Worked example from a fresh start:

| Action | `awarded` | `cumulative_score` |
| --- | --- | --- |
| (startup) | — | 200 |
| submit `flag{web-medium-xss-02_0}` | 100 | 300 |
| submit `flag{web-medium-xss-02_1}` | 100 | 400 |
| submit `flag{web-medium-xss-02_2}` (completes) | 100 | 500 |
| submit `flag{SQLi_1s_fun}` | 100 | 600 |

## Control endpoints (`_test`)

All require a valid `BENCHMARK_TOKEN`, and all are **exempt from the expiry
switch** so a test can always reset.

| Endpoint | Effect |
| --- | --- |
| `POST /openapi/v1/_test/expire` | `200 {"expired": true}`. From then on every `/openapi/v1/challenges*` call (except `_test/*`) returns `409 {"code":"invalid_state","message":"benchmark task has ended","detail":{}}`. |
| `POST /openapi/v1/_test/reset` | `200 {"reset": true, "expired": false}`. Restores the initial state: expiry off, all challenges `stopped` with `container_addr: []`, the pre-completed fixture solved again (and its two seeded submissions restored), hints cleared, submit history empty except the two seeded entries, active count 0. |
| `GET /openapi/v1/_test/state` | `200` with a JSON dump (below). |

`GET /openapi/v1/_test/state` returns:

```jsonc
{
  "expired": false,
  "active_instance_count": 0,          // pending + available
  "max_active_instances": 3,
  "cumulative_score": 200,             // task-wide
  "challenges": [                      // per challenge runtime view
    {
      "unique_code": "web-easy-sqli-01",
      "container_status": "stopped",
      "container_addr": [],
      "ready_in_seconds": null,        // >0 while pending
      "flag_count": 1,
      "correct_flag_count": 0,
      "is_completed": false,
      "solved_slots": [],
      "accepted_flags": [],            // correctly submitted flags, in order
      "hint_taken": false,
      "earned_score": 0
      // "hinted": true is added *only* once a hint has been fetched, so the
      // literal string "hinted" appearing anywhere in this dump proves that at
      // least one hint request reached the mock:
      //   assertNotIn("hinted", json.dumps(state).lower())
    }
  ],
  "hints_taken": [],                   // challenges a hint was taken for (codes)
  "submission_count": 3,
  "submissions": [                     // full submit history, oldest first
    {
      "seq": 1, "unique_code": "crypto-easy-rsa-04", "flag": "flag{crypto-easy-rsa-04_0}",
      "result": "correct",             // correct | incorrect | duplicate
      "correct": true, "matched_flag_index": 0, "awarded": 100,
      "at": "2026-10-16 15:43:14",
      "seeded": true                   // only on entries created by reset/startup
    }
  ],
  "flags": {                           // exact accepted flags and awards, per challenge
    "web-easy-sqli-01": {
      "derived": ["flag{web-easy-sqli-01_0}"],
      "aliases": ["flag{SQLi_1s_fun}"],
      "award_by_slot": [100]
    }
  }
}
```

## VPN precheck (port `--vpn-port`, default 8097)

`GET /` → `200` (no authentication):

```json
{"client_ip": "10.0.0.1", "status": "ok", "time": "2026-10-16 15:43:14"}
```

`time` is the current local time as `%Y-%m-%d %H:%M:%S`.

* `--vpn-fail` → `200 {"status": "down"}` (the body is exactly that object).
* `--vpn-timeout` → the handler sleeps 60 s before replying, so a client with a
  shorter timeout observes a hang; a normal reply follows after 60 s.
* Any other path → `404 {"detail": "Not Found"}`.

Both servers are `ThreadingHTTPServer`s, so a hanging VPN probe never blocks the
challenges API, and concurrent API calls cannot deadlock.

## Logging

Every request is logged to **stderr** as one line:

```
[2026-10-16 15:43:14] [challenges] GET /openapi/v1/challenges -> 422
[2026-10-16 15:43:14] [vpn] GET / -> 200
```

Startup also prints the bound URLs and the token. Requests that are still
sleeping (or whose client disconnected first) log only when they answer.

## Verification performed

Started exactly:

```console
python mock_tsec_api.py --port 8099 --token test-token --challenge-port 8098 --vpn-port 8097
```

then drove it over real HTTP with `urllib` (62 assertions, all passing). Results:

| Check | Observed |
| --- | --- |
| `GET /openapi/v1/challenges` with no / empty header | `422` + the exact `Field required` body |
| same with a wrong token, incl. on a POST-only path | `404 task_not_found` (auth precedes routing) |
| unknown path, wrong method | `404 {"detail":"Not Found"}`, `405` |
| list | `200`, 6 challenges, exact key set, `container_addr == []` for every non-`available` entry |
| `start` unknown | `404 challenge_not_found` |
| `start` on `misc-medium-forensics-05` | `503 resource_unavailable` |
| `start` `web-easy-sqli-01` | `200 {"unique_code":"web-easy-sqli-01","container_addr":["10.0.1.5:8080"]}` |
| state right after start | `pending`, `container_addr: []` |
| same challenge 1.8 s later, **no request in between** | `available`, `container_addr: ["10.0.1.5:8080"]` (background sweeper) |
| 4th `start` with 3 active (startable fixture `web-medium-ssrf-06`) | `409 invalid_state`, message contains `max active` |
| 503 fixture while the cap is full | still `503 resource_unavailable` (resource precedes cap) |
| `close` that frees a slot, then the capped `start` | `200` with `10.0.1.5:8080` |
| re-`start` of an active challenge | `200` (idempotent) |
| `hint` on the completed fixture / unknown / `pwn-hard-heap-03` | `409 challenge already completed`, `404`, `200 {"hint": null}` |
| `hint` recorded | `_test/state.hints_taken`, and the `hinted` marker appears; `reset` removes it again |
| `submit` with flag missing / blank / 4097 chars | `422` (`missing` / `string_too_short` / `string_too_long`) |
| `submit` with 4096 chars | `200 correct:false` |
| `submit` unknown code / wrong flag | `404 challenge_not_found` / `200` all-zero payload |
| `submit` correct flags 0,1,2 of the 3-flag challenge | `awarded 100` each, `cumulative_score` 300 → 400 → 500, `matched_flag_index` 0,1,2, `is_completed` true at the end |
| resubmit of a correct flag / seeded flag | `409 duplicate` |
| `submit flag{SQLi_1s_fun}` | `200 correct:true matched_flag_index:0` |
| `submit` a correct flag of the 503 fixture | `200 correct:true awarded:503` (only `start` is blocked) |
| `close` known / unknown | `200 {"closed": true}` → `stopped` + `[]`; `404` |
| `_test/expire` then list / start / hint / close / submit | all `409 benchmark task has ended`; `_test/state` still `200`; `_test` without token `422` |
| `_test/reset` | `200`; list clean, pre-completed fixture intact, hints/history/active count cleared, expiry off, `start` works again |
| `--challenge-port` listener | same API and state as `--port` |
| VPN ok mode | `200 {"client_ip":"10.0.0.1","status":"ok","time":...}` |
| `--vpn-fail` | `200 {"status": "down"}` in 0.08 s, API unaffected |
| `--vpn-timeout` | client timed out after 3 s, server survived, API answered in 0.01 s meanwhile |
| 40 concurrent `GET /challenges` during a pending transition | no errors, 1.33 s total |
| restart on the same ports immediately after killing the previous instance | binds fine (6 × 0.5 s retry) |
| second instance on the same ports | exits `2` with a one-line error (no port hijacking on Windows) |
| `python -m py_compile`, `ast.parse(..., feature_version=(3,9))` | clean |

The sibling suite in this directory (`test_tsecbench_mcp.py`, which boots this
mock as a subprocess on ports 18099/18098/18097 and drives the MCP tools against
it) also passes end to end:

```console
python -B mcp\tests\test_tsecbench_mcp.py   # Ran 36 tests ... OK
```

Two mock-side adjustments came out of that run and are described above: the
`hinted` marker in `_test/state` (their "the hint gate must be real" assertion
could otherwise never fail) and the extra startable fixture `web-medium-ssrf-06`
plus the `503`-before-`409` precedence (their cap-recovery test needs a
*startable* leftover, otherwise the intrinsically unstartable fixture looks like
cap pressure).

## Deviations, judgement calls and things not verified

* **Order of `start` failures**: `404` → `503` (fixture-specific) → `409`
  (capacity). The resource check precedes the cap on purpose, so an
  intrinsically unstartable challenge is never mistaken for cap pressure.
* **`cumulative_score` is task-wide** (baseline 200 from the pre-completed
  fixture). If the intended meaning was per-challenge, the numbers are in the
  worked example table — the mock would need a one-line change in `submit`.
* **`--challenge-port`** is interpreted as a second listener for the same API
  (see above); the advertised `container_addr` stays `10.0.1.5:8080` as specified
  (override with `--container-addr`).
* **Restarting an active challenge** returns `200` rather than `409`; the spec
  does not define this case.
* **`stop_pending`** is accepted in the schema but never produced — no endpoint
  was specified that needs it.
* Flags are **not trimmed**; aliases map to slot 0, and submitting a different
  spelling of an already-solved slot is reported as `duplicate` (409) so a slot
  can never be scored twice.
* **Not verified**: behaviour under an actual 60 s `--vpn-timeout` reply (only
  the hang was observed), and `--host` values other than `127.0.0.1`.
