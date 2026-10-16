"""Interactive retail analytics dashboard.

Run locally:  streamlit run app/streamlit_app.py
"""
import json
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

DATA = Path(__file__).resolve().parents[1] / "data" / "processed"
BLUE, ORANGE, MUTED = "#2a78d6", "#eb6834", "#b9b8b1"

st.set_page_config(page_title="Online Retail Analytics", page_icon="📊", layout="wide")


# ---------- data ----------
@st.cache_data
def load_orders() -> pd.DataFrame:
    tx = pd.read_parquet(DATA / "transactions.parquet")
    orders = (tx.groupby(["Invoice", "is_return"], as_index=False)
                .agg(CustomerID=("CustomerID", "first"), Country=("Country", "first"),
                     date=("InvoiceDay", "min"), value=("Revenue", "sum"), units=("Quantity", "sum")))
    orders["month"] = orders["date"].dt.to_period("M").dt.to_timestamp()
    return orders


@st.cache_data
def load_products() -> pd.DataFrame:
    tx = pd.read_parquet(DATA / "transactions.parquet",
                         columns=["StockCode", "Description", "Country", "InvoiceDay", "Revenue", "Quantity", "is_return"])
    tx["month"] = tx["InvoiceDay"].dt.to_period("M").dt.to_timestamp()
    return (tx.groupby(["StockCode", "Country", "month"], as_index=False)
              .agg(revenue=("Revenue", "sum"), units=("Quantity", "sum")))


@st.cache_data
def load_csv(name: str) -> pd.DataFrame:
    # Stock codes mix digits and letters ("22423", "85123A"); keep them as text everywhere.
    return pd.read_csv(DATA / name, dtype={"StockCode": str, "product_a": str, "product_b": str})


orders = load_orders()
products = load_products()
names = load_csv("04_product_pareto.csv").set_index("StockCode")["description"]
rfm = load_csv("03_rfm_segments.csv")
cohort = load_csv("02_cohort_retention.csv")
churn = load_csv("churn_scores.csv")
basket = load_csv("basket_pairs.csv")
model = json.loads((DATA / "churn_model_summary.json").read_text())

# ---------- filters ----------
st.title("Online Retail Analytics")
st.caption("UK online gift wholesaler · Dec 2009 – Dec 2011 · 1.0M cleaned transaction lines · all values in GBP")

with st.sidebar:
    st.header("Filters")
    min_d, max_d = orders["date"].min().date(), orders["date"].max().date()
    # Default to 2011 so year-over-year deltas are visible on first load.
    date_range = st.date_input("Date range", (pd.Timestamp("2011-01-01").date(), max_d),
                               min_value=min_d, max_value=max_d)
    market = st.radio("Market", ["All", "United Kingdom", "International"], horizontal=False)
    st.divider()
    st.markdown("**Method**  \nCleaning, SQL, statistics and model code are in the "
                "[GitHub repo](https://github.com/ShangChiOne/online-retail-analytics). Each number here is traceable to a script.")

start, end = (pd.Timestamp(d) for d in (date_range if len(date_range) == 2 else (min_d, max_d)))


def filter_market(df: pd.DataFrame) -> pd.DataFrame:
    if market == "United Kingdom":
        return df[df["Country"] == "United Kingdom"]
    if market == "International":
        return df[df["Country"] != "United Kingdom"]
    return df


o = filter_market(orders)
o_now = o[o["date"].between(start, end)]
# Same-length window one year earlier for YoY deltas.
prev_start, prev_end = start - pd.DateOffset(years=1), end - pd.DateOffset(years=1)
o_prev = o[o["date"].between(prev_start, prev_end)]


def kpis(df: pd.DataFrame) -> dict:
    sales = df[~df["is_return"]]
    gross = sales["value"].sum()
    return {
        "net": df["value"].sum(),
        "orders": len(sales),
        "customers": sales["CustomerID"].nunique(),
        "aov": sales["value"].mean() if len(sales) else 0,
        "return_rate": 100 * -df.loc[df["is_return"], "value"].sum() / gross if gross else 0,
    }


