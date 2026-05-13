# import streamlit as st
# import sys
# import os

# sys.path.insert(0, os.path.dirname(__file__))

# st.set_page_config(
#     page_title="RetailAI — Markdown & Promotion Optimizer",
#     page_icon="🏪",
#     layout="wide",
#     initial_sidebar_state="expanded"
# )

# # ── Custom CSS ─────────────────────────────────────────────────────────────
# st.markdown("""
# <style>
# /* Base */
# [data-testid="stAppViewContainer"] { background: #0f0f1a; }
# [data-testid="stSidebar"] { background: #13131f; border-right: 1px solid #1e1e35; }
# [data-testid="stSidebar"] * { color: #e2e8f0 !important; }

# /* Header */
# .block-container { padding-top: 1.5rem; }
# h1,h2,h3 { color: #e2e8f0 !important; }
# p, li, span { color: #cbd5e1 !important; }

# /* Metrics */
# [data-testid="stMetric"] {
#     background: linear-gradient(135deg, #1a1a2e, #16213e);
#     border: 1px solid #2d2d4e;
#     border-radius: 12px;
#     padding: 14px 18px;
# }
# [data-testid="stMetricValue"] { color: #a5b4fc !important; font-size: 1.6rem !important; font-weight: 700 !important; }
# [data-testid="stMetricLabel"] { color: #94a3b8 !important; font-size: 0.78rem !important; }
# [data-testid="stMetricDelta"] { font-size: 0.75rem !important; }

# /* Tabs */
# [data-testid="stTabs"] button { color: #94a3b8 !important; font-size: 0.85rem; }
# [data-testid="stTabs"] button[aria-selected="true"] { color: #a5b4fc !important; border-bottom: 2px solid #6366f1 !important; }

# /* Selectbox / inputs */
# [data-testid="stSelectbox"] > div { background: #1e1e35 !important; border-radius: 8px; }
# [data-testid="stSlider"] { color: #a5b4fc !important; }

# /* Divider */
# hr { border-color: #1e1e35 !important; }

# /* Expander */
# [data-testid="stExpander"] { background: #1a1a2e !important; border: 1px solid #2d2d4e !important; border-radius: 10px !important; }
# [data-testid="stExpander"] summary { color: #a5b4fc !important; }

# /* Dataframe */
# [data-testid="stDataFrame"] { border-radius: 10px; overflow: hidden; }

# /* Buttons */
# [data-testid="stButton"] button {
#     background: linear-gradient(135deg, #4f46e5, #7c3aed) !important;
#     color: white !important; border: none !important; border-radius: 8px !important;
#     font-weight: 600 !important;
# }

# /* Sidebar nav */
# .nav-item {
#     display: flex; align-items: center; gap: 10px;
#     padding: 10px 14px; border-radius: 10px;
#     cursor: pointer; margin-bottom: 4px;
#     transition: all 0.2s;
#     color: #94a3b8;
#     font-size: 0.9rem;
# }
# .nav-item:hover { background: rgba(99,102,241,0.15); color: #a5b4fc; }
# .nav-item.active { background: rgba(99,102,241,0.25); color: #a5b4fc; font-weight: 600; }

# /* Logo */
# .logo-area {
#     padding: 20px 16px 10px;
#     margin-bottom: 8px;
# }
# .logo-title {
#     font-size: 1.2rem;
#     font-weight: 800;
#     color: #a5b4fc !important;
#     letter-spacing: -0.5px;
# }
# .logo-sub {
#     font-size: 0.72rem;
#     color: #64748b !important;
#     margin-top: 2px;
# }
# </style>
# """, unsafe_allow_html=True)

# # ── Sidebar ─────────────────────────────────────────────────────────────────
# with st.sidebar:
#     st.markdown("""
#     <div class="logo-area">
#         <div class="logo-title">🏪 RetailAI</div>
#         <div class="logo-sub">Markdown & Promotion Optimizer</div>
#     </div>
#     """, unsafe_allow_html=True)
#     st.divider()

