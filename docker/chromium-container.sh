#!/bin/sh
# Launch Chromium the way a container running as root needs it.
#
# Chromium refuses to start as root without --no-sandbox, and a container's /dev/shm
# is normally too small for its default shared-memory use. Nothing in
# chrome-devtools-mcp 0.6.0 can pass extra browser arguments — its only relevant
# flag is --executablePath — so docker/claude/mcp.json points that flag at this
# wrapper instead of at the browser.
#
# --no-sandbox grants nothing here: the process already runs as root inside the
# benchmark sandbox, so it is not a privilege boundary being dropped.
set -eu

exec /usr/bin/chromium \
  --no-sandbox \
  --disable-dev-shm-usage \
  --disable-gpu \
  --no-first-run \
  --no-default-browser-check \
  "$@"
