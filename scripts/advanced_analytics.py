import os
import warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
from scipy import stats
from scipy.stats import ttest_ind, mannwhitneyu, shapiro
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler, RobustScaler
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import TimeSeriesSplit
from statsmodels.tsa.seasonal import seasonal_decompose
from statsmodels.tsa.holtwinters import ExponentialSmoothing

warnings.filterwarnings("ignore")

# Configuration
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_PATH = os.path.join(PROJECT_ROOT, "data", "processed", "clean_data.csv")
VIZ_DIR = os.path.join(PROJECT_ROOT, "visualizations", "advanced")
os.makedirs(VIZ_DIR, exist_ok=True)

# Style
sns.set_theme(style="whitegrid", font_scale=1.1)
plt.rcParams.update({"figure.dpi": 150, "savefig.bbox": "tight", "figure.facecolor": "white"})
PAL = ["#2563eb", "#f59e0b", "#10b981", "#ef4444", "#8b5cf6", "#06b6d4", "#ec4899", "#84cc16"]


def save(fig, name):
    fig.savefig(os.path.join(VIZ_DIR, f"{name}.png"), dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  Saved: {name}.png")


# Load data
print("Loading data...")
df = pd.read_csv(DATA_PATH, encoding="utf-8")
# Standardize column names to snake_case
df.columns = [c.strip().replace(" ", "_").replace("-", "_").lower() for c in df.columns]
df["order_date"] = pd.to_datetime(df["order_date"])
df["ship_date"] = pd.to_datetime(df["ship_date"])
df["order_yearmonth"] = df["order_date"].dt.to_period("M")
print(f"Loaded {len(df):,} rows\n")



# SECTION 1: TREND ANALYSIS

print("=" * 60)
print("SECTION 1: TREND ANALYSIS")
print("=" * 60)

# 1.1 Monthly time series preparation
monthly = df.groupby("order_yearmonth").agg(
    revenue=("sales", "sum"),
    profit=("profit", "sum"),
    orders=("order_id", "nunique"),
    transactions=("sales", "count")
).reset_index()
monthly["date"] = monthly["order_yearmonth"].dt.to_timestamp()
monthly = monthly.sort_values("date").reset_index(drop=True)

# 1.2 Time Series Decomposition
print("  1.2 Time Series Decomposition")
decomp = seasonal_decompose(monthly["revenue"], model="additive", period=12)

fig, axes = plt.subplots(4, 1, figsize=(14, 10), sharex=True)
fig.suptitle("Time Series Decomposition — Monthly Revenue", fontsize=15, fontweight="bold")
axes[0].plot(monthly["date"], decomp.observed, color=PAL[0], linewidth=1.5)
axes[0].set_ylabel("Observed")
axes[1].plot(monthly["date"], decomp.trend, color=PAL[3], linewidth=2)
axes[1].set_ylabel("Trend")
axes[2].plot(monthly["date"], decomp.seasonal, color=PAL[2], linewidth=1)
axes[2].set_ylabel("Seasonal")
axes[3].plot(monthly["date"], decomp.resid, color=PAL[4], linewidth=0.8, alpha=0.7)
axes[3].axhline(0, color="black", linewidth=0.5)
axes[3].set_ylabel("Residual")
plt.tight_layout()
save(fig, "01_time_series_decomposition")

# 1.3 Moving Averages + Momentum
print("  1.3 Moving Averages & Momentum")
monthly["MA3"] = monthly["revenue"].rolling(3).mean()
monthly["MA6"] = monthly["revenue"].rolling(6).mean()
monthly["MA12"] = monthly["revenue"].rolling(12).mean()
monthly["momentum"] = monthly["revenue"].diff()

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 9))
ax1.plot(monthly["date"], monthly["revenue"], color=PAL[0], alpha=0.4, linewidth=1, label="Actual")
ax1.plot(monthly["date"], monthly["MA3"], color=PAL[3], linewidth=2, label="3-Month MA")
ax1.plot(monthly["date"], monthly["MA6"], color=PAL[1], linewidth=2, label="6-Month MA")
ax1.plot(monthly["date"], monthly["MA12"], color=PAL[4], linewidth=2.5, label="12-Month MA")
ax1.set_title("Revenue with Moving Averages", fontsize=14, fontweight="bold")
ax1.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x/1e3:.0f}K"))
ax1.legend()