#     pages = {
#         "📊 Executive Dashboard":       "executive",
#         "📈 Demand Forecast":           "demand",
#         "📦 Inventory Intelligence":    "inventory",
#         "💡 Markdown Recommendations":  "markdown",
#         "👥 Customer Behavior":         "behavior",
#         "🧠 AI Agent Insights":         "agents",
#         "🔮 What-If Simulator":         "simulator",
#     }

#     if "page" not in st.session_state:
#         st.session_state.page = "executive"

#     for label, key in pages.items():
#         if st.button(label, use_container_width=True, key=f"nav_{key}"):
#             st.session_state.page = key

#     st.divider()
#     st.markdown("""
#     <div style="padding: 12px; background: rgba(99,102,241,0.1); border-radius: 10px; border: 1px solid #2d2d4e;">
#         <div style="font-size:0.75rem; color:#64748b;">Dataset</div>
#         <div style="font-size:0.85rem; color:#a5b4fc; font-weight:600;">AWS Gold Tables</div>
#         <div style="font-size:0.72rem; color:#64748b; margin-top:4px;">
#             6 tables · ~127K records<br>
#             product_catalogue · orders<br>
#             order_items · customers<br>
#             invoices · bq_events
#         </div>
#     </div>
#     """, unsafe_allow_html=True)

#     st.markdown("""
#     <div style="margin-top:12px; padding:10px; background: rgba(16,185,129,0.08); border-radius:10px; border:1px solid #064e3b;">
#         <div style="font-size:0.72rem; color:#6ee7b7;">Multi-Agent System</div>
#         <div style="font-size:0.78rem; color:#94a3b8; margin-top:4px;">
#             💰 Pricing Agent<br>
#             📦 Inventory Agent<br>
#             📈 Demand Agent<br>
#             🎯 Promotion Agent<br>
#             👥 Behavior Agent<br>
#             🧠 Coordinator Agent
#         </div>
#     </div>
#     """, unsafe_allow_html=True)

# # ── Page Routing ─────────────────────────────────────────────────────────────
# page = st.session_state.get("page", "executive")

# if page == "executive":
#     from pages.executive_dashboard import render
# elif page == "demand":
#     from pages.demand_forecast import render
# elif page == "inventory":
#     from pages.inventory_intelligence import render
# elif page == "markdown":
#     from pages.markdown_recommendations import render
# elif page == "behavior":
#     from pages.customer_behavior import render
# elif page == "agents":
#     from pages.agent_insights import render
# elif page == "simulator":
#     from pages.what_if_simulator import render
# else:
#     from pages.executive_dashboard import render

# render()


import streamlit as st
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

