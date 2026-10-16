-- RFM segmentation (Recency, Frequency, Monetary) scored 1-5 with NTILE quintiles.
-- Snapshot date = the day after the last transaction (2011-12-10).
WITH customer_stats AS (
    SELECT
        CustomerID,
        MAX(Country)                                                     AS country,
        CAST(JULIANDAY('2011-12-10') - JULIANDAY(MAX(order_date)) AS INT) AS recency_days,
        COUNT(*)                                                         AS frequency,
        ROUND(SUM(order_value), 2)                                       AS monetary
    FROM v_orders
    GROUP BY CustomerID
),
returns AS (
    SELECT CustomerID, ROUND(-SUM(Revenue), 2) AS returned_value
    FROM v_customer_lines
    WHERE is_return = 1
    GROUP BY CustomerID
),
scored AS (
    SELECT
        s.*,
        COALESCE(r.returned_value, 0)                      AS returned_value,
        6 - NTILE(5) OVER (ORDER BY recency_days)          AS r_score,  -- recent = 5
        NTILE(5) OVER (ORDER BY frequency)                 AS f_score,
        NTILE(5) OVER (ORDER BY monetary)                  AS m_score
    FROM customer_stats s
    LEFT JOIN returns r USING (CustomerID)
)
SELECT
    *,
    r_score || f_score || m_score AS rfm_code,
    CASE
        WHEN r_score >= 4 AND f_score >= 4 AND m_score >= 4 THEN 'Champions'
        WHEN r_score >= 3 AND f_score >= 3                  THEN 'Loyal'
        WHEN r_score >= 4 AND f_score <= 2                  THEN 'New / Promising'
        WHEN r_score <= 2 AND f_score >= 4                  THEN 'Can''t Lose Them'
        WHEN r_score <= 2 AND f_score >= 2                  THEN 'At Risk'
        WHEN r_score = 3 AND f_score <= 2                   THEN 'Need Attention'
        ELSE 'Hibernating'
    END AS segment
FROM scored
ORDER BY monetary DESC;
