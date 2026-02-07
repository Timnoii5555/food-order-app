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

# ================= 1. ตั้งค่าระบบ (Configuration) =================
try:
    SENDER_EMAIL = st.secrets["email"]["user"]
    SENDER_PASSWORD = st.secrets["email"]["password"]
    ADMIN_PASSWORD = st.secrets["admin"]["password"]
except:
    SENDER_EMAIL = 'jaskaikai4@gmail.com'
    SENDER_PASSWORD = 'zqyx nqdk ygww drpp'
    ADMIN_PASSWORD = '090090op'

RECEIVER_EMAIL = SENDER_EMAIL

# File Paths
ORDER_CSV = 'order_history.csv'
MENU_CSV = 'menu_data.csv'
TABLES_CSV = 'tables_data.csv'
CONTACT_CSV = 'contact_data.csv'
QUEUE_CSV = 'queue_data.csv'
FEEDBACK_CSV = 'feedback_data.csv'
IMAGE_FOLDER = 'uploaded_images'
BANNER_FOLDER = 'banner_images'

if not os.path.exists(IMAGE_FOLDER): os.makedirs(IMAGE_FOLDER)
if not os.path.exists(BANNER_FOLDER): os.makedirs(BANNER_FOLDER)

KITCHEN_LIMIT = 10

# หมวดหมู่ (Updated)
CATEGORIES = [
    "เนื้อสัตว์ (Meat)",
    "ทะเล (Seafood)",
    "ผัก (Veggie)",
    "ของทานเล่น (Snack)",
    "น้ำซุป (Soup)",
    "เครื่องดื่ม (Drinks)"
]


# ================= 2. ฟังก์ชันจัดการข้อมูล =================

def get_thai_time():
    tz = pytz.timezone('Asia/Bangkok')
    return datetime.now(tz)


def force_file_update(filepath):
    if os.path.exists(filepath):
        try:
            os.utime(filepath, None)
        except:
            pass


# --- ฟังก์ชันช่วยเปลี่ยนหน้า (Callback) แก้ปัญหาเมนูค้าง ---
def navigate_to(mode, page):
    st.session_state.app_mode = mode
    st.session_state.page = page
    # การใช้ Callback จะทำให้ Streamlit Rerun อัตโนมัติและปิด Popover ให้เอง


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
                if changed:
                    df.to_csv(ORDER_CSV, index=False)
                    force_file_update(ORDER_CSV)
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
                    force_file_update(QUEUE_CSV)
        except:
            pass


def load_menu():
    if not os.path.exists(MENU_CSV):
        default_data = [
            {"name": "หมูหมัก", "price": 120,
             "img": "https://images.unsplash.com/photo-1615937657715-bc7b4b7962c1?auto=format&fit=crop&w=500&q=60",
             "category": "เนื้อสัตว์ (Meat)", "in_stock": True},
            {"name": "กุ้งสด", "price": 150,
             "img": "https://images.unsplash.com/photo-1565680018434-b513d5e5fd47?auto=format&fit=crop&w=500&q=60",
             "category": "ทะเล (Seafood)", "in_stock": True},
            {"name": "น้ำซุปต้มยำ", "price": 0,
             "img": "https://images.unsplash.com/photo-1546272989-40c92939c6c2?auto=format&fit=crop&w=500&q=60",
             "category": "น้ำซุป (Soup)", "in_stock": True},
            {"name": "น้ำซุปน้ำดำ", "price": 0,
             "img": "https://images.unsplash.com/photo-1594970425029-797746816432?auto=format&fit=crop&w=500&q=60",
             "category": "น้ำซุป (Soup)", "in_stock": True},
        ]
        df = pd.DataFrame(default_data)
        df.to_csv(MENU_CSV, index=False)
        force_file_update(MENU_CSV)
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
    default_contact = {"phone": "064-448-55549", "line": "@timnoishabu", "facebook": "https://www.facebook.com",
                       "instagram": "https://www.instagram.com"}
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
    force_file_update(QUEUE_CSV)
    return new_id, False


def pop_queue():
    df = load_queue()
    if not df.empty:
        df = df.iloc[1:]
        df.to_csv(QUEUE_CSV, index=False)
        force_file_update(QUEUE_CSV)


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

    force_file_update(ORDER_CSV)

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


# ================= 3. UI & CSS =================
st.set_page_config(page_title="TimNoi Shabu", page_icon="🍲", layout="wide")

