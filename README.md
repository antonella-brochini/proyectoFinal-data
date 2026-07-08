# Superstore Sales Analytics

Un proyecto de análisis de datos de punta a punta construido sobre el dataset Superstore Sales. Cubre todo el flujo de trabajo, desde el análisis inicial del dataset sin procesar hasta machine learning avanzado, dashboards interactivos y reportes ejecutivos.

## Project Overview

Este proyecto analiza 9.986 transacciones minoristas realizadas durante 4 años (2014-2017), incluyendo 793 clientes, 1.862 productos y 49 estados de EE.UU. El objetivo es extraer insights accionables de negocio mediante un pipeline analítico estructurado:

1. **Data Profiling** - Comprensión de la estructura, tipos de datos, distribuciones y calidad del dataset
2. **Data Cleaning** - Pipeline de limpieza de 13 pasos con detección de outliers, imputación y creación de variables
3. **Data Warehousing** - Diseño de almacenamiento en PostgreSQL con dos esquemas complementarios (tabla plana + esquema estrella)
4. **SQL Analytics** - 37 consultas analíticas de nivel productivo organizadas en 9 dominios de negocio
5. **Advanced Analytics** - Descomposición de series temporales, clustering K-Means, segmentación RFM y modelos predictivos
6. **Visualization** - 28 gráficos estáticos, 4 dashboards interactivos en Plotly y una aplicación Streamlit
7. **Executive Reporting** - Recomendaciones estratégicas basadas en datos con acciones priorizadas

## Tech Stack

| Layer | Tools |
|---|---|
| **Language** | Python 3.14 |
| **Data Processing** | Pandas, NumPy |
| **Statistical Analysis** | SciPy, Statsmodels |
| **Machine Learning** | Scikit-learn (IsolationForest, KMeans, GradientBoosting, StandardScaler) |
| **Database** | PostgreSQL 18.4 |
| **Database Driver** | psycopg2-binary, python-dotenv |
| **Visualization (Static)** | Matplotlib, Seaborn |
| **Visualization (Interactive)** | Plotly |
| **Dashboard Framework** | Streamlit |
| **BI Tool** | Power BI Desktop |
| **Notebook** | Jupyter (IPython) |
| **Credentials** | Variables de entorno mediante .env |

## Project Structure
Data Analytics Project/
|
|-- data/
| |-- raw/ # Dataset original sin modificaciones
| | +-- Superstore sales dataset.csv
| +-- processed/ # Resultado limpio del pipeline
| +-- clean_data.csv
|
|-- scripts/
| |-- analyze_data.py # Fase 1: análisis del dataset y estadísticas
| |-- data_cleaning.py # Fase 2: pipeline de limpieza de 13 pasos
| |-- db_import.py # Fase 3: esquema PostgreSQL e importación de datos
| |-- business_analysis.sql # Fase 4: 37 consultas SQL analíticas
| |-- advanced_analytics.py # Fase 5: ML, clustering y forecasting
| |-- interactive_dashboard.py # Fase 5: dashboards HTML Plotly
| |-- showcase.py # Fase 4: generación de gráficos desde SQL
| |-- export_html.py # Exportador de dashboard HTML independiente
| |-- dashboard.py # Dashboard Streamlit en vivo
| |-- pull_metrics.py # Extracción de métricas PostgreSQL
| +-- superstore_pipeline.ipynb # Notebook Jupyter con todas las fases
|
|-- visualizations/
| |-- 01-12 (PNG) # Gráficos estándar de análisis
| +-- advanced/
| |-- 01-16 (PNG) # Gráficos de analítica avanzada
| +-- dashboard_.html # Dashboards interactivos Plotly
|
|-- Queries/
| +-- Query 1-8/ # Exportaciones SQL para Power BI con resultados CSV
|
|-- dashboards/ # Capturas de dashboards Power BI
| +-- 1-5.png
|
|-- docs/
| |-- Dataset Understanding.md # Documentación del dataset
| |-- sales_performance_review. # Reporte ejecutivo de negocio (PDF/DOCX)
|
|-- logs/ # Logs de ejecución de todas las etapas
| |-- analyze_data_output.txt
| |-- cleaning_log.txt
| |-- cleaning_summary.txt
| +-- db_import_log.txt
|
|-- dashboard.html # Dashboard HTML interactivo independiente
|-- .env # Credenciales locales (no versionadas)
|-- .env.example # Plantilla de credenciales
|-- .gitignore
+-- README.md

````md
## Pipeline Execution

Ejecuta cada fase secuencialmente desde la raíz del proyecto:

```bash
# Phase 1: Profile the raw dataset
python scripts/analyze_data.py > logs/analyze_data_output.txt

# Phase 2: Clean, validate, and engineer features
python scripts/data_cleaning.py

# Phase 3: Create database and import data
# (requires PostgreSQL running locally)
python scripts/db_import.py

# Phase 4: Generate charts from SQL analysis
python scripts/showcase.py

# Phase 5: Run advanced analytics (ML, forecasting)
python scripts/advanced_analytics.py

# Phase 5: Generate interactive Plotly dashboards
python scripts/interactive_dashboard.py

# Export standalone HTML dashboard
python scripts/export_html.py

# Launch Streamlit live dashboard
python -m streamlit run scripts/dashboard.py
```

## Database Schema

La base de datos PostgreSQL `working_database` contiene dos esquemas complementarios:

