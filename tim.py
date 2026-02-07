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
IMAGE_FOLDER = 'uploaded_images'
BANNER_FOLDER = 'banner_images'

if not os.path.exists(IMAGE_FOLDER): os.makedirs(IMAGE_FOLDER)
if not os.path.exists(BANNER_FOLDER): os.makedirs(BANNER_FOLDER)


# ================= 2. ฟังก์ชันจัดการข้อมูล =================

def load_menu():
    if not os.path.exists(MENU_CSV):
        default_data = [
            {"name": "หมูหมัก", "price": 120,
             "img": "https://images.unsplash.com/photo-1615937657715-bc7b4b7962c1?auto=format&fit=crop&w=500&q=60",
             "category": "Meat", "in_stock": True},
            {"name": "หมูสามชั้น", "price": 89,
             "img": "https://images.unsplash.com/photo-1600891964092-4316c288032e?auto=format&fit=crop&w=500&q=60",
             "category": "Meat", "in_stock": True},
            {"name": "กุ้งสด", "price": 150,
             "img": "https://images.unsplash.com/photo-1565680018434-b513d5e5fd47?auto=format&fit=crop&w=500&q=60",
             "category": "Seafood", "in_stock": True},
            {"name": "ผักกวางตุ้ง", "price": 40,
             "img": "https://images.unsplash.com/photo-1544025162-d76694265947?auto=format&fit=crop&w=500&q=60",
             "category": "Veggie", "in_stock": True},
        ]
        df = pd.DataFrame(default_data)
        df.to_csv(MENU_CSV, index=False)

    try:
        df = pd.read_csv(MENU_CSV)
    except:
        df = pd.DataFrame(columns=["name", "price", "img", "category", "in_stock"])
    if 'in_stock' not in df.columns: df['in_stock'] = True
    df['img'] = df['img'].astype(str)
    return df


def load_tables():
    if not os.path.exists(TABLES_CSV):
        default_tables = ["โต๊ะ 1", "โต๊ะ 2", "โต๊ะ 3", "โต๊ะ 4", "กลับบ้าน"]
        df = pd.DataFrame(default_tables, columns=["table_name"])
        df.to_csv(TABLES_CSV, index=False)
    return pd.read_csv(TABLES_CSV)


def load_orders():
    if not os.path.exists(ORDER_CSV):
        df = pd.DataFrame(columns=["เวลา", "โต๊ะ", "ลูกค้า", "รายการอาหาร", "ยอดรวม", "หมายเหตุ", "สถานะ"])
        df.to_csv(ORDER_CSV, index=False)
        return df
    return pd.read_csv(ORDER_CSV)


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


def get_image_base64(path):
    with open(path, "rb") as image_file:
        encoded = base64.b64encode(image_file.read()).decode()
    return f"data:image/png;base64,{encoded}"


def save_promo_banner(uploaded_file, index):
    if uploaded_file is not None:
        filename = f"banner_{index}.png"
        filepath = os.path.join(BANNER_FOLDER, filename)
        with open(filepath, "wb") as f:
            f.write(uploaded_file.getbuffer())
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
        text = msg.as_string()
        server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, text)
        server.quit()
    except Exception as e:
        st.error(f"❌ ส่งอีเมลไม่สำเร็จ: {e}")


def save_order(data):
    df = load_orders()
    mask = (df['โต๊ะ'] == data['โต๊ะ']) & (df['สถานะ'] == 'waiting')
    if mask.any():
        index_to_update = df.index[mask][0]
        old_items = str(df.at[index_to_update, 'รายการอาหาร'])
        new_items = old_items + ", " + str(data['รายการอาหาร'])
        old_price = float(df.at[index_to_update, 'ยอดรวม'])
        new_price = old_price + float(data['ยอดรวม'])
        old_note = str(df.at[index_to_update, 'หมายเหตุ'])
        if old_note == 'nan': old_note = ""
        new_note = data['หมายเหตุ']
        final_note = f"{old_note} | {new_note}" if new_note else old_note
        df.at[index_to_update, 'รายการอาหาร'] = new_items
        df.at[index_to_update, 'ยอดรวม'] = new_price
        df.at[index_to_update, 'หมายเหตุ'] = final_note
        df.at[index_to_update, 'เวลา'] = data['เวลา']
        df.to_csv(ORDER_CSV, index=False)
        return "merged"
    else:
        df_new = pd.DataFrame([data])
        if not os.path.exists(ORDER_CSV):
            df_new.to_csv(ORDER_CSV, index=False)
        else:
            df_new.to_csv(ORDER_CSV, mode='a', header=False, index=False)
        return "new"