# --- Polling Script (ทุก 3 วินาที) ---
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

    .out-of-stock-img { filter: grayscale(100%); opacity: 0.5; transition: all 0.3s ease; }
    .out-of-stock-label { color: red; font-weight: bold; text-align: center; margin-top: -30px; margin-bottom: 10px; background: rgba(255,255,255,0.8); border-radius: 5px; }

    h1, h2, h3 { color: #3E2723 !important; }
    .contact-row { display: flex; align-items: center; margin-bottom: 12px; background-color: white; padding: 12px; border-radius: 12px; border: 1px solid #eee; transition: all 0.2s; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }
    .contact-row:hover { transform: translateY(-2px); box-shadow: 0 4px 8px rgba(0,0,0,0.1); border-color: #8D6E63; }
    .contact-icon { width: 32px; height: 32px; margin-right: 15px; }
    .contact-link { text-decoration: none; color: #333; font-weight: bold; font-size: 16px; flex-grow: 1; }

    @keyframes pulse {
        0% { transform: scale(1); }
        50% { transform: scale(1.05); }
        100% { transform: scale(1); }
    }
    .warning-box {
        background-color: #FFEBEE;
        border-left: 5px solid #F44336;
        padding: 15px;
        border-radius: 5px;
        color: #C62828;
        font-weight: bold;
        text-align: center;
        animation: pulse 2s infinite;
        margin-bottom: 20px;
    }
    .kitchen-status-box {
        background-color: #E8F5E9; border: 2px solid #4CAF50; color: #2E7D32; padding: 15px; border-radius: 12px; text-align: center; font-weight: bold; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)

# ================= 4. โหลดข้อมูล & State =================
if 'basket' not in st.session_state: st.session_state.basket = []
if 'page' not in st.session_state: st.session_state.page = 'menu'
if 'app_mode' not in st.session_state: st.session_state.app_mode = 'customer'
if 'last_wrong_pass' not in st.session_state: st.session_state.last_wrong_pass = ""
if 'my_queue_id' not in st.session_state: st.session_state.my_queue_id = None
if 'user_table' not in st.session_state: st.session_state.user_table = None
if 'user_name' not in st.session_state: st.session_state.user_name = ""

# --- Feature (Logic): ตรวจจับการเปลี่ยนแปลงของไฟล์ Menu ---
if 'menu_mtime' not in st.session_state:
    st.session_state.menu_mtime = 0

if os.path.exists(MENU_CSV):
    current_mtime = os.path.getmtime(MENU_CSV)
    if st.session_state.menu_mtime != 0 and current_mtime != st.session_state.menu_mtime:
        st.session_state.menu_mtime = current_mtime
        st.toast("📢 มีการอัปเดตรายการอาหาร/สต็อก!")
        time.sleep(1)
        st.rerun()
    else:
        st.session_state.menu_mtime = current_mtime

daily_cleanup()

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

        # ================= 5. ส่วนหัวและเมนู =================
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
        # --- FIX: Use callbacks to ensure popover closes ---
        st.button("🏠 หน้าลูกค้า", on_click=navigate_to, args=('customer', 'menu'), use_container_width=True)
        st.button("💬 เขียนติชม/สมุดเยี่ยม", on_click=navigate_to, args=('customer', 'feedback'),
                  use_container_width=True)
        st.button("⚙️ จัดการร้าน (Admin)", on_click=navigate_to, args=('admin_login', 'menu'), use_container_width=True)

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

# ================= 6. Controller =================

if st.session_state.app_mode == 'admin_login':
    st.subheader("🔐 เข้าสู่ระบบหลังร้าน")
    if st.button("⬅️ กลับ"):
        navigate_to('customer', 'menu')
    password_input = st.text_input("🔑 ใส่รหัสผ่าน", type="password")
    if password_input == ADMIN_PASSWORD:
        st.success("รหัสถูกต้อง! ✅")
        time.sleep(0.5)
        navigate_to('admin_dashboard', 'menu')
    elif password_input:
        st.error("รหัสผิด! ❌")
        if st.session_state.last_wrong_pass != password_input:
            thai_now = get_thai_time().strftime('%d/%m/%Y %H:%M:%S')
            send_email_notification("🚨 Alert: รหัส Admin ผิด", f"เวลา: {thai_now}\nรหัสที่ใส่: {password_input}")
            st.session_state.last_wrong_pass = password_input

elif st.session_state.app_mode == 'admin_dashboard':
    st.subheader("⚙️ จัดการร้าน (Admin)")
    if st.button("🚪 ออกจากระบบ"):
        navigate_to('customer', 'menu')

    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(
        ["👨‍🍳 ครัว", "📢 โปรโมชั่น", "📦 สต็อก/โต๊ะ", "📝 เมนู", "📊 ยอดขาย", "📞 ติดต่อ", "💬 อ่านรีวิว"])

    with tab1:
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

                        val_price = row['ยอดรวม']
                        val_note = row['หมายเหตุ']


                        def is_number(s):
                            try:
                                float(str(s).replace(',', ''))
                            except:
                                return False
                            return True


                        if not is_number(val_price) and is_number(val_note):
                            display_price = val_note
                            display_note = val_price
                        else:
                            display_price = val_price
                            display_note = val_note

                        st.info(f"💰 ยอดรวม: **{display_price}** บาท")
                        with st.expander("รายการอาหาร"):
                            st.code(row['รายการอาหาร'], language="text")

                        if str(display_note) != 'nan' and str(display_note) != '':
                            st.warning(f"Note: {display_note}")

                    with c2:
                        if st.button("💰 รับเงิน", key=f"pay_{index}", type="primary", use_container_width=True):
                            orders_df.at[index, 'สถานะ'] = 'paid'
                            orders_df.to_csv(ORDER_CSV, index=False)
                            force_file_update(ORDER_CSV)
                            st.rerun()
                        if st.button("❌ ยกเลิก", key=f"cncl_{index}", use_container_width=True):
                            orders_df.at[index, 'สถานะ'] = 'cancelled'
                            orders_df.to_csv(ORDER_CSV, index=False)
                            force_file_update(ORDER_CSV)
                            st.rerun()
        else:
            st.success("ไม่มีออเดอร์ค้าง")

    with tab2:
        st.header("📢 แบนเนอร์โปรโมชั่น")
        for i in range(1, 6):
            col_b1, col_b2 = st.columns([2, 1])
            filename = f"banner_{i}.png"
            filepath = os.path.join(BANNER_FOLDER, filename)
            with col_b1:
                uploaded = st.file_uploader(f"อัปโหลดรูป {i}", type=['png', 'jpg', 'jpeg'], key=f"ban_up_{i}")
                if uploaded:
                    if save_promo_banner(uploaded, i):
                        st.success(f"บันทึกรูป {i} แล้ว")
                        time.sleep(0.5)
                        st.rerun()
            with col_b2:
                if os.path.exists(filepath):
                    st.image(filepath, use_container_width=True)
                    if st.button(f"🗑️ ลบรูป {i}", key=f"del_ban_{i}"):
                        os.remove(filepath)
                        st.rerun()
                else:
                    st.info("ว่าง")
            st.markdown("---")

    with tab3:
        st.write("#### 📦 จัดการสต็อก")
        edited_stock = st.data_editor(menu_df[['name', 'in_stock']], disabled=["name"], hide_index=True)
        if st.button("บันทึกสต็อก"):
            menu_df['in_stock'] = edited_stock['in_stock']
            menu_df.to_csv(MENU_CSV, index=False)
            force_file_update(MENU_CSV)
            st.toast("บันทึกแล้ว! ระบบจะแจ้งเตือนลูกค้าทันที")
            st.rerun()

        st.markdown("---")
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

    with tab4:
        st.write("#### ➕ เพิ่มเมนู")
        with st.form("add_m"):
            n = st.text_input("ชื่อเมนู")
            p = st.number_input("ราคา", min_value=0)
            c = st.selectbox("หมวด", CATEGORIES)
            uploaded_file = st.file_uploader("อัปโหลดรูปจากเครื่อง", type=['png', 'jpg', 'jpeg'])
            img_url_input = st.text_input("หรือใส่ URL รูปภาพ", "https://placehold.co/400")
            if st.form_submit_button("บันทึกเมนู"):
                if n:
                    final_img_path = img_url_input
                    if uploaded_file is not None:
                        saved_path = save_image(uploaded_file)
                        if saved_path: final_img_path = saved_path
                    nd = pd.DataFrame([{"name": n, "price": p, "img": final_img_path, "category": c, "in_stock": True}])
                    menu_df = pd.concat([menu_df, nd], ignore_index=True)
                    menu_df.to_csv(MENU_CSV, index=False)
                    force_file_update(MENU_CSV)
                    st.success(f"เพิ่ม {n} สำเร็จ! ลูกค้าจะเห็นเมนูใหม่ทันที")
                    time.sleep(1)
                    st.rerun()
        st.write("#### ❌ ลบเมนู")
        del_m = st.selectbox("เลือกเมนูลบ", ["-"] + menu_df['name'].tolist())
        if st.button("ลบเมนู") and del_m != "-":
            menu_df = menu_df[menu_df['name'] != del_m]
            menu_df.to_csv(MENU_CSV, index=False)
            force_file_update(MENU_CSV)
            st.rerun()

    with tab5:
        st.subheader("📊 สรุปยอดขายรายวัน")
        today_str = get_thai_time().strftime("%d/%m/%Y")
        st.caption(f"ประจำวันที่: {today_str}")
        if 'สถานะ' in orders_df.columns:
            orders_df['ยอดรวม'] = pd.to_numeric(orders_df['ยอดรวม'], errors='coerce').fillna(0)
            daily_sales = orders_df[
                (orders_df['สถานะ'] == 'paid') & (orders_df['เวลา'].astype(str).str.contains(today_str))]
            total_revenue = daily_sales['ยอดรวม'].sum()
            st.markdown(
                f"""<div class="sales-box"><div>ยอดขายรวมวันนี้</div><div class="sales-number">{total_revenue:,.2f} ฿</div><div>จำนวน {len(daily_sales)} บิล</div></div>""",
                unsafe_allow_html=True)
            st.write("📜 **ประวัติการขายวันนี้:**")
            st.dataframe(daily_sales[['เวลา', 'โต๊ะ', 'ลูกค้า', 'ยอดรวม', 'รายการอาหาร']], hide_index=True,
                         use_container_width=True)
        else:
            st.warning("ยังไม่มีข้อมูลยอดขาย")

    with tab6:
        st.subheader("📞 จัดการลิ้งค์และเบอร์โทร")
        with st.form("contact_form"):
            new_phone = st.text_input("📞 เบอร์โทรศัพท์", value=contact_info.get('phone', ''))
            new_line = st.text_input("💬 Line ID", value=contact_info.get('line', ''))
            new_fb = st.text_input("🔵 Facebook Link (URL)", value=contact_info.get('facebook', ''))
            new_ig = st.text_input("🟣 Instagram Link (URL)", value=contact_info.get('instagram', ''))
            if st.form_submit_button("💾 บันทึกข้อมูลติดต่อ"):
                new_data = {"phone": new_phone, "line": new_line, "facebook": new_fb, "instagram": new_ig}
                save_contacts(new_data)
                st.success("บันทึกเรียบร้อย!")
                time.sleep(1)
                st.rerun()

    with tab7:
        st.subheader("💬 ข้อความติชมจากลูกค้า")
        if not feedback_df.empty:
            for index, row in feedback_df.iterrows():
                with st.container(border=True):
                    c1, c2 = st.columns([4, 1])
                    with c1:
                        st.markdown(f"**{row['customer_name']}** ({row['timestamp']})")
                        st.write(f"📝 {row['message']}")
                    with c2:
                        if st.button("🗑️ ลบ", key=f"del_fb_{index}", type="primary"):
                            delete_feedback_entry(index)
                            st.rerun()
        else:
            st.info("ยังไม่มีรีวิวครับ")

# === Customer Page ===
else:
    banner_images = []
    for i in range(1, 6):
        fpath = os.path.join(BANNER_FOLDER, f"banner_{i}.png")
        if os.path.exists(fpath):
            banner_images.append(get_image_base64(fpath))

    if len(banner_images) > 0:
        slides_html = ""
        for idx, img_b64 in enumerate(banner_images):
            display_style = "block" if idx == 0 else "none"
            slides_html += f"""<div class="mySlides fade" style="display: {display_style};"><img src="{img_b64}" style="width:100%; border-radius:15px; box-shadow: 0 4px 8px rgba(0,0,0,0.2);"></div>"""

        components.html(f"""
        <!DOCTYPE html><html><head><style>.mySlides {{display: none;}}img {{vertical-align: middle;}}.fade {{-webkit-animation-name: fade; -webkit-animation-duration: 1.5s; animation-name: fade; animation-duration: 1.5s;}}@-webkit-keyframes fade {{ from {{opacity: .4}} to {{opacity: 1}} }}@keyframes fade {{ from {{opacity: .4}} to {{opacity: 1}} }}</style></head><body><div class="slideshow-container">{slides_html}</div><script>let slideIndex = 0;showSlides();function showSlides() {{let i;let slides = document.getElementsByClassName("mySlides");for (i = 0; i < slides.length; i++) {{slides[i].style.display = "none";}}slideIndex++;if (slideIndex > slides.length) {{slideIndex = 1}}slides[slideIndex-1].style.display = "block";setTimeout(showSlides, 8000);}}</script></body></html>
        """, height=320)

    # เงื่อนไขการแสดงผล: แสดงหน้าคิว เฉพาะเมื่ออยู่ในโหมดคิว (Orders >= 10)
    if is_queue_mode:
        if st.session_state.my_queue_id:
            if can_order:
                st.success(f"✅ ถึงคิวของคุณแล้ว! ({st.session_state.my_queue_id}) เชิญสั่งอาหารได้เลยครับ")
            else:
                st.markdown(f"""
                <div class="customer-queue-box">
                    <div class="queue-title">🎫 บัตรคิวของคุณ: {st.session_state.my_queue_id}</div>
                    <div class="queue-desc">รออีก {waiting_q_count} คิว</div>
                    <p style="margin-top:10px;">กรุณารอสักครู่... พนักงานกำลังเคลียร์ครัวครับ</p>
                </div>
                """, unsafe_allow_html=True)
                if st.button("🔄 เช็คสถานะคิวล่าสุด"): st.rerun()
                st.stop()
        else:
            st.markdown(f"""
            <div class="queue-full">
                <h3>🚫 ครัวแน่นมาก ({kitchen_load} ออเดอร์)</h3>
                <p>ขออภัยในความไม่สะดวก กรุณากดรับบัตรคิวเพื่อจองสิทธิ์สั่งอาหารครับ</p>
            </div>
            """, unsafe_allow_html=True)

            c_name = st.text_input("ชื่อลูกค้า (สำหรับจองใหม่ หรือ เช็คคิวเดิม)", key="q_name")
            if st.button("🎟️ กดรับบัตรคิว / กู้คืนคิวเดิม", type="primary", use_container_width=True):
                if c_name:
                    q_id, is_old = add_to_queue(c_name)
                    st.session_state.my_queue_id = q_id
                    if is_old:
                        st.success(f"🎉 ยินดีต้อนรับกลับ! กู้คืนคิวเดิม: {q_id}")
                    else:
                        st.success(f"✅ จองคิวสำเร็จ! หมายเลขคิว: {q_id}")
                    time.sleep(2)
                    st.rerun()
                else:
                    st.error("กรุณาใส่ชื่อก่อนรับคิว")

            col_ref1, col_ref2, col_ref3 = st.columns([1, 2, 1])
            with col_ref2:
                if st.button("🔄 รีเฟรชดูสถานะครัว"): st.rerun()
            st.stop()
    else:
        # --- Feature 3: แสดงคิวที่กำลังทำ (Top Queue Only) ---
        if not waiting_orders.empty:
            # ดึงออเดอร์บนสุดมาแสดงแค่อันเดียว (คิวที่ 1)
            top_order = waiting_orders.iloc[0]
            st.markdown(f"""
            <div class="kitchen-status-box">
                ✅ ครัวว่าง! สั่งปุ๊บ ได้ทานปั๊บ <br>
                <hr style="margin: 10px 0; border-top: 1px dashed #4CAF50;">
                👨‍🍳 กำลังปรุง: โต๊ะ {top_order['โต๊ะ']} (คุณ{top_order['ลูกค้า']}) <br>
                <span style="font-size:0.9em; color:#555;">(คิวถัดไปจะแสดงเมื่อคิวนี้เสร็จสิ้น)</span>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""<div class="kitchen-status-box">✅ ครัวว่าง! สั่งปุ๊บ ได้ทานปั๊บ</div>""",
                        unsafe_allow_html=True)

    st.markdown("---")

    c_t, c_c = st.columns(2)
    with c_c:
        st.markdown("### 👤 ชื่อลูกค้า")
        def_name = st.session_state.user_name if st.session_state.user_name else ""

        # --- State Persistence Logic ---
        current_input_name = st.session_state.get("customer_name_input", "")
        if current_input_name:
            default_name = current_input_name
        elif def_name:
            default_name = def_name
        else:
            default_name = ""

        cust_name = st.text_input("cust", value=default_name, placeholder="พิมพ์ชื่อเล่นของท่าน...",
                                  label_visibility="collapsed", key="customer_name_input")
        st.caption("⚠️ หากมีการจองคิวไว้แล้ว กรุณาใส่ชื่อที่ได้ทำการจองคิวไว้")

        # Auto-Resume Logic
        if cust_name:
            existing_order = orders_df[(orders_df['ลูกค้า'] == cust_name) & (orders_df['สถานะ'] == 'waiting')]
            if not existing_order.empty:
                found_table = existing_order.iloc[0]['โต๊ะ']
                if st.session_state.user_table != found_table:
                    st.session_state.user_table = found_table
                    st.session_state.user_name = cust_name
                    st.rerun()

    with c_t:
        st.markdown("### 📍 เลือกโต๊ะ")
        all_tables = tables_df['table_name'].tolist()
        available_tables = [t for t in all_tables if t not in busy_tables or t == st.session_state.user_table]
        tbl_options = ["--- เลือกโต๊ะ ---"] + available_tables

        # --- State Persistence for Selectbox ---
        current_select_table = st.session_state.get("table_select_box")
        default_idx = 0

        if current_select_table and current_select_table in tbl_options:
            default_idx = tbl_options.index(current_select_table)
        elif st.session_state.user_table and st.session_state.user_table in tbl_options:
            default_idx = tbl_options.index(st.session_state.user_table)

        table_no = st.selectbox("table", tbl_options, index=default_idx, label_visibility="collapsed",
                                key="table_select_box")

        remaining_count = len(all_tables) - len(busy_tables)
        if remaining_count < 0: remaining_count = 0

        st.markdown(f"<span style='color:green; font-weight:bold;'>🟢 เหลือโต๊ะว่าง: {remaining_count} โต๊ะ</span>",
                    unsafe_allow_html=True)

        if st.session_state.user_table and table_no == st.session_state.user_table:
            st.success(f"👋 ยินดีต้อนรับกลับ! รายการเดิมอยู่ที่: {table_no}")

    # --- Check Validation ---
    valid_input = True
    error_msg = ""

    if table_no == "--- เลือกโต๊ะ ---":
        valid_input = False

    if not cust_name:
        valid_input = False
    elif "ลูกค้าทั่วไป" in cust_name:
        valid_input = False
        error_msg = "❌ ไม่อนุญาตให้ใช้ชื่อ 'ลูกค้าทั่วไป' กรุณาระบุชื่ออื่น"

    if not valid_input:
        if error_msg:
            st.markdown(f"""<div class="warning-box">{error_msg}</div>""", unsafe_allow_html=True)
        else:
            st.markdown("""<div class="warning-box">🚨 กรุณา "เลือกโต๊ะ" และ "ใส่ชื่อ" เพื่อเริ่มสั่งอาหาร</div>""",
                        unsafe_allow_html=True)
        st.stop()

    st.markdown("<br>", unsafe_allow_html=True)

    if st.session_state.page == 'feedback':
        st.button("⬅️ กลับไปหน้าสั่งอาหาร", on_click=navigate_to, args=('customer', 'menu'))
        st.subheader("💬 เขียนติชม/สมุดเยี่ยม")
        st.info("ทุกความคิดเห็นของท่าน มีค่าสำหรับเราครับ 😊")
        with st.form("feed_form"):
            f_msg = st.text_area("ข้อความติชม (Review)", height=150)
            if st.form_submit_button("ส่งความคิดเห็น"):
                if f_msg:
                    save_feedback_entry(cust_name, f_msg)
                    st.success("ขอบคุณสำหรับความคิดเห็นครับ! ❤️")
                    time.sleep(1.5)
                    st.session_state.page = 'menu'
                    st.rerun()
                else:
                    st.error("กรุณาพิมพ์ข้อความก่อนส่งครับ")

    elif st.session_state.page == 'menu':
        st.subheader("📝 รายการอาหาร")
        cols = st.columns(2)
        for idx, row in menu_df.iterrows():
            with cols[idx % 2]:
                with st.container(border=True):
                    is_stock = row.get('in_stock', True)
                    img_src = str(row['img'])

                    if not is_stock:
                        try:
                            st.markdown(f"""
                            <div style="position:relative;">
                                <img src="{img_src}" style="width:100%; border-radius:8px; filter: grayscale(100%); opacity: 0.5;">
                                <div style="position:absolute; top:50%; left:50%; transform: translate(-50%, -50%); 
                                            background:rgba(255,255,255,0.9); padding:5px 15px; border-radius:5px; 
                                            color:red; font-weight:bold; border:2px solid red;">
                                    ❌ สินค้าหมด
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                        except:
                            st.image("https://placehold.co/400")
                    else:
                        try:
                            st.image(img_src, use_container_width=True)
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
                         use_container_width=True, on_click=navigate_to, args=('customer', 'cart')):
                pass

    elif st.session_state.page == 'cart':
        st.button("⬅️ เลือกอาหารเพิ่ม", on_click=navigate_to, args=('customer', 'menu'))
        st.markdown(f"""
        <div style="background-color:#5D4037; color:white; padding:15px; border-radius:10px; text-align:center; margin-bottom:20px;">
            <h3>🛒 สรุปรายการสั่งซื้อ</h3>
            <p>โต๊ะ: {table_no} | คุณ: {cust_name}</p>
        </div>
        """, unsafe_allow_html=True)

        if len(st.session_state.basket) > 0:
            counts = Counter(item['name'] for item in st.session_state.basket)
            unique_items = {item['name']: item for item in st.session_state.basket}

            total_price = 0
            for name, count in counts.items():
                item = unique_items[name]
                item_total = item['price'] * count
                total_price += item_total

                with st.container(border=True):
                    c1, c2 = st.columns([1, 2])
                    with c1:
                        try:
                            st.image(item['img'], use_container_width=True)
                        except:
                            st.image("https://placehold.co/100")
                    with c2:
                        st.markdown(f"**{name}**")
                        st.caption(f"{item['price']} x {count} = {item_total} บ.")

                    st.write("")
                    b1, b2, b3 = st.columns([1, 1, 1])
                    with b1:
                        if st.button("➖", key=f"dec_{name}", use_container_width=True):
                            for i, x in enumerate(st.session_state.basket):
                                if x['name'] == name:
                                    del st.session_state.basket[i]
                                    break
                            st.rerun()
                    with b2:
                        st.markdown(
                            f"<div style='text-align:center; font-size:20px; font-weight:bold; padding-top:5px;'>{count}</div>",
                            unsafe_allow_html=True)
                    with b3:
                        if st.button("➕", key=f"inc_{name}", use_container_width=True):
                            st.session_state.basket.append(item)
                            st.rerun()

            st.markdown("---")
            st.markdown(f"### 💰 รวมทั้งสิ้น: {total_price} บาท")
            note = st.text_area("📝 หมายเหตุถึงครัว (ไม่ใส่ผัก, เผ็ดน้อย)")

            if st.button("✅ ยืนยันการสั่ง (Confirm)", type="primary", use_container_width=True):
                if is_queue_mode and not can_order:
                    st.error("🚫 ยังไม่ถึงคิวของคุณครับ กรุณารอเรียกคิว")
                else:
                    now_str = get_thai_time().strftime("%d/%m/%Y %H:%M")
                    items = ", ".join([f"{name}(x{count})" for name, count in counts.items()])

                    status = save_order({"เวลา": now_str, "โต๊ะ": table_no, "ลูกค้า": cust_name, "รายการอาหาร": items,
                                         "ยอดรวม": total_price, "หมายเหตุ": note, "สถานะ": "waiting"})

                    st.session_state.user_table = table_no
                    st.session_state.user_name = cust_name

                    body_intro = "🔔 Order เพิ่มเติม" if status == "merged" else "🔔 Order ใหม่"
                    body = f"โต๊ะ: {table_no}\nลูกค้า: {cust_name}\nเวลา: {now_str}\n\n{items}\n\nสั่งรอบนี้: {total_price} บาท\nNote: {note}"
                    send_email_notification(f"{body_intro}: {table_no}", body)

                    st.session_state.basket = []
                    navigate_to('customer', 'menu')
                    st.balloons()
                    st.success("ส่งออเดอร์แล้ว!")
                    time.sleep(2)
        else:
            st.info("ตะกร้ายังว่างอยู่เลย เลือกอาหารก่อนนะครับ")
            if st.button("ไปเลือกอาหาร"):
                navigate_to('customer', 'menu')