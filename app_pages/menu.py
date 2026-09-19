"""Customer — identity screen (if not confirmed yet) and menu browsing."""

import streamlit as st

from app_lib import (
    clean_text, load_shop_context, render_customer_topbar,
    resolve_img_src, thb, add_to_queue,
)

ctx = load_shop_context()

# ============================================================================
# Identity screen — shown until the customer confirms a name + table.
# ============================================================================
if not st.session_state.details_confirmed:
    st.header("ยินดีต้อนรับ", anchor=False, icon=":material/waving_hand:")
    st.caption("ระบบสั่งอาหารออนไลน์อย่างเป็นทางการของ TimNoi Shabu")
    with st.container(horizontal=True, wrap=True):
        st.badge("สั่งตรงเข้าครัวทันที", icon=":material/bolt:", color="green")
        st.badge("ไม่มีค่าคอมมิชชั่นแฝง", icon=":material/sell:", color="blue")
        st.badge("ไม่ต้องสมัครสมาชิก", icon=":material/privacy_tip:", color="violet")
    if st.button("ทำไมต้องสั่งผ่านหน้านี้? ดีกว่ายังไง", icon=":material/help:"):
        st.switch_page("app_pages/why_us.py")

    with st.container(border=True):
        c_name_input = st.text_input("ชื่อลูกค้า (ชื่อเล่น)", value=st.session_state.user_name)

        existing_table = None
        is_returning = False
        if c_name_input:
            lookup = ctx.orders_df.copy()
            lookup["ลูกค้า"] = lookup["ลูกค้า"].astype(str)
            match = lookup[(lookup["ลูกค้า"] == c_name_input) & (lookup["สถานะ"] == "waiting")]
            if not match.empty:
                existing_table = str(match.iloc[0]["โต๊ะ"])
                is_returning = True
                st.success(f"พบรายการสั่งค้างของ **{c_name_input}**", icon=":material/celebration:")
                st.caption(f"ระบบเลือกโต๊ะ **{existing_table}** ให้อัตโนมัติ")

        table_input = None
        if is_returning:
            table_input = existing_table
            st.selectbox("โต๊ะของคุณ", [existing_table], disabled=True)
            if st.button("ไม่ใช่ฉัน / เปลี่ยนชื่อใหม่"):
                st.session_state.user_name = ""
                st.rerun()
        else:
            all_tables = ctx.tables_df["table_name"].astype(str).tolist()
            current_table = str(st.session_state.user_table)
            avail = [t for t in all_tables
                     if t in ctx.shared_tables or t not in ctx.busy_tables or t == current_table]
            if avail:
                curr = avail.index(current_table) if current_table in avail else 0
                table_input = st.selectbox("เลือกโต๊ะ", avail, index=curr)
            else:
                st.warning("ตอนนี้โต๊ะเต็มทุกโต๊ะ กรุณารอสักครู่ หรือรับบัตรคิวด้านล่าง",
                           icon=":material/event_busy:")

        if st.button("ยืนยัน", type="primary", icon=":material/check:", width="stretch"):
            clean_name = clean_text(c_name_input, 40)
            if not clean_name or not table_input:
                st.error("กรุณาระบุชื่อและเลือกโต๊ะให้ครบ")
            else:
                st.session_state.user_name = clean_name
                st.session_state.user_table = table_input
                st.session_state.details_confirmed = True
                st.query_params["name"] = clean_name
                st.query_params["table"] = table_input
                st.rerun()

    if ctx.is_queue_mode:
        st.warning(f"ครัวแน่น ({ctx.kitchen_load} ออเดอร์ในคิว)", icon=":material/warning:")
        q_name = st.text_input("จองคิว (ชื่อ)", key="q_name_precheck")
        if st.button("รับบัตรคิว", icon=":material/confirmation_number:"):
            q_name = clean_text(q_name, 40)
            if q_name:
                qid, _ = add_to_queue(q_name)
                st.session_state.my_queue_id = qid
                st.success(f"บัตรคิวของคุณคือ {qid}")
            else:
                st.error("กรุณาใส่ชื่อ")
    st.stop()

# ============================================================================
# Logged in — menu browsing.
# ============================================================================
render_customer_topbar(ctx, apply_queue_gate=True, show_cart_badge=True)

st.subheader("เมนู", anchor=False, icon=":material/menu_book:")


def render_menu_grid(items_df):
    cols = st.columns(2)
    for n, (idx, row) in enumerate(items_df.iterrows()):
        with cols[n % 2]:
            with st.container(border=True, key=f"menu_card_{idx}"):
                st.image(resolve_img_src(row["img"]), width="stretch")
                st.markdown(f"**{row['name']}**")
                if row["in_stock"]:
                    st.caption(thb(row["price"]))
                    if st.button("เพิ่มลงตะกร้า", key=f"add_{idx}",
                                  icon=":material/add_shopping_cart:", width="stretch"):
                        st.session_state.basket.append(row.to_dict())
                        st.toast(f"เพิ่ม {row['name']} แล้ว", icon=":material/check_circle:")
                        # Rerun so the cart badge in the top bar (rendered
                        # earlier on this page, above the grid) picks up the
                        # new count right away instead of lagging one
                        # interaction behind.
                        st.rerun()
                else:
                    st.badge("หมดสต็อก", icon=":material/block:", color="red")
                    st.button("หมดสต็อก", key=f"no_{idx}", disabled=True, width="stretch")


categories = [c for c in ctx.menu_df["category"].dropna().unique().tolist() if str(c).strip()]
search_query = st.text_input(
    "ค้นหาเมนู", placeholder="ค้นหาเมนู เช่น หมูหมัก, ผักรวม...",
    icon=":material/search:", label_visibility="collapsed",
)
search_query = (search_query or "").strip()

if search_query:
    matches = ctx.menu_df[ctx.menu_df["name"].astype(str).str.contains(search_query, case=False, na=False)]
    st.caption(f'ผลการค้นหา "{search_query}" — พบ {len(matches)} รายการ')
    if len(matches):
        render_menu_grid(matches)
    else:
        st.info("ไม่พบเมนูที่ค้นหา ลองคำอื่นดูนะครับ", icon=":material/search_off:")
elif categories:
    pill_options = ["ทั้งหมด"] + categories
    selected = st.pills("หมวดหมู่", pill_options, default="ทั้งหมด",
                         required=True, label_visibility="collapsed")
    items = ctx.menu_df if selected == "ทั้งหมด" else ctx.menu_df[ctx.menu_df["category"] == selected]
    render_menu_grid(items)
else:
    st.info("ยังไม่มีเมนูในระบบ", icon=":material/info:")

if st.session_state.basket:
    with st.bottom:
        count = len(st.session_state.basket)
        total = sum(i["price"] for i in st.session_state.basket)
        with st.container(horizontal=True, vertical_alignment="center",
                           horizontal_alignment="distribute"):
            st.write(f":material/shopping_cart: **{count} รายการ** · {thb(total)}")
            if st.button("ดูตะกร้า", type="primary", icon=":material/arrow_forward:"):
                st.switch_page("app_pages/cart.py")
