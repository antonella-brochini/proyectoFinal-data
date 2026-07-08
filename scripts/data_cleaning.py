# Standard Library
import os
import sys
import logging
import warnings
from datetime import datetime
from io import StringIO

# Third-Party
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")

# Paths relative to project root
PROJECT_ROOT   = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
RAW_DATA       = os.path.join(PROJECT_ROOT, 'data', 'raw', 'Superstore sales dataset.csv')
CLEAN_DATA     = os.path.join(PROJECT_ROOT, 'data', 'processed', 'clean_data.csv')
LOG_FILE       = os.path.join(PROJECT_ROOT, 'logs', 'cleaning_log.txt')
SUMMARY_FILE   = os.path.join(PROJECT_ROOT, 'logs', 'cleaning_summary.txt')

# Logging Setup
logger = logging.getLogger("DataCleaner")
logger.setLevel(logging.DEBUG)

file_handler = logging.FileHandler(LOG_FILE, mode="w", encoding="utf-8")
file_handler.setLevel(logging.DEBUG)
fmt = logging.Formatter("%(asctime)s  [%(levelname)-8s]  %(message)s",
                        datefmt="%Y-%m-%d %H:%M:%S")
file_handler.setFormatter(fmt)
logger.addHandler(file_handler)

console = logging.StreamHandler(sys.stdout)
console.setLevel(logging.INFO)
console.setFormatter(fmt)
logger.addHandler(console)


# Section banner helper
def section(title: str):
    logger.info("-" * 70)
    logger.info(f"  {title}")
    logger.info("-" * 70)


# Step 1: Load raw data and take a snapshot for comparison
section("1. Loading Raw Data")

df_raw = pd.read_csv(RAW_DATA, encoding="utf-8")
df = df_raw.copy()

ORIG_ROWS, ORIG_COLS = df.shape
logger.info(f"Loaded {ORIG_ROWS:,} rows × {ORIG_COLS} columns from '{RAW_DATA}'")
logger.info(f"Columns: {list(df.columns)}")
logger.info(f"Memory usage: {df.memory_usage(deep=True).sum() / 1024:.1f} KB")

# Snapshot for final comparison
orig_dtypes   = df.dtypes.copy()
orig_describe = df.describe().copy()
orig_missing  = df.isnull().sum().copy()


# Step 2: Remove exact duplicate rows
section("2. Exact Duplicate Removal")

exact_dupes = df.duplicated().sum()
logger.info(f"Exact duplicate rows detected: {exact_dupes}")

if exact_dupes > 0:
    dupe_mask = df.duplicated(keep="first")
    logger.debug(f"Row indices of duplicates: {df[dupe_mask].index.tolist()}")
    df.drop_duplicates(keep="first", inplace=True)
    logger.info(f"Removed {exact_dupes} exact duplicate row(s).  Shape → {df.shape}")
else:
    logger.info("No exact duplicates found. Data unchanged.")


# Step 3: Remove partial duplicates based on Order ID + Product ID
section("3. Partial Duplicate Removal (Order ID + Product ID)")

partial_dupes = df.duplicated(subset=["Order ID", "Product ID"], keep=False)
n_partial = partial_dupes.sum()
logger.info(f"Rows involved in duplicate (Order ID + Product ID) pairs: {n_partial}")

if n_partial > 0:
    dup_groups = df[partial_dupes].groupby(["Order ID", "Product ID"])
    for (oid, pid), grp in dup_groups:
        logger.debug(f"  Order={oid}, Product={pid} → {len(grp)} rows "
                     f"(keeping first, indices {grp.index.tolist()})")

    before = len(df)
    df.drop_duplicates(subset=["Order ID", "Product ID"], keep="first", inplace=True)
    removed = before - len(df)
    logger.info(f"Removed {removed} partial duplicate row(s).  Shape → {df.shape}")
else:
    logger.info("No partial duplicates found. Data unchanged.")


# Step 4: Analyze and handle missing values
section("4. Missing Value Analysis & Imputation")

missing_per_col = df.isnull().sum()
total_missing   = missing_per_col.sum()
logger.info(f"Total missing cells: {total_missing} "
            f"({total_missing / df.size * 100:.2f}% of all cells)")

