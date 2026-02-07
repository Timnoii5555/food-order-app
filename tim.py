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
SENDER_EMAIL = 'jaskaikai4@gmail.com'
SENDER_PASSWORD = 'zqyx nqdk ygww drpp'
RECEIVER_EMAIL = 'jaskaikai4@gmail.com'

ORDER_CSV = 'order_history.csv'
MENU_CSV = 'menu_data.csv'
TABLES_CSV = 'tables_data.csv'
CONTACT_CSV = 'contact_data.csv'
QUEUE_CSV = 'queue_data.csv'
FEEDBACK_CSV = 'feedback_data.csv'
BANNER_FOLDER = 'banner_images'
IMAGE_FOLDER = 'uploaded_images'

KITCHEN_LIMIT = 10
DEFAULT_CUST_NAME = "ลูกค้าทั่วไป"

if not os.path.exists(BANNER_FOLDER): os.makedirs(BANNER_FOLDER)
if not os.path.exists(IMAGE_FOLDER): os.makedirs(IMAGE_FOLDER)


# ================= 2. ฟังก์ชันจัดการข้อมูล =================

def get_thai_time():
    """ดึงเวลาปัจจุบันของประเทศไทยแบบ Real-time"""
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


def load_menu():
    if not os.path.exists(MENU_CSV):
        # ข้อมูลเริ่มต้น พร้อมหมวดหมู่ใหม่
        default_data = [
            {"name": "หมูหมัก", "price": 120,
             "img": "https://images.unsplash.com/photo-1615937657715-bc7b4b7962c1?auto=format&fit=crop&w=500&q=60",
             "category": "เนื้อ (Meat)", "in_stock": True},
            {"name": "น้ำซุปต้มยำ", "price": 50, "img": "https://placehold.co/400", "category": "น้ำซุป (Soup)",
             "in_stock": True},
        ]
        df = pd.DataFrame(default_data)
        df.to_csv(MENU_CSV, index=False)
    try:
        df = pd.read_csv(MENU_CSV)
        if 'in_stock' not in df.columns: df['in_stock'] = True
    except:
        df = pd.DataFrame(columns=["name", "price", "img", "category", "in_stock"])
    return df


def load_tables():
    if not os.path.exists(TABLES_CSV):
        default_tables = ["โต๊ะ 1", "โต๊ะ 2", "โต๊ะ 3", "โต๊ะ 4", "กลับบ้าน"]
        df = pd.DataFrame(default_tables, columns=["table_name"])
        df.to_csv(TABLES_CSV, index=False)
    return pd.read_csv(TABLES_CSV)


def load_contacts():
    if not os.path.exists(CONTACT_CSV):
        data = {"phone": "064-448-55549", "line": "@timnoishabu", "facebook": "https://facebook.com",
                "instagram": "https://instagram.com"}
        pd.DataFrame([data]).to_csv(CONTACT_CSV, index=False)
        return data
    try:
        return pd.read_csv(CONTACT_CSV).iloc[0].to_dict()
    except:
        return {"phone": "", "line": "", "facebook": "", "instagram": ""}


def save_contacts(data_dict):
    pd.DataFrame([data_dict]).to_csv(CONTACT_CSV, index=False)


def load_queue():
    if not os.path.exists(QUEUE_CSV):
        pd.DataFrame(columns=["queue_id", "customer_name", "timestamp"]).to_csv(QUEUE_CSV, index=False)
    return pd.read_csv(QUEUE_CSV)


def add_to_queue(name):
    df = load_queue()
    if not df.empty and name in df['customer_name'].values:
        return df[df['customer_name'] == name].iloc[0]['queue_id'], True
    last_id = 100
    if not df.empty:
        try:
            last_id = int(str(df.iloc[-1]['queue_id']).split('-')[1])
        except:
            pass
    new_id = f"Q-{last_id + 1}"
    new_data = {"queue_id": new_id, "customer_name": name, "timestamp": get_thai_time().strftime("%Y-%m-%d %H:%M:%S")}
    pd.concat([df, pd.DataFrame([new_data])], ignore_index=True).to_csv(QUEUE_CSV, index=False)
    return new_id, False


