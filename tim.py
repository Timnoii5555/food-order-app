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
import re
import json
import random

# ================= 1. ตั้งค่าและ Initialize =================
st.set_page_config(page_title="TimNoi Shabu", page_icon="🍲", layout="wide")

# ประกาศตัวแปร Session State
if 'basket' not in st.session_state: st.session_state.basket = []
if 'page' not in st.session_state: st.session_state.page = 'menu'
if 'app_mode' not in st.session_state: st.session_state.app_mode = 'customer'
if 'last_wrong_pass' not in st.session_state: st.session_state.last_wrong_pass = ""
if 'my_queue_id' not in st.session_state: st.session_state.my_queue_id = None
if 'user_table' not in st.session_state: st.session_state.user_table = None
if 'user_name' not in st.session_state: st.session_state.user_name = ""
if 'details_confirmed' not in st.session_state: st.session_state.details_confirmed = False
if 'last_refresh_timestamp' not in st.session_state: st.session_state.last_refresh_timestamp = 0
if 'menu_mtime' not in st.session_state: st.session_state.menu_mtime = 0

# State สำหรับระบบ OTP
if 'login_phase' not in st.session_state: st.session_state.login_phase = 1
if 'login_otp_ref' not in st.session_state: st.session_state.login_otp_ref = None
if 'login_temp_name' not in st.session_state: st.session_state.login_temp_name = ""

# กู้คืนข้อมูลลูกค้าจาก URL
if 'name' in st.query_params and 'table' in st.query_params:
    if st.session_state.user_name == "":
        st.session_state.user_name = st.query_params['name']
        st.session_state.user_table = st.query_params['table']
        st.session_state.details_confirmed = True

# ================= 2. Config & Constants (แก้ไขส่วนนี้ให้แล้วครับ) =================
try:
    # พยายามโหลดจาก Secrets ของ Streamlit Cloud ก่อน
    SENDER_EMAIL = st.secrets["email"]["user"]
    SENDER_PASSWORD = st.secrets["email"]["password"]
    ADMIN_PASSWORD = st.secrets["admin"]["password"]
except:
    # [FIXED] ถ้าไม่มี Secrets ให้ใช้ค่าที่คุณระบุมา (แก้ไขรหัสผ่าน + ใส่อีเมลจริง)
    SENDER_EMAIL = 'pupe15625@gmail.com'
    SENDER_PASSWORD = 'cpgz uqtz zaku famv'
    ADMIN_PASSWORD = '090090op'

RECEIVER_EMAIL = SENDER_EMAIL

# File Paths
ORDER_CSV = 'order_history.csv'
MENU_CSV = 'menu_data.csv'
TABLES_CSV = 'tables_data.csv'
CONTACT_CSV = 'contact_data.csv'
QUEUE_CSV = 'queue_data.csv'
FEEDBACK_CSV = 'feedback_data.csv'
LOGIN_LOG_CSV = 'login_log.csv'
REFRESH_SIGNAL_FILE = 'refresh_signal.txt'
IMAGE_FOLDER = 'uploaded_images'
BANNER_FOLDER = 'banner_images'

if not os.path.exists(IMAGE_FOLDER): os.makedirs(IMAGE_FOLDER)
if not os.path.exists(BANNER_FOLDER): os.makedirs(BANNER_FOLDER)

KITCHEN_LIMIT = 10


# ================= 3. ฟังก์ชันจัดการข้อมูล (Functions) =================

def get_thai_time():
    tz = pytz.timezone('Asia/Bangkok')
    return datetime.now(tz)


def check_system_updates():
    should_rerun = False
    if os.path.exists(REFRESH_SIGNAL_FILE):
        try:
            with open(REFRESH_SIGNAL_FILE, 'r') as f:
                signal_time = float(f.read().strip())
            if signal_time > st.session_state.last_refresh_timestamp:
                st.session_state.last_refresh_timestamp = signal_time
                should_rerun = True
        except:
            pass

    if os.path.exists(MENU_CSV):
        try:
            current_mtime = os.path.getmtime(MENU_CSV)
            if current_mtime > st.session_state.menu_mtime:
                st.session_state.menu_mtime = current_mtime
                st.toast("📢 เมนูมีการเปลี่ยนแปลง!", icon="🍲")
                should_rerun = True
        except:
            pass
    return should_rerun


def trigger_global_refresh():
    with open(REFRESH_SIGNAL_FILE, 'w') as f:
        f.write(str(time.time()))


def daily_cleanup():
    today_str = get_thai_time().strftime("%d/%m/%Y")
    if os.path.exists(ORDER_CSV):
        try:
            df = pd.read_csv(ORDER_CSV)
            if not df.empty and 'เวลา' in df.columns and 'สถานะ' in df.columns:
                changed = False
                for index, row in df.iterrows():
                    if row['สถานะ'] == 'waiting':
                        try:
                            order_date = str(row['เวลา']).split()[0]
                            if order_date != today_str:
                                df.at[index, 'สถานะ'] = 'expired'
                                changed = True
                        except:
                            pass
                if changed: df.to_csv(ORDER_CSV, index=False)
        except:
            pass

    if os.path.exists(QUEUE_CSV):
        try:
            q_df = pd.read_csv(QUEUE_CSV)
            if not q_df.empty:
                first_q_timestamp = str(q_df.iloc[0]['timestamp'])
                q_date_str = first_q_timestamp.split()[0]
                today_date_sys = get_thai_time().strftime("%Y-%m-%d")
                if q_date_str != today_date_sys:
                    pd.DataFrame(columns=["queue_id", "customer_name", "timestamp"]).to_csv(QUEUE_CSV, index=False)
        except:
            pass