if total_missing > 0:
    for col in df.columns:
        n_miss = missing_per_col[col]
        if n_miss == 0:
            continue
        pct = n_miss / len(df) * 100
        logger.info(f"  {col:20s} → {n_miss:5d} missing ({pct:.2f}%)")

    # Numeric columns: median imputation (robust to outliers)
    num_cols = df.select_dtypes(include=[np.number]).columns
    for col in num_cols:
        if df[col].isnull().any():
            med = df[col].median()
            df[col].fillna(med, inplace=True)
            logger.info(f"  Imputed '{col}' with median = {med:.4f}")

    # Categorical columns: mode imputation
    cat_cols = df.select_dtypes(include=["object"]).columns
    for col in cat_cols:
        if df[col].isnull().any():
            mode_val = df[col].mode()[0]
            df[col].fillna(mode_val, inplace=True)
            logger.info(f"  Imputed '{col}' with mode = '{mode_val}'")

    # Forward-fill / Backward-fill for sequential columns
    # Row ID should be sequential; fill gaps if any
    if df["Row ID"].isnull().any():
        df["Row ID"].ffill(inplace=True)
        df["Row ID"].bfill(inplace=True)
        logger.info("  Forward/backward-filled 'Row ID'")
else:
    logger.info("Dataset is complete — zero missing values. No imputation required.")

# Step 5: Parse, standardize, and validate date columns
section("5. Date Parsing, Standardization & Validation")

# Detect dominant date format
logger.info("Detecting date format …")

# Try D/M/YYYY first
parsed_dm  = pd.to_datetime(df["Order Date"], format="%d/%m/%Y", errors="coerce")
# Try M/D/YYYY
parsed_md  = pd.to_datetime(df["Order Date"], format="%m/%d/%Y", errors="coerce")

dm_ok  = parsed_dm.notna().sum()
md_ok  = parsed_md.notna().sum()
logger.info(f"  Parsed with D/M/YYYY: {dm_ok:,} / {len(df):,}")
logger.info(f"  Parsed with M/D/YYYY: {md_ok:,} / {len(df):,}")

if dm_ok >= md_ok:
    chosen_fmt  = "%d/%m/%Y"
    chosen_label = "D/M/YYYY"
else:
    chosen_fmt  = "%m/%d/%Y"
    chosen_label = "M/D/YYYY"

logger.info(f"  ► Chosen format: {chosen_label} (higher parse success)")

# Convert to datetime
df["Order Date"] = pd.to_datetime(df["Order Date"], format=chosen_fmt, errors="coerce")
df["Ship Date"]  = pd.to_datetime(df["Ship Date"],  format=chosen_fmt, errors="coerce")

unparsed_order = df["Order Date"].isnull().sum()
unparsed_ship  = df["Ship Date"].isnull().sum()
logger.info(f"  Unparseable Order Dates: {unparsed_order}")
logger.info(f"  Unparseable Ship Dates:  {unparsed_ship}")

# Validate date ranges
order_min, order_max = df["Order Date"].min(), df["Order Date"].max()
ship_min,  ship_max  = df["Ship Date"].min(),  df["Ship Date"].max()
logger.info(f"  Order Date range: {order_min.date()} → {order_max.date()}")
logger.info(f"  Ship Date range:  {ship_min.date()}  → {ship_max.date()}")

# Flag future dates (beyond current year + 1 as safety margin)
future_cutoff = pd.Timestamp(datetime.now().year + 1, 1, 1)
future_orders = (df["Order Date"] > future_cutoff).sum()
future_ships  = (df["Ship Date"]  > future_cutoff).sum()
logger.info(f"  Future-dated orders (>{future_cutoff.year}-01-01): {future_orders}")
logger.info(f"  Future-dated shipments: {future_ships}")

# Shipping duration validation
df["Shipping_Days"] = (df["Ship Date"] - df["Order Date"]).dt.days

neg_ship = (df["Shipping_Days"] < 0).sum()
logger.info(f"  Rows where Ship Date < Order Date (negative days): {neg_ship}")

if neg_ship > 0:
    logger.info(f"  ► Removing {neg_ship} invalid shipping rows")
    df = df[df["Shipping_Days"] >= 0].copy()
    logger.info(f"  Shape after removal → {df.shape}")

