import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from utils.data_loader import compute_sales_metrics

def render():
    st.markdown("## 📦 Inventory Intelligence Dashboard")
    st.markdown("Overstock alerts, dead inventory detection, and ABC classification insights.")

    metrics = compute_sales_metrics()

    # Summary KPIs
    total_stock = metrics["quantity"].sum()
    dead_count = metrics["is_dead_inventory"].sum()
    high_risk = (metrics["clearance_risk"] == "HIGH").sum()
    out_of_stock = (metrics["quantity"] == 0).sum()
    avg_days_stock = metrics[metrics["days_of_stock"] < 9999]["days_of_stock"].median()

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("📦 Total Stock Units", f"{total_stock:,.0f}")
    c2.metric("💀 Dead Inventory", f"{dead_count}", ">180 days stock")
    c3.metric("🔴 High Risk Items", f"{high_risk}", "Needs action")
    c4.metric("🚫 Out of Stock", f"{out_of_stock}")
    c5.metric("📅 Median Days Stock", f"{avg_days_stock:.0f} days")

    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 🏷️ ABC Classification — Revenue Contribution")
        abc_rev = metrics.groupby("abc_class")["total_revenue"].sum().reset_index()
        abc_rev.columns = ["Class", "Revenue"]
        fig = px.bar(abc_rev, x="Class", y="Revenue",
                     color="Class",
                     color_discrete_map={"A": "#10b981", "B": "#f59e0b", "C": "#ef4444"},
                     labels={"Revenue": "Total Revenue ($)"})
        fig.update_layout(height=300, margin=dict(l=0,r=0,t=20,b=0),
                          plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                          showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("### ⏳ Days of Stock Distribution")
        valid_days = metrics[(metrics["days_of_stock"] < 1000) & (metrics["days_of_stock"] > 0)]["days_of_stock"]
        fig = px.histogram(valid_days, nbins=40, 
                           color_discrete_sequence=["#6366f1"],
                           labels={"value": "Days of Stock", "count": "# Products"})
        fig.add_vline(x=90, line_dash="dash", line_color="#ef4444", annotation_text="90-day risk")
        fig.add_vline(x=180, line_dash="dash", line_color="#7c3aed", annotation_text="Dead stock")
        fig.update_layout(height=300, margin=dict(l=0,r=0,t=20,b=0),
                          plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # Overstock heatmap by category
    st.markdown("### 🌡️ Inventory Pressure by Category")
    cat_pressure = metrics[metrics["main_category"].notna()].groupby("main_category").agg(
        avg_pressure=("inventory_pressure", "mean"),
        total_stock=("quantity", "sum"),
        high_risk_count=("clearance_risk", lambda x: (x=="HIGH").sum()),
        product_count=("product_id", "count")
    ).reset_index().sort_values("avg_pressure", ascending=False).head(15)

    fig = px.bar(cat_pressure, x="avg_pressure", y="main_category", orientation="h",
                 color="avg_pressure", color_continuous_scale="RdYlGn_r",
                 labels={"avg_pressure": "Avg Inventory Pressure", "main_category": "Category"})
    fig.update_layout(height=420, margin=dict(l=0,r=0,t=20,b=0),
                      plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # ABC detail table
    tabs = st.tabs(["🔴 Dead Inventory", "🟠 High Risk", "🏆 Class A Products", "All Products"])

    with tabs[0]:
        dead = metrics[metrics["is_dead_inventory"]].nlargest(50, "quantity")[
            ["product_name", "main_category", "quantity", "sales_velocity", "days_of_stock",
             "total_revenue", "price", "abc_class"]
        ].copy()
        dead["days_of_stock"] = dead["days_of_stock"].clip(upper=9999).map("{:.0f}".format)
        dead["sales_velocity"] = dead["sales_velocity"].map("{:.4f}".format)
        dead["total_revenue"] = dead["total_revenue"].map("${:,.2f}".format)
        dead["price"] = dead["price"].map("${:,.2f}".format)
        dead.columns = ["Product", "Category", "Stock", "Velocity", "Days Stock", "Revenue", "Price", "ABC"]
        st.dataframe(dead, use_container_width=True, hide_index=True)

    with tabs[1]:
        high = metrics[metrics["clearance_risk"] == "HIGH"].nlargest(50, "quantity")[
            ["product_name", "main_category", "quantity", "sales_velocity", "inventory_pressure",
             "sell_through_rate", "price", "abc_class"]
        ].copy()
        high["sales_velocity"] = high["sales_velocity"].map("{:.4f}".format)
        high["inventory_pressure"] = high["inventory_pressure"].map("{:.1f}".format)
        high["sell_through_rate"] = high["sell_through_rate"].map("{:.1f}%".format)
        high["price"] = high["price"].map("${:,.2f}".format)
        high.columns = ["Product", "Category", "Stock", "Velocity", "Pressure", "Sell-Through", "Price", "ABC"]
        st.dataframe(high, use_container_width=True, hide_index=True)

    with tabs[2]:
        class_a = metrics[metrics["abc_class"] == "A"].nlargest(50, "total_revenue")[
            ["product_name", "main_category", "total_revenue", "total_qty_sold",
             "sell_through_rate", "quantity", "price"]
        ].copy()
        class_a["total_revenue"] = class_a["total_revenue"].map("${:,.2f}".format)
        class_a["sell_through_rate"] = class_a["sell_through_rate"].map("{:.1f}%".format)
        class_a["price"] = class_a["price"].map("${:,.2f}".format)
        class_a.columns = ["Product", "Category", "Revenue", "Qty Sold", "Sell-Through", "Stock", "Price"]
        st.dataframe(class_a, use_container_width=True, hide_index=True)

    with tabs[3]:
        all_df = metrics[
            ["product_name", "main_category", "quantity", "total_qty_sold",
             "sales_velocity", "sell_through_rate", "abc_class", "clearance_risk",
             "inventory_pressure", "is_dead_inventory"]
        ].copy()
        all_df["sales_velocity"] = all_df["sales_velocity"].map("{:.4f}".format)
        all_df["sell_through_rate"] = all_df["sell_through_rate"].map("{:.1f}%".format)
        all_df["inventory_pressure"] = all_df["inventory_pressure"].map("{:.1f}".format)
        all_df.columns = ["Product", "Category", "Stock", "Sold", "Velocity", "Sell-Through",
                          "ABC", "Risk", "Pressure", "Dead?"]
        st.dataframe(all_df, use_container_width=True, hide_index=True)
