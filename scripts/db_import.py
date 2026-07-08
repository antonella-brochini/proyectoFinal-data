import sys
import os
import csv
import logging
import time
from datetime import datetime
from decimal import Decimal
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')), '.env'))

import psycopg2
from psycopg2 import sql, extras
import pandas as pd

# Paths relative to project root
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DB_NAME     = os.environ.get("DB_NAME", "working_database")
DB_USER     = os.environ.get("DB_USER", "postgres")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "your_password_here")
DB_HOST     = os.environ.get("DB_HOST", "localhost")
DB_PORT     = os.environ.get("DB_PORT", "5432")
DB_SSLMODE  = os.environ.get("DB_SSLMODE", "require")
CSV_FILE    = os.path.join(PROJECT_ROOT, "data", "processed", "clean_data.csv")
LOG_FILE    = os.path.join(PROJECT_ROOT, "logs", "db_import_log.txt")
BATCH_SIZE  = 2000

# Logging setup
logger = logging.getLogger("DBImporter")
logger.setLevel(logging.DEBUG)

fh = logging.FileHandler(LOG_FILE, mode="w", encoding="utf-8")
fh.setLevel(logging.DEBUG)
fmt = logging.Formatter("%(asctime)s  [%(levelname)-8s]  %(message)s",
                        datefmt="%Y-%m-%d %H:%M:%S")
fh.setFormatter(fmt)
logger.addHandler(fh)

ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.INFO)
ch.setFormatter(fmt)
logger.addHandler(ch)


def section(title):
    """Print a section header."""
    logger.info("-" * 70)
    logger.info(f"  {title}")
    logger.info("-" * 70)


# Step 1: Connect to the database
section("1. Database Connection")

conn = psycopg2.connect(
    dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD,
    host=DB_HOST, port=DB_PORT, sslmode=DB_SSLMODE
)
conn.autocommit = False
cur = conn.cursor()

cur.execute("SELECT version();")
pg_version = cur.fetchone()[0]
logger.info(f"Connected to: {pg_version}")
logger.info(f"Database: {DB_NAME}  |  Host: {DB_HOST}:{DB_PORT}")


# Step 2: Load CSV into pandas
section("2. Loading CSV Data")

df = pd.read_csv(CSV_FILE, encoding="utf-8")
logger.info(f"Loaded {len(df):,} rows x {len(df.columns)} columns from '{CSV_FILE}'")
logger.info(f"Columns: {list(df.columns)}")

# Type conversions before insert
df["Order Date"]    = pd.to_datetime(df["Order Date"])
df["Ship Date"]     = pd.to_datetime(df["Ship Date"])
df["Shipping_Days"] = df["Shipping_Days"].astype(int)
df["Quantity"]      = df["Quantity"].astype(int)
df["Order_Year"]    = df["Order_Year"].astype(int)
df["Order_Month"]   = df["Order_Month"].astype(int)
df["Order_Quarter"] = df["Order_Quarter"].astype(int)
df["Is_Loss"]       = df["Is_Loss"].astype(int)
df["Postal Code"]   = df["Postal Code"].astype(str).str.zfill(5)

logger.info("Type conversions applied (dates, integers, postal code zero-padding)")


# Step 3: Drop existing objects for a clean slate
section("3. Dropping Existing Objects")

drop_sql = """
DROP TABLE IF EXISTS fact_sales       CASCADE;
DROP TABLE IF EXISTS dim_customer     CASCADE;
DROP TABLE IF EXISTS dim_product      CASCADE;
DROP TABLE IF EXISTS dim_geography    CASCADE;
DROP TABLE IF EXISTS dim_date         CASCADE;
DROP TABLE IF EXISTS dim_ship_mode    CASCADE;
DROP TABLE IF EXISTS sales_data       CASCADE;
"""
cur.execute(drop_sql)
conn.commit()
logger.info("All existing tables dropped (if any)")