colors = [PAL[2] if m >= 0 else PAL[3] for m in monthly["momentum"].fillna(0)]
ax2.bar(monthly["date"], monthly["momentum"], color=colors, alpha=0.8, width=25)
ax2.axhline(0, color="black", linewidth=0.8)
ax2.set_title("Revenue Momentum (Month-over-Month Change)", fontsize=14, fontweight="bold")
ax2.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x/1e3:.0f}K"))
plt.tight_layout()
save(fig, "02_moving_averages_momentum")

# 1.4 YoY and MoM Growth with Confidence Intervals
print("  1.4 Growth Rates with Confidence Intervals")
monthly["yoy_growth"] = monthly["revenue"].pct_change(12) * 100
monthly["mom_growth"] = monthly["revenue"].pct_change(1) * 100
yoy_mean = monthly["yoy_growth"].dropna().mean()
yoy_ci = stats.t.interval(0.95, len(monthly["yoy_growth"].dropna()) - 1,
                           loc=yoy_mean, scale=stats.sem(monthly["yoy_growth"].dropna()))

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
ax1.bar(monthly["date"].iloc[12:], monthly["yoy_growth"].iloc[12:],
        color=[PAL[2] if g >= 0 else PAL[3] for g in monthly["yoy_growth"].iloc[12:]], alpha=0.85, width=25)
ax1.axhline(yoy_mean, color=PAL[4], linewidth=2, linestyle="--", label=f"Mean: {yoy_mean:.1f}%")
ax1.axhspan(yoy_ci[0], yoy_ci[1], alpha=0.15, color=PAL[4], label=f"95% CI: [{yoy_ci[0]:.1f}%, {yoy_ci[1]:.1f}%]")
ax1.set_title("Year-over-Year Revenue Growth", fontsize=13, fontweight="bold")
ax1.set_ylabel("Growth %")
ax1.legend(fontsize=9)

ax2.bar(monthly["date"].iloc[1:], monthly["mom_growth"].iloc[1:],
        color=[PAL[2] if g >= 0 else PAL[3] for g in monthly["mom_growth"].iloc[1:]], alpha=0.85, width=25)
ax2.axhline(0, color="black", linewidth=0.8)
ax2.set_title("Month-over-Month Revenue Growth", fontsize=13, fontweight="bold")
ax2.set_ylabel("Growth %")
plt.tight_layout()
save(fig, "03_growth_rates")

# 1.5 Exponential Smoothing Forecast
print("  1.5 Sales Forecasting (Holt-Winters)")
monthly_ts = monthly.set_index("date")["revenue"].asfreq("MS")
monthly_ts = monthly_ts.interpolate()

model = ExponentialSmoothing(monthly_ts, trend="add", seasonal="add", seasonal_periods=12)
fit = model.fit(optimized=True)
forecast = fit.forecast(12)

fig, ax = plt.subplots(figsize=(14, 6))
ax.plot(monthly_ts.index, monthly_ts.values, color=PAL[0], linewidth=1.5, label="Historical")
ax.plot(forecast.index, forecast.values, color=PAL[3], linewidth=2.5, linestyle="--", label="12-Month Forecast")
ax.fill_between(forecast.index, forecast.values * 0.85, forecast.values * 1.15,
                alpha=0.15, color=PAL[3], label="±15% Confidence Band")
ax.set_title("Revenue Forecast — Holt-Winters Exponential Smoothing", fontsize=14, fontweight="bold")
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x/1e3:.0f}K"))
ax.legend()
plt.tight_layout()
save(fig, "04_forecast_holt_winters")



