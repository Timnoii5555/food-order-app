"""TimNoi Shabu — standalone back-office entrypoint.

Deployed as a SEPARATE app from tim.py (the customer storefront) so the
admin dashboard lives at its own address instead of being reachable through
the customer site's sidebar. To run it: point a second deployment (a second
Streamlit Community Cloud app, or your own server) at this file instead of
tim.py — see README.md's "หลังร้านแยกเว็บ" section for exact steps.

Shares the same app_lib.py / app_pages/admin.py as the customer app (same
CSV data, same secrets.toml), just with no customer-facing pages wired in.
"""

import streamlit as st

from app_lib import daily_cleanup, init_session_state, inject_scoped_css, live_refresh_watcher

st.set_page_config(
    page_title="TimNoi Shabu — หลังร้าน",
    page_icon="🔐",
    layout="wide",
    menu_items={
        "Get help": None,
        "Report a bug": None,
        "About": "TimNoi Shabu — ระบบจัดการหลังร้าน",
    },
)

init_session_state()
daily_cleanup()
inject_scoped_css()
live_refresh_watcher()

# Single-page app, so position="hidden" is safe here — the reload-bounces-
# to-default bug (see tim.py's routing comment) only bites *non-default*
# pages, and this one page is always the default.
pages = st.navigation(
    [st.Page("app_pages/admin.py", title="แอดมิน", icon=":material/admin_panel_settings:", default=True)],
    position="hidden",
)
pages.run()
