"""
Loan Risk Engine — Dashboard
--------------------------------
Two tabs:
  1. Portfolio Overview — pulls the SQL views built earlier, shows
     repayment rate by purpose, credit bucket, DTI bucket, employment.
  2. Live Prediction — enter one applicant's details, get a risk score
     plus the top factors driving that specific prediction (SHAP).

Requires (already produced by earlier stages, same folder):
  - rf_model.joblib, feature_columns.joblib   (from risk_model_baseline.py)
  - .env with your MySQL credentials           (from the MySQL stage)
  - business_views.sql already run in MySQL    (from the MySQL stage)

Run: streamlit run dashboard.py
"""

import os
import joblib
import shap
import pandas as pd
import streamlit as st
from pathlib import Path
from urllib.parse import quote_plus
from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv()

MODEL_DIR = Path(__file__).parent.parent / "model"  # ../model/ from app/dashboard.py


def get_config(key: str, default=None):
    """Check st.secrets first (Streamlit Cloud), fall back to .env (local)."""
    try:
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    return os.getenv(key, default)


DB_USER = get_config("DB_USER", "root")
DB_PASSWORD = get_config("DB_PASSWORD")
DB_HOST = get_config("DB_HOST", "localhost")
DB_PORT = int(get_config("DB_PORT", 3306))
DB_NAME = get_config("DB_NAME", "loan_engine")
DB_SSL = get_config("DB_SSL", "false").lower() == "true"  # set true for Aiven

st.set_page_config(page_title="Loan Risk Engine", layout="wide")


