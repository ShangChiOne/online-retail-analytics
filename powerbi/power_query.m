// Power Query (M) code for every table in the report.
// For each block: Home > Get data > Blank query > Advanced editor > paste > Done > rename the query.
// If the project folder is somewhere else, change the path in File.Contents(...).


// ===== fact_sales =====
let
    Source = Parquet.Document(File.Contents("D:\Year 3\Project Sanju\DA Project\data\processed\transactions.parquet")),
    Typed = Table.TransformColumnTypes(Source, {
        {"Invoice", type text}, {"StockCode", type text}, {"Description", type text},
        {"Quantity", Int64.Type}, {"InvoiceDate", type datetime}, {"Price", type number},
        {"CustomerID", Int64.Type}, {"Country", type text}, {"is_return", type logical},
        {"Revenue", type number}, {"InvoiceDay", type date}})
in
    Typed


// ===== dim_customer =====
let
    Source = Csv.Document(File.Contents("D:\Year 3\Project Sanju\DA Project\powerbi\data\dim_customer.csv"),
        [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(Headers, {
        {"CustomerID", Int64.Type}, {"country", type text}, {"recency_days", Int64.Type},
        {"frequency", Int64.Type}, {"monetary", type number}, {"returned_value", type number},
        {"r_score", Int64.Type}, {"f_score", Int64.Type}, {"m_score", Int64.Type},
        {"rfm_code", type text}, {"segment", type text}, {"churn_probability", type number},
        {"revenue_at_risk", type number}, {"risk_band", type text}}, "en-US")
in
    Typed


// ===== dim_product =====
let
    Source = Csv.Document(File.Contents("D:\Year 3\Project Sanju\DA Project\powerbi\data\dim_product.csv"),
        [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(Headers, {
        {"StockCode", type text}, {"Description", type text}, {"gross_revenue", type number},
        {"returns_value", type number}, {"net_revenue", type number}, {"return_rate_pct", type number},
        {"units_sold", Int64.Type}, {"orders", Int64.Type}, {"customers", Int64.Type},
        {"revenue_rank", Int64.Type}, {"pct_of_products", type number},
        {"cumulative_revenue_pct", type number}, {"abc_class", type text}}, "en-US")
in
    Typed


// ===== dim_date =====
let
    Source = Csv.Document(File.Contents("D:\Year 3\Project Sanju\DA Project\powerbi\data\dim_date.csv"),
        [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(Headers, {
        {"Date", type date}, {"Year", Int64.Type}, {"Quarter", type text}, {"MonthNum", Int64.Type},
        {"Month", type text}, {"YearMonth", type text}, {"WeekdayNum", Int64.Type},
        {"Weekday", type text}, {"IsPeakSeason", Int64.Type}}, "en-US")
in
    Typed


// ===== cohort_retention =====
let
    Source = Csv.Document(File.Contents("D:\Year 3\Project Sanju\DA Project\powerbi\data\02_cohort_retention.csv"),
        [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(Headers, {
        {"cohort_month", type text}, {"cohort_customers", Int64.Type}, {"month_number", Int64.Type},
        {"active_customers", Int64.Type}, {"retention_pct", type number}}, "en-US")
in
    Typed


// ===== basket_pairs =====
let
    Source = Csv.Document(File.Contents("D:\Year 3\Project Sanju\DA Project\powerbi\data\basket_pairs.csv"),
        [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(Headers, {
        {"product_a", type text}, {"product_b", type text}, {"orders_together", Int64.Type},
        {"support_pct", type number}, {"confidence_a_to_b_pct", type number},
        {"confidence_b_to_a_pct", type number}, {"lift", type number},
        {"name_a", type text}, {"name_b", type text}}, "en-US")
in
    Typed
