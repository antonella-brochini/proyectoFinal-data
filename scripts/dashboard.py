import os
from urllib.parse import quote_plus
import warnings
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
from dotenv import load_dotenv
from sqlalchemy import create_engine
from datetime import date

warnings.filterwarnings("ignore")

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

# Page config
st.set_page_config(
    page_title="Superstore Sales Dashboard",
    page_icon=":bar_chart:",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Colors
BLUE, GREEN, AMBER, RED, PURPLE, CYAN = "#2563eb", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#06b6d4"
COLORS = [BLUE, AMBER, GREEN, RED, PURPLE, CYAN]

# Custom CSS
st.markdown("""
<style>
    .main { background-color: #f5f5f5; }
    div[data-testid="stMetric"] {
        background: #111111;
        padding: 18px 15px;
        border-radius: 10px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.3);
    }
    div[data-testid="stMetric"] label {
        font-size: 0.85rem;
        color: #aaaaaa !important;
    }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        color: #ffffff !important;
    }
    div[data-testid="stMetric"] div[data-testid="stMetricDelta"] {
        color: #aaaaaa !important;
    }
    /* Green for positive deltas */
    div[data-testid="stMetric"] svg[data-testid="stMetricDeltaIcon"] ~ div {
        color: #10b981 !important;
    }
    div[data-testid="stSidebar"] { background: #1b2838; color: white; }
    div[data-testid="stSidebar"] * { color: white !important; }
    h1 { color: #1b3a5c; }
</style>
""", unsafe_allow_html=True)


# Data Loading
@st.cache_data
def load_data():
    db_name = os.environ.get("DB_NAME", "working_database")
    db_user = os.environ.get("DB_USER", "postgres")
    db_password = os.environ.get("DB_PASSWORD", "your_password_here")
    db_host = os.environ.get("DB_HOST", "localhost")
    db_port = os.environ.get("DB_PORT", "5432")
    sslmode = os.environ.get("DB_SSLMODE", "require")

    connection_url = (
        f"postgresql+psycopg2://{quote_plus(db_user)}:{quote_plus(db_password)}"
        f"@{db_host}:{db_port}/{db_name}?sslmode={sslmode}"
    )
    engine = create_engine(connection_url)
    df = pd.read_sql("SELECT * FROM sales_data", engine)
    df["order_date"] = pd.to_datetime(df["order_date"])
    df["ship_date"] = pd.to_datetime(df["ship_date"])
    return df

df = load_data()


# Sidebar Filters
st.sidebar.markdown("## Filters")
st.sidebar.markdown("---")

# Year filter
years = sorted(df["order_year"].unique())
selected_years = st.sidebar.multiselect("Year", years, default=years)

# Category filter
categories = sorted(df["category"].unique())
selected_categories = st.sidebar.multiselect("Category", categories, default=categories)

# Region filter
regions = sorted(df["region"].unique())
selected_regions = st.sidebar.multiselect("Region", regions, default=regions)

# Segment filter
segments = sorted(df["segment"].unique())
selected_segments = st.sidebar.multiselect("Segment", segments, default=segments)

# Date range
min_date = df["order_date"].min().date()
max_date = df["order_date"].max().date()
date_range = st.sidebar.slider("Date Range", min_value=min_date, max_value=max_date,
                                value=(min_date, max_date))

# Apply filters
mask = (
    df["order_year"].isin(selected_years) &
    df["category"].isin(selected_categories) &
    df["region"].isin(selected_regions) &
    df["segment"].isin(selected_segments) &
    (df["order_date"].dt.date >= date_range[0]) &
    (df["order_date"].dt.date <= date_range[1])
)
fdf = df[mask]  # filtered dataframe

st.sidebar.markdown("---")
st.sidebar.markdown(f"**{len(fdf):,}** transactions | **{fdf['order_id'].nunique():,}** orders")
st.sidebar.markdown(f"Data source: PostgreSQL `sales_data` ({len(df):,} rows)")


# Helper Functions
def kpi_row(data):
    """Render KPI metric cards."""
    total_sales = data["sales"].sum()
    total_profit = data["profit"].sum()
    total_orders = data["order_id"].nunique()
    total_customers = data["customer_id"].nunique()
    avg_order = total_sales / total_orders if total_orders > 0 else 0
    margin = (total_profit / total_sales * 100) if total_sales > 0 else 0
    loss_count = data["is_loss"].sum()

    c1, c2, c3, c4, c5, c6, c7 = st.columns(7)
    c1.metric("Total Sales", f"${total_sales:,.0f}")
    c2.metric("Total Profit", f"${total_profit:,.0f}",
              delta=f"{total_profit/total_sales*100:.1f}% margin" if total_sales > 0 else "0%")
    c3.metric("Total Orders", f"{total_orders:,}")
    c4.metric("Customers", f"{total_customers:,}")
    c5.metric("Avg Order Value", f"${avg_order:,.2f}")
    c6.metric("Profit Margin", f"{margin:.1f}%")
    c7.metric("Loss Transactions", f"{int(loss_count):,}",
              delta=f"{loss_count/len(data)*100:.1f}% loss rate" if len(data) > 0 else "0%",
              delta_color="inverse")


def monthly_agg(data):
    """Aggregate data by year-month."""
    m = data.copy()
    m["ym"] = m["order_date"].dt.to_period("M").astype(str)
    m["ym_date"] = m["order_date"].dt.to_period("M").dt.to_timestamp()
    g = m.groupby(["ym", "ym_date"]).agg(
        revenue=("sales", "sum"), profit=("profit", "sum"),
        orders=("order_id", "nunique"), transactions=("sales", "count")
    ).reset_index().sort_values("ym_date")
    g["margin_pct"] = (g["profit"] / g["revenue"] * 100).round(1)
    g["ma3"] = g["revenue"].rolling(3, min_periods=1).mean()
    g["ma6"] = g["revenue"].rolling(6, min_periods=1).mean()
    return g


# Title
st.markdown("# Superstore Sales Dashboard")
st.markdown("*Performance analytics for FY 2014–2017 | Data source: PostgreSQL working_database*")
st.markdown("---")


# Tab Navigation
tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["Executive Overview", "Sales Trends", "Products", "Customers", "Geography"])


