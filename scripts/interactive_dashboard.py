import os
import warnings
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

warnings.filterwarnings("ignore")

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_PATH = os.path.join(PROJECT_ROOT, "data", "processed", "clean_data.csv")
OUT_DIR = os.path.join(PROJECT_ROOT, "visualizations", "advanced")
os.makedirs(OUT_DIR, exist_ok=True)

print("Loading data...")
df = pd.read_csv(DATA_PATH, encoding="utf-8")
df.columns = [c.strip().replace(" ", "_").replace("-", "_").lower() for c in df.columns]
df["order_date"] = pd.to_datetime(df["order_date"])
df["ship_date"] = pd.to_datetime(df["ship_date"])
df["year_month"] = df["order_date"].dt.to_period("M").astype(str)
print(f"Loaded {len(df):,} rows\n")

COLORS = ["#2563eb", "#f59e0b", "#10b981", "#ef4444", "#8b5cf6", "#06b6d4"]
TEMPLATE = "plotly_white"


# Dashboard 1: Sales & Revenue Overview

print("Generating Dashboard 1: Sales & Revenue Overview...")

monthly = df.groupby("year_month").agg(
    revenue=("sales", "sum"), profit=("profit", "sum"),
    orders=("order_id", "nunique"), transactions=("sales", "count")
).reset_index()

fig1 = make_subplots(rows=2, cols=2,
    subplot_titles=("Monthly Revenue Trend", "Revenue by Region",
                    "Revenue by Category Over Time", "Discount Impact on Profit"),
    specs=[[{"type": "scatter"}, {"type": "pie"}],
           [{"type": "bar"}, {"type": "scatter"}]])

# Monthly trend
fig1.add_trace(go.Scatter(x=monthly["year_month"], y=monthly["revenue"],
    mode="lines+markers", name="Revenue", line=dict(color=COLORS[0], width=2),
    marker=dict(size=5)), row=1, col=1)
fig1.add_trace(go.Scatter(x=monthly["year_month"], y=monthly["profit"],
    mode="lines+markers", name="Profit", line=dict(color=COLORS[2], width=2),
    marker=dict(size=5)), row=1, col=1)

# Revenue by region
region_data = df.groupby("region")["sales"].sum().reset_index()
fig1.add_trace(go.Pie(labels=region_data["region"], values=region_data["sales"],
    marker=dict(colors=COLORS[:4]), hole=0.4, textinfo="label+percent"), row=1, col=2)

# Revenue by category over time
cat_monthly = df.groupby(["year_month", "category"])["sales"].sum().reset_index()
for i, cat in enumerate(df["category"].unique()):
    cat_df = cat_monthly[cat_monthly["category"] == cat]
    fig1.add_trace(go.Bar(x=cat_df["year_month"], y=cat_df["sales"],
        name=cat, marker_color=COLORS[i]), row=2, col=1)

# Discount vs profit
disc_data = df.groupby("discount").agg(avg_profit=("profit", "mean"), count=("sales", "count")).reset_index()
fig1.add_trace(go.Scatter(x=disc_data["discount"] * 100, y=disc_data["avg_profit"],
    mode="markers+lines", name="Avg Profit", marker=dict(size=disc_data["count"] / 20, color=COLORS[3]),
    line=dict(color=COLORS[3], width=2)), row=2, col=2)

fig1.update_layout(height=900, title_text="Sales & Revenue Dashboard", template=TEMPLATE,
    title_font_size=20, showlegend=True)
fig1.write_html(os.path.join(OUT_DIR, "dashboard_sales.html"))
print("  Saved: dashboard_sales.html")



# Dashboard 2: Customer Analytics

print("Generating Dashboard 2: Customer Analytics...")

snapshot = df["order_date"].max() + pd.Timedelta(days=1)
rfm = df.groupby("customer_id").agg(
    recency=("order_date", lambda x: (snapshot - x.max()).days),
    frequency=("order_id", "nunique"),
    monetary=("sales", "sum")
).reset_index()

# Add customer name
cust_names = df[["customer_id", "customer_name"]].drop_duplicates()
rfm = rfm.merge(cust_names, on="customer_id")

fig2 = make_subplots(rows=2, cols=2,
    subplot_titles=("Customer RFM Scatter (Frequency vs Monetary)", "Customer Segments by Revenue",
                    "Order Frequency Distribution", "Customer Revenue Distribution"),
    specs=[[{"type": "scatter"}, {"type": "bar"}],
           [{"type": "histogram"}, {"type": "histogram"}]])

fig2.add_trace(go.Scatter(x=rfm["frequency"], y=rfm["monetary"], mode="markers",
    marker=dict(size=8, color=rfm["recency"], colorscale="RdYlGn", showscale=True,
                colorbar=dict(title="Recency (days)")),
    text=rfm["customer_name"], hovertemplate="%{text}<br>Freq: %{x}<br>Monetary: $%{y:,.0f}<extra></extra>"),
    row=1, col=1)

seg_revenue = df.groupby("segment").agg(
    revenue=("sales", "sum"), customers=("customer_id", "nunique")
).reset_index().sort_values("revenue", ascending=True)
fig2.add_trace(go.Bar(x=seg_revenue["revenue"], y=seg_revenue["segment"],
    orientation="h", marker_color=COLORS[:3],
    text=seg_revenue["revenue"].apply(lambda x: f"${x:,.0f}"), textposition="outside"),
    row=1, col=2)

