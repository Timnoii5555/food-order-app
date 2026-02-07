import streamlit as st
import pandas as pd
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from datetime import datetime

# ================= 1. ตั้งค่าระบบ (เหมือนเดิม) =================
SENDER_EMAIL = 'jaskaikai4@gmail.com'
SENDER_PASSWORD = 'zqyx nqdk ygww drpp'
RECEIVER_EMAIL = 'jaskaikai4@gmail.com'
CSV_FILE = 'order_history.csv'

# ข้อมูลเมนู (ผมใส่รูปให้ครบตามธีม)
MENU = [
    {"name": "Premium Sliced Beef",
     "img": "https://images.unsplash.com/photo-1615937657715-bc7b4b7962c1?auto=format&fit=crop&w=500&q=60",
     "cat": "Meat & Seafood"},
    {"name": "Pork Belly",
     "img": "https://images.unsplash.com/photo-1600891964092-4316c288032e?auto=format&fit=crop&w=500&q=60",
     "cat": "Meat & Seafood"},
    {"name": "Bok Choy",
     "img": "https://images.unsplash.com/photo-1544025162-d76694265947?auto=format&fit=crop&w=500&q=60",
     "cat": "Vegetables"},
    {"name": "Fresh Shrimp",
     "img": "https://images.unsplash.com/photo-1565680018434-b513d5e5fd47?auto=format&fit=crop&w=500&q=60",
     "cat": "Meat & Seafood"},
    {"name": "Squid Rings",
     "img": "https://images.unsplash.com/photo-1599084993091-1cb5c0721cc6?auto=format&fit=crop&w=500&q=60",
     "cat": "Meat & Seafood"},
    {"name": "Morning Glory",
     "img": "https://images.unsplash.com/photo-1619250907507-28f0952cc914?auto=format&fit=crop&w=500&q=60",
     "cat": "Vegetables"},
    {"name": "Enoki Mushroom",
     "img": "https://images.unsplash.com/photo-1606728035784-a8db8b860b20?auto=format&fit=crop&w=500&q=60",
     "cat": "Vegetables"},
    {"name": "Udon Noodles",
     "img": "https://images.unsplash.com/photo-1552611052-33e04de081de?auto=format&fit=crop&w=500&q=60",
     "cat": "Sides"},
]


# ================= 2. ฟังก์ชันระบบ =================
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


def save_order_to_csv(data):
    if not os.path.exists(CSV_FILE):
        df = pd.DataFrame(columns=["เวลา", "โต๊ะ", "ลูกค้า", "รายการอาหาร", "หมายเหตุ"])
        df.to_csv(CSV_FILE, index=False)
    df_new = pd.DataFrame([data])
    df_new.to_csv(CSV_FILE, mode='a', header=False, index=False)


