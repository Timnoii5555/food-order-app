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

# ใช้ชื่อไฟล์ v2 เพื่อความเสถียรของคอลัมน์
ORDER_CSV = 'order_data_v2.csv'
MENU_CSV = 'menu_data.csv'
TABLES_CSV = 'tables_data.csv'
IMAGE_FOLDER = 'uploaded_images'

if not os.path.exists(IMAGE_FOLDER):
    os.makedirs(IMAGE_FOLDER)


# ================= 2. ฟังก์ชันจัดการข้อมูล =================

def load_menu():
    columns = ["name", "price", "img", "category", "in_stock"]
    if not os.path.exists(MENU_CSV):
        default_data = [
            {"name": "หมูหมัก", "price": 120,
             "img": "https://images.unsplash.com/photo-1615937657715-bc7b4b7962c1?auto=format&fit=crop&w=500&q=60",
             "category": "เนื้อสัตว์ (Meat)", "in_stock": True},
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
        for col in columns:
            if col not in df.columns:
                df[col] = "" if col != "price" and col != "in_stock" else (0 if col == "price" else True)
    except:
        df = pd.DataFrame(columns=columns)

    df['img'] = df['img'].astype(str)
    return df


def load_tables():
    if not os.path.exists(TABLES_CSV):
        default_tables = ["โต๊ะ 1", "โต๊ะ 2", "โต๊ะ 3", "โต๊ะ 4", "กลับบ้าน"]
        df = pd.DataFrame(default_tables, columns=["table_name"])
        df.to_csv(TABLES_CSV, index=False)
    return pd.read_csv(TABLES_CSV)


def load_orders():
    # บังคับชื่อคอลัมน์ภาษาอังกฤษ เพื่อป้องกันปัญหา CSV พัง
    cols = ["Timestamp", "Table_No", "Customer_Name", "Order_Items", "Total_Price", "Notes", "Status"]

    if not os.path.exists(ORDER_CSV):
        df = pd.DataFrame(columns=cols)
        df.to_csv(ORDER_CSV, index=False)
        return df

    try:
        df = pd.read_csv(ORDER_CSV)
        # ถ้าไฟล์เก่าคอลัมน์ไม่ครบ ให้เคลียร์ทิ้งสร้างใหม่ (ป้องกัน Error ตัวแดง)
        if len(df.columns) != len(cols):
            df = pd.DataFrame(columns=cols)
        df.columns = cols
        return df
    except:
        return pd.DataFrame(columns=cols)


def save_image(uploaded_file):
    if uploaded_file is not None:
        timestamp = int(time.time())
        file_ext = uploaded_file.name.split('.')[-1]
        new_filename = f"img_{timestamp}.{file_ext}"
        file_path = os.path.join(IMAGE_FOLDER, new_filename)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        return file_path
    return None


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
        return True
    except Exception as e:
        st.error(f"❌ ส่งอีเมลไม่สำเร็จ: {e}")
        return False


def save_order(data):
    df = load_orders()

    new_row = {
        "Timestamp": data['เวลา'],
        "Table_No": data['โต๊ะ'],
        "Customer_Name": data['ลูกค้า'],
        "Order_Items": data['รายการอาหาร'],
        "Total_Price": data['ยอดรวม'],
        "Notes": data['หมายเหตุ'],
        "Status": data['สถานะ']
    }

    # เช็คว่าโต๊ะนี้มีบิลค้างไหม (waiting)
    mask = (df['Table_No'] == data['โต๊ะ']) & (df['Status'] == 'waiting')

    if mask.any():
        idx = df.index[mask][0]
        # รวมรายการ
        old_items = str(df.at[idx, 'Order_Items'])
        new_items = old_items + ", " + str(data['รายการอาหาร'])
        # รวมราคา
        try:
            old_price = float(df.at[idx, 'Total_Price'])
        except:
            old_price = 0.0
        new_price = old_price + float(data['ยอดรวม'])
        # รวมหมายเหตุ
        old_note = str(df.at[idx, 'Notes'])
        if old_note == 'nan': old_note = ""
        new_note = str(data['หมายเหตุ'])
        final_note = f"{old_note} | {new_note}" if new_note else old_note

        df.at[idx, 'Order_Items'] = new_items
        df.at[idx, 'Total_Price'] = new_price
        df.at[idx, 'Notes'] = final_note
        df.at[idx, 'Timestamp'] = data['เวลา']

        df.to_csv(ORDER_CSV, index=False)
        return "merged"
    else:
        df_new = pd.DataFrame([new_row])
        if not os.path.exists(ORDER_CSV):
            df_new.to_csv(ORDER_CSV, index=False)
        else:
            df_new.to_csv(ORDER_CSV, mode='a', header=False, index=False)
        return "new"


def get_thai_time():
    tz = pytz.timezone('Asia/Bangkok')
    return datetime.now(tz)


def add_to_cart_by_name(name):
    menu = load_menu()
    item = menu[menu['name'] == name].iloc[0].to_dict()
    st.session_state.basket.append(item)


def remove_from_cart_by_name(name):
    for i, item in enumerate(st.session_state.basket):
        if item['name'] == name:
            del st.session_state.basket[i]
            break


# ================= 3. UI & CSS =================
st.set_page_config(page_title="Timnoi Shabu", page_icon="🍲", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Kanit:wght@300;400;600&display=swap');

    html, body, [class*="css"] {
        font-family: 'Kanit', sans-serif;
        background-color: #F8F9FA;
    }
    header, footer {visibility: hidden;}

    .stContainer {
        background-color: white;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        padding: 10px;
    }

    /* ปุ่มกด */
    div[data-testid="stButton"] button {
        background-color: #8D6E63;
        color: white;
        border: none;
        border-radius: 8px;
        font-weight: 600;
    }
    div[data-testid="stButton"] button:hover {
        background-color: #6D4C41;
        transform: translateY(-2px);
    }

    /* ปุ่มเคลียร์ออเดอร์ (สีเขียว) */
    .clear-btn button {
        background-color: #2E7D32 !important;
        color: white !important;
        width: 100%;
    }

    /* กล่องคิว */
    .queue-card {
        background: linear-gradient(135deg, #4E342E 0%, #8D6E63 100%);
        color: white;
        padding: 20px;
        border-radius: 16px;
        text-align: center;
        box-shadow: 0 8px 20px rgba(141, 110, 99, 0.3);
        margin-bottom: 20px;
    }

    h1, h2, h3 { color: #3E2723 !important; }
</style>
""", unsafe_allow_html=True)

# ================= 4. โหลดข้อมูล =================
if 'basket' not in st.session_state: st.session_state.basket = []
if 'page' not in st.session_state: st.session_state.page = 'menu'
if 'app_mode' not in st.session_state: st.session_state.app_mode = 'customer'
if 'last_wrong_pass' not in st.session_state: st.session_state.last_wrong_pass = ""

menu_df = load_menu()
tables_df = load_tables()
orders_df = load_orders()
waiting_orders = orders_df[orders_df['Status'] == 'waiting']
queue_count = len(waiting_orders)

# ================= 5. ส่วนหัวและเมนู =================
c1, c2, c3 = st.columns([1, 2, 0.5])
with c1:
    if os.path.exists("logo.png"):
        st.image("logo.png", use_container_width=True)
    else:
        st.markdown("<h1>🍲</h1>", unsafe_allow_html=True)
with c2:
    st.markdown("""
    <div style="display: flex; align-items: center; height: 100px;">
        <div>
            <h1 style='color:#3E2723; font-size:36px; margin:0;'>Timnoi Shabu</h1>
            <p style='color:#8D6E63; margin:0;'>Premium Pork & Beef</p>
        </div>
    </div>
    """, unsafe_allow_html=True)
with c3:
    st.write("")
    with st.popover("☰ เมนู", use_container_width=True):
        if st.button("🏠 สั่งอาหาร", use_container_width=True):
            st.session_state.app_mode = 'customer'
            st.rerun()
        if st.button("⚙️ ระบบหลังร้าน", use_container_width=True):
            st.session_state.app_mode = 'admin_login'
            st.rerun()
        st.markdown("---")
        if st.button("🔄 รีเฟรช", use_container_width=True): st.rerun()

st.markdown("---")

# ================= 6. Controller =================

# === Admin Login ===
if st.session_state.app_mode == 'admin_login':
    st.markdown("### 🔐 เข้าสู่ระบบหลังร้าน")
    if st.button("⬅️ กลับ"):
        st.session_state.app_mode = 'customer'
        st.rerun()
    password_input = st.text_input("รหัสผ่าน", type="password")

    if password_input == "090090op":
        st.session_state.app_mode = 'admin_dashboard'
        st.rerun()
    elif password_input:
        st.error("รหัสผิด")
        if st.session_state.last_wrong_pass != password_input:
            thai_now = get_thai_time().strftime('%d/%m/%Y %H:%M:%S')
            is_sent = send_email_notification("🚨 Alert: รหัส Admin ผิด",
                                              f"เวลา: {thai_now}\nรหัสที่ใส่: {password_input}")
            if is_sent: st.toast("แจ้งเตือนไปที่ Email แล้ว")
            st.session_state.last_wrong_pass = password_input

# === Admin Dashboard ===
elif st.session_state.app_mode == 'admin_dashboard':
    st.markdown("### ⚙️ จัดการร้าน")
    if st.button("🚪 ออกจากระบบ"):
        st.session_state.app_mode = 'customer'
        st.rerun()

    tab1, tab2, tab3, tab4 = st.tabs(["👨‍🍳 ครัว/แคชเชียร์", "🪑 โต๊ะ/ของ", "📝 เมนู", "📊 ยอดขาย"])

    with tab1:  # ครัว
        st.info(f"🔥 โต๊ะที่กำลังทาน: {queue_count} โต๊ะ")
        if st.button("🔄 รีเฟรช"): st.rerun()

        if queue_count > 0:
            for index, row in waiting_orders.iterrows():
                with st.container():
                    # แสดงรายละเอียดออเดอร์
                    st.markdown(f"#### 🏷️ โต๊ะ: {row['Table_No']}")
                    st.caption(f"🕒 {row['Timestamp']} | 👤 {row['Customer_Name']}")

                    st.markdown("---")
                    st.markdown("**รายการอาหาร:**")
                    st.code(row['Order_Items'], language="text")

                    if str(row['Notes']) != 'nan' and str(row['Notes']) != '':
                        st.warning(f"💬 หมายเหตุ: {row['Notes']}")

                    try:
                        price_val = float(row['Total_Price'])
                    except:
                        price_val = 0.0
                    st.markdown(f"💰 **ยอดรวมสะสม: {price_val:,.0f} บาท**")

                    # === ปุ่มเคลียร์ออเดอร์ (แก้ไขให้เห็นชัดๆ) ===
                    st.markdown("---")
                    # ใช้ columns หลอกเพื่อให้ปุ่มเต็มความกว้าง
                    b1, b2 = st.columns([1, 1])
                    if st.button(f"✅ จบออเดอร์ / รับเงิน ({row['Table_No']})", key=f"pay_{index}", type="primary",
                                 use_container_width=True):
                        orders_df.at[index, 'Status'] = 'paid'
                        orders_df.to_csv(ORDER_CSV, index=False)
                        st.success(f"ปิดโต๊ะ {row['Table_No']} เรียบร้อย!")
                        time.sleep(1)
                        st.rerun()
                    st.markdown("---")
        else:
            st.success("✅ ครัวว่าง! ไม่มีออเดอร์ค้างครับ")

    with tab2:  # โต๊ะ/สต็อก
        c_stock, c_table = st.columns(2)
        with c_stock:
            st.markdown("#### 📦 ตัดสต็อก")
            edited_stock = st.data_editor(menu_df[['name', 'in_stock']], disabled=["name"], hide_index=True,
                                          use_container_width=True)
            if st.button("บันทึกสต็อก"):
                menu_df['in_stock'] = edited_stock['in_stock']
                menu_df.to_csv(MENU_CSV, index=False)
                st.toast("บันทึกแล้ว")
        with c_table:
            st.markdown("#### 🪑 จัดการโต๊ะ")
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

    with tab3:  # เมนู
        st.markdown("#### ➕ เพิ่มเมนูใหม่")
        with st.form("add_m"):
            n = st.text_input("ชื่อเมนู")
            p = st.number_input("ราคา", min_value=0)
            cat_list = ["น้ำซุป (Soup)", "เนื้อสัตว์ (Meat)", "ทะเล (Seafood)", "ผัก (Veggie)", "ของทานเล่น (Snack)",
                        "เครื่องดื่ม (Drink)", "อื่นๆ (Other)"]
            c = st.selectbox("หมวดหมู่", cat_list)

            st.markdown("**รูปภาพสินค้า:**")
            uploaded_file = st.file_uploader("อัปโหลดรูป", type=['png', 'jpg', 'jpeg'])
            img_url_input = st.text_input("หรือใส่ URL", "https://placehold.co/400")

            if st.form_submit_button("บันทึกเมนู"):
                if n:
                    final_img_path = img_url_input
                    if uploaded_file is not None:
                        saved_path = save_image(uploaded_file)
                        if saved_path: final_img_path = saved_path

                    nd = pd.DataFrame([{"name": n, "price": p, "img": final_img_path, "category": c, "in_stock": True}])
                    menu_df = pd.concat([menu_df, nd], ignore_index=True)
                    menu_df.to_csv(MENU_CSV, index=False)
                    st.success(f"เพิ่ม {n} สำเร็จ!")
                    time.sleep(1)
                    st.rerun()

        st.markdown("#### ❌ ลบเมนู")
        del_m = st.selectbox("เลือกเมนูลบ", ["-"] + menu_df['name'].tolist())
        if st.button("ลบเมนู") and del_m != "-":
            menu_df = menu_df[menu_df['name'] != del_m]
            menu_df.to_csv(MENU_CSV, index=False)
            st.rerun()

    with tab4:  # ยอดขาย
        st.markdown("#### 📊 สรุปยอดขายวันนี้")
        today_str = get_thai_time().strftime("%d/%m/%Y")
        st.caption(f"วันที่: {today_str}")

        if 'Status' in orders_df.columns:
            daily_sales = orders_df[
                (orders_df['Status'] == 'paid') &
                (orders_df['Timestamp'].astype(str).str.contains(today_str))
                ]
            total_revenue = daily_sales['Total_Price'].sum()

            st.metric(label="ยอดขายรวม", value=f"{total_revenue:,.0f} ฿", delta=f"{len(daily_sales)} บิล")
            st.dataframe(daily_sales[['Timestamp', 'Table_No', 'Total_Price', 'Order_Items']], hide_index=True,
                         use_container_width=True)

# === Customer Page ===
else:
    if queue_count > 0:
        st.markdown(f"""
        <div class="queue-card">
            <h3 style='color:#FFD700 !important; margin:0;'>🔥 คิวรออาหาร: {queue_count} คิว</h3>
            <p style='margin:0; opacity:0.8;'>ครัวกำลังเร่งมือครับ!</p>
        </div>""", unsafe_allow_html=True)

    col_ref1, col_ref2, col_ref3 = st.columns([1, 2, 1])
    with col_ref2:
        if st.button("🔄 เช็คสถานะล่าสุด", use_container_width=True): st.rerun()

    with st.container():
        c_t, c_c = st.columns(2)
        with c_t:
            st.markdown("##### 📍 เลือกโต๊ะ")
            tbls = tables_df['table_name'].tolist()
            if not tbls: tbls = ["โต๊ะ 1"]
            table_no = st.selectbox("table", tbls, label_visibility="collapsed")
        with c_c:
            st.markdown("##### 👤 ชื่อลูกค้า")
            cust_name = st.text_input("cust", "ลูกค้าทั่วไป", label_visibility="collapsed")

    st.write("")

    if st.session_state.page == 'menu':
        if len(st.session_state.basket) > 0:
            if st.button(f"🛒 ดูตะกร้า ({len(st.session_state.basket)} รายการ) ➡️", type="primary",
                         use_container_width=True):
                st.session_state.page = 'cart'
                st.rerun()

        categories = menu_df['category'].unique()
        tabs = st.tabs(list(categories))

        for i, cat in enumerate(categories):
            with tabs[i]:
                cat_menu = menu_df[menu_df['category'] == cat]
                cols = st.columns(2)
                for idx, row in cat_menu.iterrows():
                    with cols[idx % 2]:
                        with st.container():
                            is_stock = row.get('in_stock', True)
                            img_src = str(row['img'])
                            try:
                                if is_stock:
                                    st.image(img_src, use_container_width=True)
                                else:
                                    st.markdown(
                                        f'<div style="opacity:0.5;filter:grayscale(100%);"><img src="{img_src}" style="width:100%;border-radius:10px;"></div>',
                                        unsafe_allow_html=True)
                                    st.caption("❌ หมดชั่วคราว")
                            except:
                                st.image("https://placehold.co/400", caption="No Image")

                            st.markdown(f"**{row['name']}**")
                            st.caption(f"{row['price']} บาท")

                            if is_stock:
                                if st.button("เพิ่ม +", key=f"add_{cat}_{idx}", use_container_width=True):
                                    st.session_state.basket.append(row.to_dict())
                                    st.toast(f"เพิ่ม {row['name']} แล้ว")
                            else:
                                st.button("หมด", key=f"out_{cat}_{idx}", disabled=True, use_container_width=True)

    elif st.session_state.page == 'cart':
        st.button("⬅️ สั่งอาหารต่อ", on_click=lambda: st.session_state.update(page='menu'))
        st.markdown(f"### 🛒 ตะกร้าของ: {table_no}")

        if len(st.session_state.basket) > 0:
            basket_df = pd.DataFrame(st.session_state.basket)
            summary = basket_df['name'].value_counts().reset_index()
            summary.columns = ['name', 'count']

            total_price = 0

            for index, row in summary.iterrows():
                item_name = row['name']
                count = row['count']
                item_info = menu_df[menu_df['name'] == item_name].iloc[0]
                price = item_info['price']
                subtotal = price * count
                total_price += subtotal

                with st.container():
                    c_img, c_detail = st.columns([1, 2])
                    with c_img:
                        try:
                            st.image(str(item_info['img']), use_container_width=True)
                        except:
                            st.write("No Img")
                    with c_detail:
                        st.markdown(f"**{item_name}**")
                        st.caption(f"{price} บ. x {count} = **{subtotal} บ.**")

                    # === ย้ายปุ่ม + - มาอยู่ด้านล่าง + ปุ่มบวกอยู่ซ้าย ลบอยู่ขวา ===
                    st.write("")
                    btn_c1, btn_c2, btn_c3 = st.columns([1, 1, 1])

                    # ปุ่ม (+) อยู่ซ้าย (ตามสั่ง)
                    with btn_c1:
                        if st.button("➕", key=f"inc_{index}", help="เพิ่มจำนวน"):
                            add_to_cart_by_name(item_name)
                            st.rerun()
                    # ตัวเลข
                    with btn_c2:
                        st.markdown(
                            f"<div style='text-align:center; padding-top:5px; font-weight:bold; font-size:18px;'>{count}</div>",
                            unsafe_allow_html=True)
                    # ปุ่ม (-) อยู่ขวา (ตามสั่ง)
                    with btn_c3:
                        if st.button("➖", key=f"del_{index}", help="ลดจำนวน"):
                            remove_from_cart_by_name(item_name)
                            st.rerun()

            st.markdown("---")
            st.markdown(f"### 💵 รวมทั้งสิ้น: {total_price:,.0f} บาท")
            note = st.text_area("📝 หมายเหตุถึงครัว (ไม่ใส่ผัก, เผ็ดน้อย)")

            if st.button("✅ ยืนยันการสั่ง", type="primary", use_container_width=True):
                now_str = get_thai_time().strftime("%d/%m/%Y %H:%M")
                items_str = ", ".join([f"{r['name']}(x{r['count']})" for i, r in summary.iterrows()])

                status = save_order({
                    "เวลา": now_str,
                    "โต๊ะ": table_no,
                    "ลูกค้า": cust_name,
                    "รายการอาหาร": items_str,
                    "ยอดรวม": total_price,
                    "หมายเหตุ": note,
                    "สถานะ": "waiting"
                })

                # ส่งอีเมล
                body_intro = "🔔 Order เพิ่มเติม" if status == "merged" else "🔔 Order ใหม่"
                body = f"โต๊ะ: {table_no}\nลูกค้า: {cust_name}\nเวลา: {now_str}\n\n{items_str}\n\nสั่งรอบนี้: {total_price} บาท\nNote: {note}"
                is_sent = send_email_notification(f"{body_intro}: {table_no}", body)

                if is_sent: st.toast("ส่งข้อมูลเข้าครัวเรียบร้อย")

                st.session_state.basket = []
                st.session_state.page = 'menu'
                st.balloons()
                st.success("ส่งออเดอร์เรียบร้อย!")
                time.sleep(2)
                st.rerun()
        else:
            st.info("ตะกร้าว่างเปล่า")
            st.button("กลับไปเลือกอาหาร", on_click=lambda: st.session_state.update(page='menu'))