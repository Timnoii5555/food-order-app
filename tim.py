import streamlit as st
import pandas as pd
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from datetime import datetime
import time
import pytz
import shutil

# ================= 1. ตั้งค่าระบบ =================
SENDER_EMAIL = 'jaskaikai4@gmail.com'
SENDER_PASSWORD = 'zqyx nqdk ygww drpp'
RECEIVER_EMAIL = 'jaskaikai4@gmail.com'

ORDER_CSV = 'order_history.csv'
MENU_CSV = 'menu_data.csv'
TABLES_CSV = 'tables_data.csv'
IMAGE_FOLDER = 'uploaded_images'

if not os.path.exists(IMAGE_FOLDER):
    os.makedirs(IMAGE_FOLDER)


# ================= 2. ฟังก์ชันจัดการข้อมูล =================

def load_menu():
    # กำหนดหัวตารางให้ชัดเจน ป้องกันข้อมูลสลับช่อง
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
            {"name": "น้ำจิ้มสุกี้", "price": 0,
             "img": "https://images.unsplash.com/photo-1599321955726-9048b5b4aa8f?auto=format&fit=crop&w=500&q=60",
             "category": "อื่นๆ (Other)", "in_stock": True},
        ]
        df = pd.DataFrame(default_data)
        df.to_csv(MENU_CSV, index=False)

    try:
        df = pd.read_csv(MENU_CSV)
        # ตรวจสอบคอลัมน์ให้ครบ
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
    # บังคับเรียงคอลัมน์ให้ถูกต้อง แก้ปัญหา Note ไปโผล่ช่องราคา
    cols = ["เวลา", "โต๊ะ", "ลูกค้า", "รายการอาหาร", "ยอดรวม", "หมายเหตุ", "สถานะ"]
    if not os.path.exists(ORDER_CSV):
        df = pd.DataFrame(columns=cols)
        df.to_csv(ORDER_CSV, index=False)
        return df

    df = pd.read_csv(ORDER_CSV)
    # ถ้าคอลัมน์ไม่ครบ ให้สร้างใหม่
    for c in cols:
        if c not in df.columns: df[c] = ""

    return df[cols]  # Return แบบเรียงคอลัมน์เป๊ะๆ


def save_image(uploaded_file):
    if uploaded_file is not None:
        timestamp = int(time.time())
        # แก้ชื่อไฟล์ให้ปลอดภัย ตัดอักขระพิเศษออก
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
    except Exception as e:
        st.error(f"❌ ส่งอีเมลไม่สำเร็จ: {e}")


def save_order(data):
    df = load_orders()
    mask = (df['โต๊ะ'] == data['โต๊ะ']) & (df['สถานะ'] == 'waiting')

    if mask.any():
        idx = df.index[mask][0]
        # รวมรายการ
        old_items = str(df.at[idx, 'รายการอาหาร'])
        new_items = old_items + ", " + str(data['รายการอาหาร'])
        # รวมราคา
        old_price = float(df.at[idx, 'ยอดรวม'])
        new_price = old_price + float(data['ยอดรวม'])
        # รวมหมายเหตุ
        old_note = str(df.at[idx, 'หมายเหตุ'])
        if old_note == 'nan': old_note = ""
        new_note = str(data['หมายเหตุ'])
        final_note = f"{old_note} | {new_note}" if new_note else old_note

        df.at[idx, 'รายการอาหาร'] = new_items
        df.at[idx, 'ยอดรวม'] = new_price
        df.at[idx, 'หมายเหตุ'] = final_note
        df.at[idx, 'เวลา'] = data['เวลา']

        df.to_csv(ORDER_CSV, index=False)
        return "merged"
    else:
        df_new = pd.DataFrame([data])
        # ใช้ header=False ถ้ามีไฟล์อยู่แล้ว เพื่อไม่ให้หัวตารางซ้ำ
        mode = 'a' if os.path.exists(ORDER_CSV) else 'w'
        header = not os.path.exists(ORDER_CSV)
        df_new.to_csv(ORDER_CSV, mode=mode, header=header, index=False)
        return "new"


def get_thai_time():
    tz = pytz.timezone('Asia/Bangkok')
    return datetime.now(tz)


# ฟังก์ชันช่วยจัดการตะกร้า (+/-)
def add_to_cart_by_name(name):
    menu = load_menu()
    item = menu[menu['name'] == name].iloc[0].to_dict()
    st.session_state.basket.append(item)


def remove_from_cart_by_name(name):
    # ลบออกทีละ 1 ชิ้น
    for i, item in enumerate(st.session_state.basket):
        if item['name'] == name:
            del st.session_state.basket[i]
            break


