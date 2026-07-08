SELECT
    TO_CHAR(MAKE_DATE(order_year, order_month, 1), 'YYYY-MM') AS month,
    ROUND(SUM(profit)::NUMERIC, 2) AS profit,
    ROUND(AVG(profit_margin)::NUMERIC, 2) AS avg_margin_pct
FROM sales_data
GROUP BY order_year, order_month
ORDER BY order_year, order_month;