# SECTION 2: CUSTOMER SEGMENTATION

print("\n" + "=" * 60)
print("SECTION 2: CUSTOMER SEGMENTATION")
print("=" * 60)

# 2.1 RFM Analysis
print("  2.1 RFM Analysis")
snapshot = df["order_date"].max() + pd.Timedelta(days=1)
rfm = df.groupby("customer_id").agg(
    recency=("order_date", lambda x: (snapshot - x.max()).days),
    frequency=("order_id", "nunique"),
    monetary=("sales", "sum")
).reset_index()

rfm["R_quartile"] = pd.qcut(rfm["recency"], 4, labels=["4-Best", "3", "2", "1-Worst"])
rfm["F_quartile"] = pd.qcut(rfm["frequency"].rank(method="first"), 4, labels=["1-Worst", "2", "3", "4-Best"])
rfm["M_quartile"] = pd.qcut(rfm["monetary"].rank(method="first"), 4, labels=["1-Worst", "2", "3", "4-Best"])


def rfm_segment(row):
    r, f, m = row["R_quartile"], row["F_quartile"], row["M_quartile"]
    if r in ["4-Best", "3"] and f in ["4-Best", "3"] and m in ["4-Best", "3"]:
        return "Champions"
    elif r in ["4-Best", "3"] and f in ["1-Worst", "2"]:
        return "New Customers"
    elif r in ["1-Worst", "2"] and f in ["4-Best", "3"]:
        return "At Risk"
    elif r in ["1-Worst", "2"] and f in ["1-Worst", "2"]:
        return "Lost"
    else:
        return "Potential Loyalists"


rfm["segment"] = rfm.apply(rfm_segment, axis=1)
seg_counts = rfm["segment"].value_counts()

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
wedges, texts, autotexts = ax1.pie(seg_counts.values, labels=seg_counts.index,
                                    autopct="%1.1f%%", colors=PAL[:5], startangle=90, textprops={"fontsize": 10})
ax1.set_title("RFM Customer Segments", fontsize=14, fontweight="bold")

seg_revenue = rfm.groupby("segment")["monetary"].sum().sort_values(ascending=True)
bars = ax2.barh(seg_revenue.index, seg_revenue.values, color=PAL[:5], alpha=0.85)
ax2.set_title("Revenue by RFM Segment", fontsize=14, fontweight="bold")
ax2.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x/1e3:.0f}K"))
plt.tight_layout()
save(fig, "05_rfm_segments")

# 2.2 K-Means Clustering
print("  2.2 K-Means Clustering")
features = ["recency", "frequency", "monetary"]
scaler = StandardScaler()
X = scaler.fit_transform(rfm[features])

# Elbow method
inertias = []
K_range = range(2, 11)
for k in K_range:
    km = KMeans(n_clusters=k, random_state=42, n_init=10)
    km.fit(X)
    inertias.append(km.inertia_)

# Fit with optimal k=4
km_final = KMeans(n_clusters=4, random_state=42, n_init=10)
rfm["cluster"] = km_final.fit_predict(X)

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
ax1.plot(list(K_range), inertias, color=PAL[0], marker="o", linewidth=2, markersize=8)
ax1.set_title("Elbow Method — Optimal K", fontsize=14, fontweight="bold")
ax1.set_xlabel("Number of Clusters")
ax1.set_ylabel("Inertia")
ax1.axvline(4, color=PAL[3], linestyle="--", linewidth=1.5, label="K=4 selected")
ax1.legend()

# Scatter: frequency vs monetary colored by cluster
scatter = ax2.scatter(rfm["frequency"], rfm["monetary"],
                      c=rfm["cluster"], cmap="viridis", alpha=0.6, s=30)
ax2.set_title("K-Means Clusters (Frequency vs Monetary)", fontsize=14, fontweight="bold")
ax2.set_xlabel("Frequency (orders)")
ax2.set_ylabel("Monetary ($)")
plt.colorbar(scatter, ax=ax2, label="Cluster")
plt.tight_layout()
save(fig, "06_kmeans_clustering")

