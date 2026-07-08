-- Superstore Sales - Business Analysis Queries
-- Database: working_database (PostgreSQL 18)
-- Schema:   sales_data (flat table, 9,986 rows, 29 columns)


-- SECTION 1: EXECUTIVE KPIs (Key Performance Indicators)
-- The numbers every stakeholder asks for first


-- 1.1 Overall business metrics
SELECT
    COUNT(DISTINCT order_id)                    AS total_orders,
    COUNT(*)                                    AS total_line_items,
    COUNT(DISTINCT customer_id)                 AS unique_customers,
    COUNT(DISTINCT product_id)                  AS unique_products,
    ROUND(SUM(sales)::NUMERIC, 2)               AS total_revenue,
    ROUND(SUM(profit)::NUMERIC, 2)              AS total_profit,
    ROUND(AVG(sales)::NUMERIC, 2)               AS avg_order_value,
    ROUND((SUM(profit) / NULLIF(SUM(sales), 0) * 100)::NUMERIC, 2)
                                                AS overall_profit_margin_pct,
    SUM(is_loss)                                AS loss_making_transactions,
    ROUND((SUM(is_loss)::NUMERIC / COUNT(*) * 100), 2)
                                                AS loss_rate_pct
FROM sales_data;

-- 1.2 Year-over-year growth
SELECT
    order_year,
    ROUND(SUM(sales)::NUMERIC, 2)               AS revenue,
    ROUND(SUM(profit)::NUMERIC, 2)              AS profit,
    COUNT(DISTINCT order_id)                     AS orders,
    ROUND(AVG(sales)::NUMERIC, 2)               AS avg_order_value,
    ROUND(
        ((SUM(sales) - LAG(SUM(sales)) OVER (ORDER BY order_year))
         / NULLIF(LAG(SUM(sales)) OVER (ORDER BY order_year), 0) * 100)::NUMERIC, 2
    )                                            AS revenue_growth_pct,
    ROUND(
        ((SUM(profit) - LAG(SUM(profit)) OVER (ORDER BY order_year))
         / NULLIF(LAG(SUM(profit)) OVER (ORDER BY order_year), 0) * 100)::NUMERIC, 2
    )                                            AS profit_growth_pct
FROM sales_data
GROUP BY order_year
ORDER BY order_year;



-- SECTION 2: SALES ANALYSIS
-- Revenue breakdowns by multiple dimensions


-- 2.1 Total sales and profit by year
SELECT
    order_year                                  AS year,
    ROUND(SUM(sales)::NUMERIC, 2)               AS total_sales,
    ROUND(SUM(profit)::NUMERIC, 2)              AS total_profit,
    COUNT(DISTINCT order_id)                     AS num_orders,
    ROUND(AVG(sales)::NUMERIC, 2)               AS avg_sale
FROM sales_data
GROUP BY order_year
ORDER BY order_year;

-- 2.2 Sales by quarter (all years combined)
SELECT
    order_quarter                              AS quarter,
    ROUND(SUM(sales)::NUMERIC, 2)              AS total_sales,
    ROUND(SUM(profit)::NUMERIC, 2)             AS total_profit,
    COUNT(*)                                    AS transactions
FROM sales_data
GROUP BY order_quarter
ORDER BY order_quarter;

-- 2.3 Monthly sales trend (time series)
SELECT
    TO_CHAR(MAKE_DATE(order_year, order_month, 1), 'YYYY-MM')
                                                AS month,
    ROUND(SUM(sales)::NUMERIC, 2)              AS revenue,
    ROUND(SUM(profit)::NUMERIC, 2)             AS profit,
    COUNT(DISTINCT order_id)                    AS orders,
    ROUND(AVG(sales)::NUMERIC, 2)              AS avg_order_value
FROM sales_data
GROUP BY order_year, order_month
ORDER BY order_year, order_month;

