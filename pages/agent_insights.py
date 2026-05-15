import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from utils.data_loader import compute_sales_metrics, compute_event_metrics, compute_elasticity_data
from agents.multi_agent import RetailAISystem


def render():
    st.markdown("## 🧠 AI Agent Insights Dashboard")
    st.markdown("Select any product and run the full multi-agent AI system to get a transparent, explainable markdown recommendation.")

    metrics       = compute_sales_metrics()
    event_metrics = compute_event_metrics()
    elasticity_df = compute_elasticity_data()
    ai_system     = RetailAISystem()

    # ── Product Selector ───────────────────────────────────────────────────
    st.markdown("### 🔍 Select a Product for AI Analysis")

    col1, col2 = st.columns([2, 1])
    with col1:
        category_options  = ["All"] + sorted(metrics["main_category"].dropna().unique().tolist())
        selected_category = st.selectbox("Filter by Category", category_options)

    filtered = metrics if selected_category == "All" else metrics[metrics["main_category"] == selected_category]
    filtered = filtered[filtered["price"] > 0].dropna(subset=["product_name"])

    with col2:
        risk_filter = st.selectbox("Filter by Risk", ["All", "HIGH", "MEDIUM", "LOW"])

    if risk_filter != "All":
        filtered = filtered[filtered["clearance_risk"] == risk_filter]

    product_names = filtered["product_name"].head(200).tolist()
    if not product_names:
        st.warning("No products match the selected filters.")
        return

    selected_name    = st.selectbox("🛍️ Choose a Product", product_names)
    selected_product = filtered[filtered["product_name"] == selected_name].iloc[0]

    pi1, pi2, pi3, pi4, pi5 = st.columns(5)
    pi1.metric("💰 Price",        f"${selected_product['price']:.2f}")
    pi2.metric("📦 Stock",        f"{selected_product['quantity']:.0f} units")
    pi3.metric("🏷️ ABC Class",   selected_product["abc_class"])
    pi4.metric("⚠️ Risk",        selected_product["clearance_risk"])
    pi5.metric("📈 Sell-Through", f"{selected_product['sell_through_rate']:.1f}%")

    elast = elasticity_df[elasticity_df["product_id"] == selected_product["product_id"]]["elasticity"].mean()
    if np.isnan(elast):
        elast = -1.2

    st.divider()

    # ── Run Agents ─────────────────────────────────────────────────────────
    with st.spinner("🤖 Running multi-agent analysis..."):
        result = ai_system.run(selected_product, event_metrics, elasticity=float(elast))

    # ── Final Recommendation Banner ────────────────────────────────────────
    risk_level   = result["risk_level"]
    markdown_pct = result["recommended_markdown"]
    rev_uplift   = result["revenue_uplift_pct"]
    margin_imp   = result["margin_impact"]
    clear_prob   = result["clearance_probability"]
    strategy     = result["strategy"]
    confidence   = result["confidence"]

    new_price   = selected_product["price"] * (1 - markdown_pct / 100)
    cost_est    = selected_product["price"] * 0.55
    orig_margin = ((selected_product["price"] - cost_est) / selected_product["price"] * 100)
    new_margin  = ((new_price - cost_est) / new_price * 100) if new_price > 0 else 0

    st.markdown("### 🧠 Coordinator Agent — Final Recommendation")

    risk_bg = {
        "🔴 Critical": "rgba(239,68,68,0.15)",
        "🟠 High":     "rgba(249,115,22,0.15)",
        "🟡 Medium":   "rgba(245,158,11,0.15)",
        "🟢 Low":      "rgba(16,185,129,0.15)",
    }.get(risk_level, "rgba(99,102,241,0.15)")

    risk_border = {
        "🔴 Critical": "#ef4444",
        "🟠 High":     "#f97316",
        "🟡 Medium":   "#f59e0b",
        "🟢 Low":      "#10b981",
    }.get(risk_level, "#6366f1")

    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #1e1b4b, #312e81);
                border-radius: 16px; padding: 24px; margin: 12px 0;
                border: 1px solid #4f46e5;">
        <div style="display: grid; grid-template-columns: repeat(5, 1fr); gap: 16px; margin-bottom: 16px;">
            <div style="text-align:center; background:rgba(110,231,183,0.1);
                        border-radius:10px; padding:12px;">
                <div style="font-size:2rem; font-weight:800; color:#6ee7b7;">
                    {markdown_pct:.1f}%
                </div>
                <div style="color:#94a3b8; font-size:0.8rem; margin-top:4px;">
                    Recommended Markdown
                </div>
            </div>
            <div style="text-align:center; background:{risk_bg};
                        border:1px solid {risk_border}; border-radius:10px; padding:12px;">
                <div style="font-size:1.4rem; font-weight:800; color:white;">
                    {risk_level}
                </div>
                <div style="color:#94a3b8; font-size:0.8rem; margin-top:4px;">
                    Inventory Risk
                </div>
            </div>
            <div style="text-align:center; background:rgba(134,239,172,0.1);
                        border-radius:10px; padding:12px;">
                <div style="font-size:2rem; font-weight:800; color:#86efac;">
                    +{rev_uplift:.1f}%
                </div>
                <div style="color:#94a3b8; font-size:0.8rem; margin-top:4px;">
                    Est. Revenue Uplift
                </div>
            </div>
            <div style="text-align:center; background:rgba(252,165,165,0.1);
                        border-radius:10px; padding:12px;">
                <div style="font-size:2rem; font-weight:800; color:#fca5a5;">
                    {margin_imp:.1f}%
                </div>
                <div style="color:#94a3b8; font-size:0.8rem; margin-top:4px;">
                    Margin Impact
                </div>
            </div>
            <div style="text-align:center; background:rgba(147,197,253,0.1);
                        border-radius:10px; padding:12px;">
                <div style="font-size:2rem; font-weight:800; color:#93c5fd;">
                    {clear_prob:.0f}%
                </div>
                <div style="color:#94a3b8; font-size:0.8rem; margin-top:4px;">
                    Clearance Probability
                </div>
            </div>
        </div>
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px;">
            <div style="padding:12px; background:rgba(255,255,255,0.05); border-radius:8px;">
                <span style="color:#c7d2fe; font-size:0.85rem;">🎯 Strategy: </span>
                <span style="color:white; font-weight:600;">{strategy}</span>
            </div>
            <div style="padding:12px; background:rgba(255,255,255,0.05); border-radius:8px;">
                <span style="color:#c7d2fe; font-size:0.85rem;">🔒 Confidence: </span>
                <span style="color:white; font-weight:600;">{confidence:.0f}%</span>
                &nbsp;
                <span style="color:#64748b; font-size:0.8rem;">(avg across all 5 agents)</span>
            </div>
        </div>
        <div style="margin-top:12px; padding:12px; background:rgba(255,255,255,0.03);
                    border-radius:8px; border-left: 3px solid #6366f1;">
            <span style="color:#94a3b8; font-size:0.8rem;">
                📌 New Price after markdown:
                <span style="color:#a5b4fc; font-weight:700;">${new_price:.2f}</span>
                &nbsp;(from ${selected_product['price']:.2f})
                &nbsp;|&nbsp; Est. margin after discount:
                <span style="color:{'#10b981' if new_margin > 20 else '#ef4444'}; font-weight:700;">
                    {new_margin:.1f}%
                </span>
                &nbsp;(was {orig_margin:.1f}%)
            </span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    # ── Individual Agent Cards ─────────────────────────────────────────────
    st.markdown("### 🤖 Individual Agent Outputs")
    st.caption("Each agent analyzes the product from its own domain expertise and provides an independent recommendation.")

    agent_outputs = result["agent_outputs"]
    agent_list    = list(agent_outputs.values())

    agent_icons = {
        "Pricing Agent":            "💰",
        "Inventory Agent":          "📦",
        "Demand Forecasting Agent": "📈",
        "Promotion Agent":          "🎯",
        "Customer Behavior Agent":  "👥",
    }

    for i in range(0, len(agent_list), 2):
        cols = st.columns(2)
        for j, col in enumerate(cols):
            if i + j < len(agent_list):
                agent      = agent_list[i + j]
                conf       = agent.confidence
                conf_color = "#10b981" if conf > 0.8 else "#f59e0b" if conf > 0.65 else "#ef4444"
                conf_label = "High" if conf > 0.8 else "Medium" if conf > 0.65 else "Low"
                icon       = agent_icons.get(agent.agent_name, "🤖")

                with col:
                    st.markdown(f"""
                    <div style="background:rgba(30,27,75,0.6); border:1px solid #2d2d4e;
                                border-radius:12px; padding:16px; margin-bottom:12px;
                                border-left: 4px solid {conf_color};">
                        <div style="display:flex; align-items:center; gap:8px; margin-bottom:10px;">
                            <span style="font-size:1.2rem;">{icon}</span>
                            <span style="color:#a5b4fc; font-weight:700; font-size:1rem;">
                                {agent.agent_name}
                            </span>
                            <span style="margin-left:auto; background:{conf_color};
                                         color:white; font-size:0.7rem; font-weight:600;
                                         padding:2px 8px; border-radius:20px;">
                                {conf_label} Confidence ({conf*100:.0f}%)
                            </span>
                        </div>
                        <div style="background:rgba(255,255,255,0.05); border-radius:8px;
                                    padding:10px; margin-bottom:10px;">
                            <div style="color:#64748b; font-size:0.75rem; margin-bottom:4px;">
                                RECOMMENDATION
                            </div>
                            <div style="color:#e2e8f0; font-weight:600; font-size:0.9rem;">
                                {agent.recommendation}
                            </div>
                        </div>
                        <div style="color:#94a3b8; font-size:0.82rem; line-height:1.5;">
                            {agent.reasoning}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    if agent.data:
                        with st.expander(f"📊 {agent.agent_name} — Raw Data", expanded=False):
                            st.json(agent.data)

    st.divider()

    # ── Coordinator Full Reasoning ─────────────────────────────────────────
    st.markdown("### 📝 Coordinator Agent — Full Reasoning")
    st.caption("The coordinator synthesizes all 5 agent outputs and explains the final decision.")

    reasoning_text = result["reasoning"]
    st.markdown(f"""
    <div style="background:rgba(15,15,26,0.8); border:1px solid #2d2d4e;
                border-radius:12px; padding:20px; color:#cbd5e1;
                font-size:0.88rem; line-height:1.7;">
        {reasoning_text.replace(chr(10), '<br>')}
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    # ── Agent Confidence Radar ─────────────────────────────────────────────
    st.markdown("### 📡 Agent Confidence Radar")
    st.caption("Higher confidence = agent has stronger signal for this product. A full balanced polygon = strong multi-agent consensus.")

    agent_names       = [a.agent_name.replace(" Agent", "") for a in agent_list]
    confidence_values = [round(a.confidence * 100, 1) for a in agent_list]
    confidence_closed = confidence_values + [confidence_values[0]]
    names_closed      = agent_names + [agent_names[0]]

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=confidence_closed,
        theta=names_closed,
        fill="toself",
        name="Confidence",
        line_color="#6366f1",
        fillcolor="rgba(99,102,241,0.25)",
        text=[f"{v}%" for v in confidence_closed],
        textposition="top center",
        mode="lines+markers+text",
        marker=dict(size=8, color="#a5b4fc")
    ))
    fig.update_layout(
        polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                tickfont=dict(color="#64748b"),
                gridcolor="rgba(255,255,255,0.1)"
            ),
            angularaxis=dict(
                tickfont=dict(color="#e2e8f0", size=12),
                gridcolor="rgba(255,255,255,0.1)"
            )
        ),
        height=400,
        margin=dict(l=60, r=60, t=40, b=40),
        paper_bgcolor="rgba(0,0,0,0)",
        showlegend=False
    )
    st.plotly_chart(fig, use_container_width=True)

    avg_conf  = np.mean(confidence_values)
    min_agent = agent_names[confidence_values.index(min(confidence_values))]
    max_agent = agent_names[confidence_values.index(max(confidence_values))]
    st.caption(
        f"Average confidence: {avg_conf:.1f}%  |  "
        f"Strongest signal: {max_agent} ({max(confidence_values):.0f}%)  |  "
        f"Weakest signal: {min_agent} ({min(confidence_values):.0f}%)"
    )

    st.divider()

    # ── Human-in-the-Loop Approval ─────────────────────────────────────────
    st.markdown("### ✅ Human-in-the-Loop Approval")
    st.caption("Review the AI recommendation and take action. You can approve, override with your own value, or reject and escalate.")

    st.markdown(f"""
    <div style="background:rgba(99,102,241,0.08); border:1px solid #4f46e5;
                border-radius:10px; padding:14px; margin-bottom:16px;">
        <span style="color:#94a3b8;">Product: </span>
        <span style="color:#e2e8f0; font-weight:600;">{selected_name}</span>
        &nbsp;&nbsp;|&nbsp;&nbsp;
        <span style="color:#94a3b8;">AI Recommends: </span>
        <span style="color:#6ee7b7; font-weight:700;">{markdown_pct:.1f}% markdown</span>
        &nbsp;&nbsp;|&nbsp;&nbsp;
        <span style="color:#94a3b8;">New Price: </span>
        <span style="color:#a5b4fc; font-weight:700;">${new_price:.2f}</span>
        &nbsp;&nbsp;|&nbsp;&nbsp;
        <span style="color:#94a3b8;">Strategy: </span>
        <span style="color:#e2e8f0; font-weight:600;">{strategy}</span>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("**✅ Approve**")
        st.caption("Accept the AI recommendation as-is and schedule the markdown.")
        if st.button("✅ Approve Recommendation", type="primary", use_container_width=True):
            st.success(
                f"✅ Approved! **{markdown_pct:.1f}% markdown** scheduled for "
                f"**{selected_name}**.  \n"
                f"New price: **${new_price:.2f}**  \n"
                f"Strategy: **{strategy}**"
            )

    with col2:
        st.markdown("**✏️ Override**")
        st.caption("Set your own markdown % instead of the AI recommendation.")
        override_val = st.number_input(
            "Custom markdown %",
            min_value=0.0, max_value=80.0,
            value=float(round(markdown_pct, 1)),
            step=0.5,
            label_visibility="collapsed"
        )
        override_price = selected_product["price"] * (1 - override_val / 100)
        st.caption(f"Override new price: **${override_price:.2f}**")
        if st.button("✏️ Apply Override", use_container_width=True):
            st.info(
                f"✏️ Override applied: **{override_val:.1f}% markdown** for "
                f"**{selected_name}**.  \n"
                f"New price: **${override_price:.2f}**"
            )

    with col3:
        st.markdown("**❌ Reject**")
        st.caption("Reject this recommendation and escalate to the pricing team for manual review.")
        reject_reason = st.selectbox(
            "Reason",
            ["Select reason", "Margin too low", "Wrong strategy", "Needs more data", "Manual pricing preferred"],
            label_visibility="collapsed"
        )
        if st.button("❌ Reject & Escalate", use_container_width=True):
            if reject_reason == "Select reason":
                st.warning("Please select a rejection reason first.")
            else:
                st.error(
                    f"❌ Rejected — Reason: **{reject_reason}**  \n"
                    f"Escalated to pricing team for **{selected_name}**."
                )