# 2.3 Customer Lifetime Value
print("  2.3 Customer Lifetime Value")
clv = df.groupby("customer_id").agg(
    total_orders=("order_id", "nunique"),
    total_revenue=("sales", "sum"),
    avg_order_value=("sales", "mean"),
    first_order=("order_date", "min"),
    last_order=("order_date", "max")
).reset_index()
clv["lifespan_days"] = (clv["last_order"] - clv["first_order"]).dt.days
clv["purchase_rate"] = np.where(clv["lifespan_days"] > 0,
                                 clv["total_orders"] / clv["lifespan_days"] * 365,
                                 clv["total_orders"])
clv["estimated_clv"] = clv["avg_order_value"] * clv["purchase_rate"] * 3

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
ax1.hist(clv["estimated_clv"], bins=50, color=PAL[0], alpha=0.7, edgecolor="white")
ax1.axvline(clv["estimated_clv"].median(), color=PAL[3], linewidth=2, linestyle="--",
            label=f"Median CLV: ${clv['estimated_clv'].median():,.0f}")
ax1.axvline(clv["estimated_clv"].mean(), color=PAL[1], linewidth=2, linestyle="--",
            label=f"Mean CLV: ${clv['estimated_clv'].mean():,.0f}")
ax1.set_title("Customer Lifetime Value Distribution (3yr)", fontsize=13, fontweight="bold")
ax1.set_xlabel("Estimated CLV ($)")
ax1.legend()

top_clv = clv.nlargest(20, "estimated_clv")
ax2.scatter(top_clv["total_orders"], top_clv["total_revenue"],
            s=top_clv["estimated_clv"] / 5, color=PAL[0], alpha=0.6, edgecolors="white")
ax2.set_title("Top 20 CLV Customers (size = CLV)", fontsize=13, fontweight="bold")
ax2.set_xlabel("Total Orders")
ax2.set_ylabel("Total Revenue ($)")
plt.tight_layout()
save(fig, "07_customer_lifetime_value")

# 2.4 Cohort Retention Analysis
print("  2.4 Cohort Retention Analysis")
df["cohort"] = df.groupby("customer_id")["order_date"].transform("min").dt.to_period("Q")
df["order_period"] = df["order_date"].dt.to_period("Q")
df["cohort_index"] = (df["order_period"] - df["cohort"]).apply(lambda x: x.n)

cohort_data = df.groupby(["cohort", "cohort_index"])["customer_id"].nunique().reset_index()
cohort_data.rename(columns={"customer_id": "customers"}, inplace=True)
cohort_sizes = cohort_data.groupby("cohort")["customers"].max().reset_index()
cohort_sizes.rename(columns={"customers": "cohort_size"}, inplace=True)
cohort_data = cohort_data.merge(cohort_sizes)
cohort_data["retention_pct"] = (cohort_data["customers"] / cohort_data["cohort_size"] * 100).round(1)

pivot = cohort_data.pivot_table(index="cohort", columns="cohort_index",
                                 values="retention_pct", aggfunc="first")
pivot.columns = [f"Q{c}" for c in pivot.columns]

fig, ax = plt.subplots(figsize=(16, 8))
sns.heatmap(pivot.iloc[:, :8], annot=True, fmt=".0f", cmap="YlGnBu", linewidths=0.5, ax=ax,
            cbar_kws={"label": "Retention %"})
ax.set_title("Customer Cohort Retention Heatmap (%)", fontsize=15, fontweight="bold")
ax.set_xlabel("Quarters Since First Order")
ax.set_ylabel("Cohort (Quarter of First Order)")
plt.tight_layout()
save(fig, "08_cohort_retention")



# SECTION 3: PRODUCT ANALYSIS

print("\n" + "=" * 60)
print("SECTION 3: PRODUCT ANALYSIS")
print("=" * 60)

