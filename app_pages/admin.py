"""Admin — password + OTP login, then the kitchen/sales/menu dashboard.

Both steps live on this one page (rather than a separate login page) since
the login flow is inherently sequential/session-bound — there's no reason
anyone would want to bookmark or link directly to "step 2 of admin login".
"""

import hmac
import os
import random
import time
from collections import Counter

import pandas as pd
import streamlit as st

from app_lib import (
    ADMIN_PASSWORD, ADMIN_READY, ALLOWED_IMAGE_EXT, BANNER_COUNT, EMAIL_READY,
    KITCHEN_LIMIT, LOGIN_LOG_CSV, MENU_CSV, OTP_MAX_ATTEMPTS, OTP_TTL_SECONDS,
    ORDER_CSV, PLACEHOLDER_IMG, TABLES_CSV, atomic_write_csv, clean_text,
    delete_feedback_entry, find_banner_path, get_thai_time, load_login_log,
    load_menu, load_orders, load_shop_context, load_tables, save_contacts,
    save_image, save_login_log, save_promo_banner, send_email_notification,
    thb, trigger_global_refresh,
)

ctx = load_shop_context()

# ============================================================================
# Login
# ============================================================================
if not st.session_state.admin_authenticated:
    st.subheader("เข้าสู่ระบบหลังร้าน", anchor=False, icon=":material/lock:")
    if st.button("กลับ", icon=":material/arrow_back:"):
        st.switch_page("app_pages/menu.py")

    if not ADMIN_READY:
        st.error(
            "ยังไม่ได้ตั้งค่ารหัสผ่านแอดมิน กรุณาสร้างไฟล์ .streamlit/secrets.toml "
            "จากตัวอย่างใน .streamlit/secrets.toml.example",
            icon=":material/error:",
        )
        st.stop()
    if not EMAIL_READY:
        st.warning(
            "ยังไม่ได้ตั้งค่าอีเมลระบบใน .streamlit/secrets.toml ระบบจะไม่สามารถส่งรหัส OTP "
            "ยืนยันตัวตนได้ จึงปิดการเข้าสู่ระบบแอดมินไว้ก่อนเพื่อความปลอดภัย",
            icon=":material/mail:",
        )
        st.stop()

    if st.session_state.login_phase == 1:
        with st.container(border=True):
            st.caption("ขั้นตอนที่ 1 จาก 2 — ยืนยันรหัสผ่าน")
            admin_device = st.text_input("ผู้ใช้งาน (ชื่อเล่น)", placeholder="ระบุชื่อผู้ใช้งาน...")
            password_input = st.text_input("รหัสผ่าน", type="password")

        if st.button("ขอเข้าสู่ระบบ", type="primary", icon=":material/login:"):
            if not password_input:
                st.error("กรุณาใส่รหัสผ่าน")
            elif hmac.compare_digest(password_input, ADMIN_PASSWORD):
                st.session_state.login_fail_count = 0
                otp_code = str(random.randint(100000, 999999))
                declared_name = admin_device if admin_device else "ไม่ระบุชื่อ"
                thai_now = get_thai_time().strftime("%d/%m/%Y %H:%M:%S")

                st.session_state.login_otp_ref = otp_code
                st.session_state.login_otp_expires = time.time() + OTP_TTL_SECONDS
                st.session_state.login_otp_attempts = 0
                st.session_state.login_temp_name = declared_name

                sent = send_email_notification(
                    f"คำขอเข้าใช้งาน Admin: {declared_name}",
                    f"OTP: {otp_code}\nUser: {declared_name}\nTime: {thai_now}",
                )
                if sent:
                    st.session_state.login_phase = 2
                    st.rerun()
                else:
                    st.error("ส่ง OTP ไม่สำเร็จ กรุณาลองใหม่อีกครั้ง", icon=":material/error:")
            else:
                st.session_state.login_fail_count += 1
                st.error("รหัสผ่านผิด", icon=":material/error:")
                save_login_log(admin_device, "Failed (Wrong Pass)")
                time.sleep(min(st.session_state.login_fail_count, 5))

    elif st.session_state.login_phase == 2:
        with st.container(border=True):
            st.caption("ขั้นตอนที่ 2 จาก 2 — ยืนยัน OTP")
            st.write(f"ส่งรหัส OTP ไปยังอีเมลเจ้าของร้านแล้ว สำหรับผู้ขอเข้าใช้: "
                     f"**{st.session_state.login_temp_name}**")
            remaining = max(0, int(st.session_state.login_otp_expires - time.time()))
            st.caption(f"รหัสจะหมดอายุใน {remaining // 60} นาที {remaining % 60} วินาที")
            otp_input = st.text_input("รหัส OTP 6 หลัก", max_chars=6)
            with st.container(horizontal=True):
                confirm = st.button("ยืนยัน", type="primary", icon=":material/check:", width="stretch")
                cancel = st.button("ยกเลิก", icon=":material/close:", width="stretch")

            if cancel:
                st.session_state.login_phase = 1
                st.rerun()

            if confirm:
                if time.time() > st.session_state.login_otp_expires:
                    st.error("OTP หมดอายุแล้ว กรุณาขอรหัสใหม่", icon=":material/schedule:")
                    st.session_state.login_phase = 1
                elif st.session_state.login_otp_attempts >= OTP_MAX_ATTEMPTS:
                    st.error("กรอกผิดเกินจำนวนที่กำหนด กรุณาขอรหัสใหม่", icon=":material/block:")
                    save_login_log(st.session_state.login_temp_name, "Failed (OTP Locked)")
                    st.session_state.login_phase = 1
                elif otp_input and hmac.compare_digest(otp_input, st.session_state.login_otp_ref):
                    save_login_log(st.session_state.login_temp_name, "Success (OTP Verified)")
                    st.success("สำเร็จ", icon=":material/check_circle:")
                    time.sleep(0.8)
                    st.session_state.admin_authenticated = True
                    st.session_state.login_phase = 1
                    st.rerun()
                else:
                    st.session_state.login_otp_attempts += 1
                    left = OTP_MAX_ATTEMPTS - st.session_state.login_otp_attempts
                    st.error(f"OTP ไม่ถูกต้อง (เหลือ {left} ครั้ง)", icon=":material/error:")

    st.stop()

