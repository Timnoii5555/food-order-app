"""Customer — feedback / guestbook page.

Deliberately not gated by the kitchen-queue check that menu.py and cart.py
apply: leaving a comment isn't an ordering action, so there's no reason to
block it just because the kitchen is full.
"""

import time

import streamlit as st

from app_lib import clean_text, load_shop_context, render_customer_topbar, require_customer_identity, save_feedback_entry

require_customer_identity()
ctx = load_shop_context()

render_customer_topbar(ctx, apply_queue_gate=False, show_cart_badge=True)

if st.button("กลับ", icon=":material/arrow_back:"):
    st.switch_page("app_pages/menu.py")
st.subheader("เขียนติชม", anchor=False, icon=":material/rate_review:")
with st.form("fb", border=False):
    m = st.text_area("ข้อความถึงร้าน", max_chars=500)
    if st.form_submit_button("ส่ง", icon=":material/send:"):
        m = clean_text(m, 500)
        if m:
            save_feedback_entry(st.session_state.user_name, m)
            st.success("ขอบคุณสำหรับความคิดเห็นครับ", icon=":material/check_circle:")
            time.sleep(1)
            st.switch_page("app_pages/menu.py")
        else:
            st.error("กรุณาพิมพ์ข้อความก่อนส่ง")
