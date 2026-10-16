"""Step 7: render every report figure to reports/figures/."""
import json

import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np
import pandas as pd

import style
from config import FIG_DIR, PROCESSED
from style import AQUA, BLUE, MUTED, ORANGE, TEXT, TEXT_2

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def revenue_yoy(kpis: pd.DataFrame) -> None:
    k = kpis[kpis["is_partial_month"] == 0].copy()
    k["year"] = k["month"].str[:4].astype(int)
    k["m"] = k["month"].str[5:].astype(int)
    fig, ax = plt.subplots(figsize=(9, 4.6))
    for year, color in ((2010, MUTED), (2011, BLUE)):
        d = k[k["year"] == year]
        ax.plot(d["m"], d["net_revenue"], color=color, marker="o", markersize=4.5, label=str(year))
        last = d.iloc[-1]
        ax.annotate(f"{year}  {style.gbp(last['net_revenue'])}", (last["m"], last["net_revenue"]),
                    xytext=(8, 0), textcoords="offset points", va="center", color=TEXT_2, fontsize=9.5)
    ytd = {y: k[(k["year"] == y) & (k["m"] <= 11)]["net_revenue"].sum() for y in (2010, 2011)}
    growth = 100 * (ytd[2011] - ytd[2010]) / ytd[2010]
    ax.set_title("Net revenue is flat year on year, and Q4 carries the business")
    style.subtitle(ax, f"Jan–Nov net revenue: 2010 {style.gbp(ytd[2010])}  →  2011 {style.gbp(ytd[2011])} "
                       f"({growth:+.1f}%). Sep–Nov = {100 * k[(k.year == 2011) & k.m.between(9, 11)].net_revenue.sum() / ytd[2011]:.0f}% of 2011 revenue.")
    ax.set_xticks(range(1, 13), MONTHS)
    ax.set_xlim(0.6, 13.2)
    ax.yaxis.set_major_formatter(mtick.FuncFormatter(style.gbp))
    ax.set_ylim(0, None)
    ax.legend(loc="upper left")
    style.save(fig, FIG_DIR / "01_revenue_yoy.png")


def new_vs_returning(kpis: pd.DataFrame) -> None:
    k = kpis[(kpis["month"] >= "2010-01") & (kpis["is_partial_month"] == 0)]
    x = np.arange(len(k))
    fig, ax = plt.subplots(figsize=(10, 4.6))
    ax.bar(x, k["returning_customers"], color=BLUE, width=0.72, label="Returning customers")
    ax.bar(x, k["new_customers"], bottom=k["returning_customers"] + 8, color=ORANGE, width=0.72,
           label="New customers")
    ax.set_xticks(x, [f"{pd.Timestamp(m):%b %Y}" if m.endswith(("01", "07")) else "" for m in k["month"]])
    tests = json.loads((PROCESSED / "hypothesis_tests.json").read_text())["acquisition_drop"]
    ax.set_title("Growth now depends on existing customers: acquisition fell sharply in 2011")
    style.subtitle(ax, f"New customers Jul–Nov: 2010 {tests['new_customers_2010']:,} → 2011 "
                       f"{tests['new_customers_2011']:,} ({tests['change_pct']:.0f}%, p < 0.001)")
    ax.set_ylabel("Active customers per month")
    ax.legend(loc="upper left", ncols=2)
    style.save(fig, FIG_DIR / "02_new_vs_returning.png")


def cohort_heatmap(cohort: pd.DataFrame) -> None:
    c = cohort[(cohort["cohort_month"] >= "2010-01") & (cohort["cohort_month"] <= "2010-12")
               & (cohort["month_number"].between(1, 12))]
    pivot = c.pivot(index="cohort_month", columns="month_number", values="retention_pct")
    sizes = cohort.drop_duplicates("cohort_month").set_index("cohort_month")["cohort_customers"]
    fig, ax = plt.subplots(figsize=(10, 5.6))
    ax.grid(False)
    im = ax.imshow(pivot.values, cmap=style.SEQ_BLUES, vmin=0, vmax=40, aspect="auto")
    for (i, j), v in np.ndenumerate(pivot.values):
        if not np.isnan(v):
            ax.text(j, i, f"{v:.0f}", ha="center", va="center", fontsize=8.5,
                    color="white" if v >= 24 else TEXT)
    ax.set_xticks(range(pivot.shape[1]), [f"M{m}" for m in pivot.columns])
    ax.set_yticks(range(pivot.shape[0]),
                  [f"{pd.Timestamp(m):%b %Y}  (n={sizes[m]:,})" for m in pivot.index])
    for s in ax.spines.values():
        s.set_visible(False)
    cbar = fig.colorbar(im, ax=ax, fraction=0.025, pad=0.02)
    cbar.outline.set_visible(False)
    cbar.ax.yaxis.set_major_formatter(mtick.PercentFormatter())
    m1 = pivot[1].mean()
    q4_m12 = pivot.loc[["2010-09", "2010-10", "2010-11"], 12].mean()
    ax.set_title("Holiday-season cohorts retain worst, then come back a year later")
    style.subtitle(ax, f"% of each 2010 cohort ordering again N months after first purchase. "
                       f"Avg month-1 retention {m1:.0f}%; Sep–Nov cohorts rebound to {q4_m12:.0f}% at M12")
    style.save(fig, FIG_DIR / "03_cohort_retention.png")


