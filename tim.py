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


# ฟังก์ชันโหลดออเดอร์ (พร้อมระบบ Status)
def load_orders():
    if not os.path.exists(ORDER_CSV):
        df = pd.DataFrame(columns=["เวลา", "โต๊ะ", "ลูกค้า", "รายการอาหาร", "ยอดรวม", "หมายเหตุ", "สถานะ"])
        df.to_csv(ORDER_CSV, index=False)
        return df

    df = pd.read_csv(ORDER_CSV)
    # ถ้าไฟล์เก่าไม่มีคอลัมน์สถานะ ให้เพิ่มเข้าไป
    if 'สถานะ' not in df.columns:
        df['สถานะ'] = 'waiting'  # waiting = รอทำ, done = เสร็จแล้ว
        df.to_csv(ORDER_CSV, index=False)
    return df


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
    df = load_orders()  # โหลดเพื่อเช็คหัวตาราง
    df_new = pd.DataFrame([data])
    # บันทึกโดยไม่ทับของเก่า (mode='a') แต่ต้องระวัง header
    if not os.path.exists(ORDER_CSV):
        df_new.to_csv(ORDER_CSV, index=False)
    else:
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
        background-color: #FDFBF7;
    }

    header {visibility: hidden;}
    footer {visibility: hidden;}

    /* ปุ่มกดทั่วไป */
    .stButton>button {
        border-radius: 8px;
        font-weight: bold;
        background-color: #8D6E63;
        color: white;
        border: none;
        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
    }
    .stButton>button:hover {
        background-color: #6D4C41;
        color: #FFECB3;
    }

    /* ปุ่มเสร็จสิ้น (สีเขียว) ในหน้าครัว */
    .done-btn {
        background-color: #2E7D32 !important;
        color: white !important;
    }

    .stTextInput>div>div>input {
        background-color: white;
        border: 1px solid #D7CCC8;
    }

    .out-of-stock {
        filter: grayscale(100%);
        opacity: 0.6;
    }

    h1, h2, h3 { color: #3E2723 !important; }

    /* กล่องคิว */
    .queue-box {
        background-color: #3E2723;
        color: #FFECB3;
        padding: 15px;
        border-radius: 10px;
        text-align: center;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
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
if 'my_order_time' not in st.session_state:
    st.session_state.my_order_time = None

menu_df = load_menu()
tables_df = load_tables()
orders_df = load_orders()

# นับจำนวนคิวที่รอ (สถานะ waiting)
waiting_orders = orders_df[orders_df['สถานะ'] == 'waiting']
queue_count = len(waiting_orders)

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

            # === NEW: ระบบครัว (Kitchen Display) ===
            st.subheader("👨‍🍳 ออเดอร์รอทำ (Kitchen)")
            st.info(f"รอคิว: {queue_count} รายการ")

            if queue_count > 0:
                # วนลูปแสดงออเดอร์ที่ค้างอยู่
                # ใช้ .iterrows() เพื่อดึง index มาใช้ในการอัปเดต
                for index, row in waiting_orders.iterrows():
                    with st.container(border=True):
                        k1, k2 = st.columns([3, 1])
                        with k1:
                            st.markdown(f"**โต๊ะ: {row['โต๊ะ']}** | 🕒 {row['เวลา']}")
                            st.markdown(f"👤 {row['ลูกค้า']}")
                            st.code(row['รายการอาหาร'], language="text")
                            if str(row['หมายเหตุ']) != 'nan' and str(row['หมายเหตุ']) != '':
                                st.warning(f"💬 Note: {row['หมายเหตุ']}")
                        with k2:
                            # ปุ่มทำเสร็จ
                            if st.button("✅ เสร็จ", key=f"done_{index}", use_container_width=True):
                                # อัปเดตสถานะเป็น done
                                orders_df.at[index, 'สถานะ'] = 'done'
                                orders_df.to_csv(ORDER_CSV, index=False)
                                st.toast("เคลียร์ออเดอร์แล้ว!", icon="🍳")
                                time.sleep(0.5)
                                st.rerun()
            else:
                st.info("ว่างครับ! ไม่มีออเดอร์ค้าง")

            st.markdown("---")

            # --- จัดการอื่นๆ (เหมือนเดิม) ---
            with st.expander("🛠️ ตั้งค่าเมนู/โต๊ะ/สต็อก"):
                # 1. จัดการโต๊ะ
                st.caption("จัดการโต๊ะ")
                with st.form("add_table_form"):
                    new_table_name = st.text_input("ชื่อโต๊ะใหม่")
                    if st.form_submit_button("เพิ่มโต๊ะ"):
                        if new_table_name and new_table_name not in tables_df['table_name'].values:
                            new_row = pd.DataFrame([{"table_name": new_table_name}])
                            tables_df = pd.concat([tables_df, new_row], ignore_index=True)
                            tables_df.to_csv(TABLES_CSV, index=False)
                            st.rerun()

                table_to_delete = st.selectbox("เลือกโต๊ะลบ", ["-เลือก-"] + tables_df['table_name'].tolist())
                if st.button("ลบโต๊ะ") and table_to_delete != "-เลือก-":
                    tables_df = tables_df[tables_df['table_name'] != table_to_delete]
                    tables_df.to_csv(TABLES_CSV, index=False)
                    st.rerun()

                st.markdown("---")
                # 2. จัดการสต็อก
                st.caption("จัดการสต็อก")
                edited_df = st.data_editor(
                    menu_df[['name', 'in_stock']],
                    column_config={"name": "เมนู", "in_stock": st.column_config.CheckboxColumn("มีของ?", default=True)},
                    disabled=["name"], hide_index=True
                )
                if st.button("บันทึกสต็อก"):
                    menu_df['in_stock'] = edited_df['in_stock']
                    menu_df.to_csv(MENU_CSV, index=False)
                    st.rerun()

                st.markdown("---")
                # 3. เพิ่ม/ลบ เมนู
                st.caption("เพิ่ม/ลบ เมนู")
                item_to_delete = st.selectbox("เลือกเมนูลบ", ["-เลือก-"] + menu_df['name'].tolist())
                if st.button("ลบเมนู") and item_to_delete != "-เลือก-":
                    menu_df = menu_df[menu_df['name'] != item_to_delete]
                    menu_df.to_csv(MENU_CSV, index=False)
                    st.rerun()

                with st.form("add_menu_form"):
                    new_name = st.text_input("ชื่อเมนู")
                    new_price = st.number_input("ราคา", min_value=0, value=50)
                    new_cat = st.selectbox("หมวดหมู่", ["Meat", "Seafood", "Veggie", "Snack", "Drink"])
                    new_img = st.text_input("URL รูป", "https://placehold.co/400")
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

# --- Header (โลโก้ + ชื่อร้าน) ---
c_logo, c_name, c_space = st.columns([0.6, 2, 4])
with c_logo:
    if os.path.exists("logo.png"):
        st.image("logo.png", width=100)
    else:
        st.markdown("<h1>🍲</h1>", unsafe_allow_html=True)
with c_name:
    st.markdown("""
        <div style="display: flex; align-items: center; height: 100px;">
            <h1 style='color:#3E2723; font-size:48px; margin:0; font-family: "Sarabun", sans-serif;'>Timnoi</h1>
        </div>
    """, unsafe_allow_html=True)

# --- QUEUE DISPLAY (ระบบคิวเรียลไทม์) ---
st.markdown("---")
if queue_count > 0:
    st.markdown(f"""
    <div class="queue-box">
        <h2>🔥 คิวรออาหารตอนนี้: {queue_count} คิว</h2>
        <p>พนักงานกำลังเร่งมือทำอาหารให้อย่างสุดฝีมือครับ!</p>
    </div>
    """, unsafe_allow_html=True)
else:
    st.markdown(f"""
    <div style="background-color:#E8F5E9; color:#2E7D32; padding:10px; border-radius:10px; text-align:center; margin-bottom:20px;">
        <h3>✅ ครัวว่าง พร้อมทำทันที!</h3>
    </div>
    """, unsafe_allow_html=True)

# ปุ่มอัปเดตสถานะ (สำหรับลูกค้ากดดูคิวล่าสุด)
if st.button("🔄 อัปเดตคิวล่าสุด"):
    st.rerun()

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

st.markdown("<br>", unsafe_allow_html=True)

# --- Page Controller ---
if st.session_state.page == 'menu':
    st.subheader("📝 รายการอาหาร")

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

        if st.button("✅ ยืนยันการสั่ง (Confirm)", type="