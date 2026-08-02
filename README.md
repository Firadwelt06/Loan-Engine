# Loan Risk & Approval Intelligence Engine

An end-to-end loan default risk engine — raw applicant data in, a live, explainable risk score and portfolio dashboard out.

**[Live dashboard →](#)** *(add your Streamlit Cloud link here once deployed)*

---

## What this is

Most "loan prediction" projects stop at a Jupyter notebook with an accuracy score. This one is built as a working pipeline with four connected stages: **data validation → SQL analytics layer → explainable ML model → live interactive dashboard**, backed by a real MySQL database.

## Why it's more than a single model

Two design decisions worth calling out, because they're the difference between a toy notebook and something a lender could actually use:

- **Leakage check before modeling.** The raw data included a `grade_subgrade` field and an `interest_rate` field that turned out to be *assigned using the same risk factors the model is meant to predict* — including them would have produced a model that looks 95%+ accurate but is actually just decoding a label that already gives away the answer. Both were identified and excluded. See `model/risk_model_baseline.py` for the full reasoning.
- **Imbalance-aware evaluation.** The target is ~80/20 (paid back vs. default). Accuracy alone is meaningless here — a model that always predicts "paid back" would score 80% for free. Evaluation instead uses precision, recall, and ROC-AUC, with `class_weight='balanced'` applied during training.

## Architecture

```
Raw CSV
   │
   ▼
[ MySQL ]  ── schema + validated load ── sql/schema.sql, scripts/load_to_mysql.py
   │
   ├──▶ [ SQL Analytics Layer ] ── business-question views ── sql/business_views.sql
   │
   └──▶ [ Risk Model ] ── Logistic Regression + Random Forest ── model/risk_model_baseline.py
              │
              ▼
        [ Explainability ] ── SHAP, per-applicant "why" ── model/explainability.py
              │
              ▼
        [ Dashboard ] ── portfolio view + live scoring ── app/dashboard.py
              │
              ▼
        Deployed on Streamlit Community Cloud, backed by Aiven MySQL (free tier)
```

## Results

| Model | ROC-AUC | Notes |
|---|---|---|
| Logistic Regression (baseline) | ~0.88 | Higher recall on defaults — catches more true defaults, more false positives |
| Random Forest | ~0.88 | Higher precision — fewer false accusations, catches somewhat fewer true defaults |

*(Fill in your actual final numbers here once you've run the model against your live MySQL data.)*

The strongest legitimate predictors were **debt-to-income ratio** and **credit score** — consistent with what a human underwriter would expect, and consistent with the SQL-layer findings (see `sql/business_views.sql` → `v_default_by_credit_bucket`, `v_default_by_dti_bucket`).

## Tech stack

- **Python** — pandas, scikit-learn, SHAP
- **MySQL** — schema design, validated ETL, analytical views
- **Streamlit** — interactive dashboard with live prediction + explanation
- **Aiven** — free managed MySQL hosting for the deployed version

## Repo structure

```
loan-risk-engine/
├── data/                     # raw dataset (or a sample, if the full file is large)
├── sql/
│   ├── schema.sql            # table definition
│   └── business_views.sql    # analytical views
├── scripts/
│   └── load_to_mysql.py      # validated CSV → MySQL loader
├── model/
│   ├── risk_model_baseline.py    # trains + evaluates the risk model
│   └── explainability.py         # SHAP global + per-applicant explanations
├── app/
│   └── dashboard.py           # Streamlit dashboard (portfolio view + live scoring)
├── deployment/
│   ├── migrate_to_aiven.sh
│   └── secrets_template.toml
├── .env.example
├── .gitignore
└── requirements.txt
```

## Running it locally

1. `pip install -r requirements.txt`
2. Copy `.env.example` to `.env`, fill in your MySQL credentials
3. `mysql -u root -p < sql/schema.sql`
4. `python scripts/load_to_mysql.py`
5. `mysql -u root -p < sql/business_views.sql`
6. `python model/risk_model_baseline.py`
7. `python model/explainability.py`
8. `streamlit run app/dashboard.py`

## Security note

The database user embedded in the deployed dashboard's secrets has **read-only (`SELECT`) access** to a single database — it cannot insert, modify, or drop anything, and cannot see any other database on the server. Schema setup and data loading are done separately via a private admin connection, never exposed in the deployed app.

## What I'd build next

- Automated retraining trigger on new data (scheduled job)
- Interest-rate regression model as a second output
- A/B comparison of SMOTE vs. class-weighting for the imbalance problem