-- 2.4 Day-of-week sales pattern
SELECT
    order_day_name,
    COUNT(*)                                    AS transactions,
    ROUND(SUM(sales)::NUMERIC, 2)              AS total_sales,
    ROUND(AVG(sales)::NUMERIC, 2)              AS avg_sale
FROM sales_data
GROUP BY order_day_name,
         CASE order_day_name
             WHEN 'Monday' THEN 1 WHEN 'Tuesday' THEN 2
             WHEN 'Wednesday' THEN 3 WHEN 'Thursday' THEN 4
             WHEN 'Friday' THEN 5 WHEN 'Saturday' THEN 6
             WHEN 'Sunday' THEN 7
         END
ORDER BY 2;

-- 2.5 Sales by region
SELECT
    region,
    ROUND(SUM(sales)::NUMERIC, 2)              AS total_sales,
    ROUND(SUM(profit)::NUMERIC, 2)             AS total_profit,
    COUNT(DISTINCT order_id)                    AS orders,
    COUNT(DISTINCT customer_id)                 AS customers,
    ROUND(AVG(profit_margin)::NUMERIC, 2)      AS avg_margin_pct,
    ROUND((SUM(sales) / (SELECT SUM(sales) FROM sales_data) * 100)::NUMERIC, 1)
                                                AS pct_of_total_revenue
FROM sales_data
GROUP BY region
ORDER BY total_sales DESC;

-- 2.6 Sales by state (top 15)
SELECT
    state,
    region,
    ROUND(SUM(sales)::NUMERIC, 2)              AS total_sales,
    ROUND(SUM(profit)::NUMERIC, 2)             AS total_profit,
    COUNT(DISTINCT order_id)                    AS orders,
    ROUND(AVG(profit_margin)::NUMERIC, 2)      AS avg_margin_pct
FROM sales_data
GROUP BY state, region
ORDER BY total_sales DESC
LIMIT 15;

-- 2.7 Sales by ship mode
SELECT
    ship_mode,
    COUNT(*)                                    AS shipments,
    ROUND(SUM(sales)::NUMERIC, 2)              AS total_sales,
    ROUND(AVG(sales)::NUMERIC, 2)              AS avg_sale,
    ROUND(AVG(shipping_days)::NUMERIC, 1)      AS avg_shipping_days
FROM sales_data
GROUP BY ship_mode
ORDER BY total_sales DESC;



-- SECTION 3: PRODUCT ANALYSIS
-- Best sellers, worst performers, category insights


-- 3.1 Top 10 products by revenue
SELECT
    product_id,
    product_name,
    category,
    sub_category,
    ROUND(SUM(sales)::NUMERIC, 2)              AS total_revenue,
    ROUND(SUM(profit)::NUMERIC, 2)             AS total_profit,
    SUM(quantity)                               AS units_sold,
    COUNT(DISTINCT order_id)                    AS num_orders,
    ROUND(AVG(profit_margin)::NUMERIC, 2)      AS avg_margin_pct
FROM sales_data
GROUP BY product_id, product_name, category, sub_category
ORDER BY total_revenue DESC
LIMIT 10;

-- 3.2 Top 10 products by profit
SELECT
    product_id,
    product_name,
    category,
    sub_category,
    ROUND(SUM(profit)::NUMERIC, 2)             AS total_profit,
    ROUND(SUM(sales)::NUMERIC, 2)              AS total_revenue,
    SUM(quantity)                               AS units_sold,
    ROUND(AVG(profit_margin)::NUMERIC, 2)      AS avg_margin_pct
FROM sales_data
GROUP BY product_id, product_name, category, sub_category
ORDER BY total_profit DESC
LIMIT 10;

-- 3.3 Worst 10 products (biggest losses)
SELECT
    product_id,
    product_name,
    category,
    sub_category,
    ROUND(SUM(profit)::NUMERIC, 2)             AS total_profit,
    ROUND(SUM(sales)::NUMERIC, 2)              AS total_revenue,
    SUM(quantity)                               AS units_sold,
    SUM(is_loss)                                AS loss_transactions,
    ROUND(AVG(discount)::NUMERIC, 2)           AS avg_discount
