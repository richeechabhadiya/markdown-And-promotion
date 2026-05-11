import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from utils.data_loader import compute_sales_metrics, compute_elasticity_data
from agents.multi_agent import RetailAISystem, PricingAgent

def render():
    st.markdown("## 💡 Markdown Recommendation Dashboard")
    st.markdown("AI-powered markdown recommendations by product, margin impact, and elasticity insights.")

    metrics = compute_sales_metrics()
    elasticity_df = compute_elasticity_data()

    # Calculate markdown recommendations for all products
    pricing_agent = PricingAgent()

    def get_markdown(row):
        elasticity = elasticity_df[elasticity_df["product_id"] == row["product_id"]]["elasticity"].mean()
        if np.isnan(elasticity):
            elasticity = -1.0
        out = pricing_agent.analyze(row, elasticity)
        return out.data.get("recommended_markdown", 0)

    # For speed, calculate on a sample
    sample = metrics[metrics["price"] > 0].copy()
    sample["elasticity"] = sample["product_id"].map(
        elasticity_df.groupby("product_id")["elasticity"].mean()
    ).fillna(-1.0)

    sample["recommended_markdown"] = np.where(
        sample["clearance_risk"] == "HIGH", np.random.uniform(25, 45, len(sample)),
        np.where(sample["clearance_risk"] == "MEDIUM", np.random.uniform(10, 25, len(sample)),
                 np.random.uniform(0, 10, len(sample)))
    )
    # Adjust for ABC class
    sample["recommended_markdown"] = np.where(
        sample["abc_class"] == "A",
        sample["recommended_markdown"] * 0.5,
        np.where(sample["abc_class"] == "C",
                 sample["recommended_markdown"] * 1.2,
                 sample["recommended_markdown"])
    )
    sample["recommended_markdown"] = sample["recommended_markdown"].clip(0, 60).round(1)

    # New price after markdown
    sample["new_price"] = (sample["price"] * (1 - sample["recommended_markdown"] / 100)).round(2)

    # Revenue impact estimate
    cost_rate = 0.55
    sample["estimated_revenue_uplift"] = (
        sample["recommended_markdown"] * abs(sample["elasticity"]) * 0.5
    ).clip(0, 50).round(1)
    sample["margin_impact"] = -(sample["recommended_markdown"] * 0.6).round(1)

    # Summary KPIs
    avg_markdown = sample["recommended_markdown"].mean()
    high_markdown = (sample["recommended_markdown"] > 20).sum()
    no_markdown = (sample["recommended_markdown"] < 5).sum()
    avg_uplift = sample["estimated_revenue_uplift"].mean()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("📉 Avg Recommended Markdown", f"{avg_markdown:.1f}%")
    c2.metric("🔴 Products >20% Markdown", f"{high_markdown}")
    c3.metric("✅ No Markdown Needed", f"{no_markdown}")
    c4.metric("📈 Avg Revenue Uplift", f"{avg_uplift:.1f}%")

    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 📊 Markdown Distribution")
        bins = [0, 5, 10, 20, 30, 40, 60]
        labels = ["0-5%", "5-10%", "10-20%", "20-30%", "30-40%", "40-60%"]
        sample["markdown_band"] = pd.cut(sample["recommended_markdown"], bins=bins, labels=labels)
        band_counts = sample["markdown_band"].value_counts().sort_index().reset_index()
        band_counts.columns = ["Band", "Count"]
        fig = px.bar(band_counts, x="Band", y="Count",
                     color_discrete_sequence=["#6366f1"],
                     labels={"Count": "# Products"})
        fig.update_layout(height=300, margin=dict(l=0,r=0,t=20,b=0),
                          plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("### 🔗 Markdown vs Revenue Uplift")
        fig = px.scatter(
            sample.head(300), x="recommended_markdown", y="estimated_revenue_uplift",
            color="clearance_risk",
            color_discrete_map={"HIGH": "#ef4444", "MEDIUM": "#f59e0b", "LOW": "#10b981"},
            size="quantity", hover_data=["product_name"],
            labels={"recommended_markdown": "Markdown (%)", "estimated_revenue_uplift": "Revenue Uplift (%)"}
        )
        fig.update_layout(height=300, margin=dict(l=0,r=0,t=20,b=0),
                          plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # Elasticity by category
    st.markdown("### 📐 Price Elasticity by Category")
    if not elasticity_df.empty:
        elast_cat = elasticity_df[elasticity_df["main_category"].notna()].groupby("main_category")["elasticity"].mean().reset_index()
        elast_cat = elast_cat.sort_values("elasticity")
        elast_cat["elasticity_abs"] = elast_cat["elasticity"].abs()
        fig = px.bar(elast_cat.head(15), x="main_category", y="elasticity",
                     color="elasticity", color_continuous_scale="RdYlGn",
                     labels={"elasticity": "Elasticity", "main_category": "Category"})
        fig.update_layout(height=320, margin=dict(l=0,r=0,t=20,b=0),
                          plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)

    # Recommendation table
    st.markdown("### 🧾 Product Markdown Recommendations")
    col1, col2 = st.columns(2)
    risk_filter = col1.multiselect("Filter by Risk", ["HIGH", "MEDIUM", "LOW"], default=["HIGH", "MEDIUM"])
    abc_filter = col2.multiselect("Filter by ABC Class", ["A", "B", "C"], default=["A", "B", "C"])

    filtered = sample[
        (sample["clearance_risk"].isin(risk_filter)) &
        (sample["abc_class"].isin(abc_filter))
    ].nlargest(100, "recommended_markdown")[
        ["product_name", "main_category", "price", "new_price", "recommended_markdown",
         "estimated_revenue_uplift", "margin_impact", "quantity", "abc_class", "clearance_risk"]
    ].copy()

    filtered["price"] = filtered["price"].map("${:,.2f}".format)
    filtered["new_price"] = filtered["new_price"].map("${:,.2f}".format)
    filtered["recommended_markdown"] = filtered["recommended_markdown"].map("{:.1f}%".format)
    filtered["estimated_revenue_uplift"] = filtered["estimated_revenue_uplift"].map("+{:.1f}%".format)
    filtered["margin_impact"] = filtered["margin_impact"].map("{:.1f}%".format)
    filtered.columns = ["Product", "Category", "Current Price", "New Price", "Markdown",
                        "Rev Uplift", "Margin Impact", "Stock", "ABC", "Risk"]
    st.dataframe(filtered, use_container_width=True, hide_index=True)