now, prev = kpis(o_now), kpis(o_prev)
has_prev = o_prev["date"].min() <= prev_start + pd.Timedelta(days=7) if len(o_prev) else False


def delta(key: str, pct: bool = True):
    if not has_prev or not prev[key]:
        return None
    if pct:
        return f"{100 * (now[key] - prev[key]) / prev[key]:+.1f}% YoY"
    return f"{now[key] - prev[key]:+.2f} pp YoY"


c = st.columns(5)
c[0].metric("Net revenue", f"£{now['net'] / 1e6:.1f}M", delta("net"))
c[1].metric("Orders", f"{now['orders'] / 1e3:.1f}k", delta("orders"))
c[2].metric("Customers", f"{now['customers'] / 1e3:.1f}k", delta("customers"))
c[3].metric("Avg order value", f"£{now['aov']:,.0f}", delta("aov"))
c[4].metric("Return rate", f"{now['return_rate']:.2f}%", delta("return_rate", pct=False), delta_color="inverse")
if not has_prev:
    st.caption("YoY deltas appear when the selected range has a full prior-year comparison window.")

tab_overview, tab_customers, tab_products, tab_risk = st.tabs(
    ["📈 Revenue", "👥 Customers & retention", "📦 Products & baskets", "⚠️ Churn risk"])

# ---------- revenue ----------
with tab_overview:
    monthly = (o_now.groupby("month", as_index=False)
               .agg(net_revenue=("value", "sum"), orders=("Invoice", "nunique")))
    line = alt.Chart(monthly).mark_line(point=alt.OverlayMarkDef(size=40), color=BLUE, strokeWidth=2).encode(
        x=alt.X("month:T", title=None, axis=alt.Axis(format="%b %Y")),
        y=alt.Y("net_revenue:Q", title="Net revenue (£)", axis=alt.Axis(format="~s")),
        tooltip=[alt.Tooltip("month:T", format="%B %Y", title="Month"),
                 alt.Tooltip("net_revenue:Q", format=",.0f", title="Net revenue £"),
                 alt.Tooltip("orders:Q", format=",", title="Orders")],
    ).properties(height=320, title="Monthly net revenue")
    st.altair_chart(line, width="stretch")
    st.caption("Dec 2011 is a partial month (data ends 9 Dec). Sep–Nov is the peak season every year.")

    cust = o_now[~o_now["is_return"] & o_now["CustomerID"].notna()]
    first = orders[~orders["is_return"]].groupby("CustomerID")["month"].min()
    active = cust.drop_duplicates(["CustomerID", "month"]).copy()
    active["type"] = (active["month"] == active["CustomerID"].map(first)).map({True: "New", False: "Returning"})
    nr = active.groupby(["month", "type"], as_index=False).size()
    bars = alt.Chart(nr).mark_bar(cornerRadiusTopLeft=2, cornerRadiusTopRight=2).encode(
        x=alt.X("yearmonth(month):O", title=None, axis=alt.Axis(format="%b %y", labelAngle=0)),
        y=alt.Y("size:Q", title="Active customers", stack=True),
        color=alt.Color("type:N", scale=alt.Scale(domain=["Returning", "New"], range=[BLUE, ORANGE]),
                        legend=alt.Legend(title=None, orient="top-left")),
        tooltip=[alt.Tooltip("month:T", format="%B %Y"), "type:N", alt.Tooltip("size:Q", title="Customers")],
    ).properties(height=300, title="New vs returning customers per month")
    st.altair_chart(bars, width="stretch")
    st.caption("Dec 2009 counts every customer as new because the data starts then. Read the trend from mid-2010 onward.")

