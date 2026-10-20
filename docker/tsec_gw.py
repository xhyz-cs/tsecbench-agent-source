#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 James and minc
"""Validate direct HTTPS API URLs or rewrite a public model API URL for TSecBench.

Direct official HTTPS API use is the default. Gateway conversion remains an
explicit option for runtimes that require platform gateway routing
(docs/platform-modes.md §3.2):

    0. the upstream API must be on the platform's allowlist;
    1. append `.tsecbench.gw` to the original hostname;
    2. https -> http.

    https://api.deepseek.com/v1  ->  http://api.deepseek.com.tsecbench.gw/v1

Usage:
    python3 tsec_gw.py validate-direct <url> # validate an HTTPS provider URL for direct use
    python3 tsec_gw.py convert <url>         # print the gateway form
    python3 tsec_gw.py check <url>           # exit 0 if already in gateway form
    python3 tsec_gw.py is-public <url>       # exit 0 if this looks like a public URL

`convert` is idempotent: an already-converted URL comes back unchanged.
"""

from __future__ import annotations

import sys
from urllib.parse import urlparse, urlunparse

GATEWAY_SUFFIX = ".tsecbench.gw"
ALLOWED_MODEL_HOSTS = {
    "api.hunyuan.cloud.tencent.com", "api.lkeap.cloud.tencent.com",
    "tokenhub.tencentmaas.com", "api.deepseek.com", "dashscope.aliyuncs.com",
    "qianfan.baidubce.com", "ark.cn-beijing.volces.com", "open.bigmodel.cn",
    "api.moonshot.cn", "api.siliconflow.cn", "spark-api-open.xf-yun.com",
    "api.minimaxi.com", "api.stepfun.com", "api.lingyiwanwu.com",
    "api.baichuan-ai.com", "api.xiaomimimo.com", "api.kimi.com",
    "token.sensenova.cn", "modelservice.jdcloud.com", "console.cloudrouter.com.cn",
}


def _host_allowed(host: str, path: str) -> bool:
    """Match the documented LLM gateway allowlist before routing credentials."""
    host = host.lower().rstrip(".")
    if host.endswith(GATEWAY_SUFFIX):
        host = host[:-len(GATEWAY_SUFFIX)]
    if host in ALLOWED_MODEL_HOSTS:
        if host == "dashscope.aliyuncs.com" and not path.startswith("/compatible-mode"):
            return False
        if host == "console.cloudrouter.com.cn" and not path.startswith("/v1"):
            return False
        return True
    if host.endswith(".maas.aliyuncs.com"):
        return path.startswith(("/compatible-mode", "/apps/anthropic"))
    return False


def _host_of(url: str) -> str:
    return (urlparse(url).hostname or "").lower()


def is_gateway_form(url: str) -> bool:
    parts = urlparse(url)
    host = _host_of(url)
    return (
        host.endswith(GATEWAY_SUFFIX)
        and parts.scheme == "http"
        and not parts.username and not parts.password and not parts.fragment
        and _host_allowed(host, parts.path)
    )


def convert(url: str) -> str:
    """Return the gateway form of ``url``. Idempotent."""
    parts = urlparse(url.strip())
    if not parts.hostname or parts.scheme not in {"http", "https"}:
        raise SystemExit("tsec_gw: expected an HTTP(S) URL with a hostname")
    if parts.username or parts.password or parts.fragment:
        raise SystemExit("tsec_gw: userinfo and URL fragments are not allowed")

    host = parts.hostname.lower()
    if not _host_allowed(host, parts.path):
        raise SystemExit("tsec_gw: model API host/path is not on the TSecBench allowlist")
    if host.endswith(GATEWAY_SUFFIX):
        if parts.scheme != "http":
            raise SystemExit("tsec_gw: gateway URLs must use HTTP")
        return urlunparse(("http", parts.netloc.lower(), parts.path or "/", "", parts.query, ""))
    if parts.scheme != "https":
        raise SystemExit("tsec_gw: public model API URLs must use HTTPS")
    if not host.endswith(GATEWAY_SUFFIX):
        host = host + GATEWAY_SUFFIX

    # Rule 2: the gateway is plain HTTP.
    netloc = host if parts.port is None else f"{host}:{parts.port}"
    return urlunparse(("http", netloc, parts.path or "/", "", parts.query, ""))


def validate_direct(url: str) -> str:
    """Validate and return an official HTTPS API URL without rewriting it."""
    parts = urlparse(url.strip())
    if not parts.hostname or parts.scheme != "https":
        raise SystemExit("tsec_gw: direct API URL must be HTTPS with a hostname")
    if parts.username or parts.password or parts.fragment:
        raise SystemExit("tsec_gw: userinfo and URL fragments are not allowed")
    try:
        parts.port  # Force urllib to reject malformed port syntax.
    except ValueError as exc:
        raise SystemExit("tsec_gw: invalid API URL port") from exc
    return url.strip()


def looks_public(url: str) -> bool:
    """Heuristic: a URL that is NOT already gateway-form."""
    return not is_gateway_form(url)


def main(argv: list[str]) -> int:
    if len(argv) != 3 or argv[1] not in {"validate-direct", "convert", "check", "is-public"}:
        print(__doc__, file=sys.stderr)
        return 64
    command, url = argv[1], argv[2]

    if command == "validate-direct":
        print(validate_direct(url))
        return 0
    if command == "convert":
        print(convert(url))
        return 0
    if command == "check":
        if is_gateway_form(url):
            print("ok: already in gateway form")
            return 0
        print(f"not in gateway form: {url}", file=sys.stderr)
        return 1
    if command == "is-public":
        return 0 if looks_public(url) else 1
    return 64


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