# TAB 1: EXECUTIVE OVERVIEW

with tab1:
    kpi_row(fdf)
    st.markdown("")

    # Row 1: Monthly trend + Category donut
    c1, c2 = st.columns([2, 1])
    with c1:
        mg = monthly_agg(fdf)
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=mg["ym_date"], y=mg["revenue"], mode="lines+markers",
                                  name="Revenue", line=dict(color=BLUE, width=2)))
        fig.add_trace(go.Scatter(x=mg["ym_date"], y=mg["profit"], mode="lines+markers",
                                  name="Profit", line=dict(color=GREEN, width=2)))
        fig.add_trace(go.Scatter(x=mg["ym_date"], y=mg["ma3"], mode="lines",
                                  name="3M Avg", line=dict(color=RED, width=1.5, dash="dash")))
        fig.update_layout(title="Monthly Revenue & Profit Trend", template="plotly_white",
                          height=380, margin=dict(l=20, r=20, t=50, b=20))
        fig.update_yaxes(tickprefix="$", tickformat=".0f")
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        cat_data = fdf.groupby("category")["sales"].sum().reset_index()
        fig = px.pie(cat_data, values="sales", names="category", hole=0.55,
                     color="category", color_discrete_sequence=COLORS[:3])
        fig.update_layout(title="Revenue by Category", template="plotly_white",
                          height=380, margin=dict(l=20, r=20, t=50, b=20),
                          showlegend=False)
        fig.update_traces(textinfo="percent+label", textfont_size=13)
        st.plotly_chart(fig, use_container_width=True)

    # Row 2: Region bar + Segment bar
    c1, c2 = st.columns(2)
    with c1:
        reg = fdf.groupby("region").agg(sales=("sales", "sum"), profit=("profit", "sum")).reset_index()
        reg = reg.sort_values("sales", ascending=True)
        fig = go.Figure()
        fig.add_trace(go.Bar(y=reg["region"], x=reg["sales"], name="Sales",
                             orientation="h", marker_color=BLUE))
        fig.add_trace(go.Bar(y=reg["region"], x=reg["profit"], name="Profit",
                             orientation="h", marker_color=GREEN))
        fig.update_layout(title="Sales vs Profit by Region", template="plotly_white",
                          barmode="group", height=350, margin=dict(l=20, r=20, t=50, b=20))
        fig.update_xaxes(tickprefix="$", tickformat=".0f")
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        seg = fdf.groupby("segment").agg(
            sales=("sales", "sum"), customers=("customer_id", "nunique")).reset_index()
        seg = seg.sort_values("sales", ascending=True)
        fig = go.Figure()
        fig.add_trace(go.Bar(y=seg["segment"], x=seg["sales"], name="Revenue",
                             orientation="h", marker_color=PURPLE,
                             text=seg["sales"].apply(lambda x: f"${x:,.0f}"), textposition="outside"))
        fig.update_layout(title="Revenue by Customer Segment", template="plotly_white",
                          height=350, margin=dict(l=20, r=20, t=50, b=20), showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    # Row 3: Ship mode + Discount impact
    c1, c2 = st.columns(2)
    with c1:
        ship = fdf.groupby("ship_mode").agg(
            txns=("sales", "count"), sales=("sales", "sum"),
            avg_days=("shipping_days", "mean")).reset_index().sort_values("sales", ascending=True)
        fig = px.bar(ship, x="sales", y="ship_mode", orientation="h",
                     color="avg_days", color_continuous_scale="Blues",
                     labels={"sales": "Revenue", "ship_mode": "Ship Mode", "avg_days": "Avg Days"})
        fig.update_layout(title="Revenue by Shipping Mode", template="plotly_white",
                          height=350, margin=dict(l=20, r=20, t=50, b=20))
        fig.update_xaxes(tickprefix="$", tickformat=".0f")
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        disc = fdf.groupby("discount_tier").agg(
            sales=("sales", "sum"), profit=("profit", "sum"),
            loss_rate=("is_loss", "mean")).reset_index()
        disc["loss_rate"] = (disc["loss_rate"] * 100).round(1)
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(go.Bar(x=disc["discount_tier"], y=disc["profit"], name="Profit",
                             marker_color=[GREEN if p >= 0 else RED for p in disc["profit"]]),
                      secondary_y=False)
        fig.add_trace(go.Scatter(x=disc["discount_tier"], y=disc["loss_rate"],
                                  name="Loss Rate %", line=dict(color=RED, width=2)),
                      secondary_y=True)
        fig.update_layout(title="Discount Impact on Profitability", template="plotly_white",
                          height=350, margin=dict(l=20, r=20, t=50, b=20))
        fig.update_yaxes(title_text="Profit ($)", secondary_y=False)
        fig.update_yaxes(title_text="Loss Rate %", secondary_y=True)
        st.plotly_chart(fig, use_container_width=True)



# TAB 2: SALES TRENDS

with tab2:
    mg = monthly_agg(fdf)

    # YoY Growth
    st.markdown("### Year-over-Year Performance")
    yoy = fdf.groupby("order_year").agg(
        revenue=("sales", "sum"), profit=("profit", "sum"),
        orders=("order_id", "nunique")).reset_index()
    yoy["rev_growth"] = yoy["revenue"].pct_change() * 100
    yoy["profit_growth"] = yoy["profit"].pct_change() * 100

    c1, c2, c3, c4 = st.columns(4)
    for i, yr in enumerate(yoy["order_year"]):
        row = yoy[yoy["order_year"] == yr].iloc[0]
        col = [c1, c2, c3, c4][i]
        col.metric(f"{int(yr)}", f"${row['revenue']:,.0f}",
                   delta=f"{row['rev_growth']:.1f}%" if pd.notna(row['rev_growth']) else "—")

    st.markdown("---")

    # Moving averages chart
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=mg["ym_date"], y=mg["revenue"], mode="lines",
                              name="Monthly Revenue", line=dict(color=BLUE, width=1), opacity=0.4,
                              fill="tozeroy", fillcolor="rgba(37,99,235,0.05)"))
    fig.add_trace(go.Scatter(x=mg["ym_date"], y=mg["ma3"], mode="lines",
                              name="3-Month MA", line=dict(color=RED, width=2.5)))
    fig.add_trace(go.Scatter(x=mg["ym_date"], y=mg["ma6"], mode="lines",
                              name="6-Month MA", line=dict(color=AMBER, width=2.5)))
    # Forecast annotation
    fig.update_layout(title="Revenue Trend with Moving Averages", template="plotly_white",
                      height=420, margin=dict(l=20, r=20, t=50, b=20))
    fig.update_yaxes(tickprefix="$", tickformat=".0f")
    st.plotly_chart(fig, use_container_width=True)

    # Dual axis: Revenue bars + Profit margin line
    st.markdown("### Revenue & Profit Margin")
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(x=mg["ym_date"], y=mg["revenue"], name="Revenue",
                         marker_color=BLUE, opacity=0.6), secondary_y=False)
    fig.add_trace(go.Scatter(x=mg["ym_date"], y=mg["margin_pct"], name="Margin %",
                             line=dict(color=GREEN, width=2.5)), secondary_y=True)
    fig.update_layout(template="plotly_white", height=380, margin=dict(l=20, r=20, t=30, b=20))
    fig.update_yaxes(title_text="Revenue ($)", tickprefix="$", secondary_y=False)
    fig.update_yaxes(title_text="Margin %", ticksuffix="%", secondary_y=True)
    st.plotly_chart(fig, use_container_width=True)

    # Seasonality heatmap
    st.markdown("### Seasonality Heatmap (Revenue by Year × Month)")
    heatmap = fdf.groupby(["order_year", "order_month"])["sales"].sum().reset_index()
    pivot = heatmap.pivot_table(index="order_year", columns="order_month", values="sales")
    month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                   "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    fig = go.Figure(go.Heatmap(
        z=pivot.values / 1000, x=month_names, y=[int(y) for y in pivot.index],
        colorscale="YlOrRd", text=np.round(pivot.values / 1000, 1),
        texttemplate="%{text}K", hovertemplate="Year %{y}, %{x}: $%{text}K<extra></extra>"))
    fig.update_layout(title="Monthly Revenue Heatmap ($K)", template="plotly_white",
                      height=320, margin=dict(l=20, r=20, t=50, b=20))
    st.plotly_chart(fig, use_container_width=True)