# 3.1 Product Performance Matrix (BCG-style)
print("  3.1 Product Performance Matrix")
prod = df.groupby(["product_id", "product_name", "category"]).agg(
    total_sales=("sales", "sum"),
    total_profit=("profit", "sum"),
    units_sold=("quantity", "sum"),
    transactions=("sales", "count")
).reset_index()

med_sales = prod["total_sales"].median()
med_profit = prod["total_profit"].median()


def classify_quadrant(row):
    if row["total_sales"] >= med_sales and row["total_profit"] >= med_profit:
        return "Stars"
    elif row["total_sales"] >= med_sales and row["total_profit"] < med_profit:
        return "Question Marks"
    elif row["total_sales"] < med_sales and row["total_profit"] >= med_profit:
        return "Cash Cows"
    else:
        return "Dogs"


prod["quadrant"] = prod.apply(classify_quadrant, axis=1)
quad_counts = prod["quadrant"].value_counts()

fig, ax = plt.subplots(figsize=(12, 9))
quad_colors = {"Stars": PAL[2], "Cash Cows": PAL[0], "Question Marks": PAL[1], "Dogs": PAL[3]}
for quad in ["Stars", "Cash Cows", "Question Marks", "Dogs"]:
    subset = prod[prod["quadrant"] == quad]
    ax.scatter(subset["total_sales"], subset["total_profit"],
               s=subset["units_sold"] * 2, alpha=0.5, color=quad_colors[quad],
               label=f"{quad} ({len(subset)})", edgecolors="white", linewidth=0.5)

ax.axhline(med_profit, color="gray", linewidth=1, linestyle="--", alpha=0.5)
ax.axvline(med_sales, color="gray", linewidth=1, linestyle="--", alpha=0.5)
ax.set_title("Product Performance Matrix (BCG-Style)", fontsize=15, fontweight="bold")
ax.set_xlabel("Total Sales ($)")
ax.set_ylabel("Total Profit ($)")
ax.legend(fontsize=11, loc="upper left")
plt.tight_layout()
save(fig, "09_product_matrix")

# 3.2 ABC Analysis
print("  3.2 ABC Analysis")
prod_sorted = prod.sort_values("total_sales", ascending=False).reset_index(drop=True)
prod_sorted["cumulative_pct"] = prod_sorted["total_sales"].cumsum() / prod_sorted["total_sales"].sum() * 100


def abc_class(pct):
    if pct <= 80:
        return "A"
    elif pct <= 95:
        return "B"
    else:
        return "C"


prod_sorted["abc"] = prod_sorted["cumulative_pct"].apply(abc_class)
abc_counts = prod_sorted["abc"].value_counts().sort_index()

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
abc_colors = {"A": PAL[2], "B": PAL[1], "C": PAL[3]}
ax1.bar(abc_counts.index, abc_counts.values, color=[abc_colors[c] for c in abc_counts.index], alpha=0.85)
ax1.set_title("ABC Analysis — Product Count", fontsize=14, fontweight="bold")
ax1.set_xlabel("Class")
ax1.set_ylabel("Number of Products")
for i, v in enumerate(abc_counts.values):
    ax1.text(i, v + 5, str(v), ha="center", fontweight="bold")

ax2.plot(prod_sorted.index, prod_sorted["cumulative_pct"], color=PAL[0], linewidth=2)
ax2.axhline(80, color=PAL[2], linestyle="--", linewidth=1.5, label="80% threshold (A)")
ax2.axhline(95, color=PAL[1], linestyle="--", linewidth=1.5, label="95% threshold (B)")
ax2.fill_between(prod_sorted.index, 0, 80, alpha=0.1, color=PAL[2], label="Class A")
ax2.fill_between(prod_sorted.index, 80, 95, alpha=0.1, color=PAL[1], label="Class B")
ax2.fill_between(prod_sorted.index, 95, 100, alpha=0.1, color=PAL[3], label="Class C")
ax2.set_title("ABC Cumulative Revenue Curve", fontsize=14, fontweight="bold")
ax2.set_xlabel("Products (sorted by revenue)")
ax2.set_ylabel("Cumulative Revenue %")
ax2.legend(fontsize=9)
plt.tight_layout()
save(fig, "10_abc_analysis")