### Flat Table (sales_data)

29 columnas que abarcan toda la información transaccional y las variables derivadas en una única tabla. Está optimizada con 15 índices B-tree y 8 restricciones CHECK para garantizar la integridad de los datos.

### Star Schema

| Table | Rows | Description |
|---|---:|---|
| dim_customer | 793 | Un registro por cada cliente único |
| dim_product | 1,862 | Un registro por cada producto único |
| dim_geography | 631 | Un registro por cada código postal |
| dim_date | 1,434 | Dimensión calendario con metadatos |
| dim_ship_mode | 4 | Tabla de referencia para los métodos de envío |
| fact_sales | 9,986 | Tabla de hechos con las transacciones y claves foráneas |

### Analytical Views

- `v_monthly_sales` - Métricas agregadas mensuales de revenue y profit
- `v_regional_performance` - Rendimiento por región y estado
- `v_category_performance` - Análisis por categoría y subcategoría de productos
- `v_top_customers` - Ranking de los 100 mejores clientes según revenue total

## SQL Analytics Coverage

El archivo `business_analysis.sql` contiene 37 consultas organizadas en 9 secciones:

| Section | Queries | Techniques |
|---|---:|---|
| Executive KPIs | 2 | Funciones de agregación, window functions, LAG |
| Sales Analysis | 7 | Series temporales, patrones por día de la semana, participación de revenue |
| Product Analysis | 6 | Rankings, filtros HAVING, correlación entre descuentos |
| Customer Analysis | 5 | RFM (NTILE), retención por cohortes, estimación de CLV |
| Profitability | 4 | Percentiles, tablas cruzadas, impacto de descuentos |
| Shipping & Logistics | 3 | Distribución del rendimiento y comparación regional |
| Advanced Analytics | 6 | Pareto (80/20), medias móviles, crecimiento MoM, pivotes de estacionalidad |
| Star Schema | 3 | JOINs entre tablas de hechos y dimensiones |
| Executive Dashboard | 1 | CROSS JOIN con CTEs para generar un resumen ejecutivo en una sola consulta |

## Advanced Analytics

El script `advanced_analytics.py` aplica técnicas de ciencia de datos que van más allá del análisis SQL:

| Analysis | Methods |
|---|---|
| **Trend Analysis** | Descomposición aditiva de series temporales, pronóstico Holt-Winters, medias móviles de 3/6/12 meses e indicadores de momentum |
| **Customer Segmentation** | Clasificación RFM por cuartiles, clustering K-Means (método del codo, K=4), Customer Lifetime Value (proyección a 3 años) y mapas de calor de retención por cohortes |
| **Product Analysis** | Matriz BCG (Stars/Cash Cows/Question Marks/Dogs), clasificación ABC de inventario, elasticidad del precio (descuento vs. ventas/profit) y detección de productos comprados en conjunto |
| **Statistical Analysis** | Matriz de correlación, 4 pruebas de hipótesis (Welch's t-test), regresión Gradient Boosting (TimeSeriesSplit CV) y detección de anomalías mediante Isolation Forest |

**Resultado:** 16 gráficos de calidad profesional guardados en `visualizations/advanced/`.

## Key Findings

| Metric | Value |
|---|---:|
| Total Revenue | $2,295,510 |
| Total Profit | $286,014 |
| Overall Margin | 12.5% |
| Total Orders | 5,009 |
| Unique Customers | 793 |
| Loss Transactions | 1,870 (18.7%) |
| YoY Avg Growth | 27.2% |

### Critical Insights

- La categoría **Furniture** genera $741K en revenue, pero solo un margen del 2.5%. Las subcategorías **Tables** y **Bookcases** acumulan pérdidas netas por $21.2K.
- Los **descuentos superiores al 20%** presentan una tasa de pérdidas combinada del 94%, generando $135K de profit negativo en 1.392 transacciones.
- **Cinco estados** (Texas, Ohio, Pennsylvania, Illinois y North Carolina) generan en conjunto $500K en revenue, pero registran pérdidas de $78.4K.
- Existe una fuerte **dependencia del cuarto trimestre (Q4)**: el 38% del revenue anual y el 39% del profit se concentran en ese período.
- El segmento **Home Office** obtiene el mayor margen (14.0%), a pesar de ser el segmento con menor cantidad de clientes.

## Dashboards

### Streamlit Dashboard (Live)

Aplicación web interactiva con 5 pestañas, filtros en la barra lateral y actualización dinámica de los gráficos.

```bash
python -m streamlit run scripts/dashboard.py
```

Pestañas disponibles:

- Executive Overview
- Sales Trends
- Products
- Customers
- Geography

### Static HTML Dashboard (Offline)

Archivo HTML independiente con 14 gráficos interactivos de Plotly, sin necesidad de ejecutar un servidor.

```bash
python scripts/export_html.py

# Abrir dashboard.html en cualquier navegador
```

### Plotly Interactive Dashboards

Cuatro dashboards HTML independientes ubicados en `visualizations/advanced/`:

- `dashboard_sales.html` - Tendencias de revenue, análisis regional e impacto de descuentos.
- `dashboard_customers.html` - Gráfico RFM, análisis de segmentos y distribuciones.
- `dashboard_products.html` - Productos con mejor desempeño, profit por subcategoría y treemap.
- `dashboard_geotemporal.html` - Ranking de estados, mapas de calor y análisis de envíos.
````
