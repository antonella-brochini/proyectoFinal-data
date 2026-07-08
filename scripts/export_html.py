"""
Export the dashboard as a standalone interactive HTML file.
Run:  python scripts/export_html.py
Output: dashboard.html (open in any browser)
"""

import os
import json
import numpy as np
import pandas as pd

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_PATH = os.path.join(PROJECT_ROOT, "data", "processed", "clean_data.csv")
OUT_PATH = os.path.join(PROJECT_ROOT, "dashboard.html")
TEMPLATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dashboard_template.html")

BLUE = "#2563eb"
GREEN = "#10b981"
AMBER = "#f59e0b"
RED = "#ef4444"
PURPLE = "#8b5cf6"

print("Loading data...")
df = pd.read_csv(DATA_PATH, encoding="utf-8")
df.columns = [c.strip().replace(" ", "_").replace("-", "_").lower() for c in df.columns]
df["order_date"] = pd.to_datetime(df["order_date"])

# KPIs
total_sales = df["sales"].sum()
total_profit = df["profit"].sum()
total_orders = df["order_id"].nunique()
total_customers = df["customer_id"].nunique()
avg_order = total_sales / total_orders
margin = total_profit / total_sales * 100
loss_count = int(df["is_loss"].sum())

# YoY
yoy = df.groupby("order_year").agg(revenue=("sales", "sum")).reset_index()
yoy["growth"] = yoy["revenue"].pct_change() * 100

# Monthly
df_m = df.copy()
df_m["ym_date"] = df_m["order_date"].dt.to_period("M").dt.to_timestamp()
mg = df_m.groupby("ym_date").agg(
    revenue=("sales", "sum"), profit=("profit", "sum"),
    orders=("order_id", "nunique")).reset_index().sort_values("ym_date")
mg["margin_pct"] = (mg["profit"] / mg["revenue"] * 100).round(1)
mg["ma3"] = mg["revenue"].rolling(3, min_periods=1).mean()

# Category
cat = df.groupby("category")["sales"].sum().reset_index()
# Region
reg = df.groupby("region").agg(sales=("sales", "sum"), profit=("profit", "sum")).reset_index().sort_values("sales")
# Top products
prod = df.groupby(["product_name", "category"]).agg(sales=("sales", "sum")).reset_index().nlargest(10, "sales")
# Top customers
cust = df.groupby(["customer_name", "segment"]).agg(sales=("sales", "sum")).reset_index().nlargest(10, "sales")
# Sub-category
subcat = df.groupby("sub_category").agg(profit=("profit", "sum")).reset_index().sort_values("profit")
# Heatmap
heatmap = df.groupby(["order_year", "order_month"])["sales"].sum().reset_index()
pivot = heatmap.pivot_table(index="order_year", columns="order_month", values="sales")
# Top states
state = df.groupby(["state", "region"]).agg(sales=("sales", "sum")).reset_index().nlargest(15, "sales")
# Discount
disc = df.groupby("discount_tier").agg(profit=("profit", "sum"), loss_rate=("is_loss", "mean")).reset_index()
disc["loss_rate"] = (disc["loss_rate"] * 100).round(1)
# Scatter
prod_all = df.groupby(["product_name", "category"]).agg(sales=("sales", "sum"), profit=("profit", "sum"), units=("quantity", "sum")).reset_index()
# US map
state_map = df.groupby(["state", "region"]).agg(sales=("sales", "sum"), profit=("profit", "sum")).reset_index()
# Customer histogram
cust_hist = df.groupby("customer_id").agg(sales=("sales", "sum")).reset_index()["sales"].round(0).tolist()

# YoY cards
yoy_html = ""
for _, row in yoy.iterrows():
    g = row["growth"]
    gs = f"{g:.1f}%" if pd.notna(g) else "--"
    gc = "#10b981" if pd.notna(g) and g >= 0 else "#ef4444"
    yoy_html += f'<div class="kpi-card"><div class="kpi-label">{int(row["order_year"])}</div><div class="kpi-value">${row["revenue"]:,.0f}</div><div class="kpi-delta" style="color:{gc}">{gs}</div></div>\n'