def load_menu():
    if not os.path.exists(MENU_CSV):
        default_data = [
            {"name": "หมูหมัก", "price": 120, "img": "https://placehold.co/400", "category": "เนื้อสัตว์ (Meat)",
             "in_stock": True},
            {"name": "ผักรวม", "price": 40, "img": "https://placehold.co/400", "category": "ผัก (Veggie)",
             "in_stock": True},
        ]
        df = pd.DataFrame(default_data)
        df.to_csv(MENU_CSV, index=False)
    try:
        df = pd.read_csv(MENU_CSV)
        required_cols = ["name", "price", "img", "category", "in_stock"]
        for col in required_cols:
            if col not in df.columns:
                if col == "in_stock":
                    df[col] = True
                else:
                    df[col] = ""
    except:
        df = pd.DataFrame(columns=["name", "price", "img", "category", "in_stock"])
    df['img'] = df['img'].astype(str)
    return df


def load_tables():
    if not os.path.exists(TABLES_CSV):
        default_tables = ["โต๊ะ 1", "โต๊ะ 2", "โต๊ะ 3", "โต๊ะ 4", "กลับบ้าน"]
        df = pd.DataFrame(default_tables, columns=["table_name"])
        df.to_csv(TABLES_CSV, index=False)
    return pd.read_csv(TABLES_CSV)


def load_orders():
    cols = ["เวลา", "โต๊ะ", "ลูกค้า", "รายการอาหาร", "ยอดรวม", "หมายเหตุ", "สถานะ"]
    if not os.path.exists(ORDER_CSV):
        df = pd.DataFrame(columns=cols)
        df.to_csv(ORDER_CSV, index=False)
        return df
    return pd.read_csv(ORDER_CSV)


def load_contacts():
    default_contact = {"phone": "0XX-XXX-XXXX", "line": "@timnoishabu", "facebook": "#", "instagram": "#"}
    if not os.path.exists(CONTACT_CSV):
        df = pd.DataFrame([default_contact])
        df.to_csv(CONTACT_CSV, index=False)
        return default_contact
    else:
        try:
            return pd.read_csv(CONTACT_CSV).iloc[0].to_dict()
        except:
            return default_contact


def save_contacts(data_dict):
    df = pd.DataFrame([data_dict])
    df.to_csv(CONTACT_CSV, index=False)


def load_queue():
    if not os.path.exists(QUEUE_CSV):
        df = pd.DataFrame(columns=["queue_id", "customer_name", "timestamp"])
        df.to_csv(QUEUE_CSV, index=False)
        return df
    return pd.read_csv(QUEUE_CSV)