FROM sales_data
GROUP BY product_id, product_name, category, sub_category
ORDER BY total_profit ASC
LIMIT 10;

-- 3.4 Category performance
SELECT
    category,
    COUNT(*)                                    AS transactions,
    COUNT(DISTINCT product_id)                  AS unique_products,
    ROUND(SUM(sales)::NUMERIC, 2)              AS total_sales,
    ROUND(SUM(profit)::NUMERIC, 2)             AS total_profit,
    ROUND(AVG(profit_margin)::NUMERIC, 2)      AS avg_margin_pct,
    SUM(is_loss)                                AS loss_count,
    ROUND((SUM(is_loss)::NUMERIC / COUNT(*) * 100), 1)
                                                AS loss_rate_pct
FROM sales_data
GROUP BY category
ORDER BY total_sales DESC;

-- 3.5 Sub-category performance
SELECT
    category,
    sub_category,
    COUNT(*)                                    AS transactions,
    ROUND(SUM(sales)::NUMERIC, 2)              AS total_sales,
    ROUND(SUM(profit)::NUMERIC, 2)             AS total_profit,
    ROUND(AVG(profit_margin)::NUMERIC, 2)      AS avg_margin_pct,
    SUM(is_loss)                                AS losses,
    RANK() OVER (ORDER BY SUM(sales) DESC)      AS sales_rank
FROM sales_data
GROUP BY category, sub_category
ORDER BY total_sales DESC;

-- 3.6 Products with highest discount-driven losses
-- (products where high average discount correlates with negative profit)
SELECT
    product_name,
    sub_category,
    COUNT(*)                                    AS times_ordered,
    ROUND(AVG(discount)::NUMERIC, 2)           AS avg_discount,
    ROUND(SUM(profit)::NUMERIC, 2)             AS total_profit,
    ROUND(AVG(profit_margin)::NUMERIC, 2)      AS avg_margin_pct
FROM sales_data
WHERE profit < 0
GROUP BY product_name, sub_category
HAVING COUNT(*) >= 3
ORDER BY total_profit ASC
LIMIT 10;



-- SECTION 4: CUSTOMER ANALYSIS
-- Segmentation, loyalty, and lifetime value


-- 4.1 Top 10 customers by revenue
SELECT
    customer_id,
    customer_name,
    segment,
    COUNT(DISTINCT order_id)                    AS total_orders,
    ROUND(SUM(sales)::NUMERIC, 2)              AS total_spent,
    ROUND(SUM(profit)::NUMERIC, 2)             AS profit_generated,
    ROUND(AVG(sales)::NUMERIC, 2)              AS avg_order_value,
    MIN(order_date)                             AS first_order,
    MAX(order_date)                             AS last_order
FROM sales_data
GROUP BY customer_id, customer_name, segment
ORDER BY total_spent DESC
LIMIT 10;

-- 4.2 Customer segments performance
SELECT
    segment,
    COUNT(DISTINCT customer_id)                 AS customers,
    COUNT(DISTINCT order_id)                    AS orders,
    ROUND(SUM(sales)::NUMERIC, 2)              AS total_sales,
    ROUND(SUM(profit)::NUMERIC, 2)             AS total_profit,
    ROUND(AVG(sales)::NUMERIC, 2)              AS avg_order_value,
    ROUND((SUM(sales) / (SELECT SUM(sales) FROM sales_data) * 100)::NUMERIC, 1)
                                                AS pct_of_revenue
FROM sales_data
GROUP BY segment
ORDER BY total_sales DESC;

