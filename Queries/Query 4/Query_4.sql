SELECT product_name,
       ROUND(SUM(profit)::NUMERIC, 2) AS total_loss
FROM sales_data
GROUP BY product_name
HAVING SUM(profit) < 0
ORDER BY total_loss ASC
LIMIT 10;