# Build data JSON
js_data = {
    "monthly": {"dates": [str(d.date()) for d in mg["ym_date"]], "revenue": mg["revenue"].round(0).tolist(), "profit": mg["profit"].round(0).tolist(), "ma3": mg["ma3"].round(0).tolist(), "margin": mg["margin_pct"].tolist()},
    "cat": {"labels": cat["category"].tolist(), "values": cat["sales"].round(0).tolist()},
    "reg": {"regions": reg["region"].tolist(), "sales": reg["sales"].round(0).tolist(), "profit": reg["profit"].round(0).tolist()},
    "prod": {"names": [n[:45] for n in prod["product_name"]], "sales": prod["sales"].round(0).tolist(), "cats": prod["category"].tolist()},
    "cust": {"names": cust["customer_name"].tolist(), "sales": cust["sales"].round(0).tolist(), "segs": cust["segment"].tolist()},
    "subcat": {"names": subcat["sub_category"].tolist(), "profit": subcat["profit"].round(0).tolist()},
    "heat": {"z": (pivot.values / 1000).round(1).tolist(), "years": [int(y) for y in pivot.index], "months": ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]},
    "state": {"states": state["state"].tolist(), "sales": state["sales"].round(0).tolist(), "regions": state["region"].tolist()},
    "disc": {"tiers": disc["discount_tier"].tolist(), "profit": disc["profit"].round(0).tolist(), "loss_rate": disc["loss_rate"].tolist()},
    "scatter": {"names": prod_all["product_name"].tolist(), "cats": prod_all["category"].tolist(), "sales": prod_all["sales"].round(0).tolist(), "profit": prod_all["profit"].round(0).tolist(), "units": prod_all["units"].tolist()},
    "map": {"states": [s[:2].upper() for s in state_map["state"]], "full_names": state_map["state"].tolist(), "sales": state_map["sales"].round(0).tolist(), "profit": state_map["profit"].round(0).tolist(), "regions": state_map["region"].tolist()},
    "custHist": cust_hist
}

