import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from utils.data_loader import load_bq_events, compute_event_metrics, load_orders, load_order_items, compute_sales_metrics
from utils.data_loader import ..., safe_dataframe

def render():
    st.markdown("## 👥 Customer Behavior Dashboard")
    st.markdown("Cart abandonment, conversion funnel, price sensitivity signals, and customer engagement analytics.")

    event_metrics     = compute_event_metrics()
    events            = load_bq_events()
    orders            = load_orders()
    order_items       = load_order_items()
    metrics           = compute_sales_metrics()

    completed_orders  = orders[orders["state"] == "complete"]

    cart_rate         = event_metrics["cart_abandonment_rate"]
    total_events      = event_metrics["total_events"]
    unique_sessions   = event_metrics["unique_sessions"]
    unique_users      = event_metrics["unique_users"]
    cart_sessions     = event_metrics["cart_sessions"]
    purchase_sessions = event_metrics["purchase_sessions"]

    # ── KPI Row ────────────────────────────────────────────────────────────
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("📊 Total Events",     f"{total_events:,}")
    c2.metric("👤 Unique Users",     f"{unique_users:,}")
    c3.metric("🔗 Sessions",         f"{unique_sessions:,}")
    c4.metric("🛒 Cart Sessions",    f"{cart_sessions:,}")
    c5.metric("🚪 Cart Abandonment", f"{cart_rate:.1f}%", "↓ Lower is better")

    if cart_rate > 70:
        st.error(f"⚠️ Cart abandonment is {cart_rate:.1f}% — very high price sensitivity. Strong signal to apply markdowns.")
    elif cart_rate > 50:
        st.warning(f"🟡 Cart abandonment is {cart_rate:.1f}% — moderate. Targeted discounts may improve conversion.")
    else:
        st.success(f"✅ Cart abandonment is {cart_rate:.1f}% — healthy conversion rate.")

    st.divider()

    # ── Row 1: Funnel + View vs Purchase ──────────────────────────────────
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 🔽 Conversion Funnel")
        st.caption("Where customers drop off — each stage loss is a markdown/pricing opportunity.")

        event_counts  = event_metrics["event_counts"]
        funnel_events = ["session_start", "view_item", "add_to_cart", "begin_checkout", "purchase"]
        funnel_data   = []
        for e in funnel_events:
            cnt = event_counts[event_counts["event_name"] == e]["count"].sum()
            funnel_data.append({"Stage": e.replace("_", " ").title(), "Count": int(cnt)})
        funnel_df = pd.DataFrame(funnel_data)

        funnel_df["Drop"] = 0.0
        for i in range(1, len(funnel_df)):
            prev = funnel_df.loc[i - 1, "Count"]
            curr = funnel_df.loc[i, "Count"]
            if prev > 0:
                funnel_df.loc[i, "Drop"] = round((1 - curr / prev) * 100, 1)

        fig = go.Figure(go.Funnel(
            y=funnel_df["Stage"],
            x=funnel_df["Count"],
            textinfo="value+percent initial",
            marker=dict(color=["#6366f1", "#8b5cf6", "#ec4899", "#f59e0b", "#10b981"])
        ))
        fig.update_layout(
            height=360, margin=dict(l=0, r=0, t=20, b=0),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)"
        )
        st.plotly_chart(fig, use_container_width=True)

        st.caption("Stage-by-stage drop-off:")
        for i in range(1, len(funnel_df)):
            drop  = funnel_df.loc[i, "Drop"]
            color = "🔴" if drop > 60 else "🟡" if drop > 30 else "🟢"
            st.caption(f"{color} {funnel_df.loc[i-1,'Stage']} → {funnel_df.loc[i,'Stage']}: **{drop}% drop-off**")

    with col2:
        st.markdown("### 👁️ Viewed but NOT Purchased (Price Sensitivity Signal)")
        st.caption("Products frequently viewed but rarely bought — likely price is too high. Top markdown candidates.")

        top_viewed = event_metrics["top_items_viewed"].copy()

        purchased_items = order_items[
            order_items["order_state"] == "complete"
        ]["item_name"].value_counts().reset_index()
        purchased_items.columns = ["item_name", "purchases"]

        if not top_viewed.empty:
            view_vs_buy = top_viewed.merge(purchased_items, on="item_name", how="left")
            view_vs_buy["purchases"]  = view_vs_buy["purchases"].fillna(0).astype(int)
            view_vs_buy["conversion"] = (view_vs_buy["purchases"] / (view_vs_buy["views"] + 1) * 100).round(1)
            view_vs_buy = view_vs_buy.sort_values("views", ascending=True).tail(10)

            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=view_vs_buy["views"],
                y=view_vs_buy["item_name"],
                orientation="h", name="Views",
                marker_color="#6366f1",
                text=view_vs_buy["views"],
                textposition="outside"
            ))
            fig.add_trace(go.Bar(
                x=view_vs_buy["purchases"],
                y=view_vs_buy["item_name"],
                orientation="h", name="Purchases",
                marker_color="#10b981",
                text=view_vs_buy["purchases"],
                textposition="outside"
            ))
            fig.update_layout(
                barmode="overlay", height=360,
                margin=dict(l=0, r=60, t=20, b=0),
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                legend=dict(font=dict(color="white")),
                xaxis=dict(title="Count")
            )
            st.plotly_chart(fig, use_container_width=True)
            st.caption("🟣 Purple bar much longer than green = high views, low purchases = price too high → markdown candidate")

    st.divider()

    # ── Row 2: Daily Trend + Add vs Remove ────────────────────────────────
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 📅 Daily Event Trend")
        st.caption("Track view_item, add_to_cart, and purchase trends — spikes show price sensitivity moments.")

        daily          = event_metrics["daily_events"]
        key_events     = ["view_item", "add_to_cart", "purchase", "remove_from_cart"]
        daily_filtered = daily[daily["event_name"].isin(key_events)]

        fig = px.line(
            daily_filtered, x="event_date", y="count", color="event_name",
            color_discrete_map={
                "view_item":        "#6366f1",
                "add_to_cart":      "#10b981",
                "purchase":         "#f59e0b",
                "remove_from_cart": "#ef4444"
            },
            labels={"count": "Events", "event_date": "Date", "event_name": "Event"}
        )
        fig.update_layout(
            height=320, margin=dict(l=0, r=0, t=20, b=0),
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            legend=dict(font=dict(color="white"))
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("### 🛍️ Customer Purchase Journey Analysis")
        st.caption("Full event funnel with drop-off at each stage — shows where pricing friction occurs.")

        # Build a complete journey breakdown from all events with item data
        journey_events = ["view_item", "add_to_cart", "remove_from_cart", "begin_checkout", "purchase"]
        journey_counts = []
        for e in journey_events:
            cnt = int(events[events["event_name"] == e]["item_name"].notna().sum())
            journey_counts.append({"Event": e.replace("_", " ").title(), "Count": cnt, "raw": e})

        journey_df = pd.DataFrame(journey_counts)

        # Color each stage
        color_map = {
            "view_item":        "#6366f1",
            "add_to_cart":      "#10b981",
            "remove_from_cart": "#ef4444",
            "begin_checkout":   "#f59e0b",
            "purchase":         "#06b6d4",
        }
        journey_df["color"] = journey_df["raw"].map(color_map)

        # Conversion rates between stages
        view_cnt     = journey_df[journey_df["raw"] == "view_item"]["Count"].values[0]
        add_cnt      = journey_df[journey_df["raw"] == "add_to_cart"]["Count"].values[0]
        remove_cnt   = journey_df[journey_df["raw"] == "remove_from_cart"]["Count"].values[0]
        checkout_cnt = journey_df[journey_df["raw"] == "begin_checkout"]["Count"].values[0]
        purchase_cnt = journey_df[journey_df["raw"] == "purchase"]["Count"].values[0]

        cart_to_remove   = round(remove_cnt / (add_cnt + 1) * 100, 1)
        view_to_add      = round(add_cnt / (view_cnt + 1) * 100, 1)
        add_to_checkout  = round(checkout_cnt / (add_cnt + 1) * 100, 1)
        checkout_to_buy  = round(purchase_cnt / (checkout_cnt + 1) * 100, 1)

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=journey_df["Count"],
            y=journey_df["Event"],
            orientation="h",
            marker_color=journey_df["color"].tolist(),
            text=journey_df["Count"].apply(lambda x: f"{x:,} events"),
            textposition="outside",
            showlegend=False
        ))
        fig.update_layout(
            height=300,
            margin=dict(l=0, r=100, t=20, b=0),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(title="Event Count")
        )
        st.plotly_chart(fig, use_container_width=True)

        # Conversion rate summary cards
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown(f"""
            <div style="background:rgba(99,102,241,0.15); border:1px solid #6366f1;
                        border-radius:8px; padding:10px; text-align:center;">
                <div style="color:#94a3b8; font-size:0.75rem;">View → Add to Cart</div>
                <div style="color:#a5b4fc; font-size:1.4rem; font-weight:700;">{view_to_add}%</div>
                <div style="color:#64748b; font-size:0.7rem;">
                    {'✅ Good' if view_to_add > 20 else '⚠️ Low — price deterring adds'}
                </div>
            </div>
            """, unsafe_allow_html=True)
            st.markdown(f"""
            <div style="background:rgba(239,68,68,0.1); border:1px solid #ef4444;
                        border-radius:8px; padding:10px; text-align:center; margin-top:8px;">
                <div style="color:#94a3b8; font-size:0.75rem;">Remove from Cart Rate</div>
                <div style="color:#fca5a5; font-size:1.4rem; font-weight:700;">{cart_to_remove}%</div>
                <div style="color:#64748b; font-size:0.7rem;">
                    {'🔴 High hesitation' if cart_to_remove > 20 else '✅ Normal'}
                </div>
            </div>
            """, unsafe_allow_html=True)
        with col_b:
            st.markdown(f"""
            <div style="background:rgba(245,158,11,0.1); border:1px solid #f59e0b;
                        border-radius:8px; padding:10px; text-align:center;">
                <div style="color:#94a3b8; font-size:0.75rem;">Add to Cart → Checkout</div>
                <div style="color:#fcd34d; font-size:1.4rem; font-weight:700;">{add_to_checkout}%</div>
                <div style="color:#64748b; font-size:0.7rem;">
                    {'✅ Good' if add_to_checkout > 30 else '⚠️ Abandoning at cart'}
                </div>
            </div>
            """, unsafe_allow_html=True)
            st.markdown(f"""
            <div style="background:rgba(6,182,212,0.1); border:1px solid #06b6d4;
                        border-radius:8px; padding:10px; text-align:center; margin-top:8px;">
                <div style="color:#94a3b8; font-size:0.75rem;">Checkout → Purchase</div>
                <div style="color:#67e8f9; font-size:1.4rem; font-weight:700;">{checkout_to_buy}%</div>
                <div style="color:#64748b; font-size:0.7rem;">
                    {'✅ Good' if checkout_to_buy > 50 else '⚠️ Dropping at payment'}
                </div>
            </div>
            """, unsafe_allow_html=True)

    st.divider()

    # ── Row 3: Customer Segments + Order Value Distribution ───────────────
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 👥 Customer Segments — Registered vs Guest")
        st.caption("Registered customers tend to be more loyal and less price-sensitive than guests.")

        guest_orders = int(completed_orders["customer_is_guest"].sum())
        reg_orders   = len(completed_orders) - guest_orders
        guest_aov    = completed_orders[completed_orders["customer_is_guest"] == 1]["grand_total"].mean()
        reg_aov      = completed_orders[completed_orders["customer_is_guest"] == 0]["grand_total"].mean()

        seg_df = pd.DataFrame({
            "Segment": ["Registered", "Guest"],
            "Orders":  [reg_orders, guest_orders]
        })
        fig = px.pie(
            seg_df, values="Orders", names="Segment", hole=0.5,
            color="Segment",
            color_discrete_map={"Registered": "#10b981", "Guest": "#f59e0b"}
        )
        fig.update_layout(
            height=280, margin=dict(l=0, r=0, t=20, b=0),
            paper_bgcolor="rgba(0,0,0,0)",
            legend=dict(font=dict(color="white"))
        )
        st.plotly_chart(fig, use_container_width=True)
        st.caption(
            f"🟢 Registered AOV: ${reg_aov:.2f}  |  "
            f"🟡 Guest AOV: ${guest_aov:.2f}  |  "
            f"{'Guests spend more — promotions attract guests' if guest_aov > reg_aov else 'Registered spend more — loyalty rewards beat blanket discounts'}"
        )

    with col2:
        st.markdown("### 💰 Order Value Distribution")
        st.caption("Understanding where most orders cluster helps set optimal markdown price points.")

        order_vals = completed_orders["grand_total"].clip(upper=500)
        median_val = completed_orders["grand_total"].median()
        mean_val   = completed_orders["grand_total"].mean()

        fig = px.histogram(
            order_vals, nbins=30,
            color_discrete_sequence=["#6366f1"],
            labels={"value": "Order Value ($)", "count": "# Orders"}
        )
        fig.add_vline(
            x=median_val, line_dash="dash", line_color="#10b981",
            annotation_text=f"Median: ${median_val:.0f}",
            annotation_font_color="#10b981"
        )
        fig.add_vline(
            x=mean_val, line_dash="dash", line_color="#f59e0b",
            annotation_text=f"Mean: ${mean_val:.0f}",
            annotation_font_color="#f59e0b"
        )
        fig.update_layout(
            height=280, margin=dict(l=0, r=0, t=20, b=0),
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)"
        )
        st.plotly_chart(fig, use_container_width=True)
        st.caption(
            f"Most orders cluster around ${median_val:.0f}. "
            f"Markdowns bringing products below ${median_val:.0f} will have highest conversion impact."
        )

    st.divider()

    # ── Row 4: Most Carted + Price Sensitivity Summary ────────────────────
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 🛒 Most Added to Cart")
        st.caption("High cart additions = strong interest. If sell-through is low, price may be blocking purchase.")

        top_carted = event_metrics["top_items_carted"]
        if not top_carted.empty:
            fig = px.bar(
                top_carted, x="add_to_cart", y="item_name",
                orientation="h",
                color_discrete_sequence=["#10b981"],
                text="add_to_cart",
                labels={"add_to_cart": "Times Added to Cart", "item_name": "Product"}
            )
            fig.update_traces(textposition="outside")
            fig.update_layout(
                height=320, margin=dict(l=0, r=60, t=20, b=0),
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)"
            )
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("### 📋 Price Sensitivity Summary for Markdown")
        st.caption("Key behavioral signals that inform markdown decisions.")

        view_cnt     = int(event_metrics["event_counts"][event_metrics["event_counts"]["event_name"] == "view_item"]["count"].sum())
        cart_cnt     = int(event_metrics["event_counts"][event_metrics["event_counts"]["event_name"] == "add_to_cart"]["count"].sum())
        purchase_cnt = int(event_metrics["event_counts"][event_metrics["event_counts"]["event_name"] == "purchase"]["count"].sum())
        remove_cnt   = int(event_metrics["event_counts"][event_metrics["event_counts"]["event_name"] == "remove_from_cart"]["count"].sum())

        view_to_cart     = round(cart_cnt     / (view_cnt + 1)  * 100, 1)
        cart_to_purchase = round(purchase_cnt / (cart_cnt + 1)  * 100, 1)
        remove_rate      = round(remove_cnt   / (cart_cnt + 1)  * 100, 1)

        st.markdown(f"""
        <div style="background:rgba(99,102,241,0.1); border:1px solid #4f46e5;
                    border-radius:12px; padding:16px; margin-top:8px;">
            <div style="color:#a5b4fc; font-weight:700; margin-bottom:12px;">
                🎯 Markdown Decision Signals
            </div>
            <div style="display:grid; gap:10px;">
                <div style="background:rgba(0,0,0,0.2); padding:10px; border-radius:8px;">
                    <span style="color:#94a3b8;">View to Cart Rate</span>
                    <span style="color:{'#10b981' if view_to_cart > 10 else '#ef4444'};
                          font-weight:700; float:right;">
                        {view_to_cart}% {'✅' if view_to_cart > 10 else '⚠️ Low — price may deter'}
                    </span>
                </div>
                <div style="background:rgba(0,0,0,0.2); padding:10px; border-radius:8px;">
                    <span style="color:#94a3b8;">Cart to Purchase Rate</span>
                    <span style="color:{'#10b981' if cart_to_purchase > 40 else '#ef4444'};
                          font-weight:700; float:right;">
                        {cart_to_purchase}% {'✅' if cart_to_purchase > 40 else '⚠️ High abandonment'}
                    </span>
                </div>
                <div style="background:rgba(0,0,0,0.2); padding:10px; border-radius:8px;">
                    <span style="color:#94a3b8;">Cart Abandonment Rate</span>
                    <span style="color:{'#ef4444' if cart_rate > 60 else '#f59e0b'};
                          font-weight:700; float:right;">
                        {cart_rate:.1f}% {'🔴 Urgent' if cart_rate > 60 else '🟡 Monitor'}
                    </span>
                </div>
                <div style="background:rgba(0,0,0,0.2); padding:10px; border-radius:8px;">
                    <span style="color:#94a3b8;">Remove from Cart Rate</span>
                    <span style="color:{'#ef4444' if remove_rate > 20 else '#10b981'};
                          font-weight:700; float:right;">
                        {remove_rate}% {'⚠️ High hesitation' if remove_rate > 20 else '✅ Normal'}
                    </span>
                </div>
                <div style="background:rgba(0,0,0,0.2); padding:10px; border-radius:8px;">
                    <span style="color:#94a3b8;">Registered vs Guest AOV</span>
                    <span style="color:#a5b4fc; font-weight:700; float:right;">
                        ${reg_aov:.0f} vs ${guest_aov:.0f}
                    </span>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)