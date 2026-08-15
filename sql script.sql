-- Step 1.1: Create table for raw customer data
CREATE TABLE raw_customers (
    customer_id VARCHAR(50) PRIMARY KEY,
    gender VARCHAR(10),
    senior_citizen INT,
    partner VARCHAR(5),
    dependents VARCHAR(5),
    tenure INT,
    phone_service VARCHAR(15),
    multiple_lines VARCHAR(20),
    internet_service VARCHAR(20),
    online_security VARCHAR(20),
    tech_support VARCHAR(20),
    contract VARCHAR(20),
    paperless_billing VARCHAR(5),
    payment_method VARCHAR(30),
    monthly_charges DECIMAL(10, 2),
    total_charges DECIMAL(10, 2),
    churn VARCHAR(5)
);

ALTER USER postgre
-- Step 2.1: Create feature engineering view
CREATE OR REPLACE VIEW view_churn_features AS
WITH PlatformMetrics AS (
    SELECT 
        customer_id,
        gender,
        tenure,
        contract,
        internet_service,
        tech_support,
        monthly_charges,
        total_charges,
        churn,
        -- Window function to derive platform-wide average monthly charges
        AVG(monthly_charges) OVER() AS platform_avg_spend
    FROM raw_customers
)
SELECT 
    customer_id,
    tenure,
    contract,
    internet_service,
    tech_support,
    monthly_charges,
    total_charges,
    -- Target variable binary conversion
    CASE WHEN churn = 'Yes' THEN 1 ELSE 0 END AS churn_label,
    -- Engineered Feature: High-Value Spender Flag
    CASE WHEN monthly_charges > platform_avg_spend THEN 1 ELSE 0 END AS is_high_value,
    -- Engineered Feature: Customer Lifecycle Tier
    CASE 
        WHEN tenure <= 12 THEN 'New'
        WHEN tenure BETWEEN 13 AND 36 THEN 'Mid-Term'
        ELSE 'Loyal'
    END AS customer_tenure_tier
FROM PlatformMetrics;

-- Test the view in pgAdmin
-- Step 1: Create the missing table structure
CREATE TABLE IF NOT EXISTS fact_churn_predictions (
    customer_id VARCHAR(50) PRIMARY KEY,
    monthly_charges DECIMAL(10, 2),
    churn_probability NUMERIC(5, 4),
    risk_level VARCHAR(20),
    is_high_value INT,
    ai_retention_plan TEXT
);














-- Step 4.1: Create combined reporting view for Power BI
CREATE OR REPLACE VIEW view_powerbi_executive_report AS
SELECT 
    r.customer_id,
    r.contract,
    r.payment_method,
    r.internet_service,
    p.monthly_charges,
    p.churn_probability,
    p.risk_level,
    p.is_high_value,
    p.ai_retention_plan,
    -- Calculate Annual Revenue at Risk ($ARR)
    CASE 
        WHEN p.risk_level = 'High Risk' THEN (p.monthly_charges * 12) 
        ELSE 0 
    END AS annual_revenue_at_risk
FROM raw_customers r
JOIN fact_churn_predictions p ON r.customer_id = p.customer_id;

-- Verify final reporting dataset
SELECT * FROM view_powerbi_executive_report WHERE risk_level = 'High Risk';
SELECT * FROM view_churn_features LIMIT 10;


-- 1. Check the machine learning output table
SELECT * FROM fact_churn_predictions;

-- 2. Check the Power BI reporting view
SELECT * FROM view_powerbi_executive_report;