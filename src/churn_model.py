"""Step 5: predict which customers will NOT buy in the next 90 days (churn risk).

Design (no leakage):
  * Features are built only from history up to a cutoff date.
  * Label = did the customer order in the 90 days after the cutoff?
  * Train/validate on cutoff 2011-09-10 (label window ends at the last data date, 2011-12-09).
  * The trained model then scores every customer as of 2011-12-10 to produce a
    "revenue at risk" action list for the retention team.
"""
import json

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold, cross_val_predict, train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from config import PROCESSED

HORIZON_DAYS = 90
TRAIN_CUTOFF = pd.Timestamp("2011-09-10")
SCORE_DATE = pd.Timestamp("2011-12-10")
FEATURES = [
    "recency_days", "tenure_days", "orders", "orders_last_90d", "orders_last_180d",
    "revenue", "revenue_last_90d", "avg_order_value", "distinct_products",
    "avg_days_between_orders", "return_rate", "is_uk",
]


def build_features(tx: pd.DataFrame, cutoff: pd.Timestamp) -> pd.DataFrame:
    hist = tx[(tx["InvoiceDate"] < cutoff) & tx["CustomerID"].notna()]
    sales = hist[~hist["is_return"]]
    orders = sales.groupby(["CustomerID", "Invoice"]).agg(
        day=("InvoiceDay", "min"), value=("Revenue", "sum")).reset_index()

    g = orders.groupby("CustomerID")
    f = pd.DataFrame({
        "recency_days": (cutoff - g["day"].max()).dt.days,
        "tenure_days": (cutoff - g["day"].min()).dt.days,
        "orders": g.size(),
        "revenue": g["value"].sum(),
    })
    for window in (90, 180):
        recent = orders[orders["day"] >= cutoff - pd.Timedelta(days=window)]
        f[f"orders_last_{window}d"] = recent.groupby("CustomerID").size()
    f["revenue_last_90d"] = (orders[orders["day"] >= cutoff - pd.Timedelta(days=90)]
                             .groupby("CustomerID")["value"].sum())
    f["avg_order_value"] = f["revenue"] / f["orders"]
    f["distinct_products"] = sales.groupby("CustomerID")["StockCode"].nunique()
    f["avg_days_between_orders"] = np.where(f["orders"] > 1, f["tenure_days"] / (f["orders"] - 1), 365)
    returned = -hist[hist["is_return"]].groupby("CustomerID")["Revenue"].sum()
    f["return_rate"] = (returned / f["revenue"]).clip(0, 1)
    f["is_uk"] = (sales.groupby("CustomerID")["Country"].agg(lambda s: s.mode()[0]) == "United Kingdom").astype(int)
    f["country"] = sales.groupby("CustomerID")["Country"].agg(lambda s: s.mode()[0])
    return f.fillna({"orders_last_90d": 0, "orders_last_180d": 0, "revenue_last_90d": 0, "return_rate": 0})


def build_labels(tx: pd.DataFrame, cutoff: pd.Timestamp) -> pd.Series:
    window = tx[(tx["InvoiceDate"] >= cutoff)
                & (tx["InvoiceDate"] < cutoff + pd.Timedelta(days=HORIZON_DAYS))
                & ~tx["is_return"] & tx["CustomerID"].notna()]
    return pd.Series(1, index=window["CustomerID"].unique(), name="active_next_90d")


def lift_table(y_true: np.ndarray, churn_prob: np.ndarray) -> pd.DataFrame:
    """Share of all churners captured when targeting the top X% riskiest customers."""
    order = np.argsort(-churn_prob)
    churned = (1 - y_true)[order]
    n = len(order)
    rows = []
    for pct in range(10, 101, 10):
        k = int(n * pct / 100)
        rows.append({"top_pct_targeted": pct,
                     "churners_captured_pct": 100 * churned[:k].sum() / churned.sum(),
                     "precision_pct": 100 * churned[:k].mean(),
                     "random_baseline_pct": pct})
    return pd.DataFrame(rows)


