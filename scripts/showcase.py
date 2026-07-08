import os
import sys
import warnings
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')), '.env'))

import numpy as np
import pandas as pd
import psycopg2
import matplotlib
matplotlib.use("Agg")  # non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns

warnings.filterwarnings("ignore")

# Configuration
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
VIZ_DIR = os.path.join(PROJECT_ROOT, "visualizations")
os.makedirs(VIZ_DIR, exist_ok=True)

DB_PARAMS = dict(
    dbname=os.environ.get("DB_NAME", "working_database"),
    user=os.environ.get("DB_USER", "postgres"),
    password=os.environ.get("DB_PASSWORD", "your_password_here"),
    host=os.environ.get("DB_HOST", "localhost"),
    port=os.environ.get("DB_PORT", "5432")
)

# Chart style
sns.set_theme(style="whitegrid", font_scale=1.1)
plt.rcParams["figure.dpi"] = 150
plt.rcParams["savefig.bbox"] = "tight"
plt.rcParams["figure.facecolor"] = "white"

# Colors
PALETTE = ["#2563eb", "#f59e0b", "#10b981", "#ef4444", "#8b5cf6", "#06b6d4"]


def run_query(sql):
    """Execute SQL and return a DataFrame."""
    conn = psycopg2.connect(**DB_PARAMS)
    df = pd.read_sql(sql, conn)
    conn.close()
    return df


def save(fig, name):
    """Save figure to visualizations folder."""
    path = os.path.join(VIZ_DIR, f"{name}.png")
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  Saved: {name}.png")



# 1. Year-over-Year Revenue & Profit Growth

print("Generating charts...")
print("  [1/12] YoY Revenue & Profit")

df = run_query("""
    SELECT order_year AS year,
           SUM(sales) AS revenue,
           SUM(profit) AS profit,
           COUNT(DISTINCT order_id) AS orders
    FROM sales_data GROUP BY order_year ORDER BY order_year
""")

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
ax1.bar(df["year"].astype(str), df["revenue"], color=PALETTE[0], alpha=0.85, label="Revenue")
ax1.bar(df["year"].astype(str), df["profit"], color=PALETTE[2], alpha=0.85, label="Profit")
ax1.set_title("Revenue vs Profit by Year", fontsize=14, fontweight="bold")
ax1.set_xlabel("Year")
ax1.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x/1e3:.0f}K"))
ax1.legend()

ax2.plot(df["year"].astype(str), df["orders"], color=PALETTE[0], marker="o", linewidth=2.5, markersize=8)
ax2.set_title("Total Orders by Year", fontsize=14, fontweight="bold")
ax2.set_xlabel("Year")
for i, v in enumerate(df["orders"]):
    ax2.annotate(f"{v:,}", (df["year"].astype(str)[i], v), textcoords="offset points",
                 xytext=(0, 10), ha="center", fontsize=10, fontweight="bold")
plt.tight_layout()
save(fig, "01_yoy_revenue_profit")



# 2. Monthly Revenue Trend (with moving average)

print("  [2/12] Monthly Trend")

df = run_query("""
    WITH monthly AS (
        SELECT order_year, order_month, SUM(sales) AS revenue
        FROM sales_data GROUP BY order_year, order_month
    )
    SELECT TO_CHAR(MAKE_DATE(order_year, order_month, 1), 'Mon YYYY') AS month_label,
           revenue,
           AVG(revenue) OVER (ORDER BY order_year, order_month
                              ROWS BETWEEN 2 PRECEDING AND CURRENT ROW) AS ma3,
           order_year, order_month
    FROM monthly ORDER BY order_year, order_month
""")

fig, ax = plt.subplots(figsize=(16, 6))
ax.plot(range(len(df)), df["revenue"], color=PALETTE[0], alpha=0.5, linewidth=1, label="Monthly")
ax.plot(range(len(df)), df["ma3"], color=PALETTE[3], linewidth=2.5, label="3-Month Avg")
ax.fill_between(range(len(df)), df["revenue"], alpha=0.1, color=PALETTE[0])
tick_pos = range(0, len(df), 3)
ax.set_xticks(list(tick_pos))
ax.set_xticklabels([df.iloc[i]["month_label"] for i in tick_pos], rotation=45, ha="right")
ax.set_title("Monthly Revenue Trend", fontsize=14, fontweight="bold")
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x/1e3:.0f}K"))
ax.legend()
plt.tight_layout()
save(fig, "02_monthly_trend")



# 3. Sales by Region (pie + bar)

