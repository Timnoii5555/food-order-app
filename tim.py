import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from datetime import datetime
import time
import pytz
from collections import Counter
import base64

# ================= 1. ตั้งค่าระบบ =================
ORDER_CSV = 'order_history.csv'
MENU_CSV = 'menu_data.csv'
TABLES_CSV = 'tables_data.csv'
CONTACT_CSV = 'contact_data.csv'
QUEUE_CSV = 'queue_data.csv'
FEEDBACK_CSV = 'feedback_data.csv'
BANNER_FOLDER = 'banner_images'

KITCHEN_LIMIT = 10  # ระบบคิวจะเริ่มทำงานเมื่อออเดอร์ค้างถึง 10

if not os.path.exists(BANNER_FOLDER): os.makedirs(BANNER_FOLDER)


# ================= 2. ฟังก์ชันจัดการข้อมูล =================

def get_thai_time():
    tz = pytz.timezone('Asia/Bangkok')
    return datetime.now(tz)


def load_orders():
    cols = ["เวลา", "โต๊ะ", "ลูกค้า", "รายการอาหาร", "ยอดรวม", "หมายเหตุ", "สถานะ"]
    if not os.path.exists(ORDER_CSV):
        pd.DataFrame(columns=cols).to_csv(ORDER_CSV, index=False)
    try:
        df = pd.read_csv(ORDER_CSV)
        if list(df.columns) != cols: return pd.DataFrame(columns=cols)
        return df
    except:
        return pd.DataFrame(columns=cols)


def load_queue():
    if not os.path.exists(QUEUE_CSV):
        pd.DataFrame(columns=["queue_id", "customer_name", "timestamp"]).to_csv(QUEUE_CSV, index=False)
    return pd.read_csv(QUEUE_CSV)


def add_to_queue(name):
    df = load_queue()
    if not df.empty and name in df['customer_name'].values:
        return df[df['customer_name'] == name].iloc[0]['queue_id']
    last_id = 100
    if not df.empty:
        try:
            last_id = int(str(df.iloc[-1]['queue_id']).split('-')[1])
        except:
            pass
    new_id = f"Q-{last_id + 1}"
    new_data = {"queue_id": new_id, "customer_name": name, "timestamp": get_thai_time().strftime("%Y-%m-%d %H:%M:%S")}
    pd.concat([df, pd.DataFrame([new_data])], ignore_index=True).to_csv(QUEUE_CSV, index=False)
    return new_id


def pop_queue():
    df = load_queue()
    if not df.empty:
        df.iloc[1:].to_csv(QUEUE_CSV, index=False)


def save_order(data):
    df = load_orders()
    mask = (df['โต๊ะ'] == data['โต๊ะ']) & (df['สถานะ'] == 'waiting')
    if mask.any():
        idx = df.index[mask][0]
        # ทบรายการอาหารและราคา
        df.at[idx, 'รายการอาหาร'] = f"{df.at[idx, 'รายการอาหาร']}, {data['รายการอาหาร']}"
        try:
            old_p = float(df.at[idx, 'ยอดรวม'])
        except:
            old_p = 0.0
        df.at[idx, 'ยอดรวม'] = old_p + float(data['ยอดรวม'])
        df.to_csv(ORDER_CSV, index=False)
        return "merged"
    else:
        pd.concat([df, pd.DataFrame([data])], ignore_index=True).to_csv(ORDER_CSV, index=False)
        return "new"


def get_image_base64(path):
    with open(path, "rb") as f: return f"data:image/png;base64,{base64.b64encode(f.read()).decode()}"