def rfm_segments(rfm: pd.DataFrame) -> None:
    g = rfm.groupby("segment").agg(customers=("CustomerID", "size"), revenue=("monetary", "sum"))
    g["cust_pct"] = 100 * g["customers"] / g["customers"].sum()
    g["rev_pct"] = 100 * g["revenue"] / g["revenue"].sum()
    g = g.sort_values("rev_pct")
    y = np.arange(len(g))
    h = 0.36
    fig, ax = plt.subplots(figsize=(9.5, 4.8))
    ax.grid(axis="x")
    ax.grid(axis="y", visible=False)
    ax.barh(y + h / 2 + 0.02, g["cust_pct"], height=h, color=MUTED, label="% of customers")
    ax.barh(y - h / 2 - 0.02, g["rev_pct"], height=h, color=BLUE, label="% of revenue")
    for yi, (cp, rp) in enumerate(zip(g["cust_pct"], g["rev_pct"])):
        ax.text(rp + 0.8, yi - h / 2 - 0.02, f"{rp:.0f}%", va="center", fontsize=9, color=TEXT)
    ax.set_yticks(y, g.index)
    ax.xaxis.set_major_formatter(mtick.PercentFormatter())
    champ = g.loc["Champions"]
    ax.set_title("23% of customers generate 70% of revenue")
    style.subtitle(ax, f"RFM segments (SQL, NTILE quintiles). Champions: {champ.cust_pct:.0f}% of customers, "
                       f"{champ.rev_pct:.0f}% of revenue")
    ax.legend(loc="lower right")
    style.save(fig, FIG_DIR / "04_rfm_segments.png")


def pareto(products: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(8.5, 4.6))
    ax.plot(products["pct_of_products"], products["cumulative_revenue_pct"], color=BLUE)
    cut = products[products["cumulative_revenue_pct"] <= 80]["pct_of_products"].max()
    ax.plot([0, cut, cut], [80, 80, 0], color=TEXT_2, linewidth=0.9)
    ax.scatter([cut], [80], s=40, color=BLUE, zorder=3, edgecolor=style.SURFACE, linewidth=2)
    ax.annotate(f"{cut:.0f}% of products → 80% of revenue\n({(products['abc_class'] == 'A').sum():,} 'A-class' SKUs)",
                (cut, 80), xytext=(14, -38), textcoords="offset points", color=TEXT, fontsize=9.5)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 102)
    ax.xaxis.set_major_formatter(mtick.PercentFormatter())
    ax.yaxis.set_major_formatter(mtick.PercentFormatter())
    ax.set_xlabel("Share of products (ranked by net revenue)")
    ax.set_ylabel("Cumulative share of revenue")
    ax.set_title("Revenue is concentrated in a small product core")
    style.subtitle(ax, f"{len(products):,} products. Protect stock levels for A-class; review the long tail.")
    style.save(fig, FIG_DIR / "05_product_pareto.png")


def countries(country: pd.DataFrame) -> None:
    c = country[(country["country"] != "United Kingdom") & (country["customers"] >= 5)]
    c = c.nlargest(10, "gross_revenue").sort_values("gross_revenue")
    fig, ax = plt.subplots(figsize=(9, 4.8))
    ax.grid(axis="x")
    ax.grid(axis="y", visible=False)
    ax.barh(c["country"], c["gross_revenue"], color=BLUE, height=0.62)
    for yi, (rev, rpc, n) in enumerate(zip(c["gross_revenue"], c["revenue_per_customer"], c["customers"])):
        ax.text(rev, yi, f"  {style.gbp(rev)} · {n} customers · {style.gbp(rpc)}/customer",
                va="center", fontsize=8.8, color=TEXT_2)
    ax.xaxis.set_major_formatter(mtick.FuncFormatter(style.gbp))
    ax.set_xlim(0, c["gross_revenue"].max() * 1.75)
    uk = country.set_index("country").loc["United Kingdom"]
    ax.set_title("Outside the UK, a few large wholesale accounts drive revenue")
    style.subtitle(ax, f"UK = {uk.revenue_share_pct:.0f}% of revenue. Top 10 other markets "
                       f"(≥ 5 customers). EIRE has only 3 customers, so it is excluded.")
    style.save(fig, FIG_DIR / "06_international_markets.png")


