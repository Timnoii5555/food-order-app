"""ทำไมต้องสั่งผ่านหน้านี้? — standalone info page (moved out of the identity
screen's expander so it has its own URL and doesn't compete with the sign-in
form for attention)."""

import streamlit as st

from app_lib import render_why_us_grid

st.header("ทำไมต้องสั่งผ่านหน้านี้?", anchor=False, icon=":material/help:")
st.caption("จุดเด่นของระบบสั่งอาหารออนไลน์ของ TimNoi Shabu เทียบกับการสั่งแบบเดิม")
render_why_us_grid()
