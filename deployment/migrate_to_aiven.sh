# Migrate local MySQL data to your free Aiven MySQL instance
# This script now prints diagnostics and resolves the sql file paths
# so it works better on Windows environments (WSL/Git Bash) and CI.

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

if [ ! -d "$SQL_DIR" ]; then
      echo "ERROR: SQL directory not found at $SQL_DIR" >&2
      ls -la "$REPO_ROOT" || true
      exit 1
fi

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

echo "1) Creating schema on Aiven (you'll be prompted for password because of -p)"
mysql --host=mysql-loan-engine-adeleyebukola587-ccbd.e.aivencloud.com --port=14761 \
                  --user=avnadmin -p --ssl-mode=REQUIRED < "$SQL_DIR/schema.sql"

echo "2) Creating business views on Aiven"
mysql --host=mysql-loan-engine-adeleyebukola587-ccbd.e.aivencloud.com --port=14761 \
                  --user=avnadmin -p --ssl-mode=REQUIRED < "$SQL_DIR/business_views.sql"

echo "--- migrate_to_aiven.sh finished ---"

# 3. Re-run your existing loader against Aiven instead of localhost.
#    Just update the .env values (see .env.example in repo root) and run:
#    python load_to_mysql.py
