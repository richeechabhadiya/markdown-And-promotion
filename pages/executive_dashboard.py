import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from utils.data_loader import load_orders, load_order_items, load_product_catalogue, compute_sales_metrics

def render():
    st.markdown("## 📊 Executive Dashboard")
    st.markdown("Real-time KPIs across Revenue, Margin, and Inventory performance.")

    orders = load_orders()
    order_items = load_order_items()
    metrics = compute_sales_metrics()

    completed_orders = orders[orders["state"] == "complete"]
    completed_items = order_items[order_items["order_state"] == "complete"]

    total_revenue = completed_orders["grand_total"].sum()
    total_orders = len(completed_orders)
    avg_order_value = completed_orders["grand_total"].mean()
    total_discount = completed_orders["discount_amount"].abs().sum()
    discount_rate = total_discount / (total_revenue + total_discount + 1e-9) * 100
    total_products = metrics["product_id"].nunique()
    dead_inventory_count = metrics["is_dead_inventory"].sum()
    high_risk_count = (metrics["clearance_risk"] == "HIGH").sum()

    # Pre-compute ABC counts and revenue once — used everywhere
    abc_a = int((metrics["abc_class"] == "A").sum())
    abc_b = int((metrics["abc_class"] == "B").sum())
    abc_c = int((metrics["abc_class"] == "C").sum())
    rev_a = metrics[metrics["abc_class"] == "A"]["total_revenue"].sum()
    rev_b = metrics[metrics["abc_class"] == "B"]["total_revenue"].sum()
    rev_c = metrics[metrics["abc_class"] == "C"]["total_revenue"].sum()

    # Pre-compute risk counts once — used everywhere
    risk_high  = int((metrics["clearance_risk"] == "HIGH").sum())
    risk_med   = int((metrics["clearance_risk"] == "MEDIUM").sum())
    risk_low   = int((metrics["clearance_risk"] == "LOW").sum())
    risk_total = risk_high + risk_med + risk_low

    # ── KPI Row 1 ──────────────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("💵 Total Revenue",   f"${total_revenue:,.0f}", "Completed Orders")
    c2.metric("🛒 Total Orders",    f"{total_orders:,}",      f"AOV: ${avg_order_value:.2f}")
    c3.metric("🏷️ Discount Rate",  f"{discount_rate:.1f}%",  f"${total_discount:,.0f} given")
    c4.metric("📦 Products",        f"{total_products:,}",    f"{dead_inventory_count} dead stock")

    st.divider()

    # ── KPI Row 2 ──────────────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🏆 Class A Products",     f"{abc_a} products", f"Revenue: ${rev_a:,.0f}")
    c2.metric("🟡 Class B Products",     f"{abc_b} products", f"Revenue: ${rev_b:,.0f}")
    c3.metric("🔴 High Clearance Risk",  f"{risk_high} products", "Needs Markdown")
    c4.metric("⚠️ Dead Inventory",       f"{dead_inventory_count}", ">180 days stock")

    st.divider()

    # ── Charts Row 1 ───────────────────────────────────────────────────────
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 📅 Monthly Revenue Trend")
        monthly = completed_orders.copy()
        monthly["month"] = monthly["order_date"].dt.to_period("M").astype(str)
        monthly_rev = monthly.groupby("month")["grand_total"].sum().reset_index()
        monthly_rev.columns = ["Month", "Revenue"]
        monthly_rev = monthly_rev.sort_values("Month")
        fig = px.area(monthly_rev, x="Month", y="Revenue",
                      color_discrete_sequence=["#6366f1"],
                      labels={"Revenue": "Revenue ($)"})
        fig.update_layout(height=300, margin=dict(l=0, r=0, t=20, b=0),
                          plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("### 🏷️ ABC — Product Count vs Revenue Share")

        # Two tabs — one for product count, one for revenue
        tab1, tab2 = st.tabs(["By Product Count", "By Revenue Share"])

        with tab1:
            abc_count_data = pd.DataFrame({
                "Class": ["A — Top Performers", "B — Mid Tier", "C — Tail"],
                "Products": [abc_a, abc_b, abc_c]
            })
            fig = px.pie(
                abc_count_data, values="Products", names="Class", hole=0.45,
                color="Class",
                color_discrete_map={
                    "A — Top Performers": "#10b981",
                    "B — Mid Tier":       "#f59e0b",
                    "C — Tail":           "#ef4444"
                }
            )
            fig.update_traces(textposition="inside", textinfo="percent+label", sort=False)
            fig.update_layout(height=260, margin=dict(l=0, r=0, t=10, b=0),
                              paper_bgcolor="rgba(0,0,0,0)", showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
            st.caption(f"🟢 A: {abc_a} products  |  🟡 B: {abc_b} products  |  🔴 C: {abc_c} products")

        with tab2:
            abc_rev_data = pd.DataFrame({
                "Class": ["A — Top Performers", "B — Mid Tier", "C — Tail"],
                "Revenue": [rev_a, rev_b, rev_c]
            })
            fig = px.pie(
                abc_rev_data, values="Revenue", names="Class", hole=0.45,
                color="Class",
                color_discrete_map={
                    "A — Top Performers": "#10b981",
                    "B — Mid Tier":       "#f59e0b",
                    "C — Tail":           "#ef4444"
                }
            )
            fig.update_traces(textposition="inside", textinfo="percent+label", sort=False)
            fig.update_layout(height=260, margin=dict(l=0, r=0, t=10, b=0),
                              paper_bgcolor="rgba(0,0,0,0)", showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
            st.caption(f"🟢 A: ${rev_a:,.0f}  |  🟡 B: ${rev_b:,.0f}  |  🔴 C: ${rev_c:,.0f}")

    # ── Charts Row 2 ───────────────────────────────────────────────────────
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 🔥 Clearance Risk Breakdown")
        st.caption("Based on product count — same total products as ABC above")

        risk_counts = pd.DataFrame({
            "Risk":    ["HIGH",      "MEDIUM",   "LOW"],
            "Count":   [risk_high,   risk_med,   risk_low],
            "Pct":     [
                round(risk_high  / risk_total * 100, 1),
                round(risk_med   / risk_total * 100, 1),
                round(risk_low   / risk_total * 100, 1),
            ]
        })

        fig = px.bar(
            risk_counts, x="Pct", y="Risk", orientation="h",
            color="Risk",
            color_discrete_map={"HIGH": "#ef4444", "MEDIUM": "#f59e0b", "LOW": "#10b981"},
            text="Pct",
            labels={"Pct": "% of Products", "Risk": ""}
        )
        fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
        fig.update_layout(
            height=300, margin=dict(l=0, r=60, t=20, b=0),
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            showlegend=False, xaxis=dict(range=[0, 110])
        )
        st.plotly_chart(fig, use_container_width=True)
        st.caption(
            f"🔴 HIGH: {risk_high} products  "
            f"|  🟡 MEDIUM: {risk_med} products  "
            f"|  🟢 LOW: {risk_low} products  "
            f"|  Total: {risk_total} products"
        )

    with col2:
        st.markdown("### 💳 Payment Methods")
        pay = completed_orders["payment_method"].value_counts().head(5).reset_index()
        pay.columns = ["Method", "Count"]
        fig = px.bar(pay, x="Count", y="Method", orientation="h",
                     color_discrete_sequence=["#6366f1"])
        fig.update_layout(height=300, margin=dict(l=0, r=0, t=20, b=0),
                          plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)

    # ── Top 10 Products Table ──────────────────────────────────────────────
    st.markdown("### 🏪 Top 10 Revenue-Generating Products")
    top_products = metrics.nlargest(10, "total_revenue")[
        ["product_name", "main_category", "total_revenue", "total_qty_sold",
         "abc_class", "clearance_risk", "sell_through_rate"]
    ].copy()
    top_products["total_revenue"]    = top_products["total_revenue"].map("${:,.2f}".format)
    top_products["sell_through_rate"] = top_products["sell_through_rate"].map("{:.1f}%".format)
    top_products.columns = ["Product", "Category", "Revenue", "Qty Sold", "ABC", "Risk", "Sell-Through"]
    st.dataframe(top_products, use_container_width=True, hide_index=True)