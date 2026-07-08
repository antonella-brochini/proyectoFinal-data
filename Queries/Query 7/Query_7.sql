SELECT
    TO_CHAR(MAKE_DATE(order_year, order_month, 1), 'YYYY-MM') AS month,
    ROUND(SUM(sales)::NUMERIC, 2) AS revenue,
    COUNT(DISTINCT order_id) AS orders
FROM sales_data
GROUP BY order_year, order_month
ORDER BY order_year, order_month;