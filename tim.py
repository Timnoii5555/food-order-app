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
            {"name": "กุ้งสด", "price": 150,
             "img": "https://images.unsplash.com/photo-1565680018434-b513d5e5fd47?auto=format&fit=crop&w=500&q=60",
             "category": "ทะเล (Seafood)", "in_stock": True},
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
        pd.DataFrame(default_tables, columns=["table_name"]).to_csv(TABLES_CSV, index=False)
    return pd.read_csv(TABLES_CSV)


def load_orders():
    cols = ["เวลา", "โต๊ะ", "ลูกค้า", "รายการอาหาร", "ยอดรวม", "หมายเหตุ", "สถานะ"]
    if not os.path.exists(ORDER_CSV):
        pd.DataFrame(columns=cols).to_csv(ORDER_CSV, index=False)
        return pd.DataFrame(columns=cols)
    try:
        df = pd.read_csv(ORDER_CSV)
        if list(df.columns) != cols:
            # ถ้าคอลัมน์ไม่ตรง ให้พยายามล้างข้อมูลเสียทิ้งเพื่อเริ่มใหม่ให้ถูกต้อง
            return pd.DataFrame(columns=cols)
        return df
    except:
        return pd.DataFrame(columns=cols)


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


def load_queue():
    if not os.path.exists(QUEUE_CSV):
        pd.DataFrame(columns=["queue_id", "customer_name", "timestamp"]).to_csv(QUEUE_CSV, index=False)
    return pd.read_csv(QUEUE_CSV)


def save_order(data):
    df = load_orders()
    mask = (df['โต๊ะ'] == data['โต๊ะ']) & (df['สถานะ'] == 'waiting')
    if mask.any():
        idx = df.index[mask][0]
        # ทบรายการอาหาร
        df.at[idx, 'รายการอาหาร'] = str(df.at[idx, 'รายการอาหาร']) + ", " + str(data['รายการอาหาร'])
        # ทบราคาสินค้า (ป้องกันบั๊กราคาไม่เพิ่ม)
        try:
            old_price = float(df.at[idx, 'ยอดรวม'])
        except:
            old_price = 0.0
        df.at[idx, 'ยอดรวม'] = old_price + float(data['ยอดรวม'])
        # ทบหมายเหตุ
        old_note = str(df.at[idx, 'หมายเหตุ'])
        new_note = str(data['หมายเหตุ'])
        if new_note and old_note != 'nan':
            df.at[idx, 'หมายเหตุ'] = f"{old_note} | {new_note}"
        elif new_note:
            df.at[idx, 'หมายเหตุ'] = new_note

        df.at[idx, 'เวลา'] = data['เวลา']
        df.to_csv(ORDER_CSV, index=False)
        return "merged"
    else:
        df_new = pd.DataFrame([data])
        pd.concat([df, df_new], ignore_index=True).to_csv(ORDER_CSV, index=False)
        return "new"


def get_image_base64(path):
    with open(path, "rb") as f: return f"data:image/png;base64,{base64.b64encode(f.read()).decode()}"