# 3.3 Price Elasticity (Discount vs Sales Volume)
print("  3.3 Price Elasticity Analysis")
elasticity = df.groupby("discount").agg(
    avg_sales=("sales", "mean"),
    avg_quantity=("quantity", "mean"),
    avg_profit=("profit", "mean"),
    transactions=("sales", "count")
).reset_index()

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
ax1.scatter(elasticity["discount"] * 100, elasticity["avg_sales"],
            s=elasticity["transactions"] / 5, color=PAL[0], alpha=0.7, edgecolors="white")
z = np.polyfit(elasticity["discount"] * 100, elasticity["avg_sales"], 1)
p = np.poly1d(z)
x_line = np.linspace(0, 80, 100)
ax1.plot(x_line, p(x_line), color=PAL[3], linewidth=2, linestyle="--",
         label=f"Trend (slope={z[0]:.1f})")
ax1.set_title("Discount % vs Avg Sale Value", fontsize=13, fontweight="bold")
ax1.set_xlabel("Discount (%)")
ax1.set_ylabel("Avg Sale ($)")
ax1.legend()

ax2.scatter(elasticity["discount"] * 100, elasticity["avg_profit"],
            s=elasticity["transactions"] / 5, color=[PAL[2] if p >= 0 else PAL[3] for p in elasticity["avg_profit"]],
            alpha=0.7, edgecolors="white")
ax2.axhline(0, color="black", linewidth=0.8)
ax2.set_title("Discount % vs Avg Profit", fontsize=13, fontweight="bold")
ax2.set_xlabel("Discount (%)")
ax2.set_ylabel("Avg Profit ($)")
plt.tight_layout()
save(fig, "11_price_elasticity")

# 3.4 Cross-Selling Opportunities (products frequently in same order)
print("  3.4 Cross-Selling Opportunities")
order_products = df.groupby("order_id")["sub_category"].apply(list).reset_index()
from collections import Counter
from itertools import combinations

pair_counter = Counter()
for _, row in order_products.iterrows():
    items = sorted(set(row["sub_category"]))
    for pair in combinations(items, 2):
        pair_counter[pair] += 1

top_pairs = pair_counter.most_common(15)
pairs_df = pd.DataFrame(top_pairs, columns=["pair", "count"])
pairs_df["label"] = pairs_df["pair"].apply(lambda x: f"{x[0]} + {x[1]}")

fig, ax = plt.subplots(figsize=(14, 7))
bars = ax.barh(range(len(pairs_df)-1, -1, -1), pairs_df["count"], color=PAL[5], alpha=0.85)
ax.set_yticks(range(len(pairs_df)-1, -1, -1))
ax.set_yticklabels(pairs_df["label"], fontsize=10)
ax.set_title("Top 15 Cross-Selling Opportunities (Product Pairs in Same Order)", fontsize=14, fontweight="bold")
ax.set_xlabel("Co-occurrence Count")
plt.tight_layout()
save(fig, "12_cross_selling")



# SECTION 4: ADVANCED STATISTICAL ANALYSIS

print("\n" + "=" * 60)
print("SECTION 4: ADVANCED STATISTICAL ANALYSIS")
print("=" * 60)

# 4.1 Correlation Matrix
print("  4.1 Correlation Matrix")
numeric_cols = ["sales", "quantity", "discount", "profit", "shipping_days",
                "profit_margin", "order_year", "order_month"]
corr = df[numeric_cols].corr()

fig, ax = plt.subplots(figsize=(10, 8))
mask = np.triu(np.ones_like(corr, dtype=bool))
sns.heatmap(corr, mask=mask, annot=True, fmt=".2f", cmap="RdBu_r",
            center=0, vmin=-1, vmax=1, linewidths=0.5, ax=ax,
            square=True, cbar_kws={"shrink": 0.8})
