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
IMAGE_FOLDER = 'uploaded_images'
BANNER_FOLDER = 'banner_images'

if not os.path.exists(IMAGE_FOLDER): os.makedirs(IMAGE_FOLDER)
if not os.path.exists(BANNER_FOLDER): os.makedirs(BANNER_FOLDER)

KITCHEN_LIMIT = 10
DEFAULT_CUST_NAME = "ลูกค้าทั่วไป"


# ================= 2. ฟังก์ชันจัดการข้อมูล =================

def get_thai_time():
    tz = pytz.timezone('Asia/Bangkok')
    return datetime.now(tz)


def load_menu():
    if not os.path.exists(MENU_CSV):
        default_data = [
            {"name": "หมูหมัก", "price": 120,
             "img": "https://images.unsplash.com/photo-1615937657715-bc7b4b7962c1?auto=format&fit=crop&w=500&q=60",
             "category": "เนื้อ (Meat)", "in_stock": True},
            {"name": "หมูสามชั้น", "price": 89,
             "img": "https://images.unsplash.com/photo-1600891964092-4316c288032e?auto=format&fit=crop&w=500&q=60",
             "category": "เนื้อ (Meat)", "in_stock": True},
            {"name": "กุ้งสด", "price": 150,
             "img": "https://images.unsplash.com/photo-1565680018434-b513d5e5fd47?auto=format&fit=crop&w=500&q=60",
             "category": "ทะเล (Seafood)", "in_stock": True},
            {"name": "ผักกวางตุ้ง", "price": 40,
             "img": "https://images.unsplash.com/photo-1544025162-d76694265947?auto=format&fit=crop&w=500&q=60",
             "category": "ผัก (Veggie)", "in_stock": True},
        ]
        df = pd.DataFrame(default_data)
        df.to_csv(MENU_CSV, index=False)
    try:
        df = pd.read_csv(MENU_CSV)
    except:
        df = pd.DataFrame(columns=["name", "price", "img", "category", "in_stock"])
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
    try:
        df = pd.read_csv(ORDER_CSV)
        if not all(col in df.columns for col in cols):
            df = pd.DataFrame(columns=cols)
    except:
        df = pd.DataFrame(columns=cols)
    return df


def load_contacts():
    if not os.path.exists(CONTACT_CSV):
        data = {"phone": "064-448-55549", "line": "@timnoishabu", "facebook": "https://facebook.com",
                "instagram": "https://instagram.com"}
        df = pd.DataFrame([data])
        df.to_csv(CONTACT_CSV, index=False)
        return data
    else:
        try:
            return pd.read_csv(CONTACT_CSV).iloc[0].to_dict()
        except:
            return {"phone": "", "line": "", "facebook": "", "instagram": ""}


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
            last_id = int(df.iloc[-1]['queue_id'].split('-')[1])
        except:
            pass
    new_id = f"Q-{last_id + 1}"
    new_data = {"queue_id": new_id, "customer_name": name, "timestamp": get_thai_time().strftime("%Y-%m-%d %H:%M:%S")}
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
    new_entry = {"timestamp": get_thai_time().strftime("%d/%m/%Y %H:%M:%S"), "customer_name": name, "message": message}
    df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
    df.to_csv(FEEDBACK_CSV, index=False)


def delete_feedback_entry(index):
    df = load_feedback()
    df = df.drop(index)
    df.to_csv(FEEDBACK_CSV, index=False)


def save_image(uploaded_file):
    if uploaded_file is not None:
        timestamp = int(time.time())
        file_path = os.path.join(IMAGE_FOLDER, f"img_{timestamp}.png")
        with open(file_path, "wb") as f: f.write(uploaded_file.getbuffer())
        return file_path
    return None


def get_image_base64(path):
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
        server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_string())
        server.quit()
    except:
        pass


