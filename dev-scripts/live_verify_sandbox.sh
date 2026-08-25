#!/usr/bin/env bash
# ============================================================================
# DAP live sandbox verification — real containers, full lifecycle
# ============================================================================
# Runs the DAP API on a podman host (WSL/Linux) with
# DAP_SANDBOX_RUNTIME=podman and exercises the full sandbox lifecycle over
# HTTP, cross-checking the API state against the REAL podman container state
# at every step (podman inspect / exec). Covers:
#
#   1.  create  -> container exists (created), --network none
#   2.  start   -> running; container executes real Linux (uname -r)
#   3.  suspend -> paused   4. resume  -> running
#   5.  stop    -> exited   6. suspend from stopped -> no-op (SOLUTION 36)
#   7.  resume  -> re-starts an exited container (SOLUTION 36)
#   8.  delete  -> container destroyed
#   9.  drift   -> container lost on host -> 502, sandbox parks in error
#   10. restart -> API restart; persisted container_id still driveable
#
# Usage:
#   bash dev-scripts/live_verify_sandbox.sh [repo_root] [port]
#
# Defaults: repo_root = parent of dev-scripts/, port = 8002.
# Requires: podman on PATH; a venv with the deps (.venv-wsl or python3).
# Safe: uses a throwaway SQLite DB and removes every container it creates.

set -u

REPO="${1:-$(cd "$(dirname "$0")/.." && pwd)}"
PORT="${2:-8002}"
DB="${LIVE_VERIFY_DB:-$HOME/dap_live_verify.db}"
LOG=/tmp/dap_live_verify_server.log

# Interpreter with the deps. Override with LIVE_VERIFY_PY.
# Candidates: explicit override, home venv, WSL venv in repo, then system.
# The import probe rejects interpreters that lack the deps, and -x follows
# symlinks, so a dangling venv symlink (e.g. to a uv interpreter under
# another user) is skipped.
for candidate in "${LIVE_VERIFY_PY:-}" \
  "$HOME/.venv-dap-live/bin/python" \
  "$REPO/.venv-wsl/bin/python" \
  "$(command -v python3 2>/dev/null)"; do
  [ -z "$candidate" ] && continue
  if { [ -x "$candidate" ] || command -v "$candidate" >/dev/null 2>&1; } &&
     "$candidate" -c 'import fastapi, sqlalchemy, aiosqlite, uvicorn' 2>/dev/null; then
    PY="$candidate"; break
  fi
done
[ -n "${PY:-}" ] || { echo "FATAL: no python with the deps found (set LIVE_VERIFY_PY)"; exit 2; }

cd "$REPO"
BASE="http://127.0.0.1:$PORT"
PASS=0
FAIL=0
SRV_PID=""

command -v podman >/dev/null 2>&1 || { echo "FATAL: podman not on PATH"; exit 2; }
if ! podman image exists docker.io/library/ubuntu:24.04 2>/dev/null; then
  echo "pulling base image docker.io/library/ubuntu:24.04 ..."
  podman pull docker.io/library/ubuntu:24.04 || { echo "FATAL: image pull failed"; exit 2; }
fi

# -- helpers ---------------------------------------------------------------

cleanup() {
  [ -n "$SRV_PID" ] && kill "$SRV_PID" 2>/dev/null
  # destroy any stray dap containers (covers early failures / aborted runs)
  local strays
  strays=$(podman ps -aq --filter name=dap-sbx- 2>/dev/null || true)
  [ -n "$strays" ] && podman rm -f $strays 2>/dev/null
  rm -f "$DB"
}
trap cleanup EXIT

start_server() {
  : > "$LOG"
  TESTING=1 \
  DATABASE_URL="sqlite+aiosqlite:///$DB" \
  DAP_SANDBOX_RUNTIME=podman \
  DAP_AUTH_STRICT=0 \
  nohup "$PY" -m uvicorn src.main:app --host 127.0.0.1 --port "$PORT" >>"$LOG" 2>&1 &
  SRV_PID=$!
  local i
  for i in $(seq 1 90); do
    if curl -fsS "$BASE/health" >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
  done
  echo "FATAL: server did not come up on :$PORT"; tail -30 "$LOG"
  exit 3
}

