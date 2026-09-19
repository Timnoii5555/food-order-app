"""TimNoi Shabu — customer storefront. Entrypoint.

A multi-page Streamlit app for customers: scan a table QR code, browse the
menu, and place orders (app_pages/menu.py, cart.py, feedback.py, why_us.py).

The admin/back-office dashboard (kitchen queue, sales, menu, promotions,
tables, contact details, reviews) is a SEPARATE app — see admin_app.py —
deployed on its own so it isn't reachable through this site's navigation.
Both entrypoints share the same app_lib.py and CSV data.

Everything shared across customer pages — constants, CSV-backed data
helpers, the header, the live-refresh fragment — lives in app_lib.py. This
file only does the one-time-per-run setup and then routes to the current
page.

Data lives in plain CSV files next to this script (see app_lib.py's *_CSV
constants) so the app needs no external database. Visual styling comes from
``.streamlit/config.toml`` (brand theme) plus native Streamlit widgets —
see the README for why almost no custom HTML/CSS is used.
"""

import streamlit as st

from app_lib import (
    daily_cleanup, init_session_state, inject_scoped_css, live_refresh_watcher,
    load_contacts, render_header, render_sidebar_extras, restore_identity_from_query_params,
)

# ============================================================================
# Page config (must run before any other Streamlit command)
# ============================================================================
st.set_page_config(
    page_title="TimNoi Shabu",
    page_icon="🍲",
    layout="wide",
    menu_items={
        "Get help": None,
        "Report a bug": None,
        "About": "TimNoi Shabu — ระบบสั่งอาหารหน้าร้านและจัดการครัว",
    },
)

# ============================================================================
# Shared setup — runs on every page view, before routing to the active page.
# ============================================================================
init_session_state()
restore_identity_from_query_params()
daily_cleanup()
inject_scoped_css()
live_refresh_watcher()

contacts = load_contacts()
render_header(contacts)

# ============================================================================
# Routing — a real multi-page app (distinct, bookmarkable URLs) using
# Streamlit's own sidebar navigation. Earlier this used position="top" with
# a custom "เมนู" popover for navigation, hiding Streamlit's built-in nav
# bar — but a hidden/collapsed sidebar toggle isn't where people expect
# site navigation to live, and doubling "เมนู" as both "food menu" and
# "site navigation" was confusing. position="sidebar" (Streamlit's default)
# gives a real, always-reachable sidebar nav on every page; it does not
# have the reload-routing bug position="hidden" has (see git history) now
# that check_system_updates() (app_lib.py) never reports a change on a
# session's very first check.
# ============================================================================
pages = st.navigation(
    [
        st.Page("app_pages/menu.py", title="เมนู", icon=":material/storefront:",
                url_path="menu", default=True),
        st.Page("app_pages/cart.py", title="ตะกร้า", icon=":material/shopping_cart:",
                url_path="cart"),
        st.Page("app_pages/feedback.py", title="ติชม", icon=":material/rate_review:",
                url_path="feedback"),
        st.Page("app_pages/why_us.py", title="ทำไมต้องสั่งที่นี่", icon=":material/help:",
                url_path="why-us"),
    ],
    position="sidebar",
)
render_sidebar_extras(contacts)
pages.run()