def pop_queue():
    df = load_queue()
    if not df.empty:
        df.iloc[1:].to_csv(QUEUE_CSV, index=False)


# --- ระบบ Feedback (ใช้เวลาไทย) ---
def load_feedback():
    if not os.path.exists(FEEDBACK_CSV):
        pd.DataFrame(columns=["timestamp", "customer_name", "message"]).to_csv(FEEDBACK_CSV, index=False)
    return pd.read_csv(FEEDBACK_CSV)


def save_feedback_entry(name, message):
    df = load_feedback()
    new_entry = {
        "timestamp": get_thai_time().strftime("%d/%m/%Y %H:%M:%S"),
        "customer_name": name,
        "message": message
    }
    pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True).to_csv(FEEDBACK_CSV, index=False)


def delete_feedback_entry(index):
    df = load_feedback()
    df.drop(index).to_csv(FEEDBACK_CSV, index=False)


def save_order(data):
    df = load_orders()
    mask = (df['โต๊ะ'] == data['โต๊ะ']) & (df['สถานะ'] == 'waiting')
    if mask.any():
        idx = df.index[mask][0]
        # ทบรายการอาหาร
        df.at[idx, 'รายการอาหาร'] = f"{df.at[idx, 'รายการอาหาร']}, {data['รายการอาหาร']}"
        # ทบราคา (แก้ไขบั๊กราคาไม่เพิ่ม)
        try:
            old_p = float(df.at[idx, 'ยอดรวม'])
        except:
            old_p = 0.0
        df.at[idx, 'ยอดรวม'] = old_p + float(data['ยอดรวม'])
        # ทบหมายเหตุ
        old_n = str(df.at[idx, 'หมายเหตุ'])
        new_n = str(data['หมายเหตุ'])
        if new_n and old_n != 'nan':
            df.at[idx, 'หมายเหตุ'] = f"{old_n} | {new_n}"
        elif new_n:
            df.at[idx, 'หมายเหตุ'] = new_n

        df.to_csv(ORDER_CSV, index=False)
        return "merged"
    else:
        pd.concat([df, pd.DataFrame([data])], ignore_index=True).to_csv(ORDER_CSV, index=False)
        return "new"


def save_image(uploaded_file):
    if uploaded_file is not None:
        timestamp = int(time.time())
        file_ext = uploaded_file.name.split('.')[-1]
        new_filename = f"img_{timestamp}.{file_ext}"
        file_path = os.path.join(IMAGE_FOLDER, new_filename)
        with open(file_path, "wb") as f: f.write(uploaded_file.getbuffer())
        return file_path
    return None


def save_promo_banner(uploaded_file, index):
    if uploaded_file is not None:
        filename = f"banner_{index}.png"
        filepath = os.path.join(BANNER_FOLDER, filename)
        with open(filepath, "wb") as f: f.write(uploaded_file.getbuffer())
        return True
    return False


def get_image_base64(path):
    if os.path.exists(path):
        with open(path, "rb") as f: return f"data:image/png;base64,{base64.b64encode(f.read()).decode()}"
    return ""


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
        server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_string())
        server.quit()
    except:
        pass


def sanitize_link(link):
    if not link: return "#"
    link = str(link).strip()
    return link if link.startswith(("http://", "https://")) else "https://" + link