ax.set_title("Correlation Matrix — Numerical Variables", fontsize=14, fontweight="bold")
plt.tight_layout()
save(fig, "13_correlation_matrix")

# 4.2 Hypothesis Testing
print("  4.2 Hypothesis Testing")
results = []

# Test 1: Do discounted orders generate more revenue?
discounted = df[df["discount"] > 0]["sales"]
no_discount = df[df["discount"] == 0]["sales"]
t_stat, p_val = ttest_ind(discounted, no_discount, equal_var=False)
results.append(("Discounted vs No-Discount Sales", f"t={t_stat:.2f}", f"p={p_val:.4f}",
                "Significant" if p_val < 0.05 else "Not Significant"))

# Test 2: Profit difference between regions
regions = df["region"].unique()
west = df[df["region"] == "West"]["profit"]
east = df[df["region"] == "East"]["profit"]
t_stat2, p_val2 = ttest_ind(west, east, equal_var=False)
results.append(("West vs East Profit", f"t={t_stat2:.2f}", f"p={p_val2:.4f}",
                "Significant" if p_val2 < 0.05 else "Not Significant"))

# Test 3: Profit by segment
consumer = df[df["segment"] == "Consumer"]["profit"]
corporate = df[df["segment"] == "Corporate"]["profit"]
t_stat3, p_val3 = ttest_ind(consumer, corporate, equal_var=False)
results.append(("Consumer vs Corporate Profit", f"t={t_stat3:.2f}", f"p={p_val3:.4f}",
                "Significant" if p_val3 < 0.05 else "Not Significant"))

# Test 4: Do higher quantities yield higher profit margins?
high_qty = df[df["quantity"] >= 5]["profit_margin"]
low_qty = df[df["quantity"] < 5]["profit_margin"]
t_stat4, p_val4 = ttest_ind(high_qty, low_qty, equal_var=False)
results.append(("High Qty vs Low Qty Margin", f"t={t_stat4:.2f}", f"p={p_val4:.4f}",
                "Significant" if p_val4 < 0.05 else "Not Significant"))

ht_df = pd.DataFrame(results, columns=["Test", "Statistic", "P-Value", "Result (α=0.05)"])

fig, ax = plt.subplots(figsize=(12, 4))
ax.axis("off")
table = ax.table(cellText=ht_df.values, colLabels=ht_df.columns, loc="center",
                 cellLoc="center")
table.auto_set_font_size(False)
table.set_fontsize(11)
table.scale(1.2, 2)
for (row, col), cell in table.get_celld().items():
    if row == 0:
        cell.set_facecolor(PAL[0])
        cell.set_text_props(color="white", fontweight="bold")
    elif col == 3:
        cell.set_facecolor("#d4edda" if cell.get_text().get_text() == "Significant" else "#f8d7da")
ax.set_title("Hypothesis Testing Results", fontsize=14, fontweight="bold", pad=20)
plt.tight_layout()
save(fig, "14_hypothesis_testing")

# 4.3 Predictive Modeling (Gradient Boosting)
print("  4.3 Predictive Modeling — Sales Forecast")
model_df = df.copy()
model_df["day_of_year"] = model_df["order_date"].dt.dayofyear
model_df["week_of_year"] = model_df["order_date"].dt.isocalendar().week.astype(int)
model_df["day_of_week"] = model_df["order_date"].dt.dayofweek

features = ["quantity", "discount", "shipping_days", "order_year", "order_month",
            "day_of_year", "week_of_year", "day_of_week"]
X = model_df[features].values
y = model_df["sales"].values

tscv = TimeSeriesSplit(n_splits=5)
mae_scores, r2_scores = [], []

