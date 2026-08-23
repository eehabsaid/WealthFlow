#!/usr/bin/env bash
#
# run_e2e_tests.sh — run the Playwright/pytest UI suite (tests/ui) against a
# real, running instance of WealthFlow WITHOUT touching the production
# database.
#
# Strategy (safest to weakest, we use #1):
#   1. Never let the app process open db.sqlite3 at all during the test run.
#      We copy it to a disposable file and point Django at the COPY via the
#      WEALTHFLOW_DB_NAME env var (see wealthflow/settings.py). Any pending
#      migrations are applied to that copy, never to production.
#   2. As a paranoia backstop (in case something outside this script also
#      talks to db.sqlite3 while the suite runs, or a future edit
#      reintroduces a hard-coded path), we still snapshot db.sqlite3 before
#      starting and diff it on exit; if it changed, we restore it from the
#      snapshot automatically.
#
# Usage:
#   ./scripts/run_e2e_tests.sh
#   ALLURE_RESULTS_DIR=allure-results ./scripts/run_e2e_tests.sh
#
# Exit code is the pytest exit code (0 = all tests passed).

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PROD_DB="db.sqlite3"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_DB="db.sqlite3.bak.${TIMESTAMP}"
TEST_DB="db_e2e_test_${TIMESTAMP}.sqlite3"
SERVER_HOST="${WEALTHFLOW_E2E_HOST:-127.0.0.1}"
SERVER_PORT="${WEALTHFLOW_E2E_PORT:-8000}"
SERVER_LOG="e2e_server_${TIMESTAMP}.log"
SERVER_PID=""
ALLURE_RESULTS_DIR="${ALLURE_RESULTS_DIR:-allure-results}"
TEST_EXIT_CODE=1
# Defaults to the whole pytest suite under tests/; pass an argument to scope
# it down, e.g. ./scripts/run_e2e_tests.sh tests/ui/test_auth_ui.py
PYTEST_TARGET="${1:-tests}"

log() { echo "[e2e] $*"; }
err() { echo "[e2e][ERROR] $*" >&2; }

cleanup() {
  local exit_code=$?

  # Stop the test server, if it's still up.
  if [[ -n "${SERVER_PID}" ]] && kill -0 "${SERVER_PID}" 2>/dev/null; then
    log "Stopping test server (pid ${SERVER_PID})"
    kill "${SERVER_PID}" 2>/dev/null || true
    wait "${SERVER_PID}" 2>/dev/null || true
  fi

  # Remove the disposable test database (and any WAL/SHM sidecar files).
  if [[ -f "${TEST_DB}" ]]; then
    log "Removing disposable test database ${TEST_DB}"
    rm -f "${TEST_DB}" "${TEST_DB}-wal" "${TEST_DB}-shm"
  fi

  # Paranoia backstop: the app was never pointed at PROD_DB during the run,
  # so it should be byte-identical to the pre-run backup. If it isn't
  # (e.g. something else touched it concurrently), restore it.
  if [[ -f "${PROD_DB}" && -f "${BACKUP_DB}" ]]; then
    if ! cmp -s "${PROD_DB}" "${BACKUP_DB}"; then
      err "production database changed during the test run — restoring from backup"
      cp -f "${BACKUP_DB}" "${PROD_DB}"
    else
      log "Verified production database is untouched."
    fi
  fi

  log "Production db backup kept at: ${BACKUP_DB}"
  log "Server log kept at: ${SERVER_LOG}"

  if [[ $exit_code -ne 0 && "${TEST_EXIT_CODE}" -eq 1 ]]; then
    exit $exit_code
  fi
  exit "${TEST_EXIT_CODE}"
}
trap cleanup EXIT

if [[ ! -f "${PROD_DB}" ]]; then
  err "${PROD_DB} not found in ${ROOT_DIR}"
  exit 1
fi

log "Backing up production database -> ${BACKUP_DB}"
cp "${PROD_DB}" "${BACKUP_DB}"

log "Creating disposable test database (copy of production data) -> ${TEST_DB}"
cp "${PROD_DB}" "${TEST_DB}"

log "Applying any pending migrations to the TEST database only (production is never migrated by this script)"
WEALTHFLOW_DB_NAME="${TEST_DB}" python manage.py migrate --noinput

log "Starting Django dev server against the TEST database on ${SERVER_HOST}:${SERVER_PORT}"
WEALTHFLOW_DB_NAME="${TEST_DB}" python manage.py runserver "${SERVER_HOST}:${SERVER_PORT}" --noreload \
  > "${SERVER_LOG}" 2>&1 &
SERVER_PID=$!

log "Waiting for the server to become ready..."
READY=0
for _ in $(seq 1 30); do
  if curl -sf "http://${SERVER_HOST}:${SERVER_PORT}/accounts/login/" -o /dev/null; then
    READY=1
    break
  fi
  sleep 1
done

if [[ "${READY}" -ne 1 ]]; then
  err "Server did not become ready in time. See ${SERVER_LOG}"
  exit 1
fi
log "Server is up."

log "Running Playwright/pytest E2E suite (${PYTEST_TARGET}) against the TEST database..."
set +e
pytest "${PYTEST_TARGET}" \
  --base-url="http://${SERVER_HOST}:${SERVER_PORT}" \
  --alluredir="${ALLURE_RESULTS_DIR}"
TEST_EXIT_CODE=$?
set -e

log "Test run finished with exit code ${TEST_EXIT_CODE}. Allure results in ${ALLURE_RESULTS_DIR}/"