# ================= 3. UI & CSS =================
st.set_page_config(page_title="TimNoi Shabu", page_icon="🍲", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;500;700&display=swap');
    html, body, [class*="css"] { font-family: 'Sarabun', sans-serif; background-color: #FDFBF7; }
    .stButton>button { border-radius: 8px; font-weight: bold; background-color: #8D6E63; color: white; border: none; height: 50px; }
    .stButton>button:hover { background-color: #6D4C41; color: #FFECB3; }
    .queue-box { background: linear-gradient(135deg, #3E2723 0%, #5D4037 100%); color: white; padding: 30px; border-radius: 20px; text-align: center; margin-bottom: 20px; }
    .contact-row { display: flex; align-items: center; margin-bottom: 12px; background-color: white; padding: 12px; border-radius: 12px; border: 1px solid #eee; }
    .contact-icon { width: 32px; height: 32px; margin-right: 15px; }
    .sales-box { background-color: #FFF3E0; border: 2px solid #FFB74D; color: #E65100; padding: 20px; border-radius: 12px; text-align: center; margin-bottom: 20px; }
    .sales-number { font-size: 48px; font-weight: bold; color: #BF360C; }
</style>
""", unsafe_allow_html=True)

# ================= 4. โหลดข้อมูล & State =================
if 'page' not in st.session_state: st.session_state.page = 'menu'
if 'app_mode' not in st.session_state: st.session_state.app_mode = 'customer'
if 'my_queue_id' not in st.session_state: st.session_state.my_queue_id = None
if 'basket' not in st.session_state: st.session_state.basket = []

menu_df = load_menu()
orders_df = load_orders()
contact_info = load_contacts()
queue_df = load_queue()
feedback_df = load_feedback()
tables_df = load_tables()

waiting_orders = orders_df[orders_df['สถานะ'] == 'waiting']
kitchen_load = len(waiting_orders)

# ================= 5. ส่วนหัว =================
c_logo, c_name, c_menu = st.columns([1.3, 2, 0.5])
with c_logo:
    if os.path.exists("logo.png"):
        st.image("logo.png", width=320)
    else:
        st.markdown("<h1>🍲</h1>", unsafe_allow_html=True)
with c_name:
    st.markdown(f"""
        <div style="display: flex; flex-direction: column; justify-content: center; height: 220px;">
            <h1 style='color:#3E2723; font-size:50px; margin:0;'>TimNoi Shabu</h1>
            <p style='color:#8D6E63; font-size:20px; font-weight:bold;'>ร้านนี้ไม่มีหมูเพราะที่เห็นเป็นเนื้อหมา</p>
            <div style='margin-top:10px; border-top: 2px solid #D7CCC8;'>
                <p style='margin:5px 0;'>🕒 00:00 - 23:59 น. | 📞 {contact_info.get('phone', '-')}</p>
            </div>
        </div>
    """, unsafe_allow_html=True)
with c_menu:
    with st.popover("☰"):
        if st.button("🏠 หน้าลูกค้า", use_container_width=True): st.session_state.update(app_mode='customer',
                                                                                        page='menu'); st.rerun()
        if st.button("💬 เขียนติชม", use_container_width=True): st.session_state.update(app_mode='customer',
                                                                                       page='feedback'); st.rerun()
        if st.button("⚙️ จัดการร้าน", use_container_width=True): st.session_state.app_mode = 'admin_login'; st.rerun()
        st.markdown("---")
        fb_url = sanitize_link(contact_info.get('facebook', ''))
        ig_url = sanitize_link(contact_info.get('instagram', ''))
        st.markdown(f"""
        <div class="contact-row"><img src="https://cdn-icons-png.flaticon.com/512/5968/5968764.png" class="contact-icon"><a href="{fb_url}" target="_blank" class="contact-link">Facebook</a></div>
        <div class="contact-row"><img src="https://cdn-icons-png.flaticon.com/512/3955/3955024.png" class="contact-icon"><a href="{ig_url}" target="_blank" class="contact-link">Instagram</a></div>
        """, unsafe_allow_html=True)

st.divider()

# ================= 6. Controller =================

if st.session_state.app_mode == 'admin_login':
    st.subheader("🔐 เข้าสู่ระบบ")
    pw = st.text_input("รหัสผ่าน", type="password")
    if pw == "090090op": st.session_state.app_mode = 'admin_dashboard'; st.rerun()

elif st.session_state.app_mode == 'admin_dashboard':
    st.subheader("⚙️ จัดการร้าน")
    if st.button("🚪 ออก"): st.session_state.app_mode = 'customer'; st.rerun()

    tabs = st.tabs(["👨‍🍳 ครัว (Auto)", "📢 โปรโมชั่น", "📦 สต็อก", "📝 เมนู", "📊 ยอดขาย", "📞 ติดต่อ", "💬 รีวิว"])

    with tabs[0]:  # หน้าครัว รีเฟรชทุก 1 นาที
        st.markdown(
            f"**สถานะครัว: {kitchen_load}/{KITCHEN_LIMIT}** | อัปเดตล่าสุด: {get_thai_time().strftime('%H:%M:%S')}")
        st.progress(min(kitchen_load / KITCHEN_LIMIT, 1.0))

        if kitchen_load > 0:
            for idx, row in waiting_orders.iterrows():
                with st.container(border=True):
                    c1, c2 = st.columns([3, 1])
                    with c1:
                        st.write(f"**{row['โต๊ะ']}** | {row['ลูกค้า']} | 💰 {float(row['ยอดรวม']):,.2f} บ.")
                        st.caption(f"รายการ: {row['รายการอาหาร']}")
                        if str(row['หมายเหตุ']) != 'nan' and row['หมายเหตุ']: st.warning(f"📝 {row['หมายเหตุ']}")
                    with c2:
                        if st.button("✅ จ่ายแล้ว", key=f"pay_{idx}", use_container_width=True):
                            orders_df.at[idx, 'สถานะ'] = 'paid';
                            orders_df.to_csv(ORDER_CSV, index=False);
                            st.rerun()
                        if st.button("❌ ยกเลิก", key=f"can_{idx}", use_container_width=True):
                            orders_df.at[idx, 'สถานะ'] = 'cancelled';
                            orders_df.to_csv(ORDER_CSV, index=False);
                            st.rerun()
        else:
            st.info("ไม่มีออเดอร์ค้าง")

        time.sleep(60)  # Auto-refresh ทุก 1 นาที
        st.rerun()

    with tabs[1]:  # โปรโมชั่น
        for i in range(1, 6):
            c1, c2 = st.columns(2)
            with c1:
                up = st.file_uploader(f"รูป {i}", type=['png', 'jpg'], key=f"up_{i}")
                if up: save_promo_banner(up, i); st.rerun()
            with c2:
                p = os.path.join(BANNER_FOLDER, f"banner_{i}.png")
                if os.path.exists(p):
                    st.image(p, width=200)
                    if st.button(f"ลบ {i}", key=f"del_{i}"): os.remove(p); st.rerun()

    with tabs[2]:  # สต็อก
        st.write("📦 จัดการสต็อก")
        edit_s = st.data_editor(menu_df[['name', 'in_stock']], disabled=["name"], hide_index=True)
        if st.button("💾 บันทึกสต็อก"):
            menu_df['in_stock'] = edit_s['in_stock'];
            menu_df.to_csv(MENU_CSV, index=False);
            st.toast("บันทึกแล้ว")

    with tabs[3]:  # เมนู
        st.write("#### ➕ เพิ่มเมนู")
        with st.form("add_m"):
            n = st.text_input("ชื่อเมนู")
            p = st.number_input("ราคา", min_value=0)
            # หมวดหมู่ใหม่ (ไทย+Eng) + น้ำซุป
            cat_opts = ["เนื้อ (Meat)", "ทะเล (Seafood)", "ผัก (Veggie)", "ของทานเล่น (Snack)", "น้ำซุป (Soup)"]
            c = st.selectbox("หมวด", cat_opts)
            uploaded_file = st.file_uploader("รูปภาพ", type=['png', 'jpg', 'jpeg'])
            if st.form_submit_button("บันทึก"):
                final_path = "https://placehold.co/400"
                if uploaded_file: final_path = save_image(uploaded_file) or final_path
                new_row = pd.DataFrame([{"name": n, "price": p, "img": final_path, "category": c, "in_stock": True}])
                pd.concat([menu_df, new_row], ignore_index=True).to_csv(MENU_CSV, index=False)
                st.success("เพิ่มแล้ว");
                st.rerun()

        st.write("#### ❌ ลบเมนู")
        dm = st.selectbox("เลือกเมนู", ["-"] + menu_df['name'].tolist())
        if st.button("ลบเมนู") and dm != "-":
            menu_df[menu_df['name'] != dm].to_csv(MENU_CSV, index=False);
            st.rerun()

    with tabs[4]:  # ยอดขาย
        orders_df['ยอดรวม'] = pd.to_numeric(orders_df['ยอดรวม'], errors='coerce').fillna(0)
        today = get_thai_time().strftime("%d/%m/%Y")
        ds = orders_df[(orders_df['สถานะ'] == 'paid') & (orders_df['เวลา'].str.contains(today))]
        st.markdown(
            f'<div class="sales-box">ยอดขายวันนี้<br><h2 style="margin:0;">{ds["ยอดรวม"].sum():,.2f} ฿</h2></div>',
            unsafe_allow_html=True)
        st.dataframe(ds[['เวลา', 'โต๊ะ', 'ลูกค้า', 'ยอดรวม', 'รายการอาหาร']], hide_index=True)

    with tabs[5]:  # ติดต่อ
        with st.form("con"):
            ph = st.text_input("โทร", contact_info.get('phone', ''));
            li = st.text_input("Line", contact_info.get('line', ''))
            fb = st.text_input("FB", contact_info.get('facebook', ''));
            ig = st.text_input("IG", contact_info.get('instagram', ''))
            if st.form_submit_button("บันทึก"):
                save_contacts({"phone": ph, "line": li, "facebook": fb, "instagram": ig});
                st.success("บันทึกแล้ว");
                st.rerun()

    with tabs[6]:  # รีวิว
        st.subheader("💬 รีวิวล่าสุด")
        feedback_df = load_feedback()  # โหลดใหม่เสมอ
        if not feedback_df.empty:
            for idx, row in feedback_df.iterrows():
                with st.container(border=True):
                    c1, c2 = st.columns([4, 1])
                    with c1:
                        st.write(f"**{row['customer_name']}**")
                        st.caption(f"🕒 {row['timestamp']}")  # เวลาไทย
                        st.write(row['message'])
                    with c2:
                        if st.button("ลบ", key=f"dfb_{idx}"): delete_feedback_entry(idx); st.rerun()
        else:
            st.info("ไม่มีรีวิว")

# === Customer Page ===
else:
    # --- 🚦 ระบบคิว (ครัวเต็ม >= 10) ---
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
                    if st.button("🔄 อัปเดตคิว"): st.rerun()
                    st.stop()
            except:
                st.session_state.my_queue_id = None; st.rerun()

    if show_booking_ui:
        st.error(f"🚫 ขออภัยครับ ขณะนี้ครัวเต็ม ({kitchen_load}/{KITCHEN_LIMIT}) กรุณารับคิวออนไลน์")
        q_name = st.text_input("ระบุชื่อของคุณเพื่อรับคิวออนไลน์", value="")
        st.caption("ℹ️ หากมีการจองคิวไว้แล้ว กรุณาใส่ชื่อเดิมที่เคยได้จองไว้")
        if st.button("🎫 รับคิว / เช็คคิวเดิม", type="primary", use_container_width=True):
            if q_name.strip() and q_name != DEFAULT_CUST_NAME:
                qid, is_old = add_to_queue(q_name)
                st.session_state.my_queue_id = qid
                st.rerun()
            else:
                st.warning("⚠️ กรุณาใส่ชื่อที่จองคิวไว้")
        st.stop()

    # --- 🍜 หน้าสั่งอาหาร ---
    # Banner Carousel (8 วินาที)
    imgs = [get_image_base64(os.path.join(BANNER_FOLDER, f"banner_{i}.png")) for i in range(1, 6) if
            os.path.exists(os.path.join(BANNER_FOLDER, f"banner_{i}.png"))]
    if imgs:
        slides = "".join([
                             f'<div class="mySlides fade" style="display:{"block" if i == 0 else "none"};"><img src="{img}" style="width:100%; border-radius:15px;"></div>'
                             for i, img in enumerate(imgs)])
        components.html(
            f'<!DOCTYPE html><html><head><style>.mySlides {{display:none;}} img{{vertical-align:middle;}} .fade {{animation:f 1.5s;}} @keyframes f{{from{{opacity:.4}} to{{opacity:1}}}}</style></head><body>{slides}<script>let s=0;show();function show(){{let i,x=document.getElementsByClassName("mySlides");for(i=0;i<x.length;i++)x[i].style.display="none";s++;if(s>x.length)s=1;x[s-1].style.display="block";setTimeout(show, 8000);}}</script></body></html>',
            height=320)

    st.subheader("🛒 เริ่มสั่งอาหาร")
    c_t, c_c = st.columns(2)
    with c_t:
        tbls = tables_df['table_name'].tolist() if not tables_df.empty else ["โต๊ะ 1"]
        table_no = st.selectbox("📍 เลือกโต๊ะ", tbls)
    with c_c:
        cust_name = st.text_input("👤 ชื่อของคุณ", value="", placeholder="ใส่ชื่อที่จองไว้...")
        st.caption("ℹ️ หากมีการจองคิวไว้แล้ว กรุณาใส่ชื่อเดิมที่เคยได้จองไว้")

    # 🔥 [STRICT VALIDATION] ตรวจสอบชื่อลูกค้า 🔥
    if not cust_name.strip() or cust_name == DEFAULT_CUST_NAME:
        st.warning("⚠️ กรุณาใส่ชื่อที่จองคิวไว้")
        st.stop()

    if st.session_state.page == 'feedback':
        st.subheader("💬 เขียนติชม")
        with st.form("fb"):
            m = st.text_area("ข้อความ")
            if st.form_submit_button("ส่ง"):
                if m: save_feedback_entry(cust_name, m); st.success("ส่งแล้ว!"); time.sleep(
                    1); st.session_state.page = 'menu'; st.rerun()
        if st.button("⬅️ กลับ"): st.session_state.page = 'menu'; st.rerun()

    elif st.session_state.page == 'menu':
        menu_df = pd.read_csv(MENU_CSV)
        cols = st.columns(2)
        for i, r in menu_df.iterrows():
            with cols[i % 2]:
                with st.container(border=True):
                    st.image(r['img'], use_container_width=True)
                    st.write(f"**{r['name']}** - {r['price']} บ.")
                    st.caption(r['category'])
                    if st.button("🛒 ใส่ตะกร้า", key=f"add_{i}", use_container_width=True):
                        st.session_state.basket.append(r.to_dict());
                        st.toast("เพิ่มแล้ว")
        if st.session_state.basket:
            if st.button(f"🛒 สรุปออเดอร์ ({len(st.session_state.basket)})", type="primary", use_container_width=True):
                st.session_state.page = 'cart';
                st.rerun()

    elif st.session_state.page == 'cart':
        counts = Counter(x['name'] for x in st.session_state.basket)
        unique = {x['name']: x for x in st.session_state.basket}
        total = sum(x['price'] for x in st.session_state.basket)

        st.subheader("🛒 ตะกร้าสินค้า")
        for name, count in counts.items():
            st.write(f"{name} x {count} = {unique[name]['price'] * count} บ.")

        st.divider()
        st.write(f"### รวมทั้งสิ้น: {total} บาท")
        note = st.text_area("📝 หมายเหตุถึงครัว")

        if st.button("✅ ยืนยันการสั่ง", type="primary", use_container_width=True):
            if kitchen_load >= KITCHEN_LIMIT:
                st.error("🚫 ครัวเต็มกะทันหัน กรุณารอสักครู่")
            else:
                items_str = ", ".join([f"{n}(x{c})" for n, c in counts.items()])
                # บันทึกออเดอร์
                save_order({
                    "เวลา": get_thai_time().strftime("%H:%M"),
                    "โต๊ะ": table_no,
                    "ลูกค้า": cust_name,
                    "รายการอาหาร": items_str,
                    "ยอดรวม": total,
                    "หมายเหตุ": note,
                    "สถานะ": "waiting"
                })
                if st.session_state.my_queue_id:
                    pop_queue();
                    st.session_state.my_queue_id = None
                st.session_state.basket = [];
                st.session_state.page = 'menu'
                st.balloons();
                st.success("สั่งเรียบร้อย!");
                time.sleep(2);
                st.rerun()
        if st.button("⬅️ กลับ"): st.session_state.page = 'menu'; st.rerun()