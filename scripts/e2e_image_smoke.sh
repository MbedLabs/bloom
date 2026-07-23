#!/usr/bin/env bash
#
# End-to-end smoke test against a *published* Bloom image.
#
# Proves the release-blocking path the unit suite cannot, using a real named
# volume and a full container teardown/recreate (not just a restart):
#   empty named-volume PostgreSQL
#     -> `alembic upgrade head` builds the schema on the real image (before the
#        app boots; RUN_STARTUP_DATA_REPAIR=false, so no create_all rescue)
#     -> `alembic current` is at head (migrations are complete on their own)
#     -> app boots; admin can log in
#     -> a project is created (database write)
#     -> a >1 MB ReqIF import succeeds THROUGH nginx (client_max_body_size)
#     -> BOTH containers are removed and recreated with the SAME named volume
#     -> the project and imported requirements still exist, and re-importing the
#        same ReqIF is idempotent (skipped, not duplicated)
#     -> /api/health is liveness-only; /api/ready confirms the database
#
# Usage:
#   scripts/e2e_image_smoke.sh <image-ref>
#
# Requires: docker, curl, python3. The published image supplies the app + alembic.
set -euo pipefail

IMAGE="${1:?usage: e2e_image_smoke.sh <image-ref>}"
PLATFORM="${E2E_PLATFORM:-linux/amd64}"
APP_PORT="${E2E_APP_PORT:-}"
BASE=""

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
FIXTURE="${SCRIPT_DIR}/e2e/sample.reqif"
[ -f "$FIXTURE" ] || { echo "missing ReqIF fixture: $FIXTURE" >&2; exit 1; }

SUFFIX="$$"
NET="bloom-e2e-net-${SUFFIX}"
PG="bloom-e2e-pg-${SUFFIX}"
APP="bloom-e2e-app-${SUFFIX}"
PGVOL="bloom-e2e-pgdata-${SUFFIX}"

DB_USER="e2e_user"
DB_PASSWORD="e2e-strong-db-password-not-a-default"
DB_NAME="e2e_bloom"
DATABASE_URL="postgresql+asyncpg://${DB_USER}:${DB_PASSWORD}@${PG}:5432/${DB_NAME}"

ADMIN_EMAIL="e2e-admin@e2e.example.com"
ADMIN_PASSWORD="E2eAdminPassword-1234567"   # >= 16 chars, non-default

ENV_ARGS=(
  -e "BLOOM_ENV=production"
  -e "DATABASE_URL=${DATABASE_URL}"
  -e "SECRET_KEY=e2e-secret-key-that-is-definitely-long-enough-0123456789"
  -e "ADMIN_EMAIL=${ADMIN_EMAIL}"
  -e "ADMIN_PASSWORD=${ADMIN_PASSWORD}"
  -e "ADMIN_FULL_NAME=E2E Admin"
  -e "AUTO_SEED_ADMIN=true"
  # Production-path migration test: the app must NOT build or repair the schema.
  # alembic (run explicitly below, before the app boots) is the only schema
  # builder, so a missing/incomplete migration fails instead of being rescued by
  # create_all().
  -e "RUN_STARTUP_DATA_REPAIR=false"
  -e "BLOOM_DISABLE_RATE_LIMIT=1"
  -e "ENABLE_DOCS=false"
)

log()  { printf '\n\033[1;34m==>\033[0m %s\n' "$*"; }
fail() { printf '\n\033[1;31mFAIL:\033[0m %s\n' "$*" >&2; exit 1; }

cleanup() {
  local code=$?
  [ "$code" = 0 ] || { log "Dumping app logs (exit ${code})"; docker logs "$APP" 2>&1 | tail -80 || true; }
  docker rm -f "$APP" "$PG" >/dev/null 2>&1 || true
  docker volume rm "$PGVOL" >/dev/null 2>&1 || true
  docker network rm "$NET" >/dev/null 2>&1 || true
  rm -f "${PADDED:-}" 2>/dev/null || true
}
trap cleanup EXIT

