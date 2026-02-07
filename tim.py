import streamlit as st
import pandas as pd
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from datetime import datetime
import time
import pytz

# ================= 1. ตั้งค่าระบบ =================
SENDER_EMAIL = 'jaskaikai4@gmail.com'
SENDER_PASSWORD = 'zqyx nqdk ygww drpp'
RECEIVER_EMAIL = 'jaskaikai4@gmail.com'

ORDER_CSV = 'order_history.csv'
MENU_CSV = 'menu_data.csv'
TABLES_CSV = 'tables_data.csv'


# ================= 2. ฟังก์ชันจัดการข้อมูล =================

def load_menu():
    if not os.path.exists(MENU_CSV):
        default_data = [
            {"name": "หมูหมัก (Marinated Pork)", "price": 120,
             "img": "https://images.unsplash.com/photo-1615937657715-bc7b4b7962c1?auto=format&fit=crop&w=500&q=60",
             "category": "Meat", "in_stock": True},
            {"name": "หมูสามชั้น (Pork Belly)", "price": 89,
             "img": "https://images.unsplash.com/photo-1600891964092-4316c288032e?auto=format&fit=crop&w=500&q=60",
             "category": "Meat", "in_stock": True},
            {"name": "กุ้งสด (Fresh Shrimp)", "price": 150,
             "img": "https://images.unsplash.com/photo-1565680018434-b513d5e5fd47?auto=format&fit=crop&w=500&q=60",
             "category": "Seafood", "in_stock": True},
            {"name": "ผักกวางตุ้ง (Bok Choy)", "price": 40,
             "img": "https://images.unsplash.com/photo-1544025162-d76694265947?auto=format&fit=crop&w=500&q=60",
             "category": "Veggie", "in_stock": True},
        ]
        df = pd.DataFrame(default_data)
        df.to_csv(MENU_CSV, index=False)

    df = pd.read_csv(MENU_CSV)
    if 'in_stock' not in df.columns:
        df['in_stock'] = True
        df.to_csv(MENU_CSV, index=False)
    return df


def load_tables():
    if not os.path.exists(TABLES_CSV):
        default_tables = ["โต๊ะ 1", "โต๊ะ 2", "โต๊ะ 3", "โต๊ะ 4", "กลับบ้าน"]
        df = pd.DataFrame(default_tables, columns=["table_name"])
        df.to_csv(TABLES_CSV, index=False)
    return pd.read_csv(TABLES_CSV)


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
    if not os.path.exists(ORDER_CSV):
        df = pd.DataFrame(columns=["เวลา", "โต๊ะ", "ลูกค้า", "รายการอาหาร", "ยอดรวม", "หมายเหตุ"])
        df.to_csv(ORDER_CSV, index=False)
    df_new = pd.DataFrame([data])
    df_new.to_csv(ORDER_CSV, mode='a', header=False, index=False)


def get_thai_time():
    tz = pytz.timezone('Asia/Bangkok')
    return datetime.now(tz)


# ================= 3. UI & CSS (ธีม Vintage Premium) =================
st.set_page_config(page_title="Timnoi Shabu", page_icon="🍲", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;500;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Sarabun', sans-serif;
        background-color: #FDFBF7; /* พื้นหลังสีครีมอ่อน */
    }

    /* ซ่อน Header */
    header {visibility: hidden;}
    footer {visibility: hidden;}

    /* ปรับแต่งปุ่มกด (ธีมทอง/น้ำตาล) */
    .stButton>button {
        border-radius: 8px;
        font-weight: bold;
        background-color: #8D6E63; /* สีน้ำตาลวินเทจ */
        color: white;
        border: none;
        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
    }
    .stButton>button:hover {
        background-color: #6D4C41; /* เข้มขึ้นเมื่อเอาเมาส์ชี้ */
        color: #FFECB3; /* ตัวหนังสือสีทอง */
    }

    /* กล่องข้อความ และ Input */
    .stTextInput>div>div>input {
        background-color: white;
        border: 1px solid #D7CCC8;
    }

    /* ของหมด */
    .out-of-stock {
        filter: grayscale(100%);
        opacity: 0.6;
    }

    /* หัวข้อต่างๆ สีน้ำตาลเข้ม */
    h1, h2, h3 {
        color: #3E2723 !important; 
    }
