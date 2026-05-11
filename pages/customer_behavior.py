import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from utils.data_loader import load_bq_events, compute_event_metrics, load_orders

def render():
    st.markdown("## 👥 Customer Behavior Dashboard")
    st.markdown("Cart abandonment analysis, conversion funnel, and customer engagement analytics.")

    event_metrics = compute_event_metrics()
    events = load_bq_events()
    orders = load_orders()

    cart_rate = event_metrics["cart_abandonment_rate"]
    total_events = event_metrics["total_events"]
    unique_sessions = event_metrics["unique_sessions"]
    unique_users = event_metrics["unique_users"]
    cart_sessions = event_metrics["cart_sessions"]
    purchase_sessions = event_metrics["purchase_sessions"]

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("📊 Total Events", f"{total_events:,}")
    c2.metric("👤 Unique Users", f"{unique_users:,}")
    c3.metric("🔗 Sessions", f"{unique_sessions:,}")
    c4.metric("🛒 Cart Sessions", f"{cart_sessions:,}")
    c5.metric("🚪 Cart Abandonment", f"{cart_rate:.1f}%", "↓ Lower is better")

    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 🔽 Conversion Funnel")
        event_counts = event_metrics["event_counts"]
        funnel_events = ["session_start", "view_item", "add_to_cart", "begin_checkout", "purchase"]
        funnel_data = []
        for e in funnel_events:
            cnt = event_counts[event_counts["event_name"] == e]["count"].sum()
            funnel_data.append({"Stage": e.replace("_", " ").title(), "Count": cnt})
        funnel_df = pd.DataFrame(funnel_data)
        fig = go.Figure(go.Funnel(
            y=funnel_df["Stage"], x=funnel_df["Count"],
            textinfo="value+percent initial",
            marker=dict(color=["#6366f1", "#8b5cf6", "#ec4899", "#f59e0b", "#10b981"])
        ))
        fig.update_layout(height=340, margin=dict(l=0,r=0,t=20,b=0),
                          paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("### 📱 Event Distribution")
        top_events = event_counts.head(10)
        fig = px.bar(top_events, x="count", y="event_name", orientation="h",
                     color_discrete_sequence=["#6366f1"],
                     labels={"count": "Event Count", "event_name": "Event"})
        fig.update_layout(height=340, margin=dict(l=0,r=0,t=20,b=0),
                          plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # Daily event trend
    st.markdown("### 📅 Daily Event Trend")
    daily = event_metrics["daily_events"]
    key_events = ["view_item", "add_to_cart", "purchase", "remove_from_cart"]
    daily_filtered = daily[daily["event_name"].isin(key_events)]
    fig = px.line(daily_filtered, x="event_date", y="count", color="event_name",
                  color_discrete_sequence=["#6366f1", "#10b981", "#f59e0b", "#ef4444"],
                  labels={"count": "Events", "event_date": "Date", "event_name": "Event"})
    fig.update_layout(height=320, margin=dict(l=0,r=0,t=20,b=0),
                      plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, use_container_width=True)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 👁️ Top Viewed Products")
        top_viewed = event_metrics["top_items_viewed"]
        if not top_viewed.empty:
            fig = px.bar(top_viewed, x="views", y="item_name", orientation="h",
                         color_discrete_sequence=["#8b5cf6"])
            fig.update_layout(height=320, margin=dict(l=0,r=0,t=20,b=0),
                              plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("### 🛒 Most Added to Cart")
        top_carted = event_metrics["top_items_carted"]
        if not top_carted.empty:
            fig = px.bar(top_carted, x="add_to_cart", y="item_name", orientation="h",
                         color_discrete_sequence=["#10b981"])
            fig.update_layout(height=320, margin=dict(l=0,r=0,t=20,b=0),
                              plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True)

    # Device & Geography
    st.divider()
    st.markdown("### 🌍 User Geography (from Events)")
    try:
        import json
        geo_data = events["geo"].dropna().head(5000)
        geo_parsed = geo_data.apply(lambda x: json.loads(x) if isinstance(x, str) else {})
        countries = geo_parsed.apply(lambda x: x.get("country", "Unknown"))
        country_counts = countries.value_counts().head(15).reset_index()
        country_counts.columns = ["Country", "Sessions"]
        fig = px.bar(country_counts, x="Sessions", y="Country", orientation="h",
                     color_discrete_sequence=["#6366f1"])
        fig.update_layout(height=380, margin=dict(l=0,r=0,t=20,b=0),
                          plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)
    except Exception:
        st.info("Geo data parsing unavailable.")

    # Platform breakdown
    platform_counts = events["platform"].value_counts().reset_index()
    platform_counts.columns = ["Platform", "Count"]
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 💻 Platform Split")
        fig = px.pie(platform_counts, values="Count", names="Platform", hole=0.5,
                     color_discrete_sequence=["#6366f1", "#10b981", "#f59e0b"])
        fig.update_layout(height=280, margin=dict(l=0,r=0,t=20,b=0), paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        st.markdown("### 📊 Customer Segments")
        completed_orders = load_orders()[load_orders()["state"] == "complete"].copy()
        guest_orders = completed_orders["customer_is_guest"].sum()
        reg_orders = len(completed_orders) - guest_orders
        seg_df = pd.DataFrame({"Segment": ["Registered", "Guest"], "Orders": [reg_orders, guest_orders]})
        fig = px.pie(seg_df, values="Orders", names="Segment", hole=0.5,
                     color_discrete_sequence=["#10b981", "#f59e0b"])
        fig.update_layout(height=280, margin=dict(l=0,r=0,t=20,b=0), paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)
