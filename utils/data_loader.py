import pandas as pd
import numpy as np
import streamlit as st
import json
import ast
import os

DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "retail_data.xlsx")

@st.cache_data
def load_all_data():
    xl = pd.read_excel(DATA_PATH, sheet_name=None)
    return {k: v for k, v in xl.items()}

@st.cache_data
def load_product_catalogue():
    df = pd.read_excel(DATA_PATH, sheet_name="product_catalogue")
    df["price"] = pd.to_numeric(df["price"], errors="coerce").fillna(0)
    df["special_price"] = pd.to_numeric(df["special_price"], errors="coerce").fillna(0)
    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce").fillna(0)
    df["discount_pct"] = np.where(df["price"] > 0, (df["price"] - df["special_price"]) / df["price"] * 100, 0).clip(0, 100)
    return df

@st.cache_data
def load_orders():
    df = pd.read_excel(DATA_PATH, sheet_name="orders")
    df["order_date"] = pd.to_datetime(df["order_date"], errors="coerce")
    df["grand_total"] = pd.to_numeric(df["grand_total"], errors="coerce").fillna(0)
    df["net_revenue"] = pd.to_numeric(df["net_revenue"], errors="coerce").fillna(0)
    df["discount_amount"] = pd.to_numeric(df["discount_amount"], errors="coerce").fillna(0)
    df["total_qty_ordered"] = pd.to_numeric(df["total_qty_ordered"], errors="coerce").fillna(0)
    return df

@st.cache_data
def load_order_items():
    df = pd.read_excel(DATA_PATH, sheet_name="order_items")
    df["order_date"] = pd.to_datetime(df["order_date"], errors="coerce")
    df["price"] = pd.to_numeric(df["price"], errors="coerce").fillna(0)
    df["row_total"] = pd.to_numeric(df["row_total"], errors="coerce").fillna(0)
    df["discount_amount"] = pd.to_numeric(df["discount_amount"], errors="coerce").fillna(0)
    df["qty_ordered"] = pd.to_numeric(df["qty_ordered"], errors="coerce").fillna(0)
    df["line_total_after_discount"] = pd.to_numeric(df["line_total_after_discount"], errors="coerce").fillna(0)
    return df

@st.cache_data
def load_customers():
    df = pd.read_excel(DATA_PATH, sheet_name="customers")
    df["customer_created_date"] = pd.to_datetime(df["customer_created_date"], errors="coerce")
    return df

@st.cache_data
def load_invoices():
    df = pd.read_excel(DATA_PATH, sheet_name="invoices")
    df["invoice_date"] = pd.to_datetime(df["invoice_date"], errors="coerce")
    df["grand_total"] = pd.to_numeric(df["grand_total"], errors="coerce").fillna(0)
    return df

@st.cache_data
def load_bq_events():
    df = pd.read_excel(DATA_PATH, sheet_name="bq_events")
    df["event_date"] = pd.to_datetime(df["event_date"], errors="coerce")
    df["event_value_in_usd"] = pd.to_numeric(df["event_value_in_usd"], errors="coerce").fillna(0)
    return df

@st.cache_data
def compute_sales_metrics():
    orders = load_orders()
    order_items = load_order_items()
    products = load_product_catalogue()

    sales = order_items[order_items["order_state"] == "complete"].copy()
    product_sales = sales.groupby("product_id").agg(
        total_qty_sold=("qty_ordered", "sum"),
        total_revenue=("row_total", "sum"),
        total_discounts=("discount_amount", "sum"),
        order_count=("order_id", "nunique"),
        avg_price=("price", "mean"),
    ).reset_index()

    # Sales velocity (units/day) — use date range from data
    date_range_days = (orders["order_date"].max() - orders["order_date"].min()).days or 1
    product_sales["sales_velocity"] = product_sales["total_qty_sold"] / date_range_days

    merged = products.merge(product_sales, on="product_id", how="left")
    merged["total_qty_sold"] = merged["total_qty_sold"].fillna(0)
    merged["total_revenue"] = merged["total_revenue"].fillna(0)
    merged["total_discounts"] = merged["total_discounts"].fillna(0)
    merged["order_count"] = merged["order_count"].fillna(0)
    merged["sales_velocity"] = merged["sales_velocity"].fillna(0)

    # Inventory turnover
    merged["inventory_turnover"] = np.where(
        merged["quantity"] > 0,
        merged["total_qty_sold"] / merged["quantity"],
        0
    )

    # Sell-through rate
    total_available = merged["quantity"] + merged["total_qty_sold"]
    merged["sell_through_rate"] = np.where(
        total_available > 0,
        merged["total_qty_sold"] / total_available * 100,
        0
    ).clip(0, 100)

    # Inventory pressure (low turnover + high stock = high pressure)
    merged["inventory_pressure"] = np.where(
        merged["quantity"] > 0,
        (merged["quantity"] / (merged["sales_velocity"] * 30 + 0.01)).clip(0, 100),
        0
    )

    # ABC classification
    merged = merged.sort_values("total_revenue", ascending=False)
    merged["revenue_cumsum"] = merged["total_revenue"].cumsum()
    total_rev = merged["total_revenue"].sum()
    merged["cumsum_pct"] = merged["revenue_cumsum"] / (total_rev + 1e-9) * 100
    merged["abc_class"] = pd.cut(merged["cumsum_pct"], bins=[0, 70, 90, 100], labels=["A", "B", "C"])
    merged["abc_class"] = merged["abc_class"].astype(str).replace("nan", "C")

    # Clearance risk
    merged["clearance_risk"] = np.where(
        (merged["quantity"] > 50) & (merged["sales_velocity"] < 0.1), "HIGH",
        np.where(
            (merged["quantity"] > 20) & (merged["sales_velocity"] < 0.3), "MEDIUM",
            "LOW"
        )
    )

    # Dead inventory: >90 days of stock at current velocity
    merged["days_of_stock"] = np.where(
        merged["sales_velocity"] > 0,
        merged["quantity"] / merged["sales_velocity"],
        9999
    )
    merged["is_dead_inventory"] = merged["days_of_stock"] > 180

    return merged

