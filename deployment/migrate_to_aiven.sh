#!/usr/bin/env sh

set -eu

echo "--- migrate_to_aiven.sh starting ---"
echo "PWD: $(pwd)"
echo "Shell: ${SHELL:-unknown}"
echo "Args: $*"

# Resolve paths relative to the script location
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SQL_DIR="$REPO_ROOT/sql"
echo "Script dir: $SCRIPT_DIR"
echo "Repository root: $REPO_ROOT"
echo "SQL dir: $SQL_DIR"

# Verify SQL directory existence
if [ ! -d "$SQL_DIR" ]; then
      echo "ERROR: SQL directory not found at $SQL_DIR" >&2
      ls -la "$REPO_ROOT" || true
      exit 1
fi

# Verify required SQL files exist
if [ ! -f "$SQL_DIR/schema.sql" ]; then
      echo "ERROR: schema.sql not found in $SQL_DIR" >&2
      ls -la "$SQL_DIR" || true
      exit 1
fi

if [ ! -f "$SQL_DIR/business_views.sql" ]; then
      echo "ERROR: business_views.sql not found in $SQL_DIR" >&2
      ls -la "$SQL_DIR" || true
      exit 1
fi

# Check mysql client availability
if ! command -v mysql >/dev/null 2>&1; then
      echo "ERROR: 'mysql' client not found in PATH." >&2
      echo "On Windows install the MySQL client or run this script from WSL/Git Bash." >&2
      exit 1
fi

echo "Found mysql: $(mysql --version 2>/dev/null || true)"

# Load DB settings from .env in the repo root
ENV_FILE="$REPO_ROOT/.env"
if [ -f "$ENV_FILE" ]; then
    echo "Loading environment from $ENV_FILE"
    set -a
    . "$ENV_FILE"
    set +a
else
    echo "ERROR: .env file not found at $ENV_FILE" >&2
    exit 1
fi

MYSQL_HOST="${DB_HOST:-}"
MYSQL_PORT="${DB_PORT:-}"
MYSQL_USER="${DB_USER:-avnadmin}"
MYSQL_DB="${DB_NAME:-defaultdb}"

if [ -z "$MYSQL_HOST" ] || [ -z "$MYSQL_PORT" ] || [ -z "$DB_PASSWORD" ]; then
    echo "ERROR: DB_HOST, DB_PORT, and DB_PASSWORD must be set in $ENV_FILE" >&2
    exit 1
fi

echo "Using MySQL host=$MYSQL_HOST port=$MYSQL_PORT db=$MYSQL_DB"

echo "1) Creating schema on Aiven (you'll be prompted for password because of -p)"
mysql --host="$MYSQL_HOST" --port="$MYSQL_PORT" \
      --user="$MYSQL_USER" -p --ssl-mode=REQUIRED "$MYSQL_DB" < "$SQL_DIR/schema.sql"

echo "2) Creating business views on Aiven"
mysql --host="$MYSQL_HOST" --port="$MYSQL_PORT" \
      --user="$MYSQL_USER" -p --ssl-mode=REQUIRED "$MYSQL_DB" < "$SQL_DIR/business_views.sql"

echo "--- migrate_to_aiven.sh finished ---"