# ================= 3. UI & CSS (Beautiful & Modern) =================
st.set_page_config(page_title="Timnoi Shabu", page_icon="🍲", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Kanit:wght@300;400;600&display=swap');

    html, body, [class*="css"] {
        font-family: 'Kanit', sans-serif;
        background-color: #F8F9FA; /* พื้นหลังสีเทาอ่อน สบายตา */
    }

    header, footer {visibility: hidden;}

    /* Card Design */
    .stContainer {
        background-color: white;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        padding: 10px;
    }

    /* ปุ่มกด */
    .stButton>button {
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.2s;
    }

    /* ปุ่มเพิ่มลงตะกร้า */
    div[data-testid="stButton"] button {
        background-color: #8D6E63;
        color: white;
        border: none;
    }
    div[data-testid="stButton"] button:hover {
        background-color: #6D4C41;
        transform: translateY(-2px);
    }

    /* ปุ่ม +/- ในตะกร้า */
    .small-btn button {
        padding: 0px 10px;
        font-size: 14px;
        line-height: 1;
        min-height: 30px;
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

    /* รูปภาพเมนู */
    .menu-img {
        border-radius: 10px;
        object-fit: cover;
        width: 100%;
        height: 150px;
    }

    /* Tab Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: white;
        border-radius: 20px;
        padding: 5px 20px;
        border: 1px solid #E0E0E0;
    }
    .stTabs [aria-selected="true"] {
        background-color: #8D6E63 !important;
        color: white !important;
        border-color: #8D6E63 !important;
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
waiting_orders = orders_df[orders_df['สถานะ'] == 'waiting']
queue_count = len(waiting_orders)

# ================= 5. ส่วนหัวและเมนู =================
c1, c2, c3 = st.columns([1, 2, 0.5])
with c1:
    # แก้โลโก้ไม่ชัด: เพิ่ม width และใช้ use_container_width
    if os.path.exists("logo.png"):
        st.image("logo.png", width=150)
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

# === Admin Dashboard ===
elif st.session_state.app_mode == 'admin_dashboard':
    st.markdown("### ⚙️ จัดการร้าน")
    if st.button("🚪 ออกจากระบบ"):
        st.session_state.app_mode = 'customer'
        st.rerun()

    tab1, tab2, tab3, tab4 = st.tabs(["👨‍🍳 ครัว", "🪑 โต๊ะ/ของ", "📝 เมนู", "📊 ยอดขาย"])

    with tab1:  # ครัว
        st.info(f"🔥 โต๊ะที่กำลังทาน: {queue_count} โต๊ะ")
        if st.button("🔄 รีเฟรช"): st.rerun()

        if queue_count > 0:
            for index, row in waiting_orders.iterrows():
                with st.container():
                    c1, c2 = st.columns([3, 1])
                    with c1:
                        st.markdown(f"### โต๊ะ: {row['โต๊ะ']}")
                        st.caption(f"เวลา: {row['เวลา']} | ลูกค้า: {row['ลูกค้า']}")
                        st.markdown("---")
                        # แก้ Note ไปโผล่ช่องราคา: แสดงแยกกันชัดเจน
                        st.markdown(f"**รายการอาหาร:**")
                        st.code(row['รายการอาหาร'], language="text")

                        if str(row['หมายเหตุ']) != 'nan' and str(row['หมายเหตุ']) != '':
                            st.warning(f"💬 หมายเหตุเพิ่มเติม: {row['หมายเหตุ']}")

                        st.markdown(f"💰 **ยอดรวมสะสม: {float(row['ยอดรวม']):,.0f} บาท**")

                    with c2:
                        if st.button("💰 รับเงิน (จบโต๊ะ)", key=f"pay_{index}", type="primary",
                                     use_container_width=True):
                            orders_df.at[index, 'สถานะ'] = 'paid'
                            orders_df.to_csv(ORDER_CSV, index=False)
                            st.success("เรียบร้อย")
                            time.sleep(1)
                            st.rerun()
        else:
            st.success("ยังไม่มีลูกค้า")

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
            # เพิ่มหมวดหมู่ให้เลือก
            cat_list = ["เนื้อสัตว์ (Meat)", "ทะเล (Seafood)", "ผัก (Veggie)", "ของทานเล่น (Snack)",
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

                    # บันทึกข้อมูลให้ครบทุกช่อง แก้ปัญหารูปหาย
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

        if 'สถานะ' in orders_df.columns:
            daily_sales = orders_df[
                (orders_df['สถานะ'] == 'paid') &
                (orders_df['เวลา'].astype(str).str.contains(today_str))
                ]
            total_revenue = daily_sales['ยอดรวม'].sum()

            st.metric(label="ยอดขายรวม", value=f"{total_revenue:,.0f} ฿", delta=f"{len(daily_sales)} บิล")
            st.dataframe(daily_sales[['เวลา', 'โต๊ะ', 'ยอดรวม', 'รายการอาหาร']], hide_index=True,
                         use_container_width=True)

# === Customer Page ===
else:
    # Queue Display
    if queue_count > 0:
        st.markdown(f"""
        <div class="queue-card">
            <h3 style='color:#FFD700 !important; margin:0;'>🔥 คิวรออาหาร: {queue_count} คิว</h3>
            <p style='margin:0; opacity:0.8;'>ครัวกำลังเร่งมือครับ!</p>
        </div>""", unsafe_allow_html=True)

    col_ref1, col_ref2, col_ref3 = st.columns([1, 2, 1])
    with col_ref2:
        if st.button("🔄 เช็คสถานะล่าสุด", use_container_width=True): st.rerun()

    # Table Selection
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

    # Menu Page
    if st.session_state.page == 'menu':
        # ปุ่มตะกร้าลอย
        if len(st.session_state.basket) > 0:
            if st.button(f"🛒 ดูตะกร้า ({len(st.session_state.basket)} รายการ) ➡️", type="primary",
                         use_container_width=True):
                st.session_state.page = 'cart'
                st.rerun()

        # แยกหมวดหมู่อาหาร (Tabs)
        categories = menu_df['category'].unique()
        # เรียงลำดับหมวดหมู่ (ถ้าต้องการ)
        # categories = sorted(categories)

        tabs = st.tabs(list(categories))

        for i, cat in enumerate(categories):
            with tabs[i]:
                # กรองเมนูเฉพาะหมวดนี้
                cat_menu = menu_df[menu_df['category'] == cat]

                # แสดงผลแบบ Grid
                cols = st.columns(2)
                for idx, row in cat_menu.iterrows():
                    with cols[idx % 2]:
                        with st.container():
                            # รูปภาพ
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

                            # ชื่อและราคา
                            st.markdown(f"**{row['name']}**")
                            st.caption(f"{row['price']} บาท")

                            # ปุ่มเพิ่ม
                            if is_stock:
                                if st.button("เพิ่ม +", key=f"add_{cat}_{idx}", use_container_width=True):
                                    st.session_state.basket.append(row.to_dict())
                                    st.toast(f"เพิ่ม {row['name']} แล้ว")
                            else:
                                st.button("หมด", key=f"out_{cat}_{idx}", disabled=True, use_container_width=True)

    # Cart Page (ปรับปรุงใหม่ มีปุ่ม +/-)
    elif st.session_state.page == 'cart':
        st.button("⬅️ สั่งอาหารต่อ", on_click=lambda: st.session_state.update(page='menu'))
        st.markdown(f"### 🛒 ตะกร้าของ: {table_no}")

        if len(st.session_state.basket) > 0:
            # รวมรายการที่เหมือนกัน
            basket_df = pd.DataFrame(st.session_state.basket)
            summary = basket_df['name'].value_counts().reset_index()
            summary.columns = ['name', 'count']

            total_price = 0

            # แสดงรายการแบบ Card มีปุ่ม +/-
            for index, row in summary.iterrows():
                item_name = row['name']
                count = row['count']

                # หาข้อมูลสินค้า
                item_info = menu_df[menu_df['name'] == item_name].iloc[0]
                price = item_info['price']
                subtotal = price * count
                total_price += subtotal

                with st.container():
                    c_img, c_detail, c_action = st.columns([1, 2, 1.5])
                    with c_img:
                        try:
                            st.image(str(item_info['img']), use_container_width=True)
                        except:
                            st.write("No Img")
                    with c_detail:
                        st.markdown(f"**{item_name}**")
                        st.caption(f"{price} บ. x {count} = **{subtotal} บ.**")
                    with c_action:
                        # ปุ่ม +/-
                        bc1, bc2, bc3 = st.columns([1, 1, 1])
                        with bc1:
                            if st.button("➖", key=f"del_{index}", help="ลดจำนวน"):
                                remove_from_cart_by_name(item_name)
                                st.rerun()
                        with bc2:
                            st.markdown(
                                f"<div style='text-align:center; padding-top:5px; font-weight:bold;'>{count}</div>",
                                unsafe_allow_html=True)
                        with bc3:
                            if st.button("➕", key=f"inc_{index}", help="เพิ่มจำนวน"):
                                add_to_cart_by_name(item_name)
                                st.rerun()

            st.markdown("---")
            st.markdown(f"### 💵 รวมทั้งสิ้น: {total_price:,.0f} บาท")
            note = st.text_area("📝 หมายเหตุถึงครัว (ไม่ใส่ผัก, เผ็ดน้อย)")

            if st.button("✅ ยืนยันการสั่ง", type="primary", use_container_width=True):
                now_str = get_thai_time().strftime("%d/%m/%Y %H:%M")

                # สร้าง string รายการอาหาร
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

                st.session_state.basket = []
                st.session_state.page = 'menu'
                st.balloons()
                st.success("ส่งออเดอร์เรียบร้อย!")
                time.sleep(2)
                st.rerun()
        else:
            st.info("ตะกร้าว่างเปล่า")
            st.button("กลับไปเลือกอาหาร", on_click=lambda: st.session_state.update(page='menu'))