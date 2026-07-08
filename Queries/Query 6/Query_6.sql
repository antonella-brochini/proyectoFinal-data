SELECT
    CASE
        WHEN COUNT(DISTINCT order_id) = 1 THEN 'One-time'
        WHEN COUNT(DISTINCT order_id) BETWEEN 2 AND 5 THEN 'Repeat (2-5)'
        WHEN COUNT(DISTINCT order_id) BETWEEN 6 AND 10 THEN 'Loyal (6-10)'
        ELSE 'VIP (11+)'
    END AS customer_tier,
    COUNT(*) AS num_customers,
    ROUND(SUM(sales)::NUMERIC, 2) AS total_revenue
FROM sales_data
GROUP BY customer_id, customer_name
ORDER BY num_customers DESC;