# Step 4: Create the flat denormalized table
section("4. Creating Flat Table: sales_data")

flat_table_ddl = """
CREATE TABLE sales_data (
    row_id              INTEGER          NOT NULL,
    order_id            VARCHAR(20)      NOT NULL,
    order_date          DATE             NOT NULL,
    ship_date           DATE             NOT NULL,
    shipping_days       SMALLINT         NOT NULL,
    ship_mode           VARCHAR(20)      NOT NULL,
    customer_id         VARCHAR(20)      NOT NULL,
    customer_name       VARCHAR(100)     NOT NULL,
    segment             VARCHAR(20)      NOT NULL,
    country             VARCHAR(50)      NOT NULL DEFAULT 'United States',
    city                VARCHAR(100)     NOT NULL,
    state               VARCHAR(50)      NOT NULL,
    postal_code         VARCHAR(10)      NOT NULL,
    region              VARCHAR(20)      NOT NULL,
    product_id          VARCHAR(30)      NOT NULL,
    category            VARCHAR(30)      NOT NULL,
    sub_category        VARCHAR(30)      NOT NULL,
    product_name        TEXT             NOT NULL,
    sales               NUMERIC(12,4)    NOT NULL,
    quantity            SMALLINT         NOT NULL,
    discount            NUMERIC(4,2)     NOT NULL,
    profit              NUMERIC(12,4)    NOT NULL,
    order_year          SMALLINT         NOT NULL,
    order_month         SMALLINT         NOT NULL,
    order_quarter       SMALLINT         NOT NULL,
    order_day_name      VARCHAR(10)      NOT NULL,
    profit_margin       NUMERIC(8,4)     NOT NULL,
    is_loss             SMALLINT         NOT NULL,
    discount_tier       VARCHAR(30)      NOT NULL,

    CONSTRAINT pk_sales_data_row_id      PRIMARY KEY (row_id),
    CONSTRAINT chk_sales_positive        CHECK (sales >= 0),
    CONSTRAINT chk_quantity_positive     CHECK (quantity > 0),
    CONSTRAINT chk_discount_range        CHECK (discount >= 0 AND discount <= 1),
    CONSTRAINT chk_shipping_days_valid   CHECK (shipping_days >= 0),
    CONSTRAINT chk_is_loss_binary        CHECK (is_loss IN (0, 1)),
    CONSTRAINT chk_month_range           CHECK (order_month BETWEEN 1 AND 12),
    CONSTRAINT chk_quarter_range         CHECK (order_quarter BETWEEN 1 AND 4),
    CONSTRAINT chk_ship_date_after_order CHECK (ship_date >= order_date)
);

CREATE INDEX idx_sales_order_date    ON sales_data (order_date);
CREATE INDEX idx_sales_order_year    ON sales_data (order_year);
CREATE INDEX idx_sales_region        ON sales_data (region);
CREATE INDEX idx_sales_state         ON sales_data (state);
CREATE INDEX idx_sales_category      ON sales_data (category);
CREATE INDEX idx_sales_sub_category  ON sales_data (sub_category);
CREATE INDEX idx_sales_segment       ON sales_data (segment);
CREATE INDEX idx_sales_ship_mode     ON sales_data (ship_mode);
CREATE INDEX idx_sales_customer_id   ON sales_data (customer_id);
CREATE INDEX idx_sales_product_id    ON sales_data (product_id);
CREATE INDEX idx_sales_is_loss       ON sales_data (is_loss);
CREATE INDEX idx_sales_discount_tier ON sales_data (discount_tier);
CREATE INDEX idx_sales_profit        ON sales_data (profit);
CREATE INDEX idx_sales_year_month    ON sales_data (order_year, order_month);
CREATE INDEX idx_sales_city_state    ON sales_data (city, state);

COMMENT ON TABLE sales_data IS 'Flat denormalized sales table for analytics';
"""

cur.execute(flat_table_ddl)
conn.commit()
logger.info("Table 'sales_data' created with 29 columns, 15 indexes, 8 constraints")


