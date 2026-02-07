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

KITCHEN_LIMIT = 10
DEFAULT_CUST_NAME = "ลูกค้าทั่วไป"

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
        # 1. ทบรายการอาหาร
        df.at[idx, 'รายการอาหาร'] = f"{df.at[idx, 'รายการอาหาร']}, {data['รายการอาหาร']}"
        # 2. ทบราคา (แก้ไขบั๊กราคาไม่บวกเพิ่ม)
        try:
            old_p = float(df.at[idx, 'ยอดรวม'])
        except:
            old_p = 0.0
        df.at[idx, 'ยอดรวม'] = old_p + float(data['ยอดรวม'])
        # 3. ทบหมายเหตุ
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


def get_image_base64(path):
    if os.path.exists(path):
        with open(path, "rb") as f: return f"data:image/png;base64,{base64.b64encode(f.read()).decode()}"
    return ""


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
                <p style='margin:5px 0;'>🕒 00:00 - 23:59 น. | 📞 064-448-55549</p>
            </div>
        </div>
    """, unsafe_allow_html=True)
with c_menu:
    with st.popover("☰"):
        if st.button("🏠 หน้าลูกค้า", use_container_width=True): st.session_state.update(app_mode='customer',
                                                                                        page='menu'); st.rerun()
        if st.button("⚙️ จัดการร้าน", use_container_width=True): st.session_state.app_mode = 'admin_login'; st.rerun()

st.divider()

# ================= 6. Controller =================

if st.session_state.app_mode == 'admin_login':
    pw = st.text_input("รหัสผ่าน", type="password")
    if pw == "090090op": st.session_state.app_mode = 'admin_dashboard'; st.rerun()

elif st.session_state.app_mode == 'admin_dashboard':
    tabs = st.tabs(["👨‍🍳 ครัว (Auto)", "📦 สต็อก", "📊 ยอดขาย", "💬 รีวิว"])

    with tabs[0]:  # หน้าครัว รีเฟรชทุก 1 นาที
        st.markdown(
            f"**สถานะครัว: {kitchen_load}/{KITCHEN_LIMIT}** | อัปเดตล่าสุด: {get_thai_time().strftime('%H:%M:%S')}")
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

        time.sleep(60)
        st.rerun()

    with tabs[1]:
        st.write("📦 ระบบจัดการสต็อกอาหาร")
        # โค้ดส่วนจัดการสต็อก

# === 🛒 หน้าลูกค้า (Customer) ===
else:
    # --- 🚦 LOGIC ระบบคิวอัตโนมัติ (ครัวเต็ม >= 10) ---
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
                    if st.button("🔄 อัปเดตสถานะคิว", use_container_width=True): st.rerun()
                    st.stop()
            except:
                st.session_state.my_queue_id = None; st.rerun()

    # --- 🎫 หน้าจอรับคิว (แสดงเฉพาะตอนครัวเต็ม) ---
    if show_booking_ui:
        st.error(f"🚫 ขออภัยครับ ขณะนี้ครัวเต็ม ({kitchen_load}/{KITCHEN_LIMIT}) กรุณารับคิวออนไลน์")
        q_name = st.text_input("ระบุชื่อของคุณเพื่อรับคิวออนไลน์", value="", placeholder="พิมพ์ชื่อที่นี่...")
        st.caption("ℹ️ หากมีการจองคิวไว้แล้ว กรุณาใส่ชื่อเดิมที่เคยได้จองไว้")

        if st.button("🎫 รับคิว / เช็คคิวเดิม", type="primary", use_container_width=True):
            if q_name.strip() and q_name != DEFAULT_CUST_NAME:
                st.session_state.my_queue_id = add_to_queue(q_name)
                st.rerun()
            else:
                st.warning("⚠️ กรุณาใส่ชื่อที่จองคิวไว้")
        st.stop()

    # --- 🍜 หน้าสั่งอาหารปกติ ---
    st.subheader("🛒 เริ่มสั่งอาหาร")
    c_t, c_c = st.columns(2)
    with c_t:
        table_no = st.selectbox("📍 เลือกโต๊ะ", ["โต๊ะ 1", "โต๊ะ 2", "โต๊ะ 3", "โต๊ะ 4", "กลับบ้าน"])
    with c_c:
        cust_name = st.text_input("👤 ชื่อของคุณ", value="", placeholder="กรุณาใส่ชื่อที่จองคิวไว้")
        st.caption("ℹ️ หากมีการจองคิวไว้แล้ว กรุณาใส่ชื่อเดิมที่เคยได้จองไว้")

    # 🔥 [STRICT VALIDATION] ตรวจสอบชื่อลูกค้า 🔥
    if not cust_name.strip() or cust_name == DEFAULT_CUST_NAME:
        st.warning("⚠️ กรุณาใส่ชื่อที่จองคิวไว้")
        st.stop()

    # --- เมนูอาหาร ---
    if st.session_state.page == 'menu':
        if not os.path.exists(MENU_CSV):
            st.info("ยังไม่มีรายการอาหาร กรุณาเพิ่มเมนูในระบบจัดการร้าน")
        else:
            menu_df = pd.read_csv(MENU_CSV)
            cols = st.columns(2)
            for i, r in menu_df.iterrows():
                with cols[i % 2]:
                    with st.container(border=True):
                        st.image(r['img'], use_container_width=True)
                        st.write(f"**{r['name']}** - {r['price']} บ.")
                        if st.button("🛒 ใส่ตะกร้า", key=f"add_{i}", use_container_width=True):
                            st.session_state.basket.append(r.to_dict());
                            st.toast(f"เพิ่ม {r['name']} แล้ว")

            if st.session_state.basket:
                st.divider()
                if st.button(f"🛒 สรุปออเดอร์ ({len(st.session_state.basket)} รายการ) ➡️", type="primary",
                             use_container_width=True):
                    st.session_state.page = 'cart';
                    st.rerun()

    elif st.session_state.page == 'cart':
        st.subheader("🛒 สรุปรายการสั่งซื้อ")
        if not st.session_state.basket:
            st.info("ยังไม่มีสินค้าในตะกร้า")
            if st.button("⬅️ กลับไปหน้าเมนู"): st.session_state.page = 'menu'; st.rerun()
        else:
            counts = Counter(x['name'] for x in st.session_state.basket)
            unique = {x['name']: x for x in st.session_state.basket}
            total = sum(x['price'] for x in st.session_state.basket)

            for name, count in counts.items():
                st.write(f"✅ {name} x {count} = {unique[name]['price'] * count} บาท")

            st.divider()
            st.write(f"### รวมทั้งสิ้น: {total} บาท")
            note = st.text_area("📝 หมายเหตุ (เช่น ไม่ใส่ผัก, เผ็ดน้อย)")

            if st.button("✅ ยืนยันการสั่งซื้อ", type="primary", use_container_width=True):
                # ตรวจสอบครัวนาทีสุดท้าย
                orders_df = load_orders()
                current_load = len(orders_df[orders_df['สถานะ'] == 'waiting'])

                if current_load >= KITCHEN_LIMIT and not st.session_state.my_queue_id:
                    st.error("🚫 ขออภัย ครัวเต็มแล้ว กรุณารับคิวก่อนสั่งอาหาร")
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
                    # เคลียร์ข้อมูลหลังสั่งสำเร็จ
                    if st.session_state.my_queue_id:
                        pop_queue();
                        st.session_state.my_queue_id = None
                    st.session_state.basket = [];
                    st.session_state.page = 'menu'
                    st.balloons();
                    st.success("สั่งอาหารสำเร็จ! กำลังเตรียมออเดอร์ครับ")
                    time.sleep(2);
                    st.rerun()

            if st.button("⬅️ เลือกอาหารเพิ่ม"): st.session_state.page = 'menu'; st.rerun()