# ================= 3. UI & CSS =================
st.set_page_config(page_title="TimNoi Shabu", page_icon="🍲", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;500;700&display=swap');
    html, body, [class*="css"] { font-family: 'Sarabun', sans-serif; background-color: #FDFBF7; }
    .stButton>button { border-radius: 8px; font-weight: bold; background-color: #8D6E63; color: white; border: none; }
    .stButton>button:hover { background-color: #6D4C41; color: #FFECB3; }
    .contact-row { display: flex; align-items: center; margin-bottom: 12px; background-color: white; padding: 10px; border-radius: 10px; border: 1px solid #eee; }
    .contact-icon { width: 30px; height: 30px; margin-right: 12px; }
    .sales-box { background-color: #FFF3E0; border: 2px solid #FFB74D; color: #E65100; padding: 20px; border-radius: 12px; text-align: center; }
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

waiting_orders = orders_df[orders_df['สถานะ'] == 'waiting']
kitchen_load = len(waiting_orders)

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
            <h1 style='color:#3E2723; font-size:50px; margin:0;'>TimNoi Shabu</h1>
            <p style='color:#8D6E63; font-size:20px; font-weight:bold;'>ร้านนี้ไม่มีหมูเพราะที่เห็นเป็นเนื้อหมา</p>
            <div style='margin-top:10px; border-top: 2px solid #D7CCC8;'>
                <p style='margin:5px 0;'>🕒 00:00 - 23:59 น. | 📞 {contact_info['phone']}</p>
            </div>
        </div>
    """, unsafe_allow_html=True)

with c_menu:
    with st.popover("☰"):
        if st.button("🏠 หน้าลูกค้า", use_container_width=True): st.session_state.update(app_mode='customer',
                                                                                        page='menu'); st.rerun()
        if st.button("💬 เขียนรีวิว", use_container_width=True): st.session_state.update(app_mode='customer',
                                                                                        page='feedback'); st.rerun()
        if st.button("⚙️ จัดการร้าน", use_container_width=True): st.session_state.update(
            app_mode='admin_login'); st.rerun()
        st.markdown("---")
        st.markdown(f"""
            <div class="contact-row"><img src="https://cdn-icons-png.flaticon.com/512/5968/5968764.png" class="contact-icon"><a href="{contact_info['facebook']}" target="_blank">Facebook</a></div>
            <div class="contact-row"><img src="https://cdn-icons-png.flaticon.com/512/3955/3955024.png" class="contact-icon"><a href="{contact_info['instagram']}" target="_blank">Instagram</a></div>
        """, unsafe_allow_html=True)

st.divider()

# ================= 6. Controller =================

# === Admin Login ===
if st.session_state.app_mode == 'admin_login':
    st.subheader("🔐 เข้าสู่ระบบ")
    pw = st.text_input("รหัสผ่าน", type="password")
    if pw == "090090op": st.session_state.update(app_mode='admin_dashboard'); st.rerun()

# === Admin Dashboard ===
elif st.session_state.app_mode == 'admin_dashboard':
    st.subheader("⚙️ จัดการร้าน")
    if st.button("🚪 ออกจากระบบ"): st.session_state.app_mode = 'customer'; st.rerun()

    tabs = st.tabs(["👨‍🍳 ครัว (Auto)", "📢 โปรโมชั่น", "📦 สต็อก/โต๊ะ", "📝 เมนู", "📊 ยอดขาย", "📞 ติดต่อ", "💬 รีวิว"])

    with tabs[0]:  # หน้าครัว
        st.markdown(f"**สถานะครัว: {kitchen_load}/{KITCHEN_LIMIT}** | อัปเดต: {get_thai_time().strftime('%H:%M:%S')}")
        if kitchen_load > 0:
            for idx, row in waiting_orders.iterrows():
                with st.container(border=True):
                    c1, c2 = st.columns([3, 1])
                    with c1:
                        st.markdown(f"**{row['โต๊ะ']}** | {row['ลูกค้า']}")
                        st.info(f"💰 {float(row['ยอดรวม']):,.2f} บาท")
                        st.caption(f"🍱 {row['รายการอาหาร']}")
                        if str(row['หมายเหตุ']) != 'nan' and row['หมายเหตุ']: st.warning(f"📝 {row['หมายเหตุ']}")
                    with c2:
                        if st.button("💰 รับเงิน", key=f"pay_{idx}", use_container_width=True, type="primary"):
                            orders_df.at[idx, 'สถานะ'] = 'paid';
                            orders_df.to_csv(ORDER_CSV, index=False);
                            st.rerun()
                        if st.button("❌ ยกเลิก", key=f"can_{idx}", use_container_width=True):
                            orders_df.at[idx, 'สถานะ'] = 'cancelled';
                            orders_df.to_csv(ORDER_CSV, index=False);
                            st.rerun()
        else:
            st.info("ไม่มีออเดอร์ค้าง")

        # Auto Refresh เฉพาะหน้าครัว และเมื่ออยู่ในโหมด Admin เท่านั้น
        time.sleep(10)
        st.rerun()

    # --- ส่วนอื่นๆ ของ Admin (สต็อก, เมนู, ยอดขาย) ---
    with tabs[2]:  # สต็อก
        st.write("📦 จัดการสต็อก")
        edit_s = st.data_editor(menu_df[['name', 'in_stock']], disabled=["name"], hide_index=True)
        if st.button("💾 บันทึกสต็อก"):
            menu_df['in_stock'] = edit_s['in_stock'];
            menu_df.to_csv(MENU_CSV, index=False);
            st.toast("บันทึกแล้ว")

    with tabs[4]:  # ยอดขาย
        orders_df['ยอดรวม'] = pd.to_numeric(orders_df['ยอดรวม'], errors='coerce').fillna(0)
        today = get_thai_time().strftime("%d/%m/%Y")
        ds = orders_df[(orders_df['สถานะ'] == 'paid') & (orders_df['เวลา'].str.contains(today))]
        st.markdown(
            f'<div class="sales-box">ยอดขายวันนี้<br><h2 style="margin:0;">{ds["ยอดรวม"].sum():,.2f} ฿</h2></div>',
            unsafe_allow_html=True)
        st.dataframe(ds[['เวลา', 'โต๊ะ', 'ลูกค้า', 'ยอดรวม', 'รายการอาหาร']], hide_index=True)

# === Customer Page ===
else:
    # Banner
    imgs = [get_image_base64(os.path.join(BANNER_FOLDER, f"banner_{i}.png")) for i in range(1, 6) if
            os.path.exists(os.path.join(BANNER_FOLDER, f"banner_{i}.png"))]
    if imgs:
        slides = "".join([
                             f'<div class="mySlides fade" style="display:{"block" if i == 0 else "none"};"><img src="{img}" style="width:100%; border-radius:15px;"></div>'
                             for i, img in enumerate(imgs)])
        components.html(
            f'<!DOCTYPE html><html><head><style>.mySlides {{display:none;}} img{{vertical-align:middle;}} .fade {{animation:f 1.5s;}} @keyframes f{{from{{opacity:.4}} to{{opacity:1}}}}</style></head><body>{slides}<script>let s=0;show();function show(){{let i,x=document.getElementsByClassName("mySlides");for(i=0;i<x.length;i++)x[i].style.display="none";s++;if(s>x.length)s=1;x[s-1].style.display="block";setTimeout(show, 8000);}}</script></body></html>',
            height=320)

    # เลือกโต๊ะและชื่อ
    c_t, c_c = st.columns(2)
    with c_t:
        table_no = st.selectbox("📍 เลือกโต๊ะ", tables_df['table_name'].tolist())
    with c_c:
        cust_name = st.text_input("👤 ชื่อของคุณ", value=DEFAULT_CUST_NAME)

    # 🔥 บังคับเปลี่ยนชื่อ 🔥
    if not cust_name or cust_name == DEFAULT_CUST_NAME:
        st.warning("🔒 กรุณาเปลี่ยนชื่อ 'ลูกค้าทั่วไป' เป็นชื่อของคุณเพื่อเริ่มสั่งอาหาร")
        st.stop()

    if st.session_state.page == 'menu':
        st.subheader("🍱 รายการอาหาร")
        cols = st.columns(2)
        for i, r in menu_df.iterrows():
            with cols[i % 2]:
                with st.container(border=True):
                    if r['in_stock']:
                        st.image(r['img'], use_container_width=True)
                        st.write(f"**{r['name']}**")
                        st.caption(f"ราคา {r['price']} บาท")
                        if st.button("🛒 ใส่ตะกร้า", key=f"add_{i}", use_container_width=True):
                            st.session_state.basket.append(r.to_dict());
                            st.toast(f"เพิ่ม {r['name']}")
                    else:
                        st.error(f"❌ {r['name']} หมด")

        if st.session_state.basket:
            if st.button(f"🛒 สรุปยอด ({len(st.session_state.basket)}) ➡️", type="primary", use_container_width=True):
                st.session_state.page = 'cart';
                st.rerun()

    elif st.session_state.page == 'cart':
        st.subheader("🛒 ตะกร้าของท่าน")
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
                        st.write(f"**{name}**")
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

            st.divider()
            st.markdown(f"### 💰 ยอดรวม: {total} บาท")
            note = st.text_area("📝 หมายเหตุ (เช่น ไม่เอาผัก, เผ็ดน้อย)")

            if st.button("✅ ยืนยันการสั่งซื้อ", type="primary", use_container_width=True):
                if kitchen_load >= KITCHEN_LIMIT:
                    st.error("🚫 ครัวเต็มชั่วคราว กรุณารอพนักงานเรียกคิว")
                else:
                    items_str = ", ".join([f"{n}(x{c})" for n, c in counts.items()])
                    save_order({
                        "เวลา": get_thai_time().strftime("%d/%m/%Y %H:%M"),
                        "โต๊ะ": table_no,
                        "ลูกค้า": cust_name,
                        "รายการอาหาร": items_str,
                        "ยอดรวม": total,
                        "หมายเหตุ": note,
                        "สถานะ": "waiting"
                    })
                    st.session_state.basket = [];
                    st.session_state.page = 'menu'
                    st.balloons();
                    st.success("ส่งออเดอร์สำเร็จ!");
                    time.sleep(2);
                    st.rerun()

        if st.button("⬅️ กลับไปหน้าเมนู"): st.session_state.page = 'menu'; st.rerun()

    elif st.session_state.page == 'feedback':
        st.subheader("💬 เขียนติชมบริการ")
        with st.form("fb"):
            msg = st.text_area("ข้อความของคุณ")
            if st.form_submit_button("ส่งรีวิว"):
                # ฟังก์ชันบันทึกรีวิว
                st.success("ขอบคุณสำหรับรีวิวครับ!");
                st.session_state.page = 'menu';
                st.rerun()
        if st.button("⬅️ กลับ"): st.session_state.page = 'menu'; st.rerun()