-- Monthly business KPIs: net revenue, orders, active & new customers, AOV, return rate.
-- Revenue includes guest (no CustomerID) lines; customer metrics use identified customers only.
WITH monthly_revenue AS (
    SELECT
        STRFTIME('%Y-%m', InvoiceDate)                             AS month,
        ROUND(SUM(CASE WHEN is_return = 0 THEN Revenue END), 2)    AS gross_revenue,
        ROUND(-SUM(CASE WHEN is_return = 1 THEN Revenue END), 2)   AS returns_value,
        ROUND(SUM(Revenue), 2)                                     AS net_revenue
    FROM transactions
    GROUP BY 1
),
monthly_orders AS (
    SELECT
        order_month                     AS month,
        COUNT(*)                        AS orders,
        COUNT(DISTINCT CustomerID)      AS active_customers,
        ROUND(AVG(order_value), 2)      AS avg_order_value
    FROM v_orders
    GROUP BY 1
),
new_customers AS (
    SELECT cohort_month AS month, COUNT(*) AS new_customers
    FROM v_customer_cohort
    GROUP BY 1
)
SELECT
    r.month,
    r.gross_revenue,
    r.returns_value,
    r.net_revenue,
    ROUND(100.0 * r.returns_value / r.gross_revenue, 2)            AS return_rate_pct,
    o.orders,
    o.active_customers,
    COALESCE(n.new_customers, 0)                                   AS new_customers,
    o.active_customers - COALESCE(n.new_customers, 0)              AS returning_customers,
    o.avg_order_value,
    -- Year-over-year growth using a 12-month window offset.
    ROUND(100.0 * (r.net_revenue - LAG(r.net_revenue, 12) OVER (ORDER BY r.month))
          / LAG(r.net_revenue, 12) OVER (ORDER BY r.month), 1)     AS net_revenue_yoy_pct,
    CASE WHEN r.month = '2011-12' THEN 1 ELSE 0 END                AS is_partial_month
FROM monthly_revenue r
JOIN monthly_orders o USING (month)
LEFT JOIN new_customers n USING (month)
ORDER BY r.month;