expect() { # desc actual expected
  if [ "$2" = "$3" ]; then
    echo "  PASS  $1 [$2]"
    PASS=$((PASS + 1))
  else
    echo "  FAIL  $1 (got '$2', want '$3')"
    FAIL=$((FAIL + 1))
  fi
}

cid_state() {
  podman inspect --format '{{.State.Status}}' "$1" 2>/dev/null || echo "GONE"
}

http() { # method path [json-body] -> prints "<code>" (body goes to stdout of curl, discarded)
  local m="$1" p="$2" b="${3:-}"
  if [ -n "$b" ]; then
    curl -s -o /dev/null -w '%{http_code}' -X "$m" "$BASE$p" -H 'Content-Type: application/json' -d "$b"
  else
    curl -s -o /dev/null -w '%{http_code}' -X "$m" "$BASE$p"
  fi
}

json_field() { # body field
  printf '%s' "$1" | "$PY" -c 'import json,sys; print(json.load(sys.stdin).get(sys.argv[1], ""))' "$2"
}

# -- run -------------------------------------------------------------------

echo "== preflight: ${PY##*/} podman $(podman --version 2>/dev/null | awk '{print $3}') =="
start_server
echo "server up (pid $SRV_PID) on :$PORT, db=$DB"

expect "health reports podman runtime" \
  "$(json_field "$(curl -fsS "$BASE/health")" sandbox_runtime)" "podman"

WS=$(curl -fsS -X POST "$BASE/api/workspace/workspaces" \
  -H 'Content-Type: application/json' -d '{"name":"live-verify"}')
WS=$(json_field "$WS" id)
[ -n "$WS" ] || { echo "FATAL: workspace create failed: $WS"; exit 3; }
echo "workspace $WS"

# 1. create
echo "== 1. create =="
R=$(curl -s -w '\n%{http_code}' -X POST "$BASE/api/sandbox/sandboxes" \
  -H 'Content-Type: application/json' \
  -d "{\"workspace_id\":\"$WS\",\"stack\":\"python\",\"tier\":\"basic\"}")