# ============================================================================
# Dashboard
# ============================================================================
menu_df, tables_df, orders_df, contact_info = ctx.menu_df, ctx.tables_df, ctx.orders_df, ctx.contact_info
busy_tables, feedback_df = ctx.busy_tables, ctx.feedback_df

st.subheader("จัดการร้าน", anchor=False, icon=":material/settings:")
with st.container(horizontal=True):
    if st.button("ออกจากระบบ", icon=":material/logout:"):
        st.session_state.admin_authenticated = False
        st.switch_page("app_pages/menu.py")
    if st.button("รีเฟรชทุกอุปกรณ์", type="primary", icon=":material/sync:"):
        trigger_global_refresh()
        st.toast("ส่งคำสั่งรีเฟรชแล้ว", icon=":material/sync:")

tab_kitchen, tab_promo, tab_stock, tab_menu, tab_sales, tab_contact, tab_reviews, tab_log = st.tabs(
    ["ครัว", "โปรโมชั่น", "สต็อก/โต๊ะ", "เมนู", "ยอดขาย", "ติดต่อ", "รีวิว", "ประวัติล็อกอิน"],
)

# ---- ครัว -------------------------------------------------------------
with tab_kitchen:
    @st.dialog("ยกเลิกออเดอร์นี้?")
    def confirm_cancel_order(order_index, table_name):
        st.write(f"ยืนยันยกเลิกออเดอร์ของ **{table_name}** ใช่หรือไม่? การกระทำนี้ย้อนกลับไม่ได้")
        with st.container(horizontal=True):
            if st.button("ยกเลิกออเดอร์", type="primary", icon=":material/delete:"):
                fresh = load_orders()
                fresh.at[order_index, "สถานะ"] = "cancelled"
                atomic_write_csv(fresh, ORDER_CSV)
                trigger_global_refresh()
                st.toast("ยกเลิกออเดอร์แล้ว", icon=":material/delete:")
                st.rerun()
            if st.button("ปิด"):
                st.rerun()

    @st.fragment(run_every="5s")
    def kitchen_board():
        live_orders = load_orders()
        live_waiting = live_orders[live_orders["สถานะ"] == "waiting"]
        load_now = len(live_waiting)

        with st.container(horizontal=True):
            st.metric("ออเดอร์ค้าง", f"{load_now}/{KITCHEN_LIMIT}", border=True)
            st.metric("สถานะครัว", "แน่น" if load_now >= KITCHEN_LIMIT else "ปกติ", border=True)
        st.progress(min(load_now / KITCHEN_LIMIT, 1.0))

        if load_now == 0:
            st.success("ไม่มีออเดอร์ค้าง", icon=":material/check_circle:")
            return

        for index, row in live_waiting.iterrows():
            with st.container(border=True):
                c1, c2 = st.columns([3, 1])
                with c1:
                    st.markdown(f"**{row['โต๊ะ']}** · {row['เวลา']}")
                    st.caption(f"ลูกค้า: {row['ลูกค้า']}")
                    st.write(thb(row["ยอดรวม"]))
                    with st.expander("รายการอาหาร", icon=":material/list_alt:"):
                        st.code(str(row["รายการอาหาร"]), language="text")
                    note = str(row["หมายเหตุ"])
                    if note not in ("nan", ""):
                        st.warning(note, icon=":material/sticky_note_2:")
                with c2:
                    if st.button("รับเงิน", key=f"pay_{index}", type="primary",
                                  icon=":material/payments:", width="stretch"):
                        fresh = load_orders()
                        fresh.at[index, "สถานะ"] = "paid"
                        atomic_write_csv(fresh, ORDER_CSV)
                        trigger_global_refresh()
                        st.toast("รับเงินเรียบร้อย", icon=":material/check_circle:")
                        st.rerun(scope="fragment")
                    if st.button("ยกเลิก", key=f"cncl_{index}", icon=":material/cancel:",
                                  width="stretch"):
                        confirm_cancel_order(index, row["โต๊ะ"])

    kitchen_board()