st.set_page_config(
    page_title="RetailAI — Markdown & Promotion Optimizer",
    page_icon="🏪",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Hide default Streamlit page nav ────────────────────────────────────────
st.markdown("<style>[data-testid='stSidebarNav'] {display: none;}</style>", unsafe_allow_html=True)

# ── Custom CSS ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* Base */
[data-testid="stAppViewContainer"] { background: #0f0f1a; }
[data-testid="stSidebar"] { background: #13131f; border-right: 1px solid #1e1e35; }
[data-testid="stSidebar"] * { color: #e2e8f0 !important; }

/* Header */
.block-container { padding-top: 1.5rem; }
h1,h2,h3 { color: #e2e8f0 !important; }
p, li, span { color: #cbd5e1 !important; }

/* Metrics */
[data-testid="stMetric"] {
    background: linear-gradient(135deg, #1a1a2e, #16213e);
    border: 1px solid #2d2d4e;
    border-radius: 12px;
    padding: 14px 18px;
}
[data-testid="stMetricValue"] { color: #a5b4fc !important; font-size: 1.6rem !important; font-weight: 700 !important; }
[data-testid="stMetricLabel"] { color: #94a3b8 !important; font-size: 0.78rem !important; }
[data-testid="stMetricDelta"] { font-size: 0.75rem !important; }

/* Tabs */
[data-testid="stTabs"] button { color: #94a3b8 !important; font-size: 0.85rem; }
[data-testid="stTabs"] button[aria-selected="true"] { color: #a5b4fc !important; border-bottom: 2px solid #6366f1 !important; }

/* Selectbox / inputs */
[data-testid="stSelectbox"] > div { background: #1e1e35 !important; border-radius: 8px; }
[data-testid="stSlider"] { color: #a5b4fc !important; }

/* Divider */
hr { border-color: #1e1e35 !important; }

/* Expander */
[data-testid="stExpander"] { background: #1a1a2e !important; border: 1px solid #2d2d4e !important; border-radius: 10px !important; }
[data-testid="stExpander"] summary { color: #a5b4fc !important; }

/* Dataframe */
[data-testid="stDataFrame"] { border-radius: 10px; overflow: hidden; }

/* Buttons */
[data-testid="stButton"] button {
    background: linear-gradient(135deg, #4f46e5, #7c3aed) !important;
    color: white !important; border: none !important; border-radius: 8px !important;
    font-weight: 600 !important;
}

/* Sidebar nav */
.nav-item {
    display: flex; align-items: center; gap: 10px;
    padding: 10px 14px; border-radius: 10px;
    cursor: pointer; margin-bottom: 4px;
    transition: all 0.2s;
    color: #94a3b8;
    font-size: 0.9rem;
}
.nav-item:hover { background: rgba(99,102,241,0.15); color: #a5b4fc; }
.nav-item.active { background: rgba(99,102,241,0.25); color: #a5b4fc; font-weight: 600; }

/* Logo */
.logo-area {
    padding: 20px 16px 10px;
    margin-bottom: 8px;
}
.logo-title {
    font-size: 1.2rem;
    font-weight: 800;
    color: #a5b4fc !important;
    letter-spacing: -0.5px;
}
.logo-sub {
    font-size: 0.72rem;
    color: #64748b !important;
    margin-top: 2px;
}
</style>
""", unsafe_allow_html=True)

# ── Sidebar ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div class="logo-area">
        <div class="logo-title">🏪 RetailAI</div>
        <div class="logo-sub">Markdown & Promotion Optimizer</div>
    </div>
    """, unsafe_allow_html=True)
    st.divider()

    pages = {
        "📊 Executive Dashboard":       "executive",
        "📈 Demand Forecast":           "demand",
        "📦 Inventory Intelligence":    "inventory",
        "💡 Markdown Recommendations":  "markdown",
        "👥 Customer Behavior":         "behavior",
        "🧠 AI Agent Insights":         "agents",
        "🔮 What-If Simulator":         "simulator",
    }

    if "page" not in st.session_state:
        st.session_state.page = "executive"

    for label, key in pages.items():
        if st.button(label, use_container_width=True, key=f"nav_{key}"):
            st.session_state.page = key

    st.divider()
    st.markdown("""
    <div style="padding: 12px; background: rgba(99,102,241,0.1); border-radius: 10px; border: 1px solid #2d2d4e;">
        <div style="font-size:0.75rem; color:#64748b;">Dataset</div>
        <div style="font-size:0.85rem; color:#a5b4fc; font-weight:600;">AWS Gold Tables</div>
        <div style="font-size:0.72rem; color:#64748b; margin-top:4px;">
            6 tables · ~127K records<br>
            product_catalogue · orders<br>
            order_items · customers<br>
            invoices · bq_events
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div style="margin-top:12px; padding:10px; background: rgba(16,185,129,0.08); border-radius:10px; border:1px solid #064e3b;">
        <div style="font-size:0.72rem; color:#6ee7b7;">Multi-Agent System</div>
        <div style="font-size:0.78rem; color:#94a3b8; margin-top:4px;">
            💰 Pricing Agent<br>
            📦 Inventory Agent<br>
            📈 Demand Agent<br>
            🎯 Promotion Agent<br>
            👥 Behavior Agent<br>
            🧠 Coordinator Agent
        </div>
    </div>
    """, unsafe_allow_html=True)

# ── Page Routing ─────────────────────────────────────────────────────────────
page = st.session_state.get("page", "executive")

if page == "executive":
    from pages.executive_dashboard import render
elif page == "demand":
    from pages.demand_forecast import render
elif page == "inventory":
    from pages.inventory_intelligence import render
elif page == "markdown":
    from pages.markdown_recommendations import render
elif page == "behavior":
    from pages.customer_behavior import render
elif page == "agents":
    from pages.agent_insights import render
elif page == "simulator":
    from pages.what_if_simulator import render
else:
    from pages.executive_dashboard import render

render()