import streamlit as st
import pandas as pd
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from datetime import datetime
import time
import pytz

# ================= 1. ตั้งค่าระบบ (EMAIL) =================
SENDER_EMAIL = 'jaskaikai4@gmail.com'
SENDER_PASSWORD = 'zqyx nqdk ygww drpp'
RECEIVER_EMAIL = 'jaskaikai4@gmail.com'

# ชื่อไฟล์เก็บข้อมูล
ORDER_CSV = 'order_history.csv'
MENU_CSV = 'menu_data.csv'
TABLES_CSV = 'tables_data.csv'  # <--- ไฟล์เก็บรายชื่อโต๊ะ (ใหม่)


# ================= 2. ฟังก์ชันจัดการข้อมูล (Backend) =================

def load_menu():
    # ถ้ายังไม่มีไฟล์เมนู ให้สร้างใหม่
    if not os.path.exists(MENU_CSV):
        default_data = [
            {"name": "หมูหมัก (Marinated Pork)", "price": 120,
             "img": "https://images.unsplash.com/photo-1615937657715-bc7b4b7962c1?auto=format&fit=crop&w=500&q=60",
             "category": "Meat", "in_stock": True},
            {"name": "หมูสามชั้น (Pork Belly)", "price": 89,
             "img": "https://images.unsplash.com/photo-1600891964092-4316c288032e?auto=format&fit=crop&w=500&q=60",
             "category": "Meat", "in_stock": True},
            {"name": "กุ้งสด (Fresh Shrimp)", "price": 150,
             "img": "https://images.unsplash.com/photo-1565680018434-b513d5e5fd47?auto=format&fit=crop&w=500&q=60",
             "category": "Seafood", "in_stock": True},
            {"name": "ผักกวางตุ้ง (Bok Choy)", "price": 40,
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


# ฟังก์ชันโหลดรายชื่อโต๊ะ (ใหม่)
def load_tables():
    if not os.path.exists(TABLES_CSV):
        # สร้างรายชื่อโต๊ะเริ่มต้น (ภาษาไทย)
        default_tables = ["โต๊ะ 1", "โต๊ะ 2", "โต๊ะ 3", "โต๊ะ 4", "กลับบ้าน"]
        df = pd.DataFrame(default_tables, columns=["table_name"])
        df.to_csv(TABLES_CSV, index=False)
    return pd.read_csv(TABLES_CSV)


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
    if not os.path.exists(ORDER_CSV):
        df = pd.DataFrame(columns=["เวลา", "โต๊ะ", "ลูกค้า", "รายการอาหาร", "ยอดรวม", "หมายเหตุ"])
        df.to_csv(ORDER_CSV, index=False)
    df_new = pd.DataFrame([data])
    df_new.to_csv(ORDER_CSV, mode='a', header=False, index=False)


def get_thai_time():
    tz = pytz.timezone('Asia/Bangkok')
    return datetime.now(tz)


# ================= 3. ตั้งค่าหน้าจอ (UI & CSS) =================
st.set_page_config(page_title="Timnoi Shabu", page_icon="🍲", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Kanit:wght@300;500;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Kanit', sans-serif;
    }

    header {visibility: hidden;}
    footer {visibility: hidden;}

    .stButton>button {
        border-radius: 10px;
        font-weight: bold;
    }

    /* สไตล์สำหรับของหมด */
    .out-of-stock {
        filter: grayscale(100%);
        opacity: 0.6;
    }
</style>
""", unsafe_allow_html=True)

# ================= 4. โหลดข้อมูล =================
if 'basket' not in st.session_state:
    st.session_state.basket = []
if 'page' not in st.session_state:
    st.session_state.page = 'menu'
if 'last_wrong_pass' not in st.session_state:
    st.session_state.last_wrong_pass = ""

menu_df = load_menu()
tables_df = load_tables()  # โหลดข้อมูลโต๊ะ

# ================= 5. ส่วนจัดการ (Admin Sidebar) =================
with st.sidebar:
    st.header("⚙️ จัดการร้าน (Admin)")
    admin_mode = st.checkbox("เข้าสู่โหมดผู้ดูแลระบบ")

    if admin_mode:
        st.markdown("---")
        password_input = st.text_input("🔑 ใส่รหัสผ่านเพื่อแก้ไข", type="password")

        if password_input == "090090op":
            st.success("รหัสถูกต้อง! ✅")
            st.session_state.last_wrong_pass = ""

            # === 1. จัดการโต๊ะ (NEW) ===
            st.subheader("🪑 จัดการโต๊ะ (Tables)")

            # เพิ่มโต๊ะใหม่
            with st.form("add_table_form"):
                new_table_name = st.text_input("ชื่อโต๊ะใหม่ (เช่น โต๊ะ 5, โต๊ะ VIP)")
                if st.form_submit_button("เพิ่มโต๊ะ"):
                    if new_table_name:
                        # เช็คว่ามีชื่อซ้ำไหม
                        if new_table_name not in tables_df['table_name'].values:
                            new_row = pd.DataFrame([{"table_name": new_table_name}])
                            tables_df = pd.concat([tables_df, new_row], ignore_index=True)
                            tables_df.to_csv(TABLES_CSV, index=False)
                            st.success(f"เพิ่ม '{new_table_name}' เรียบร้อย!")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.warning("ชื่อโต๊ะนี้มีอยู่แล้ว")

            # ลบโต๊ะ
            table_to_delete = st.selectbox("เลือกโต๊ะที่จะลบ", ["-เลือก-"] + tables_df['table_name'].tolist())
            if st.button("ยืนยันลบโต๊ะ") and table_to_delete != "-เลือก-":
                tables_df = tables_df[tables_df['table_name'] != table_to_delete]
                tables_df.to_csv(TABLES_CSV, index=False)
                st.success(f"ลบ {table_to_delete} เรียบร้อย!")
                time.sleep(1)
                st.rerun()

            st.markdown("---")

            # === 2. จัดการสต็อก ===
            st.subheader("📦 จัดการสต็อก (Stock)")
            st.info("ติ๊กถูก = มีของ | ไม่ติ๊ก = ของหมด")

            edited_df = st.data_editor(
                menu_df[['name', 'in_stock']],
                column_config={
                    "name": "ชื่อเมนู",
                    "in_stock": st.column_config.CheckboxColumn("สถานะสินค้า", default=True)
                },
                disabled=["name"],
                hide_index=True,
                key="stock_editor"
            )

            if st.button("บันทึกสถานะสต็อก"):
                menu_df['in_stock'] = edited_df['in_stock']
                menu_df.to_csv(MENU_CSV, index=False)
                st.toast("อัปเดตสต็อกเรียบร้อย!", icon="💾")
                time.sleep(1)
                st.rerun()

            st.markdown("---")

            # === 3. จัดการเมนู (เพิ่ม/ลบ) ===
            st.subheader("❌ ลบเมนู")
            item_to_delete = st.selectbox("เลือกเมนูที่จะลบ", ["-เลือก-"] + menu_df['name'].tolist())
            if st.button("ยืนยันลบเมนู") and item_to_delete != "-เลือก-":
                menu_df = menu_df[menu_df['name'] != item_to_delete]
                menu_df.to_csv(MENU_CSV, index=False)
                st.success(f"ลบ {item_to_delete} เรียบร้อย!")
                time.sleep(1)
                st.rerun()

            st.subheader("➕ เพิ่มเมนูใหม่")
            with st.form("add_menu_form"):
                new_