# ---- โปรโมชั่น ----------------------------------------------------------
with tab_promo:
    st.write("อัปโหลดรูปแบนเนอร์โปรโมชั่น (สูงสุด 5 รูป) ระบบจะสลับแสดงให้ลูกค้าเห็นอัตโนมัติ")

    @st.dialog("ลบแบนเนอร์นี้?")
    def confirm_delete_banner(path):
        st.write("ยืนยันลบรูปแบนเนอร์นี้ใช่หรือไม่?")
        with st.container(horizontal=True):
            if st.button("ลบ", type="primary", icon=":material/delete:"):
                os.remove(path)
                trigger_global_refresh()
                st.rerun()
            if st.button("ปิด"):
                st.rerun()

    for i in range(1, BANNER_COUNT + 1):
        c1, c2 = st.columns([2, 1])
        with c1:
            uploaded = st.file_uploader(f"รูปที่ {i}", type=sorted(ALLOWED_IMAGE_EXT), key=f"ban_up_{i}")
            if uploaded and save_promo_banner(uploaded, i):
                st.rerun()
        with c2:
            fp = find_banner_path(i)
            if fp:
                st.image(fp, width="stretch")
                if st.button("ลบ", key=f"del_ban_{i}", icon=":material/delete:"):
                    confirm_delete_banner(fp)

