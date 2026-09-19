"""TimNoi Shabu — order-ahead & kitchen console. Entrypoint.

A multi-page Streamlit app used two ways:
  * Customers scan a table QR code, browse the menu, and place orders
    (app_pages/menu.py, cart.py, feedback.py).
  * Staff open the admin panel to run the kitchen queue, sales, menu,
    promotions, tables, contact details, and reviews (app_pages/admin.py).

Everything shared across pages — constants, CSV-backed data helpers, the
header, the live-refresh fragment — lives in app_lib.py. This file only
does the one-time-per-run setup and then routes to the current page.

Data lives in plain CSV files next to this script (see app_lib.py's *_CSV
constants) so the app needs no external database. Visual styling comes from
``.streamlit/config.toml`` (brand theme) plus native Streamlit widgets —
see the README for why almost no custom HTML/CSS is used.
"""

import streamlit as st

from app_lib import (
    daily_cleanup, init_session_state, inject_scoped_css, live_refresh_watcher,
    load_contacts, render_header, restore_identity_from_query_params,
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
render_header(load_contacts())

# ============================================================================
# Routing — a real multi-page app (distinct, bookmarkable URLs) using
# Streamlit's own navigation. position="hidden" looks tempting (the header
# above already provides navigation via its "เมนู" popover) but it has a
# real bug: reloading the browser on a non-default page silently bounces
# back to the default page, since "hidden" also switches off the bit of
# Streamlit that reads the current path back out of the URL on a fresh
# load. position="top" doesn't have that bug, so it's used here instead,
# with its nav bar hidden by the one targeted CSS rule in
# inject_scoped_css() (Streamlit's own stable data-testid, not a guess).
# ============================================================================
pages = st.navigation(
    [
        st.Page("app_pages/menu.py", title="เมนู", icon=":material/storefront:",
                url_path="menu", default=True),
        st.Page("app_pages/cart.py", title="ตะกร้า", icon=":material/shopping_cart:",
                url_path="cart"),
        st.Page("app_pages/feedback.py", title="ติชม", icon=":material/rate_review:",
                url_path="feedback"),
        st.Page("app_pages/admin.py", title="แอดมิน", icon=":material/admin_panel_settings:",
                url_path="admin"),
    ],
    position="top",
)
pages.run()
