-- Product revenue concentration (Pareto / ABC classification) and product-level return rate.
WITH product AS (
    SELECT
        StockCode,
        MAX(Description)                                           AS description,
        ROUND(SUM(CASE WHEN is_return = 0 THEN Revenue END), 2)    AS gross_revenue,
        ROUND(-COALESCE(SUM(CASE WHEN is_return = 1 THEN Revenue END), 0), 2) AS returns_value,
        SUM(CASE WHEN is_return = 0 THEN Quantity END)             AS units_sold,
        COUNT(DISTINCT CASE WHEN is_return = 0 THEN Invoice END)   AS orders,
        COUNT(DISTINCT CustomerID)                                 AS customers
    FROM transactions
    GROUP BY StockCode
),
ranked AS (
    SELECT
        *,
        gross_revenue - returns_value                                              AS net_revenue,
        ROW_NUMBER() OVER (ORDER BY gross_revenue - returns_value DESC)            AS revenue_rank,
        SUM(gross_revenue - returns_value) OVER (ORDER BY gross_revenue - returns_value DESC
                                                 ROWS UNBOUNDED PRECEDING)         AS running_revenue,
        SUM(gross_revenue - returns_value) OVER ()                                 AS total_revenue,
        COUNT(*) OVER ()                                                           AS product_count
    FROM product
    WHERE gross_revenue > 0
)
SELECT
    StockCode,
    description,
    gross_revenue,
    returns_value,
    ROUND(net_revenue, 2)                                       AS net_revenue,
    ROUND(100.0 * returns_value / gross_revenue, 2)             AS return_rate_pct,
    units_sold,
    orders,
    customers,
    revenue_rank,
    ROUND(100.0 * revenue_rank / product_count, 2)              AS pct_of_products,
    ROUND(100.0 * running_revenue / total_revenue, 2)           AS cumulative_revenue_pct,
    CASE
        WHEN 100.0 * running_revenue / total_revenue <= 80 THEN 'A'
        WHEN 100.0 * running_revenue / total_revenue <= 95 THEN 'B'
        ELSE 'C'
    END                                                         AS abc_class
FROM ranked
ORDER BY revenue_rank;
