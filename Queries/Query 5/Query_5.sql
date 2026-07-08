SELECT customer_name, segment,
       COUNT(DISTINCT order_id) AS orders,
       ROUND(SUM(sales)::NUMERIC, 2) AS total_spent
FROM sales_data
GROUP BY customer_name, segment
ORDER BY total_spent DESC
LIMIT 10;