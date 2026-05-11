import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from utils.data_loader import load_orders, load_order_items, compute_sales_metrics

def render():
    st.markdown("## 📈 Demand Forecast Dashboard")
    st.markdown("Sales velocity analysis and product-level demand predictions.")

    orders = load_orders()
    order_items = load_order_items()
    metrics = compute_sales_metrics()

    completed_orders = orders[orders["state"] == "complete"]
    completed_items = order_items[order_items["order_state"] == "complete"]

    # Weekly trend
    weekly = completed_orders.copy()
    weekly["week"] = weekly["order_date"].dt.to_period("W").astype(str)
    weekly_data = weekly.groupby("week").agg(
        orders=("order_id", "count"),
        revenue=("grand_total", "sum"),
        qty=("total_qty_ordered", "sum")
    ).reset_index().sort_values("week")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 📦 Weekly Units Ordered")
        fig = px.bar(weekly_data.tail(26), x="week", y="qty",
                     color_discrete_sequence=["#6366f1"],
                     labels={"qty": "Units Ordered", "week": "Week"})
        fig.update_layout(height=320, margin=dict(l=0,r=0,t=20,b=0),
                          plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("### 📅 Weekly Revenue Trend")
        fig = px.line(weekly_data.tail(26), x="week", y="revenue",
                      color_discrete_sequence=["#10b981"],
                      markers=True,
                      labels={"revenue": "Revenue ($)", "week": "Week"})
        fig.update_layout(height=320, margin=dict(l=0,r=0,t=20,b=0),
                          plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # Demand heatmap by category
    st.markdown("### 🗓️ Sales by Category & Month")
    cat_monthly = completed_items.copy()
    cat_monthly["month"] = cat_monthly["order_date"].dt.strftime("%Y-%m")
    cat_pivot = cat_monthly.groupby(["product_main_category", "month"])["qty_ordered"].sum().reset_index()
    cat_pivot = cat_pivot[cat_pivot["product_main_category"].notna()]
    top_cats = cat_pivot.groupby("product_main_category")["qty_ordered"].sum().nlargest(8).index
    cat_pivot = cat_pivot[cat_pivot["product_main_category"].isin(top_cats)]
    pivot_table = cat_pivot.pivot_table(index="product_main_category", columns="month", values="qty_ordered", fill_value=0)
    
    if not pivot_table.empty:
        fig = px.imshow(pivot_table, color_continuous_scale="Blues",
                        labels=dict(x="Month", y="Category", color="Units"))
        fig.update_layout(height=380, margin=dict(l=0,r=0,t=20,b=0),
                          paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # Product demand table
    st.markdown("### 🔍 Product-Level Demand Intelligence")

    col1, col2, col3 = st.columns(3)
    velocity_filter = col1.selectbox("Sales Velocity", ["All", "High (>0.5/day)", "Medium (0.1-0.5)", "Low (<0.1)"])
    category_options = ["All"] + sorted(metrics["main_category"].dropna().unique().tolist())
    category_filter = col2.selectbox("Category", category_options)
    n_rows = col3.slider("Show rows", 10, 100, 25)

    demand_df = metrics[["product_name", "main_category", "sales_velocity", "total_qty_sold",
                          "order_count", "sell_through_rate", "abc_class"]].copy()

    if velocity_filter == "High (>0.5/day)":
        demand_df = demand_df[demand_df["sales_velocity"] > 0.5]
    elif velocity_filter == "Medium (0.1-0.5)":
        demand_df = demand_df[(demand_df["sales_velocity"] >= 0.1) & (demand_df["sales_velocity"] <= 0.5)]
    elif velocity_filter == "Low (<0.1)":
        demand_df = demand_df[demand_df["sales_velocity"] < 0.1]

    if category_filter != "All":
        demand_df = demand_df[demand_df["main_category"] == category_filter]

    # Add 30-day forecast
    demand_df["forecast_30d"] = (demand_df["sales_velocity"] * 30).round(0).astype(int)
    demand_df["forecast_90d"] = (demand_df["sales_velocity"] * 90).round(0).astype(int)

    display_df = demand_df.nlargest(n_rows, "total_qty_sold")[
        ["product_name", "main_category", "sales_velocity", "total_qty_sold",
         "forecast_30d", "forecast_90d", "sell_through_rate", "abc_class"]
    ].copy()

    display_df["sales_velocity"] = display_df["sales_velocity"].map("{:.3f}".format)
    display_df["sell_through_rate"] = display_df["sell_through_rate"].map("{:.1f}%".format)
    display_df.columns = ["Product", "Category", "Velocity/Day", "Total Sold",
                          "30D Forecast", "90D Forecast", "Sell-Through", "ABC"]
    st.dataframe(display_df, use_container_width=True, hide_index=True)

    # Scatter plot: velocity vs sell-through
    st.markdown("### 🎯 Sales Velocity vs Sell-Through Rate")
    scatter_df = metrics[metrics["sales_velocity"] > 0].head(200).copy()
    fig = px.scatter(
        scatter_df, x="sales_velocity", y="sell_through_rate",
        color="clearance_risk", size="quantity",
        color_discrete_map={"HIGH": "#ef4444", "MEDIUM": "#f59e0b", "LOW": "#10b981"},
        hover_data=["product_name", "abc_class"],
        labels={"sales_velocity": "Sales Velocity (units/day)", "sell_through_rate": "Sell-Through Rate (%)"}
    )
    fig.update_layout(height=380, margin=dict(l=0,r=0,t=20,b=0),
                      plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, use_container_width=True)
