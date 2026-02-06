import streamlit as st
import pandas as pd
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from datetime import datetime

# ================= 1. ตั้งค่าอีเมล (ใส่ข้อมูลครบแล้วครับ) =================
SENDER_EMAIL = 'jaskaikai4@gmail.com'  # อีเมลคนส่ง
SENDER_PASSWORD = 'zqyx nqdk ygww drpp'  # รหัสผ่านแอป (App Password)
RECEIVER_EMAIL = 'jaskaikai4@gmail.com'  # อีเมลคนรับ (ส่งหาตัวเอง)

# ================= 2. ข้อมูลร้านอาหาร =================
CSV_FILE = 'order_history.csv'
MENU = {
    "🍜 ก๋วยเตี๋ยวต้มยำ": 50,
    "🍜 ก๋วยเตี๋ยวหมูน้ำใส": 45,
    "🍛 ข้าวกะเพราหมูสับ + ไข่ดาว": 55,
    "🍗 ข้าวมันไก่ต้ม": 50,
    "🍗 ข้าวมันไก่ทอด": 50,
    "🥤 น้ำลำไย": 20,
    "🥤 ชาดำเย็น": 20,
    "🧊 น้ำแข็งเปล่า": 2
}


# ================= 3. ฟังก์ชันระบบ =================

# ฟังก์ชันส่งอีเมล
def send_email_notification(subject, body):
    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL
    msg['To'] = RECEIVER_EMAIL
    msg['Subject'] = subject

    msg.attach(MIMEText(body, 'plain'))  # ส่งแบบข้อความปกติ

    try:
        # เชื่อมต่อ Server Gmail
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        text = msg.as_string()
        server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, text)
        server.quit()
        # ส่งสำเร็จ
    except Exception as e:
        st.error(f"❌ ส่งอีเมลไม่สำเร็จ: {e}")
        st.warning("คำแนะนำ: ลองเช็คอินเทอร์เน็ต หรือเช็คว่ารหัสผ่านแอปถูกยกเลิกไปหรือยัง")


def save_order_to_csv(data):
    if not os.path.exists(CSV_FILE):
        df = pd.DataFrame(columns=["เวลา", "โต๊ะ", "ลูกค้า", "รายการอาหาร", "หมายเหตุ", "ยอดรวม"])
        df.to_csv(CSV_FILE, index=False)
    df_new = pd.DataFrame([data])
    df_new.to_csv(CSV_FILE, mode='a', header=False, index=False)


# ================= 4. หน้าจอแอปพลิเคชัน =================
st.set_page_config(page_title="ระบบสั่งอาหารออนไลน์", page_icon="🍽️")

st.title("🍽️ เมนูอาหาร (สั่งออนไลน์)")
st.write("เลือกรายการอาหารที่ต้องการด้านล่างได้เลยครับ")

# --- ส่วนข้อมูลลูกค้า ---
st.sidebar.header("📍 ข้อมูลโต๊ะ")
table_no = st.sidebar.selectbox("เลือกเบอร์โต๊ะ", ["โต๊ะ 1", "โต๊ะ 2", "โต๊ะ 3", "โต๊ะ 4", "กลับบ้าน"])
customer_name = st.sidebar.text_input("ชื่อลูกค้า (เผื่อเรียกเสิร์ฟ)")

# --- ส่วนรายการอาหาร ---
st.subheader("📝 รายการอาหาร")
selected_items = []
total_price = 0

with st.form("order_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    menu_items = list(MENU.items())
    half = len(menu_items) // 2

    with col1:
        for item, price in menu_items[:half]:
            if st.checkbox(f"{item} ({price}.-)"):
                selected_items.append(item)
                total_price += price
    with col2:
        for item, price in menu_items[half:]:
            if st.checkbox(f"{item} ({price}.-)"):
                selected_items.append(item)
                total_price += price

    st.markdown("---")
    remark = st.text_area("💬 หมายเหตุ (เช่น ไม่เผ็ด, ไม่ใส่ผัก)")
    st.write(f"### 💰 ยอดรวม: {total_price} บาท")

    submitted = st.form_submit_button("✅ ยืนยันการสั่งอาหาร", type="primary")

# --- เมื่อกดปุ่มสั่ง ---
if submitted:
    if not selected_items:
        st.error("❌ กรุณาเลือกอาหารอย่างน้อย 1 รายการครับ")
    else:
        # 1. เตรียมข้อมูล
        timestamp = datetime.now().strftime("%d/%m/%Y %H:%M")
        items_str = ", ".join(selected_items)

        # 2. บันทึกลง CSV
        order_data = {
            "เวลา": timestamp,
            "โต๊ะ": table_no,
            "ลูกค้า": customer_name,
            "รายการอาหาร": items_str,
            "หมายเหตุ": remark,
            "ยอดรวม": total_price
        }
        save_order_to_csv(order_data)

        # 3. เตรียมเนื้อหาอีเมล
        email_subject = f"🔔 ออเดอร์ใหม่: {table_no} ({customer_name})"

        email_body = f"ได้รับออเดอร์ใหม่!\n"
        email_body += f"เวลา: {timestamp}\n"
        email_body += f"โต๊ะ: {table_no}\n"
        email_body += f"ลูกค้า: {customer_name}\n"
        email_body += f"--------------------------------\n"
        email_body += f"รายการอาหาร:\n"
        for item in selected_items:
            email_body += f"- {item}\n"
        email_body += f"--------------------------------\n"
        email_body += f"หมายเหตุ: {remark}\n"
        email_body += f"ยอดรวม: {total_price} บาท\n"

        # 4. ส่งอีเมล
        send_email_notification(email_subject, email_body)

        # 5. แสดงผลหน้าจอ
        st.success(f"🎉 สั่งเรียบร้อย! ส่งใบสั่งอาหารไปที่อีเมลร้านแล้วครับ")
        st.balloons()

# --- ส่วนดูยอดขาย ---
st.markdown("---")
with st.expander("🔐 ดูประวัติออเดอร์ (เจ้าของร้าน)"):
    if os.path.exists(CSV_FILE):
        st.dataframe(pd.read_csv(CSV_FILE))
    else:
        st.info("ยังไม่มีข้อมูล")