def add_to_queue(name):
    df = load_queue()
    if not df.empty and name in df['customer_name'].values:
        existing_id = df[df['customer_name'] == name].iloc[0]['queue_id']
        return existing_id, True
    last_id = 100
    if not df.empty:
        try:
            last_str = str(df.iloc[-1]['queue_id'])
            if '-' in last_str: last_id = int(last_str.split('-')[1])
        except:
            pass
    new_id = f"Q-{last_id + 1}"
    new_data = {"queue_id": new_id, "customer_name": name, "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    df = pd.concat([df, pd.DataFrame([new_data])], ignore_index=True)
    df.to_csv(QUEUE_CSV, index=False)
    return new_id, False


def pop_queue():
    df = load_queue()
    if not df.empty:
        df = df.iloc[1:]
        df.to_csv(QUEUE_CSV, index=False)


def load_feedback():
    if not os.path.exists(FEEDBACK_CSV):
        df = pd.DataFrame(columns=["timestamp", "customer_name", "message"])
        df.to_csv(FEEDBACK_CSV, index=False)
        return df
    return pd.read_csv(FEEDBACK_CSV)


def save_feedback_entry(name, message):
    df = load_feedback()
    new_entry = {"timestamp": datetime.now().strftime("%d/%m/%Y %H:%M"), "customer_name": name, "message": message}
    df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
    df.to_csv(FEEDBACK_CSV, index=False)


def delete_feedback_entry(index):
    df = load_feedback()
    try:
        df = df.drop(index)
        df.to_csv(FEEDBACK_CSV, index=False)
    except:
        pass


def load_login_log():
    if not os.path.exists(LOGIN_LOG_CSV):
        df = pd.DataFrame(columns=["timestamp", "declared_name", "status"])
        df.to_csv(LOGIN_LOG_CSV, index=False)
        return df
    return pd.read_csv(LOGIN_LOG_CSV)


def save_login_log(declared_name, status="Success"):
    df = load_login_log()
    timestamp = get_thai_time().strftime("%d/%m/%Y %H:%M:%S")
    new_entry = {"timestamp": timestamp, "declared_name": declared_name, "status": status}
    if "real_device_info" in df.columns: new_entry["real_device_info"] = "-"
    df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
    df.to_csv(LOGIN_LOG_CSV, index=False)


def save_image(uploaded_file):
    if uploaded_file is not None:
        timestamp = int(time.time())
        file_ext = uploaded_file.name.split('.')[-1]
        new_filename = f"img_{timestamp}.{file_ext}"
        file_path = os.path.join(IMAGE_FOLDER, new_filename)
        with open(file_path, "wb") as f: f.write(uploaded_file.getbuffer())
        return file_path
    return None


def get_image_base64(path):
    if not os.path.exists(path): return ""
    with open(path, "rb") as image_file:
        encoded = base64.b64encode(image_file.read()).decode()
    return f"data:image/png;base64,{encoded}"


def save_promo_banner(uploaded_file, index):
    if uploaded_file is not None:
        filename = f"banner_{index}.png"
        filepath = os.path.join(BANNER_FOLDER, filename)
        with open(filepath, "wb") as f: f.write(uploaded_file.getbuffer())
        return True
    return False


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
    mask = (df['โต๊ะ'] == data['โต๊ะ']) & (df['สถานะ'] == 'waiting')
    status_result = "new"
    if mask.any():
        index_to_update = df.index[mask][0]
        old_items = str(df.at[index_to_update, 'รายการอาหาร'])
        new_items = old_items + ", " + str(data['รายการอาหาร'])
        old_price = float(df.at[index_to_update, 'ยอดรวม'])
        new_price = old_price + float(data['ยอดรวม'])
        old_note = str(df.at[index_to_update, 'หมายเหตุ'])
        if old_note == 'nan': old_note = ""
        new_note = data['หมายเหตุ']
        final_note = f"{old_note} | {new_note}" if new_note else old_note
        df.at[index_to_update, 'รายการอาหาร'] = new_items
        df.at[index_to_update, 'ยอดรวม'] = new_price
        df.at[index_to_update, 'หมายเหตุ'] = final_note
        df.at[index_to_update, 'เวลา'] = data['เวลา']
        df.to_csv(ORDER_CSV, index=False)
        status_result = "merged"
    else:
        df_new = pd.DataFrame([data])
        cols = ["เวลา", "โต๊ะ", "ลูกค้า", "รายการอาหาร", "ยอดรวม", "หมายเหตุ", "สถานะ"]
        df_new = df_new[cols]
        if not os.path.exists(ORDER_CSV):
            df_new.to_csv(ORDER_CSV, index=False)
        else:
            df_new.to_csv(ORDER_CSV, mode='a', header=False, index=False)
        status_result = "new"

    if 'my_queue_id' in st.session_state and st.session_state.my_queue_id:
        queue_df = load_queue()
        if not queue_df.empty and queue_df.iloc[0]['queue_id'] == st.session_state.my_queue_id:
            pop_queue()
            st.session_state.my_queue_id = None
    return status_result


def sanitize_link(link):
    if not link: return "#"
    link = str(link).strip()
    if link.startswith("http://") or link.startswith("https://"): return link
    return "https://" + link


# ================= 4. UI Rendering =================

# JavaScript Poller
components.html(
    """
    <script>
        setInterval(function(){
            window.parent.document.querySelector(".stApp").dispatchEvent(new Event("change"));
        }, 3000);
    </script>
    """,
    height=0,
)

# CSS Styling
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;500;700&display=swap');
    html, body, [class*="css"] { font-family: 'Sarabun', sans-serif; background-color: #FDFBF7; }
    header, footer {visibility: hidden;}
    .stButton>button { border-radius: 8px; font-weight: bold; background-color: #8D6E63; color: white; border: none; box-shadow: 0 2px 4px rgba(0,0,0,0.2); transition: 0.3s; }
    .stButton>button:hover { background-color: #6D4C41; color: #FFECB3; transform: scale(1.02); }
    .customer-queue-box { background: linear-gradient(135deg, #3E2723 0%, #5D4037 100%); color: white; padding: 20px; border-radius: 16px; text-align: center; margin-bottom: 20px; box-shadow: 0 8px 16px rgba(0,0,0,0.2); border: 2px solid #D7CCC8; }
    .queue-title { font-size: 18px; font-weight: bold; color: #FFECB3; text-transform: uppercase; }
    .queue-big-number { font-size: 56px; font-weight: 800; line-height: 1; color: white; margin: 10px 0; }
    .queue-empty { background-color: #E8F5E9; border: 2px dashed #4CAF50; color: #2E7D32; padding: 15px; border-radius: 12px; text-align: center; font-weight: bold; }
    .queue-full { background-color: #FFEBEE; border: 2px dashed #EF5350; color: #C62828; padding: 15px; border-radius: 12px; text-align: center; font-weight: bold; }
    .sales-box { background-color: #FFF3E0; border: 2px solid #FFB74D; color: #E65100; padding: 20px; border-radius: 12px; text-align: center; margin-bottom: 20px; }
    .sales-number { font-size: 48px; font-weight: bold; color: #BF360C; }
    .out-of-stock { filter: grayscale(100%); opacity: 0.6; }
    h1, h2, h3 { color: #3E2723 !important; }
    .contact-row { display: flex; align-items: center; margin-bottom: 12px; background-color: white; padding: 12px; border-radius: 12px; border: 1px solid #eee; transition: all 0.2s; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }
    .contact-row:hover { transform: translateY(-2px); box-shadow: 0 4px 8px rgba(0,0,0,0.1); border-color: #8D6E63; }
    .contact-icon { width: 32px; height: 32px; margin-right: 15px; }
    .contact-link { text-decoration: none; color: #333; font-weight: bold; font-size: 16px; flex-grow: 1; }
    .kitchen-status-box { background-color: #E8F5E9; border: 2px solid #4CAF50; color: #2E7D32; padding: 15px; border-radius: 12px; text-align: center; font-weight: bold; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
</style>
""", unsafe_allow_html=True)

# Main Logic Check
if check_system_updates(): st.rerun()
daily_cleanup()

# Load Data
menu_df = load_menu()
tables_df = load_tables()
orders_df = load_orders()
contact_info = load_contacts()
queue_df = load_queue()
feedback_df = load_feedback()

waiting_orders = orders_df[orders_df['สถานะ'] == 'waiting']
busy_tables = waiting_orders['โต๊ะ'].unique().tolist()
kitchen_load = len(waiting_orders)

is_queue_mode = False
can_order = True
waiting_q_count = 0

if kitchen_load >= KITCHEN_LIMIT:
    is_queue_mode = True
    can_order = False

if not queue_df.empty:
    if st.session_state.my_queue_id:
        try:
            my_idx = queue_df.index[queue_df['queue_id'] == st.session_state.my_queue_id].tolist()[0]
            waiting_q_count = my_idx
            if st.session_state.my_queue_id == queue_df.iloc[0]['queue_id']:
                if kitchen_load < KITCHEN_LIMIT:
                    can_order = True
                    is_queue_mode = False
                else:
                    can_order = False
                    is_queue_mode = True
        except:
            waiting_q_count = len(queue_df)

        # ================= 5. ส่วนหัว (Header) =================
c_logo, c_name, c_menu = st.columns([1.3, 2, 0.5])
with c_logo:
    if os.path.exists("logo.png"):
        st.image("logo.png", width=320)
    else:
        st.markdown("<h1>🍲</h1>", unsafe_allow_html=True)
with c_name:
    st.markdown(f"""
        <div style="display: flex; flex-direction: column; justify-content: center; height: 220px;">
            <h1 style='color:#3E2723; font-size:50px; margin:0; line-height:1; font-weight:800;'>TimNoi Shabu</h1>
            <p style='color:#8D6E63; font-size:20px; margin:5px 0 0 0; font-weight:bold;'>ร้านนี้ไม่มีหมูเพราะที่เห็นเป็นเนื้อหมา</p>
            <div style='margin-top:15px; border-top: 2px solid #D7CCC8; padding-top:10px;'>
                <p style='color:#5D4037; font-size:16px; margin:0;'>🕒 เปิดบริการ: 00:00 - 23:59 น.</p>
                <p style='color:#5D4037; font-size:16px; margin:0;'>📞 โทร: {contact_info.get('phone', '-')}</p>
            </div>
        </div>
    """, unsafe_allow_html=True)
with c_menu:
    st.write("")
    with st.popover("☰ เมนู", use_container_width=True):
        st.markdown("### เมนูหลัก")
        if st.button("🏠 หน้าลูกค้า", use_container_width=True):
            st.session_state.app_mode = 'customer'
            st.rerun()
        if st.button("💬 เขียนติชม/สมุดเยี่ยม", use_container_width=True):
            st.session_state.app_mode = 'customer'
            st.session_state.page = 'feedback'
            st.rerun()
        if st.button("⚙️ จัดการร้าน (Admin)", use_container_width=True):
            st.session_state.app_mode = 'admin_login'
            st.session_state.login_phase = 1
            st.rerun()
        st.markdown("---")
        if st.button("🔄 รีเฟรช", use_container_width=True): st.rerun()
        st.markdown("---")
        st.markdown("### 📞 ช่องทางติดต่อ")
        fb_url = sanitize_link(contact_info.get('facebook', ''))
        ig_url = sanitize_link(contact_info.get('instagram', ''))
        line_id = contact_info.get('line', '-')
        fb_icon = "https://cdn-icons-png.flaticon.com/512/5968/5968764.png"
        ig_icon = "https://cdn-icons-png.flaticon.com/512/3955/3955024.png"
        line_icon = "https://upload.wikimedia.org/wikipedia/commons/4/41/LINE_logo.svg"
        st.markdown(f"""
        <div class="contact-row"><img src="{fb_icon}" class="contact-icon"><a href="{fb_url}" target="_blank" class="contact-link">Facebook</a></div>
        <div class="contact-row"><img src="{ig_icon}" class="contact-icon"><a href="{ig_url}" target="_blank" class="contact-link">Instagram</a></div>
        <div class="contact-row"><img src="{line_icon}" class="contact-icon"><span class="contact-link" style="color:#555;">Line: {line_id}</span></div>
        """, unsafe_allow_html=True)

st.markdown("---")

# ================= 6. Controller Logic =================

# --- ADMIN SECTION ---
if st.session_state.app_mode == 'admin_login':
    st.subheader("🔐 เข้าสู่ระบบหลังร้าน")
    if st.button("⬅️ กลับ"):
        st.session_state.app_mode = 'customer'
        st.rerun()

    if st.session_state.login_phase == 1:
        with st.container(border=True):
            st.info("ขั้นตอนที่ 1: ยืนยันรหัสผ่าน")
            admin_device = st.text_input("👤 ผู้ใช้งาน (ชื่อเล่น)", placeholder="ระบุชื่อผู้ใช้งาน...")
            password_input = st.text_input("🔑 ใส่รหัสผ่าน", type="password")

        if st.button("ขอเข้าสู่ระบบ (Request Access)"):
            if password_input:
                if password_input == ADMIN_PASSWORD:
                    otp_code = str(random.randint(100000, 999999))
                    declared_name = admin_device if admin_device else "ไม่ระบุชื่อ"
                    thai_now = get_thai_time().strftime('%d/%m/%Y %H:%M:%S')

                    st.session_state.login_otp_ref = otp_code
                    st.session_state.login_temp_name = declared_name

                    email_subject = f"🔒 คำขอเข้าใช้งาน Admin: {declared_name}"
                    email_body = f"OTP: {otp_code}\nUser: {declared_name}\nTime: {thai_now}"
                    send_email_notification(email_subject, email_body)

                    st.session_state.login_phase = 2
                    st.rerun()
                else:
                    st.error("รหัสผ่านผิด! ❌")
                    save_login_log(admin_device, "Failed (Wrong Pass)")

    elif st.session_state.login_phase == 2:
        with st.container(border=True):
            st.subheader("🛡️ ขั้นตอนที่ 2: OTP")
            st.info("ส่ง OTP ไปยังอีเมลเจ้าของร้านแล้ว")
            st.markdown(f"👤 ผู้ขอเข้าใช้: **{st.session_state.login_temp_name}**")
            otp_input = st.text_input("🔢 กรอกรหัส OTP 6 หลัก", max_chars=6)
            c1, c2 = st.columns(2)
            with c1:
                if st.button("ยืนยัน", type="primary", use_container_width=True):
                    if otp_input == st.session_state.login_otp_ref:
                        save_login_log(st.session_state.login_temp_name, "Success (OTP Verified)")
                        st.success("สำเร็จ!")
                        time.sleep(1)
                        st.session_state.app_mode = 'admin_dashboard'
                        st.session_state.login_phase = 1
                        st.rerun()
                    else:
                        st.error("OTP ผิด!")
            with c2:
                if st.button("ยกเลิก", use_container_width=True):
                    st.session_state.login_phase = 1
                    st.rerun()

elif st.session_state.app_mode == 'admin_dashboard':
    st.subheader("⚙️ จัดการร้าน (Admin)")
    c_ref1, c_ref2 = st.columns([3, 1])
    with c_ref1:
        if st.button("🚪 ออกจากระบบ"):
            st.session_state.app_mode = 'customer'
            st.rerun()
    with c_ref2:
        if st.button("🔄 รีเฟรชระบบ", type="primary", use_container_width=True):
            trigger_global_refresh()
            st.toast("ส่งคำสั่งรีเฟรชแล้ว", icon="🔄")
            time.sleep(1)
            st.rerun()

    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
        "👨‍🍳 ครัว", "📢 โปรโมชั่น", "📦 สต็อก/โต๊ะ", "📝 เมนู",
        "📊 ยอดขาย", "📞 ติดต่อ", "💬 อ่านรีวิว", "📜 ประวัติ Login"
    ])

    with tab1:  # ครัว
        st.markdown(f"#### 🔥 สถานะครัว: {kitchen_load}/{KITCHEN_LIMIT} ออเดอร์")
        st.progress(min(kitchen_load / KITCHEN_LIMIT, 1.0))
        if st.button("🔄 รีเฟรชออเดอร์"): st.rerun()
        if kitchen_load > 0:
            for index, row in waiting_orders.iterrows():
                with st.container(border=True):
                    c1, c2 = st.columns([3, 1])
                    with c1:
                        st.markdown(f"**{row['โต๊ะ']}** | {row['เวลา']}")
                        st.markdown(f"👤 {row['ลูกค้า']}")
                        st.info(f"💰 {row['ยอดรวม']} บาท")
                        with st.expander("รายการอาหาร"): st.code(row['รายการอาหาร'], language="text")
                        if str(row['หมายเหตุ']) not in ['nan', '']: st.warning(f"Note: {row['หมายเหตุ']}")
                    with c2:
                        if st.button("💰 รับเงิน", key=f"pay_{index}", type="primary", use_container_width=True):
                            orders_df.at[index, 'สถานะ'] = 'paid'
                            orders_df.to_csv(ORDER_CSV, index=False)
                            st.toast("✅ รับเงินเรียบร้อย!")
                            time.sleep(0.5)
                            st.rerun()
                        if st.button("❌ ยกเลิก", key=f"cncl_{index}", use_container_width=True):
                            orders_df.at[index, 'สถานะ'] = 'cancelled'
                            orders_df.to_csv(ORDER_CSV, index=False)
                            st.toast("❌ ยกเลิกแล้ว")
                            time.sleep(0.5)
                            st.rerun()
        else:
            st.success("ไม่มีออเดอร์ค้าง")

    with tab2:  # Banner
        st.header("📢 แบนเนอร์")
        for i in range(1, 6):
            c1, c2 = st.columns([2, 1])
            with c1:
                uploaded = st.file_uploader(f"รูป {i}", type=['png', 'jpg'], key=f"ban_up_{i}")
                if uploaded and save_promo_banner(uploaded, i): st.rerun()
            with c2:
                fp = os.path.join(BANNER_FOLDER, f"banner_{i}.png")
                if os.path.exists(fp):
                    st.image(fp, use_container_width=True)
                    if st.button(f"ลบ {i}", key=f"del_ban_{i}"):
                        os.remove(fp)
                        st.rerun()

    with tab3:  # Stock & Tables
        st.write("#### 📦 สต็อก")
        edited = st.data_editor(menu_df[['name', 'in_stock']], disabled=["name"], hide_index=True)
        if st.button("บันทึกสต็อก"):
            menu_df['in_stock'] = edited['in_stock']
            menu_df.to_csv(MENU_CSV, index=False)
            st.toast("บันทึกแล้ว")
        st.write("#### 🪑 จัดการโต๊ะ")
        with st.form("add_tbl"):
            new_t = st.text_input("ชื่อโต๊ะใหม่")
            if st.form_submit_button("เพิ่ม"):
                if new_t:
                    tables_df = pd.concat([tables_df, pd.DataFrame([{"table_name": new_t}])], ignore_index=True)
                    tables_df.to_csv(TABLES_CSV, index=False)
                    st.rerun()
        del_t = st.selectbox("ลบโต๊ะ", ["-"] + tables_df['table_name'].tolist())
        if st.button("ลบโต๊ะ") and del_t != "-":
            tables_df = tables_df[tables_df['table_name'] != del_t]
            tables_df.to_csv(TABLES_CSV, index=False)
            st.rerun()

    with tab4:  # Menu
        st.write("#### ➕ เพิ่มเมนู")
        with st.form("add_m"):
            n = st.text_input("ชื่อ")
            p = st.number_input("ราคา", min_value=0)
            c = st.selectbox("หมวด", ["เนื้อสัตว์ (Meat)", "อาหารทะเล (Seafood)", "ผัก (Veggie)", "ของทานเล่น (Snack)",
                                      "เครื่องดื่ม (Drinks)", "อื่นๆ (Others)"])
            up_file = st.file_uploader("รูป")
            url_img = st.text_input("URL รูป", "https://placehold.co/400")
            if st.form_submit_button("บันทึก"):
                if n:
                    final_path = save_image(up_file) if up_file else url_img
                    new_m = pd.DataFrame([{"name": n, "price": p, "img": final_path, "category": c, "in_stock": True}])
                    menu_df = pd.concat([menu_df, new_m], ignore_index=True)
                    menu_df.to_csv(MENU_CSV, index=False)
                    st.rerun()
        st.write("#### ❌ ลบเมนู")
        del_m = st.selectbox("เลือกเมนู", ["-"] + menu_df['name'].tolist())
        if st.button("ลบเมนู") and del_m != "-":
            menu_df = menu_df[menu_df['name'] != del_m]
            menu_df.to_csv(MENU_CSV, index=False)
            st.rerun()

    with tab5:  # Sales
        st.subheader("📊 ยอดขายรายวัน")
        today = get_thai_time().strftime("%d/%m/%Y")
        st.caption(f"วันที่: {today}")
        if 'สถานะ' in orders_df.columns:
            orders_df['ยอดรวม'] = pd.to_numeric(orders_df['ยอดรวม'], errors='coerce').fillna(0)
            daily = orders_df[(orders_df['สถานะ'] == 'paid') & (orders_df['เวลา'].astype(str).str.contains(today))]
            st.markdown(
                f"""<div class="sales-box"><div>ยอดรวม</div><div class="sales-number">{daily['ยอดรวม'].sum():,.2f} ฿</div></div>""",
                unsafe_allow_html=True)
            st.dataframe(daily[['เวลา', 'โต๊ะ', 'ลูกค้า', 'ยอดรวม']], hide_index=True, use_container_width=True)

    with tab6:  # Contact
        st.subheader("📞 ข้อมูลติดต่อ")
        with st.form("contact"):
            np = st.text_input("เบอร์", contact_info.get('phone', ''))
            nl = st.text_input("Line", contact_info.get('line', ''))
            nf = st.text_input("FB", contact_info.get('facebook', ''))
            ni = st.text_input("IG", contact_info.get('instagram', ''))
            if st.form_submit_button("บันทึก"):
                save_contacts({"phone": np, "line": nl, "facebook": nf, "instagram": ni})
                st.rerun()

    with tab7:  # Feedback
        st.subheader("💬 รีวิว")
        for i, r in feedback_df.iterrows():
            with st.container(border=True):
                st.write(f"**{r['customer_name']}**: {r['message']}")
                if st.button("ลบ", key=f"dfb_{i}"):
                    delete_feedback_entry(i)
                    st.rerun()

    with tab8:  # Log
        st.subheader("📜 Login Log")
        st.dataframe(load_login_log().iloc[::-1], hide_index=True, use_container_width=True)
        if st.button("ล้างประวัติ"):
            pd.DataFrame(columns=["timestamp", "declared_name", "status"]).to_csv(LOGIN_LOG_CSV, index=False)
            st.rerun()

# --- CUSTOMER SECTION ---
else:
    # Login Screen
    if not st.session_state.details_confirmed:
        st.markdown(
            """<div style="background-color: white; padding: 20px; border-radius: 15px; text-align: center;"><h2>👋 ยินดีต้อนรับ!</h2></div>""",
            unsafe_allow_html=True)
        col_c = st.columns([1, 2, 1])
        with col_c[1]:
            st.write("")
            with st.container(border=True):
                c_name_input = st.text_input("👤 ชื่อลูกค้า (ชื่อเล่น)", value=st.session_state.user_name)

                existing_table = None
                is_returning = False

                # Auto-Detect Customer
                if c_name_input:
                    orders_df['ลูกค้า'] = orders_df['ลูกค้า'].astype(str)
                    match = orders_df[(orders_df['ลูกค้า'] == c_name_input) & (orders_df['สถานะ'] == 'waiting')]
                    if not match.empty:
                        existing_table = str(match.iloc[0]['โต๊ะ'])
                        is_returning = True
                        st.success(f"🎉 พบรายการสั่งค้างของ: **{c_name_input}**")
                        st.info(f"ระบบเลือกโต๊ะ **{existing_table}** ให้อัตโนมัติ")

                if is_returning:
                    table_input = st.selectbox("📍 โต๊ะของคุณ", [existing_table], disabled=True)
                    if st.button("ไม่ใช่ฉัน / เปลี่ยนชื่อใหม่"):
                        st.session_state.user_name = ""
                        st.rerun()
                else:
                    all_tables = tables_df['table_name'].astype(str).tolist()
                    busy_str = [str(x) for x in busy_tables]
                    avail = [t for t in all_tables if t not in busy_str or t == str(st.session_state.user_table)]
                    curr = avail.index(str(st.session_state.user_table)) if str(
                        st.session_state.user_table) in avail else 0
                    table_input = st.selectbox("📍 เลือกโต๊ะ", avail, index=curr)

                if st.button("✅ ยืนยัน", type="primary", use_container_width=True):
                    if not c_name_input.strip() or not table_input:
                        st.error("กรุณาระบุข้อมูลให้ครบ")
                    else:
                        st.session_state.user_name = c_name_input
                        st.session_state.user_table = table_input
                        st.session_state.details_confirmed = True
                        st.query_params['name'] = c_name_input
                        st.query_params['table'] = table_input
                        st.rerun()

        if is_queue_mode:
            st.markdown("---")
            st.warning(f"⚠️ ครัวแน่น ({kitchen_load} คิว)")
            q_name = st.text_input("จองคิว (ชื่อ)")
            if st.button("🎟️ รับบัตรคิว"):
                if q_name:
                    qid, _ = add_to_queue(q_name)
                    st.session_state.my_queue_id = qid
                    st.success(f"คิว: {qid}")
        st.stop()

    # Logged In UI
    st.markdown(
        f"""<div style="background-color: #5D4037; color: white; padding: 10px; border-radius: 10px; margin-bottom: 10px;">👤 <b>{st.session_state.user_name}</b> | 📍 <b>{st.session_state.user_table}</b></div>""",
        unsafe_allow_html=True)
    if st.button("✏️ เปลี่ยนชื่อ/โต๊ะ"):
        st.session_state.details_confirmed = False
        st.query_params.clear()
        st.rerun()

    # Banners
    bans = [get_image_base64(os.path.join(BANNER_FOLDER, f"banner_{i}.png")) for i in range(1, 6) if
            os.path.exists(os.path.join(BANNER_FOLDER, f"banner_{i}.png"))]
    if bans:
        slides = "".join([
                             f'<div class="mySlides fade" style="display: {"block" if i == 0 else "none"};"><img src="{b}" style="width:100%; border-radius:15px;"></div>'
                             for i, b in enumerate(bans)])
        components.html(
            f"""<!DOCTYPE html><html><head><style>.mySlides {{display: none;}}.fade {{animation-name: fade; animation-duration: 1.5s;}}@keyframes fade {{from {{opacity: .4}} to {{opacity: 1}}}}</style></head><body><div class="slideshow-container">{slides}</div><script>let si=0;ss();function ss(){{let i;let s=document.getElementsByClassName("mySlides");for(i=0;i<s.length;i++){{s[i].style.display="none";}}si++;if(si>s.length){{si=1}}s[si-1].style.display="block";setTimeout(ss,5000);}}</script></body></html>""",
            height=320)

    # Queue Check
    if is_queue_mode:
        if st.session_state.my_queue_id:
            if can_order:
                st.success("✅ ถึงคิวแล้ว!")
            else:
                st.info(f"บัตรคิว: {st.session_state.my_queue_id} | รออีก {waiting_q_count} คิว")
                if st.button("เช็คสถานะ"): st.rerun()
                st.stop()
        else:
            st.warning("🚫 ครัวแน่น กรุณารับบัตรคิว")
            qn = st.text_input("ชื่อจองคิว")
            if st.button("รับบัตรคิว") and qn:
                qid, _ = add_to_queue(qn)
                st.session_state.my_queue_id = qid
                st.rerun()
            st.stop()

    # Kitchen Status
    if not waiting_orders.empty:
        st.markdown(f"""<div class="kitchen-status-box">👨‍🍳 กำลังปรุง: โต๊ะ {waiting_orders.iloc[0]['โต๊ะ']}</div>""",
                    unsafe_allow_html=True)
    else:
        st.markdown("""<div class="kitchen-status-box">✅ ครัวว่าง!</div>""", unsafe_allow_html=True)

    # Content Pages
    if st.session_state.page == 'feedback':
        st.button("⬅️ กลับ", on_click=lambda: st.session_state.update(page='menu'))
        st.subheader("💬 เขียนติชม")
        with st.form("fb"):
            m = st.text_area("ข้อความ")
            if st.form_submit_button("ส่ง"):
                save_feedback_entry(st.session_state.user_name, m)
                st.success("ขอบคุณครับ")
                time.sleep(1)
                st.session_state.page = 'menu'
                st.rerun()

    elif st.session_state.page == 'menu':
        st.subheader("📝 เมนู")
        cats = menu_df['category'].unique() if 'category' in menu_df.columns else []
        if len(cats) > 0:
            tabs = st.tabs(list(cats))
            for i, cat in enumerate(cats):
                with tabs[i]:
                    items = menu_df[menu_df['category'] == cat]
                    cols = st.columns(2)
                    for idx, row in items.iterrows():
                        with cols[idx % 2]:
                            with st.container(border=True):
                                try:
                                    if row['in_stock']:
                                        st.image(row['img'], use_container_width=True)
                                    else:
                                        st.markdown(
                                            f'<div style="opacity:0.5;filter:grayscale(100%);"><img src="{row["img"]}" style="width:100%;"></div><div style="text-align:center;color:red;font-weight:bold;">หมด</div>',
                                            unsafe_allow_html=True)
                                except:
                                    st.image("https://placehold.co/400")
                                st.markdown(f"**{row['name']}**")
                                if row['in_stock']:
                                    st.caption(f"{row['price']}.-")
                                    if st.button("ใส่ตะกร้า", key=f"add_{row['name']}_{idx}", use_container_width=True):
                                        st.session_state.basket.append(row.to_dict())
                                        st.toast(f"เพิ่ม {row['name']}")
                                else:
                                    st.button("หมด", key=f"no_{idx}", disabled=True)
        else:
            st.info("ไม่มีหมวดหมู่เมนู")

        if st.session_state.basket:
            st.markdown("---")
            if st.button(f"🛒 สรุปยอด ({len(st.session_state.basket)}) ➡️", type="primary", use_container_width=True):
                st.session_state.page = 'cart'
                st.rerun()

    elif st.session_state.page == 'cart':
        st.button("⬅️ เลือกเพิ่ม", on_click=lambda: st.session_state.update(page='menu'))
        st.subheader("🛒 ตะกร้าสินค้า")
        if st.session_state.basket:
            counts = Counter(i['name'] for i in st.session_state.basket)
            uniq = {i['name']: i for i in st.session_state.basket}
            total = 0
            for n, c in counts.items():
                item = uniq[n]
                sub = item['price'] * c
                total += sub
                with st.container(border=True):
                    c1, c2 = st.columns([1, 3])
                    with c1:
                        st.image(item['img'], use_container_width=True)
                    with c2:
                        st.markdown(f"**{n}**")
                        st.caption(f"{item['price']} x {c} = {sub} บ.")
                    b1, b2, b3 = st.columns([1, 1, 1])
                    with b1:
                        if st.button("➖", key=f"d_{n}"):
                            for i, x in enumerate(st.session_state.basket):
                                if x['name'] == n:
                                    del st.session_state.basket[i]
                                    break
                            st.rerun()
                    with b2:
                        st.markdown(f"<div style='text-align:center;'>{c}</div>", unsafe_allow_html=True)
                    with b3:
                        if st.button("➕", key=f"i_{n}"):
                            st.session_state.basket.append(item)
                            st.rerun()

            st.markdown("---")
            st.subheader(f"รวม: {total} บาท")
            note = st.text_area("หมายเหตุ")
            if st.button("✅ ยืนยันการสั่ง", type="primary", use_container_width=True):
                if is_queue_mode and not can_order:
                    st.error("ยังไม่ถึงคิว")
                else:
                    now = get_thai_time().strftime("%d/%m/%Y %H:%M")
                    items_str = ", ".join([f"{n}(x{c})" for n, c in counts.items()])
                    res = save_order({
                        "เวลา": now, "โต๊ะ": st.session_state.user_table,
                        "ลูกค้า": st.session_state.user_name, "รายการอาหาร": items_str,
                        "ยอดรวม": total, "หมายเหตุ": note, "สถานะ": "waiting"
                    })

                    email_body = f"Order: {res}\nTable: {st.session_state.user_table}\nItems: {items_str}\nTotal: {total}"
                    send_email_notification(f"New Order: {st.session_state.user_table}", email_body)

                    st.session_state.basket = []
                    st.session_state.page = 'menu'
                    st.balloons()
                    st.success("ส่งออเดอร์แล้ว!")
                    time.sleep(2)
                    st.rerun()
        else:
            st.info("ตะกร้าว่าง")
            if st.button("กลับไปเลือก"):
                st.session_state.page = 'menu'
                st.rerun()