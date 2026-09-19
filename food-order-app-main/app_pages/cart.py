"""Customer — cart / checkout page."""

import time
from collections import Counter

import streamlit as st

from app_lib import (
    clean_text, get_thai_time, load_shop_context, render_customer_topbar,
    require_customer_identity, save_order, send_email_notification,
    thb,
)

require_customer_identity()
ctx = load_shop_context()

render_customer_topbar(ctx, apply_queue_gate=True, show_cart_badge=False)

if st.button("เลือกเพิ่ม", icon=":material/arrow_back:"):
    st.switch_page("app_pages/menu.py")
st.subheader("ตะกร้าสินค้า", anchor=False, icon=":material/shopping_cart:")

if st.session_state.basket:
    counts = Counter(i["name"] for i in st.session_state.basket)
    uniq = {i["name"]: i for i in st.session_state.basket}
    total = 0
    for name, count in counts.items():
        item = uniq[name]
        subtotal = item["price"] * count
        total += subtotal
        with st.container(border=True, key=f"cart_item_{name}"):
            st.markdown(f"**{name}**")
            st.caption(f"{thb(item['price'])} x {count} = {thb(subtotal)}")
            with st.container(horizontal=True, gap="small", vertical_alignment="center"):
                if st.button("−", key=f"d_{name}", help="ลดจำนวน"):
                    for i, x in enumerate(st.session_state.basket):
                        if x["name"] == name:
                            del st.session_state.basket[i]
                            break
                    st.rerun()
                st.markdown(f"**{count}**")
                if st.button("+", key=f"i_{name}", help="เพิ่มจำนวน"):
                    st.session_state.basket.append(item)
                    st.rerun()

    st.subheader(f"รวม {thb(total)}", anchor=False)
    note = st.text_area("หมายเหตุถึงร้าน (ถ้ามี)", max_chars=200)
    blocked = ctx.is_queue_mode and not ctx.can_order
    if blocked:
        st.caption("ยังไม่ถึงคิวของคุณ จึงยังสั่งอาหารไม่ได้ในตอนนี้")
    if st.button("ยืนยันการสั่ง", type="primary", icon=":material/send:",
                  width="stretch", disabled=blocked):
        now = get_thai_time().strftime("%d/%m/%Y %H:%M")
        items_str = ", ".join(f"{n}(x{c})" for n, c in counts.items())
        save_order({
            "เวลา": now, "โต๊ะ": st.session_state.user_table,
            "ลูกค้า": st.session_state.user_name, "รายการอาหาร": items_str,
            "ยอดรวม": total, "หมายเหตุ": clean_text(note, 200), "สถานะ": "waiting",
        })
        send_email_notification(
            f"ออเดอร์ใหม่: {st.session_state.user_table}",
            f"Table: {st.session_state.user_table}\nItems: {items_str}\nTotal: {total}",
        )
        st.session_state.basket = []
        st.balloons()
        st.success("ส่งออเดอร์แล้ว ขอบคุณครับ", icon=":material/check_circle:")
        time.sleep(1.5)
        st.switch_page("app_pages/menu.py")
else:
    st.info("ตะกร้าว่าง", icon=":material/info:")
    if st.button("กลับไปเลือกเมนู", icon=":material/arrow_back:"):
        st.switch_page("app_pages/menu.py")