# Step 5: Bulk import data into the flat table
section("5. Importing Data into sales_data")

flat_columns = [
    "row_id", "order_id", "order_date", "ship_date", "shipping_days",
    "ship_mode", "customer_id", "customer_name", "segment", "country",
    "city", "state", "postal_code", "region", "product_id", "category",
    "sub_category", "product_name", "sales", "quantity", "discount",
    "profit", "order_year", "order_month", "order_quarter", "order_day_name",
    "profit_margin", "is_loss", "discount_tier"
]

csv_to_db_col_map = {
    "Row ID": "row_id", "Order ID": "order_id", "Order Date": "order_date",
    "Ship Date": "ship_date", "Shipping_Days": "shipping_days",
    "Ship Mode": "ship_mode", "Customer ID": "customer_id",
    "Customer Name": "customer_name", "Segment": "segment", "Country": "country",
    "City": "city", "State": "state", "Postal Code": "postal_code",
    "Region": "region", "Product ID": "product_id", "Category": "category",
    "Sub-Category": "sub_category", "Product Name": "product_name",
    "Sales": "sales", "Quantity": "quantity", "Discount": "discount",
    "Profit": "profit", "Order_Year": "order_year", "Order_Month": "order_month",
    "Order_Quarter": "order_quarter", "Order_DayName": "order_day_name",
    "Profit_Margin": "profit_margin", "Is_Loss": "is_loss",
    "Discount_Tier": "discount_tier"
}

df_db = df.rename(columns=csv_to_db_col_map)

insert_sql = sql.SQL(
    "INSERT INTO sales_data ({cols}) VALUES ({placeholders})"
).format(
    cols=sql.SQL(", ").join(sql.Identifier(c) for c in flat_columns),
    placeholders=sql.SQL(", ").join(sql.Placeholder() for _ in flat_columns)
)

start_time = time.time()
total_inserted = 0

for batch_start in range(0, len(df_db), BATCH_SIZE):
    batch = df_db.iloc[batch_start:batch_start + BATCH_SIZE]
    rows = []
    for _, row in batch.iterrows():
        vals = []
        for col in flat_columns:
            v = row[col]
            if pd.isna(v):
                vals.append(None)
            elif col in ("order_date", "ship_date"):
                vals.append(v.date() if hasattr(v, "date") else v)
            elif col in ("sales", "profit", "profit_margin", "discount"):
                vals.append(float(v))
            elif col in ("row_id", "shipping_days", "quantity",
                         "order_year", "order_month", "order_quarter", "is_loss"):
                vals.append(int(v))
            else:
                vals.append(str(v))
        rows.append(tuple(vals))

    extras.execute_batch(cur, insert_sql, rows)
    conn.commit()
    total_inserted += len(rows)
    logger.debug(f"  Batch inserted rows {batch_start+1}-{batch_start+len(rows)}")

elapsed = time.time() - start_time
logger.info(f"Inserted {total_inserted:,} rows in {elapsed:.2f}s "
            f"({total_inserted/elapsed:,.0f} rows/sec)")


# Step 6: Create the star schema (dimensions + fact table)
section("6. Creating Star Schema")