@st.cache_resource
@st.cache_resource
def get_engine():
    # Ensure variables are treated as strings before quoting
    user = str(DB_USER) if DB_USER else ""
    pwd = str(DB_PASSWORD) if DB_PASSWORD else ""
    
    conn_str = (
        f"mysql+pymysql://{quote_plus(user)}:{quote_plus(pwd)}"
        f"@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )
    
    # Auto-enable SSL for Aiven cloud hosts or if DB_SSL is explicitly set to true
    connect_args = {}
    if DB_SSL or (DB_HOST and "aivencloud.com" in str(DB_HOST)):
        connect_args["ssl"] = {"ssl_mode": "REQUIRED"}
        
    return create_engine(conn_str, connect_args=connect_args)


@st.cache_resource
def load_model_assets():
    rf = joblib.load(MODEL_DIR / "rf_model.joblib")
    feature_columns = joblib.load(MODEL_DIR / "feature_columns.joblib")
    explainer = shap.TreeExplainer(rf)
    return rf, feature_columns, explainer


@st.cache_data(ttl=300)
def load_view(view_name: str) -> pd.DataFrame:
    engine = get_engine()
    return pd.read_sql(f"SELECT * FROM {view_name}", con=engine)


def prepare_single_applicant(raw: dict, feature_columns: list) -> pd.DataFrame:
    """Turn a form submission into the exact one-hot column layout the model expects."""
    df = pd.DataFrame([raw])
    df = pd.get_dummies(df)
    df = df.reindex(columns=feature_columns, fill_value=0)
    return df


def get_prediction_and_explanation(raw: dict, rf, feature_columns, explainer, top_n=5):
    X_row = prepare_single_applicant(raw, feature_columns)
    prob_paid_back = rf.predict_proba(X_row)[0][1]

    shap_values = explainer.shap_values(X_row)
    if isinstance(shap_values, list):
        shap_row = shap_values[1][0]
    elif shap_values.ndim == 3:
        shap_row = shap_values[0, :, 1]
    else:
        shap_row = shap_values[0]

    contributions = pd.Series(shap_row, index=X_row.columns).sort_values(
        key=abs, ascending=False
    )
    return prob_paid_back, contributions.head(top_n)


# ============================================================
# UI
# ============================================================

st.title("Loan Risk Engine")

tab1, tab2 = st.tabs(["Portfolio Overview", "Live Prediction"])

# ---------------- Tab 1: Portfolio Overview ----------------
with tab1:
    st.subheader("Repayment rate across the portfolio")

    try:
        col1, col2 = st.columns(2)

        with col1:
            df_purpose = load_view("v_default_by_purpose")
            st.markdown("**By loan purpose**")
            st.bar_chart(df_purpose.set_index("loan_purpose")["repayment_rate_pct"])

            df_credit = load_view("v_default_by_credit_bucket")
            st.markdown("**By credit score bucket**")
            st.bar_chart(df_credit.set_index("credit_bucket")["repayment_rate_pct"])

        with col2:
            df_employment = load_view("v_default_by_employment")
            st.markdown("**By employment status**")
            st.bar_chart(df_employment.set_index("employment_status")["repayment_rate_pct"])

            df_dti = load_view("v_default_by_dti_bucket")
            st.markdown("**By debt-to-income bucket**")
            st.bar_chart(df_dti.set_index("dti_bucket")["repayment_rate_pct"])

        st.markdown("**Raw table — by loan purpose**")
        st.dataframe(df_purpose, use_container_width=True)

    except Exception as e:
        st.error(
            "Couldn't load from MySQL. Check your .env is in this folder and "
            "business_views.sql has been run. Error: " + str(e)
        )

# ---------------- Tab 2: Live Prediction ----------------
with tab2:
    st.subheader("Score a new applicant")

    try:
        rf, feature_columns, explainer = load_model_assets()

        with st.form("applicant_form"):
            c1, c2, c3 = st.columns(3)

            with c1:
                age = st.number_input("Age", 18, 100, 35)
                gender = st.selectbox("Gender", ["Male", "Female"])
                marital_status = st.selectbox("Marital Status", ["Single", "Married", "Divorced"])
                education_level = st.selectbox(
                    "Education", ["High School", "Bachelor's", "Master's", "PhD"]
                )

            with c2:
                annual_income = st.number_input("Annual Income", 0.0, 1_000_000.0, 30000.0)
                monthly_income = st.number_input("Monthly Income", 0.0, 100_000.0, 2500.0)
                employment_status = st.selectbox(
                    "Employment Status", ["Employed", "Self-employed", "Unemployed", "Retired", "Student"]
                )
                debt_to_income_ratio = st.slider("Debt-to-Income Ratio", 0.0, 1.0, 0.2)

            with c3:
                credit_score = st.slider("Credit Score", 300, 850, 650)
                loan_amount = st.number_input("Loan Amount", 0.0, 100_000.0, 10000.0)
                loan_purpose = st.selectbox(
                    "Loan Purpose",
                    ["Car", "Debt consolidation", "Business", "Home", "Education", "Medical", "Other"],
                )
                loan_term = st.selectbox("Loan Term (months)", [12, 24, 36, 48, 60])

            c4, c5, c6 = st.columns(3)
            with c4:
                installment = st.number_input("Installment", 0.0, 10000.0, 300.0)
            with c5:
                num_of_open_accounts = st.number_input("Open Accounts", 0, 50, 5)
                total_credit_limit = st.number_input("Total Credit Limit", 0.0, 500000.0, 20000.0)
            with c6:
                current_balance = st.number_input("Current Balance", 0.0, 500000.0, 8000.0)
                delinquency_history = st.number_input("Delinquency History (count)", 0, 20, 0)
                public_records = st.number_input("Public Records", 0, 10, 0)
                num_of_delinquencies = st.number_input("Number of Delinquencies", 0, 20, 0)

            submitted = st.form_submit_button("Score this applicant")

        if submitted:
            raw = dict(
                age=age, gender=gender, marital_status=marital_status,
                education_level=education_level, annual_income=annual_income,
                monthly_income=monthly_income, employment_status=employment_status,
                debt_to_income_ratio=debt_to_income_ratio, credit_score=credit_score,
                loan_amount=loan_amount, loan_purpose=loan_purpose, loan_term=loan_term,
                installment=installment, num_of_open_accounts=num_of_open_accounts,
                total_credit_limit=total_credit_limit, current_balance=current_balance,
                delinquency_history=delinquency_history, public_records=public_records,
                num_of_delinquencies=num_of_delinquencies,
            )

            prob, top_factors = get_prediction_and_explanation(
                raw, rf, feature_columns, explainer
            )

            st.metric("Predicted repayment probability", f"{prob:.1%}")
            if prob >= 0.7:
                st.success("Low risk")
            elif prob >= 0.5:
                st.warning("Moderate risk")
            else:
                st.error("High risk")

            st.markdown("**Top factors behind this prediction:**")
            for feature, value in top_factors.items():
                direction = "⬆️ helps repayment" if value > 0 else "⬇️ raises default risk"
                st.write(f"- `{feature}` — {direction} (impact: {value:+.3f})")

    except FileNotFoundError:
        st.error(
            "Model files not found. Run risk_model_baseline.py first — "
            "this tab needs rf_model.joblib and feature_columns.joblib in this folder."
        )