```md
# Phase 2: Comprensión del Dataset - Superstore Sales Dataset

---

# 1. Descripción General del Dataset

| Propiedad | Valor |
|------------|--------|
| **Archivo** | `Superstore sales dataset.csv` |
| **Codificación** | UTF-8 |
| **Total de filas** | 9,994 |
| **Total de columnas** | 21 |
| **Rango de fechas** | 3 de enero de 2014 – 30 de diciembre de 2017 (4 años completos) |
| **Cobertura geográfica** | Estados Unidos (un solo país) |
| **Dominio** | Retail / Comercio electrónico |
| **Granularidad** | Una fila representa un producto (line item) dentro de una orden de compra |

Este dataset simula datos transaccionales de ventas de una cadena minorista ficticia en Estados Unidos. Cada registro representa un producto incluido dentro de una orden de compra, mostrando todo el proceso desde que el cliente realiza el pedido hasta que este es enviado.

---

# 2. Diccionario de Columnas

## 2.1 Columnas de Identificación y Tiempo

| # | Columna | Tipo de dato | Descripción |
|---|----------|--------------|-------------|
| 1 | **Row ID** | Integer | Identificador secuencial único para cada registro (1–9,994). |
| 2 | **Order ID** | String | Identificador único de la orden. Formato: `{Prefix}-{Year}-{Sequence}` (ej.: `CA-2016-152156`). El prefijo puede ser `CA` o `US`. |
| 3 | **Order Date** | Date (String) | Fecha en la que se realizó la orden. Formato `D/M/YYYY` (ej.: `8/11/2016` = 8 de noviembre de 2016). |
| 4 | **Ship Date** | Date (String) | Fecha en la que la orden fue enviada. Formato `D/M/YYYY`. |
| 5 | **Ship Mode** | Categorical | Método de envío. Existen cuatro categorías: Standard Class (59.7%), Second Class (19.5%), First Class (15.4%) y Same Day (5.4%). |

## 2.2 Columnas del Cliente

| # | Columna | Tipo de dato | Descripción |
|---|----------|--------------|-------------|
| 6 | **Customer ID** | String | Identificador único del cliente. Formato `{Initials}-{5-digit number}` (ej.: `CG-12520`). |
| 7 | **Customer Name** | String | Nombre completo del cliente. Existen 793 clientes únicos distribuidos en 9,994 transacciones. |
| 8 | **Segment** | Categorical | Segmento del cliente. Tres categorías: Consumer (51.9%), Corporate (30.2%) y Home Office (17.8%). |

## 2.3 Columnas Geográficas

| # | Columna | Tipo de dato | Descripción |
|---|----------|--------------|-------------|
| 9 | **Country** | String | Siempre contiene el valor `United States`, por lo que el dataset corresponde a un único país. |
| 10 | **City** | String | Ciudad donde se realizó la venta. Contiene 531 ciudades únicas. |
| 11 | **State** | String | Estado de Estados Unidos. Incluye 49 estados (considerando Washington D.C.). |
| 12 | **Postal Code** | Integer | Código postal de cinco dígitos. Existen 631 códigos postales distintos y no presenta valores faltantes. |
| 13 | **Region** | Categorical | Región geográfica del país. Cuatro categorías: West (32.0%), East (28.5%), Central (23.2%) y South (16.2%). |

## 2.4 Columnas del Producto

| # | Columna | Tipo de dato | Descripción |
|---|----------|--------------|-------------|
| 14 | **Product ID** | String | Identificador único del producto. Formato `{Category}-{SubCat}-{Number}` (ej.: `FUR-BO-10001798`). Existen 1,862 productos únicos. |
| 15 | **Category** | Categorical | Categoría principal del producto. Tres categorías: Office Supplies (60.3%), Furniture (21.2%) y Technology (18.5%). |
| 16 | **Sub-Category** | Categorical | Subcategoría del producto. Contiene 17 categorías diferentes (por ejemplo: Binders, Paper, Phones, Chairs, etc.). |
| 17 | **Product Name** | String | Nombre descriptivo del producto. Existen 1,850 nombres únicos, ya que algunos productos comparten el mismo nombre. |

## 2.5 Columnas Financieras

| # | Columna | Tipo de dato | Descripción |
|---|----------|--------------|-------------|
| 18 | **Sales** | Float | Monto de ventas en dólares estadounidenses (USD). Rango: $0.44 – $22,638.48. Promedio: $229.86. |
| 19 | **Quantity** | Integer | Cantidad de unidades vendidas. Rango: 1–14. Promedio: 3.79 unidades. |
| 20 | **Discount** | Float | Descuento aplicado expresado como proporción. Rango: 0.00–0.80. Promedio: 0.156. |
| 21 | **Profit** | Float | Ganancia neta en USD. Rango: −$6,599.98 – $8,399.98. Promedio: $28.66. |

---

# 3. Evaluación de Valores Faltantes

| Columna | Valores faltantes | % |
|----------|:----------------:|:--:|
| Todas las columnas | 0 | 0.00% |

**Conclusión:** El dataset está completamente limpio en cuanto a valores faltantes. Ninguna de las 21 columnas presenta datos ausentes, por lo que no fue necesario aplicar técnicas de imputación.

---

# 4. Análisis del Formato de Fechas

### Formato detectado: `D/M/YYYY` (Día/Mes/Año)

| Propiedad | Order Date | Ship Date |
|------------|------------|-----------|
| Formato | `D/M/YYYY` | `D/M/YYYY` |
| Fechas convertidas correctamente | 9,994 / 9,994 (100%) | 9,994 / 9,994 (100%) |
| Fecha más antigua | 3 de enero de 2014 | 7 de enero de 2014 |
| Fecha más reciente | 30 de diciembre de 2017 | 5 de enero de 2018 |

> **Nota importante:** Aunque el dataset corresponde a Estados Unidos, las fechas están almacenadas utilizando el formato **día/mes/año (D/M/YYYY)** y no el formato estadounidense **mes/día/año (M/D/YYYY)**. Al importar los datos en herramientas como Excel o pandas es recomendable especificar `dayfirst=True` para evitar interpretaciones incorrectas (por ejemplo, `12/6/2016` corresponde al **12 de junio**, no al **6 de diciembre**).

### Métrica derivada: Duración del envío

| Métrica | Valor |
|---------|-------|
| Duración mínima | 0 días (Same Day) |
| Duración máxima | 7 días |
| Duración promedio | 4.0 días |
| Envíos antes de la compra | 0 |

La duración de los envíos es consistente con las categorías de **Ship Mode**. Los envíos **Same Day** ocurren el mismo día, **First Class** tarda aproximadamente entre 1 y 2 días, **Second Class** entre 3 y 4 días y **Standard Class** entre 5 y 7 días.

---

# 5. Análisis de Duplicados

| Verificación | Resultado |
|--------------|-----------|
| Filas completamente duplicadas | **0** |
| Combinaciones duplicadas de **Order ID + Product ID** | **8** |

**Conclusión:** No existen registros duplicados completos dentro del dataset. Las ocho combinaciones repetidas de **Order ID** y **Product ID** corresponden a casos válidos del negocio, donde un mismo producto aparece más de una vez dentro de una orden con diferentes cantidades u otras características.

---

# 6. Principales Observaciones sobre la Calidad de los Datos

## 6.1 Transacciones con Pérdidas (Negative Profit)

| Métrica | Valor |
|---------|-------|
| Registros con **Profit** negativo | 1,871 (18.7%) |
| Pérdida acumulada | **−$156,131.29** |

Casi una de cada cinco transacciones genera pérdidas para la empresa. Este comportamiento representa uno de los aspectos más relevantes del dataset y será un punto central durante el análisis exploratorio.

### 6.2 Distribución de **Discount**

| Métrica | Valor |
|---------|-------|
| Transacciones sin descuento | 4,798 (48.0%) |
| Descuento promedio | 15.6% |
| Descuento máximo | 80% |
| Niveles distintos de descuento | 12 |

Los descuentos se presentan en valores estandarizados (0.0, 0.1, 0.2, ..., 0.8), lo que indica que responden a una política comercial previamente definida y no a descuentos asignados de manera individual.

### 6.3 Outliers y Asimetría de las Distribuciones

| Métrica | Sales | Profit |
|----------|-------|--------|
| IQR | $192.66 | $27.64 |
| Outliers (criterio IQR) | 1,167 | 1,881 |
| Skewness | 12.973 | 7.561 |

Tanto **Sales** como **Profit** presentan una fuerte asimetría positiva (right skew). Esto significa que la mayoría de las transacciones corresponden a montos relativamente pequeños, mientras que unas pocas operaciones de gran tamaño elevan considerablemente el promedio.

Esta característica debe tenerse en cuenta al aplicar técnicas estadísticas o modelos predictivos, ya que podría ser conveniente utilizar transformaciones logarítmicas o métodos robustos frente a valores extremos.

### 6.4 Concentración Geográfica

Los tres estados con mayor cantidad de transacciones representan el **41.2%** del total del dataset:

- California: 2,001 registros (20.0%)
- New York: 1,128 registros (11.3%)
- Texas: 985 registros (9.9%)

Esta concentración geográfica deberá considerarse al interpretar los resultados del análisis regional.

---

# 7. Fortalezas y Limitaciones del Dataset

## Fortalezas

- Dataset completamente limpio, sin valores faltantes ni registros duplicados.
- Contiene 21 variables que abarcan dimensiones temporales, geográficas, de clientes, productos y métricas financieras.
- Incluye cuatro años completos de información, permitiendo realizar análisis de tendencias, estacionalidad y comparaciones interanuales.
- Representa un escenario de negocio realista al incluir transacciones con pérdidas, diferentes estrategias de descuentos y múltiples segmentos de clientes.

## Limitaciones

- Toda la información corresponde únicamente a Estados Unidos, por lo que no es posible realizar análisis internacionales.
- No incluye información demográfica de los clientes (edad, género, ingresos, etc.).
- No dispone del costo individual de los productos (COGS), por lo que solo se conocen **Sales** y **Profit**.
- Se trata de un dataset ficticio ampliamente utilizado con fines educativos (originalmente desarrollado por Tableau), por lo que no representa operaciones de una empresa real.
- La elevada asimetría de **Sales** y **Profit** puede afectar algunos análisis estadísticos si no se consideran técnicas apropiadas.

---

# 8. Resumen General del Dataset

| Métrica | Valor |
|----------|-------|
| Total de registros | 9,994 |
| Órdenes únicas | ~5,009 |
| Clientes únicos | 793 |
| Productos únicos | 1,862 |
| Estados cubiertos | 49 |
| Ciudades cubiertas | 531 |
| **Sales** total | ~$2,297,201 |
| **Profit** total | ~$286,397 |
| Margen promedio de ganancia | ~12.5% |
| Formato de fechas | D/M/YYYY |
| Valores faltantes | 0 |
| Filas duplicadas | 0 |

---

*Documento preparado como parte de la Fase 2: Comprensión del Dataset – Proyecto de Análisis de Ventas Superstore.*
```