</style>
""", unsafe_allow_html=True)

# ================= 4. โหลดข้อมูล =================
if 'basket' not in st.session_state:
    st.session_state.basket = []
if 'page' not in st.session_state:
    st.session_state.page = 'menu'
if 'last_wrong_pass' not in st.session_state:
    st.session_state.last_wrong_pass = ""

menu_df = load_menu()
tables_df = load_tables()

# ================= 5. ส่วนจัดการ (Admin Sidebar) =================
with st.sidebar:
    st.header("⚙️ จัดการร้าน (Admin)")
    admin_mode = st.checkbox("เข้าสู่โหมดผู้ดูแลระบบ")

    if admin_mode:
        st.markdown("---")
        password_input = st.text_input("🔑 ใส่รหัสผ่านเพื่อแก้ไข", type="password")

        if password_input == "090090op":
            st.success("รหัสถูกต้อง! ✅")
            st.session_state.last_wrong_pass = ""

            # --- 1. จัดการโต๊ะ ---
            st.subheader("🪑 จัดการโต๊ะ")
            with st.form("add_table_form"):
                new_table_name = st.text_input("ชื่อโต๊ะใหม่")
                if st.form_submit_button("เพิ่มโต๊ะ"):
                    if new_table_name:
                        if new_table_name not in tables_df['table_name'].values:
                            new_row = pd.DataFrame([{"table_name": new_table_name}])
                            tables_df = pd.concat([tables_df, new_row], ignore_index=True)
                            tables_df.to_csv(TABLES_CSV, index=False)
                            st.success(f"เพิ่มเรียบร้อย!")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.warning("ชื่อซ้ำ")

            table_to_delete = st.selectbox("เลือกโต๊ะที่จะลบ", ["-เลือก-"] + tables_df['table_name'].tolist())
            if st.button("ยืนยันลบโต๊ะ") and table_to_delete != "-เลือก-":
                tables_df = tables_df[tables_df['table_name'] != table_to_delete]
                tables_df.to_csv(TABLES_CSV, index=False)
                st.rerun()

            st.markdown("---")
            # --- 2. จัดการสต็อก ---
            st.subheader("📦 จัดการสต็อก")
            edited_df = st.data_editor(
                menu_df[['name', 'in_stock']],
                column_config={
                    "name": "ชื่อเมนู",
                    "in_stock": st.column_config.CheckboxColumn("สถานะ", default=True)
                },
                disabled=["name"],
                hide_index=True
            )
            if st.button("บันทึกสต็อก"):
                menu_df['in_stock'] = edited_df['in_stock']
                menu_df.to_csv(MENU_CSV, index=False)
                st.toast("บันทึกแล้ว!", icon="💾")
                time.sleep(1)
                st.rerun()

            st.markdown("---")
            # --- 3. เพิ่ม/ลบ เมนู ---
            st.subheader("❌ ลบเมนู")
            item_to_delete = st.selectbox("เลือกเมนู", ["-เลือก-"] + menu_df['name'].tolist())
            if st.button("ยืนยันลบเมนู") and item_to_delete != "-เลือก-":
                menu_df = menu_df[menu_df['name'] != item_to_delete]
                menu_df.to_csv(MENU_CSV, index=False)
                st.rerun()

            st.subheader("➕ เพิ่มเมนู")
            with st.form("add_menu_form"):
                new_name = st.text_input("ชื่อเมนู")
                new_price = st.number_input("ราคา", min_value=0, value=50)
                new_cat = st.selectbox("หมวดหมู่", ["Meat", "Seafood", "Veggie", "Snack", "Drink"])
                new_img = st.text_input("URL รูปภาพ", "https://placehold.co/400")
                if st.form_submit_button("บันทึกเมนู"):
                    if new_name:
                        new_data = pd.DataFrame(
                            [{"name": new_name, "price": new_price, "img": new_img, "category": new_cat,
                              "in_stock": True}])
                        menu_df = pd.concat([menu_df, new_data], ignore_index=True)
                        menu_df.to_csv(MENU_CSV, index=False)
                        st.rerun()

        elif password_input:
            st.error("รหัสผิด! ❌")
            if st.session_state.last_wrong_pass != password_input:
                thai_now = get_thai_time().strftime('%d/%m/%Y %H:%M:%S')
                send_email_notification("🚨 Alert: รหัส Admin ผิด", f"เวลา: {thai_now}\nรหัสที่ใส่: {password_input}")
                st.session_state.last_wrong_pass = password_input
        else:
            st.info("กรุณาใส่รหัสผ่าน")

# ================= 6. ส่วนหน้าจอหลัก (ลูกค้า) =================

# --- ส่วน Header (โลโก้ + ชื่อร้าน) ---
# ปรับตัวเลขตรงนี้ [0.6, 2, 4] เพื่อบีบให้ช่องแรก(โลโก้)แคบๆ จะได้อยู่ใกล้ชื่อร้าน
c_logo, c_name, c_space = st.columns([0.6, 2, 4])

with c_logo:
    if os.path.exists("logo.png"):
        st.image("logo.png", width=100)  # ปรับขนาดรูปให้พอดี
    else:
        st.markdown("<h1>🍲</h1>", unsafe_allow_html=True)

with c_name:
    # ใช้ CSS จัดให้ตัวหนังสืออยู่กึ่งกลางความสูงของรูป และเป็นสีน้ำตาลเข้ม
    st.markdown("""
        <div style="display: flex; align-items: center; height: 100px;">
            <h1 style='color:#3E2723; font-size:48px; margin:0; font-family: "Sarabun", sans-serif;'>Timnoi</h1>
        </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# --- ส่วนเลือกโต๊ะ ---