extreme_ship = (df["Shipping_Days"] > 365).sum()
logger.info(f"  Rows with shipping > 365 days (outlier): {extreme_ship}")

logger.info(f"  Shipping days — Min: {df['Shipping_Days'].min()}, "
            f"Max: {df['Shipping_Days'].max()}, "
            f"Mean: {df['Shipping_Days'].mean():.1f}, "
            f"Median: {df['Shipping_Days'].median():.0f}")


# Step 6: Remove rows with impossible values
section("6. Invalid Row Detection & Removal")

invalid_count = 0

# Negative or zero Quantity
neg_qty = (df["Quantity"] <= 0).sum()
logger.info(f"  Rows with Quantity ≤ 0: {neg_qty}")
if neg_qty > 0:
    df = df[df["Quantity"] > 0].copy()
    invalid_count += neg_qty
    logger.info(f"  ► Removed {neg_qty} row(s).  Shape → {df.shape}")

# Negative Sales (impossible for revenue)
neg_sales = (df["Sales"] < 0).sum()
logger.info(f"  Rows with negative Sales: {neg_sales}")
if neg_sales > 0:
    df = df[df["Sales"] >= 0].copy()
    invalid_count += neg_sales
    logger.info(f"  ► Removed {neg_sales} row(s).  Shape → {df.shape}")

# Quantity > 100 (unrealistic for retail)
extreme_qty = (df["Quantity"] > 100).sum()
logger.info(f"  Rows with Quantity > 100: {extreme_qty}")
if extreme_qty > 0:
    df = df[df["Quantity"] <= 100].copy()
    invalid_count += extreme_qty
    logger.info(f"  ► Removed {extreme_qty} row(s).  Shape → {df.shape}")

# Discount > 1.0 (> 100% is invalid)
over_disc = (df["Discount"] > 1.0).sum()
logger.info(f"  Rows with Discount > 100%: {over_disc}")
if over_disc > 0:
    df = df[df["Discount"] <= 1.0].copy()
    invalid_count += over_disc
    logger.info(f"  ► Removed {over_disc} row(s).  Shape → {df.shape}")

# (zero revenue — likely test/cancelled orders)
zero_sales = ((df["Sales"] == 0) & (df["Quantity"] > 0)).sum()
logger.info(f"  Rows with Sales = 0 but Quantity > 0: {zero_sales}")

logger.info(f"  Total invalid rows removed in Step 6: {invalid_count}")


# Step 7: Validate categorical columns against known valid values
section("7. Categorical Data Validation")

# Ship Mode
valid_ship_modes = {"Standard Class", "Second Class", "First Class", "Same Day"}
invalid_modes = df[~df["Ship Mode"].isin(valid_ship_modes)]["Ship Mode"].unique()
logger.info(f"  Ship Mode — valid values: {valid_ship_modes}")
logger.info(f"  Ship Mode — unexpected values: {invalid_modes.tolist() if len(invalid_modes) else 'None'}")

# Segment
valid_segments = {"Consumer", "Corporate", "Home Office"}
invalid_segs = df[~df["Segment"].isin(valid_segments)]["Segment"].unique()
logger.info(f"  Segment — valid values: {valid_segments}")
logger.info(f"  Segment — unexpected values: {invalid_segs.tolist() if len(invalid_segs) else 'None'}")

# Region
valid_regions = {"West", "East", "Central", "South"}
invalid_regs = df[~df["Region"].isin(valid_regions)]["Region"].unique()
logger.info(f"  Region — valid values: {valid_regions}")
logger.info(f"  Region — unexpected values: {invalid_regs.tolist() if len(invalid_regs) else 'None'}")

# Category
valid_categories = {"Office Supplies", "Furniture", "Technology"}
invalid_cats = df[~df["Category"].isin(valid_categories)]["Category"].unique()
logger.info(f"  Category — valid values: {valid_categories}")
logger.info(f"  Category — unexpected values: {invalid_cats.tolist() if len(invalid_cats) else 'None'}")

# Country (should be single value)
countries = df["Country"].unique()
logger.info(f"  Country unique values: {countries.tolist()}")
if len(countries) > 1:
    logger.warning("  Multiple countries detected — verify data scope")

