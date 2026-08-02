-- ============================================
-- Loan Risk Engine — Business Question Views
-- Run this AFTER data is loaded into loan_engine.loans
-- ============================================

USE loan_engine;

-- 1. Default rate by loan purpose
CREATE OR REPLACE VIEW v_default_by_purpose AS
SELECT
    loan_purpose,
    COUNT(*)                              AS total_loans,
    SUM(loan_paid_back)                   AS paid_back,
    ROUND(AVG(loan_paid_back) * 100, 2)   AS repayment_rate_pct
FROM loans
GROUP BY loan_purpose
ORDER BY repayment_rate_pct ASC;

-- 2. Default rate by grade (letter, collapsed from subgrade)
CREATE OR REPLACE VIEW v_default_by_grade AS
SELECT
    LEFT(grade_subgrade, 1)               AS grade_letter,
    COUNT(*)                              AS total_loans,
    ROUND(AVG(loan_paid_back) * 100, 2)   AS repayment_rate_pct,
    ROUND(AVG(interest_rate), 2)          AS avg_interest_rate
FROM loans
GROUP BY grade_letter
ORDER BY grade_letter;

-- 3. Default rate by employment status
CREATE OR REPLACE VIEW v_default_by_employment AS
SELECT
    employment_status,
    COUNT(*)                              AS total_loans,
    ROUND(AVG(loan_paid_back) * 100, 2)   AS repayment_rate_pct,
    ROUND(AVG(debt_to_income_ratio), 3)   AS avg_dti
FROM loans
GROUP BY employment_status
ORDER BY repayment_rate_pct ASC;

-- 4. Repayment rate by credit score bucket (the strongest legit predictor)
CREATE OR REPLACE VIEW v_default_by_credit_bucket AS
SELECT
    CASE
        WHEN credit_score < 580 THEN '1. Poor (<580)'
        WHEN credit_score < 670 THEN '2. Fair (580-669)'
        WHEN credit_score < 740 THEN '3. Good (670-739)'
        WHEN credit_score < 800 THEN '4. Very Good (740-799)'
        ELSE '5. Excellent (800+)'
    END                                    AS credit_bucket,
    COUNT(*)                              AS total_loans,
    ROUND(AVG(loan_paid_back) * 100, 2)   AS repayment_rate_pct
FROM loans
GROUP BY credit_bucket
ORDER BY credit_bucket;

-- 5. Repayment rate by debt-to-income bucket (second strongest legit predictor)
CREATE OR REPLACE VIEW v_default_by_dti_bucket AS
SELECT
    CASE
        WHEN debt_to_income_ratio < 0.10 THEN '1. <10%'
        WHEN debt_to_income_ratio < 0.20 THEN '2. 10-20%'
        WHEN debt_to_income_ratio < 0.30 THEN '3. 20-30%'
        WHEN debt_to_income_ratio < 0.40 THEN '4. 30-40%'
        ELSE '5. 40%+'
    END                                    AS dti_bucket,
    COUNT(*)                              AS total_loans,
    ROUND(AVG(loan_paid_back) * 100, 2)   AS repayment_rate_pct
FROM loans
GROUP BY dti_bucket
ORDER BY dti_bucket;

-- 6. Age bracket vs repayment (demographic slice for the dashboard)
CREATE OR REPLACE VIEW v_default_by_age_bracket AS
SELECT
    CASE
        WHEN age < 25 THEN '1. Under 25'
        WHEN age < 35 THEN '2. 25-34'
        WHEN age < 45 THEN '3. 35-44'
        WHEN age < 55 THEN '4. 45-54'
        WHEN age < 65 THEN '5. 55-64'
        ELSE '6. 65+'
    END                                    AS age_bracket,
    COUNT(*)                              AS total_loans,
    ROUND(AVG(loan_paid_back) * 100, 2)   AS repayment_rate_pct
FROM loans
GROUP BY age_bracket
ORDER BY age_bracket;

-- ============================================
-- Quick sanity checks — run these to confirm the load worked
-- ============================================
-- SELECT COUNT(*) FROM loans;                    -- should be 20000
-- SELECT * FROM v_default_by_grade;               -- should match Python correlation check
-- SELECT * FROM v_default_by_credit_bucket;