CODE=${R##*$'\n'}
R=${R%$'\n'*}
expect "create returns 201" "$CODE" "201"
SID=$(json_field "$R" id)
CID=$(json_field "$R" container_id)
[ -n "$CID" ] || { echo "FATAL: no container_id in create response: $R"; exit 3; }
expect "API status creating" \
  "$(json_field "$(curl -fsS "$BASE/api/sandbox/sandboxes/$SID/status")" status)" "creating"
expect "real container exists (created)" "$(cid_state "$CID")" "created"

# 2. start
echo "== 2. start =="
expect "start -> 204" "$(http POST "/api/sandbox/sandboxes/$SID/start")" "204"
expect "container running" "$(cid_state "$CID")" "running"
expect "API status running" \
  "$(json_field "$(curl -fsS "$BASE/api/sandbox/sandboxes/$SID/status")" status)" "running"
K=$(podman exec "$CID" uname -r 2>/dev/null)
if [ -n "$K" ]; then
  echo "  PASS  container executes real Linux (kernel $K)"
  PASS=$((PASS + 1))
else
  echo "  FAIL  podman exec uname -r produced no output"
  FAIL=$((FAIL + 1))
fi
# Functional proof of --network none: only the loopback must exist inside.
NIF=$(podman exec "$CID" ls /sys/class/net 2>/dev/null | tr -d ' \n')
expect "no network inside container (--network none)" "$NIF" "lo"

# 3/4. suspend + resume
echo "== 3. suspend / 4. resume =="
expect "suspend -> 204" "$(http POST "/api/sandbox/sandboxes/$SID/suspend")" "204"
expect "container paused" "$(cid_state "$CID")" "paused"
expect "API status suspended" \
  "$(json_field "$(curl -fsS "$BASE/api/sandbox/sandboxes/$SID/status")" status)" "suspended"
expect "resume -> 204" "$(http POST "/api/sandbox/sandboxes/$SID/resume")" "204"
expect "container running again" "$(cid_state "$CID")" "running"

# 5/6/7. stop, suspend-while-stopped (SOLUTION 36), resume-while-stopped
echo "== 5. stop / 6. suspend from stopped / 7. resume from stopped =="
expect "stop -> 204" "$(http POST "/api/sandbox/sandboxes/$SID/stop")" "204"
expect "container exited" "$(cid_state "$CID")" "exited"
expect "suspend (from stopped) -> 204" "$(http POST "/api/sandbox/sandboxes/$SID/suspend")" "204"
expect "container still exited (pause no-op)" "$(cid_state "$CID")" "exited"
expect "resume (from stopped) -> 204" "$(http POST "/api/sandbox/sandboxes/$SID/resume")" "204"
expect "container re-started" "$(cid_state "$CID")" "running"

# 8. delete
echo "== 8. delete =="
expect "delete -> 204" "$(http DELETE "/api/sandbox/sandboxes/$SID")" "204"
expect "container destroyed" "$(cid_state "$CID")" "GONE"
expect "API 404 after delete" "$(http GET "/api/sandbox/sandboxes/$SID/status")" "404"

# 9. drift: container lost on the host
echo "== 9. drift (container lost on host) =="
R=$(curl -fsS -X POST "$BASE/api/sandbox/sandboxes" \
  -H 'Content-Type: application/json' -d "{\"workspace_id\":\"$WS\",\"stack\":\"python\"}")
SID2=$(json_field "$R" id)
CID2=$(json_field "$R" container_id)
http POST "/api/sandbox/sandboxes/$SID2/start" >/dev/null
http POST "/api/sandbox/sandboxes/$SID2/suspend" >/dev/null
podman rm -f "$CID2" >/dev/null 2>&1  # simulate host reset / manual cleanup
expect "resume after container loss -> 502" \
  "$(http POST "/api/sandbox/sandboxes/$SID2/resume")" "502"
expect "API parks in error" \
  "$(json_field "$(curl -fsS "$BASE/api/sandbox/sandboxes/$SID2/status")" status)" "error"

# 10. API restart: persisted container_id still driveable (registry is empty)
echo "== 10. API restart durability =="
R=$(curl -fsS -X POST "$BASE/api/sandbox/sandboxes" \
  -H 'Content-Type: application/json' -d "{\"workspace_id\":\"$WS\",\"stack\":\"python\"}")
SID3=$(json_field "$R" id)
CID3=$(json_field "$R" container_id)
http POST "/api/sandbox/sandboxes/$SID3/start" >/dev/null
kill "$SRV_PID" 2>/dev/null; wait "$SRV_PID" 2>/dev/null
SRV_PID=""
start_server
expect "health after restart" "$(http GET /health)" "200"
expect "stop after restart -> 204" "$(http POST "/api/sandbox/sandboxes/$SID3/stop")" "204"
expect "container exited after restart-stop" "$(cid_state "$CID3")" "exited"
expect "start after restart -> 204" "$(http POST "/api/sandbox/sandboxes/$SID3/start")" "204"
expect "container running after restart" "$(cid_state "$CID3")" "running"

# cleanup our test sandboxes
http DELETE "/api/sandbox/sandboxes/$SID2" >/dev/null
http DELETE "/api/sandbox/sandboxes/$SID3" >/dev/null

echo
echo "======================================"
echo " LIVE VERIFY RESULT: $PASS passed, $FAIL failed"
echo "======================================"
[ "$FAIL" -eq 0 ] || exit 1
echo "ALL GREEN"
