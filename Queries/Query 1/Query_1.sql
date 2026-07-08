SELECT
    COUNT(DISTINCT order_id) AS total_orders,
    ROUND(SUM(sales)::NUMERIC, 2) AS total_sales,
    ROUND(SUM(profit)::NUMERIC, 2) AS total_profit
FROM sales_data;