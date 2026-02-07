import streamlit as st
import pandas as pd
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from datetime import datetime
import time
import pytz

# ================= 1. ตั้งค่าระบบ =================
SENDER_EMAIL = 'jaskaikai4@gmail.com'
SENDER_PASSWORD = 'zqyx nqdk ygww drpp'
RECEIVER_EMAIL = 'jaskaikai4@gmail.com'

ORDER_CSV = 'order_history.csv'
MENU_CSV = 'menu_data.csv'
TABLES_CSV = 'tables_data.csv'


# ================= 2. ฟังก์ชันจัดการข้อมูล =================

def load_menu():
    if not os.path.exists(MENU_CSV):
        default_data = [
            {"name": "หมูหมัก", "price": 120,
             "img": "https://images.unsplash.com/photo-1615937657715-bc7b4b7962c1?auto=format&fit=crop&w=500&q=60",
             "category": "Meat", "in_stock": True},
            {"name": "หมูสามชั้น", "price": 89,
             "img": "https://images.unsplash.com/photo-1600891964092-4316c288032e?auto=format&fit=crop&w=500&q=60",
             "category": "Meat", "in_stock": True},
            {"name": "กุ้งสด", "price": 150,
             "img": "https://images.unsplash.com/photo-1565680018434-b513d5e5fd47?auto=format&fit=crop&w=500&q=60",
             "category": "Seafood", "in_stock": True},
            {"name": "ผักกวางตุ้ง", "price": 40,
             "img": "https://images.unsplash.com/photo-1544025162-d76694265947?auto=format&fit=crop&w=500&q=60",
             "category": "Veggie", "in_stock": True},
        ]
        df = pd.DataFrame(default_data)
        df.to_csv(MENU_CSV, index=False)

    df = pd.read_csv(MENU_CSV)
    if 'in_stock' not in df.columns:
        df['in_stock'] = True
        df.to_csv(MENU_CSV, index=False)
    return df


def load_tables():
    if not os.path.exists(TABLES_CSV):
        default_tables = ["โต๊ะ 1", "โต๊ะ 2", "โต๊ะ 3", "โต๊ะ 4", "กลับบ้าน"]
        df = pd.DataFrame(default_tables, columns=["table_name"])
        df.to_csv(TABLES_CSV, index=False)
    return pd.read_csv(TABLES_CSV)


def load_orders():
    if not os.path.exists(ORDER_CSV):
        df = pd.DataFrame(columns=["เวลา", "โต๊ะ", "ลูกค้า", "รายการอาหาร", "ยอดรวม", "หมายเหตุ", "สถานะ"])
        df.to_csv(ORDER_CSV, index=False)
        return df

    df = pd.read_csv(ORDER_CSV)
    if 'สถานะ' not in df.columns:
        df['สถานะ'] = 'waiting'
        df.to_csv(ORDER_CSV, index=False)
    return df


def send_email_notification(subject, body):
    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL
    msg['To'] = RECEIVER_EMAIL
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        text = msg.as_string()
        server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, text)
        server.quit()
    except Exception as e:
        st.error(f"❌ ส่งอีเมลไม่สำเร็จ: {e}")


def save_order(data):
    df = load_orders()
    df_new = pd.DataFrame([data])
    if not os.path.exists(ORDER_CSV):
        df_new.to_csv(ORDER_CSV, index=False)
    else:
        df_new.to_csv(ORDER_CSV, mode='a', header=False, index=False)


def get_thai_time():
    tz = pytz.timezone('Asia/Bangkok')
    return datetime.now(tz)