# ---- สต็อก/โต๊ะ ---------------------------------------------------------
with tab_stock:
    st.write("#### สต็อกสินค้า")
    edited = st.data_editor(
        menu_df[["name", "category", "price", "in_stock"]],
        disabled=["name", "category", "price"],
        hide_index=True,
        column_config={
            "name": "เมนู",
            "category": "หมวดหมู่",
            "price": st.column_config.NumberColumn("ราคา", format="%d ฿"),
            "in_stock": st.column_config.CheckboxColumn("มีสินค้า"),
        },
    )
    if st.button("บันทึกสต็อก", icon=":material/save:"):
        fresh = load_menu()
        fresh["in_stock"] = edited["in_stock"].values
        atomic_write_csv(fresh, MENU_CSV)
        st.toast("บันทึกสต็อกแล้ว", icon=":material/check_circle:")

    st.write("#### จัดการโต๊ะ")
    with st.form("add_tbl", border=False):
        new_t = st.text_input("ชื่อโต๊ะใหม่")
        is_shared_new = st.checkbox("โต๊ะนี้ไม่จำกัดจำนวนคนพร้อมกัน (เช่น กลับบ้าน/ซื้อกลับ)")
        if st.form_submit_button("เพิ่มโต๊ะ", icon=":material/add:"):
            new_t = clean_text(new_t, 40)
            if new_t and new_t not in tables_df["table_name"].astype(str).tolist():
                new_row = pd.DataFrame([{"table_name": new_t, "is_shared": is_shared_new}])
                atomic_write_csv(pd.concat([tables_df, new_row], ignore_index=True), TABLES_CSV)
                trigger_global_refresh()
                st.rerun()
            else:
                st.error("กรุณาใส่ชื่อโต๊ะที่ยังไม่มีอยู่")

    @st.dialog("ลบโต๊ะนี้?")
    def confirm_delete_table(table_name):
        st.write(f"ยืนยันลบ **{table_name}** ใช่หรือไม่?")
        if table_name in busy_tables:
            st.warning("โต๊ะนี้กำลังมีออเดอร์ค้างอยู่ — ลบแล้วออเดอร์เดิมจะยังอยู่ในระบบแต่โต๊ะจะหายจากรายการ",
                       icon=":material/warning:")
        with st.container(horizontal=True):
            if st.button("ลบโต๊ะ", type="primary", icon=":material/delete:"):
                fresh = load_tables()
                atomic_write_csv(fresh[fresh["table_name"] != table_name], TABLES_CSV)
                trigger_global_refresh()
                st.rerun()
            if st.button("ปิด"):
                st.rerun()

    del_t = st.selectbox("เลือกโต๊ะที่ต้องการลบ", ["-"] + tables_df["table_name"].tolist())
    if st.button("ลบโต๊ะ", icon=":material/delete:") and del_t != "-":
        confirm_delete_table(del_t)

# ---- เมนู ---------------------------------------------------------------
with tab_menu:
    st.write("#### เพิ่มเมนูใหม่")
    with st.form("add_m", border=False):
        n = st.text_input("ชื่อเมนู")
        p = st.number_input("ราคา", min_value=0, step=5)
        c = st.selectbox("หมวดหมู่", ["เนื้อสัตว์ (Meat)", "อาหารทะเล (Seafood)", "ผัก (Veggie)",
                                      "ของทานเล่น (Snack)", "เครื่องดื่ม (Drinks)", "อื่นๆ (Others)"])
        up_file = st.file_uploader("อัปโหลดรูป", type=sorted(ALLOWED_IMAGE_EXT))
        url_img = st.text_input("หรือใส่ URL รูปภาพ", PLACEHOLDER_IMG)
        if st.form_submit_button("บันทึกเมนู", icon=":material/save:"):
            n = clean_text(n, 60)
            if n:
                final_path = save_image(up_file) if up_file else url_img
                new_m = pd.DataFrame([{"name": n, "price": p, "img": final_path,
                                        "category": c, "in_stock": True}])
                atomic_write_csv(pd.concat([load_menu(), new_m], ignore_index=True), MENU_CSV)
                st.rerun()
            else:
                st.error("กรุณาใส่ชื่อเมนู")

    st.write("#### ลบเมนู")
    menu_names = menu_df["name"].tolist()
    dupes = [n for n, count in Counter(menu_names).items() if count > 1]

    @st.dialog("ลบเมนูนี้?")
    def confirm_delete_menu(item_name, has_dupe):
        st.write(f"ยืนยันลบ **{item_name}** ใช่หรือไม่?")
        if has_dupe:
            st.warning("มีเมนูชื่อนี้มากกว่า 1 รายการ — จะลบทั้งหมดที่ชื่อตรงกัน", icon=":material/warning:")
        with st.container(horizontal=True):
            if st.button("ลบเมนู", type="primary", icon=":material/delete:"):
                fresh = load_menu()
                atomic_write_csv(fresh[fresh["name"] != item_name], MENU_CSV)
                st.rerun()
            if st.button("ปิด"):
                st.rerun()

    del_m = st.selectbox("เลือกเมนู", ["-"] + menu_names)
    if st.button("ลบเมนู", icon=":material/delete:") and del_m != "-":
        confirm_delete_menu(del_m, del_m in dupes)