# ---------- customers ----------
with tab_customers:
    left, right = st.columns([1, 1])
    seg = filter_market(rfm.rename(columns={"country": "Country"}))
    g = seg.groupby("segment").agg(customers=("CustomerID", "size"), revenue=("monetary", "sum"),
                                   median_recency=("recency_days", "median")).reset_index()
    g["% customers"] = 100 * g["customers"] / g["customers"].sum()
    g["% revenue"] = 100 * g["revenue"] / g["revenue"].sum()
    g = g.sort_values("revenue", ascending=False)
    with left:
        st.subheader("RFM segments")
        long = g.melt(id_vars="segment", value_vars=["% customers", "% revenue"])
        chart = alt.Chart(long).mark_bar(cornerRadiusEnd=2).encode(
            y=alt.Y("segment:N", sort=g["segment"].tolist(), title=None),
            x=alt.X("value:Q", title="Share (%)"),
            yOffset="variable:N",
            color=alt.Color("variable:N", scale=alt.Scale(range=[MUTED, BLUE]),
                            legend=alt.Legend(title=None, orient="bottom")),
            tooltip=["segment:N", "variable:N", alt.Tooltip("value:Q", format=".1f")],
        ).properties(height=340)
        st.altair_chart(chart, width="stretch")
    with right:
        st.subheader("Segment playbook")
        playbook = {
            "Champions": "Reward and protect: early access, account manager",
            "Loyal": "Upsell bundles built from basket pairs",
            "Can't Lose Them": "Personal win-back call; high value, gone quiet",
            "At Risk": "Automated win-back offer before the Q4 peak",
            "New / Promising": "Second-order incentive within 30 days",
            "Need Attention": "Reactivation email with best-sellers",
            "Hibernating": "Low-cost newsletter only",
        }
        g["Action"] = g["segment"].map(playbook)
        st.dataframe(
            g[["segment", "customers", "revenue", "median_recency", "Action"]],
            hide_index=True, width="stretch",
            column_config={
                "segment": "Segment",
                "customers": st.column_config.NumberColumn("Customers", format="%d"),
                "revenue": st.column_config.NumberColumn("Lifetime revenue", format="£%.0f"),
                "median_recency": st.column_config.NumberColumn("Median days since order", format="%d"),
            })

    st.subheader("Cohort retention")
    st.caption("Share of each monthly acquisition cohort that ordered again N months after their first purchase "
               "(all markets).")
    co = cohort[(cohort["month_number"].between(1, 12)) & (cohort["cohort_month"] >= "2010-01")]
    heat = alt.Chart(co).mark_rect().encode(
        x=alt.X("month_number:O", title="Months since first purchase"),
        y=alt.Y("cohort_month:O", title="Acquisition cohort"),
        color=alt.Color("retention_pct:Q", scale=alt.Scale(scheme="blues", domain=[0, 40]), title="Retention %"),
        tooltip=["cohort_month:O", "month_number:O", alt.Tooltip("retention_pct:Q", title="Retention %"),
                 alt.Tooltip("cohort_customers:Q", title="Cohort size")],
    ).properties(height=480)
    st.altair_chart(heat, width="stretch")

