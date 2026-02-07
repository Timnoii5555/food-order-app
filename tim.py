import streamlit as st
import pandas as pd
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from datetime import datetime

# ================= 1. ตั้งค่าระบบ (EMAIL) =================
SENDER_EMAIL = 'jaskaikai4@gmail.com'
SENDER_PASSWORD = 'zqyx nqdk ygww drpp'
RECEIVER_EMAIL = 'jaskaikai4@gmail.com'

# ชื่อไฟล์เก็บข้อมูล
ORDER_CSV = 'order_history.csv'  # ประวัติการสั่งซื้อ
MENU_CSV = 'menu_data.csv'  # รายการอาหาร (สร้างอัตโนมัติ)


# ================= 2. ฟังก์ชันจัดการข้อมูล (Backend) =================

# โหลดเมนู (ถ้าไม่มีไฟล์ จะสร้างเมนูเริ่มต้นให้)
def load_menu():
    if not os.path.exists(MENU_CSV):
        # ข้อมูลเริ่มต้น (Timnoi Original)
        default_data = [
            {"name": "Premium Sliced Beef", "price": 120,
             "img": "https://images.unsplash.com/photo-1615937657715-bc7b4b7962c1?auto=format&fit=crop&w=500&q=60",
             "category": "Meat"},
            {"name": "Pork Belly", "price": 89,
             "img": "https://images.unsplash.com/photo-1600891964092-4316c288032e?auto=format&fit=crop&w=500&q=60",
             "category": "Meat"},
            {"name": "Fresh Shrimp", "price": 150,
             "img": "https://images.unsplash.com/photo-1565680018434-b513d5e5fd47?auto=format&fit=crop&w=500&q=60",
             "category": "Seafood"},
            {"name": "Bok Choy", "price": 40,
             "img": "https://images.unsplash.com/photo-1544025162-d76694265947?auto=format&fit=crop&w=500&q=60",
             "category": "Veggie"},
        ]
        df = pd.DataFrame(default_data)
        df.to_csv(MENU_CSV, index=False)

    return pd.read_csv(MENU_CSV)


# ฟังก์ชันส่งอีเมล
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


# บันทึกออเดอร์
def save_order(data):
    if not os.path.exists(ORDER_CSV):
        df = pd.DataFrame(columns=["เวลา", "โต๊ะ", "ลูกค้า", "รายการอาหาร", "ยอดรวม", "หมายเหตุ"])
        df.to_csv(ORDER_CSV, index=False)
    df_new = pd.DataFrame([data])
    df_new.to_csv(ORDER_CSV, mode='a', header=False, index=False)


# ================= 3. ตั้งค่าหน้าจอ (UI & CSS) =================
st.set_page_config(page_title="Timnoi Shabu", page_icon="🍲", layout="wide")

# CSS ตกแต่ง (Timnoi Theme)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Kanit:wght@300;500;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Kanit', sans-serif;
    }

    /* ซ่อน Header มาตรฐาน */
    header {visibility: hidden;}
    footer {visibility: hidden;}

    /* กล่องข้อมูลลูกค้า (Top Bar) */
    .customer-box {
        background-color: #fff0f0;
        border: 2px solid #ea2a33;
        border-radius: 15px;
        padding: 15px;
        text-align: center;
        margin-bottom: 20px;
    }

    /* ปุ่มกด */
    .stButton>button {
        border-radius: 10px;
        font-weight: bold;
    }

    /* การ์ดเมนู */
    .menu-card-img {
        border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)

# ================= 4. โหลดข้อมูล =================
if 'basket' not in st.session_state:
    st.session_state.basket = []
if 'page' not in st.session_state:
    st.session_state.page = 'menu'

# โหลดเมนูจากไฟล์ CSV
menu_df = load_menu()