for train_idx, test_idx in tscv.split(X):
    X_train, X_test = X[train_idx], X[test_idx]
    y_train, y_test = y[train_idx], y[test_idx]
    gb = GradientBoostingRegressor(n_estimators=100, max_depth=4, random_state=42)
    gb.fit(X_train, y_train)
    y_pred = gb.predict(X_test)
    mae_scores.append(mean_absolute_error(y_test, y_pred))
    r2_scores.append(r2_score(y_test, y_pred))

# Feature importance
gb_full = GradientBoostingRegressor(n_estimators=100, max_depth=4, random_state=42)
gb_full.fit(X, y)
importance = pd.Series(gb_full.feature_importances_, index=features).sort_values(ascending=True)

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
ax1.barh(importance.index, importance.values, color=PAL[0], alpha=0.85)
ax1.set_title("Feature Importance — Sales Prediction (GBR)", fontsize=13, fontweight="bold")

# Actual vs Predicted on last fold
X_train, X_test = X[train_idx], X[test_idx]
y_train, y_test = y[train_idx], y[test_idx]
y_pred = gb_full.predict(X_test)
sample = np.random.choice(len(y_test), min(500, len(y_test)), replace=False)
ax2.scatter(y_test[sample], y_pred[sample], alpha=0.3, s=15, color=PAL[0])
max_val = max(y_test.max(), y_pred.max())
ax2.plot([0, max_val], [0, max_val], color=PAL[3], linewidth=2, linestyle="--", label="Perfect prediction")
ax2.set_title(f"Actual vs Predicted Sales\nMAE={np.mean(mae_scores):.1f} | R²={np.mean(r2_scores):.2f}",
              fontsize=13, fontweight="bold")
ax2.set_xlabel("Actual Sales ($)")
ax2.set_ylabel("Predicted Sales ($)")
ax2.legend()
plt.tight_layout()
save(fig, "15_predictive_modeling")

# 4.4 Outlier Deep Dive
print("  4.4 Outlier Analysis")
from sklearn.ensemble import IsolationForest

iso_features = ["sales", "quantity", "discount", "profit"]
iso_scaler = RobustScaler()
X_iso = iso_scaler.fit_transform(df[iso_features])

iso = IsolationForest(n_estimators=200, contamination=0.03, random_state=42)
df["anomaly"] = iso.fit_predict(X_iso)
anomalies = df[df["anomaly"] == -1]
normal = df[df["anomaly"] == 1]

fig, axes = plt.subplots(2, 2, figsize=(14, 10))
for ax, feat in zip(axes.flat, iso_features):
    ax.hist(normal[feat], bins=50, alpha=0.5, color=PAL[0], label=f"Normal ({len(normal):,})")
    ax.hist(anomalies[feat], bins=50, alpha=0.7, color=PAL[3], label=f"Anomaly ({len(anomalies):,})")
    ax.set_title(feat, fontsize=13, fontweight="bold")
    ax.legend(fontsize=9)
fig.suptitle("Outlier Detection — Isolation Forest (3% contamination)", fontsize=15, fontweight="bold", y=1.01)
plt.tight_layout()
save(fig, "16_outlier_analysis")



# SUMMARY

print("\n" + "=" * 60)
print("ANALYSIS COMPLETE")
print("=" * 60)
print(f"Charts saved to: {VIZ_DIR}/")
print(f"Total charts generated: 16")
print(f"\nKey findings:")
print(f"  - YoY avg growth: {yoy_mean:.1f}% (95% CI: [{yoy_ci[0]:.1f}%, {yoy_ci[1]:.1f}%])")
print(f"  - RFM segments: {dict(seg_counts)}")
print(f"  - K-Means optimal clusters: 4")
print(f"  - Median CLV (3yr): ${clv['estimated_clv'].median():,.0f}")
print(f"  - ABC: {dict(abc_counts)} products")
print(f"  - Model MAE: {np.mean(mae_scores):.1f}, R²: {np.mean(r2_scores):.2f}")
print(f"  - Anomalies detected: {len(anomalies)} ({len(anomalies)/len(df)*100:.1f}%)")
