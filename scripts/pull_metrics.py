import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')), '.env'))

import psycopg2
import pandas as pd

conn = psycopg2.connect(
    dbname=os.environ.get("DB_NAME", "working_database"),
    user=os.environ.get("DB_USER", "postgres"),
    password=os.environ.get("DB_PASSWORD", "your_password_here"),
    host=os.environ.get("DB_HOST", "localhost"),
    port=os.environ.get("DB_PORT", "5432")
)

queries = {
    "category_perf": """
        SELECT category, SUM(sales) AS sales, SUM(profit) AS profit,
               ROUND((SUM(profit)/SUM(sales)*100)::numeric, 1) AS margin,
               COUNT(*) AS txns, SUM(is_loss) AS losses
        FROM sales_data GROUP BY category ORDER BY sales DESC""",

    "subcat_profit": """
        SELECT sub_category, SUM(sales) AS sales, SUM(profit) AS profit,
               ROUND((SUM(profit)/SUM(sales)*100)::numeric, 1) AS margin
        FROM sales_data GROUP BY sub_category ORDER BY profit""",

    "region_perf": """
        SELECT region, SUM(sales) AS sales, SUM(profit) AS profit,
               ROUND((SUM(profit)/SUM(sales)*100)::numeric, 1) AS margin,
               COUNT(DISTINCT customer_id) AS customers,
               SUM(is_loss) AS losses, COUNT(*) AS txns
        FROM sales_data GROUP BY region ORDER BY sales DESC""",

    "state_perf": """
        SELECT state, region, SUM(sales) AS sales, SUM(profit) AS profit,
               ROUND((SUM(profit)/SUM(sales)*100)::numeric, 1) AS margin
        FROM sales_data GROUP BY state, region ORDER BY profit LIMIT 10""",

    "worst_states": """
        SELECT state, region, SUM(sales) AS sales, SUM(profit) AS profit,
               ROUND((SUM(profit)/SUM(sales)*100)::numeric, 1) AS margin
        FROM sales_data GROUP BY state, region ORDER BY profit ASC LIMIT 10""",

    "yoy_growth": """
        SELECT order_year, SUM(sales) AS sales, SUM(profit) AS profit,
               COUNT(DISTINCT order_id) AS orders
        FROM sales_data GROUP BY order_year ORDER BY order_year""",

    "discount_impact": """
        SELECT discount_tier, COUNT(*) AS txns, SUM(sales) AS sales,
               SUM(profit) AS profit, SUM(is_loss) AS losses,
               ROUND((SUM(is_loss)::numeric/COUNT(*)*100), 1) AS loss_rate
        FROM sales_data GROUP BY discount_tier ORDER BY MIN(discount)""",

    "customer_retention": """
        SELECT CASE WHEN order_count = 1 THEN 'One-time'
                    WHEN order_count BETWEEN 2 AND 5 THEN 'Repeat (2-5)'
                    WHEN order_count BETWEEN 6 AND 10 THEN 'Loyal (6-10)'
                    ELSE 'VIP (11+)' END AS tier,
               COUNT(*) AS customers, SUM(total_spent) AS revenue
        FROM (SELECT customer_id, COUNT(DISTINCT order_id) AS order_count,
                     SUM(sales) AS total_spent FROM sales_data
              GROUP BY customer_id) t
        GROUP BY 1 ORDER BY MIN(order_count)""",

    "top_loss_products": """
        SELECT product_name, sub_category, SUM(profit) AS total_loss,
               COUNT(*) AS times, ROUND(AVG(discount)::numeric, 2) AS avg_disc
        FROM sales_data WHERE is_loss = 1
        GROUP BY product_name, sub_category
        HAVING COUNT(*) >= 3 ORDER BY total_loss LIMIT 10""",

    "segment_perf": """
        SELECT segment, COUNT(DISTINCT customer_id) AS customers,
               SUM(sales) AS sales, SUM(profit) AS profit,
               ROUND((SUM(profit)/SUM(sales)*100)::numeric, 1) AS margin
        FROM sales_data GROUP BY segment ORDER BY sales DESC""",

    "monthly_trend": """
        SELECT order_year, order_month, SUM(sales) AS sales, SUM(profit) AS profit
        FROM sales_data GROUP BY order_year, order_month ORDER BY order_year, order_month""",

    "ship_mode_perf": """
        SELECT ship_mode, COUNT(*) AS txns, SUM(sales) AS sales,
               SUM(profit) AS profit, AVG(shipping_days) AS avg_days
        FROM sales_data GROUP BY ship_mode ORDER BY sales DESC""",

    "q4_vs_other": """
        SELECT CASE WHEN order_quarter = 4 THEN 'Q4' ELSE 'Q1-Q3' END AS period,
               SUM(sales) AS sales, SUM(profit) AS profit, COUNT(DISTINCT order_id) AS orders
        FROM sales_data GROUP BY 1 ORDER BY period"""
}

for name, sql in queries.items():
    df = pd.read_sql(sql, conn)
    print(f"\n{'='*50}")
    print(f"  {name.upper()}")
    print(f"{'='*50}")
    print(df.to_string(index=False))

conn.close()