-- 4.3 Repeat customers (ordered more than once)
WITH customer_orders AS (
    SELECT
        customer_id,
        customer_name,
        segment,
        COUNT(DISTINCT order_id) AS order_count,
        ROUND(SUM(sales)::NUMERIC, 2) AS total_spent
    FROM sales_data
    GROUP BY customer_id, customer_name, segment
)
SELECT
    CASE
        WHEN order_count = 1 THEN 'One-time'
        WHEN order_count BETWEEN 2 AND 5 THEN 'Repeat (2-5)'
        WHEN order_count BETWEEN 6 AND 10 THEN 'Loyal (6-10)'
        ELSE 'VIP (11+)'
    END                                         AS customer_tier,
    COUNT(*)                                    AS num_customers,
    ROUND(SUM(total_spent)::NUMERIC, 2)        AS total_revenue,
    ROUND(AVG(order_count)::NUMERIC, 1)        AS avg_orders
FROM customer_orders
GROUP BY 1
ORDER BY MIN(order_count);

-- 4.4 RFM Segmentation (Recency, Frequency, Monetary)
-- Industry-standard customer value model
WITH rfm AS (
    SELECT
        customer_id,
        customer_name,
        segment,
        MAX(order_date)                         AS last_order_date,
        (SELECT MAX(order_date) FROM sales_data) - MAX(order_date)
                                                AS recency_days,
        COUNT(DISTINCT order_id)                AS frequency,
        ROUND(SUM(sales)::NUMERIC, 2)          AS monetary
    FROM sales_data
    GROUP BY customer_id, customer_name, segment
)
SELECT
    customer_id,
    customer_name,
    segment,
    recency_days::INT,
    frequency,
    monetary,
    NTILE(4) OVER (ORDER BY recency_days DESC)  AS r_score,
    NTILE(4) OVER (ORDER BY frequency)          AS f_score,
    NTILE(4) OVER (ORDER BY monetary)           AS m_score,
    CASE
        WHEN NTILE(4) OVER (ORDER BY recency_days DESC) >= 3
         AND NTILE(4) OVER (ORDER BY frequency) >= 3
         AND NTILE(4) OVER (ORDER BY monetary) >= 3
            THEN 'Champions'
        WHEN NTILE(4) OVER (ORDER BY recency_days DESC) >= 3
         AND NTILE(4) OVER (ORDER BY frequency) <= 2
            THEN 'New Customers'
        WHEN NTILE(4) OVER (ORDER BY recency_days DESC) <= 2
         AND NTILE(4) OVER (ORDER BY frequency) >= 3
            THEN 'At Risk'
        WHEN NTILE(4) OVER (ORDER BY recency_days DESC) <= 2
         AND NTILE(4) OVER (ORDER BY frequency) <= 2
            THEN 'Lost'
        ELSE 'Potential Loyalists'
    END                                         AS rfm_segment
FROM rfm
ORDER BY monetary DESC
LIMIT 30;

-- 4.5 Customer lifetime value (CLV) estimate
-- Based on average order value x purchase frequency x estimated lifespan
WITH customer_stats AS (
    SELECT
        customer_id,
        customer_name,
        segment,
        COUNT(DISTINCT order_id)                    AS total_orders,
        ROUND(SUM(sales)::NUMERIC, 2)              AS total_revenue,
        ROUND(AVG(sales)::NUMERIC, 2)              AS avg_order_value,
        (MAX(order_date) - MIN(order_date))::INT
                                                    AS customer_days,
        CASE
            WHEN (MAX(order_date) - MIN(order_date))::INT > 0
            THEN ROUND((COUNT(DISTINCT order_id)::NUMERIC /
                        (MAX(order_date) - MIN(order_date))::INT) * 365, 2)
            ELSE COUNT(DISTINCT order_id)::NUMERIC
        END                                         AS orders_per_year
    FROM sales_data
    GROUP BY customer_id, customer_name, segment
    HAVING COUNT(DISTINCT order_id) > 1
)
SELECT
    customer_id,
    customer_name,
    segment,
    total_orders,
    total_revenue,
    avg_order_value,
    orders_per_year,
    ROUND((avg_order_value * orders_per_year * 3)::NUMERIC, 2)
                                                AS projected_3yr_clv
