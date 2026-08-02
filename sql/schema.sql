-- ============================================
-- Loan Risk Engine — Database Schema
-- ============================================

CREATE DATABASE IF NOT EXISTS loan_engine;
USE loan_engine;

DROP TABLE IF EXISTS loans;

CREATE TABLE loans (
    loan_id                INT AUTO_INCREMENT PRIMARY KEY,
    age                    INT NOT NULL,
    gender                 VARCHAR(10) NOT NULL,
    marital_status          VARCHAR(15) NOT NULL,
    education_level         VARCHAR(20) NOT NULL,
    annual_income           DECIMAL(12,2) NOT NULL,
    monthly_income          DECIMAL(10,2) NOT NULL,
    employment_status       VARCHAR(20) NOT NULL,
    debt_to_income_ratio    DECIMAL(5,3) NOT NULL,
    credit_score            INT NOT NULL,
    loan_amount             DECIMAL(12,2) NOT NULL,
    loan_purpose            VARCHAR(30) NOT NULL,
    interest_rate           DECIMAL(5,2) NOT NULL,
    loan_term               INT NOT NULL,
    installment              DECIMAL(10,2) NOT NULL,
    grade_subgrade           VARCHAR(2) NOT NULL,
    num_of_open_accounts     INT NOT NULL,
    total_credit_limit       DECIMAL(12,2) NOT NULL,
    current_balance          DECIMAL(12,2) NOT NULL,
    delinquency_history       INT NOT NULL,
    public_records            INT NOT NULL,
    num_of_delinquencies      INT NOT NULL,
    loan_paid_back            TINYINT NOT NULL,  -- 1 = paid back, 0 = default

    -- indexes for the queries we'll run most often
    INDEX idx_grade (grade_subgrade),
    INDEX idx_purpose (loan_purpose),
    INDEX idx_employment (employment_status),
    INDEX idx_paid_back (loan_paid_back)
);