star_ddl = """
CREATE TABLE dim_customer (
    customer_sk     SERIAL          PRIMARY KEY,
    customer_id     VARCHAR(20)     NOT NULL UNIQUE,
    customer_name   VARCHAR(100)    NOT NULL,
    segment         VARCHAR(20)     NOT NULL
);

CREATE TABLE dim_product (
    product_sk      SERIAL          PRIMARY KEY,
    product_id      VARCHAR(30)     NOT NULL UNIQUE,
    product_name    TEXT            NOT NULL,
    category        VARCHAR(30)     NOT NULL,
    sub_category    VARCHAR(30)     NOT NULL
);

CREATE TABLE dim_geography (
    geography_sk    SERIAL          PRIMARY KEY,
    postal_code     VARCHAR(10)     NOT NULL UNIQUE,
    city            VARCHAR(100)    NOT NULL,
    state           VARCHAR(50)     NOT NULL,
    country         VARCHAR(50)     NOT NULL DEFAULT 'United States',
    region          VARCHAR(20)     NOT NULL
);

CREATE TABLE dim_date (
    date_sk         SERIAL          PRIMARY KEY,
    full_date       DATE            NOT NULL UNIQUE,
    year            SMALLINT        NOT NULL,
    quarter         SMALLINT        NOT NULL,
    month           SMALLINT        NOT NULL,
    month_name      VARCHAR(10)     NOT NULL,
    day_of_month    SMALLINT        NOT NULL,
    day_of_week     SMALLINT        NOT NULL,
    day_name        VARCHAR(10)     NOT NULL,
    is_weekend      BOOLEAN         NOT NULL
);

CREATE TABLE dim_ship_mode (
    ship_mode_sk    SERIAL          PRIMARY KEY,
    ship_mode       VARCHAR(20)     NOT NULL UNIQUE
);

CREATE TABLE fact_sales (
    sale_id         INTEGER         PRIMARY KEY,
    order_id        VARCHAR(20)     NOT NULL,
    customer_sk     INTEGER         NOT NULL REFERENCES dim_customer(customer_sk),
    product_sk      INTEGER         NOT NULL REFERENCES dim_product(product_sk),
    geography_sk    INTEGER         NOT NULL REFERENCES dim_geography(geography_sk),
    order_date_sk   INTEGER         NOT NULL REFERENCES dim_date(date_sk),
    ship_date_sk    INTEGER         NOT NULL REFERENCES dim_date(date_sk),
    ship_mode_sk    INTEGER         NOT NULL REFERENCES dim_ship_mode(ship_mode_sk),
    sales           NUMERIC(12,4)   NOT NULL,
    quantity         SMALLINT        NOT NULL,
    discount        NUMERIC(4,2)    NOT NULL,
    profit          NUMERIC(12,4)   NOT NULL,
    shipping_days   SMALLINT        NOT NULL,
    profit_margin   NUMERIC(8,4)    NOT NULL,
    is_loss         SMALLINT        NOT NULL,
    discount_tier   VARCHAR(30)     NOT NULL
);

CREATE INDEX idx_fact_customer   ON fact_sales (customer_sk);
CREATE INDEX idx_fact_product    ON fact_sales (product_sk);
CREATE INDEX idx_fact_geography  ON fact_sales (geography_sk);
CREATE INDEX idx_fact_order_date ON fact_sales (order_date_sk);
CREATE INDEX idx_fact_ship_date  ON fact_sales (ship_date_sk);
CREATE INDEX idx_fact_ship_mode  ON fact_sales (ship_mode_sk);
CREATE INDEX idx_fact_order_id   ON fact_sales (order_id);
CREATE INDEX idx_fact_profit     ON fact_sales (profit);
CREATE INDEX idx_fact_is_loss    ON fact_sales (is_loss);
"""

cur.execute(star_ddl)
conn.commit()
logger.info("Star schema created: 5 dimension tables + 1 fact table")


# Step 7: Populate dimension tables from the dataframe
section("7. Populating Dimension Tables")

# dim_customer - one row per unique customer
customers = df_db[["customer_id", "customer_name", "segment"]].drop_duplicates(
    subset=["customer_id"], keep="first").sort_values("customer_id")
cust_rows = [tuple(r) for r in customers.values]
extras.execute_batch(cur,
    "INSERT INTO dim_customer (customer_id, customer_name, segment) VALUES (%s, %s, %s)",
    cust_rows)
conn.commit()
logger.info(f"dim_customer: {len(cust_rows):,} rows inserted")

# dim_product - one row per unique product
products = df_db[["product_id", "product_name", "category", "sub_category"]].drop_duplicates(
    subset=["product_id"], keep="first").sort_values("product_id")
