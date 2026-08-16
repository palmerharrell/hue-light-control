#!/usr/bin/env bash
# Manual deploy to MINIPC. Run by hand from a local checkout when you're
# ready to ship main to production — this is not wired to CI.
#
# Requires:
#   - MINIPC_HOST set to the deploy target, e.g.:
#       export MINIPC_HOST=palmer@192.168.x.x
#   - REMOTE_DIR set to the backend source directory on MINIPC, e.g.:
#       export REMOTE_DIR=/opt/hue-light-control
#   - REMOTE_STATIC_DIR set to the nginx-served static directory, e.g.:
#       export REMOTE_STATIC_DIR=/opt/webapps/hueLightControl
#   - One-time manual setup already done on MINIPC: those directories
#     created, backend/config.yaml placed at $REMOTE_DIR/backend/config.yaml,
#     a .env placed at $REMOTE_DIR/.env with the real CORS_ORIGIN (both
#     scp'd by hand — never by this script, which only ever syncs
#     docker-compose.yml itself, not the directory it lives in), and
#     nginx.conf wired up. See docs/deploy.md.
set -euo pipefail

: "${MINIPC_HOST:?set MINIPC_HOST, e.g. palmer@192.168.x.x}"
: "${REMOTE_DIR:?set REMOTE_DIR, e.g. /opt/hue-light-control}"
: "${REMOTE_STATIC_DIR:?set REMOTE_STATIC_DIR, e.g. /opt/webapps/hueLightControl}"

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "==> Building frontend"
( cd "$repo_root/frontend" && npm run build )

echo "==> Syncing frontend build to $MINIPC_HOST:$REMOTE_STATIC_DIR"
rsync -az --delete "$repo_root/frontend/dist/" "$MINIPC_HOST:$REMOTE_STATIC_DIR/"

echo "==> Syncing backend source to $MINIPC_HOST:$REMOTE_DIR"
rsync -az --delete \
  --exclude 'config.yaml' \
  --exclude '__pycache__/' \
  --exclude '.venv/' \
  "$repo_root/backend/" "$MINIPC_HOST:$REMOTE_DIR/backend/"
rsync -az "$repo_root/docker-compose.yml" "$MINIPC_HOST:$REMOTE_DIR/docker-compose.yml"

echo "==> Rebuilding and restarting backend container"
ssh "$MINIPC_HOST" "cd $REMOTE_DIR && docker compose up -d --build"

echo "==> Done. If nginx.conf changed, restart the webapps container by hand."