# TAB 3: PRODUCTS

with tab3:
    prod = fdf.groupby(["product_name", "category", "sub_category"]).agg(
        sales=("sales", "sum"), profit=("profit", "sum"),
        units=("quantity", "sum"), transactions=("sales", "count")
    ).reset_index()

    # Top 10 Products
    c1, c2 = st.columns(2)
    with c1:
        top10 = prod.nlargest(10, "sales")
        fig = px.bar(top10, x="sales", y=top10["product_name"].apply(lambda x: x[:40]),
                     orientation="h", color="category", color_discrete_sequence=COLORS[:3],
                     labels={"sales": "Revenue", "product_name": ""})
        fig.update_layout(title="Top 10 Products by Revenue", template="plotly_white",
                          height=450, margin=dict(l=20, r=40, t=50, b=20), showlegend=False,
                          yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        # Sub-category performance
        subcat = fdf.groupby("sub_category").agg(
            sales=("sales", "sum"), profit=("profit", "sum")).reset_index()
        subcat = subcat.sort_values("profit", ascending=True)
        fig = px.bar(subcat, x="profit", y="sub_category", orientation="h",
                     color="profit", color_continuous_scale=["#ef4444", "#fbbf24", "#10b981"],
                     labels={"profit": "Profit", "sub_category": ""})
        fig.update_layout(title="Profit by Sub-Category", template="plotly_white",
                          height=450, margin=dict(l=20, r=40, t=50, b=20),
                          coloraxis_showscale=False)
        fig.add_vline(x=0, line_color="black", line_width=1)
        st.plotly_chart(fig, use_container_width=True)

    # Product scatter matrix
    st.markdown("### Product Performance Matrix")
    fig = px.scatter(prod, x="sales", y="profit", size="units", color="category",
                     hover_data=["product_name"], color_discrete_sequence=COLORS[:3],
                     labels={"sales": "Total Sales ($)", "profit": "Total Profit ($)"})
    fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
    fig.add_vline(x=prod["sales"].median(), line_dash="dash", line_color="gray", opacity=0.5)
    fig.update_layout(title="Sales vs Profit (bubble size = units sold)", template="plotly_white",
                      height=450, margin=dict(l=20, r=20, t=50, b=20))
    st.plotly_chart(fig, use_container_width=True)

    # Downloadable table
    st.markdown("### Product Data Table")
    st.dataframe(prod.sort_values("sales", ascending=False).head(50),
                 use_container_width=True, height=400)
    st.download_button("Download Product Data (CSV)", prod.to_csv(index=False),
                       "product_analysis.csv", "text/csv")

# TAB 4: CUSTOMERS

with tab4:
    cust = fdf.groupby(["customer_id", "customer_name", "segment"]).agg(
        orders=("order_id", "nunique"), sales=("sales", "sum"),
        profit=("profit", "sum"), first_order=("order_date", "min"),
        last_order=("order_date", "max")
    ).reset_index()
    cust["margin"] = (cust["profit"] / cust["sales"] * 100).round(1)
    cust["avg_order_value"] = (cust["sales"] / cust["orders"]).round(2)

    # Top 10 Customers
    c1, c2 = st.columns(2)
    with c1:
        top_cust = cust.nlargest(10, "sales")
        fig = px.bar(top_cust, x="sales", y="customer_name", orientation="h",
                     color="segment", color_discrete_sequence=COLORS[:3],
                     labels={"sales": "Revenue", "customer_name": ""})
        fig.update_layout(title="Top 10 Customers by Revenue", template="plotly_white",
                          height=450, margin=dict(l=20, r=40, t=50, b=20),
                          yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        # Customer distribution
        fig = go.Figure()
        fig.add_trace(go.Histogram(x=cust["sales"], nbinsx=50, name="Revenue",
                                   marker_color=BLUE, opacity=0.7))
        fig.update_layout(title="Customer Revenue Distribution", template="plotly_white",
                          height=450, margin=dict(l=20, r=20, t=50, b=20),
                          xaxis_title="Total Revenue ($)", yaxis_title="Number of Customers")
        st.plotly_chart(fig, use_container_width=True)

    # Customer frequency vs monetary scatter
    st.markdown("### Customer Frequency vs Monetary Value")
    # Use absolute profit for bubble size (marker size must be non-negative)
    cust["abs_profit"] = cust["profit"].abs().clip(lower=1)
    fig = px.scatter(cust, x="orders", y="sales", size="abs_profit",
                     color="segment", hover_data=["customer_name", "margin", "profit"],
                     color_discrete_sequence=COLORS[:3],
                     labels={"orders": "Number of Orders", "sales": "Total Revenue ($)"})
    fig.update_layout(template="plotly_white", height=450,
                      margin=dict(l=20, r=20, t=30, b=20))
    st.plotly_chart(fig, use_container_width=True)

    # Repeat vs One-time
    st.markdown("### Customer Loyalty Tiers")
    cust["tier"] = pd.cut(cust["orders"], bins=[0, 1, 5, 10, 100],
                          labels=["One-time", "Repeat (2-5)", "Loyal (6-10)", "VIP (11+)"])
    tier_data = cust.groupby("tier", observed=True).agg(
        customers=("customer_id", "count"), revenue=("sales", "sum")).reset_index()
    c1, c2 = st.columns(2)
    with c1:
        fig = px.bar(tier_data, x="tier", y="customers", color="tier",
                     color_discrete_sequence=COLORS[:4])
        fig.update_layout(title="Customer Count by Tier", template="plotly_white",
                          height=350, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        fig = px.bar(tier_data, x="tier", y="revenue", color="tier",
                     color_discrete_sequence=COLORS[:4])
        fig.update_layout(title="Revenue by Customer Tier", template="plotly_white",
                          height=350, showlegend=False)
        fig.update_yaxes(tickprefix="$", tickformat=".0f")
        st.plotly_chart(fig, use_container_width=True)

    # Downloadable table
    st.dataframe(cust.sort_values("sales", ascending=False).head(50),
                 use_container_width=True, height=400)
    st.download_button("Download Customer Data (CSV)", cust.to_csv(index=False),
                       "customer_analysis.csv", "text/csv")



# TAB 5: GEOGRAPHY

with tab5:
    geo = fdf.groupby(["state", "region", "city"]).agg(
        sales=("sales", "sum"), profit=("profit", "sum"),
        orders=("order_id", "nunique"), customers=("customer_id", "nunique")
    ).reset_index()
    geo["margin"] = (geo["profit"] / geo["sales"] * 100).round(1)

    # State map
    st.markdown("### Sales by State")
    state_data = fdf.groupby(["state", "region"]).agg(
        sales=("sales", "sum"), profit=("profit", "sum")).reset_index()

    fig = px.choropleth(state_data, locations=[s[:2].upper() for s in state_data["state"]],
                        locationmode="USA-states", scope="usa", color="sales",
                        color_continuous_scale="Blues", hover_name="state",
                        hover_data={"sales": ":,.0f", "profit": ":,.0f", "region": True},
                        labels={"sales": "Revenue"})
    fig.update_layout(title="Revenue by State", template="plotly_white",
                      height=500, margin=dict(l=20, r=20, t=50, b=20))
    st.plotly_chart(fig, use_container_width=True)

    # Top 15 States
    c1, c2 = st.columns(2)
    with c1:
        top_states = state_data.nlargest(15, "sales")
        fig = px.bar(top_states, x="sales", y="state", orientation="h",
                     color="region", color_discrete_sequence=COLORS[:4],
                     labels={"sales": "Revenue", "state": ""})
        fig.update_layout(title="Top 15 States by Revenue", template="plotly_white",
                          height=500, margin=dict(l=20, r=40, t=50, b=20),
                          yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        # Region breakdown
        reg_data = fdf.groupby(["region", "category"])["sales"].sum().reset_index()
        fig = px.bar(reg_data, x="region", y="sales", color="category",
                     color_discrete_sequence=COLORS[:3], barmode="stack",
                     labels={"sales": "Revenue", "region": "Region"})
        fig.update_layout(title="Revenue by Region & Category", template="plotly_white",
                          height=500, margin=dict(l=20, r=20, t=50, b=20))
        fig.update_yaxes(tickprefix="$", tickformat=".0f")
        st.plotly_chart(fig, use_container_width=True)

    # Profit map
    st.markdown("### Profitability by State")
    fig = px.choropleth(state_data, locations=[s[:2].upper() for s in state_data["state"]],
                        locationmode="USA-states", scope="usa", color="profit",
                        color_continuous_scale="RdYlGn", hover_name="state",
                        hover_data={"profit": ":,.0f", "sales": ":,.0f"},
                        labels={"profit": "Profit"})
    fig.update_layout(title="Profit by State (Green = Profit, Red = Loss)",
                      template="plotly_white", height=500,
                      margin=dict(l=20, r=20, t=50, b=20))
    st.plotly_chart(fig, use_container_width=True)

    # Downloadable table
    st.dataframe(geo.sort_values("sales", ascending=False).head(50),
                 use_container_width=True, height=400)
    st.download_button("Download Geographic Data (CSV)", geo.to_csv(index=False),
                       "geography_analysis.csv", "text/csv")


# Footer
st.markdown("---")
st.markdown(
    f"<div style='text-align:center; color:#999; font-size:0.8rem;'>"
    f"Superstore Sales Dashboard | Data: PostgreSQL working_database "
    f"({len(df):,} transactions, 2014-2017) | Built with Streamlit + Plotly | "
    f"Showing {len(fdf):,} filtered records</div>",
    unsafe_allow_html=True
)