fig2.add_trace(go.Histogram(x=rfm["frequency"], nbinsx=30, marker_color=COLORS[0], name="Frequency"),
    row=2, col=1)
fig2.add_trace(go.Histogram(x=rfm["monetary"], nbinsx=50, marker_color=COLORS[2], name="Monetary"),
    row=2, col=2)

fig2.update_layout(height=900, title_text="Customer Analytics Dashboard", template=TEMPLATE,
    title_font_size=20, showlegend=False)
fig2.write_html(os.path.join(OUT_DIR, "dashboard_customers.html"))
print("  Saved: dashboard_customers.html")



# Dashboard 3: Product & Profitability

print("Generating Dashboard 3: Product & Profitability...")

prod = df.groupby(["product_name", "category", "sub_category"]).agg(
    total_sales=("sales", "sum"), total_profit=("profit", "sum"),
    units_sold=("quantity", "sum"), avg_discount=("discount", "mean")
).reset_index()

fig3 = make_subplots(rows=2, cols=2,
    subplot_titles=("Top 15 Products by Revenue", "Profit by Sub-Category",
                    "Category Performance (Treemap)", "Profit Margin Distribution"),
    specs=[[{"type": "bar"}, {"type": "bar"}],
           [{"type": "treemap"}, {"type": "histogram"}]])

top15 = prod.nlargest(15, "total_sales")
fig3.add_trace(go.Bar(x=top15["total_sales"], y=top15["product_name"].apply(lambda x: x[:40]),
    orientation="h", marker_color=COLORS[0], name="Revenue",
    text=top15["total_sales"].apply(lambda x: f"${x:,.0f}"), textposition="outside"),
    row=1, col=1)

sub_cat = df.groupby("sub_category")["profit"].sum().sort_values().reset_index()
colors_bar = [COLORS[2] if v >= 0 else COLORS[3] for v in sub_cat["profit"]]
fig3.add_trace(go.Bar(x=sub_cat["profit"], y=sub_cat["sub_category"],
    orientation="h", marker_color=colors_bar, name="Profit"),
    row=1, col=2)

fig3.add_trace(go.Treemap(labels=prod["sub_category"], parents=prod["category"],
    values=prod["total_sales"], marker=dict(colors=COLORS)),
    row=2, col=1)

margin_data = df["profit_margin"].clip(-100, 100)
fig3.add_trace(go.Histogram(x=margin_data, nbinsx=60, marker_color=COLORS[4], name="Margin %"),
    row=2, col=2)

fig3.update_layout(height=900, title_text="Product & Profitability Dashboard", template=TEMPLATE,
    title_font_size=20, showlegend=False)
fig3.write_html(os.path.join(OUT_DIR, "dashboard_products.html"))
print("  Saved: dashboard_products.html")



# Dashboard 4: Geographic & Time Analysis

print("Generating Dashboard 4: Geographic & Time Analysis...")

state_data = df.groupby(["state", "region"]).agg(
    revenue=("sales", "sum"), profit=("profit", "sum"),
    orders=("order_id", "nunique")
).reset_index()

fig4 = make_subplots(rows=2, cols=2,
    subplot_titles=("Revenue by State (Top 20)", "Revenue Heatmap: Year x Month",
                    "Shipping Days by Region", "Day-of-Week Sales Pattern"),
    specs=[[{"type": "bar"}, {"type": "heatmap"}],
           [{"type": "bar"}, {"type": "scatter"}]])

top20_states = state_data.nlargest(20, "revenue")
fig4.add_trace(go.Bar(x=top20_states["revenue"], y=top20_states["state"],
    orientation="h", marker_color=COLORS[0],
    text=top20_states["revenue"].apply(lambda x: f"${x:,.0f}"), textposition="outside"),
    row=1, col=1)

# Heatmap
heatmap_data = df.groupby(["order_year", "order_month"])["sales"].sum().reset_index()
pivot = heatmap_data.pivot_table(index="order_year", columns="order_month", values="sales")
fig4.add_trace(go.Heatmap(z=pivot.values, x=[f"M{m}" for m in pivot.columns],
    y=pivot.index.tolist(), colorscale="YlOrRd", text=np.round(pivot.values / 1000, 0),
    texttemplate="%{text}K"), row=1, col=2)

# Shipping by region
ship_region = df.groupby("region")["shipping_days"].mean().sort_values().reset_index()
fig4.add_trace(go.Bar(x=ship_region["region"], y=ship_region["shipping_days"],
    marker_color=COLORS[4], name="Avg Shipping Days"), row=2, col=1)

# Day of week pattern
dow = df.groupby("order_dayname").agg(
    revenue=("sales", "sum"), orders=("order_id", "nunique")
).reset_index()
day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
dow["order"] = dow["order_dayname"].map({d: i for i, d in enumerate(day_order)})
dow = dow.sort_values("order")
fig4.add_trace(go.Scatter(x=dow["order_dayname"], y=dow["revenue"],
    mode="lines+markers", line=dict(color=COLORS[1], width=3), marker=dict(size=10)),
    row=2, col=2)

fig4.update_layout(height=900, title_text="Geographic & Temporal Dashboard", template=TEMPLATE,
    title_font_size=20, showlegend=False)
fig4.write_html(os.path.join(OUT_DIR, "dashboard_geotemporal.html"))
print("  Saved: dashboard_geotemporal.html")


print(f"\nAll 4 interactive dashboards saved to: {OUT_DIR}/")
print("Open the .html files in your browser to interact with the charts.")