prod_rows = [tuple(r) for r in products.values]
extras.execute_batch(cur,
    "INSERT INTO dim_product (product_id, product_name, category, sub_category) VALUES (%s, %s, %s, %s)",
    prod_rows)
conn.commit()
logger.info(f"dim_product: {len(prod_rows):,} rows inserted")

# dim_geography - one row per postal code
geo = df_db[["postal_code", "city", "state", "country", "region"]].drop_duplicates(
    subset=["postal_code"], keep="first").sort_values("postal_code")
geo_rows = [tuple(r) for r in geo.values]
extras.execute_batch(cur,
    "INSERT INTO dim_geography (postal_code, city, state, country, region) VALUES (%s, %s, %s, %s, %s)",
    geo_rows)
conn.commit()
logger.info(f"dim_geography: {len(geo_rows):,} rows inserted")

# dim_date - one row per unique date (from both order and ship dates)
all_dates = pd.concat([df["Order Date"], df["Ship Date"]]).drop_duplicates().sort_values()
date_rows = []
for d in all_dates:
    date_rows.append((
        d.date(), d.year, (d.month - 1) // 3 + 1, d.month,
        d.strftime("%B"), d.day, d.weekday() + 1, d.strftime("%A"),
        d.weekday() >= 5
    ))
extras.execute_batch(cur,
    """INSERT INTO dim_date (full_date, year, quarter, month, month_name,
       day_of_month, day_of_week, day_name, is_weekend)
       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
    date_rows)
conn.commit()
logger.info(f"dim_date: {len(date_rows):,} rows inserted")

# dim_ship_mode - the 4 shipping methods
ship_modes = sorted(df["Ship Mode"].unique())
for mode in ship_modes:
    cur.execute("INSERT INTO dim_ship_mode (ship_mode) VALUES (%s)", (mode,))
conn.commit()
logger.info(f"dim_ship_mode: {len(ship_modes)} rows inserted")


# Step 8: Populate the fact table using surrogate key lookups
section("8. Populating Fact Table (fact_sales)")

# Build lookup dicts for surrogate keys
cur.execute("SELECT customer_id, customer_sk FROM dim_customer")
cust_sk = dict(cur.fetchall())

cur.execute("SELECT product_id, product_sk FROM dim_product")
prod_sk = dict(cur.fetchall())

cur.execute("SELECT postal_code, geography_sk FROM dim_geography")
geo_sk = dict(cur.fetchall())

cur.execute("SELECT full_date, date_sk FROM dim_date")
date_sk = {str(k): v for k, v in cur.fetchall()}

cur.execute("SELECT ship_mode, ship_mode_sk FROM dim_ship_mode")
mode_sk = dict(cur.fetchall())

# Build and insert fact rows
fact_rows = []
for _, row in df_db.iterrows():
    fact_rows.append((
        int(row["row_id"]),
        str(row["order_id"]),
        cust_sk[str(row["customer_id"])],
        prod_sk[str(row["product_id"])],
        geo_sk[str(row["postal_code"])],
        date_sk[str(row["order_date"].date())],
        date_sk[str(row["ship_date"].date())],
        mode_sk[str(row["ship_mode"])],
        float(row["sales"]),
        int(row["quantity"]),
        float(row["discount"]),
        float(row["profit"]),
        int(row["shipping_days"]),
        float(row["profit_margin"]),
        int(row["is_loss"]),
        str(row["discount_tier"])
    ))

start_time = time.time()
for batch_start in range(0, len(fact_rows), BATCH_SIZE):
    batch = fact_rows[batch_start:batch_start + BATCH_SIZE]
    extras.execute_batch(cur,
        """INSERT INTO fact_sales
           (sale_id, order_id, customer_sk, product_sk, geography_sk,
            order_date_sk, ship_date_sk, ship_mode_sk,
            sales, quantity, discount, profit, shipping_days,
            profit_margin, is_loss, discount_tier)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
        batch)
    conn.commit()