# Sub-Category consistency with Category
expected_mapping = {
    "Office Supplies": {"Binders", "Paper", "Furnishings", "Storage", "Art",
                        "Appliances", "Labels", "Envelopes", "Fasteners", "Supplies"},
    "Furniture":       {"Chairs", "Tables", "Bookcases", "Furnishings"},
    "Technology":      {"Phones", "Accessories", "Machines", "Copiers"},
}

cross_check = df[["Category", "Sub-Category"]].drop_duplicates()
for _, row in cross_check.iterrows():
    cat, subcat = row["Category"], row["Sub-Category"]
    if cat in expected_mapping:
        if subcat not in expected_mapping[cat]:
            # Furnishings appears in both Furniture and Office Supplies — known
            if not (cat == "Furniture" and subcat == "Furnishings"):
                logger.warning(f"  Unexpected mapping: {cat} → {subcat}")

logger.info("  Sub-Category ↔ Category cross-validation complete.")

# Whitespace & casing cleanup
str_cols = df.select_dtypes(include=["object"]).columns
for col in str_cols:
    before = df[col].copy()
    df[col] = df[col].astype(str).str.strip()
    changed = (before != df[col]).sum()
    if changed > 0:
        logger.info(f"  Stripped whitespace in '{col}': {changed} value(s) changed")

logger.info("  Categorical validation complete.")


# Step 8: Detect outliers using IQR, Z-Score, Modified Z-Score, and Isolation Forest
section("8. Advanced Outlier Detection")

# IQR Method (Sales & Profit)
logger.info("── 8a. IQR Method ──")

for col in ["Sales", "Profit"]:
    q1 = df[col].quantile(0.25)
    q3 = df[col].quantile(0.75)
    iqr = q3 - q1
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr
    outliers = ((df[col] < lower) | (df[col] > upper)).sum()
    logger.info(f"  {col}: Q1={q1:.2f}, Q3={q3:.2f}, IQR={iqr:.2f}, "
                f"Bounds=[{lower:.2f}, {upper:.2f}], Outliers={outliers}")

# Z-Score Method
logger.info("── 8b. Z-Score Method (|z| > 3) ──")

for col in ["Sales", "Profit", "Quantity"]:
    z = np.abs(stats.zscore(df[col], nan_policy="omit"))
    n_outliers = (z > 3).sum()
    logger.info(f"  {col}: Z-score outliers (|z|>3) = {n_outliers} "
                f"({n_outliers/len(df)*100:.2f}%)")

# Modified Z-Score (MAD-based, more robust)
logger.info("── 8c. Modified Z-Score (MAD-based, threshold=3.5) ──")

for col in ["Sales", "Profit"]:
    median = df[col].median()
    mad = np.median(np.abs(df[col] - median))
    if mad == 0:
        mad = 1e-10
    mod_z = 0.6745 * (df[col] - median) / mad
    n_outliers = (np.abs(mod_z) > 3.5).sum()
    logger.info(f"  {col}: MAD={mad:.2f}, Modified Z outliers = {n_outliers} "
                f"({n_outliers/len(df)*100:.2f}%)")

# Isolation Forest (ML-based anomaly detection)
logger.info("── 8d. Isolation Forest (ML Anomaly Detection) ──")

iso_features = ["Sales", "Quantity", "Discount", "Profit"]
X_iso = df[iso_features].dropna()

scaler = StandardScaler()
X_scaled = scaler.fit_transform(X_iso)

iso_forest = IsolationForest(
    n_estimators=200,
    contamination=0.02,   # expect ~2% anomalies
    random_state=42,
    n_jobs=-1
)
df_iso = df.loc[X_iso.index].copy()
iso_forest.fit(X_scaled)
df_iso["anomaly_score"] = iso_forest.decision_function(X_scaled)
df_iso["is_anomaly"]    = iso_forest.predict(X_scaled)

anomalies = df_iso[df_iso["is_anomaly"] == -1]
logger.info(f"  Features used: {iso_features}")
logger.info(f"  Contamination set: 2%")
logger.info(f"  Anomalies detected: {len(anomalies)} ({len(anomalies)/len(df)*100:.2f}%)")