# ================= 3. ตั้งค่า UI & CSS =================
st.set_page_config(page_title="TeeNoi Shabu", page_icon="🍲", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }

    /* ซ่อน Header เดิม */
    header {visibility: hidden;}
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* CSS จากไฟล์ HTML ที่คุณให้มา (ปรับให้เข้ากับ Streamlit) */
    .stApp {
        background-color: #f8f6f6;
    }

    /* การ์ดสินค้า (หน้าแรก) */
    .menu-card {
        background: white;
        border-radius: 16px;
        padding: 10px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        border: 1px solid #e5e7eb;
        transition: transform 0.2s;
    }
    .menu-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
    }

    /* ปุ่ม Add (+) */
    .btn-add {
        background-color: #f1f5f9;
        color: #334155;
        border-radius: 12px;
        padding: 8px;
        width: 100%;
        font-weight: bold;
        border: none;
        cursor: pointer;
    }
    .btn-add:hover {
        background-color: #ea2a33;
        color: white;
    }

    /* Modal จำลอง (สำหรับหน้าตะกร้า) */
    .cart-container {
        background-color: white;
        border-radius: 16px;
        padding: 20px;
        border: 1px solid #e5e7eb;
        box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
    }

    /* ปุ่ม Confirm สีเขียว */
    .btn-confirm {
        background-color: #22c55e !important;
        color: white !important;
        font-weight: 800 !important;
        border-radius: 12px !important;
        padding: 15px !important;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .btn-confirm:hover {
        filter: brightness(1.1);
    }

</style>
""", unsafe_allow_html=True)

# ================= 4. Logic การทำงาน =================

# Initialize Session State
if 'basket' not in st.session_state:
    st.session_state.basket = []
if 'page' not in st.session_state:
    st.session_state.page = 'menu'  # menu = หน้าเลือกของ, cart = หน้าสรุป

# --- ส่วน Sidebar (Top Nav จำลอง) ---
with st.sidebar:
    st.markdown("<h1 style='color:#ea2a33;'>🍲 TeeNoi Shabu</h1>", unsafe_allow_html=True)
    table_no = st.selectbox("เลือกโต๊ะ", ["Table 12", "Table 13", "Table 14"])
    customer_name = st.text_input("ชื่อลูกค้า", "Guest")

    st.markdown("---")

    # ปุ่มสลับหน้า
    if st.button("🏠 กลับหน้าเมนู", use_container_width=True):
        st.session_state.page = 'menu'
        st.rerun()

    if len(st.session_state.basket) > 0:
        st.info(f"ในตะกร้ามี {len(st.session_state.basket)} รายการ")
        if st.button("🛒 ดูตะกร้าสินค้า", type="primary", use_container_width=True):
            st.session_state.page = 'cart'
            st.rerun()

# ================= 5. หน้าจอ (แบ่งตาม State) =================

if st.session_state.page == 'menu':
    # --- หน้า 1: เมนูอาหาร (Grid) ---
    st.title("🥩 เมนูอาหาร")

    cols = st.columns(4)
    for index, item in enumerate(MENU):
        with cols[index % 4]:
            st.image(item["img"], use_column_width=True)
            st.markdown(f"**{item['name']}**")
            st.caption(item['cat'])

            if st.button(f"Add ➕", key=f"add_{index}"):
                st.session_state.basket.append(item)
                st.toast(f"เพิ่ม {item['name']} แล้ว!", icon="✅")

    # Floating Bar ด้านล่าง (แสดงเมื่อมีของ)
    if len(st.session_state.basket) > 0:
        st.markdown("---")
        c1, c2 = st.columns([3, 1])
        with c1:
            st.success(f"🧺 คุณเลือกอาหารแล้ว {len(st.session_state.basket)} จาน")
        with c2:
            if st.button("ไปหน้าสรุปออเดอร์ ➡️", type="primary", use_container_width=True):
                st.session_state.page = 'cart'
                st.rerun()

else:
    # --- หน้า 2: ตะกร้าสินค้า (Order Confirmation Review) ---
    st.markdown("### 📋 Review Your Order")
    st.caption(f"{table_no} • Final Check")

    # แปลงรายการในตะกร้าเป็น DataFrame เพื่อนับจำนวน
    if len(st.session_state.basket) > 0:
        basket_names = [item['name'] for item in st.session_state.basket]
        df_basket = pd.Series(basket_names).value_counts().reset_index()
        df_basket.columns = ['รายการ', 'จำนวน']

        # แสดงรายการแบบสวยงาม (เลียนแบบ Modal ใน HTML)
        for index, row in df_basket.iterrows():
            with st.container(border=True):
                c_img, c_name, c_qty, c_del = st.columns([1, 4, 2, 1])

                # หารูปภาพจากชื่อ
                img_url = next((item['img'] for item in MENU if item['name'] == row['รายการ']), "")

                with c_img:
                    st.image(img_url, width=60)
                with c_name:
                    st.markdown(f"**{row['รายการ']}**")
                    st.caption("Standard Cut")
                with c_qty:
                    st.markdown(f"**x {row['จำนวน']}**")
                with c_del:
                    if st.button("❌", key=f"del_{index}"):
                        # ลบ 1 ชิ้นจาก basket
                        for i, item in enumerate(st.session_state.basket):
                            if item['name'] == row['รายการ']:
                                del st.session_state.basket[i]
                                break
                        st.rerun()

        st.markdown("---")
        remark = st.text_area("💬 หมายเหตุเพิ่มเติม (Note)", placeholder="เช่น ไม่ใส่ผัก, ขอเน้นมันๆ")

        # ส่วนสรุปยอด (Footer Actions)
        c_add, c_confirm = st.columns([1, 2])

        with c_add:
            if st.button("⬅️ สั่งเพิ่มอีก", use_container_width=True):
                st.session_state.page = 'menu'
                st.rerun()

        with c_confirm:
            # ปุ่มสีเขียว Confirm Order (ตาม HTML)
            if st.button(f"✅ CONFIRM ORDER ({len(st.session_state.basket)} Items)", type="primary",
                         use_container_width=True):
                # 1. บันทึก & ส่งเมล
                timestamp = datetime.now().strftime("%d/%m/%Y %H:%M")
                items_str = ", ".join([f"{row['รายการ']} (x{row['จำนวน']})" for index, row in df_basket.iterrows()])

                save_order_to_csv({
                    "เวลา": timestamp,
                    "โต๊ะ": table_no,
                    "ลูกค้า": customer_name,
                    "รายการอาหาร": items_str,
                    "หมายเหตุ": remark
                })

                email_body = f"Review Order:\nโต๊ะ: {table_no}\nลูกค้า: {customer_name}\nเวลา: {timestamp}\n\n{items_str}\n\nNote: {remark}"
                send_email_notification(f"✅ Order Confirmed: {table_no}", email_body)

                # 2. จบการทำงาน
                st.session_state.basket = []
                st.session_state.page = 'menu'
                st.balloons()
                st.success("ส่งออเดอร์เรียบร้อย! พนักงานกำลังเตรียมอาหารครับ")

    else:
        st.warning("ตะกร้าว่างเปล่า! กรุณาเลือกอาหารก่อนครับ")
        if st.button("กลับไปเลือกอาหาร"):
            st.session_state.page = 'menu'
            st.rerun()