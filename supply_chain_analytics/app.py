"""
Supply Chain Analytics Platform — Main Application.

Entry point for the Streamlit app with authentication, navigation,
sidebar, custom CSS, and business insights panel.
"""

import os
import sys
import logging

import streamlit as st
import bcrypt
import pandas as pd

# Ensure project root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.database import get_db, init_db, get_engine
from database.models import User

# ── Logging Setup ──────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ── Page Config ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Supply Chain Analytics Platform",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ─────────────────────────────────────────────────────────────
def inject_css():
    """Inject custom CSS for dark mode enterprise styling."""
    st.markdown("""
    <style>
        /* ── Import Fonts ─────────────────────────────────────────── */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

        /* ── Global ───────────────────────────────────────────────── */
        .stApp {
            font-family: 'Inter', sans-serif;
        }

        /* ── Sidebar Styling ──────────────────────────────────────── */
        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #0f172a 0%, #1e1b4b 50%, #0f172a 100%);
            border-right: 1px solid rgba(99, 102, 241, 0.2);
        }

        section[data-testid="stSidebar"] .stMarkdown p {
            color: #e2e8f0;
        }

        /* ── KPI Cards ────────────────────────────────────────────── */
        .kpi-card {
            background: linear-gradient(135deg, rgba(30, 27, 75, 0.8), rgba(15, 23, 42, 0.9));
            border: 1px solid rgba(99, 102, 241, 0.3);
            border-left: 4px solid #6366f1;
            border-radius: 12px;
            padding: 18px 16px;
            margin: 4px 0;
            backdrop-filter: blur(10px);
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }

        .kpi-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(99, 102, 241, 0.2);
        }

        .kpi-card.kpi-alert {
            border-left: 4px solid #ef4444;
            background: linear-gradient(135deg, rgba(127, 29, 29, 0.3), rgba(15, 23, 42, 0.9));
        }

        .kpi-label {
            color: #94a3b8;
            font-size: 0.75rem;
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 6px;
        }

        .kpi-value {
            color: #f1f5f9;
            font-size: 1.5rem;
            font-weight: 700;
            line-height: 1.2;
        }

        /* ── Insight Cards ────────────────────────────────────────── */
        .insight-card {
            background: rgba(30, 27, 75, 0.5);
            border: 1px solid rgba(99, 102, 241, 0.2);
            border-radius: 10px;
            padding: 16px 18px;
            margin: 8px 0;
            color: #e2e8f0;
            font-size: 0.9rem;
            line-height: 1.6;
            transition: background 0.2s ease;
        }

        .insight-card:hover {
            background: rgba(30, 27, 75, 0.7);
        }

        /* ── Login Card ───────────────────────────────────────────── */
        .login-container {
            max-width: 420px;
            margin: 80px auto;
            padding: 40px;
            background: linear-gradient(135deg, rgba(30, 27, 75, 0.9), rgba(15, 23, 42, 0.95));
            border: 1px solid rgba(99, 102, 241, 0.3);
            border-radius: 20px;
            backdrop-filter: blur(20px);
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
        }

        .login-title {
            text-align: center;
            font-size: 1.8rem;
            font-weight: 800;
            background: linear-gradient(135deg, #6366f1, #a78bfa, #c084fc);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 8px;
        }

        .login-subtitle {
            text-align: center;
            color: #94a3b8;
            font-size: 0.9rem;
            margin-bottom: 30px;
        }

        /* ── Header Branding ──────────────────────────────────────── */
        .brand-header {
            text-align: center;
            padding: 15px 0;
            margin-bottom: 10px;
        }

        .brand-title {
            font-size: 1.4rem;
            font-weight: 800;
            background: linear-gradient(135deg, #6366f1, #a78bfa);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            letter-spacing: -0.02em;
        }

        .brand-sub {
            font-size: 0.7rem;
            color: #64748b;
            text-transform: uppercase;
            letter-spacing: 0.15em;
        }

        /* ── Misc Tweaks ──────────────────────────────────────────── */
        .stDataFrame {
            border-radius: 10px;
            overflow: hidden;
        }

        div[data-testid="stMetricValue"] {
            font-weight: 700;
        }

        .stButton > button {
            background: linear-gradient(135deg, #4f46e5, #7c3aed);
            color: white;
            border: none;
            border-radius: 8px;
            padding: 8px 24px;
            font-weight: 600;
            transition: all 0.2s ease;
        }

        .stButton > button:hover {
            background: linear-gradient(135deg, #6366f1, #8b5cf6);
            box-shadow: 0 4px 15px rgba(99, 102, 241, 0.4);
            transform: translateY(-1px);
        }

        .stSelectbox > div > div {
            border-color: rgba(99, 102, 241, 0.3);
        }

        .stDownloadButton > button {
            background: linear-gradient(135deg, #059669, #10b981);
            border: none;
            color: white;
            border-radius: 8px;
        }

        /* ── Business Insights Panel ──────────────────────────────── */
        .insights-panel {
            background: linear-gradient(135deg, rgba(30, 27, 75, 0.5), rgba(15, 23, 42, 0.7));
            border: 1px solid rgba(99, 102, 241, 0.2);
            border-radius: 14px;
            padding: 20px;
            margin-top: 10px;
        }

        .insights-title {
            font-size: 1rem;
            font-weight: 700;
            color: #a78bfa;
            margin-bottom: 12px;
        }

        /* ── Animation ────────────────────────────────────────────── */
        @keyframes fadeInUp {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .kpi-card, .insight-card {
            animation: fadeInUp 0.4s ease-out;
        }

        /* ── Scrollbar ────────────────────────────────────────────── */
        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-track { background: #0f172a; }
        ::-webkit-scrollbar-thumb { background: #4f46e5; border-radius: 3px; }
    </style>
    """, unsafe_allow_html=True)


