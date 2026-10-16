-- Base views shared by every analysis query.
-- transactions: one row per product line; returns carry negative Quantity / Revenue.

DROP VIEW IF EXISTS v_customer_lines;
CREATE VIEW v_customer_lines AS
SELECT *
FROM transactions
WHERE CustomerID IS NOT NULL;

-- One row per sales invoice (order) for identified customers.
DROP VIEW IF EXISTS v_orders;
CREATE VIEW v_orders AS
SELECT
    Invoice,
    CustomerID,
    Country,
    MIN(InvoiceDate)              AS order_ts,
    DATE(MIN(InvoiceDate))        AS order_date,
    STRFTIME('%Y-%m', MIN(InvoiceDate)) AS order_month,
    COUNT(*)                      AS lines,
    SUM(Quantity)                 AS units,
    ROUND(SUM(Revenue), 2)        AS order_value
FROM v_customer_lines
WHERE is_return = 0
GROUP BY Invoice, CustomerID, Country;

-- Each customer's first purchase month = acquisition cohort.
DROP VIEW IF EXISTS v_customer_cohort;
CREATE VIEW v_customer_cohort AS
SELECT CustomerID, MIN(order_month) AS cohort_month, MIN(order_date) AS first_order_date
FROM v_orders
GROUP BY CustomerID;
