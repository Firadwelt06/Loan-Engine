"""
Loan Risk Engine — Load raw CSV into MySQL
--------------------------------------------
1. Run schema.sql first (creates the database + table).
2. Copy .env.example to .env and fill in your MySQL credentials.
3. Run: python load_to_mysql.py
"""

import os
import pandas as pd
from urllib.parse import quote_plus
from sqlalchemy import create_engine, inspect
from dotenv import load_dotenv

load_dotenv()  # reads .env in the same folder

DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", 3306))
DB_NAME = os.getenv("DB_NAME", "loan_engine")
CSV_PATH = os.getenv("CSV_PATH", "loan_dataset_20000.csv")

if not DB_PASSWORD:
    raise ValueError(
        "DB_PASSWORD not set. Copy .env.example to .env and fill it in."
    )

def main():
    print("Reading CSV...")
    df = pd.read_csv(CSV_PATH)
    print(f"Loaded {len(df)} rows, {len(df.columns)} columns from CSV.")

    # Basic sanity check before loading — fail loudly, not silently
    expected_cols = {
        "age", "gender", "marital_status", "education_level", "annual_income",
        "monthly_income", "employment_status", "debt_to_income_ratio",
        "credit_score", "loan_amount", "loan_purpose", "interest_rate",
        "loan_term", "installment", "grade_subgrade", "num_of_open_accounts",
        "total_credit_limit", "current_balance", "delinquency_history",
        "public_records", "num_of_delinquencies", "loan_paid_back",
    }
    missing = expected_cols - set(df.columns)
    if missing:
        raise ValueError(f"CSV is missing expected columns: {missing}")

    conn_str = (
        f"mysql+pymysql://{quote_plus(DB_USER)}:{quote_plus(DB_PASSWORD)}"
        f"@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )
    engine = create_engine(conn_str)

    # Fail with a clear message if schema.sql wasn't run yet — otherwise
    # pandas will silently try to auto-create a schema-less 'loans' table,
    # which breaks on any server that requires primary keys.
    inspector = inspect(engine)
    if "loans" not in inspector.get_table_names():
        raise RuntimeError(
            "Table 'loans' does not exist in the database yet.\n"
            "Run sql/schema.sql against this database first, e.g.:\n"
            "    mysql -u <user> -p < sql/schema.sql\n"
            "Then re-run this script."
        )

    print("Loading into MySQL table 'loans'...")
    df.to_sql(
        name="loans",
        con=engine,
        if_exists="append",   # table already created by schema.sql
        index=False,
        chunksize=2000,       # batch inserts, avoids one giant transaction
        method="multi",
    )

    # Verify row count landed correctly
    with engine.connect() as conn:
        result = conn.exec_driver_sql("SELECT COUNT(*) FROM loans")
        count = result.scalar()
    print(f"Done. {count} rows now in loan_engine.loans.")

if __name__ == "__main__":
    main()