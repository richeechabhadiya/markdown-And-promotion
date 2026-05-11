import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from utils.data_loader import compute_sales_metrics, compute_elasticity_data

def render():
    st.markdown("## 🔮 What-If Pricing Simulator")
    st.markdown("Simulate different markdown percentages and predict the impact on sales, revenue, and margins.")

    metrics = compute_sales_metrics()
    elasticity_df = compute_elasticity_data()

    col1, col2 = st.columns([2, 1])
    with col1:
        product_options = metrics[metrics["price"] > 0]["product_name"].dropna().head(300).tolist()
        selected_name = st.selectbox("🛍️ Select Product", product_options)
    with col2:
        category_options = ["All"] + sorted(metrics["main_category"].dropna().unique().tolist())
        st.selectbox("Browse by Category", category_options, key="sim_cat")

    product = metrics[metrics["product_name"] == selected_name].iloc[0]
    pid = product["product_id"]
    price = product["price"]
    quantity = product["quantity"]
    velocity = product["sales_velocity"]
    abc_class = product["abc_class"]
    clearance_risk = product["clearance_risk"]
    sell_through = product["sell_through_rate"]

    elast = elasticity_df[elasticity_df["product_id"] == pid]["elasticity"].mean()
    if np.isnan(elast):
        elast = -1.2

    # Product info card
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("💰 Current Price", f"${price:.2f}")
    col2.metric("📦 Stock", f"{quantity:.0f} units")
    col3.metric("🏷️ ABC Class", abc_class)
    col4.metric("⚠️ Risk", clearance_risk)

    st.divider()

    # Simulator controls
    st.markdown("### 🎛️ Simulator Controls")
    col1, col2, col3 = st.columns(3)
    with col1:
        markdown_pct = st.slider("Markdown Percentage (%)", 0, 70, 15, step=5)
    with col2:
        elasticity_override = st.slider("Price Elasticity", -5.0, -0.1, float(round(elast, 1)), step=0.1)
    with col3:
        forecast_days = st.slider("Forecast Horizon (days)", 7, 180, 30)

    # Calculations
    new_price = price * (1 - markdown_pct / 100)
    cost_estimate = price * 0.55
    
    original_margin = ((price - cost_estimate) / price * 100) if price > 0 else 0
    new_margin = ((new_price - cost_estimate) / new_price * 100) if new_price > 0 else 0
    margin_impact = new_margin - original_margin

    demand_multiplier = 1 + abs(elasticity_override) * (markdown_pct / 100)
    new_velocity = velocity * demand_multiplier

    base_qty = velocity * forecast_days
    new_qty = new_velocity * forecast_days
    incremental_qty = new_qty - base_qty

    base_revenue = base_qty * price
    new_revenue = new_qty * new_price
    revenue_change = new_revenue - base_revenue
    revenue_change_pct = (revenue_change / (base_revenue + 1e-9)) * 100

    base_profit = base_qty * (price - cost_estimate)
    new_profit = new_qty * (new_price - cost_estimate)
    profit_change = new_profit - base_profit

    clearance_prob = min(
        (new_qty / (quantity + 1e-9)) * 100,
        98
    )

    # Results banner
    st.divider()
    st.markdown("### 📊 Simulation Results")

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("🏷️ New Price", f"${new_price:.2f}", f"-${price-new_price:.2f}")
    c2.metric("📦 Units Sold", f"{new_qty:.0f}", f"+{incremental_qty:.0f}")
    c3.metric("💵 Revenue", f"${new_revenue:,.0f}", f"{revenue_change_pct:+.1f}%")
    c4.metric("📉 Margin", f"{new_margin:.1f}%", f"{margin_impact:.1f}pp")
    c5.metric("🎯 Clearance Prob.", f"{min(clearance_prob,98):.0f}%")

    st.divider()

    # Sweep simulation: show all markdown levels
    st.markdown("### 📈 Markdown Sweep Analysis")
    sweep_pcts = list(range(0, 65, 5))
    sweep_results = []
    for pct in sweep_pcts:
        np_ = price * (1 - pct / 100)
        dm = 1 + abs(elasticity_override) * (pct / 100)
        q = velocity * forecast_days * dm
        rev = q * np_
        prof = q * (np_ - cost_estimate)
        marg = ((np_ - cost_estimate) / (np_ + 1e-9)) * 100
        sweep_results.append({
            "Markdown %": pct, "New Price": np_,
            "Units": round(q, 1), "Revenue": round(rev, 2),
            "Profit": round(prof, 2), "Margin %": round(marg, 1)
        })
    sweep_df = pd.DataFrame(sweep_results)

    col1, col2 = st.columns(2)
    with col1:
        fig = px.line(sweep_df, x="Markdown %", y=["Revenue", "Profit"],
                      color_discrete_sequence=["#6366f1", "#10b981"],
                      labels={"value": "$", "variable": "Metric"},
                      title="Revenue vs Profit by Markdown Depth")
        fig.add_vline(x=markdown_pct, line_dash="dash", line_color="#ef4444",
                      annotation_text=f"Selected: {markdown_pct}%")
        fig.update_layout(height=350, margin=dict(l=0,r=0,t=40,b=0),
                          plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig = px.line(sweep_df, x="Markdown %", y=["Units", "Margin %"],
                      color_discrete_sequence=["#f59e0b", "#ef4444"],
                      labels={"value": "Value", "variable": "Metric"},
                      title="Units Sold & Margin by Markdown Depth")
        fig.add_vline(x=markdown_pct, line_dash="dash", line_color="#6366f1",
                      annotation_text=f"Selected: {markdown_pct}%")
        fig.update_layout(height=350, margin=dict(l=0,r=0,t=40,b=0),
                          plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)

    # Optimal markdown finder
    sweep_df["Revenue_Score"] = (sweep_df["Revenue"] / sweep_df["Revenue"].max()) * 0.6 + \
                                 (sweep_df["Margin %"] / sweep_df["Margin %"].max()) * 0.4
    optimal_row = sweep_df.loc[sweep_df["Revenue_Score"].idxmax()]

    st.success(
        f"🎯 **Optimal Markdown:** {optimal_row['Markdown %']:.0f}% — "
        f"Projected Revenue: ${optimal_row['Revenue']:,.0f} | "
        f"Units: {optimal_row['Units']:.0f} | Margin: {optimal_row['Margin %']:.1f}%"
    )

    st.markdown("### 📋 Full Sweep Table")
    display_sweep = sweep_df.copy()
    display_sweep["New Price"] = display_sweep["New Price"].map("${:,.2f}".format)
    display_sweep["Revenue"] = display_sweep["Revenue"].map("${:,.0f}".format)
    display_sweep["Profit"] = display_sweep["Profit"].map("${:,.0f}".format)
    display_sweep["Margin %"] = display_sweep["Margin %"].map("{:.1f}%".format)
    display_sweep = display_sweep.drop(columns=["Revenue_Score"])
    st.dataframe(display_sweep, use_container_width=True, hide_index=True)
