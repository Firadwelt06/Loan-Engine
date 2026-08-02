"""
Loan Risk Engine — Baseline Risk Model
----------------------------------------
Pulls cleaned data straight from MySQL (loan_engine.loans), trains two
classifiers, and evaluates them properly for an imbalanced target.

Deliberately DROPS grade_subgrade and interest_rate — see leakage check
from the data-audit stage. Both are assigned using the same risk factors
we're trying to predict, so including them would inflate accuracy
artificially and produce a model that's useless in a real underwriting
scenario (grade doesn't exist yet at prediction time).

1. Make sure the MySQL loading stage is done (loans table populated).
2. Copy your existing .env (same one from the load stage) into this folder,
   or point ENV_PATH below at it.
3. pip install -r requirements.txt
4. python risk_model_baseline.py
"""

import os
import joblib
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    classification_report,
    roc_auc_score,
    confusion_matrix,
)

load_dotenv()

DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", 3306))
DB_NAME = os.getenv("DB_NAME", "loan_engine")

if not DB_PASSWORD:
    raise ValueError("DB_PASSWORD not set — copy your .env into this folder.")

# Columns excluded from the model and why
LEAKY_COLUMNS = ["grade_subgrade", "interest_rate"]  # set using the target's own risk factors
ID_COLUMNS = ["loan_id"]                              # not predictive, just a row identifier
TARGET = "loan_paid_back"
MODEL_DIR = Path(__file__).parent  # always save/load alongside this script


def load_data_from_mysql() -> pd.DataFrame:
    conn_str = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    engine = create_engine(conn_str)
    df = pd.read_sql("SELECT * FROM loans", con=engine)
    print(f"Pulled {len(df)} rows from MySQL.")
    return df


def prepare_features(df: pd.DataFrame):
    df = df.drop(columns=LEAKY_COLUMNS + ID_COLUMNS, errors="ignore")

    y = df[TARGET]
    X = df.drop(columns=[TARGET])

    # One-hot encode categoricals (gender, marital_status, education_level,
    # employment_status, loan_purpose)
    X = pd.get_dummies(X, drop_first=True)

    return X, y


def evaluate(name, model, X_test, y_test):
    preds = model.predict(X_test)
    probs = model.predict_proba(X_test)[:, 1]

    print(f"\n=== {name} ===")
    print(classification_report(y_test, preds, target_names=["Default", "Paid Back"]))
    print(f"ROC-AUC: {roc_auc_score(y_test, probs):.3f}")
    print("Confusion matrix (rows=actual, cols=predicted):")
    print(confusion_matrix(y_test, preds))


def main():
    df = load_data_from_mysql()
    X, y = prepare_features(df)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    print(f"Train: {len(X_train)} rows | Test: {len(X_test)} rows")
    print(f"Train class balance:\n{y_train.value_counts(normalize=True)}")

    # Logistic Regression needs scaled features; tree models don't.
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # --- Model 1: Logistic Regression baseline ---
    log_reg = LogisticRegression(
        class_weight="balanced",  # <-- imbalance handling, swap for SMOTE here if comparing
        max_iter=1000,
        random_state=42,
    )
    log_reg.fit(X_train_scaled, y_train)
    evaluate("Logistic Regression (baseline)", log_reg, X_test_scaled, y_test)

    # --- Model 2: Random Forest ---
    rf = RandomForestClassifier(
        n_estimators=300,
        class_weight="balanced",
        max_depth=10,
        random_state=42,
        n_jobs=-1,
    )
    rf.fit(X_train, y_train)  # trees don't need scaling
    evaluate("Random Forest", rf, X_test, y_test)

    # Feature importance from the Random Forest — sets up the SHAP step later
    importances = (
        pd.Series(rf.feature_importances_, index=X.columns)
        .sort_values(ascending=False)
        .head(10)
    )
    print("\n=== Top 10 features (Random Forest) ===")
    print(importances)

    # Save both models + the scaler + the feature column order for reuse
    joblib.dump(log_reg, MODEL_DIR / "log_reg_model.joblib")
    joblib.dump(rf, MODEL_DIR / "rf_model.joblib")
    joblib.dump(scaler, MODEL_DIR / "scaler.joblib")
    joblib.dump(list(X.columns), MODEL_DIR / "feature_columns.joblib")
    print(f"\nSaved model files in: {MODEL_DIR}")


if __name__ == "__main__":
    main()