if len(anomalies) > 0:
    logger.info(f"  Anomaly profile (means):")
    for feat in iso_features:
        logger.info(f"    {feat:12s}: anomaly mean={anomalies[feat].mean():.2f}  "
                    f"vs normal mean={df_iso[df_iso['is_anomaly']==1][feat].mean():.2f}")

# NOTE: We LOG anomalies but do NOT remove them - outliers are legitimate
# business data (large corporate orders, high-discount clearance, etc.)
logger.info("  ► Anomalies logged but preserved (legitimate business extremes).")


# Step 9: Create derived features from existing columns
section("9. Derived Feature Engineering")

# Year, Month, Quarter from Order Date 
df["Order_Year"]    = df["Order Date"].dt.year
df["Order_Month"]   = df["Order Date"].dt.month
df["Order_Quarter"] = df["Order Date"].dt.quarter
df["Order_DayName"] = df["Order Date"].dt.day_name()
logger.info("  Created: Order_Year, Order_Month, Order_Quarter, Order_DayName")

# Profit Margin
df["Profit_Margin"] = np.where(
    df["Sales"] != 0,
    (df["Profit"] / df["Sales"]) * 100,
    0.0
)
logger.info("  Created: Profit_Margin (%)")

# Is_Loss flag
df["Is_Loss"] = (df["Profit"] < 0).astype(int)
logger.info(f"  Created: Is_Loss  (flagged {df['Is_Loss'].sum():,} loss rows)")

# Discount Tier
bins   = [-0.01, 0, 0.1, 0.2, 0.3, 0.5, 0.8, 1.0]
labels = ["No Discount", "Low (1-10%)", "Medium (11-20%)", "High (21-30%)",
          "Very High (31-50%)", "Extreme (51-80%)", "Clearance (81-100%)"]
df["Discount_Tier"] = pd.cut(df["Discount"], bins=bins, labels=labels,
                              include_lowest=True)
logger.info("  Created: Discount_Tier (categorical)")

# Shipping duration already in Shipping_Days
logger.info(f"  Shipping_Days already computed (Step 5d)")


# Step 10: Optimize data types for memory efficiency
section("10. Data Type Optimization")

# Convert appropriate string columns to Categorical for memory efficiency
cat_convert = ["Ship Mode", "Segment", "Country", "Region",
               "Category", "Sub-Category", "Discount_Tier", "Order_DayName"]
for col in cat_convert:
    if col in df.columns:
        df[col] = df[col].astype("category")
        logger.info(f"  '{col}' → category  (unique: {df[col].nunique()})")

# Downcast numeric where safe
df["Row ID"]    = pd.to_numeric(df["Row ID"],    downcast="integer")
df["Quantity"]  = pd.to_numeric(df["Quantity"],  downcast="integer")
df["Is_Loss"]   = pd.to_numeric(df["Is_Loss"],   downcast="integer")

logger.info(f"  Memory after optimization: {df.memory_usage(deep=True).sum() / 1024:.1f} KB")


# Step 11: Final integrity checks after all cleaning steps
section("11. Final Data Integrity Checks")

# Re-check missing
final_missing = df.isnull().sum().sum()
logger.info(f"  Total missing cells after cleaning: {final_missing}")

# Re-check duplicates
final_dupes = df.duplicated().sum()
logger.info(f"  Exact duplicate rows after cleaning: {final_dupes}")

# Primary key uniqueness
pk_dupes = df.duplicated(subset=["Row ID"]).sum()
logger.info(f"  Row ID uniqueness violations: {pk_dupes}")

# Data completeness ratio
total_cells = df.size
non_null    = df.notnull().sum().sum()
logger.info(f"  Data completeness: {non_null}/{total_cells} "
            f"({non_null/total_cells*100:.2f}%)")


# Step 12: Reorder columns and save cleaned dataset
section("12. Saving Cleaned Dataset")