# Write template HTML (not an f-string, so JS braces are safe)
print("Writing dashboard.html...")
html = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Superstore Sales Dashboard</title>
<script src="https://cdn.plot.ly/plotly-2.35.0.min.js"></script>
<style>
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background:#f0f2f6; }
.header { background:#1b3a5c; color:white; padding:28px 40px; }
.header h1 { font-size:1.7rem; font-weight:700; }
.header p { font-size:0.85rem; color:#aaa; margin-top:4px; }
.container { max-width:1400px; margin:0 auto; padding:20px; }
.row { display:flex; gap:16px; flex-wrap:wrap; margin-bottom:16px; }
.card { background:white; border-radius:12px; padding:16px; box-shadow:0 2px 8px rgba(0,0,0,0.06); flex:1; min-width:420px; }
.card-full { background:white; border-radius:12px; padding:16px; box-shadow:0 2px 8px rgba(0,0,0,0.06); width:100%; margin-bottom:16px; }
.kpi-row { display:grid; grid-template-columns:repeat(7,1fr); gap:10px; margin-bottom:20px; }
.yoy-row { display:grid; grid-template-columns:repeat(4,1fr); gap:10px; margin-bottom:20px; }
.kpi-card { background:#111; border-radius:10px; padding:16px 10px; text-align:center; box-shadow:0 2px 6px rgba(0,0,0,0.3); }
.kpi-label { font-size:0.7rem; color:#aaa; text-transform:uppercase; letter-spacing:0.5px; margin-bottom:6px; }
.kpi-value { font-size:1.3rem; font-weight:700; color:#fff; }
.kpi-delta { font-size:0.8rem; color:#10b981; margin-top:4px; }
.section-title { font-size:1.2rem; font-weight:700; color:#1b3a5c; margin-bottom:12px; padding-bottom:6px; border-bottom:2px solid #e0e0e0; }
.tab-nav { display:flex; gap:4px; margin-bottom:16px; flex-wrap:wrap; }
.tab-btn { padding:10px 22px; border:none; border-radius:8px; cursor:pointer; font-size:0.9rem; font-weight:600; background:#ddd; color:#555; transition:all 0.2s; }
.tab-btn.active { background:#1b3a5c; color:white; }
.tab-btn:hover { background:#2563eb; color:white; }
.tab-content { display:none; }
.tab-content.active { display:block; }
.chart { width:100%; height:400px; }
.chart-tall { width:100%; height:500px; }
.footer { text-align:center; padding:25px; color:#999; font-size:0.8rem; }
@media (max-width:900px) { .kpi-row{grid-template-columns:repeat(3,1fr);} .yoy-row{grid-template-columns:repeat(2,1fr);} .card{min-width:100%;} }
</style>
</head>
<body>
<div class="header">
    <h1>Superstore Sales Dashboard</h1>
    <p>Performance analytics for FY 2014-2017 | 9,986 transactions | Data: clean_data.csv</p>
</div>
<div class="container">
<div class="tab-nav">
    <button class="tab-btn active" onclick="showTab('overview',this)">Executive Overview</button>
    <button class="tab-btn" onclick="showTab('trends',this)">Sales Trends</button>
    <button class="tab-btn" onclick="showTab('products',this)">Products</button>
    <button class="tab-btn" onclick="showTab('customers',this)">Customers</button>
    <button class="tab-btn" onclick="showTab('geography',this)">Geography</button>
</div>

<div id="overview" class="tab-content active">
<div class="kpi-row">__KPI_CARDS__</div>
<div class="row">
    <div class="card"><div id="c_monthly" class="chart"></div></div>
    <div class="card"><div id="c_category" class="chart"></div></div>
</div>
<div class="row">
    <div class="card"><div id="c_region" class="chart"></div></div>
    <div class="card"><div id="c_discount" class="chart"></div></div>
</div>
</div>

<div id="trends" class="tab-content">
<div class="section-title">Year-over-Year Performance</div>
<div class="yoy-row">__YOY_CARDS__</div>
<div class="card-full"><div id="c_revmargin" class="chart"></div></div>
<div class="card-full"><div id="c_heatmap" class="chart-tall"></div></div>
</div>

<div id="products" class="tab-content">
<div class="row">
    <div class="card"><div id="c_topprods" class="chart-tall"></div></div>
    <div class="card"><div id="c_subcat" class="chart-tall"></div></div>
</div>
<div class="card-full"><div id="c_scatter" class="chart-tall"></div></div>
</div>

<div id="customers" class="tab-content">
<div class="row">
    <div class="card"><div id="c_topcusts" class="chart-tall"></div></div>
    <div class="card"><div id="c_custhist" class="chart-tall"></div></div>
</div>
</div>

<div id="geography" class="tab-content">
<div class="card-full"><div id="c_usmap" class="chart-tall"></div></div>
<div class="card-full"><div id="c_topstates" class="chart-tall"></div></div>
</div>
</div>

<div class="footer">Superstore Sales Dashboard | Data: clean_data.csv (9,986 transactions, 2014-2017) | Built with Plotly</div>

<script>
var D = __DATA_JSON__;
var L = { paper_bgcolor:'rgba(0,0,0,0)', plot_bgcolor:'rgba(0,0,0,0)', margin:{l:50,r:30,t:45,b:40}, font:{family:'Segoe UI, sans-serif'} };
var C = { responsive:true, displayModeBar:false };

function mc(id, data, lay) {
    var merged = Object.assign({}, L, lay);
    Plotly.newPlot(id, data, merged, C);
}

mc('c_monthly', [
    { x:D.monthly.dates, y:D.monthly.revenue, type:'scatter', mode:'lines+markers', name:'Revenue', line:{color:'#2563eb',width:2} },
    { x:D.monthly.dates, y:D.monthly.profit, type:'scatter', mode:'lines+markers', name:'Profit', line:{color:'#10b981',width:2} },
    { x:D.monthly.dates, y:D.monthly.ma3, type:'scatter', mode:'lines', name:'3M Avg', line:{color:'#ef4444',width:1.5,dash:'dash'} }
], { title:'Monthly Revenue & Profit Trend', yaxis:{tickprefix:'$',tickformat:',.0f'} });

mc('c_category', [
    { labels:D.cat.labels, values:D.cat.values, type:'pie', hole:0.55, textinfo:'percent+label', marker:{colors:['#2563eb','#f59e0b','#10b981']} }
], { title:'Revenue by Category', showlegend:false });

mc('c_region', [
    { y:D.reg.regions, x:D.reg.sales, type:'bar', name:'Sales', orientation:'h', marker:{color:'#2563eb'} },
    { y:D.reg.regions, x:D.reg.profit, type:'bar', name:'Profit', orientation:'h', marker:{color:'#10b981'} }
], { title:'Sales vs Profit by Region', barmode:'group', xaxis:{tickprefix:'$',tickformat:',.0f'} });

mc('c_discount', [
    { x:D.disc.tiers, y:D.disc.profit, type:'bar', name:'Profit', marker:{color:D.disc.profit.map(function(v){return v>=0?'#10b981':'#ef4444'})} },
    { x:D.disc.tiers, y:D.disc.loss_rate, type:'scatter', mode:'lines+markers', name:'Loss Rate %', yaxis:'y2', line:{color:'#ef4444',width:2} }
], { title:'Discount Impact on Profitability', yaxis:{title:'Profit ($)',tickprefix:'$',tickformat:',.0f'}, yaxis2:{title:'Loss Rate %',overlaying:'y',side:'right',ticksuffix:'%'} });

mc('c_revmargin', [
    { x:D.monthly.dates, y:D.monthly.revenue, type:'bar', name:'Revenue', marker:{color:'#2563eb',opacity:0.6} },
    { x:D.monthly.dates, y:D.monthly.margin, type:'scatter', mode:'lines+markers', name:'Margin %', yaxis:'y2', line:{color:'#10b981',width:2.5} }
], { title:'Revenue & Profit Margin Over Time', yaxis:{title:'Revenue ($)',tickprefix:'$',tickformat:',.0f'}, yaxis2:{title:'Margin %',overlaying:'y',side:'right',ticksuffix:'%'} });

mc('c_heatmap', [
    { z:D.heat.z, x:D.heat.months, y:D.heat.years, type:'heatmap', colorscale:'YlOrRd', text:D.heat.z.map(function(r){return r.map(function(v){return v+'K'})}), texttemplate:'%{text}', hovertemplate:'Year %{y}, %{x}: $%{text}<extra></extra>' }
], { title:'Monthly Revenue Heatmap ($K)' });

mc('c_topprods', [
    { x:D.prod.sales, y:D.prod.names, type:'bar', orientation:'h', marker:{color:D.prod.cats.map(function(c){return c==='Technology'?'#2563eb':c==='Furniture'?'#f59e0b':'#10b981'})}, text:D.prod.sales.map(function(v){return '$'+v.toLocaleString()}), textposition:'outside' }
], { title:'Top 10 Products by Revenue', yaxis:{autorange:'reversed'}, xaxis:{tickprefix:'$',tickformat:',.0f'} });

mc('c_subcat', [
    { x:D.subcat.profit, y:D.subcat.names, type:'bar', orientation:'h', marker:{color:D.subcat.profit.map(function(v){return v>=0?'#10b981':'#ef4444'})}, text:D.subcat.profit.map(function(v){return '$'+v.toLocaleString()}), textposition:'outside' }
], { title:'Profit by Sub-Category', yaxis:{autorange:'reversed'}, xaxis:{zeroline:true,zerolinecolor:'black',tickprefix:'$',tickformat:',.0f'} });

mc('c_scatter', [
    { x:D.scatter.sales, y:D.scatter.profit, type:'scatter', mode:'markers', text:D.scatter.names, marker:{size:D.scatter.units.map(function(v){return Math.max(Math.sqrt(v)*3,5)}), color:D.scatter.cats.map(function(c){return c==='Technology'?'#2563eb':c==='Furniture'?'#f59e0b':'#10b981'}), opacity:0.6}, hovertemplate:'%{text}<br>Sales: $%{x:,.0f}<br>Profit: $%{y:,.0f}<extra></extra>' }
], { title:'Product Performance Matrix', xaxis:{tickprefix:'$',tickformat:',.0f',title:'Total Sales'}, yaxis:{tickprefix:'$',tickformat:',.0f',title:'Total Profit'} });

mc('c_topcusts', [
    { x:D.cust.sales, y:D.cust.names, type:'bar', orientation:'h', marker:{color:D.cust.segs.map(function(s){return s==='Consumer'?'#2563eb':s==='Corporate'?'#f59e0b':'#10b981'})}, text:D.cust.sales.map(function(v){return '$'+v.toLocaleString()}), textposition:'outside' }
], { title:'Top 10 Customers by Revenue', yaxis:{autorange:'reversed'}, xaxis:{tickprefix:'$',tickformat:',.0f'} });

mc('c_custhist', [
    { x:D.custHist, type:'histogram', nbinsx:40, marker:{color:'#2563eb',opacity:0.7} }
], { title:'Customer Revenue Distribution', xaxis:{title:'Total Revenue ($)',tickprefix:'$',tickformat:',.0f'}, yaxis:{title:'Number of Customers'} });

mc('c_usmap', [
    { type:'choropleth', locations:D.map.states, locationmode:'USA-states', scope:'usa', z:D.map.sales, colorscale:'Blues', text:D.map.full_names, hovertemplate:'%{text}<br>Revenue: $%{z:,.0f}<extra></extra>', colorbar:{tickprefix:'$',tickformat:',.0f'} }
], { title:'Revenue by State', geo:{scope:'usa'} });

mc('c_topstates', [
    { x:D.state.sales, y:D.state.states, type:'bar', orientation:'h', marker:{color:D.state.regions.map(function(r){return r==='West'?'#2563eb':r==='East'?'#f59e0b':r==='Central'?'#10b981':'#8b5cf6'})}, text:D.state.sales.map(function(v){return '$'+v.toLocaleString()}), textposition:'outside' }
], { title:'Top 15 States by Revenue', yaxis:{autorange:'reversed'}, xaxis:{tickprefix:'$',tickformat:',.0f'} });

function showTab(id, btn) {
    document.querySelectorAll('.tab-content').forEach(function(el){el.classList.remove('active')});
    document.querySelectorAll('.tab-btn').forEach(function(el){el.classList.remove('active')});
    document.getElementById(id).classList.add('active');
    btn.classList.add('active');
    setTimeout(function(){ window.dispatchEvent(new Event('resize')); }, 100);
}
</script>
</body>
</html>"""

# Build KPI cards HTML
kpi_cards = f"""
<div class="kpi-card"><div class="kpi-label">Total Sales</div><div class="kpi-value">${total_sales:,.0f}</div></div>
<div class="kpi-card"><div class="kpi-label">Total Profit</div><div class="kpi-value">${total_profit:,.0f}</div><div class="kpi-delta">{margin:.1f}% margin</div></div>
<div class="kpi-card"><div class="kpi-label">Total Orders</div><div class="kpi-value">{total_orders:,}</div></div>
<div class="kpi-card"><div class="kpi-label">Customers</div><div class="kpi-value">{total_customers:,}</div></div>
<div class="kpi-card"><div class="kpi-label">Avg Order Value</div><div class="kpi-value">${avg_order:,.2f}</div></div>
<div class="kpi-card"><div class="kpi-label">Profit Margin</div><div class="kpi-value">{margin:.1f}%</div></div>
<div class="kpi-card"><div class="kpi-label">Loss Transactions</div><div class="kpi-value">{loss_count:,}</div><div class="kpi-delta" style="color:#ef4444">{loss_count/len(df)*100:.1f}% loss rate</div></div>
"""

# Substitute placeholders
html = html.replace("__KPI_CARDS__", kpi_cards.strip())
html = html.replace("__YOY_CARDS__", yoy_html.strip())
html = html.replace("__DATA_JSON__", json.dumps(js_data))

with open(OUT_PATH, "w", encoding="utf-8") as f:
    f.write(html)

size_mb = os.path.getsize(OUT_PATH) / (1024 * 1024)
print(f"Saved: {OUT_PATH} ({size_mb:.1f} MB)")
print("Open dashboard.html in any browser -- no server needed.")