print("  [3/12] Regional Sales")

df = run_query("""
    SELECT region, SUM(sales) AS sales, SUM(profit) AS profit,
           COUNT(DISTINCT order_id) AS orders
    FROM sales_data GROUP BY region ORDER BY sales DESC
""")

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
ax1.pie(df["sales"], labels=df["region"], autopct="%1.1f%%",
        colors=PALETTE[:4], startangle=90, textprops={"fontsize": 11})
ax1.set_title("Revenue Share by Region", fontsize=14, fontweight="bold")

bars = ax2.barh(df["region"][::-1], df["profit"][::-1], color=[PALETTE[2] if p > 0 else PALETTE[3] for p in df["profit"][::-1]])
ax2.set_title("Profit by Region", fontsize=14, fontweight="bold")
ax2.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x/1e3:.0f}K"))
for bar, val in zip(bars, df["profit"][::-1]):
    ax2.text(bar.get_width() + 1000, bar.get_y() + bar.get_height()/2,
             f"${val:,.0f}", va="center", fontsize=10)
plt.tight_layout()
save(fig, "03_regional_sales")



# 4. Top 10 States by Revenue

print("  [4/12] Top States")

df = run_query("""
    SELECT state, region, SUM(sales) AS sales, SUM(profit) AS profit
    FROM sales_data GROUP BY state, region ORDER BY sales DESC LIMIT 10
""")

fig, ax = plt.subplots(figsize=(12, 6))
bars = ax.barh(range(len(df)-1, -1, -1), df["sales"], color=PALETTE[0], alpha=0.85)
ax.set_yticks(range(len(df)-1, -1, -1))
ax.set_yticklabels([f"{s} ({r})" for s, r in zip(df["state"], df["region"])])
ax.set_title("Top 10 States by Revenue", fontsize=14, fontweight="bold")
ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x/1e3:.0f}K"))
for bar, val in zip(bars, df["sales"]):
    ax.text(bar.get_width() + 1000, bar.get_y() + bar.get_height()/2,
            f"${val:,.0f}", va="center", fontsize=9)
plt.tight_layout()
save(fig, "04_top_states")



# 5. Category & Sub-Category Performance

print("  [5/12] Category Performance")

df = run_query("""
    SELECT category, sub_category, SUM(sales) AS sales, SUM(profit) AS profit,
           ROUND(AVG(profit_margin), 1) AS avg_margin
    FROM sales_data GROUP BY category, sub_category ORDER BY sales DESC
""")

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7))

# Sub-category sales
colors = [PALETTE[2] if p >= 0 else PALETTE[3] for p in df["profit"]]
ax1.barh(range(len(df)-1, -1, -1), df["sales"], color=colors, alpha=0.85)
ax1.set_yticks(range(len(df)-1, -1, -1))
ax1.set_yticklabels([f"{sc} ({c})" for c, sc in zip(df["category"], df["sub_category"])], fontsize=9)
ax1.set_title("Sales by Sub-Category (green=profit, red=loss)", fontsize=13, fontweight="bold")
ax1.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x/1e3:.0f}K"))

# Category summary
cat_df = df.groupby("category").agg(sales=("sales", "sum"), profit=("profit", "sum")).reset_index()
x = np.arange(len(cat_df))
w = 0.35
ax2.bar(x - w/2, cat_df["sales"], w, color=PALETTE[0], label="Sales")
ax2.bar(x + w/2, cat_df["profit"], w, color=PALETTE[2], label="Profit")
ax2.set_xticks(x)
ax2.set_xticklabels(cat_df["category"])
ax2.set_title("Sales vs Profit by Category", fontsize=13, fontweight="bold")
ax2.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x/1e3:.0f}K"))
ax2.legend()
plt.tight_layout()
save(fig, "05_category_performance")



# 6. Top 10 Products by Revenue

print("  [6/12] Top Products")

df = run_query("""
    SELECT LEFT(product_name, 45) AS product_name, category,
           SUM(sales) AS revenue, SUM(profit) AS profit
    FROM sales_data GROUP BY product_name, category
    ORDER BY revenue DESC LIMIT 10
""")

fig, ax = plt.subplots(figsize=(14, 6))
bars = ax.barh(range(len(df)-1, -1, -1), df["revenue"], color=PALETTE[0], alpha=0.85)
ax.set_yticks(range(len(df)-1, -1, -1))
ax.set_yticklabels(df["product_name"], fontsize=9)
ax.set_title("Top 10 Products by Revenue", fontsize=14, fontweight="bold")
ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x/1e3:.0f}K"))
for bar, val in zip(bars, df["revenue"]):
    ax.text(bar.get_width() + 500, bar.get_y() + bar.get_height()/2,
            f"${val:,.0f}", va="center", fontsize=9)