# ---------- products ----------
with tab_products:
    p = filter_market(products)
    p = p[p["month"].between(start.to_period("M").to_timestamp(), end)]
    top = (p.groupby("StockCode", as_index=False).agg(revenue=("revenue", "sum"), units=("units", "sum"))
             .nlargest(15, "revenue"))
    top["product"] = top["StockCode"].map(names).str.title()
    st.subheader("Top 15 products by net revenue")
    chart = alt.Chart(top).mark_bar(color=BLUE, cornerRadiusEnd=2).encode(
        y=alt.Y("product:N", sort="-x", title=None, axis=alt.Axis(labelLimit=320)),
        x=alt.X("revenue:Q", title="Net revenue (£)", axis=alt.Axis(format="~s")),
        tooltip=["product:N", "StockCode:N", alt.Tooltip("revenue:Q", format=",.0f"), alt.Tooltip("units:Q", format=",")],
    ).properties(height=420)
    st.altair_chart(chart, width="stretch")

    st.subheader("Frequently bought together")
    st.caption("Market-basket rules from all orders. Lift = how many times more often the pair is bought "
               "together than chance would predict.")
    codes = pd.unique(pd.concat([basket["product_a"], basket["product_b"]]))
    labels = {c: f"{str(names.get(c, c)).title()} ({c})" for c in codes}
    default = list(codes).index("22423") if "22423" in codes else 0
    pick = st.selectbox("Choose a product", options=list(codes), index=default, format_func=labels.get)
    recs_a = basket[basket["product_a"] == pick].rename(
        columns={"product_b": "code", "name_b": "Recommend", "confidence_a_to_b_pct": "confidence"})
    recs_b = basket[basket["product_b"] == pick].rename(
        columns={"product_a": "code", "name_a": "Recommend", "confidence_b_to_a_pct": "confidence"})
    recs = pd.concat([recs_a, recs_b])[["Recommend", "orders_together", "confidence", "lift"]]
    st.dataframe(recs.nlargest(10, "lift"), hide_index=True, width="stretch",
                 column_config={
                     "orders_together": st.column_config.NumberColumn("Orders together", format="%d"),
                     "confidence": st.column_config.NumberColumn("% of buyers also buy", format="%.1f%%"),
                     "lift": st.column_config.NumberColumn("Lift", format="%.1fx"),
                 })

# ---------- churn ----------
with tab_risk:
    st.subheader("Who should the retention team call first?")
    m = st.columns(4)
    m[0].metric("Model hold-out ROC-AUC", f"{model['holdout_auc']:.2f}",
                f"+{model['holdout_auc'] - model['recency_only_auc']:.2f} vs recency rule")
    m[1].metric("Precision in top 20% risk", f"{model['top20pct_precision_pct']:.0f}%",
                f"base rate {model['holdout_churn_rate_pct']:.0f}%", delta_color="off")
    m[2].metric("High-risk, high-value customers", f"{model['high_risk_high_value_customers']:,}")
    m[3].metric("Their 90-day revenue at risk", f"£{model['high_risk_high_value_revenue_at_risk']:,.0f}")

    risk = filter_market(churn.rename(columns={"country": "Country"}))
    f1, f2, f3 = st.columns(3)
    bands = f1.multiselect("Risk band", ["High", "Medium", "Low"], default=["High", "Medium"])
    min_value = f2.slider("Minimum lifetime revenue (£)", 0, 20000, 2000, step=500)
    # Customers silent for a year are already lost: a win-back campaign, not a retention call.
    max_recency = f3.slider("Max days since last order", 30, 730, 180, step=30)
    view = risk[risk["risk_band"].isin(bands) & (risk["revenue"] >= min_value)
                & (risk["recency_days"] <= max_recency)]
    view = view.sort_values("revenue_at_risk", ascending=False)
    st.dataframe(
        view[["CustomerID", "Country", "recency_days", "orders", "revenue", "churn_probability", "revenue_at_risk"]],
        hide_index=True, width="stretch", height=380,
        column_config={
            "CustomerID": st.column_config.NumberColumn("Customer", format="%d"),
            "recency_days": st.column_config.NumberColumn("Days since order", format="%d"),
            "orders": st.column_config.NumberColumn("Orders", format="%d"),
            "revenue": st.column_config.NumberColumn("Lifetime revenue", format="£%.0f"),
            "churn_probability": st.column_config.ProgressColumn("Churn probability", min_value=0, max_value=1,
                                                                 format="%.2f"),
            "revenue_at_risk": st.column_config.NumberColumn("90-day revenue at risk", format="£%.0f"),
        })
    st.download_button("Download call list (CSV)", view.to_csv(index=False), "churn_call_list.csv", "text/csv")
    st.caption(f"Logistic regression trained on history before {model['train_cutoff']}; label = no order in the "
               f"next {model['horizon_days']} days. Scores use all data to 9 Dec 2011.")
