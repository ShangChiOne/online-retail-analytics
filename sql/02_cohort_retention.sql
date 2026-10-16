-- Monthly acquisition-cohort retention.
-- retention_pct = share of a cohort's customers who placed an order N months after their first month.
WITH activity AS (
    SELECT DISTINCT o.CustomerID, c.cohort_month, o.order_month
    FROM v_orders o
    JOIN v_customer_cohort c USING (CustomerID)
),
indexed AS (
    SELECT
        cohort_month,
        CustomerID,
        (CAST(SUBSTR(order_month, 1, 4) AS INT) - CAST(SUBSTR(cohort_month, 1, 4) AS INT)) * 12
        + (CAST(SUBSTR(order_month, 6, 2) AS INT) - CAST(SUBSTR(cohort_month, 6, 2) AS INT)) AS month_number
    FROM activity
),
cohort_size AS (
    SELECT cohort_month, COUNT(*) AS cohort_customers
    FROM v_customer_cohort
    GROUP BY 1
)
SELECT
    i.cohort_month,
    s.cohort_customers,
    i.month_number,
    COUNT(DISTINCT i.CustomerID)                                        AS active_customers,
    ROUND(100.0 * COUNT(DISTINCT i.CustomerID) / s.cohort_customers, 1) AS retention_pct
FROM indexed i
JOIN cohort_size s USING (cohort_month)
GROUP BY i.cohort_month, s.cohort_customers, i.month_number
ORDER BY i.cohort_month, i.month_number;
