-- Market performance by country (identified customers), with revenue per customer
-- and repeat-purchase rate to separate big markets from loyal ones.
WITH per_customer AS (
    SELECT CustomerID, Country, COUNT(*) AS orders, SUM(order_value) AS revenue
    FROM v_orders
    GROUP BY CustomerID, Country
),
returns AS (
    SELECT Country, -SUM(Revenue) AS returns_value
    FROM v_customer_lines
    WHERE is_return = 1
    GROUP BY Country
)
SELECT
    p.Country                                                         AS country,
    COUNT(*)                                                          AS customers,
    SUM(p.orders)                                                     AS orders,
    ROUND(SUM(p.revenue), 2)                                          AS gross_revenue,
    ROUND(SUM(p.revenue) / SUM(p.orders), 2)                          AS avg_order_value,
    ROUND(SUM(p.revenue) / COUNT(*), 2)                               AS revenue_per_customer,
    ROUND(100.0 * SUM(CASE WHEN p.orders > 1 THEN 1 ELSE 0 END) / COUNT(*), 1) AS repeat_rate_pct,
    ROUND(100.0 * COALESCE(r.returns_value, 0) / SUM(p.revenue), 2)   AS return_rate_pct,
    ROUND(100.0 * SUM(p.revenue) / SUM(SUM(p.revenue)) OVER (), 2)    AS revenue_share_pct
FROM per_customer p
LEFT JOIN returns r ON r.Country = p.Country
GROUP BY p.Country
ORDER BY gross_revenue DESC;