@st.cache_data
def compute_elasticity_data():
    order_items = load_order_items()
    products = load_product_catalogue()
    
    product_discounts = order_items[order_items["order_state"] == "complete"].groupby("product_id").agg(
        avg_discount=("discount_amount", "mean"),
        total_qty=("qty_ordered", "sum"),
        avg_price=("price", "mean"),
    ).reset_index()

    merged = products[["product_id", "price", "special_price", "discount_pct", "main_category"]].merge(
        product_discounts, on="product_id", how="inner"
    )
    merged = merged[merged["avg_price"] > 0]

    # Simplified price elasticity: % change in qty / % change in price
    baseline_qty = merged["total_qty"].median()
    baseline_price = merged["avg_price"].median()
    merged["elasticity"] = np.where(
        merged["discount_pct"] > 0,
        -(merged["total_qty"] / (baseline_qty + 1e-9) - 1) / (merged["discount_pct"] / 100 + 1e-9),
        -1.0
    )
    merged["elasticity"] = merged["elasticity"].clip(-10, 0)
    merged["discount_sensitivity"] = pd.cut(
        merged["elasticity"].abs(),
        bins=[0, 1, 2, 10],
        labels=["Low", "Medium", "High"]
    ).astype(str)

    return merged

@st.cache_data
def compute_event_metrics():
    events = load_bq_events()
    event_counts = events.groupby("event_name").size().reset_index(name="count").sort_values("count", ascending=False)
    
    add_to_cart = events[events["event_name"] == "add_to_cart"]
    remove_from_cart = events[events["event_name"] == "remove_from_cart"]
    purchases = events[events["event_name"] == "purchase"]
    views = events[events["event_name"] == "view_item"]

    cart_sessions = add_to_cart["ga_session_id"].nunique()
    purchase_sessions = purchases["ga_session_id"].nunique()
    cart_abandonment_rate = (1 - purchase_sessions / (cart_sessions + 1e-9)) * 100

    daily_events = events.groupby(["event_date", "event_name"]).size().reset_index(name="count")

    top_items_viewed = events[events["event_name"] == "view_item"]["item_name"].value_counts().head(10).reset_index()
    top_items_viewed.columns = ["item_name", "views"]

    top_items_carted = add_to_cart["item_name"].value_counts().head(10).reset_index()
    top_items_carted.columns = ["item_name", "add_to_cart"]

    return {
        "event_counts": event_counts,
        "cart_abandonment_rate": cart_abandonment_rate,
        "cart_sessions": cart_sessions,
        "purchase_sessions": purchase_sessions,
        "daily_events": daily_events,
        "top_items_viewed": top_items_viewed,
        "top_items_carted": top_items_carted,
        "total_events": len(events),
        "unique_sessions": events["ga_session_id"].nunique(),
        "unique_users": events["user_pseudo_id"].nunique(),
    }

# def safe_dataframe(df):
#     """Convert all columns to Arrow-safe types before passing to st.dataframe"""
#     df = df.copy()
#     for col in df.columns:
#         if df[col].dtype == object:
#             df[col] = df[col].astype(str)
#         elif str(df[col].dtype).startswith("bool"):
#             df[col] = df[col].astype(str)
#     return df