# ================= 5. ส่วนจัดการ (Admin Sidebar) =================
with st.sidebar:
    st.header("⚙️ จัดการร้าน (Admin)")
    admin_mode = st.checkbox("แก้ไขเมนูอาหาร")

    if admin_mode:
        st.info("โหมดแก้ไข: เพิ่ม/ลบ เมนูได้ที่นี่")

        # 1. ลบเมนู
        st.subheader("❌ ลบเมนู")
        delete_list = menu_df['name'].tolist()
        item_to_delete = st.selectbox("เลือกเมนูที่จะลบ", ["-เลือก-"] + delete_list)
        if st.button("ยืนยันลบเมนู") and item_to_delete != "-เลือก-":
            menu_df = menu_df[menu_df['name'] != item_to_delete]
            menu_df.to_csv(MENU_CSV, index=False)
            st.success(f"ลบ {item_to_delete} เรียบร้อย!")
            st.rerun()

        st.markdown("---")

        # 2. เพิ่มเมนู
        st.subheader("➕ เพิ่มเมนูใหม่")
        with st.form("add_menu_form"):
            new_name = st.text_input("ชื่อเมนู")
            new_price = st.number_input("ราคา (บาท)", min_value=0, value=50)
            new_cat = st.selectbox("หมวดหมู่", ["Meat", "Seafood", "Veggie", "Snack", "Drink"])
            new_img = st.text_input("ลิ้งค์รูปภาพ (URL)", "https://placehold.co/400")

            if st.form_submit_button("บันทึกเมนูใหม่"):
                if new_name:
                    new_data = pd.DataFrame(
                        [{"name": new_name, "price": new_price, "img": new_img, "category": new_cat}])
                    menu_df = pd.concat([menu_df, new_data], ignore_index=True)
                    menu_df.to_csv(MENU_CSV, index=False)
                    st.success("เพิ่มเมนูสำเร็จ!")
                    st.rerun()
                else:
                    st.error("กรุณาใส่ชื่อเมนู")

# ================= 6. ส่วนหน้าจอหลัก (ลูกค้า) =================

# --- Header: โลโก้ & ข้อมูลโต๊ะ (ให้เห็นชัดๆ) ---
col_logo, col_info = st.columns([1, 3])

with col_logo:
    # พยายามหารูป logo.png ในเครื่อง
    if os.path.exists("logo.png"):
        st.image("logo.png", width=120)
    else:
        # ถ้าไม่มีรูป ให้แสดงชื่อร้านสวยๆ แทน
        st.markdown("<h1 style='color:#ea2a33; font-size:40px;'>🍲 Timnoi</h1>", unsafe_allow_html=True)

with col_info:
    # กล่องเลือกโต๊ะที่เด่นชัด
    with st.container(border=True):
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("### 📍 เลือกโต๊ะ")
            table_no = st.selectbox("Table No.", ["Table 1", "Table 2", "Table 3", "Table 4", "กลับบ้าน"],
                                    label_visibility="collapsed")
        with c2:
            st.markdown("### 👤 ชื่อลูกค้า")
            customer_name = st.text_input("Customer Name", "ลูกค้าทั่วไป", label_visibility="collapsed")

st.markdown("---")

# --- Page Controller ---

if st.session_state.page == 'menu':
    # === หน้าเลือกอาหาร ===
    st.subheader(f"📝 เมนูอาหาร (โต๊ะ: {table_no})")

    # Grid แสดงอาหาร
    cols = st.columns(4)
    for index, row in menu_df.iterrows():
        with cols[index % 4]:
            with st.container(border=True):
                # แสดงรูป
                try:
                    st.image(row['img'], use_container_width=True)
                except:
                    st.image("https://placehold.co/400", caption="No Image")

                st.markdown(f"**{row['name']}**")
                st.caption(f"ราคา: {row['price']} บาท")

                if st.button(f"ใส่ตะกร้า 🛒", key=f"add_{index}", use_container_width=True):
                    st.session_state.basket.append(row.to_dict())
                    st.toast(f"เพิ่ม {row['name']} แล้ว!", icon="✅")

    # ปุ่มไปหน้าชำระเงิน (ลอยอยู่ด้านล่าง หรือ แสดงเมื่อมีของ)
    if len(st.session_state.basket) > 0:
        st.markdown("---")
        btn_col1, btn_col2 = st.columns([3, 1])
        with btn_col1:
            st.info(f"🛒 ในตะกร้ามี {len(st.session_state.basket)} รายการ | รอการยืนยัน")
        with btn_col2:
            if st.button("ไปหน้าสรุปออเดอร์ ➡️", type="primary", use_container_width=True):
                st.session_state.page = 'cart'
                st.rerun()

