import os
import pandas as pd
import numpy as np

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
df = pd.read_csv(os.path.join(PROJECT_ROOT, 'data', 'raw', 'Superstore sales dataset.csv'), encoding='utf-8')

print('='*60)
print('DATASET SHAPE')
print('='*60)
print(f'Rows: {df.shape[0]}')
print(f'Columns: {df.shape[1]}')

print('\n' + '='*60)
print('COLUMN NAMES AND DTYPES')
print('='*60)
for col in df.columns:
    print(f'  {col:20s} -> {df[col].dtype}')

print('\n' + '='*60)
print('MISSING VALUES PER COLUMN')
print('='*60)
missing = df.isnull().sum()
for col in df.columns:
    pct = (missing[col] / len(df)) * 100
    print(f'  {col:20s} -> {missing[col]:5d} missing ({pct:.2f}%)')
print(f'\n  TOTAL missing cells: {missing.sum()}')

print('\n' + '='*60)
print('UNIQUE VALUES PER COLUMN')
print('='*60)
for col in df.columns:
    print(f'  {col:20s} -> {df[col].nunique():6d} unique')

print('\n' + '='*60)
print('NUMERIC COLUMNS SUMMARY')
print('='*60)
print(df.describe().to_string())

print('\n' + '='*60)
print('DATE COLUMNS ANALYSIS')
print('='*60)
print('Order Date sample values:', df['Order Date'].head(10).tolist())
print('Ship Date sample values:', df['Ship Date'].head(10).tolist())

order_dates = pd.to_datetime(df['Order Date'], format='%d/%m/%Y', errors='coerce')
ship_dates = pd.to_datetime(df['Ship Date'], format='%d/%m/%Y', errors='coerce')
print(f'Order Date - parsed (d/m/Y): {order_dates.notna().sum()} of {len(df)}')
print(f'  Date range: {order_dates.min()} to {order_dates.max()}')
print(f'Ship Date - parsed (d/m/Y): {ship_dates.notna().sum()} of {len(df)}')
print(f'  Date range: {ship_dates.min()} to {ship_dates.max()}')

# Check mixed formats
order_dates_us = pd.to_datetime(df['Order Date'], format='%m/%d/%Y', errors='coerce')
print(f'Order Date - parsed (m/d/Y): {order_dates_us.notna().sum()} of {len(df)}')

shipping_days = (ship_dates - order_dates).dt.days
print(f'\nShipping days stats:')
print(f'  Min: {shipping_days.min()}, Max: {shipping_days.max()}, Mean: {shipping_days.mean():.1f}')
print(f'  Negative shipping days: {(shipping_days < 0).sum()}')

print('\n' + '='*60)
print('CATEGORICAL COLUMNS BREAKDOWN')
print('='*60)
cat_cols = ['Ship Mode', 'Segment', 'Country', 'Region', 'Category', 'Sub-Category']
for col in cat_cols:
    print(f'\n{col} ({df[col].nunique()} unique):')
    vc = df[col].value_counts()
    for val, cnt in vc.items():
        print(f'  {str(val):30s} -> {cnt:5d} ({cnt/len(df)*100:.1f}%)')

print('\n' + '='*60)
print('STATE DISTRIBUTION (Top 15)')
print('='*60)
state_vc = df['State'].value_counts()
for val, cnt in state_vc.head(15).items():
    print(f'  {val:30s} -> {cnt:5d} ({cnt/len(df)*100:.1f}%)')
total_states = df['State'].nunique()
print(f'  Total unique states: {total_states}')

print('\n' + '='*60)
print('DUPLICATE ROWS')
print('='*60)
dupes = df.duplicated().sum()
print(f'  Exact duplicate rows: {dupes}')
dupes_subset = df.duplicated(subset=['Order ID', 'Product ID']).sum()
print(f'  Duplicate Order ID + Product ID combos: {dupes_subset}')

print('\n' + '='*60)
print('NEGATIVE PROFIT ROWS')
print('='*60)
neg_profit = df[df['Profit'] < 0]
print(f'  Rows with negative profit: {len(neg_profit)} ({len(neg_profit)/len(df)*100:.1f}%)')
print(f'  Total loss amount: ${neg_profit["Profit"].sum():,.2f}')

print('\n' + '='*60)
print('DISCOUNT ANALYSIS')
print('='*60)
zero_disc = (df['Discount'] == 0).sum()
print(f'  Zero discount rows: {zero_disc} ({zero_disc/len(df)*100:.1f}%)')
print(f'  Max discount: {df["Discount"].max()}')
print(f'  Mean discount: {df["Discount"].mean():.3f}')

print('\n' + '='*60)
print('POSTAL CODE ANALYSIS')
print('='*60)
pc_missing = df['Postal Code'].isnull().sum()
pc_unique = df['Postal Code'].nunique()
print(f'  Missing postal codes: {pc_missing}')
print(f'  Unique postal codes: {pc_unique}')

print('\n' + '='*60)
print('OUTLIER CHECK (Sales & Profit)')
print('='*60)
q1_sales = df['Sales'].quantile(0.25)
q3_sales = df['Sales'].quantile(0.75)
iqr_sales = q3_sales - q1_sales
outliers_sales = ((df['Sales'] < q1_sales - 1.5*iqr_sales) | (df['Sales'] > q3_sales + 1.5*iqr_sales)).sum()
print(f'  Sales IQR: {iqr_sales:.2f}, Outliers (1.5*IQR): {outliers_sales}')

q1_profit = df['Profit'].quantile(0.25)
q3_profit = df['Profit'].quantile(0.75)
iqr_profit = q3_profit - q1_profit
outliers_profit = ((df['Profit'] < q1_profit - 1.5*iqr_profit) | (df['Profit'] > q3_profit + 1.5*iqr_profit)).sum()
print(f'  Profit IQR: {iqr_profit:.2f}, Outliers (1.5*IQR): {outliers_profit}')

# Skewness
print(f'  Sales skewness: {df["Sales"].skew():.3f}')
print(f'  Profit skewness: {df["Profit"].skew():.3f}')