# ================= 3. UI & CSS (Mobile Optimized) =================
st.set_page_config(page_title="Timnoi Shabu", page_icon="🍲", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;500;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Sarabun', sans-serif;
        background-color: #FDFBF7;
    }

    header, footer {visibility: hidden;}

    .stButton>button {
        border-radius: 8px;
        font-weight: bold;
        background-color: #8D6E63;
        color: white;
        border: none;
        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
    }
    .stButton>button:hover {
        background-color: #6D4C41;
        color: #FFECB3;
    }

    /* กล่องคิวสำหรับลูกค้า (Customer Queue Box) */
    .customer-queue-box {
        background: linear-gradient(135deg, #3E2723 0%, #5D4037 100%);
        color: white;
        padding: 20px;
        border-radius: 16px;
        text-align: center;
        margin-bottom: 20px;
        box-shadow: 0 8px 16px rgba(0,0,0,0.2);
        border: 2px solid #D7CCC8;
    }

    .queue-title {
        font-size: 18px;
        font-weight: bold;
        color: #FFECB3;
        margin-bottom: 5px;
        text-transform: uppercase;
    }

    .queue-big-number {
        font-size: 56px;
        font-weight: 800;
        line-height: 1;
        color: white;
        text-shadow: 2px 2px 0px #000;
        margin: 10px 0;
    }

    .queue-desc {
        font-size: 14px;
        color: #EFEFEF;
    }

    /* กล่องสถานะว่าง */
    .queue-empty {
        background-color: #E8F5E9;
        border: 2px dashed #4CAF50;
        color: #2E7D32;
        padding: 15px;
        border-radius: 12px;
        text-align: center;
        font-weight: bold;
    }

    .out-of-stock {
        filter: grayscale(100%);
        opacity: 0.6;
    }

    h1, h2, h3 { color: #3E2723 !important; }
</style>
""", unsafe_allow_html=True)

# ================= 4. โหลดข้อมูล & State =================
if 'basket' not in st.session_state:
    st.session_state.basket = []
if 'page' not in st.session_state:
    st.session_state.page = 'menu'
if 'app_mode' not in st.session_state:
    st.session_state.app_mode = 'customer'
if 'last_wrong_pass' not in st.session_state:
    st.session_state.last_wrong_pass = ""

menu_df = load_menu()
tables_df = load_tables()
orders_df = load_orders()

# นับคิว (ที่ยังไม่เสร็จ)
waiting_orders = orders_df[orders_df['สถานะ'] == 'waiting']
queue_count = len(waiting_orders)

# ================= 5. ส่วนหัวและเมนู (Top Navigation) =================

c_logo, c_name, c_menu = st.columns([0.8, 2, 0.5])

with c_logo:
    if os.path.exists("logo.png"):
        st.image("logo.png", width=80)
    else:
        st.markdown("<h1>🍲</h1>", unsafe_allow_html=True)

with c_name:
    st.markdown("""
        <div style="display: flex; align-items: center; height: 80px;">
            <h1 style='color:#3E2723; font-size:32px; margin:0;'>Timnoi</h1>
        </div>
    """, unsafe_allow_html=True)

with c_menu:
    st.write("")
    with st.popover("☰", use_container_width=True):
        st.markdown("### เมนูหลัก")
        if st.button("🏠 หน้าลูกค้า (สั่งอาหาร)", use_container_width=True):
            st.session_state.app_mode = 'customer'
            st.rerun()

        if st.button("⚙️ จัดการร้าน (Admin)", use_container_width=True):
            st.session_state.app_mode = 'admin_login'
            st.rerun()

        st.markdown("---")
        if st.button("🔄 รีเฟรชข้อมูล", use_container_width=True):
            st.rerun()

st.markdown("---")

# ================= 6. Controller เปลี่ยนหน้า =================

# === กรณี 1: หน้า Admin Login ===
if st.session_state.app_mode == 'admin_login':
    st.subheader("🔐 เข้าสู่ระบบหลังร้าน")
    if st.button("⬅️ กลับไปหน้าสั่งอาหาร"):
        st.session_state.app_mode = 'customer'
        st.rerun()
    password_input = st.text_input("🔑 ใส่รหัสผ่าน", type="password")
    if password_input == "090090op":
        st.success("รหัสถูกต้อง! ✅")
        time.sleep(0.5)
        st.session_state.app_mode = 'admin_dashboard'
        st.rerun()
    elif password_input:
        st.error("รหัสผิด! ❌")
        if st.session_state.last_wrong_pass != password_input:
            thai_now = get_thai_time().strftime('%d/%m/%Y %H:%M:%S')
            send_email_notification("🚨 Alert: รหัส Admin ผิด", f"เวลา: {thai_now}\nรหัสที่ใส่: {password_input}")
            st.session_state.last_wrong_pass = password_input

# === กรณี 2: หน้า Admin Dashboard ===
elif st.session_state.app_mode == 'admin_dashboard':
    st.subheader("⚙️ จัดการร้าน (Admin)")
    if st.button("🚪 ออกจากระบบ"):
        st.session_state.app_mode = 'customer'
        st.rerun()

    tab1, tab2, tab3 = st.tabs(["👨‍🍳 ครัว (KDS)", "🪑/📦 จัดการของ", "📝 เมนู"])

    with tab1:  # หน้าครัว
        st.info(f"🔥 ออเดอร์รอทำ: {queue_count} รายการ")
        if st.button("🔄 รีเฟรชออเดอร์ (ครัว)"): st.rerun()  # ปุ่มรีเฟรชสำหรับพ่อครัว

        if queue_count > 0:
            for index, row in waiting_orders.iterrows():
                with st.container(border=True):
                    c1, c2 = st.columns([3, 1])
                    with c1:
                        st.markdown(f"**{row['โต๊ะ']}** ({row['เวลา']})")
                        st.code(row['รายการอาหาร'], language="text")
                        if str(row['หมายเหตุ']) != 'nan': st.warning(f"Note: {row['หมายเหตุ']}")
                    with c2:
                        if st.button("✅ เสร็จ", key=f"done_{index}"):
                            orders_df.at[index, 'สถานะ'] = 'done'
                            orders_df.to_csv(ORDER_CSV, index=False)
                            st.rerun()
        else:
            st.success("ครัวว่างครับ!")

    with tab2:  # จัดการโต๊ะ/สต็อก
        st.write("#### 📦 จัดการสต็อก")
        edited_stock = st.data_editor(menu_df[['name', 'in_stock']], disabled=["name"], hide_index=True)
        if st.button("บันทึกสต็อก"):
            menu_df['in_stock'] = edited_stock['in_stock']
            menu_df.to_csv(MENU_CSV, index=False)
            st.toast("บันทึกแล้ว")

        st.write("#### 🪑 จัดการโต๊ะ")
        with st.form("add_tbl"):
            new_t = st.text_input("ชื่อโต๊ะใหม่")
            if st.form_submit_button("เพิ่ม"):
                if new_t:
                    new_r = pd.DataFrame([{"table_name": new_t}])
                    tables_df = pd.concat([tables_df, new_r], ignore_index=True)
                    tables_df.to_csv(TABLES_CSV, index=False)
                    st.rerun()
        del_t = st.selectbox("ลบโต๊ะ", ["-"] + tables_df['table_name'].tolist())
        if st.button("ลบโต๊ะ") and del_t != "-":
            tables_df = tables_df[tables_df['table_name'] != del_t]
            tables_df.to_csv(TABLES_CSV, index=False)
            st.rerun()

    with tab3:  # จัดการเมนู
        st.write("#### ➕ เพิ่มเมนู")
        with st.form("add_m"):
            n = st.text_input("ชื่อ")
            p = st.number_input("ราคา", min_value=0)
            c = st.selectbox("หมวด", ["Meat", "Seafood", "Veggie", "Snack"])
            i = st.text_input("รูป URL", "https://placehold.co/400")
            if st.form_submit_button("บันทึก"):
                if n:
                    nd = pd.DataFrame([{"name": n, "price": p, "img": i, "category": c, "in_stock": True}])
                    menu_df = pd.concat([menu_df, nd], ignore_index=True)
                    menu_df.to_csv(MENU_CSV, index=False)
                    st.rerun()
        st.write("#### ❌ ลบเมนู")
        del_m = st.selectbox("เลือกเมนูลบ", ["-"] + menu_df['name'].tolist())
        if st.button("ลบเมนู") and del_m != "-":
            menu_df = menu_df[menu_df['name'] != del_m]
            menu_df.to_csv(MENU_CSV, index=False)
            st.rerun()

# === กรณี 3: หน้าลูกค้า (Customer) ===
else:
    # ==========================================
    # 🔥 ส่วนแสดงคิวลูกค้า (อยู่บนสุด เด่นสุด) 🔥
    # ==========================================
    if queue_count > 0:
        st.markdown(f"""
        <div class="customer-queue-box">
            <div class="queue-title">🔥 คิวรออาหารตอนนี้</div>
            <div class="queue-big-number">{queue_count}</div>
            <div class="queue-desc">คิว</div>
            <p style="margin-top:10px; font-size:14px; opacity:0.9;">พนักงานกำลังเร่งมือทำอาหารให้อย่างสุดฝีมือครับ!</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="queue-empty">
            ✅ ครัวว่าง! สั่งปุ๊บ ได้ทานปั๊บ
        </div>
        """, unsafe_allow_html=True)

    # ปุ่มรีเฟรชเฉพาะคิว (สำคัญมาก เพื่อให้ลูกค้ากดดูค่าล่าสุด)
    col_ref1, col_ref2, col_ref3 = st.columns([1, 2, 1])
    with col_ref2:
        if st.button("🔄 เช็คคิวล่าสุด (Refresh)", use_container_width=True):
            st.rerun()

    st.markdown("---")

    # --- ส่วนเลือกโต๊ะ ---
    c_t, c_c = st.columns(2)
    with c_t:
        st.markdown("### 📍 เลือกโต๊ะ")
        tbls = tables_df['table_name'].tolist()
        if not tbls: tbls = ["โต๊ะ 1"]
        table_no = st.selectbox("table", tbls, label_visibility="collapsed")
    with c_c:
        st.markdown("### 👤 ชื่อลูกค้า")
        cust_name = st.text_input("cust", "ลูกค้าทั่วไป", label_visibility="collapsed")

    st.markdown("<br>", unsafe_allow_html=True)

    # --- ส่วนเลือกอาหาร ---
    if st.session_state.page == 'menu':
        st.subheader("📝 รายการอาหาร")
        cols = st.columns(2)
        for idx, row in menu_df.iterrows():
            with cols[idx % 2]:
                with st.container(border=True):
                    is_stock = row.get('in_stock', True)
                    try:
                        if is_stock:
                            st.image(row['img'], use_container_width=True)
                        else:
                            st.markdown(
                                f'<div style="opacity:0.5;filter:grayscale(100%);"><img src="{row["img"]}" style="width:100%;border-radius:8px;"></div>',
                                unsafe_allow_html=True)
                            st.markdown(
                                "<div style='text-align:center;color:red;font-weight:bold;margin-top:-60px;margin-bottom:40px;'>❌ หมด</div>",
                                unsafe_allow_html=True)
                    except:
                        st.image("https://placehold.co/400")

                    st.markdown(f"**{row['name']}**")
                    if is_stock:
                        st.caption(f"{row['price']}.-")
                        if st.button("ใส่ตะกร้า", key=f"add_{idx}", use_container_width=True):
                            st.session_state.basket.append(row.to_dict())
                            st.toast(f"เพิ่ม {row['name']}")
                    else:
                        st.button("หมด", key=f"no_{idx}", disabled=True)

        if len(st.session_state.basket) > 0:
            st.markdown("---")
            if st.button(f"🛒 สรุปยอด ({len(st.session_state.basket)} รายการ) ➡️", type="primary",
                         use_container_width=True):
                st.session_state.page = 'cart'
                st.rerun()

    # --- ส่วนสรุปตะกร้า ---
    elif st.session_state.page == 'cart':
        st.button("⬅️ เลือกอาหารเพิ่ม", on_click=lambda: st.session_state.update(page='menu'))
        st.info(f"สรุปรายการ: {table_no} | คุณ {cust_name}")

        if len(st.session_state.basket) > 0:
            total = sum([x['price'] for x in st.session_state.basket])
            df_b = pd.DataFrame(st.session_state.basket)
            summ = df_b['name'].value_counts().reset_index()
            summ.columns = ['รายการ', 'จำนวน']
            summ['ราคา'] = summ['รายการ'].apply(
                lambda x: menu_df[menu_df['name'] == x]['price'].values[0] * summ[summ['รายการ'] == x]['จำนวน'].values[
                    0])
            st.dataframe(summ, hide_index=True, use_container_width=True)
            st.markdown(f"### รวม: {total} บาท")
            note = st.text_area("หมายเหตุ")

            if st.button("✅ ยืนยันการสั่ง", type="primary", use_container_width=True):
                now_str = get_thai_time().strftime("%d/%m/%Y %H:%M")
                items = ", ".join([f"{r['รายการ']}(x{r['จำนวน']})" for i, r in summ.iterrows()])
                save_order(
                    {"เวลา": now_str, "โต๊ะ": table_no, "ลูกค้า": cust_name, "รายการอาหาร": items, "ยอดรวม": total,
                     "หมายเหตุ": note, "สถานะ": "waiting"})
                body = f"โต๊ะ: {table_no}\nลูกค้า: {cust_name}\nเวลา: {now_str}\n\n{items}\n\nรวม: {total} บาท\nNote: {note}"
                send_email_notification(f"🔔 Order: {table_no}", body)
                st.session_state.basket = []
                st.session_state.page = 'menu'
                st.balloons()
                st.success("ส่งออเดอร์แล้ว!")
                time.sleep(2)
                st.rerun()
        else:
            st.warning("ตะกร้าว่าง")