def get_thai_time():
    tz = pytz.timezone('Asia/Bangkok')
    return datetime.now(tz)


# ================= 3. UI & CSS =================
st.set_page_config(page_title="Timnoi Shabu", page_icon="🍲", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;500;700&display=swap');
    html, body, [class*="css"] { font-family: 'Sarabun', sans-serif; background-color: #FDFBF7; }
    header, footer {visibility: hidden;}
    .stButton>button { border-radius: 8px; font-weight: bold; background-color: #8D6E63; color: white; border: none; box-shadow: 0 2px 4px rgba(0,0,0,0.2); }
    .stButton>button:hover { background-color: #6D4C41; color: #FFECB3; }

    .customer-queue-box { background: linear-gradient(135deg, #3E2723 0%, #5D4037 100%); color: white; padding: 20px; border-radius: 16px; text-align: center; margin-bottom: 20px; box-shadow: 0 8px 16px rgba(0,0,0,0.2); border: 2px solid #D7CCC8; }
    .queue-title { font-size: 18px; font-weight: bold; color: #FFECB3; text-transform: uppercase; }
    .queue-big-number { font-size: 56px; font-weight: 800; line-height: 1; color: white; margin: 10px 0; }
    .queue-empty { background-color: #E8F5E9; border: 2px dashed #4CAF50; color: #2E7D32; padding: 15px; border-radius: 12px; text-align: center; font-weight: bold; }

    .sales-box { background-color: #FFF3E0; border: 2px solid #FFB74D; color: #E65100; padding: 20px; border-radius: 12px; text-align: center; margin-bottom: 20px; }
    .sales-number { font-size: 48px; font-weight: bold; color: #BF360C; }

    .out-of-stock { filter: grayscale(100%); opacity: 0.6; }
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

# ================= 5. ส่วนหัวและเมนู (Full Header with Updated Text) =================
# จัด Layout ใหม่ให้โลโก้ 320px อยู่ซ้าย และข้อความอยู่ขวาแบบเต็มๆ
c_logo, c_name, c_menu = st.columns([1.3, 2, 0.5])

with c_logo:
    if os.path.exists("logo.png"):
        st.image("logo.png", width=320)
    else:
        st.markdown("<h1>🍲</h1>", unsafe_allow_html=True)

with c_name:
    # --- อัปเดตข้อความตรงนี้ตามที่ขอครับ ---
    st.markdown("""
        <div style="display: flex; flex-direction: column; justify-content: center; height: 220px;">
            <h1 style='color:#3E2723; font-size:60px; margin:0; line-height:1; font-weight:800;'>Timnoi</h1>
            <p style='color:#8D6E63; font-size:20px; margin:5px 0 0 0; font-weight:bold;'>ร้านนี้ไม่มีหมูเพราะที่เห็นเป็นเนื้อหมา</p>
            <div style='margin-top:15px; border-top: 2px solid #D7CCC8; padding-top:10px;'>
                <p style='color:#5D4037; font-size:16px; margin:0;'>🕒 เปิดบริการ: 00:00 - 23:59 น.</p>
                <p style='color:#5D4037; font-size:16px; margin:0;'>📞 โทร: 064-448-55549</p>
            </div>
        </div>
    """, unsafe_allow_html=True)

with c_menu:
    st.write("")
    with st.popover("☰", use_container_width=True):
        st.markdown("### เมนูหลัก")
        if st.button("🏠 หน้าลูกค้า", use_container_width=True):
            st.session_state.app_mode = 'customer'
            st.rerun()
        if st.button("⚙️ จัดการร้าน (Admin)", use_container_width=True):
            st.session_state.app_mode = 'admin_login'
            st.rerun()
        st.markdown("---")
        if st.button("🔄 รีเฟรช", use_container_width=True): st.rerun()

st.markdown("---")

# ================= 6. Controller =================

# === Admin Login ===
if st.session_state.app_mode == 'admin_login':
    st.subheader("🔐 เข้าสู่ระบบหลังร้าน")
    if st.button("⬅️ กลับ"):
        st.session_state.app_mode = 'customer'
        st.rerun()
    password_input = st.text_input("🔑 ใส่รหัสผ่าน", type="password")
    if password_input == "090090op":
        st.success("รหัสถูกต้อง! ✅")
        time.sleep(0.5)
        st.session_state.app_mode = 'admin_dashboard'
        st.rerun()
    elif password_input:
        st.error("รหัสผิด! ❌")
        if st.session_state.last_wrong_pass != password_input:
            thai_now = get_thai_time().strftime('%d/%m/%Y %H:%M:%S')
            send_email_notification("🚨 Alert: รหัส Admin ผิด", f"เวลา: {thai_now}\nรหัสที่ใส่: {password_input}")
            st.session_state.last_wrong_pass = password_input

# === Admin Dashboard ===
elif st.session_state.app_mode == 'admin_dashboard':
    st.subheader("⚙️ จัดการร้าน (Admin)")
    if st.button("🚪 ออกจากระบบ"):
        st.session_state.app_mode = 'customer'
        st.rerun()

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["👨‍🍳 ครัว", "📢 โปรโมชั่น(5)", "📦 สต็อก/โต๊ะ", "📝 เมนู", "📊 ยอดขาย"])

    with tab1:
        st.info(f"🔥 โต๊ะที่กำลังทานอยู่: {queue_count} โต๊ะ")
        if st.button("🔄 รีเฟรชออเดอร์"): st.rerun()
        if queue_count > 0:
            for index, row in waiting_orders.iterrows():
                with st.container(border=True):
                    c1, c2 = st.columns([3, 1])
                    with c1:
                        st.markdown(f"**{row['โต๊ะ']}** | {row['เวลา']}")
                        st.markdown(f"👤 {row['ลูกค้า']}")
                        st.info(f"💰 ยอดรวม: **{row['ยอดรวม']}** บาท")
                        with st.expander("รายการอาหาร"):
                            st.code(row['รายการอาหาร'], language="text")
                        if str(row['หมายเหตุ']) != 'nan': st.warning(f"Note: {row['หมายเหตุ']}")
                    with c2:
                        if st.button("💰 รับเงิน", key=f"pay_{index}", type="primary"):
                            orders_df.at[index, 'สถานะ'] = 'paid'
                            orders_df.to_csv(ORDER_CSV, index=False)
                            st.rerun()
        else:
            st.success("ไม่มีออเดอร์ค้าง")

    with tab2:
        st.header("📢 แบนเนอร์โปรโมชั่น (สูงสุด 5 รูป)")
        for i in range(1, 6):
            col_b1, col_b2 = st.columns([2, 1])
            filename = f"banner_{i}.png"
            filepath = os.path.join(BANNER_FOLDER, filename)
            with col_b1:
                uploaded = st.file_uploader(f"อัปโหลดรูป {i}", type=['png', 'jpg', 'jpeg'], key=f"ban_up_{i}")
                if uploaded:
                    if save_promo_banner(uploaded, i):
                        st.success(f"บันทึกรูป {i} แล้ว")
                        time.sleep(0.5)
                        st.rerun()
            with col_b2:
                if os.path.exists(filepath):
                    st.image(filepath, use_container_width=True)
                    if st.button(f"🗑️ ลบรูป {i}", key=f"del_ban_{i}"):
                        os.remove(filepath)
                        st.rerun()
                else:
                    st.info("ว่าง")
            st.markdown("---")

    with tab3:
        st.write("#### 📦 จัดการสต็อก")
        edited_stock = st.data_editor(menu_df[['name', 'in_stock']], disabled=["name"], hide_index=True)
        if st.button("บันทึกสต็อก"):
            menu_df['in_stock'] = edited_stock['in_stock']
            menu_df.to_csv(MENU_CSV, index=False)
            st.toast("บันทึกแล้ว")
        st.markdown("---")
        st.write("#### 🪑 จัดการโต๊ะ")
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

    with tab4:
        st.write("#### ➕ เพิ่มเมนู")
        with st.form("add_m"):
            n = st.text_input("ชื่อเมนู")
            p = st.number_input("ราคา", min_value=0)
            c = st.selectbox("หมวด", ["Meat", "Seafood", "Veggie", "Snack"])
            uploaded_file = st.file_uploader("อัปโหลดรูปจากเครื่อง", type=['png', 'jpg', 'jpeg'])
            img_url_input = st.text_input("หรือใส่ URL รูปภาพ", "https://placehold.co/400")
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
        st.write("#### ❌ ลบเมนู")
        del_m = st.selectbox("เลือกเมนูลบ", ["-"] + menu_df['name'].tolist())
        if st.button("ลบเมนู") and del_m != "-":
            menu_df = menu_df[menu_df['name'] != del_m]
            menu_df.to_csv(MENU_CSV, index=False)
            st.rerun()

    with tab5:  # สรุปยอดขาย
        st.subheader("📊 สรุปยอดขายรายวัน")
        today_str = get_thai_time().strftime("%d/%m/%Y")
        st.caption(f"ประจำวันที่: {today_str}")
        if 'สถานะ' in orders_df.columns:
            orders_df['ยอดรวม'] = pd.to_numeric(orders_df['ยอดรวม'], errors='coerce').fillna(0)
            daily_sales = orders_df[
                (orders_df['สถานะ'] == 'paid') & (orders_df['เวลา'].astype(str).str.contains(today_str))]
            total_revenue = daily_sales['ยอดรวม'].sum()
            st.markdown(
                f"""<div class="sales-box"><div>ยอดขายรวมวันนี้</div><div class="sales-number">{total_revenue:,.2f} ฿</div><div>จำนวน {len(daily_sales)} บิล</div></div>""",
                unsafe_allow_html=True)
            st.write("📜 **ประวัติการขายวันนี้:**")
            st.dataframe(daily_sales[['เวลา', 'โต๊ะ', 'ลูกค้า', 'ยอดรวม', 'รายการอาหาร']], hide_index=True,
                         use_container_width=True)
        else:
            st.warning("ยังไม่มีข้อมูลยอดขาย")

# === Customer Page ===
else:
    banner_images = []
    for i in range(1, 6):
        fpath = os.path.join(BANNER_FOLDER, f"banner_{i}.png")
        if os.path.exists(fpath):
            banner_images.append(get_image_base64(fpath))

    if len(banner_images) > 0:
        slides_html = ""
        for idx, img_b64 in enumerate(banner_images):
            display_style = "block" if idx == 0 else "none"
            slides_html += f"""
            <div class="mySlides fade" style="display: {display_style};">
              <img src="{img_b64}" style="width:100%; border-radius:15px; box-shadow: 0 4px 8px rgba(0,0,0,0.2);">
            </div>
            """
        components.html(f"""
        <!DOCTYPE html>
        <html>
        <head>
        <style>
        .mySlides {{display: none;}}
        img {{vertical-align: middle;}}
        .fade {{-webkit-animation-name: fade; -webkit-animation-duration: 1.5s; animation-name: fade; animation-duration: 1.5s;}}
        @-webkit-keyframes fade {{ from {{opacity: .4}} to {{opacity: 1}} }}
        @keyframes fade {{ from {{opacity: .4}} to {{opacity: 1}} }}
        </style>
        </head>
        <body>
        <div class="slideshow-container">{slides_html}</div>
        <script>
        let slideIndex = 0;
        showSlides();
        function showSlides() {{
          let i;
          let slides = document.getElementsByClassName("mySlides");
          for (i = 0; i < slides.length; i++) {{slides[i].style.display = "none";}}
          slideIndex++;
          if (slideIndex > slides.length) {{slideIndex = 1}}    
          slides[slideIndex-1].style.display = "block";  
          setTimeout(showSlides, 5000); 
        }}
        </script>
        </body>
        </html>
        """, height=320)

    if queue_count > 0:
        st.markdown(f"""
        <div class="customer-queue-box">
            <div class="queue-title">🔥 คิวรออาหารตอนนี้</div>
            <div class="queue-big-number">{queue_count}</div>
            <div class="queue-desc">คิว</div>
        </div>""", unsafe_allow_html=True)
    else:
        st.markdown("""<div class="queue-empty">✅ ครัวว่าง! สั่งปุ๊บ ได้ทานปั๊บ</div>""", unsafe_allow_html=True)

    col_ref1, col_ref2, col_ref3 = st.columns([1, 2, 1])
    with col_ref2:
        if st.button("🔄 เช็คคิวล่าสุด (Refresh)", use_container_width=True): st.rerun()

    st.markdown("---")

    c_t, c_c = st.columns(2)
    with c_t:
        st.markdown("### 📍 เลือกโต๊ะ")
        tbls = tables_df['table_name'].tolist()
        if not tbls: tbls = ["โต๊ะ 1"]
        table_no = st.selectbox("table", tbls, label_visibility="collapsed")
    with c_c:
        st.markdown("### 👤 ชื่อลูกค้า")
        cust_name = st.text_input("cust", "ลูกค้าทั่วไป", label_visibility="collapsed")

    st.markdown("<br>", unsafe_allow_html=True)

    if st.session_state.page == 'menu':
        st.subheader("📝 รายการอาหาร")
        cols = st.columns(2)
        for idx, row in menu_df.iterrows():
            with cols[idx % 2]:
                with st.container(border=True):
                    is_stock = row.get('in_stock', True)
                    img_src = str(row['img'])
                    try:
                        if is_stock:
                            st.image(img_src, use_container_width=True)
                        else:
                            st.markdown(
                                f'<div style="opacity:0.5;filter:grayscale(100%);"><img src="{img_src}" style="width:100%;border-radius:8px;"></div>',
                                unsafe_allow_html=True)
                            st.markdown(
                                "<div style='text-align:center;color:red;font-weight:bold;margin-top:-60px;margin-bottom:40px;'>❌ หมด</div>",
                                unsafe_allow_html=True)
                    except:
                        st.image("https://placehold.co/400")
                    st.markdown(f"**{row['name']}**")
                    if is_stock:
                        st.caption(f"{row['price']}.-")
                        if st.button("ใส่ตะกร้า", key=f"add_{idx}", use_container_width=True):
                            st.session_state.basket.append(row.to_dict())
                            st.toast(f"เพิ่ม {row['name']}")
                    else:
                        st.button("หมด", key=f"no_{idx}", disabled=True)

        if len(st.session_state.basket) > 0:
            st.markdown("---")
            if st.button(f"🛒 สรุปยอด ({len(st.session_state.basket)} รายการ) ➡️", type="primary",
                         use_container_width=True):
                st.session_state.page = 'cart'
                st.rerun()

    elif st.session_state.page == 'cart':
        st.button("⬅️ เลือกอาหารเพิ่ม", on_click=lambda: st.session_state.update(page='menu'))
        st.markdown(f"""
        <div style="background-color:#5D4037; color:white; padding:15px; border-radius:10px; text-align:center; margin-bottom:20px;">
            <h3>🛒 สรุปรายการสั่งซื้อ</h3>
            <p>โต๊ะ: {table_no} | คุณ: {cust_name}</p>
        </div>
        """, unsafe_allow_html=True)

        if len(st.session_state.basket) > 0:
            counts = Counter(item['name'] for item in st.session_state.basket)
            unique_items = {item['name']: item for item in st.session_state.basket}

            total_price = 0
            for name, count in counts.items():
                item = unique_items[name]
                item_total = item['price'] * count
                total_price += item_total

                with st.container(border=True):
                    c1, c2 = st.columns([1, 2])
                    with c1:
                        try:
                            st.image(item['img'], use_container_width=True)
                        except:
                            st.image("https://placehold.co/100")
                    with c2:
                        st.markdown(f"**{name}**")
                        st.caption(f"{item['price']} x {count} = {item_total} บ.")

                    st.write("")
                    b1, b2, b3 = st.columns([1, 1, 1])
                    with b1:
                        if st.button("➖", key=f"dec_{name}", use_container_width=True):
                            for i, x in enumerate(st.session_state.basket):
                                if x['name'] == name:
                                    del st.session_state.basket[i]
                                    break
                            st.rerun()
                    with b2:
                        st.markdown(
                            f"<div style='text-align:center; font-size:20px; font-weight:bold; padding-top:5px;'>{count}</div>",
                            unsafe_allow_html=True)
                    with b3:
                        if st.button("➕", key=f"inc_{name}", use_container_width=True):
                            st.session_state.basket.append(item)
                            st.rerun()

            st.markdown("---")
            st.markdown(f"### 💰 รวมทั้งสิ้น: {total_price} บาท")
            note = st.text_area("📝 หมายเหตุถึงครัว (ไม่ใส่ผัก, เผ็ดน้อย)")

            if st.button("✅ ยืนยันการสั่ง (Confirm)", type="primary", use_container_width=True):
                now_str = get_thai_time().strftime("%d/%m/%Y %H:%M")
                items = ", ".join([f"{name}(x{count})" for name, count in counts.items()])

                status = save_order({"เวลา": now_str, "โต๊ะ": table_no, "ลูกค้า": cust_name, "รายการอาหาร": items,
                                     "ยอดรวม": total_price, "หมายเหตุ": note, "สถานะ": "waiting"})

                body_intro = "🔔 Order เพิ่มเติม" if status == "merged" else "🔔 Order ใหม่"
                body = f"โต๊ะ: {table_no}\nลูกค้า: {cust_name}\nเวลา: {now_str}\n\n{items}\n\nสั่งรอบนี้: {total_price} บาท\nNote: {note}"
                send_email_notification(f"{body_intro}: {table_no}", body)

                st.session_state.basket = []
                st.session_state.page = 'menu'
                st.balloons()
                st.success("ส่งออเดอร์แล้ว!")
                time.sleep(2)
                st.rerun()
        else:
            st.info("ตะกร้ายังว่างอยู่เลย เลือกอาหารก่อนนะครับ")
            if st.button("ไปเลือกอาหาร"):
                st.session_state.page = 'menu'
                st.rerun()