elapsed = time.time() - start_time
logger.info(f"fact_sales: {len(fact_rows):,} rows inserted in {elapsed:.2f}s "
            f"({len(fact_rows)/elapsed:,.0f} rows/sec)")


# Step 9: Create analytical views for common queries
section("9. Creating Analytical Views")

views_sql = """
CREATE OR REPLACE VIEW v_monthly_sales AS
SELECT
    order_year, order_month,
    COUNT(*)              AS transactions,
    SUM(sales)            AS total_sales,
    SUM(profit)           AS total_profit,
    AVG(profit_margin)    AS avg_margin,
    SUM(is_loss)          AS loss_transactions
FROM sales_data
GROUP BY order_year, order_month
ORDER BY order_year, order_month;

CREATE OR REPLACE VIEW v_regional_performance AS
SELECT
    region, state,
    COUNT(*)              AS transactions,
    SUM(sales)            AS total_sales,
    SUM(profit)           AS total_profit,
    ROUND(AVG(profit_margin), 2) AS avg_margin_pct,
    ROUND(SUM(is_loss)::NUMERIC / COUNT(*) * 100, 2) AS loss_rate_pct
FROM sales_data
GROUP BY region, state
ORDER BY total_sales DESC;

CREATE OR REPLACE VIEW v_category_performance AS
SELECT
    category, sub_category,
    COUNT(*)              AS transactions,
    SUM(sales)            AS total_sales,
    SUM(profit)           AS total_profit,
    ROUND(AVG(profit_margin), 2) AS avg_margin_pct,
    SUM(is_loss)          AS loss_count
FROM sales_data
GROUP BY category, sub_category
ORDER BY total_sales DESC;

CREATE OR REPLACE VIEW v_top_customers AS
SELECT
    customer_id, customer_name, segment,
    COUNT(*)              AS order_count,
    SUM(sales)            AS total_spent,
    SUM(profit)           AS total_profit_generated,
    ROUND(AVG(sales), 2)  AS avg_order_value
FROM sales_data
GROUP BY customer_id, customer_name, segment
ORDER BY total_spent DESC
LIMIT 100;
"""

cur.execute(views_sql)
conn.commit()
logger.info("Created 4 analytical views: v_monthly_sales, v_regional_performance, "
            "v_category_performance, v_top_customers")


# Step 10: Run verification checks
section("10. Data Import Verification")

checks_passed = 0
checks_total  = 0

def verify(description, query, expected=None):
    global checks_passed, checks_total
    checks_total += 1
    cur.execute(query)
    result = cur.fetchone()[0]
    status = "PASS" if (expected is None or str(result) == str(expected)) else "FAIL"
    if status == "PASS":
        checks_passed += 1
    logger.info(f"  [{status}] {description}: {result:,}"
                f"{'  (expected: ' + str(expected) + ')' if expected is not None and status == 'FAIL' else ''}")
    return result

# Row counts
logger.info("-- Row Count Verification --")
verify("sales_data row count",
       "SELECT COUNT(*) FROM sales_data", len(df))
verify("fact_sales row count",
       "SELECT COUNT(*) FROM fact_sales", len(df))
verify("dim_customer row count",
       "SELECT COUNT(*) FROM dim_customer", len(customers))
verify("dim_product row count",
       "SELECT COUNT(*) FROM dim_product", len(products))
verify("dim_geography row count",
       "SELECT COUNT(*) FROM dim_geography", len(geo))
verify("dim_date row count",
       "SELECT COUNT(*) FROM dim_date", len(date_rows))
verify("dim_ship_mode row count",
       "SELECT COUNT(*) FROM dim_ship_mode", len(ship_modes))

# Aggregate totals match CSV
logger.info("-- Aggregate Consistency (Flat vs CSV) --")
csv_total_sales  = round(df["Sales"].sum(), 2)
csv_total_profit = round(df["Profit"].sum(), 2)