elif st.session_state.page == 'cart':
    # === หน้าสรุปรายการ ===
    st.button("⬅️ กลับไปเลือกเพิ่ม", on_click=lambda: st.session_state.update(page='menu'))

    st.markdown(f"""
    <div style="background-color:#ea2a33; color:white; padding:15px; border-radius:10px; text-align:center; margin-bottom:20px;">
        <h2>🛒 สรุปรายการสั่งซื้อ</h2>
        <h3>โต๊ะ: {table_no} | คุณ: {customer_name}</h3>
    </div>
    """, unsafe_allow_html=True)

    if len(st.session_state.basket) > 0:
        # คำนวณยอดรวม
        total_price = sum([item['price'] for item in st.session_state.basket])

        # แสดงรายการ
        basket_df = pd.DataFrame(st.session_state.basket)
        # นับจำนวนสินค้าที่ซ้ำกัน
        summary_df = basket_df['name'].value_counts().reset_index()
        summary_df.columns = ['รายการ', 'จำนวน']

        # เพิ่มราคาต่อหน่วยและราคารวม
        summary_df['ราคาต่อหน่วย'] = summary_df['รายการ'].apply(
            lambda x: menu_df[menu_df['name'] == x]['price'].values[0])
        summary_df['รวม'] = summary_df['จำนวน'] * summary_df['ราคาต่อหน่วย']

        st.dataframe(summary_df, hide_index=True, use_container_width=True)

        st.markdown(f"### 💰 ยอดรวมทั้งสิ้น: **{total_price}** บาท")
        remark = st.text_area("💬 หมายเหตุถึงครัว", placeholder="เช่น ไม่ใส่ผัก, ขอน้ำจิ้มเพิ่ม")

        # ปุ่มยืนยัน
        if st.button("✅ ยืนยันการสั่งอาหาร (Confirm)", type="primary", use_container_width=True):
            # 1. เตรียมข้อมูล
            timestamp = datetime.now().strftime("%d/%m/%Y %H:%M")
            items_str = ", ".join([f"{row['รายการ']} (x{row['จำนวน']})" for index, row in summary_df.iterrows()])

            # 2. บันทึกลงไฟล์
            save_order({
                "เวลา": timestamp,
                "โต๊ะ": table_no,
                "ลูกค้า": customer_name,
                "รายการอาหาร": items_str,
                "ยอดรวม": total_price,
                "หมายเหตุ": remark
            })

            # 3. ส่งอีเมล
            email_subject = f"🔔 Order ใหม่: {table_no} ({customer_name})"
            email_body = f"เวลา: {timestamp}\nโต๊ะ: {table_no}\nลูกค้า: {customer_name}\n\nรายการ:\n{items_str}\n\nหมายเหตุ: {remark}\nยอดรวม: {total_price} บาท"
            send_email_notification(email_subject, email_body)

            # 4. Reset และกลับหน้าแรก
            st.session_state.basket = []
            st.session_state.page = 'menu'
            st.balloons()
            st.success("ส่งออเดอร์เรียบร้อย! กำลังกลับหน้าหลัก...")

            # **สำคัญ** เทคนิคทำให้รอแป๊บนึงแล้วค่อยรีเฟรช
            import time

            with st.spinner('กำลังส่งข้อมูล...'):
                time.sleep(2)
            st.rerun()  # สั่งรีเฟรชหน้าจอทันที

    else:
        st.warning("ไม่มีสินค้าในตะกร้า")