def save_order(data):
    df = load_orders()
    mask = (df['โต๊ะ'] == data['โต๊ะ']) & (df['สถานะ'] == 'waiting')
    if mask.any():
        idx = df.index[mask][0]
        old_items = str(df.at[idx, 'รายการอาหาร'])
        new_items = old_items + ", " + str(data['รายการอาหาร'])
        try:
            old_p = float(df.at[idx, 'ยอดรวม'])
        except:
            old_p = 0.0
        new_p = old_p + float(data['ยอดรวม'])
        old_n = str(df.at[idx, 'หมายเหตุ'])
        if old_n == 'nan': old_n = ""
        new_n = data['หมายเหตุ']
        final_n = f"{old_n} | {new_n}" if new_n and old_n else (new_n if new_n else old_n)
        df.at[idx, 'รายการอาหาร'] = new_items
        df.at[idx, 'ยอดรวม'] = new_p
        df.at[idx, 'หมายเหตุ'] = final_n
        df.at[idx, 'เวลา'] = data['เวลา']
        df.to_csv(ORDER_CSV, index=False)
        res = "merged"
    else:
        df_new = pd.DataFrame([data])
        df_final = pd.concat([df, df_new], ignore_index=True)
        df_final.to_csv(ORDER_CSV, index=False)
        res = "new"

    if 'my_queue_id' in st.session_state and st.session_state.my_queue_id:
        q_df = load_queue()
        if not q_df.empty and q_df.iloc[0]['queue_id'] == st.session_state.my_queue_id:
            pop_queue()
            st.session_state.my_queue_id = None
    return res


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
    header, footer {visibility: hidden;}
    .stButton>button { border-radius: 8px; font-weight: bold; background-color: #8D6E63; color: white; border: none; }
    .stButton>button:hover { background-color: #6D4C41; color: #FFECB3; }
    .customer-queue-box { background: linear-gradient(135deg, #3E2723 0%, #5D4037 100%); color: white; padding: 20px; border-radius: 16px; text-align: center; margin-bottom: 20px; }
    .queue-big-number { font-size: 56px; font-weight: 800; color: white; }
    .queue-empty { background-color: #E8F5E9; border: 2px dashed #4CAF50; color: #2E7D32; padding: 15px; border-radius: 12px; text-align: center; font-weight: bold; }
    .queue-full { background-color: #FFEBEE; border: 2px dashed #EF5350; color: #C62828; padding: 15px; border-radius: 12px; text-align: center; font-weight: bold; }
    .sales-box { background-color: #FFF3E0; border: 2px solid #FFB74D; color: #E65100; padding: 20px; border-radius: 12px; text-align: center; margin-bottom: 20px; }
    .sales-number { font-size: 48px; font-weight: bold; color: #BF360C; }
    .contact-row { display: flex; align-items: center; margin-bottom: 12px; background-color: white; padding: 12px; border-radius: 12px; border: 1px solid #eee; }
    .contact-icon { width: 32px; height: 32px; margin-right: 15px; }
    .contact-link { text-decoration: none; color: #333; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# ================= 4. โหลดข้อมูล & State =================
if 'basket' not in st.session_state: st.session_state.basket = []
if 'page' not in st.session_state: st.session_state.page = 'menu'
if 'app_mode' not in st.session_state: st.session_state.app_mode = 'customer'
if 'my_queue_id' not in st.session_state: st.session_state.my_queue_id = None

menu_df = load_menu()
tables_df = load_tables()
orders_df = load_orders()
contact_info = load_contacts()
queue_df = load_queue()
feedback_df = load_feedback()

waiting_orders = orders_df[orders_df['สถานะ'] == 'waiting']
kitchen_load = len(waiting_orders)
is_queue_mode = kitchen_load >= KITCHEN_LIMIT
can_order = kitchen_load < KITCHEN_LIMIT
waiting_q_count = 0

if not queue_df.empty:
    is_queue_mode = True
    can_order = False
    if st.session_state.my_queue_id == queue_df.iloc[0]['queue_id']:
        if kitchen_load < KITCHEN_LIMIT: can_order = True
    if st.session_state.my_queue_id:
        try:
            waiting_q_count = queue_df.index[queue_df['queue_id'] == st.session_state.my_queue_id].tolist()[0]
        except:
            waiting_q_count = len(queue_df)

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
            <h1 style='color:#3E2723; font-size:50px; margin:0; line-height:1; font-weight:800;'>TimNoi Shabu</h1>
            <p style='color:#8D6E63; font-size:20px; margin:5px 0 0 0; font-weight:bold;'>ร้านนี้ไม่มีหมูเพราะที่เห็นเป็นเนื้อหมา</p>
            <div style='margin-top:15px; border-top: 2px solid #D7CCC8; padding-top:10px;'>
                <p style='color:#5D4037; font-size:16px; margin:0;'>🕒 เปิดบริการ: 00:00 - 23:59 น.</p>
                <p style='color:#5D4037; font-size:16px; margin:0;'>📞 โทร: {contact_info.get('phone', '-')}</p>
            </div>
        </div>
    """, unsafe_allow_html=True)
with c_menu:
    with st.popover("☰", use_container_width=True):
        if st.button("🏠 หน้าลูกค้า", use_container_width=True): st.session_state.update(app_mode='customer',
                                                                                        page='menu'); st.rerun()
        if st.button("💬 เขียนรีวิว", use_container_width=True): st.session_state.update(app_mode='customer',
                                                                                        page='feedback'); st.rerun()
        if st.button("⚙️ จัดการร้าน", use_container_width=True): st.session_state.update(
            app_mode='admin_login'); st.rerun()
        st.markdown("---")
        fb_url = sanitize_link(contact_info.get('facebook', ''))
        ig_url = sanitize_link(contact_info.get('instagram', ''))
        st.markdown(f"""
        <div class="contact-row"><img src="https://cdn-icons-png.flaticon.com/512/5968/5968764.png" class="contact-icon"><a href="{fb_url}" target="_blank" class="contact-link">Facebook</a></div>
        <div class="contact-row"><img src="https://cdn-icons-png.flaticon.com/512/3955/3955024.png" class="contact-icon"><a href="{ig_url}" target="_blank" class="contact-link">Instagram</a></div>
        """, unsafe_allow_html=True)

st.markdown("---")

# ================= 6. Controller =================

if st.session_state.app_mode == 'admin_login':
    st.subheader("🔐 เข้าสู่ระบบ")
    password = st.text_input("🔑 รหัสผ่าน", type="password")
    if password == "090090op": st.session_state.update(app_mode='admin_dashboard'); st.rerun()

elif st.session_state.app_mode == 'admin_dashboard':
    st.subheader("⚙️ ระบบจัดการร้าน")
    if st.button("🚪 ออก"): st.session_state.update(app_mode='customer'); st.rerun()

    tabs = st.tabs(["👨‍🍳 ครัว (Auto)", "📢 โปรโมชั่น", "📦 สต็อก", "📝 เมนู", "📊 ยอดขาย", "📞 ติดต่อ", "💬 รีวิว"])

    with tabs[0]:  # หน้าครัว
        st.markdown(f"#### 🔥 ครัว: {kitchen_load}/{KITCHEN_LIMIT} | อัปเดต: {get_thai_time().strftime('%H:%M:%S')}")
        st.progress(min(kitchen_load / KITCHEN_LIMIT, 1.0))
        if kitchen_load > 0:
            for idx, row in waiting_orders.iterrows():
                with st.container(border=True):
                    c1, c2 = st.columns([3, 1])
                    with c1:
                        st.markdown(f"**{row['โต๊ะ']}** | {row['ลูกค้า']}")
                        st.info(f"💰 {float(row['ยอดรวม']):,.2f} บาท")
                        st.caption(row['รายการอาหาร'])
                        if str(row['หมายเหตุ']) != 'nan' and row['หมายเหตุ']: st.warning(f"Note: {row['หมายเหตุ']}")
                    with c2:
                        if st.button("💰 รับเงิน", key=f"pay_{idx}", type="primary", use_container_width=True):
                            orders_df.at[idx, 'สถานะ'] = 'paid';
                            orders_df.to_csv(ORDER_CSV, index=False);
                            st.rerun()
                        # 🔥 [NEW] ปุ่มยกเลิกออเดอร์สำหรับพนักงาน 🔥
                        if st.button("❌ ยกเลิก", key=f"cancel_{idx}", use_container_width=True):
                            orders_df.at[idx, 'สถานะ'] = 'cancelled'
                            orders_df.to_csv(ORDER_CSV, index=False)
                            st.toast("ยกเลิกออเดอร์แล้ว")
                            time.sleep(1)
                            st.rerun()
        else:
            st.success("ว่าง")
        time.sleep(10);
        st.rerun()  # Auto Refresh 10s

    with tabs[1]:  # โปรโมชั่น
        for i in range(1, 6):
            f = f"banner_{i}.png";
            p = os.path.join(BANNER_FOLDER, f)
            c1, c2 = st.columns(2)
            with c1:
                up = st.file_uploader(f"รูป {i}", type=['png', 'jpg'], key=f"up_{i}")
                if up: save_promo_banner(up, i); st.rerun()
            with c2:
                if os.path.exists(p):
                    st.image(p, width=200)
                    if st.button(f"🗑️ ลบ {i}", key=f"del_{i}"): os.remove(p); st.rerun()

    with tabs[2]:  # สต็อก/โต๊ะ
        st.write("📦 จัดการสต็อก")
        edit_s = st.data_editor(menu_df[['name', 'in_stock']], disabled=["name"], hide_index=True)
        if st.button("💾 บันทึกสต็อก"): menu_df['in_stock'] = edit_s['in_stock']; menu_df.to_csv(MENU_CSV,
                                                                                                index=False); st.toast(
            "เซฟแล้ว")
        st.divider()
        st.write("🪑 จัดการโต๊ะ")
        with st.form("add_t"):
            nt = st.text_input("ชื่อโต๊ะ")
            if st.form_submit_button("เพิ่ม"):
                if nt: pd.concat([tables_df, pd.DataFrame([{"table_name": nt}])], ignore_index=True).to_csv(TABLES_CSV,
                                                                                                            index=False); st.rerun()

    with tabs[3]:  # เมนู
        with st.form("add_m"):
            n = st.text_input("ชื่อ");
            p = st.number_input("ราคา", min_value=0)
            c = st.selectbox("หมวด",
                             ["เนื้อ (Meat)", "ทะเล (Seafood)", "ผัก (Veggie)", "ของทานเล่น (Snack)", "น้ำซุป (Soup)"])
            img_u = st.text_input("URL รูป", "https://placehold.co/400")
            if st.form_submit_button("เพิ่มเมนู"):
                pd.concat(
                    [menu_df, pd.DataFrame([{"name": n, "price": p, "img": img_u, "category": c, "in_stock": True}])],
                    ignore_index=True).to_csv(MENU_CSV, index=False);
                st.rerun()
        st.divider()
        dm = st.selectbox("ลบเมนู", ["-"] + menu_df['name'].tolist())
        if st.button("ลบ") and dm != "-": menu_df[menu_df['name'] != dm].to_csv(MENU_CSV, index=False); st.rerun()

    with tabs[4]:  # ยอดขาย
        orders_df['ยอดรวม'] = pd.to_numeric(orders_df['ยอดรวม'], errors='coerce').fillna(0)
        today = get_thai_time().strftime("%d/%m/%Y")
        ds = orders_df[(orders_df['สถานะ'] == 'paid') & (orders_df['เวลา'].str.contains(today))]
        st.markdown(
            f"""<div class="sales-box">ยอดขายวันนี้<br><span class="sales-number">{ds['ยอดรวม'].sum():,.2f} ฿</span><br>{len(ds)} บิล</div>""",
            unsafe_allow_html=True)
        st.dataframe(ds[['เวลา', 'โต๊ะ', 'ลูกค้า', 'ยอดรวม', 'รายการอาหาร']], hide_index=True)

    with tabs[5]:  # ติดต่อ
        with st.form("con"):
            ph = st.text_input("โทร", contact_info['phone']);
            li = st.text_input("Line", contact_info['line'])
            fb = st.text_input("FB", contact_info['facebook']);
            ig = st.text_input("IG", contact_info['instagram'])
            if st.form_submit_button("เซฟ"): save_contacts(
                {"phone": ph, "line": li, "facebook": fb, "instagram": ig}); st.rerun()

    with tabs[6]:  # รีวิว
        fb_df = load_feedback()
        for i, r in fb_df.iterrows():
            with st.container(border=True):
                c1, c2 = st.columns([4, 1])
                with c1: st.write(f"**{r['customer_name']}** ({r['timestamp']})"); st.write(r['message'])
                with c2:
                    if st.button("🗑️", key=f"dfb_{i}"): delete_feedback_entry(i); st.rerun()

else:  # Customer Page
    # Banner Carousel
    imgs = [get_image_base64(os.path.join(BANNER_FOLDER, f"banner_{i}.png")) for i in range(1, 6) if
            os.path.exists(os.path.join(BANNER_FOLDER, f"banner_{i}.png"))]
    if imgs:
        slides = "".join([
                             f'<div class="mySlides fade" style="display:{"block" if i == 0 else "none"};"><img src="{img}" style="width:100%; border-radius:15px;"></div>'
                             for i, img in enumerate(imgs)])
        # 🔥 [NEW] เปลี่ยนเวลาเป็น 8000ms (8 วินาที) 🔥
        components.html(
            f'<!DOCTYPE html><html><head><style>.mySlides {{display:none;}} img{{vertical-align:middle;}} .fade {{animation:f 1.5s;}} @keyframes f{{from{{opacity:.4}} to{{opacity:1}}}}</style></head><body>{slides}<script>let s=0;show();function show(){{let i,x=document.getElementsByClassName("mySlides");for(i=0;i<x.length;i++)x[i].style.display="none";s++;if(s>x.length)s=1;x[s-1].style.display="block";setTimeout(show, 8000);}}</script></body></html>',
            height=320)

    if is_queue_mode:
        if st.session_state.my_queue_id:
            if can_order:
                st.success(f"✅ ถึงคิวคุณแล้ว! ({st.session_state.my_queue_id})")
            else:
                st.markdown(
                    f'<div class="customer-queue-box">🎫 คิวของคุณ: {st.session_state.my_queue_id}<br>รออีก {waiting_q_count} คิว</div>',
                    unsafe_allow_html=True)
                if st.button("🔄 อัปเดตคิว"): st.rerun()
                st.stop()
        else:
            st.markdown(f'<div class="queue-full">🚫 ครัวเต็ม ({kitchen_load} ออเดอร์) กรุณารับคิวครับ</div>',
                        unsafe_allow_html=True)
            cn = st.text_input("ระบุชื่อของคุณ")
            if st.button("🎟️ รับคิว / เช็คคิวเดิม", type="primary", use_container_width=True):
                if cn and cn != DEFAULT_CUST_NAME:
                    qid, _ = add_to_queue(cn); st.session_state.my_queue_id = qid; st.rerun()
                else:
                    st.error("กรุณาใส่ชื่อที่ไม่ใช่ 'ลูกค้าทั่วไป'")
            st.stop()
    else:
        st.markdown('<div class="queue-empty">✅ ครัวว่าง! สั่งได้เลยครับ</div>', unsafe_allow_html=True)

    c_t, c_c = st.columns(2)
    with c_t:
        table_no = st.selectbox("โต๊ะ", tables_df['table_name'].tolist())
    with c_c:
        cust_name = st.text_input("ชื่อลูกค้า", DEFAULT_CUST_NAME)

    if not cust_name or cust_name == DEFAULT_CUST_NAME:
        st.warning("🔒 กรุณาใส่ชื่อของคุณเพื่อเริ่มสั่งอาหาร")
        st.stop()

    if st.session_state.page == 'feedback':
        st.subheader("💬 เขียนรีวิว")
        with st.form("fbf"):
            m = st.text_area("ข้อความ");
            submit = st.form_submit_button("ส่ง")
            if submit and m: save_feedback_entry(cust_name, m); st.success("ขอบคุณครับ!"); time.sleep(
                1); st.session_state.page = 'menu'; st.rerun()
        if st.button("⬅️ กลับ"): st.session_state.page = 'menu'; st.rerun()

    elif st.session_state.page == 'menu':
        st.subheader("📝 รายการอาหาร")
        cols = st.columns(2)
        for i, r in menu_df.iterrows():
            with cols[i % 2]:
                with st.container(border=True):
                    if r['in_stock']:
                        st.image(r['img'], use_container_width=True)
                        st.write(f"**{r['name']}**");
                        st.caption(f"{r['price']} บ.")
                        if st.button("🛒 ใส่ตะกร้า", key=f"add_{i}", use_container_width=True):
                            st.session_state.basket.append(r.to_dict());
                            st.toast(f"เพิ่ม {r['name']}")
                    else:
                        st.error(f"❌ {r['name']} หมด")
        if st.session_state.basket:
            if st.button(f"🛒 ดูรายการในตะกร้า ({len(st.session_state.basket)})", type="primary",
                         use_container_width=True):
                st.session_state.page = 'cart';
                st.rerun()

    elif st.session_state.page == 'cart':
        st.subheader("🛒 สรุปการสั่งซื้อ")
        if st.session_state.basket:
            counts = Counter(x['name'] for x in st.session_state.basket)
            unique = {x['name']: x for x in st.session_state.basket}
            total = 0
            for name, count in counts.items():
                item = unique[name];
                sub = item['price'] * count;
                total += sub
                with st.container(border=True):
                    c1, c2 = st.columns([1, 2])
                    with c1:
                        st.image(item['img'], width=100)
                    with c2:
                        st.write(f"**{name}**");
                        st.caption(f"{item['price']} x {count} = {sub} บ.")
                        b1, b2, b3 = st.columns(3)
                        with b1:
                            if st.button("➖", key=f"min_{name}"):
                                for i, x in enumerate(st.session_state.basket):
                                    if x['name'] == name: del st.session_state.basket[i]; break
                                st.rerun()
                        with b2:
                            st.write(f"**{count}**")
                        with b3:
                            if st.button("➕", key=f"pls_{name}"): st.session_state.basket.append(item); st.rerun()
            st.divider();
            st.write(f"### 💰 รวมทั้งสิ้น: {total} บาท")
            note = st.text_area("📝 หมายเหตุ (ไม่ผัก, เผ็ดน้อย)")
            if st.button("✅ ยืนยันการสั่งอาหาร", type="primary", use_container_width=True):
                if is_queue_mode and not can_order:
                    st.error("🚫 ยังไม่ถึงคิวครับ")
                else:
                    items_str = ", ".join([f"{n}(x{c})" for n, c in counts.items()])
                    save_order(
                        {"เวลา": get_thai_time().strftime("%d/%m/%Y %H:%M"), "โต๊ะ": table_no, "ลูกค้า": cust_name,
                         "รายการอาหาร": items_str, "ยอดรวม": total, "หมายเหตุ": note, "สถานะ": "waiting"})
                    st.session_state.basket = [];
                    st.session_state.page = 'menu'
                    st.balloons();
                    st.success("ส่งออเดอร์แล้ว!");
                    time.sleep(2);
                    st.rerun()
        if st.button("⬅️ กลับ"): st.session_state.page = 'menu'; st.rerun()