FROM customer_stats
ORDER BY projected_3yr_clv DESC
LIMIT 20;



-- SECTION 5: PROFITABILITY DEEP DIVE
-- Understanding where money is made and lost


-- 5.1 Profit distribution by category and sub-category
SELECT
    category,
    sub_category,
    ROUND(MIN(profit)::NUMERIC, 2)             AS min_profit,
    ROUND(PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY profit)::NUMERIC, 2)
                                                AS q1_profit,
    ROUND(PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY profit)::NUMERIC, 2)
                                                AS median_profit,
    ROUND(PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY profit)::NUMERIC, 2)
                                                AS q3_profit,
    ROUND(MAX(profit)::NUMERIC, 2)             AS max_profit,
    ROUND(AVG(profit)::NUMERIC, 2)             AS avg_profit
FROM sales_data
GROUP BY category, sub_category
ORDER BY avg_profit DESC;

-- 5.2 Impact of discounts on profitability
SELECT
    discount_tier,
    COUNT(*)                                    AS transactions,
    ROUND(SUM(sales)::NUMERIC, 2)              AS total_sales,
    ROUND(SUM(profit)::NUMERIC, 2)             AS total_profit,
    ROUND(AVG(profit_margin)::NUMERIC, 2)      AS avg_margin_pct,
    SUM(is_loss)                                AS loss_count,
    ROUND((SUM(is_loss)::NUMERIC / COUNT(*) * 100), 1)
                                                AS loss_rate_pct
FROM sales_data
GROUP BY discount_tier
ORDER BY MIN(discount);

-- 5.3 Loss analysis: what causes losses?
WITH loss_data AS (
    SELECT
        category,
        sub_category,
        region,
        ship_mode,
        ROUND(AVG(discount)::NUMERIC, 2)       AS avg_discount,
        ROUND(SUM(profit)::NUMERIC, 2)         AS total_loss,
        COUNT(*)                                AS loss_count
    FROM sales_data
    WHERE is_loss = 1
    GROUP BY category, sub_category, region, ship_mode
)
SELECT *
FROM loss_data
ORDER BY total_loss ASC
LIMIT 15;

-- 5.4 Profit margin by region and category (cross-tab view)
SELECT
    region,
    ROUND(SUM(CASE WHEN category = 'Office Supplies' THEN profit ELSE 0 END)::NUMERIC, 2)
                                                AS office_supplies_profit,
    ROUND(SUM(CASE WHEN category = 'Furniture' THEN profit ELSE 0 END)::NUMERIC, 2)
                                                AS furniture_profit,
    ROUND(SUM(CASE WHEN category = 'Technology' THEN profit ELSE 0 END)::NUMERIC, 2)
                                                AS technology_profit,
    ROUND(SUM(profit)::NUMERIC, 2)             AS total_profit
FROM sales_data
GROUP BY region
ORDER BY total_profit DESC;



-- SECTION 6: SHIPPING & LOGISTICS
-- Delivery performance analysis


-- 6.1 Shipping performance by mode
SELECT
    ship_mode,
    COUNT(*)                                    AS shipments,
    ROUND(AVG(shipping_days)::NUMERIC, 1)      AS avg_days,
    MIN(shipping_days)                          AS min_days,
    MAX(shipping_days)                          AS max_days,
    ROUND(SUM(sales)::NUMERIC, 2)              AS total_sales,
    ROUND(AVG(sales)::NUMERIC, 2)              AS avg_sale_value
FROM sales_data
GROUP BY ship_mode
ORDER BY avg_days;

-- 6.2 Shipping days distribution
SELECT
    shipping_days,
    COUNT(*)                                    AS orders,
    ROUND((COUNT(*)::NUMERIC / (SELECT COUNT(*) FROM sales_data) * 100), 1)
                                                AS pct_of_orders,
    ROUND(SUM(sales)::NUMERIC, 2)              AS total_sales