def order_timing(timing: pd.DataFrame) -> None:
    order = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    p = timing.pivot_table(index="weekday", columns="hour", values="orders", fill_value=0)
    p = p.reindex([d for d in order if d in p.index])
    p = p.loc[:, 7:20]
    fig, ax = plt.subplots(figsize=(10, 3.6))
    ax.grid(False)
    im = ax.imshow(p.values, cmap=style.SEQ_BLUES, aspect="auto")
    ax.set_xticks(range(p.shape[1]), [f"{h:02d}:00" for h in p.columns], fontsize=8.5)
    ax.set_yticks(range(p.shape[0]), p.index)
    for s in ax.spines.values():
        s.set_visible(False)
    cbar = fig.colorbar(im, ax=ax, fraction=0.025, pad=0.02)
    cbar.outline.set_visible(False)
    peak = timing.loc[timing["orders"].idxmax()]
    sat_orders = int(timing.loc[timing["weekday"] == "Sat", "orders"].sum())
    ax.set_title("Orders arrive on weekday working hours, a B2B pattern")
    style.subtitle(ax, f"Orders by weekday × hour. Peak: {peak.weekday} {int(peak.hour):02d}:00. "
                       f"Saturday: only {sat_orders} orders in 2 years. Time campaigns for Tue–Thu, 10:00–15:00.")
    style.save(fig, FIG_DIR / "07_order_timing.png")


def churn_lift(lift: pd.DataFrame, summary: dict) -> None:
    fig, ax = plt.subplots(figsize=(8.5, 4.6))
    x = np.r_[0, lift["top_pct_targeted"]]
    ax.plot(x, np.r_[0, lift["churners_captured_pct"]], color=BLUE, marker="o", markersize=4.5,
            label=f"Churn model ({summary['chosen_model'].lower()})")
    ax.plot(x, x, color=MUTED, label="Random targeting")
    ax.xaxis.set_major_formatter(mtick.PercentFormatter())
    ax.yaxis.set_major_formatter(mtick.PercentFormatter())
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 102)
    ax.set_xlabel("Share of customers contacted (highest risk first)")
    ax.set_ylabel("Share of all churners reached")
    p20 = lift.loc[lift["top_pct_targeted"] == 20].iloc[0]
    ax.annotate(f"Top 20%: {p20.precision_pct:.0f}% of contacts\nreally churn (base rate {summary['holdout_churn_rate_pct']:.0f}%)",
                (20, p20.churners_captured_pct), xytext=(18, -6), textcoords="offset points",
                color=TEXT, fontsize=9.5, va="top")
    ax.set_title("The churn model finds at-risk customers far better than chance")
    style.subtitle(ax, f"Cumulative gains on a 30% hold-out. ROC-AUC {summary['holdout_auc']:.2f} "
                       f"vs {summary['recency_only_auc']:.2f} for a simple recency rule")
    ax.legend(loc="lower right")
    style.save(fig, FIG_DIR / "08_churn_model_gains.png")


def main() -> None:
    style.apply()
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    kpis = pd.read_csv(PROCESSED / "01_monthly_kpis.csv")
    revenue_yoy(kpis)
    new_vs_returning(kpis)
    cohort_heatmap(pd.read_csv(PROCESSED / "02_cohort_retention.csv"))
    rfm_segments(pd.read_csv(PROCESSED / "03_rfm_segments.csv"))
    pareto(pd.read_csv(PROCESSED / "04_product_pareto.csv"))
    countries(pd.read_csv(PROCESSED / "05_country_performance.csv"))
    order_timing(pd.read_csv(PROCESSED / "06_order_timing.csv"))
    churn_lift(pd.read_csv(PROCESSED / "churn_lift.csv"),
               json.loads((PROCESSED / "churn_model_summary.json").read_text()))


if __name__ == "__main__":
    main()
