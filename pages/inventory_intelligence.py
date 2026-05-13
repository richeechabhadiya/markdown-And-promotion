import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from utils.data_loader import compute_sales_metrics

def render():
    st.markdown("## 📦 Inventory Intelligence Dashboard")
    st.markdown("Overstock alerts, dead inventory detection, sell-through analysis, and actionable inventory insights.")

    metrics = compute_sales_metrics()

    # ── Summary KPIs ───────────────────────────────────────────────────────
    total_stock      = metrics["quantity"].sum()
    dead_count       = metrics["is_dead_inventory"].sum()
    high_risk        = (metrics["clearance_risk"] == "HIGH").sum()
    out_of_stock     = (metrics["quantity"] == 0).sum()
    avg_days_stock   = metrics[metrics["days_of_stock"] < 9999]["days_of_stock"].median()
    total_products   = len(metrics)
    avg_sell_through = metrics["sell_through_rate"].mean()
    zero_sales       = (metrics["total_qty_sold"] == 0).sum()

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("📦 Total Stock Units",   f"{total_stock:,.0f}")
    c2.metric("💀 Dead Inventory",      f"{dead_count}",     ">180 days stock")
    c3.metric("🔴 High Risk Items",     f"{high_risk}",      "Needs action")
    c4.metric("🚫 Out of Stock",        f"{out_of_stock}")
    c5.metric("📅 Median Days Stock",   f"{avg_days_stock:.0f} days")

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("🛒 Total Products",      f"{total_products:,}")
    c2.metric("📊 Avg Sell-Through",    f"{avg_sell_through:.1f}%")
    c3.metric("⚠️ Zero Sales Products", f"{zero_sales}",     "Never sold")
    c4.metric("🟡 Medium Risk",         f"{(metrics['clearance_risk']=='MEDIUM').sum()}")
    c5.metric("🟢 Healthy Stock",       f"{(metrics['clearance_risk']=='LOW').sum()}")

    st.divider()

    # ── Row 1: Sell-Through by Category + Days of Stock ───────────────────
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 📊 Sell-Through Rate by Category")
        st.caption("How much of available stock has been sold per category. Higher % = healthier inventory.")

        cat_st = metrics[metrics["main_category"].notna()].groupby("main_category").agg(
            avg_sell_through=("sell_through_rate", "mean"),
            product_count=("product_id", "count")
        ).reset_index().sort_values("avg_sell_through", ascending=True)

        # Color by sell-through level
        cat_st["color"] = cat_st["avg_sell_through"].apply(
            lambda x: "#ef4444" if x < 30 else ("#f59e0b" if x < 60 else "#10b981")
        )

        fig = px.bar(
            cat_st, x="avg_sell_through", y="main_category",
            orientation="h",
            color="avg_sell_through",
            color_continuous_scale=["#ef4444", "#f59e0b", "#10b981"],
            range_color=[0, 100],
            text="avg_sell_through",
            labels={"avg_sell_through": "Avg Sell-Through (%)", "main_category": "Category"}
        )
        fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
        fig.add_vline(x=50, line_dash="dash", line_color="white",
                      annotation_text="50% target", annotation_font_color="gray")
        fig.update_layout(
            height=360, margin=dict(l=0, r=60, t=20, b=0),
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            coloraxis_showscale=False, xaxis=dict(range=[0, 115])
        )
        st.plotly_chart(fig, use_container_width=True)
        st.caption("🟢 >60% = Healthy  |  🟡 30–60% = Monitor  |  🔴 <30% = Needs markdown")

    with col2:
        st.markdown("### ⏳ Days of Stock Distribution")
        st.caption("Stock health overview — how long current inventory will last at current sales rate.")

        valid_days = metrics[
            (metrics["days_of_stock"] < 9999) &
            (metrics["days_of_stock"] > 0)
        ]["days_of_stock"]

        zones = pd.DataFrame({
            "Zone":  ["🟢 Healthy\n<30 days", "🟡 Monitor\n30–90 days",
                      "🟠 At Risk\n90–180 days", "🔴 Dead Stock\n>180 days"],
            "Count": [
                int((valid_days < 30).sum()),
                int(((valid_days >= 30)  & (valid_days < 90)).sum()),
                int(((valid_days >= 90)  & (valid_days < 180)).sum()),
                int((valid_days >= 180).sum()),
            ],
            "Color": ["#10b981", "#f59e0b", "#f97316", "#ef4444"]
        })
        zones["Pct"] = (zones["Count"] / zones["Count"].sum() * 100).round(1)

        fig = go.Figure()
        for _, row in zones.iterrows():
            fig.add_trace(go.Bar(
                x=[row["Zone"]],
                y=[row["Pct"]],          # ← use % not raw count
                text=f"{row['Count']} products<br>({row['Pct']}%)",
                textposition="outside",
                marker_color=row["Color"],
                name=row["Zone"],
                hovertemplate=f"{row['Zone']}<br>Products: {row['Count']}<br>Share: {row['Pct']}%<extra></extra>"
            ))

        fig.update_layout(
            height=360,
            margin=dict(l=0, r=0, t=40, b=0),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            showlegend=False,
            yaxis=dict(
                title="% of Products",
                range=[0, 110],
                gridcolor="rgba(255,255,255,0.05)"
            ),
            xaxis=dict(title=""),
            bargap=0.3
        )
        st.plotly_chart(fig, use_container_width=True)

        # Clear insight below
        dead_pct = zones[zones["Zone"].str.contains("Dead")]["Pct"].values[0]
        healthy_pct = zones[zones["Zone"].str.contains("Healthy")]["Pct"].values[0]
        st.caption(
            f"🔴 {dead_pct}% of products have >180 days stock — serious overstock situation.  "
            f"Only {healthy_pct}% are in healthy range."
        )

        # Mini insight box
        st.markdown(f"""
        <div style="background:rgba(239,68,68,0.1); border:1px solid #ef4444;
                    border-radius:8px; padding:10px; margin-top:8px;">
            <div style="color:#ef4444; font-weight:600; font-size:0.85rem;">
                ⚠️ Key Insight
            </div>
            <div style="color:#cbd5e1; font-size:0.8rem; margin-top:4px;">
                <b>{zones.iloc[3]['Count']} products</b> have more than 180 days of stock.
                At current sales velocity, these products will take
                <b>6+ months</b> to clear without markdown intervention.
            </div>
        </div>
        """, unsafe_allow_html=True)
    with col1:
        st.markdown("### 🫧 Stock vs Sales Velocity (Action Matrix)")
        st.caption("X = how fast selling | Y = stock left | Color = risk level")

        bubble_df = metrics[
            (metrics["quantity"] > 0) &
            (metrics["sales_velocity"] >= 0) &
            (metrics["main_category"].notna())
        ].copy()

        # Separate HIGH risk for emphasis
        high_risk_df   = bubble_df[bubble_df["clearance_risk"] == "HIGH"].head(100)
        medium_risk_df = bubble_df[bubble_df["clearance_risk"] == "MEDIUM"].head(80)
        low_risk_df    = bubble_df[bubble_df["clearance_risk"] == "LOW"].head(60)
        bubble_df      = pd.concat([low_risk_df, medium_risk_df, high_risk_df])

        fig = go.Figure()

        for risk, color, label in [
            ("LOW",    "#10b981", "🟢 LOW Risk"),
            ("MEDIUM", "#f59e0b", "🟡 MEDIUM Risk"),
            ("HIGH",   "#ef4444", "🔴 HIGH Risk — Markdown Needed"),
        ]:
            df_ = bubble_df[bubble_df["clearance_risk"] == risk]
            if df_.empty:
                continue
            fig.add_trace(go.Scatter(
                x=df_["sales_velocity"],
                y=df_["quantity"],
                mode="markers",
                name=label,
                marker=dict(
                    color=color,
                    size=df_["quantity"].clip(upper=500) / 15 + 6,
                    opacity=0.75,
                    line=dict(width=0.5, color="white")
                ),
                hovertemplate=(
                    "<b>%{customdata[0]}</b><br>"
                    "Category: %{customdata[1]}<br>"
                    "Stock: %{y} units<br>"
                    "Velocity: %{x:.3f} units/day<br>"
                    "Sell-Through: %{customdata[2]:.1f}%<br>"
                    "Days of Stock: %{customdata[3]:.0f}<br>"
                    "<extra></extra>"
                ),
                customdata=df_[["product_name", "main_category", "sell_through_rate", "days_of_stock"]].values
            ))

        # Quadrant dividers
        fig.add_vline(x=0.1, line_dash="dash", line_color="rgba(255,255,255,0.25)")
        fig.add_hline(y=100, line_dash="dash", line_color="rgba(255,255,255,0.25)")

        # Clean quadrant labels (no overlap)
        fig.add_annotation(x=0.45, y=bubble_df["quantity"].max()*0.95,
                           text="⭐ Fast + High Stock", showarrow=False,
                           font=dict(color="#10b981", size=10),
                           bgcolor="rgba(0,0,0,0.4)")
        fig.add_annotation(x=0.45, y=10,
                           text="✅ Fast + Low Stock", showarrow=False,
                           font=dict(color="#10b981", size=10),
                           bgcolor="rgba(0,0,0,0.4)")
        fig.add_annotation(x=0.01, y=bubble_df["quantity"].max()*0.95,
                           text="🔴 Slow + High Stock\n→ Markdown Now", showarrow=False,
                           font=dict(color="#ef4444", size=10),
                           bgcolor="rgba(0,0,0,0.4)",
                           xanchor="left")
        fig.add_annotation(x=0.01, y=10,
                           text="🟡 Slow + Low Stock\n→ Monitor", showarrow=False,
                           font=dict(color="#f59e0b", size=10),
                           bgcolor="rgba(0,0,0,0.4)",
                           xanchor="left")

        fig.update_layout(
            height=380,
            margin=dict(l=0, r=0, t=20, b=0),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(
                range=[0, 0.5],
                title="Sales Velocity (units/day)",
                gridcolor="rgba(255,255,255,0.05)"
            ),
            yaxis=dict(
                title="Stock Remaining (units)",
                gridcolor="rgba(255,255,255,0.05)"
            ),
            legend=dict(
                title="Risk Level",
                font=dict(color="white"),
                bgcolor="rgba(0,0,0,0.3)"
            )
        )
        st.plotly_chart(fig, use_container_width=True)

        # Summary below chart
        high_count = int((bubble_df["clearance_risk"] == "HIGH").sum())
        med_count  = int((bubble_df["clearance_risk"] == "MEDIUM").sum())
        st.caption(
            f"🔴 {high_count} HIGH risk products shown (high stock + barely selling)  |  "
            f"🟡 {med_count} MEDIUM risk  |  "
            f"Hover over any bubble for product details"
        )

    # ── Row 3: Inventory Value at Risk ────────────────────────────────────
    st.markdown("### 💰 Inventory Value at Risk by Category")
    st.caption(
        "Stock Value = quantity × price. "
        "This shows how much money is tied up in HIGH risk (slow-moving) inventory per category."
    )

    metrics["stock_value"] = metrics["quantity"] * metrics["price"]

    value_at_risk = metrics[
        metrics["clearance_risk"] == "HIGH"
    ].groupby("main_category").agg(
        stock_value=("stock_value", "sum"),
        product_count=("product_id", "count"),
        avg_days_stock=("days_of_stock", "mean")
    ).reset_index().sort_values("stock_value", ascending=False).head(10)

    value_at_risk["avg_days_stock"] = value_at_risk["avg_days_stock"].clip(upper=9999).round(0)

    fig = px.bar(
        value_at_risk,
        x="main_category", y="stock_value",
        color="stock_value",
        color_continuous_scale=["#f59e0b", "#ef4444"],
        text="stock_value",
        hover_data=["product_count", "avg_days_stock"],
        labels={
            "stock_value":    "Stock Value at Risk ($)",
            "main_category":  "Category",
            "product_count":  "Products at Risk",
            "avg_days_stock": "Avg Days of Stock"
        }
    )
    fig.update_traces(texttemplate="$%{text:,.0f}", textposition="outside")
    fig.update_layout(
        height=360, margin=dict(l=0, r=0, t=40, b=0),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        coloraxis_showscale=False,
        xaxis_tickangle=-30
    )
    st.plotly_chart(fig, use_container_width=True)
    st.caption(
        f"💸 Total stock value tied up in HIGH risk products: "
        f"${value_at_risk['stock_value'].sum():,.0f}"
    )

    st.divider()

    # ── Tabbed Detail Tables ───────────────────────────────────────────────
    tabs = st.tabs(["🔴 Dead Inventory", "🟠 High Risk", "🏆 Class A Products", "All Products"])

    with tabs[0]:
        st.caption("Products with >180 days of stock at current sales velocity — these need immediate clearance action.")
        dead = metrics[metrics["is_dead_inventory"]].nlargest(50, "quantity")[[
            "product_name", "main_category", "quantity", "sales_velocity",
            "days_of_stock", "total_revenue", "price", "abc_class"
        ]].copy()
        dead["stock_value"]    = (dead["quantity"] * dead["price"]).map("${:,.2f}".format)
        dead["days_of_stock"]  = dead["days_of_stock"].clip(upper=9999).map("{:.0f}".format)
        dead["sales_velocity"] = dead["sales_velocity"].map("{:.4f}".format)
        dead["total_revenue"]  = dead["total_revenue"].map("${:,.2f}".format)
        dead["price"]          = dead["price"].map("${:,.2f}".format)
        dead.columns = ["Product", "Category", "Stock", "Velocity", "Days Stock", "Revenue", "Price", "ABC", "Stock Value"]
        st.dataframe(dead, use_container_width=True, hide_index=True)

    with tabs[1]:
        st.caption("Products with HIGH clearance risk — high stock + very low sales velocity. Priority markdown candidates.")
        high = metrics[metrics["clearance_risk"] == "HIGH"].nlargest(50, "quantity")[[
            "product_name", "main_category", "quantity", "sales_velocity",
            "days_of_stock", "sell_through_rate", "price", "abc_class"
        ]].copy()
        high["stock_value"]      = (high["quantity"] * high["price"]).map("${:,.2f}".format)
        high["sales_velocity"]   = high["sales_velocity"].map("{:.4f}".format)
        high["days_of_stock"]    = high["days_of_stock"].clip(upper=9999).map("{:.0f}".format)
        high["sell_through_rate"] = high["sell_through_rate"].map("{:.1f}%".format)
        high["price"]            = high["price"].map("${:,.2f}".format)
        high.columns = ["Product", "Category", "Stock", "Velocity", "Days Stock", "Sell-Through", "Price", "ABC", "Stock Value"]
        st.dataframe(high, use_container_width=True, hide_index=True)

    with tabs[2]:
        st.caption("Top revenue-generating products (Class A). Handle with care — protect margins, avoid deep markdowns.")
        class_a = metrics[metrics["abc_class"] == "A"].nlargest(50, "total_revenue")[[
            "product_name", "main_category", "total_revenue", "total_qty_sold",
            "sell_through_rate", "quantity", "price", "clearance_risk"
        ]].copy()
        class_a["total_revenue"]    = class_a["total_revenue"].map("${:,.2f}".format)
        class_a["sell_through_rate"] = class_a["sell_through_rate"].map("{:.1f}%".format)
        class_a["price"]            = class_a["price"].map("${:,.2f}".format)
        class_a.columns = ["Product", "Category", "Revenue", "Qty Sold", "Sell-Through", "Stock", "Price", "Risk"]
        st.dataframe(class_a, use_container_width=True, hide_index=True)

    with tabs[3]:
        st.caption("Full product inventory list with all key metrics.")
        all_df = metrics[[
            "product_name", "main_category", "quantity", "total_qty_sold",
            "sales_velocity", "sell_through_rate", "abc_class",
            "clearance_risk", "days_of_stock", "is_dead_inventory"
        ]].copy()
        all_df["sales_velocity"]    = all_df["sales_velocity"].map("{:.4f}".format)
        all_df["sell_through_rate"] = all_df["sell_through_rate"].map("{:.1f}%".format)
        all_df["days_of_stock"]     = all_df["days_of_stock"].clip(upper=9999).map("{:.0f}".format)
        all_df.columns = [
            "Product", "Category", "Stock", "Sold", "Velocity",
            "Sell-Through", "ABC", "Risk", "Days Stock", "Dead?"
        ]
        st.dataframe(all_df, use_container_width=True, hide_index=True)