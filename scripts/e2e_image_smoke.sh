#!/usr/bin/env bash
#
# End-to-end smoke test against a *published* Bloom image.
#
# Proves the release-blocking path the unit suite cannot:
#   empty database
#     -> container boots and builds its schema
#     -> `alembic upgrade head` applies cleanly on the real image
#     -> admin can log in
#     -> a project is created (database write)
#     -> a >1 MB ReqIF import succeeds THROUGH nginx and imports requirements
#        (i.e. client_max_body_size is configured; nginx's 1 MB default would 413
#        the headline "bring your DOORS/Polarion data in" feature)
#     -> after a container restart, re-importing the same ReqIF is idempotent
#        (skipped, not re-created) — proving the imported data persisted
#     -> /api/health is liveness-only (never falsely reports database "connected")
#     -> /api/ready reports the database connected
#
# Usage:
#   scripts/e2e_image_smoke.sh <image-ref>
#
# Requires: docker, curl, python3. The published image supplies the app + alembic.
set -euo pipefail

IMAGE="${1:?usage: e2e_image_smoke.sh <image-ref>}"
PLATFORM="${E2E_PLATFORM:-linux/amd64}"
APP_PORT="${E2E_APP_PORT:-18081}"
BASE="http://127.0.0.1:${APP_PORT}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
FIXTURE="${SCRIPT_DIR}/e2e/sample.reqif"
[ -f "$FIXTURE" ] || { echo "missing ReqIF fixture: $FIXTURE" >&2; exit 1; }

SUFFIX="$$"
NET="bloom-e2e-net-${SUFFIX}"
PG="bloom-e2e-pg-${SUFFIX}"
APP="bloom-e2e-app-${SUFFIX}"

DB_USER="e2e_user"
DB_PASSWORD="e2e-strong-db-password-not-a-default"
DB_NAME="e2e_bloom"
DATABASE_URL="postgresql+asyncpg://${DB_USER}:${DB_PASSWORD}@${PG}:5432/${DB_NAME}"

ADMIN_EMAIL="e2e-admin@e2e.example.com"
ADMIN_PASSWORD="E2eAdminPassword-1234567"   # >= 16 chars, non-default

env_args() {
  printf ' -e %s' \
    "BLOOM_ENV=production" \
    "DATABASE_URL=${DATABASE_URL}" \
    "SECRET_KEY=e2e-secret-key-that-is-definitely-long-enough-0123456789" \
    "ADMIN_EMAIL=${ADMIN_EMAIL}" \
    "ADMIN_PASSWORD=${ADMIN_PASSWORD}" \
    "ADMIN_FULL_NAME=E2E Admin" \
    "AUTO_SEED_ADMIN=true" \
    "RUN_STARTUP_DATA_REPAIR=true" \
    "BLOOM_DISABLE_RATE_LIMIT=1" \
    "ENABLE_DOCS=false"
}

log()  { printf '\n\033[1;34m==>\033[0m %s\n' "$*"; }
fail() { printf '\n\033[1;31mFAIL:\033[0m %s\n' "$*" >&2; exit 1; }

cleanup() {
  local code=$?
  [ "$code" = 0 ] || { log "Dumping app logs (exit ${code})"; docker logs "$APP" 2>&1 | tail -80 || true; }
  docker rm -f "$APP" "$PG" >/dev/null 2>&1 || true
  docker network rm "$NET" >/dev/null 2>&1 || true
  rm -f "${PADDED:-}" 2>/dev/null || true
}
trap cleanup EXIT

json_field() { python3 -c 'import sys,json;print(json.load(sys.stdin)["'"$1"'"])'; }

login() {
  curl -fsS -X POST "${BASE}/api/auth/login" \
    -H 'Content-Type: application/json' \
    -d "{\"email\":\"${ADMIN_EMAIL}\",\"password\":\"${ADMIN_PASSWORD}\"}" | json_field access_token
}

wait_ready() {
  local what="$1"
  for _ in $(seq 1 60); do
    if curl -fsS "${BASE}/api/ready" >/dev/null 2>&1; then return 0; fi
    sleep 2
  done
  fail "app never became ready ${what}"
}

log "Using image: ${IMAGE}"
docker network create "$NET" >/dev/null

log "Starting an empty PostgreSQL"
docker run -d --name "$PG" --network "$NET" \
  -e "POSTGRES_USER=${DB_USER}" \
  -e "POSTGRES_PASSWORD=${DB_PASSWORD}" \
  -e "POSTGRES_DB=${DB_NAME}" \
  postgres:16 >/dev/null