plt.tight_layout()
save(fig, "06_top_products")



# 7. Worst 10 Products (Loss Makers)

print("  [7/12] Worst Products")

df = run_query("""
    SELECT LEFT(product_name, 45) AS product_name,
           SUM(profit) AS total_loss, AVG(discount) AS avg_discount
    FROM sales_data GROUP BY product_name
    HAVING SUM(profit) < 0 ORDER BY total_loss ASC LIMIT 10
""")

fig, ax = plt.subplots(figsize=(14, 6))
bars = ax.barh(range(len(df)-1, -1, -1), df["total_loss"], color=PALETTE[3], alpha=0.85)
ax.set_yticks(range(len(df)-1, -1, -1))
ax.set_yticklabels(df["product_name"], fontsize=9)
ax.set_title("10 Biggest Loss-Making Products", fontsize=14, fontweight="bold", color=PALETTE[3])
ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:,.0f}"))
ax.axvline(x=0, color="black", linewidth=0.8)
plt.tight_layout()
save(fig, "07_worst_products")



# 8. Customer Segments

print("  [8/12] Customer Segments")

df = run_query("""
    SELECT segment, COUNT(DISTINCT customer_id) AS customers,
           SUM(sales) AS sales, SUM(profit) AS profit
    FROM sales_data GROUP BY segment ORDER BY sales DESC
""")

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
ax1.pie(df["sales"], labels=df["segment"], autopct="%1.1f%%",
        colors=PALETTE[:3], startangle=90, textprops={"fontsize": 11})
ax1.set_title("Revenue by Customer Segment", fontsize=14, fontweight="bold")

x = np.arange(len(df))
ax2.bar(x, df["customers"], color=PALETTE[4], alpha=0.85)
ax2.set_xticks(x)
ax2.set_xticklabels(df["segment"])
ax2.set_title("Number of Customers by Segment", fontsize=14, fontweight="bold")
for i, v in enumerate(df["customers"]):
    ax2.text(i, v + 5, str(v), ha="center", fontweight="bold")
plt.tight_layout()
save(fig, "08_customer_segments")



# 9. Discount Impact on Profitability

print("  [9/12] Discount Impact")

df = run_query("""
    SELECT discount_tier, COUNT(*) AS txns, SUM(profit) AS profit,
           ROUND(AVG(profit_margin), 1) AS avg_margin,
           SUM(is_loss) AS losses
    FROM sales_data GROUP BY discount_tier ORDER BY MIN(discount)
""")

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
colors = [PALETTE[2] if p >= 0 else PALETTE[3] for p in df["profit"]]
ax1.bar(df["discount_tier"], df["profit"], color=colors, alpha=0.85)
ax1.set_title("Total Profit by Discount Tier", fontsize=14, fontweight="bold")
ax1.set_ylabel("Profit ($)")
ax1.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x/1e3:.0f}K"))
ax1.tick_params(axis="x", rotation=30)

ax2.bar(df["discount_tier"], df["losses"], color=PALETTE[3], alpha=0.85)
ax2.set_title("Loss Transactions by Discount Tier", fontsize=14, fontweight="bold")
ax2.set_ylabel("Number of Losses")
ax2.tick_params(axis="x", rotation=30)
plt.tight_layout()
save(fig, "09_discount_impact")



# 10. Shipping Performance

print("  [10/12] Shipping Performance")

df = run_query("""
    SELECT ship_mode, COUNT(*) AS shipments, AVG(shipping_days) AS avg_days,
           SUM(sales) AS sales
    FROM sales_data GROUP BY ship_mode ORDER BY avg_days
""")

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
ax1.bar(df["ship_mode"], df["avg_days"], color=PALETTE[4], alpha=0.85)
ax1.set_title("Avg Shipping Days by Mode", fontsize=14, fontweight="bold")
ax1.set_ylabel("Days")
for i, v in enumerate(df["avg_days"]):
    ax1.text(i, v + 0.1, f"{v:.1f}", ha="center", fontweight="bold")

ax2.barh(df["ship_mode"][::-1], df["sales"][::-1], color=PALETTE[0], alpha=0.85)
ax2.set_title("Revenue by Shipping Mode", fontsize=14, fontweight="bold")
ax2.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x/1e3:.0f}K"))
plt.tight_layout()
save(fig, "10_shipping_performance")