json_field() { python3 -c 'import sys,json;print(json.load(sys.stdin)["'"$1"'"])'; }

refresh_base() {
  local port_binding
  port_binding="$(docker port "$APP" 8080/tcp | head -n 1)"
  APP_PORT="${port_binding##*:}"
  [ -n "$APP_PORT" ] || fail "Docker did not allocate an application port"
  BASE="http://127.0.0.1:${APP_PORT}"
}

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

start_pg() {
  # Reuses the named PGVOL so data survives a container recreate.
  docker run -d --name "$PG" --network "$NET" \
    -v "${PGVOL}:/var/lib/postgresql/data" \
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
}

start_app() {
  local publish="127.0.0.1::8080"
  if [ -n "$APP_PORT" ]; then publish="127.0.0.1:${APP_PORT}:8080"; fi
  docker run -d --name "$APP" --network "$NET" \
    -p "$publish" \
    --platform "$PLATFORM" \
    "${ENV_ARGS[@]}" \
    "$IMAGE" >/dev/null
  refresh_base
}

import_reqif() {
  curl -fsS -X POST "${BASE}/api/projects/${project_id}/import/reqif" \
    -H "Authorization: Bearer ${1}" \
    -F "file=@${PADDED};type=application/xml;filename=e2e.reqif"
}

log "Using image: ${IMAGE}"
docker network create "$NET" >/dev/null

log "Starting an empty named-volume PostgreSQL"
start_pg

log "Applying alembic upgrade head against the published image (before the app boots)"
docker run --rm --network "$NET" --platform "$PLATFORM" \
  "${ENV_ARGS[@]}" \
  --entrypoint alembic "$IMAGE" upgrade head

log "Verifying the database is at alembic head (migrations are complete on their own)"
current="$(docker run --rm --network "$NET" --platform "$PLATFORM" \
  "${ENV_ARGS[@]}" \
  --entrypoint alembic "$IMAGE" current 2>&1)"
echo "    ${current}"
printf '%s' "$current" | grep -q '(head)' \
  || fail "database is not at alembic head after upgrade (migration incomplete)"

log "Booting the application container (schema already built by alembic; no create_all)"
start_app
wait_ready "on first boot"

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
  -d '{"name":"E2E Project","prefix":"EET"}' | json_field id)"
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
import_result="$(import_reqif "$token")"
echo "    import = ${import_result}"
imported="$(printf '%s' "$import_result" | json_field imported)"
[ "$imported" = "2" ] || fail "expected 2 imported requirements, got '${imported}'"

log "Removing BOTH containers and recreating them with the SAME named volume"
docker rm -f "$APP" "$PG" >/dev/null
start_pg
# No alembic re-run: the schema and data live in the persistent PGVOL.
start_app
wait_ready "after container recreation"

log "The project and its imported requirements must still exist"
token="$(login)"
[ -n "$token" ] || fail "admin login failed after recreation (database did not persist)"
project_json="$(curl -fsS "${BASE}/api/projects/${project_id}" -H "Authorization: Bearer ${token}")"
echo "    project = ${project_json}"
req_count="$(printf '%s' "$project_json" | json_field requirement_count)"
[ "$req_count" = "2" ] \
  || fail "project/requirements did not persist across recreation (requirement_count=${req_count})"

log "Re-importing the same ReqIF must be idempotent (proves the data persisted)"
reimport="$(import_reqif "$token")"
echo "    reimport = ${reimport}"
reimported="$(printf '%s' "$reimport" | json_field imported)"
reskipped="$(printf '%s' "$reimport" | json_field skipped)"
[ "$reimported" = "0" ] || fail "re-import created ${reimported} duplicates; data did not persist"
[ "$reskipped" = "2" ] || fail "re-import skipped '${reskipped}', expected 2 persisted requirements"

log "PASS: Bloom published image survives full container recreation with a named volume"
