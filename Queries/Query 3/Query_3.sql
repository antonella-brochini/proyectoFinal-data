SELECT product_name, category,
       ROUND(SUM(sales)::NUMERIC, 2) AS revenue,
       SUM(quantity) AS units_sold
FROM sales_data
GROUP BY product_name, category
ORDER BY revenue DESC
LIMIT 10;