# ================= 3. UI & CSS =================
st.set_page_config(page_title="TimNoi Shabu", page_icon="🍲", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;500;700&display=swap');
    html, body, [class*="css"] { font-family: 'Sarabun', sans-serif; background-color: #FDFBF7; }
    .stButton>button { border-radius: 8px; font-weight: bold; background-color: #8D6E63; color: white; border: none; height: 50px; }
    .stButton>button:hover { background-color: #6D4C41; color: #FFECB3; }
    .queue-box { background: linear-gradient(135deg, #3E2723 0%, #5D4037 100%); color: white; padding: 30px; border-radius: 20px; text-align: center; margin-bottom: 20px; }
</style>
""", unsafe_allow_html=True)

# ================= 4. โหลดข้อมูล & State =================
if 'page' not in st.session_state: st.session_state.page = 'menu'
if 'app_mode' not in st.session_state: st.session_state.app_mode = 'customer'
if 'my_queue_id' not in st.session_state: st.session_state.my_queue_id = None
if 'basket' not in st.session_state: st.session_state.basket = []

orders_df = load_orders()
waiting_orders = orders_df[orders_df['สถานะ'] == 'waiting']
kitchen_load = len(waiting_orders)
queue_df = load_queue()

# ================= 5. ส่วนหัว (Header) =================
c_logo, c_name, c_menu = st.columns([1.3, 2, 0.5])
with c_logo:
    if os.path.exists("logo.png"): st.image("logo.png", width=320)
with c_name:
    st.markdown(f"""
        <div style="display: flex; flex-direction: column; justify-content: center; height: 220px;">
            <h1 style='color:#3E2723; font-size:50px; margin:0;'>TimNoi Shabu</h1>
            <p style='color:#8D6E63; font-size:20px; font-weight:bold;'>ร้านนี้ไม่มีหมูเพราะที่เห็นเป็นเนื้อหมา</p>
            <div style='margin-top:15px; border-top: 2px solid #D7CCC8; padding-top:10px;'>
                <p style='color:#5D4037; font-size:16px; margin:0;'>🕒 เปิดบริการ: 00:00 - 23:59 น.</p>
                <p style='color:#5D4037; font-size:16px; margin:0;'>📞 โทร: 064-448-55549</p>
            </div>
        </div>
    """, unsafe_allow_html=True)
with c_menu:
    with st.popover("☰"):
        if st.button("🏠 หน้าลูกค้า", use_container_width=True): st.session_state.app_mode = 'customer'; st.rerun()
        if st.button("⚙️ จัดการร้าน", use_container_width=True): st.session_state.app_mode = 'admin_login'; st.rerun()

st.divider()

# ================= 6. Controller =================

if st.session_state.app_mode == 'admin_login':
    pw = st.text_input("รหัสผ่าน", type="password")
    if pw == "090090op": st.session_state.app_mode = 'admin_dashboard'; st.rerun()

elif st.session_state.app_mode == 'admin_dashboard':
    tabs = st.tabs(["👨‍🍳 ครัว (Auto)", "📦 สต็อก", "📝 เมนู", "📊 ยอดขาย", "💬 รีวิว"])

    with tabs[0]:  # หน้าครัว รีเฟรชทุก 10 วิ
        st.markdown(f"**สถานะครัว: {kitchen_load}/{KITCHEN_LIMIT}**")
        if kitchen_load > 0:
            for idx, row in waiting_orders.iterrows():
                with st.container(border=True):
                    c1, c2 = st.columns([3, 1])
                    with c1:
                        st.write(f"**{row['โต๊ะ']}** | {row['ลูกค้า']} | 💰 {float(row['ยอดรวม']):,.2f} บ.")
                        st.caption(row['รายการอาหาร'])
                    with c2:
                        if st.button("✅ จ่ายแล้ว", key=f"p_{idx}"):
                            orders_df.at[idx, 'สถานะ'] = 'paid';
                            orders_df.to_csv(ORDER_CSV, index=False);
                            st.rerun()
                        if st.button("❌ ยกเลิก", key=f"can_{idx}"):
                            orders_df.at[idx, 'สถานะ'] = 'cancelled';
                            orders_df.to_csv(ORDER_CSV, index=False);
                            st.rerun()
        else:
            st.info("ไม่มีออเดอร์ค้าง")
        time.sleep(10);
        st.rerun()

    with tabs[1]:  # พนักงานสามารถกดแท็บอื่นๆ ได้โดยไม่โดนขัดจังหวะ
        st.write("📦 จัดการสต็อกอาหาร")
        # (โค้ดจัดการสต็อก...)

# === 🛒 หน้าลูกค้า (Customer) ===
else:
    # --- 🚦 ระบบคิว (แสดงเมื่อออเดอร์ค้างถึง 10 เท่านั้น) ---
    show_booking_ui = False
    if kitchen_load >= KITCHEN_LIMIT:
        if not st.session_state.my_queue_id:
            show_booking_ui = True
        else:
            try:
                my_pos = queue_df['queue_id'].tolist().index(st.session_state.my_queue_id)
                if my_pos == 0 and kitchen_load < KITCHEN_LIMIT:
                    show_booking_ui = False
                else:
                    st.markdown(f"""<div class="queue-box"><h2>🎫 คิวของคุณคือ {st.session_state.my_queue_id}</h2>
                    <p>รออีก {my_pos} คิวจะถึงลำดับของคุณ</p></div>""", unsafe_allow_html=True)
                    if st.button("🔄 อัปเดตสถานะคิว"): st.rerun()
                    st.stop()
            except:
                st.session_state.my_queue_id = None; st.rerun()

    if show_booking_ui:
        st.error(f"🚫 ขออภัยครับ ขณะนี้ครัวเต็ม ({kitchen_load}/{KITCHEN_LIMIT}) กรุณารับคิวออนไลน์")
        q_name = st.text_input("ระบุชื่อของคุณเพื่อรับคิวออนไลน์")
        st.caption("ℹ️ หากมีการจองคิวไว้แล้ว กรุณาใส่ชื่อเดิมที่เคยได้จองไว้")  # หมายเหตุเล็กๆ
        if st.button("🎫 รับคิว / เช็คคิวเดิม", type="primary", use_container_width=True):
            if q_name:
                st.session_state.my_queue_id = add_to_queue(q_name); st.rerun()
            else:
                st.warning("⚠️ กรุณาใส่ชื่อที่จองคิวไว้")  # คำเตือนเมื่อไม่ใส่ชื่อ
        st.stop()

    # --- 🍜 หน้าสั่งอาหารปกติ ---
    st.subheader("🛒 เริ่มสั่งอาหาร")
    c_t, c_c = st.columns(2)
    with c_t:
        table_no = st.selectbox("📍 เลือกโต๊ะ", ["โต๊ะ 1", "โต๊ะ 2", "โต๊ะ 3", "โต๊ะ 4", "กลับบ้าน"])
    with c_c:
        cust_name = st.text_input("👤 ชื่อของคุณ", placeholder="ใส่ชื่อที่จองไว้...")
        st.caption("ℹ️ หากมีการจองคิวไว้แล้ว กรุณาใส่ชื่อเดิมที่เคยได้จองไว้")  # หมายเหตุใต้ช่องชื่อ

    # ✅ แสดงแจ้งเตือนสีเหลืองเฉพาะเมื่อเว้นว่าง
    if not cust_name:
        st.warning("⚠️ กรุณาใส่ชื่อที่จองคิวไว้")
        st.stop()

    # (ส่วนแสดงรายการอาหาร และ ตะกร้าสินค้า...)
    st.divider()
    st.info("เชิญเลือกเมนูอาหารด้านล่างได้เลยครับ")
    # ...