verify("Total Sales (sales_data)",
       "SELECT ROUND(SUM(sales)::NUMERIC, 2) FROM sales_data", csv_total_sales)
verify("Total Profit (sales_data)",
       "SELECT ROUND(SUM(profit)::NUMERIC, 2) FROM sales_data", csv_total_profit)

# Flat table matches star schema
logger.info("-- Cross-Schema Consistency (Flat vs Star) --")
verify("Flat total sales matches star total",
       """SELECT CASE WHEN
           (SELECT SUM(sales) FROM sales_data) =
           (SELECT SUM(sales) FROM fact_sales)
           THEN 1 ELSE 0 END""", 1)
verify("Flat total profit matches star total",
       """SELECT CASE WHEN
           (SELECT SUM(profit) FROM sales_data) =
           (SELECT SUM(profit) FROM fact_sales)
           THEN 1 ELSE 0 END""", 1)

# Constraint and referential integrity
logger.info("-- Constraint & Integrity Checks --")
verify("No negative sales values",
       "SELECT COUNT(*) FROM sales_data WHERE sales < 0", 0)
verify("No negative quantities",
       "SELECT COUNT(*) FROM sales_data WHERE quantity <= 0", 0)
verify("No invalid discounts (>1)",
       "SELECT COUNT(*) FROM sales_data WHERE discount > 1", 0)
verify("No ship before order",
       "SELECT COUNT(*) FROM sales_data WHERE ship_date < order_date", 0)
verify("Orphaned fact rows (customer)",
       """SELECT COUNT(*) FROM fact_sales f
          LEFT JOIN dim_customer c ON f.customer_sk = c.customer_sk
          WHERE c.customer_sk IS NULL""", 0)
verify("Orphaned fact rows (product)",
       """SELECT COUNT(*) FROM fact_sales f
          LEFT JOIN dim_product p ON f.product_sk = p.product_sk
          WHERE p.product_sk IS NULL""", 0)

# Sample data preview
logger.info("-- Sample Data Preview (first 3 rows) --")
cur.execute("""SELECT row_id, order_id, order_date, customer_name,
               category, sales, profit FROM sales_data ORDER BY row_id LIMIT 3""")
for row in cur.fetchall():
    logger.info(f"  Row {row[0]}: {row[1]} | {row[2]} | {row[3]} | {row[4]} | "
                f"${row[5]:,.2f} | ${row[6]:,.2f}")

# Table sizes
logger.info("-- Table Sizes --")
tables = ["sales_data", "fact_sales", "dim_customer", "dim_product",
          "dim_geography", "dim_date", "dim_ship_mode"]
for tbl in tables:
    cur.execute(f"SELECT pg_size_pretty(pg_total_relation_size('{tbl}'))")
    size = cur.fetchone()[0]
    cur.execute(f"SELECT COUNT(*) FROM {tbl}")
    cnt = cur.fetchone()[0]
    logger.info(f"  {tbl:20s} -> {cnt:>6,} rows  |  {size}")


# Step 11: Print final summary
section("11. Import Summary")

logger.info(f"Database         : {DB_NAME}")
logger.info(f"Host             : {DB_HOST}:{DB_PORT}")
logger.info(f"User             : {DB_USER}")
logger.info(f"CSV Source       : {CSV_FILE} ({len(df):,} rows)")
logger.info(f"Flat Table       : sales_data ({len(df):,} rows, 29 cols)")
logger.info(f"Star Schema      : 5 dimensions + 1 fact table ({len(fact_rows):,} facts)")
logger.info(f"Views Created    : 4 analytical views")
logger.info(f"Verification     : {checks_passed}/{checks_total} checks passed")

if checks_passed == checks_total:
    logger.info("ALL VERIFICATION CHECKS PASSED - Database is ready!")
else:
    logger.warning(f"{checks_total - checks_passed} check(s) FAILED - review log")

cur.close()
conn.close()
logger.info("Connection closed.")