FROM sales_data
GROUP BY shipping_days
ORDER BY shipping_days;

-- 6.3 Average shipping days by region
SELECT
    region,
    ROUND(AVG(shipping_days)::NUMERIC, 1)      AS avg_shipping_days,
    COUNT(*)                                    AS orders
FROM sales_data
GROUP BY region
ORDER BY avg_shipping_days;



-- SECTION 7: ADVANCED ANALYTICS
-- Window functions, cohort analysis, Pareto, running totals


-- 7.1 Pareto Analysis (80/20 rule) - do 20% of products drive 80% of revenue?
WITH product_revenue AS (
    SELECT
        product_id,
        product_name,
        SUM(sales) AS revenue
    FROM sales_data
    GROUP BY product_id, product_name
),
ranked AS (
    SELECT
        product_id,
        product_name,
        revenue,
        SUM(revenue) OVER (ORDER BY revenue DESC) AS cumulative_revenue,
        SUM(revenue) OVER ()                       AS total_revenue
    FROM product_revenue
)
SELECT
    COUNT(*)                                    AS top_products_needed,
    ROUND(MAX(cumulative_revenue)::NUMERIC, 2) AS revenue_captured,
    ROUND((MAX(cumulative_revenue) / MAX(total_revenue) * 100)::NUMERIC, 1)
                                                AS pct_of_total,
    (SELECT COUNT(*) FROM product_revenue)      AS total_products,
    ROUND((COUNT(*)::NUMERIC / (SELECT COUNT(*) FROM product_revenue) * 100), 1)
                                                AS pct_of_products
FROM ranked
WHERE cumulative_revenue <= (SELECT SUM(sales) * 0.80 FROM sales_data);

-- 7.2 Running total of sales over time
SELECT
    TO_CHAR(MAKE_DATE(order_year, order_month, 1), 'YYYY-MM')
                                                AS month,
    ROUND(SUM(sales)::NUMERIC, 2)              AS monthly_revenue,
    ROUND(SUM(SUM(sales)) OVER (ORDER BY order_year, order_month)::NUMERIC, 2)
                                                AS cumulative_revenue,
    ROUND(SUM(SUM(profit)) OVER (ORDER BY order_year, order_month)::NUMERIC, 2)
                                                AS cumulative_profit
FROM sales_data
GROUP BY order_year, order_month
ORDER BY order_year, order_month;

-- 7.3 Moving averages (3-month rolling average)
WITH monthly AS (
    SELECT
        order_year,
        order_month,
        SUM(sales) AS revenue
    FROM sales_data
    GROUP BY order_year, order_month
)
SELECT
    TO_CHAR(MAKE_DATE(order_year, order_month, 1), 'YYYY-MM')
                                                AS month,
    ROUND(revenue::NUMERIC, 2)                 AS monthly_revenue,
    ROUND(AVG(revenue) OVER (
        ORDER BY order_year, order_month
        ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
    )::NUMERIC, 2)                              AS moving_avg_3mo,
    ROUND(AVG(revenue) OVER (
        ORDER BY order_year, order_month
        ROWS BETWEEN 5 PRECEDING AND CURRENT ROW
    )::NUMERIC, 2)                              AS moving_avg_6mo
FROM monthly
ORDER BY order_year, order_month;

-- 7.4 Month-over-month growth rate
WITH monthly AS (
    SELECT
        order_year,
        order_month,
        SUM(sales) AS revenue
    FROM sales_data
    GROUP BY order_year, order_month
)
SELECT
    TO_CHAR(MAKE_DATE(order_year, order_month, 1), 'YYYY-MM')
                                                AS month,
    ROUND(revenue::NUMERIC, 2)                 AS revenue,
    ROUND(LAG(revenue) OVER (ORDER BY order_year, order_month)::NUMERIC, 2)
                                                AS prev_month,
    ROUND(
        ((revenue - LAG(revenue) OVER (ORDER BY order_year, order_month))
         / NULLIF(LAG(revenue) OVER (ORDER BY order_year, order_month), 0) * 100
        )::NUMERIC, 2
    )                                           AS mom_growth_pct