for _ in $(seq 1 30); do
  docker exec "$PG" pg_isready -U "$DB_USER" -d "$DB_NAME" >/dev/null 2>&1 && break
  sleep 2
done
docker exec "$PG" pg_isready -U "$DB_USER" -d "$DB_NAME" >/dev/null 2>&1 \
  || fail "postgres never became ready"

log "Booting the application container (builds schema on an empty DB)"
# shellcheck disable=SC2046
docker run -d --name "$APP" --network "$NET" \
  -p "127.0.0.1:${APP_PORT}:8080" \
  --platform "$PLATFORM" \
  $(env_args) \
  "$IMAGE" >/dev/null
wait_ready "on first boot"

log "Applying alembic upgrade head against the published image"
# shellcheck disable=SC2046
docker run --rm --network "$NET" --platform "$PLATFORM" \
  $(env_args) \
  --entrypoint alembic "$IMAGE" upgrade head

log "/api/health must be liveness-only (never claim database \"connected\")"
health="$(curl -fsS "${BASE}/api/health")"
echo "    health = ${health}"
printf '%s' "$health" | grep -q '"connected"' \
  && fail "/api/health falsely reports the database connected"
printf '%s' "$health" | grep -q '"status":"healthy"' \
  || fail "/api/health did not report healthy"

log "/api/ready must confirm the database"
ready="$(curl -fsS "${BASE}/api/ready")"
echo "    ready = ${ready}"
printf '%s' "$ready" | grep -q '"database":"connected"' \
  || fail "/api/ready did not confirm the database"

log "Admin login"
token="$(login)"
[ -n "$token" ] || fail "login returned no access_token"

log "Creating a project (database write)"
project_id="$(curl -fsS -X POST "${BASE}/api/projects" \
  -H "Authorization: Bearer ${token}" \
  -H 'Content-Type: application/json' \
  -d '{"name":"E2E Project","prefix":"E2E"}' | json_field id)"
[ -n "$project_id" ] || fail "project creation did not return an id"
echo "    project id = ${project_id}"

log "Building a >1 MB ReqIF payload from the sample fixture"
PADDED="$(mktemp)"
python3 - "$FIXTURE" "$PADDED" <<'PY'
import sys
src, dst = sys.argv[1], sys.argv[2]
data = open(src, "rb").read()
# Pad with a large XML comment (ignored by the parser) to clear 1 MB. The unit
# contains no double hyphen, so the comment stays well-formed.
pad = b"<!-- " + (b"e2e padding data 0123456789 " * 60000) + b" -->\n"
data = data.replace(b"</REQ-IF>", pad + b"</REQ-IF>")
open(dst, "wb").write(data)
print("padded size:", len(data))
PY
[ "$(wc -c < "$PADDED")" -gt 1048576 ] || fail "padded ReqIF is not over 1 MB"

log "Importing the >1 MB ReqIF through nginx (exercises client_max_body_size)"
import_result="$(curl -fsS -X POST "${BASE}/api/projects/${project_id}/import/reqif" \
  -H "Authorization: Bearer ${token}" \
  -F "file=@${PADDED};type=application/xml;filename=e2e.reqif")"
echo "    import = ${import_result}"
imported="$(printf '%s' "$import_result" | json_field imported)"
[ "$imported" = "2" ] || fail "expected 2 imported requirements, got '${imported}'"

log "Restarting the container to prove persistence"
docker restart "$APP" >/dev/null
wait_ready "after restart"

log "Re-importing the same ReqIF must be idempotent (proves the data persisted)"
token="$(login)"
reimport="$(curl -fsS -X POST "${BASE}/api/projects/${project_id}/import/reqif" \
  -H "Authorization: Bearer ${token}" \
  -F "file=@${PADDED};type=application/xml;filename=e2e.reqif")"
echo "    reimport = ${reimport}"
reimported="$(printf '%s' "$reimport" | json_field imported)"
reskipped="$(printf '%s' "$reimport" | json_field skipped)"
[ "$reimported" = "0" ] || fail "re-import created ${reimported} duplicates; data did not persist"
[ "$reskipped" = "2" ] || fail "re-import skipped '${reskipped}', expected 2 persisted requirements"

log "PASS: Bloom published image is end-to-end healthy"