# ---- ยอดขาย -------------------------------------------------------------
with tab_sales:
    today_date = get_thai_time().date()
    orders_df["ยอดรวม"] = pd.to_numeric(orders_df["ยอดรวม"], errors="coerce").fillna(0)
    paid = orders_df[orders_df["สถานะ"] == "paid"].copy()
    paid["_dt"] = pd.to_datetime(paid["เวลา"], format="%d/%m/%Y %H:%M", errors="coerce")
    daily = paid[paid["_dt"].dt.date == today_date]

    with st.container(horizontal=True):
        st.metric("ยอดขายวันนี้", thb(daily["ยอดรวม"].sum()), border=True)
        st.metric("จำนวนออเดอร์วันนี้", len(daily), border=True)
        avg = daily["ยอดรวม"].mean() if len(daily) else 0
        st.metric("ยอดเฉลี่ย/ออเดอร์", thb(avg), border=True)

    st.caption(f"วันที่ {today_date.strftime('%d/%m/%Y')}")
    st.dataframe(daily[["เวลา", "โต๊ะ", "ลูกค้า", "ยอดรวม"]], hide_index=True, width="stretch")

    last7 = pd.date_range(end=today_date, periods=7).date
    trend = paid.dropna(subset=["_dt"]).groupby(paid["_dt"].dt.date)["ยอดรวม"].sum()
    trend = trend.reindex(last7, fill_value=0)
    trend_df = pd.DataFrame({"วันที่": [d.strftime("%d/%m") for d in last7],
                              "ยอดขาย": trend.values.astype(int)})
    st.write("#### ยอดขายย้อนหลัง 7 วัน")
    st.bar_chart(trend_df, x="วันที่", y="ยอดขาย")

# ---- ติดต่อ -------------------------------------------------------------
with tab_contact:
    st.subheader("ข้อมูลติดต่อ", anchor=False, icon=":material/contact_phone:")
    with st.form("contact", border=False):
        np_ = st.text_input("เบอร์โทร", contact_info.get("phone", ""))
        nl = st.text_input("LINE", contact_info.get("line", ""))
        nf = st.text_input("Facebook URL", contact_info.get("facebook", ""))
        ni = st.text_input("Instagram URL", contact_info.get("instagram", ""))
        if st.form_submit_button("บันทึก", icon=":material/save:"):
            save_contacts({"phone": clean_text(np_, 30), "line": clean_text(nl, 40),
                            "facebook": clean_text(nf, 200), "instagram": clean_text(ni, 200)})
            trigger_global_refresh()
            st.toast("บันทึกข้อมูลติดต่อแล้ว", icon=":material/check_circle:")
            st.rerun()

# ---- รีวิว --------------------------------------------------------------
with tab_reviews:
    st.subheader("ความคิดเห็นจากลูกค้า", anchor=False, icon=":material/rate_review:")

    @st.dialog("ลบความคิดเห็นนี้?")
    def confirm_delete_feedback(idx):
        st.write("ยืนยันลบความคิดเห็นนี้ใช่หรือไม่?")
        with st.container(horizontal=True):
            if st.button("ลบ", type="primary", icon=":material/delete:"):
                delete_feedback_entry(idx)
                st.rerun()
            if st.button("ปิด"):
                st.rerun()

    if feedback_df.empty:
        st.caption("ยังไม่มีความคิดเห็น")
    for i, r in feedback_df[::-1].iterrows():
        with st.container(border=True):
            st.markdown(f"**{r['customer_name']}** · {r.get('timestamp', '')}")
            st.write(r["message"])
            if st.button("ลบ", key=f"dfb_{i}", icon=":material/delete:"):
                confirm_delete_feedback(i)

# ---- ประวัติล็อกอิน -------------------------------------------------------
with tab_log:
    st.subheader("ประวัติการเข้าสู่ระบบ", anchor=False, icon=":material/history:")
    st.dataframe(load_login_log()[::-1], hide_index=True, width="stretch")

    @st.dialog("ล้างประวัติล็อกอินทั้งหมด?")
    def confirm_clear_log():
        st.write("ยืนยันล้างประวัติการเข้าสู่ระบบทั้งหมดใช่หรือไม่? การกระทำนี้ย้อนกลับไม่ได้")
        with st.container(horizontal=True):
            if st.button("ล้างประวัติ", type="primary", icon=":material/delete_forever:"):
                atomic_write_csv(
                    pd.DataFrame(columns=["timestamp", "declared_name", "status"]), LOGIN_LOG_CSV
                )
                st.rerun()
            if st.button("ปิด"):
                st.rerun()

    if st.button("ล้างประวัติ", icon=":material/delete_forever:"):
        confirm_clear_log()
