import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from utils.data_loader import compute_sales_metrics, compute_event_metrics, compute_elasticity_data
from agents.multi_agent import RetailAISystem

def render():
    st.markdown("## 🧠 AI Agent Insights Dashboard")
    st.markdown("Run the multi-agent system on any product and see each agent's individual reasoning.")

    metrics = compute_sales_metrics()
    event_metrics = compute_event_metrics()
    elasticity_df = compute_elasticity_data()

    ai_system = RetailAISystem()

    # Product selector
    st.markdown("### 🔍 Select a Product for AI Analysis")
    
    col1, col2 = st.columns([2, 1])
    with col1:
        category_options = ["All"] + sorted(metrics["main_category"].dropna().unique().tolist())
        selected_category = st.selectbox("Filter by Category", category_options)

    filtered = metrics if selected_category == "All" else metrics[metrics["main_category"] == selected_category]
    filtered = filtered[filtered["price"] > 0].dropna(subset=["product_name"])

    with col2:
        risk_options = ["All", "HIGH", "MEDIUM", "LOW"]
        risk_filter = st.selectbox("Filter by Risk", risk_options)
    
    if risk_filter != "All":
        filtered = filtered[filtered["clearance_risk"] == risk_filter]

    product_names = filtered["product_name"].head(200).tolist()
    if not product_names:
        st.warning("No products match the selected filters.")
        return

    selected_name = st.selectbox("🛍️ Choose a Product", product_names)
    selected_product = filtered[filtered["product_name"] == selected_name].iloc[0]

    # Get elasticity
    elast = elasticity_df[elasticity_df["product_id"] == selected_product["product_id"]]["elasticity"].mean()
    if np.isnan(elast):
        elast = -1.2

    st.divider()

    # Run agents
    with st.spinner("🤖 Running multi-agent analysis..."):
        result = ai_system.run(selected_product, event_metrics, elasticity=float(elast))

    # Final decision banner
    risk_colors = {"🔴 Critical": "🔴", "🟠 High": "🟠", "🟡 Medium": "🟡", "🟢 Low": "🟢"}
    risk_emoji = result["risk_level"].split()[0]

    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #1e1b4b, #312e81); border-radius: 16px; padding: 24px; margin: 12px 0; border: 1px solid #4f46e5;">
        <h2 style="color: #a5b4fc; margin: 0 0 16px 0;">🧠 Coordinator Agent — Final Recommendation</h2>
        <div style="display: grid; grid-template-columns: repeat(5, 1fr); gap: 16px;">
            <div style="text-align: center;">
                <div style="font-size: 2rem; font-weight: 800; color: #6ee7b7;">{result['recommended_markdown']:.1f}%</div>
                <div style="color: #94a3b8; font-size: 0.8rem;">Markdown</div>
            </div>
            <div style="text-align: center;">
                <div style="font-size: 2rem; font-weight: 800; color: #fcd34d;">{result['risk_level']}</div>
                <div style="color: #94a3b8; font-size: 0.8rem;">Risk Level</div>
            </div>
            <div style="font-size: 2rem; font-weight: 800; color: #86efac; text-align: center;">
                <div>+{result['revenue_uplift_pct']:.1f}%</div>
                <div style="color: #94a3b8; font-size: 0.8rem;">Rev Uplift</div>
            </div>
            <div style="text-align: center;">
                <div style="font-size: 2rem; font-weight: 800; color: #fca5a5;">{result['margin_impact']:.1f}%</div>
                <div style="color: #94a3b8; font-size: 0.8rem;">Margin Impact</div>
            </div>
            <div style="text-align: center;">
                <div style="font-size: 2rem; font-weight: 800; color: #93c5fd;">{result['clearance_probability']:.0f}%</div>
                <div style="color: #94a3b8; font-size: 0.8rem;">Clearance Prob.</div>
            </div>
        </div>
        <div style="margin-top: 16px; padding: 12px; background: rgba(255,255,255,0.05); border-radius: 8px;">
            <span style="color: #c7d2fe;">Strategy: </span>
            <span style="color: white; font-weight: 600;">{result['strategy']}</span>
            &nbsp;&nbsp;|&nbsp;&nbsp;
            <span style="color: #c7d2fe;">Confidence: </span>
            <span style="color: white; font-weight: 600;">{result['confidence']:.0f}%</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Agent outputs
    st.markdown("### 🤖 Individual Agent Outputs")
    agent_outputs = result["agent_outputs"]

    agent_list = list(agent_outputs.values())
    for i in range(0, len(agent_list), 2):
        cols = st.columns(2)
        for j, col in enumerate(cols):
            if i + j < len(agent_list):
                agent = agent_list[i + j]
                conf_color = "#10b981" if agent.confidence > 0.8 else "#f59e0b" if agent.confidence > 0.65 else "#ef4444"
                with col:
                    with st.expander(f"{agent.agent_name} — {agent.recommendation[:50]}...", expanded=True):
                        st.markdown(f"**Recommendation:** {agent.recommendation}")
                        st.progress(agent.confidence, text=f"Confidence: {agent.confidence*100:.0f}%")
                        st.markdown(f"**Reasoning:** {agent.reasoning}")
                        if agent.data:
                            st.json(agent.data)

    # Coordinator reasoning
    st.divider()
    st.markdown("### 📝 Coordinator Full Reasoning")
    st.markdown(result["reasoning"])

    # Confidence radar
    st.markdown("### 📡 Agent Confidence Radar")
    agent_names = [a.agent_name.replace(" Agent", "") for a in agent_list]
    confidence_values = [a.confidence * 100 for a in agent_list]
    confidence_values.append(confidence_values[0])  # close the polygon
    agent_names_closed = agent_names + [agent_names[0]]

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=confidence_values, theta=agent_names_closed,
        fill="toself", name="Confidence",
        line_color="#6366f1", fillcolor="rgba(99,102,241,0.2)"
    ))
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
        height=360, margin=dict(l=0,r=0,t=20,b=0),
        paper_bgcolor="rgba(0,0,0,0)"
    )
    st.plotly_chart(fig, use_container_width=True)

    # Human approval
    st.divider()
    st.markdown("### ✅ Human-in-the-Loop Approval")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("✅ Approve Recommendation", type="primary", use_container_width=True):
            st.success(f"✅ Approved! {result['recommended_markdown']:.1f}% markdown scheduled for **{selected_name}**.")
    with col2:
        if st.button("✏️ Override Markdown", use_container_width=True):
            override_val = st.number_input("Enter override markdown %", 0.0, 80.0, float(result["recommended_markdown"]))
            st.info(f"Override set to {override_val:.1f}%")
    with col3:
        if st.button("❌ Reject & Escalate", use_container_width=True):
            st.error("Recommendation rejected and escalated to pricing team.")