# ── Authentication ─────────────────────────────────────────────────────────
def authenticate(username: str, password: str) -> dict | None:
    """Verify username/password against database. Returns user dict or None."""
    try:
        session = get_db()
        user = session.query(User).filter(User.username == username).first()
        session.close()

        if user and bcrypt.checkpw(password.encode("utf-8"),
                                     user.password_hash.encode("utf-8")):
            return {
                "user_id": user.user_id,
                "username": user.username,
                "full_name": user.full_name,
                "role": user.role,
                "email": user.email,
            }
    except Exception as e:
        logger.error("Authentication error: %s", e)
    return None


def render_login():
    """Render the login page."""
    st.markdown("""
    <div class="login-container">
        <div class="login-title">📊 Supply Chain Analytics</div>
        <div class="login-subtitle">AI-Powered Business Intelligence Platform</div>
    </div>
    """, unsafe_allow_html=True)

    # Center the login form
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        with st.form("login_form"):
            st.markdown("#### 🔐 Sign In")
            username = st.text_input("Username", placeholder="Enter username")
            password = st.text_input("Password", type="password", placeholder="Enter password")
            submitted = st.form_submit_button("Sign In", use_container_width=True)

            if submitted:
                if username and password:
                    user = authenticate(username, password)
                    if user:
                        st.session_state["authenticated"] = True
                        st.session_state["user"] = user
                        st.rerun()
                    else:
                        st.error("❌ Invalid credentials. Please try again.")
                else:
                    st.warning("Please enter both username and password.")

        st.markdown("---")
        st.markdown("""
        <div style="text-align: center; color: #64748b; font-size: 0.8rem;">
            <strong>Demo Accounts:</strong><br>
            Admin: <code>admin / admin123</code><br>
            Manager: <code>manager / manager123</code><br>
            Analyst: <code>analyst / analyst123</code>
        </div>
        """, unsafe_allow_html=True)


# ── Main Application ──────────────────────────────────────────────────────
def main():
    """Main application entry point."""
    inject_css()

    # Initialize database tables
    init_db()

    # Check authentication
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    if not st.session_state["authenticated"]:
        render_login()
        return

    user = st.session_state["user"]

    # ── Sidebar ────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown("""
        <div class="brand-header">
            <div class="brand-title">📊 SupplyChain AI</div>
            <div class="brand-sub">Analytics Platform</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")

        # User info
        role_emoji = {"Admin": "👑", "Supply Chain Manager": "🏭", "Analyst": "📈"}.get(
            user["role"], "👤")
        st.markdown(f"""
        <div style="text-align: center; padding: 5px 0;">
            <div style="font-size: 1.2rem;">{role_emoji}</div>
            <div style="color: #e2e8f0; font-weight: 600;">{user['full_name']}</div>
            <div style="color: #64748b; font-size: 0.8rem;">{user['role']}</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")

        # Navigation
        st.markdown("#### Navigation")
        selected = st.radio(
            label="",
            options=["Dashboard", "Inventory", "Suppliers", "Logistics", "Forecasting", "Reports"],
            index=0,
            key="selected_page",
            label_visibility="collapsed",
        )

        st.markdown("---")

        # Business Insights in sidebar
        st.markdown("""
        <div class="insights-title">💡 Business Insights</div>
        """, unsafe_allow_html=True)

        try:
            from services.forecasting_service import ForecastingService
            fc_service = ForecastingService()
            insights = fc_service.generate_business_insights()
            for insight in insights[:5]:
                st.markdown(f"""
                <div class="insight-card" style="padding: 10px 12px; font-size: 0.8rem; margin: 4px 0;">
                    {insight['icon']} <strong>{insight['category']}</strong><br>
                    {insight['message']}
                </div>
                """, unsafe_allow_html=True)
        except Exception:
            st.markdown("""
            <div class="insight-card" style="font-size: 0.8rem;">
                📊 Insights will appear after data is loaded.
            </div>
            """, unsafe_allow_html=True)

        # Spacer + Logout
        st.markdown("<br>" * 2, unsafe_allow_html=True)
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state["authenticated"] = False
            st.session_state.pop("user", None)
            st.session_state.pop("forecast_result", None)
            st.rerun()

    # ── Page Router ────────────────────────────────────────────────────
    if selected == "Dashboard":
        from app_pages.dashboard import render_dashboard
        render_dashboard()

    elif selected == "Inventory":
        from app_pages.inventory import render_inventory
        render_inventory()

    elif selected == "Suppliers":
        from app_pages.suppliers import render_suppliers
        render_suppliers()

    elif selected == "Logistics":
        from app_pages.logistics import render_logistics
        render_logistics()

    elif selected == "Forecasting":
        from app_pages.forecasting import render_forecasting
        render_forecasting()

    elif selected == "Reports":
        from app_pages.reports import render_reports
        render_reports()


if __name__ == "__main__":
    main()
