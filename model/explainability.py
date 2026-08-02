"""
Loan Risk Engine — Explainability (SHAP)
-------------------------------------------
Turns the Random Forest's predictions into "here's why" instead of just
a risk score. Two outputs:

  1. Global summary plot — which features matter most across all applicants
  2. Per-applicant explanation — for one specific loan, what pushed the
     prediction up or down (this is what the dashboard will call live)

Requires risk_model_baseline.py to have been run first (needs rf_model.joblib,
feature_columns.joblib, and a live MySQL connection for fresh data).

Run: python explainability.py
"""

import os
import joblib
import shap
import matplotlib.pyplot as plt
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv()

MODEL_DIR = Path(__file__).parent  # rf_model.joblib etc. live alongside this script

DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", 3306))
DB_NAME = os.getenv("DB_NAME", "loan_engine")

LEAKY_COLUMNS = ["grade_subgrade", "interest_rate"]
ID_COLUMNS = ["loan_id"]
TARGET = "loan_paid_back"


def load_data_from_mysql() -> pd.DataFrame:
    conn_str = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    engine = create_engine(conn_str)
    return pd.read_sql("SELECT * FROM loans", con=engine)


def prepare_features(df, feature_columns):
    df = df.drop(columns=LEAKY_COLUMNS + ID_COLUMNS + [TARGET], errors="ignore")
    df = pd.get_dummies(df, drop_first=True)
    # Align to the exact columns/order the model was trained on —
    # handles any category that didn't appear in this particular sample
    df = df.reindex(columns=feature_columns, fill_value=0)
    return df


def explain_applicant(row_index, X, explainer, shap_values, top_n=5):
    """
    Print the top N factors driving the prediction for one applicant,
    in plain language. This is the function the dashboard will reuse.
    """
    row_shap = shap_values[row_index]
    contributions = pd.Series(row_shap, index=X.columns).sort_values(
        key=abs, ascending=False
    )

    print(f"\n--- Applicant #{row_index} — top {top_n} factors ---")
    for feature, value in contributions.head(top_n).items():
        direction = "increases repayment likelihood" if value > 0 else "increases default risk"
        print(f"  {feature:<35} {direction}  (impact: {value:+.3f})")


def main():
    rf = joblib.load(MODEL_DIR / "rf_model.joblib")
    feature_columns = joblib.load(MODEL_DIR / "feature_columns.joblib")

    df = load_data_from_mysql()
    X = prepare_features(df, feature_columns)

    # SHAP on a sample for speed — 1000 rows is plenty for a stable global picture
    sample = X.sample(n=min(1000, len(X)), random_state=42)

    print("Computing SHAP values (this can take a minute on the full set)...")
    explainer = shap.TreeExplainer(rf)
    shap_values = explainer.shap_values(sample)

    # shap_values shape depends on sklearn/shap version — normalize to the
    # "positive class" (loan_paid_back = 1) array
    if isinstance(shap_values, list):
        shap_values_pos = shap_values[1]
    elif shap_values.ndim == 3:
        shap_values_pos = shap_values[:, :, 1]
    else:
        shap_values_pos = shap_values

    # --- 1. Global summary plot ---
    plt.figure()
    shap.summary_plot(shap_values_pos, sample, show=False)
    plt.tight_layout()
    plt.savefig(MODEL_DIR / "shap_global_summary.png", dpi=150)
    plt.close()
    print(f"Saved: {MODEL_DIR / 'shap_global_summary.png'}")

    # --- 2. Per-applicant explanations, 3 examples ---
    sample_reset = sample.reset_index(drop=True)
    for i in [0, 1, 2]:
        explain_applicant(i, sample_reset, explainer, shap_values_pos)

    print("\nDone. Use explain_applicant() the same way inside the dashboard")
    print("to show a live 'why' breakdown for any applicant a user enters.")


if __name__ == "__main__":
    main()