# Reorder columns: identifiers first, then temporal, customer, geo, product, financial, derived
id_cols     = ["Row ID", "Order ID"]
date_cols   = ["Order Date", "Ship Date", "Shipping_Days"]
cust_cols   = ["Customer ID", "Customer Name", "Segment"]
geo_cols    = ["Country", "City", "State", "Postal Code", "Region"]
prod_cols   = ["Product ID", "Category", "Sub-Category", "Product Name"]
fin_cols    = ["Sales", "Quantity", "Discount", "Profit"]
ship_cols   = ["Ship Mode"]
deriv_cols  = ["Order_Year", "Order_Month", "Order_Quarter", "Order_DayName",
               "Profit_Margin", "Is_Loss", "Discount_Tier"]

ordered = id_cols + date_cols + ship_cols + cust_cols + geo_cols + prod_cols + fin_cols + deriv_cols
# Include only columns that exist
ordered = [c for c in ordered if c in df.columns]
df = df[ordered]

df.to_csv(CLEAN_DATA, index=False, encoding="utf-8")

CLEAN_ROWS, CLEAN_COLS = df.shape
logger.info(f"Saved {CLEAN_ROWS:,} rows × {CLEAN_COLS} columns → '{CLEAN_DATA}'")
logger.info(f"New columns added: {set(df.columns) - set(df_raw.columns)}")


# Step 13: Generate and save summary report
section("13. Generating Summary Report")

summary_lines = []

def s(text=""):
    summary_lines.append(text)

s("=" * 65)
s("  DATA CLEANING SUMMARY REPORT")
s("  Superstore Sales Dataset")
s(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
s("=" * 65)
s()
s("DIMENSION COMPARISON")
s("-" * 65)
s(f"  {'Metric':<22s} {'Original':<18s} {'Cleaned':<18s}")
s(f"  {'-'*20:<22s} {'-'*16:<18s} {'-'*16:<18s}")
s(f"  {'Rows':<22s} {ORIG_ROWS:<18,} {CLEAN_ROWS:<18,}")
s(f"  {'Columns':<22s} {ORIG_COLS:<18} {CLEAN_COLS:<18}")
rows_removed = ORIG_ROWS - CLEAN_ROWS
s(f"  {'Rows Removed':<22s} {'—':<18s} {rows_removed:<18,}")
s(f"  {'Removal Rate':<22s} {'—':<18s} {rows_removed/ORIG_ROWS*100:<17.2f}%")
s()
s("CLEANING ACTIONS PERFORMED")
s("-" * 65)
s(f"  Exact duplicates removed          :  {exact_dupes}")
partial_removed = max(0, n_partial - df.duplicated(subset=['Order ID','Product ID'], keep='first').sum() - (ORIG_ROWS - len(df)))
s(f"  Partial duplicates removed        :  see log")
s(f"  Invalid rows removed (Step 6)     :  {invalid_count}")
s(f"  Negative shipping days removed    :  {neg_ship}")
s(f"  Missing values imputed            :  {total_missing}")
s(f"  Date format standardized          :  {chosen_label}")
s(f"  Derived columns added             :  {len(set(df.columns)-set(df_raw.columns))}")
s(f"  Data types optimized              :  {len(cat_convert)} columns")
s(f"  ML anomalies detected (logged)    :  {len(anomalies)}")
s()
s("NUMERIC SUMMARY (Cleaned Data)")
s("-" * 65)
s(df[["Sales", "Quantity", "Discount", "Profit", "Profit_Margin", "Shipping_Days"]].describe().to_string())
s()
s("DATA QUALITY SCORECARD")
s("-" * 65)

completeness = non_null / total_cells * 100
uniqueness   = (1 - df.duplicated().sum() / len(df)) * 100
valid_dates  = (df["Order Date"].notna().sum() / len(df)) * 100

s(f"  Completeness    :  {completeness:.2f}%")
s(f"  Uniqueness      :  {uniqueness:.2f}%")
s(f"  Date Validity   :  {valid_dates:.2f}%")
s(f"  Missing Values  :  {df.isnull().sum().sum()}")
s(f"  Duplicate Rows  :  {df.duplicated().sum()}")

summary_text = "\n".join(summary_lines)

with open(SUMMARY_FILE, "w", encoding="utf-8") as f:
    f.write(summary_text)

logger.info(f"Summary report saved → '{SUMMARY_FILE}'")

# Print summary to console as well
print("\n")
print(summary_text)

logger.info("═══ PIPELINE COMPLETE ═══")