FROM monthly
ORDER BY order_year, order_month;

-- 7.5 Seasonality: average monthly revenue by year (heatmap-ready data)
SELECT
    order_year,
    ROUND(SUM(CASE WHEN order_month = 1  THEN sales ELSE 0 END)::NUMERIC, 0) AS jan,
    ROUND(SUM(CASE WHEN order_month = 2  THEN sales ELSE 0 END)::NUMERIC, 0) AS feb,
    ROUND(SUM(CASE WHEN order_month = 3  THEN sales ELSE 0 END)::NUMERIC, 0) AS mar,
    ROUND(SUM(CASE WHEN order_month = 4  THEN sales ELSE 0 END)::NUMERIC, 0) AS apr,
    ROUND(SUM(CASE WHEN order_month = 5  THEN sales ELSE 0 END)::NUMERIC, 0) AS may,
    ROUND(SUM(CASE WHEN order_month = 6  THEN sales ELSE 0 END)::NUMERIC, 0) AS jun,
    ROUND(SUM(CASE WHEN order_month = 7  THEN sales ELSE 0 END)::NUMERIC, 0) AS jul,
    ROUND(SUM(CASE WHEN order_month = 8  THEN sales ELSE 0 END)::NUMERIC, 0) AS aug,
    ROUND(SUM(CASE WHEN order_month = 9  THEN sales ELSE 0 END)::NUMERIC, 0) AS sep,
    ROUND(SUM(CASE WHEN order_month = 10 THEN sales ELSE 0 END)::NUMERIC, 0) AS oct,
    ROUND(SUM(CASE WHEN order_month = 11 THEN sales ELSE 0 END)::NUMERIC, 0) AS nov,
    ROUND(SUM(CASE WHEN order_month = 12 THEN sales ELSE 0 END)::NUMERIC, 0) AS dec
FROM sales_data
GROUP BY order_year
ORDER BY order_year;

-- 7.6 Customer cohort analysis (by first order quarter)
WITH first_order AS (
    SELECT
        customer_id,
        MIN(order_date) AS cohort_date
    FROM sales_data
    GROUP BY customer_id
),
cohort_data AS (
    SELECT
        f.customer_id,
        TO_CHAR(DATE_TRUNC('quarter', f.cohort_date), 'YYYY-"Q"Q')
                                                AS cohort,
        EXTRACT(QUARTER FROM AGE(s.order_date, f.cohort_date))::INT
            + EXTRACT(YEAR FROM AGE(s.order_date, f.cohort_date))::INT * 4
                                                AS quarters_since_first,
        s.sales
    FROM sales_data s
    JOIN first_order f ON s.customer_id = f.customer_id
)
SELECT
    cohort,
    COUNT(DISTINCT customer_id)                 AS cohort_size,
    COUNT(DISTINCT CASE WHEN quarters_since_first = 0 THEN customer_id END) AS q0,
    COUNT(DISTINCT CASE WHEN quarters_since_first = 1 THEN customer_id END) AS q1,
    COUNT(DISTINCT CASE WHEN quarters_since_first = 2 THEN customer_id END) AS q2,
    COUNT(DISTINCT CASE WHEN quarters_since_first = 3 THEN customer_id END) AS q3,
    COUNT(DISTINCT CASE WHEN quarters_since_first = 4 THEN customer_id END) AS q4,
    COUNT(DISTINCT CASE WHEN quarters_since_first >= 5 THEN customer_id END) AS q5_plus
FROM cohort_data
GROUP BY cohort
ORDER BY cohort;


