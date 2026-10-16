-- When do orders arrive? Weekday x hour order counts and revenue (identified customers).
-- SQLite %w: 0 = Sunday ... 6 = Saturday.
SELECT
    CAST(STRFTIME('%w', order_ts) AS INT)  AS weekday_num,
    CASE STRFTIME('%w', order_ts)
        WHEN '0' THEN 'Sun' WHEN '1' THEN 'Mon' WHEN '2' THEN 'Tue' WHEN '3' THEN 'Wed'
        WHEN '4' THEN 'Thu' WHEN '5' THEN 'Fri' ELSE 'Sat'
    END                                     AS weekday,
    CAST(STRFTIME('%H', order_ts) AS INT)  AS hour,
    COUNT(*)                                AS orders,
    ROUND(SUM(order_value), 2)              AS revenue
FROM v_orders
GROUP BY 1, 2, 3
ORDER BY 1, 3;