def main() -> dict:
    tx = pd.read_parquet(PROCESSED / "transactions.parquet")

    train = build_features(tx, TRAIN_CUTOFF)
    active = build_labels(tx, TRAIN_CUTOFF)
    train["active_next_90d"] = train.index.isin(active.index).astype(int)
    X, y = train[FEATURES], train["active_next_90d"].to_numpy()
    print(f"  training customers: {len(train):,} | active next 90d: {y.mean():.1%}")

    models = {
        "Logistic regression": make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000)),
        "Gradient boosting": HistGradientBoostingClassifier(max_depth=4, learning_rate=0.05,
                                                            max_iter=300, random_state=42),
    }
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    scores = {}
    for name, model in models.items():
        p_active = cross_val_predict(model, X, y, cv=cv, method="predict_proba")[:, 1]
        scores[name] = {"cv_roc_auc": float(roc_auc_score(y, p_active))}
        print(f"  {name:<20} 5-fold ROC-AUC = {scores[name]['cv_roc_auc']:.3f}")

    # Baseline a manager would use without a model: "recency only".
    baseline_auc = float(roc_auc_score(y, -X["recency_days"]))
    print(f"  {'Recency-only rule':<20} ROC-AUC = {baseline_auc:.3f}")

    # Prefer the explainable model unless the complex one is materially better (> 0.01 AUC).
    gain = scores["Gradient boosting"]["cv_roc_auc"] - scores["Logistic regression"]["cv_roc_auc"]
    best_name = "Gradient boosting" if gain > 0.01 else "Logistic regression"
    best = models[best_name]

    # Hold-out lift chart for the chosen model.
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.3, stratify=y, random_state=42)
    best.fit(X_tr, y_tr)
    churn_prob = 1 - best.predict_proba(X_te)[:, 1]
    lift = lift_table(y_te, churn_prob)
    lift.to_csv(PROCESSED / "churn_lift.csv", index=False)
    holdout_auc = float(roc_auc_score(y_te, 1 - churn_prob))

    # Coefficients of the interpretable model, to explain drivers.
    logit = models["Logistic regression"].fit(X, y)
    coefs = pd.Series(logit[-1].coef_[0], index=FEATURES).sort_values()

    # Refit on all labelled data, then score today's customers.
    best.fit(X, y)
    now = build_features(tx, SCORE_DATE)
    now["churn_probability"] = 1 - best.predict_proba(now[FEATURES])[:, 1]
    # Expected 90-day revenue at risk = probability of churn x their typical 90-day spend.
    daily_spend = now["revenue"] / now["tenure_days"].clip(lower=90)
    now["expected_90d_value"] = daily_spend * HORIZON_DAYS
    now["revenue_at_risk"] = now["churn_probability"] * now["expected_90d_value"]
    now["risk_band"] = pd.cut(now["churn_probability"], [0, 0.4, 0.7, 1.0], labels=["Low", "Medium", "High"])
    scored = now.reset_index().rename(columns={"index": "CustomerID"})
    scored.sort_values("revenue_at_risk", ascending=False).to_csv(PROCESSED / "churn_scores.csv", index=False)

    high_value = scored[(scored["risk_band"] == "High") & (scored["revenue"] >= scored["revenue"].quantile(0.8))]
    top20 = lift.loc[lift["top_pct_targeted"] == 20, "churners_captured_pct"].item()
    top20_precision = lift.loc[lift["top_pct_targeted"] == 20, "precision_pct"].item()
    summary = {
        "train_cutoff": str(TRAIN_CUTOFF.date()),
        "horizon_days": HORIZON_DAYS,
        "training_customers": int(len(train)),
        "base_active_rate": float(y.mean()),
        "models": scores,
        "recency_only_auc": baseline_auc,
        "chosen_model": best_name,
        "holdout_auc": holdout_auc,
        "top20pct_captures_churners_pct": float(top20),
        "top20pct_precision_pct": float(top20_precision),
        "holdout_churn_rate_pct": float(100 * (1 - y_te).mean()),
        "logit_coefficients": coefs.round(3).to_dict(),
        "high_risk_high_value_customers": int(len(high_value)),
        "high_risk_high_value_revenue_at_risk": float(high_value["revenue_at_risk"].sum()),
        "total_revenue_at_risk": float(scored["revenue_at_risk"].sum()),
    }
    (PROCESSED / "churn_model_summary.json").write_text(json.dumps(summary, indent=2))
    print(f"  chosen: {best_name} | hold-out AUC {holdout_auc:.3f} | top 20% precision {top20_precision:.0f}%")
    return summary


if __name__ == "__main__":
    main()