col_table, col_cust = st.columns(2)
with col_table:
    st.markdown("### 📍 เลือกโต๊ะ")
    table_list = tables_df['table_name'].tolist()
    if not table_list: table_list = ["โต๊ะ 1"]
    table_no = st.selectbox("label_table", table_list, label_visibility="collapsed")

with col_cust:
    st.markdown("### 👤 ชื่อลูกค้า")
    customer_name = st.text_input("label_name", "ลูกค้าทั่วไป", label_visibility="collapsed")

st.markdown("<br>", unsafe_allow_html=True)  # เว้นบรรทัดนิดนึง

# --- Page Controller ---
if st.session_state.page == 'menu':
    st.subheader("📝 รายการอาหาร")

    # Grid อาหาร
    cols = st.columns(4)
    for index, row in menu_df.iterrows():
        with cols[index % 4]:
            with st.container(border=True):
                is_in_stock = row.get('in_stock', True)
                try:
                    if is_in_stock:
                        st.image(row['img'], use_container_width=True)
                    else:
                        st.markdown(
                            f'<div style="opacity: 0.5; filter: grayscale(100%);"><img src="{row["img"]}" style="width:100%; border-radius:8px;"></div>',
                            unsafe_allow_html=True)
                        st.markdown(
                            "<div style='text-align:center; color:#B71C1C; font-weight:bold; margin-top:-80px; margin-bottom:60px; font-size:18px; text-shadow: 1px 1px 0px white;'>❌ หมดชั่วคราว</div>",
                            unsafe_allow_html=True)
                except:
                    st.image("https://placehold.co/400", caption="No Image")

                st.markdown(f"**{row['name']}**")

                if is_in_stock:
                    st.caption(f"ราคา: {row['price']} บาท")
                    if st.button(f"ใส่ตะกร้า 🛒", key=f"add_{index}", use_container_width=True):
                        st.session_state.basket.append(row.to_dict())
                        st.toast(f"เพิ่ม {row['name']} แล้ว!", icon="✅")
                else:
                    st.caption(f"ราคา: {row['price']} บาท (หมด)")
                    st.button("❌ หมด", key=f"add_{index}", disabled=True, use_container_width=True)

    if len(st.session_state.basket) > 0:
        st.markdown("---")
        c1, c2 = st.columns([3, 1])
        with c1:
            st.info(f"🛒 ตะกร้า: {len(st.session_state.basket)} รายการ")
        with c2:
            if st.button("ไปหน้าสรุปออเดอร์ ➡️", type="primary", use_container_width=True):
                st.session_state.page = 'cart'
                st.rerun()

elif st.session_state.page == 'cart':
    st.button("⬅️ กลับไปเลือกอาหาร", on_click=lambda: st.session_state.update(page='menu'))

    st.markdown(f"""
    <div style="background-color:#5D4037; color:white; padding:20px; border-radius:10px; text-align:center; margin-bottom:20px;">
        <h2>🛒 สรุปรายการสั่งซื้อ</h2>
        <p>โต๊ะ: {table_no} | คุณ: {customer_name}</p>
    </div>
    """, unsafe_allow_html=True)

    if len(st.session_state.basket) > 0:
        total_price = sum([item['price'] for item in st.session_state.basket])

        basket_df = pd.DataFrame(st.session_state.basket)
        summary_df = basket_df['name'].value_counts().reset_index()
        summary_df.columns = ['รายการ', 'จำนวน']
        summary_df['ราคาต่อหน่วย'] = summary_df['รายการ'].apply(
            lambda x: menu_df[menu_df['name'] == x]['price'].values[0])
        summary_df['รวม'] = summary_df['จำนวน'] * summary_df['ราคาต่อหน่วย']

        st.dataframe(summary_df, hide_index=True, use_container_width=True)

        st.markdown(f"### 💰 ยอดรวม: **{total_price}** บาท")
        remark = st.text_area("💬 หมายเหตุ", placeholder="เช่น ไม่ใส่ผัก")

        if st.button("✅ ยืนยันการสั่ง (Confirm)", type="primary", use_container_width=True):
            thai_now_str = get_thai_time().strftime("%d/%m/%Y %H:%M")
            items_str = ", ".join([f"{row['รายการ']} (x{row['จำนวน']})" for index, row in summary_df.iterrows()])

            save_order({
                "เวลา": thai_now_str,
                "โต๊ะ": table_no,
                "ลูกค้า": customer_name,
                "รายการอาหาร": items_str,
                "ยอดรวม": total_price,
                "หมายเหตุ": remark
            })

            email_body = f"โต๊ะ: {table_no}\nลูกค้า: {customer_name}\nเวลา: {thai_now_str}\n\n{items_str}\n\nยอดรวม: {total_price} บาท\nหมายเหตุ: {remark}"
            send_email_notification(f"🔔 Order ใหม่: {table_no}", email_body)

            st.session_state.basket = []
            st.session_state.page = 'menu'
            st.balloons()
            st.success("สั่งเรียบร้อย!")
            time.sleep(2)
            st.rerun()
    else:
        st.warning("ตะกร้าว่างเปล่า")