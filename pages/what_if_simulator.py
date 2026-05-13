"""
what_if_simulator.py  — FIXED
==============================
Bugs fixed vs original:

BUG 1 ✅  cost_estimate was hardcoded as price * 0.55 for every product.
          Now uses actual cost_price from product_catalogue where available,
          falls back to price * 0.55 only when missing.

BUG 2 ✅  Demand multiplier formula was:
            1 + abs(elasticity) * (markdown_pct / 100)
          This is dimensionally wrong. Correct formula:
            price_change_pct = -markdown_pct / 100   (price fell)
            demand_change_pct = elasticity * price_change_pct  (negative × negative = positive)
            new_units = base_units * (1 + demand_change_pct)

BUG 3 ✅  Elasticity slider allowed -10 (unrealistic, distorts all outputs).
          Real retail range is -3.0 to -0.3. Clamped and default changed.

BUG 4 ✅  Sales velocity was units/day — for a 30-day horizon on a slow product
          this gave absurd numbers like 3 units. Now displayed as units/week
          in the UI card and used correctly in calculations.

BUG 5 ✅  Revenue change shown green even when margin was destroyed.
          Added combined health score and explicit margin warning.

BUG 6 ✅  No cost floor check — price could go below cost.
          Now enforces: new_price >= cost_estimate * 1.10 (10% above cost).

BUG 7 ✅  Optimal markdown finder in sweep analysis ignored cost floor
          and margin constraints. Fixed to skip invalid discount levels.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from utils.data_loader import compute_sales_metrics, compute_elasticity_data


# ── helpers ──────────────────────────────────────────────────────────────────

def correct_demand_uplift(elasticity: float, markdown_pct: float) -> float:
    """
    Correct elasticity-based demand formula.
    elasticity = % change in demand / % change in price
    When price falls by markdown_pct:
      price_change_pct = -markdown_pct / 100   (negative because price fell)
      demand_change_pct = elasticity × price_change_pct
        = (negative) × (negative) = positive   ← demand rises
    Returns demand_change as a fraction (e.g. 0.30 = +30% more units)
    """
    price_change_pct = -markdown_pct / 100      # e.g. -0.15 for 15% markdown
    demand_change    =  elasticity * price_change_pct  # e.g. (-1.5)*(-0.15) = +0.225
    return max(0.0, demand_change)              # can't be negative (price cut can't reduce demand)


def get_cost_price(product: pd.Series) -> float:
    """
    Returns cost price from actual data if the column exists,
    otherwise falls back to 55% of selling price (industry average).
    """
    # Try real cost_price column first
    if "cost_price" in product.index and product["cost_price"] > 0:
        return float(product["cost_price"])
    # Fallback: 55% of price
    return float(product["price"]) * 0.55


def health_badge(revenue_change_pct: float, margin_impact_pp: float) -> str:
    """Returns a coloured status string based on combined revenue+margin outcome."""
    if revenue_change_pct > 0 and margin_impact_pp > -5:
        return "🟢 Healthy — revenue up, margin acceptable"
    if revenue_change_pct > 0 and margin_impact_pp <= -10:
        return "🟡 Caution — revenue up but margin erosion is significant"
    if revenue_change_pct <= 0:
        return "🔴 Not recommended — revenue declines at this discount level"
    return "🟡 Monitor"


# ── main render ──────────────────────────────────────────────────────────────

def render():
    st.markdown("## 🔮 What-If Pricing Simulator")
    st.markdown(
        "Simulate different markdown percentages and predict the impact "
        "on sales, revenue, and margins using **price elasticity theory**."
    )

    metrics      = compute_sales_metrics()
    elasticity_df= compute_elasticity_data()

    # ── Product selector ──────────────────────────────────────────
    col1, col2 = st.columns([2, 1])
    with col1:
        product_options = (metrics[metrics["price"] > 0]["product_name"]
                           .dropna().head(300).tolist())
        selected_name = st.selectbox("🛍️ Select Product", product_options)
    with col2:
        category_options = ["All"] + sorted(metrics["main_category"].dropna().unique().tolist())
        st.selectbox("Browse by Category", category_options, key="sim_cat")

    product  = metrics[metrics["product_name"] == selected_name].iloc[0]
    pid      = product["product_id"]
    price    = float(product["price"])
    quantity = float(product["quantity"])

    # FIX 4: velocity is stored as units/day → convert to units/week for display
    velocity_day  = float(product["sales_velocity"])          # units per day (raw)
    velocity_week = round(velocity_day * 7, 2)                # units per week (display)

    abc_class      = product["abc_class"]
    clearance_risk = product["clearance_risk"]

    # FIX 1: use real cost price, not hardcoded 55%
    cost_price = get_cost_price(product)
    min_sell_price = cost_price * 1.10                        # cost floor

    # FIX 3: elasticity — use data, clamped to realistic range
    elast_raw = elasticity_df[elasticity_df["product_id"] == pid]["elasticity"].mean()
    elast_default = float(np.clip(elast_raw if not np.isnan(elast_raw) else -1.2, -3.0, -0.3))

    # ── Product info card ─────────────────────────────────────────
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("💰 Current Price",  f"${price:.2f}")
    col2.metric("💲 Cost Price",     f"${cost_price:.2f}")
    col3.metric("📦 Stock",          f"{quantity:.0f} units")
    col4.metric("🏷️ ABC Class",      abc_class)
    col5.metric("⚠️ Risk",           clearance_risk)

    # Current margin info
    curr_margin = ((price - cost_price) / price * 100) if price > 0 else 0
    st.caption(
        f"📊 Current margin: **{curr_margin:.1f}%** | "
        f"Sales velocity: **{velocity_week:.2f} units/week** | "
        f"Cost floor (min sell price): **${min_sell_price:.2f}**"
    )

    st.divider()

    # ── Simulator controls ────────────────────────────────────────
    st.markdown("### 🎛️ Simulator Controls")
    col1, col2, col3 = st.columns(3)
    with col1:
        markdown_pct = st.slider("Markdown Percentage (%)", 0, 70, 15, step=5)
    with col2:
        # FIX 3: realistic range -3.0 to -0.3 — not -10 to -0.1
        elasticity_override = st.slider(
            "Price Elasticity",
            min_value=-3.0, max_value=-0.3,
            value=elast_default,
            step=0.1,
            help=(
                "How sensitive demand is to price changes. "
                "-0.3 = inelastic (luxury/staple). "
                "-1.0 = unit elastic. "
                "-3.0 = very elastic (price-sensitive). "
                "Real retail range: -0.3 to -3.0."
            )
        )
    with col3:
        forecast_days = st.slider("Forecast Horizon (days)", 7, 180, 30)

    # ── Core calculations (FIXED) ─────────────────────────────────
    new_price = price * (1 - markdown_pct / 100)

    # FIX 6: enforce cost floor
    below_floor = new_price < min_sell_price
    if below_floor:
        st.error(
            f"⛔ **Price floor breach!** At {markdown_pct}% discount, "
            f"new price ${new_price:.2f} is below cost floor ${min_sell_price:.2f}. "
            f"Maximum allowed discount: **{((price - min_sell_price)/price*100):.0f}%**"
        )
        new_price = min_sell_price      # cap at floor for display

    # Margin calculations
    original_margin_pct = ((price     - cost_price) / price     * 100) if price > 0 else 0
    new_margin_pct      = ((new_price - cost_price) / new_price * 100) if new_price > 0 else 0
    margin_impact_pp    = new_margin_pct - original_margin_pct

    # FIX 2: correct demand uplift formula
    demand_change_frac = correct_demand_uplift(elasticity_override, markdown_pct)
    demand_multiplier  = 1 + demand_change_frac

    # Unit calculations using daily velocity * forecast days
    base_qty        = velocity_day * forecast_days
    new_qty         = base_qty * demand_multiplier
    incremental_qty = new_qty - base_qty

    # Revenue calculations
    base_revenue      = base_qty * price
    new_revenue       = new_qty * new_price
    revenue_change    = new_revenue - base_revenue
    revenue_change_pct= (revenue_change / (base_revenue + 1e-9)) * 100

    # Profit calculations
    base_profit  = base_qty * (price     - cost_price)
    new_profit   = new_qty  * (new_price - cost_price)
    profit_change= new_profit - base_profit
    profit_change_pct = (profit_change / (abs(base_profit) + 1e-9)) * 100

    # Clearance probability
    clearance_prob = min((new_qty / (quantity + 1e-9)) * 100, 98) if quantity > 0 else 0

    # FIX 5: health assessment
    health = health_badge(revenue_change_pct, margin_impact_pp)

    # ── Results ───────────────────────────────────────────────────
    st.divider()
    st.markdown("### 📊 Simulation Results")

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("🏷️ New Price",
              f"${new_price:.2f}",
              f"-${price - new_price:.2f}" if not below_floor else "⛔ At floor")
    c2.metric("📦 Units Sold",
              f"{new_qty:.0f}",
              f"+{incremental_qty:.0f}")
    c3.metric("💵 Revenue",
              f"${new_revenue:,.0f}",
              f"{revenue_change_pct:+.1f}%")
    c4.metric("📉 Margin",
              f"{new_margin_pct:.1f}%",
              f"{margin_impact_pp:+.1f}pp",
              delta_color="inverse")          # red when margin drops
    c5.metric("🎯 Clearance Prob.", f"{clearance_prob:.0f}%")

    # FIX 5: combined health status
    st.info(f"**Decision Health:** {health}")

    # Additional context row
    col_a, col_b, col_c = st.columns(3)
    col_a.metric("📈 Demand Uplift",
                 f"+{demand_change_frac*100:.1f}%",
                 f"multiplier ×{demand_multiplier:.2f}")
    col_b.metric("💰 Profit Change",
                 f"${new_profit:,.0f}",
                 f"{profit_change_pct:+.1f}%",
                 delta_color="normal")
    col_c.metric("📊 Elasticity Used",
                 f"{elasticity_override:.1f}",
                 "inelastic" if abs(elasticity_override) < 1 else
                 "elastic" if abs(elasticity_override) > 2 else "moderate")

    st.divider()

    # ── Sweep analysis ────────────────────────────────────────────
    st.markdown("### 📈 Markdown Sweep Analysis")
    st.caption(
        "Tests every discount level from 0% to 60% and shows the optimal point. "
        "Grey zone = below cost floor (blocked)."
    )

    sweep_pcts   = list(range(0, 65, 5))
    sweep_results= []

    for pct in sweep_pcts:
        np_  = price * (1 - pct / 100)
        # FIX 7: respect cost floor in sweep
        valid = np_ >= min_sell_price
        if not valid:
            sweep_results.append({
                "Markdown %": pct, "New Price": np_,
                "Units": 0, "Revenue": 0, "Profit": 0,
                "Margin %": 0, "Valid": False
            })
            continue
        dc   = correct_demand_uplift(elasticity_override, pct)
        q    = velocity_day * forecast_days * (1 + dc)
        rev  = q * np_
        prof = q * (np_ - cost_price)
        marg = ((np_ - cost_price) / (np_ + 1e-9)) * 100
        sweep_results.append({
            "Markdown %": pct, "New Price": round(np_, 2),
            "Units": round(q, 1), "Revenue": round(rev, 2),
            "Profit": round(prof, 2), "Margin %": round(marg, 1),
            "Valid": True
        })

    sweep_df       = pd.DataFrame(sweep_results)
    sweep_valid    = sweep_df[sweep_df["Valid"]]
    sweep_invalid  = sweep_df[~sweep_df["Valid"]]

    col1, col2 = st.columns(2)
    with col1:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=sweep_valid["Markdown %"], y=sweep_valid["Revenue"],
            name="Revenue", line=dict(color="#6366f1", width=2.5)
        ))
        fig.add_trace(go.Scatter(
            x=sweep_valid["Markdown %"], y=sweep_valid["Profit"],
            name="Profit", line=dict(color="#10b981", width=2.5)
        ))
        # Mark invalid zone
        if not sweep_invalid.empty:
            fig.add_vrect(
                x0=sweep_invalid["Markdown %"].min(), x1=65,
                fillcolor="rgba(239,68,68,0.1)", line_width=0,
                annotation_text="Below cost floor",
                annotation_position="top left"
            )
        fig.add_vline(x=markdown_pct, line_dash="dash", line_color="#ef4444",
                      annotation_text=f"Selected: {markdown_pct}%")
        fig.update_layout(
            title="Revenue vs Profit by Markdown Depth",
            height=350, margin=dict(l=0, r=0, t=40, b=0),
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            legend=dict(orientation="h", y=1.1)
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(
            x=sweep_valid["Markdown %"], y=sweep_valid["Units"],
            name="Units Sold", line=dict(color="#f59e0b", width=2.5),
            yaxis="y"
        ))
        fig2.add_trace(go.Scatter(
            x=sweep_valid["Markdown %"], y=sweep_valid["Margin %"],
            name="Margin %", line=dict(color="#ef4444", width=2),
            yaxis="y2"
        ))
        fig2.add_hline(y=10, line_dash="dot", line_color="#6b7280",
                       annotation_text="Min 10% margin floor")
        fig2.add_vline(x=markdown_pct, line_dash="dash", line_color="#6366f1",
                       annotation_text=f"Selected: {markdown_pct}%")
        fig2.update_layout(
            title="Units Sold & Margin % by Markdown Depth",
            height=350, margin=dict(l=0, r=0, t=40, b=0),
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            yaxis=dict(title="Units"),
            yaxis2=dict(title="Margin %", overlaying="y", side="right"),
            legend=dict(orientation="h", y=1.1)
        )
        st.plotly_chart(fig2, use_container_width=True)

    # ── FIX 7: Optimal markdown with constraints ──────────────────
    if not sweep_valid.empty and sweep_valid["Revenue"].max() > 0:
        # Score = 60% revenue weight + 40% margin weight
        rev_norm  = sweep_valid["Revenue"] / sweep_valid["Revenue"].max()
        marg_norm = (sweep_valid["Margin %"].clip(lower=0) /
                     sweep_valid["Margin %"].clip(lower=0).max())
        score     = rev_norm * 0.6 + marg_norm * 0.4
        optimal_row = sweep_valid.loc[score.idxmax()]

        st.success(
            f"🎯 **Optimal Markdown (revenue + margin balanced): "
            f"{optimal_row['Markdown %']:.0f}%** — "
            f"Projected Revenue: ${optimal_row['Revenue']:,.0f} | "
            f"Units: {optimal_row['Units']:.0f} | "
            f"Margin: {optimal_row['Margin %']:.1f}% | "
            f"Profit: ${optimal_row['Profit']:,.0f}"
        )
    else:
        st.warning("⚠️ No valid markdown levels found above cost floor at current cost price.")

    # ── Full sweep table ──────────────────────────────────────────
    st.markdown("### 📋 Full Sweep Table")
    display_sweep = sweep_df.copy()
    display_sweep["New Price"] = display_sweep["New Price"].map("${:,.2f}".format)
    display_sweep["Revenue"]   = display_sweep.apply(
        lambda r: f"${r['Revenue']:,.0f}" if r["Valid"] else "⛔ Below floor", axis=1)
    display_sweep["Profit"]    = display_sweep.apply(
        lambda r: f"${r['Profit']:,.0f}"  if r["Valid"] else "—", axis=1)
    display_sweep["Margin %"]  = display_sweep.apply(
        lambda r: f"{r['Margin %']:.1f}%" if r["Valid"] else "—", axis=1)
    display_sweep["Status"]    = display_sweep["Valid"].map(
        {True: "✅ Valid", False: "⛔ Below floor"})
    display_sweep = display_sweep.drop(columns=["Valid"])
    st.dataframe(display_sweep, use_container_width=True, hide_index=True)

    # ── Elasticity explainer ──────────────────────────────────────
    with st.expander("📚 How elasticity is calculated (methodology)"):
        st.markdown(f"""
**Price Elasticity Formula:**
```
Elasticity = % change in demand / % change in price
```

**For this simulation (elasticity = {elasticity_override:.1f}, markdown = {markdown_pct}%):**
```
Price change   = -{markdown_pct}% (price fell)
Demand change  = {elasticity_override:.1f} × (-{markdown_pct/100:.2f}) = +{abs(elasticity_override * markdown_pct/100)*100:.1f}%
New units      = {base_qty:.1f} × (1 + {demand_change_frac:.3f}) = {new_qty:.1f} units
```

**Elasticity guide:**
| Value | Meaning | Typical product |
|-------|---------|-----------------|
| -0.3 to -0.8 | Inelastic — demand barely changes | Luxury, staples |
| -0.8 to -1.5 | Moderate — standard retail response | Apparel, Electronics |
| -1.5 to -3.0 | Elastic — strong discount response | Commodity, Grocery |

**Why not -10?** An elasticity of -10 means a 10% price cut causes 100% demand increase. This is unrealistic for retail (even flash sales rarely exceed 3×). The slider is capped at -3.0 to keep simulations grounded in real retail behaviour.
        """)