# 11. Seasonality Heatmap

print("  [11/12] Seasonality Heatmap")

df = run_query("""
    SELECT order_year,
           SUM(CASE WHEN order_month=1  THEN sales ELSE 0 END) AS Jan,
           SUM(CASE WHEN order_month=2  THEN sales ELSE 0 END) AS Feb,
           SUM(CASE WHEN order_month=3  THEN sales ELSE 0 END) AS Mar,
           SUM(CASE WHEN order_month=4  THEN sales ELSE 0 END) AS Apr,
           SUM(CASE WHEN order_month=5  THEN sales ELSE 0 END) AS May,
           SUM(CASE WHEN order_month=6  THEN sales ELSE 0 END) AS Jun,
           SUM(CASE WHEN order_month=7  THEN sales ELSE 0 END) AS Jul,
           SUM(CASE WHEN order_month=8  THEN sales ELSE 0 END) AS Aug,
           SUM(CASE WHEN order_month=9  THEN sales ELSE 0 END) AS Sep,
           SUM(CASE WHEN order_month=10 THEN sales ELSE 0 END) AS Oct,
           SUM(CASE WHEN order_month=11 THEN sales ELSE 0 END) AS Nov,
           SUM(CASE WHEN order_month=12 THEN sales ELSE 0 END) AS Dec
    FROM sales_data GROUP BY order_year ORDER BY order_year
""")

df = df.set_index("order_year")
df = df / 1000  # to thousands

fig, ax = plt.subplots(figsize=(14, 5))
sns.heatmap(df, annot=True, fmt=".0f", cmap="YlOrRd", linewidths=1,
            ax=ax, cbar_kws={"label": "Revenue ($K)"})
ax.set_title("Monthly Revenue Heatmap by Year ($K)", fontsize=14, fontweight="bold")
ax.set_ylabel("")
plt.tight_layout()
save(fig, "11_seasonality_heatmap")



# 12. Executive Dashboard (combined KPIs)

print("  [12/12] Executive Dashboard")

kpi = run_query("""
    SELECT
        COUNT(DISTINCT order_id) AS total_orders,
        COUNT(DISTINCT customer_id) AS customers,
        ROUND(SUM(sales)) AS revenue,
        ROUND(SUM(profit)) AS profit,
        ROUND((SUM(profit)/NULLIF(SUM(sales),0)*100)::NUMERIC, 1) AS margin,
        ROUND(AVG(sales)::NUMERIC, 2) AS avg_order,
        SUM(is_loss) AS losses,
        ROUND((SUM(is_loss)::NUMERIC/COUNT(*)*100), 1) AS loss_rate
    FROM sales_data
""")

fig, axes = plt.subplots(2, 4, figsize=(18, 8))
fig.suptitle("EXECUTIVE DASHBOARD — Superstore Sales (2014-2017)",
             fontsize=18, fontweight="bold", y=0.98)

kpis = [
    ("Total Revenue", f"${kpi['revenue'].iloc[0]:,.0f}", PALETTE[0]),
    ("Total Profit", f"${kpi['profit'].iloc[0]:,.0f}", PALETTE[2]),
    ("Profit Margin", f"{kpi['margin'].iloc[0]}%", PALETTE[4]),
    ("Total Orders", f"{kpi['total_orders'].iloc[0]:,}", PALETTE[0]),
    ("Avg Order Value", f"${kpi['avg_order'].iloc[0]:,.2f}", PALETTE[5]),
    ("Customers", f"{kpi['customers'].iloc[0]:,}", PALETTE[4]),
    ("Loss Transactions", f"{kpi['losses'].iloc[0]:,}", PALETTE[3]),
    ("Loss Rate", f"{kpi['loss_rate'].iloc[0]}%", PALETTE[3]),
]

for ax, (label, value, color) in zip(axes.flat, kpis):
    ax.text(0.5, 0.65, value, transform=ax.transAxes, ha="center", va="center",
            fontsize=28, fontweight="bold", color=color)
    ax.text(0.5, 0.25, label, transform=ax.transAxes, ha="center", va="center",
            fontsize=13, color="#555555")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.patch.set_facecolor("#f8f9fa")
    ax.patch.set_alpha(0.7)

plt.tight_layout(rect=[0, 0, 1, 0.95])
save(fig, "12_executive_dashboard")


print(f"\nAll charts saved to: {VIZ_DIR}/")
print(f"Total: 12 visualization files generated.")
