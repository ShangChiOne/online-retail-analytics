# Power BI build guide

This builds a Power BI version of the dashboard on the same cleaned data. It takes about 1–2 hours in Power BI Desktop (free).

## 1. Load the data (Get Data)

| Table | Source | Notes |
|---|---|---|
| `fact_sales` | `data/processed/transactions.parquet` | Get Data → **Parquet**. One row per product line; returns have negative `Quantity` / `Revenue` |
| `dim_customer` | `powerbi/data/dim_customer.csv` | RFM scores, segment, churn probability, revenue at risk |
| `dim_product` | `powerbi/data/dim_product.csv` | ABC class, return rate, revenue rank |
| `dim_date` | `powerbi/data/dim_date.csv` | Mark as date table (Table tools → Mark as date table → `Date`) |
| `cohort_retention` | `powerbi/data/02_cohort_retention.csv` | Pre-computed in SQL, standalone |
| `basket_pairs` | `powerbi/data/basket_pairs.csv` | Pre-computed, standalone |

In Power Query, set `fact_sales[InvoiceDay]` to **Date** type, and `CustomerID` to **Whole number** in both fact and dimension tables. Set `StockCode` to **Text** in both `fact_sales` and `dim_product`.

## 2. Relationships (star schema)

```
dim_date[Date]            1 ──── * fact_sales[InvoiceDay]
dim_customer[CustomerID]  1 ──── * fact_sales[CustomerID]
dim_product[StockCode]    1 ──── * fact_sales[StockCode]
```

All relationships are single-direction, from the dimension to the fact table.

## 3. DAX measures

Create a blank table called `_Measures` and add:

```DAX
Net Revenue = SUM ( fact_sales[Revenue] )

Gross Revenue = CALCULATE ( [Net Revenue], fact_sales[is_return] = FALSE () )

Returns Value = - CALCULATE ( [Net Revenue], fact_sales[is_return] = TRUE () )

Return Rate % = DIVIDE ( [Returns Value], [Gross Revenue] )

Orders = CALCULATE ( DISTINCTCOUNT ( fact_sales[Invoice] ), fact_sales[is_return] = FALSE () )

Customers = CALCULATE ( DISTINCTCOUNT ( fact_sales[CustomerID] ),
                        fact_sales[is_return] = FALSE (), NOT ISBLANK ( fact_sales[CustomerID] ) )

Avg Order Value = DIVIDE ( [Gross Revenue], [Orders] )

Net Revenue PY = CALCULATE ( [Net Revenue], SAMEPERIODLASTYEAR ( dim_date[Date] ) )

Net Revenue YoY % = DIVIDE ( [Net Revenue] - [Net Revenue PY], [Net Revenue PY] )

New Customers =
VAR FirstPurchase =
    ADDCOLUMNS (
        VALUES ( fact_sales[CustomerID] ),
        "@first", CALCULATE ( MIN ( fact_sales[InvoiceDay] ), ALL ( dim_date ), fact_sales[is_return] = FALSE () )
    )
RETURN
    COUNTROWS ( FILTER ( FirstPurchase,
        NOT ISBLANK ( fact_sales[CustomerID] ) && [@first] IN VALUES ( dim_date[Date] ) ) )

Returning Customers = [Customers] - [New Customers]

Revenue at Risk = SUM ( dim_customer[revenue_at_risk] )

Champions Revenue Share =
DIVIDE (
    CALCULATE ( [Net Revenue], dim_customer[segment] = "Champions" ),
    CALCULATE ( [Net Revenue], NOT ISBLANK ( fact_sales[CustomerID] ) )
)
```

## 4. Report pages

**Page 1 – Executive overview**
- KPI cards: Net Revenue, Net Revenue YoY %, Orders, Customers, Avg Order Value, Return Rate %
- Line chart: `dim_date[YearMonth]` × Net Revenue, with Year as the legend (2010 vs 2011)
- Stacked column: YearMonth × New Customers + Returning Customers
- Slicers (one row at the top): Year, Country

**Page 2 – Customers**
- Clustered bar: `dim_customer[segment]` × count of customers and Net Revenue (show as % of total)
- Matrix heatmap from `cohort_retention`: rows `cohort_month`, columns `month_number` (filter 1–12), values `retention_pct`, with a single-hue blue background colour scale (conditional formatting)
- Table: segment, customers, revenue, median recency

**Page 3 – Products**
- Bar: Top 15 `dim_product[Description]` by Net Revenue (Top N filter)
- Donut is *not* recommended here. Use a 100% stacked bar of revenue by `abc_class`
- Table from `basket_pairs`: name_a, name_b, lift, confidence, with a slicer on `name_a`

**Page 4 – Churn risk**
- Cards: Revenue at Risk, count of High-risk customers
- Table: CustomerID, country, recency_days, monetary, churn_probability (data bars), revenue_at_risk, filtered to `risk_band` ∈ {High, Medium}, `recency_days` ≤ 180, `monetary` ≥ 2000
- Scatter: recency_days × monetary, coloured by risk_band

## 5. Design tips

- Use one accent colour (`#2a78d6`) for the primary series and grey (`#b9b8b1`) for comparisons.
- Give every visual a title that states the takeaway ("Champions = 70% of revenue"), not just "Revenue by segment".
- Publish to the web (if your organisation allows) or export to PDF, add screenshots to the README, and link the `.pbix` file.
