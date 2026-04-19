#!/bin/bash
# ./dev.sh up          # Start everything (build + migrate)
# ./dev.sh rebuild     # Rebuild backend after code/.env changes
# ./dev.sh migrate     # Run Alembic migrations
# ./dev.sh logs        # Tail backend logs
# ./dev.sh test        # Run pytest
# ./dev.sh psql        # Open DB shell
# ./dev.sh reset-db    # Wipe + recreate DB
# ./dev.sh curl GET /api/companies
# ./dev.sh down        # Stop all

set -euo pipefail

COMPOSE_FILE="docker-compose.dev.yml"
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"

cd "$PROJECT_DIR"

case "${1:-help}" in
  up)
    echo ">> Starting dev stack..."
    docker compose -f "$COMPOSE_FILE" up -d --build
    echo ">> Running migrations..."
    docker compose -f "$COMPOSE_FILE" exec backend alembic upgrade head 2>/dev/null || true
    echo ">> Backend: http://localhost:8000  |  DB: localhost:5435"
    ;;

  down)
    echo ">> Stopping dev stack..."
    docker compose -f "$COMPOSE_FILE" down
    ;;

  rebuild)
    echo ">> Rebuilding backend container..."
    docker compose -f "$COMPOSE_FILE" up -d --build backend
    docker compose -f "$COMPOSE_FILE" exec backend alembic upgrade head 2>/dev/null || true
    ;;

  migrate)
    echo ">> Running migrations..."
    docker compose -f "$COMPOSE_FILE" exec backend alembic upgrade head
    ;;

  logs)
    docker compose -f "$COMPOSE_FILE" logs -f --tail=50 "${2:-backend}"
    ;;

  test)
    docker compose -f "$COMPOSE_FILE" exec backend python -m pytest tests/ -v "${2:-}"
    ;;

  psql)
    docker compose -f "$COMPOSE_FILE" exec db psql -U wfm -d wfmintel
    ;;

  reset-db)
    echo ">> Resetting database..."
    docker compose -f "$COMPOSE_FILE" down -v
    docker compose -f "$COMPOSE_FILE" up -d
    echo ">> Waiting for DB..."
    sleep 3
    docker compose -f "$COMPOSE_FILE" exec backend alembic upgrade head
    echo ">> Done."
    ;;

  curl)
    AUTH="${AUTH_ADMIN:-admin:admin}"
    shift
    METHOD="${1:-GET}"
    PATH_]="${2:-/api/health}"
    DATA="${3:-}"
    if [ "$METHOD" = "GET" ]; then
      curl -s -u "$AUTH" "http://localhost:8000${PATH_]}" | python3 -m json.tool 2>/dev/null || curl -s -u "$AUTH" "http://localhost:8000${PATH_]}"
    else
      curl -s -u "$AUTH" -X "$METHOD" -H "Content-Type: application/json" "http://localhost:8000${PATH_]}" -d "$DATA" | python3 -m json.tool 2>/dev/null || curl -s -u "$AUTH" -X "$METHOD" -H "Content-Type: application/json" "http://localhost:8000${PATH_]}" -d "$DATA"
    fi
    ;;

  *)
    echo "Usage: $0 {up|down|rebuild|migrate|logs|test|psql|reset-db|curl}"
    echo ""
    echo "  up          Start all containers (build + migrate)"
    echo "  down        Stop and remove containers"
    echo "  rebuild     Rebuild backend only (pick up code/.env changes)"
    echo "  migrate     Run Alembic migrations"
    echo "  logs [svc]  Tail logs (default: backend)"
    echo "  test [args]  Run pytest inside backend container"
    echo "  psql        Open PostgreSQL shell"
    echo "  reset-db    Drop all data, recreate DB + migrate"
    echo "  curl        Quick API call: $0 curl [METHOD] [PATH] [DATA]"
    echo "              Example: $0 curl POST /api/companies '{\"name\":\"X\",...}'"
    ;;
esac