-- SECTION 8: STAR SCHEMA QUERIES
-- Demonstrating normalized schema usage with JOINs


-- 8.1 Sales by customer segment using star schema
SELECT
    c.segment,
    COUNT(DISTINCT f.order_id)                  AS orders,
    ROUND(SUM(f.sales)::NUMERIC, 2)            AS total_sales,
    ROUND(SUM(f.profit)::NUMERIC, 2)           AS total_profit
FROM fact_sales f
JOIN dim_customer c  ON f.customer_sk  = c.customer_sk
GROUP BY c.segment
ORDER BY total_sales DESC;

-- 8.2 Monthly sales using date dimension
SELECT
    d.year,
    d.month,
    d.month_name,
    COUNT(DISTINCT f.order_id)                  AS orders,
    ROUND(SUM(f.sales)::NUMERIC, 2)            AS revenue,
    ROUND(SUM(f.profit)::NUMERIC, 2)           AS profit
FROM fact_sales f
JOIN dim_date d ON f.order_date_sk = d.date_sk
GROUP BY d.year, d.month, d.month_name
ORDER BY d.year, d.month;

-- 8.3 Top products with geography using star schema
SELECT
    p.product_name,
    p.category,
    g.region,
    g.state,
    ROUND(SUM(f.sales)::NUMERIC, 2)            AS total_sales,
    SUM(f.quantity)                             AS units_sold
FROM fact_sales f
JOIN dim_product p    ON f.product_sk   = p.product_sk
JOIN dim_geography g  ON f.geography_sk = g.geography_sk
GROUP BY p.product_name, p.category, g.region, g.state
ORDER BY total_sales DESC
LIMIT 20;



-- SECTION 9: EXECUTIVE DASHBOARD SUMMARY
-- One query to rule them all


-- 9.1 Complete business snapshot
WITH metrics AS (
    SELECT
        -- Revenue
        ROUND(SUM(sales)::NUMERIC, 0)                                     AS total_revenue,
        ROUND(SUM(profit)::NUMERIC, 0)                                    AS total_profit,
        ROUND((SUM(profit) / NULLIF(SUM(sales), 0) * 100)::NUMERIC, 1)   AS profit_margin,
        -- Orders
        COUNT(DISTINCT order_id)                                          AS total_orders,
        ROUND(AVG(sales)::NUMERIC, 2)                                     AS avg_order_value,
        -- Customers
        COUNT(DISTINCT customer_id)                                       AS total_customers,
        ROUND(SUM(sales)::NUMERIC / COUNT(DISTINCT customer_id), 2)      AS revenue_per_customer,
        -- Products
        COUNT(DISTINCT product_id)                                        AS products_sold,
        -- Losses
        SUM(is_loss)                                                      AS loss_transactions,
        ROUND((SUM(is_loss)::NUMERIC / COUNT(*) * 100), 1)               AS loss_rate
    FROM sales_data
),
top_product AS (
    SELECT product_name, SUM(sales) AS rev
    FROM sales_data
    GROUP BY product_name
    ORDER BY rev DESC
    LIMIT 1
),
top_customer AS (
    SELECT customer_name, SUM(sales) AS spent
    FROM sales_data
    GROUP BY customer_name
    ORDER BY spent DESC
    LIMIT 1
),
top_region AS (
    SELECT region, SUM(sales) AS rev
    FROM sales_data
    GROUP BY region
    ORDER BY rev DESC
    LIMIT 1
)
SELECT
    m.total_revenue,
    m.total_profit,
    m.profit_margin,
    m.total_orders,
    m.avg_order_value,
    m.total_customers,
    m.revenue_per_customer,
    m.products_sold,
    m.loss_transactions,
    m.loss_rate,
    tp.product_name                               AS top_product,
    tc.customer_name                              AS top_customer,
    tr.region                                     AS top_region
FROM metrics m
CROSS JOIN top_product tp
CROSS JOIN top_customer tc
CROSS JOIN top_region tr;
