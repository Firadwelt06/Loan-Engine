"""
Run the SQL schema file against the configured MySQL server using SQLAlchemy.
This avoids requiring the `mysql` client on Windows.

Usage:
    python scripts/run_schema.py

It reads DB_* values from the repository .env (same as load_to_mysql.py).
"""
import os
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()

DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", 3306))
DB_NAME = os.getenv("DB_NAME", "loan_engine")
SQL_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "sql", "schema.sql")

if not DB_PASSWORD:
    raise ValueError("DB_PASSWORD not set in environment/.env")

conn_str = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(conn_str)

print(f"Running schema file: {SQL_FILE}")
with open(SQL_FILE, "r", encoding="utf-8") as f:
    sql = f.read()

# Naive split on ';' — adequate for this simple schema file.
statements = [s.strip() for s in sql.split(";") if s.strip()]

with engine.connect() as conn:
    for stmt in statements:
        # skip SQL comments
        sstr = stmt.lstrip()
        if sstr.startswith("--") or sstr.startswith("/*"):
            continue
        try:
            print(f"Executing: {sstr.splitlines()[0][:120]}...")
            conn.exec_driver_sql(sstr)
        except Exception as e:
            print(f"Warning: statement failed: {e}")

print("Schema run complete. Verify the 'loans' table exists or re-run load_to_mysql.py")
