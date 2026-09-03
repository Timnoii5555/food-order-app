"""TimNoi Shabu — order-ahead & kitchen console.

A single-script Streamlit app used two ways:
  * Customers scan a table QR code, browse the menu, and place orders.
  * Staff open the admin panel to run the kitchen queue, sales, menu,
    promotions, tables, contact details, and reviews.

Data lives in plain CSV files next to this script (see the *_CSV constants)
so the app needs no external database. Visual styling comes from
``.streamlit/config.toml`` (brand theme) plus native Streamlit widgets —
see the accompanying README for why almost no custom HTML/CSS is used.
"""

from __future__ import annotations

import base64
import hmac
import os
import random
import re
import smtplib
import time
from collections import Counter
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import pandas as pd
import pytz
import streamlit as st

# ============================================================================
# 1. Page config (must run before any other Streamlit command)
# ============================================================================
_early_mode = st.session_state.get("app_mode", "customer")
st.set_page_config(
    page_title="TimNoi Shabu",
    page_icon="🍲",
    layout="wide" if _early_mode == "admin_dashboard" else "centered",
    menu_items={
        "Get help": None,
        "Report a bug": None,
        "About": "TimNoi Shabu — ระบบสั่งอาหารหน้าร้านและจัดการครัว",
    },
)

# ============================================================================
# 2. Session state
# ============================================================================
_DEFAULT_STATE = {
    "basket": [],
    "page": "menu",
    "app_mode": "customer",
    "my_queue_id": None,
    "user_table": None,
    "user_name": "",
    "details_confirmed": False,
    "last_refresh_timestamp": 0.0,
    "menu_mtime": 0.0,
    "login_phase": 1,
    "login_otp_ref": None,
    "login_otp_expires": None,
    "login_otp_attempts": 0,
    "login_temp_name": "",
    "login_fail_count": 0,
}
for _key, _value in _DEFAULT_STATE.items():
    st.session_state.setdefault(_key, _value)


def clean_text(value, max_len: int = 60) -> str:
    """Strip control characters/whitespace and cap length of user input."""
    if value is None:
        return ""
    value = re.sub(r"[\r\n\t\x00-\x1f]", " ", str(value)).strip()
    return value[:max_len]


# Restore a returning customer's identity from the QR-code URL, if present.
if not st.session_state.user_name and "name" in st.query_params and "table" in st.query_params:
    _name = clean_text(st.query_params.get("name", ""), 40)
    _table = clean_text(st.query_params.get("table", ""), 60)
    if _name and _table:
        st.session_state.user_name = _name
        st.session_state.user_table = _table
        st.session_state.details_confirmed = True

# ============================================================================
# 3. Secrets & constants
# ============================================================================
def _secret(section: str, key: str):
    try:
        return st.secrets[section][key]
    except Exception:
        return None


SENDER_EMAIL = _secret("email", "user")
SENDER_PASSWORD = _secret("email", "password")
ADMIN_PASSWORD = _secret("admin", "password")
RECEIVER_EMAIL = SENDER_EMAIL
EMAIL_READY = bool(SENDER_EMAIL and SENDER_PASSWORD)
ADMIN_READY = bool(ADMIN_PASSWORD)

ORDER_CSV = "order_history.csv"
MENU_CSV = "menu_data.csv"
TABLES_CSV = "tables_data.csv"
CONTACT_CSV = "contact_data.csv"
QUEUE_CSV = "queue_data.csv"
FEEDBACK_CSV = "feedback_data.csv"
LOGIN_LOG_CSV = "login_log.csv"
REFRESH_SIGNAL_FILE = "refresh_signal.txt"
IMAGE_FOLDER = "uploaded_images"
BANNER_FOLDER = "banner_images"
BANNER_COUNT = 5

os.makedirs(IMAGE_FOLDER, exist_ok=True)
os.makedirs(BANNER_FOLDER, exist_ok=True)

KITCHEN_LIMIT = 10
OTP_TTL_SECONDS = 5 * 60
OTP_MAX_ATTEMPTS = 5
ALLOWED_IMAGE_EXT = {"png", "jpg", "jpeg", "webp", "gif"}
PLACEHOLDER_IMG = "https://placehold.co/400x400?text=TimNoi"


# ============================================================================
# 4. Data helpers
# ============================================================================
def get_thai_time():
    return pd.Timestamp.now(pytz.timezone("Asia/Bangkok")).to_pydatetime()


def to_bool(value, default: bool = False) -> bool:
    """Normalize a CSV cell (bool, 'True'/'False', NaN, ...) to a real bool."""
    if isinstance(value, bool):
        return value
    if pd.isna(value):
        return default
    return str(value).strip().lower() not in ("false", "0", "no", "")


def thb(amount) -> str:
    try:
        return f"{float(amount):,.0f} บาท"
    except (TypeError, ValueError):
        return "0 บาท"


def check_system_updates() -> bool:
    """Return True (and update session state) if shared data changed on disk."""
    should_rerun = False
    if os.path.exists(REFRESH_SIGNAL_FILE):
        try:
            with open(REFRESH_SIGNAL_FILE, "r") as f:
                signal_time = float(f.read().strip())
            if signal_time > st.session_state.last_refresh_timestamp:
                st.session_state.last_refresh_timestamp = signal_time
                should_rerun = True
        except (OSError, ValueError):
            pass

    if os.path.exists(MENU_CSV):
        try:
            current_mtime = os.path.getmtime(MENU_CSV)
            if current_mtime > st.session_state.menu_mtime:
                if st.session_state.menu_mtime:  # skip the toast on first load
                    st.toast("เมนูมีการเปลี่ยนแปลง", icon=":material/campaign:")
                st.session_state.menu_mtime = current_mtime
                should_rerun = True
        except OSError:
            pass
    return should_rerun


def trigger_global_refresh() -> None:
    """Nudge every connected browser to pick up new data within a few seconds."""
    try:
        with open(REFRESH_SIGNAL_FILE, "w") as f:
            f.write(str(time.time()))
    except OSError:
        pass


def daily_cleanup() -> None:
    today_str = get_thai_time().strftime("%d/%m/%Y")
    if os.path.exists(ORDER_CSV):
        try:
            df = pd.read_csv(ORDER_CSV)
            if not df.empty and "เวลา" in df.columns and "สถานะ" in df.columns:
                is_stale = (df["สถานะ"] == "waiting") & (
                    df["เวลา"].astype(str).str.split().str[0] != today_str
                )
                if is_stale.any():
                    df.loc[is_stale, "สถานะ"] = "expired"
                    df.to_csv(ORDER_CSV, index=False)
        except (OSError, pd.errors.ParserError):
            pass

    if os.path.exists(QUEUE_CSV):
        try:
            q_df = pd.read_csv(QUEUE_CSV)
            if not q_df.empty:
                q_date_str = str(q_df.iloc[0]["timestamp"]).split()[0]
                today_date_sys = get_thai_time().strftime("%Y-%m-%d")
                if q_date_str != today_date_sys:
                    pd.DataFrame(columns=["queue_id", "customer_name", "timestamp"]).to_csv(
                        QUEUE_CSV, index=False
                    )
        except (OSError, pd.errors.ParserError, IndexError):
            pass


def load_menu() -> pd.DataFrame:
    if not os.path.exists(MENU_CSV):
        default_data = [
            {"name": "หมูหมัก", "price": 120, "img": PLACEHOLDER_IMG,
             "category": "เนื้อสัตว์ (Meat)", "in_stock": True},
            {"name": "ผักรวม", "price": 40, "img": PLACEHOLDER_IMG,
             "category": "ผัก (Veggie)", "in_stock": True},
        ]
        pd.DataFrame(default_data).to_csv(MENU_CSV, index=False)
    try:
        df = pd.read_csv(MENU_CSV)
        for col, default in (("name", ""), ("price", 0), ("img", ""),
                              ("category", "อื่นๆ (Others)"), ("in_stock", True)):
            if col not in df.columns:
                df[col] = default
    except (OSError, pd.errors.ParserError):
        df = pd.DataFrame(columns=["name", "price", "img", "category", "in_stock"])
    df["img"] = df["img"].astype(str)
    df["price"] = pd.to_numeric(df["price"], errors="coerce").fillna(0)
    df["in_stock"] = df["in_stock"].apply(to_bool, default=True)
    return df


def load_tables() -> pd.DataFrame:
    if not os.path.exists(TABLES_CSV):
        default_tables = pd.DataFrame([
            {"table_name": "โต๊ะ 1", "is_shared": False},
            {"table_name": "โต๊ะ 2", "is_shared": False},
            {"table_name": "โต๊ะ 3", "is_shared": False},
            {"table_name": "โต๊ะ 4", "is_shared": False},
            {"table_name": "กลับบ้าน", "is_shared": True},
        ])
        default_tables.to_csv(TABLES_CSV, index=False)
    try:
        df = pd.read_csv(TABLES_CSV)
    except (OSError, pd.errors.ParserError):
        df = pd.DataFrame(columns=["table_name", "is_shared"])
    if "is_shared" not in df.columns:
        df["is_shared"] = False
    df["is_shared"] = df["is_shared"].apply(to_bool, default=False)
    return df


def load_orders() -> pd.DataFrame:
    cols = ["เวลา", "โต๊ะ", "ลูกค้า", "รายการอาหาร", "ยอดรวม", "หมายเหตุ", "สถานะ"]
    if not os.path.exists(ORDER_CSV):
        df = pd.DataFrame(columns=cols)
        df.to_csv(ORDER_CSV, index=False)
        return df
    try:
        return pd.read_csv(ORDER_CSV)
    except (OSError, pd.errors.ParserError):
        return pd.DataFrame(columns=cols)


def load_contacts() -> dict:
    default_contact = {"phone": "0XX-XXX-XXXX", "line": "@timnoishabu", "facebook": "", "instagram": ""}
    if not os.path.exists(CONTACT_CSV):
        pd.DataFrame([default_contact]).to_csv(CONTACT_CSV, index=False)
        return default_contact
    try:
        row = pd.read_csv(CONTACT_CSV).iloc[0].to_dict()
        return {**default_contact, **{k: v for k, v in row.items() if pd.notna(v)}}
    except (OSError, pd.errors.ParserError, IndexError):
        return default_contact


def save_contacts(data: dict) -> None:
    pd.DataFrame([data]).to_csv(CONTACT_CSV, index=False)


def load_queue() -> pd.DataFrame:
    cols = ["queue_id", "customer_name", "timestamp"]
    if not os.path.exists(QUEUE_CSV):
        df = pd.DataFrame(columns=cols)
        df.to_csv(QUEUE_CSV, index=False)
        return df
    try:
        return pd.read_csv(QUEUE_CSV)
    except (OSError, pd.errors.ParserError):
        return pd.DataFrame(columns=cols)


def add_to_queue(name: str):
    df = load_queue()
    if not df.empty and name in df["customer_name"].values:
        existing_id = df[df["customer_name"] == name].iloc[0]["queue_id"]
        return existing_id, True
    last_id = 100
    if not df.empty:
        for raw in reversed(df["queue_id"].astype(str).tolist()):
            if "-" in raw and raw.split("-")[1].isdigit():
                last_id = int(raw.split("-")[1])
                break
    new_id = f"Q-{last_id + 1}"
    new_row = {"queue_id": new_id, "customer_name": name,
               "timestamp": datetime_now_str()}
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    df.to_csv(QUEUE_CSV, index=False)
    trigger_global_refresh()
    return new_id, False


def datetime_now_str() -> str:
    return get_thai_time().strftime("%Y-%m-%d %H:%M:%S")


def pop_queue() -> None:
    df = load_queue()
    if not df.empty:
        df.iloc[1:].to_csv(QUEUE_CSV, index=False)
        trigger_global_refresh()


def load_feedback() -> pd.DataFrame:
    cols = ["timestamp", "customer_name", "message"]
    if not os.path.exists(FEEDBACK_CSV):
        df = pd.DataFrame(columns=cols)
        df.to_csv(FEEDBACK_CSV, index=False)
        return df
    try:
        return pd.read_csv(FEEDBACK_CSV)
    except (OSError, pd.errors.ParserError):
        return pd.DataFrame(columns=cols)


def save_feedback_entry(name: str, message: str) -> None:
    df = load_feedback()
    new_entry = {"timestamp": get_thai_time().strftime("%d/%m/%Y %H:%M"),
                 "customer_name": name, "message": message}
    df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
    df.to_csv(FEEDBACK_CSV, index=False)


def delete_feedback_entry(index) -> None:
    df = load_feedback()
    try:
        df.drop(index).to_csv(FEEDBACK_CSV, index=False)
    except KeyError:
        pass


def load_login_log() -> pd.DataFrame:
    cols = ["timestamp", "declared_name", "status"]
    if not os.path.exists(LOGIN_LOG_CSV):
        df = pd.DataFrame(columns=cols)
        df.to_csv(LOGIN_LOG_CSV, index=False)
        return df
    try:
        return pd.read_csv(LOGIN_LOG_CSV)
    except (OSError, pd.errors.ParserError):
        return pd.DataFrame(columns=cols)


def save_login_log(declared_name: str, status: str = "Success") -> None:
    df = load_login_log()
    new_entry = {"timestamp": get_thai_time().strftime("%d/%m/%Y %H:%M:%S"),
                 "declared_name": declared_name or "ไม่ระบุชื่อ", "status": status}
    df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
    df.to_csv(LOGIN_LOG_CSV, index=False)


def save_image(uploaded_file) -> str | None:
    if uploaded_file is None:
        return None
    ext = uploaded_file.name.rsplit(".", 1)[-1].lower() if "." in uploaded_file.name else ""
    if ext not in ALLOWED_IMAGE_EXT:
        ext = "png"
    new_filename = f"img_{int(time.time() * 1000)}.{ext}"
    file_path = os.path.join(IMAGE_FOLDER, new_filename)
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return file_path


def get_image_base64(path: str) -> str:
    if not os.path.exists(path):
        return ""
    ext = path.rsplit(".", 1)[-1].lower() if "." in path else "png"
    mime = "jpeg" if ext == "jpg" else (ext if ext in ALLOWED_IMAGE_EXT else "png")
    with open(path, "rb") as image_file:
        encoded = base64.b64encode(image_file.read()).decode()
    return f"data:image/{mime};base64,{encoded}"


def resolve_img_src(path) -> str:
    """Turn a menu/banner 'img' cell into something st.image can render."""
    path = str(path or "").strip()
    if path.startswith("http://") or path.startswith("https://"):
        return path
    if path and os.path.exists(path):
        return get_image_base64(path) or PLACEHOLDER_IMG
    return PLACEHOLDER_IMG


def find_banner_path(index: int) -> str | None:
    for ext in ALLOWED_IMAGE_EXT:
        candidate = os.path.join(BANNER_FOLDER, f"banner_{index}.{ext}")
        if os.path.exists(candidate):
            return candidate
    return None


def save_promo_banner(uploaded_file, index: int) -> bool:
    if uploaded_file is None:
        return False
    ext = uploaded_file.name.rsplit(".", 1)[-1].lower() if "." in uploaded_file.name else ""
    if ext not in ALLOWED_IMAGE_EXT:
        ext = "png"
    existing = find_banner_path(index)
    if existing:
        os.remove(existing)
    filepath = os.path.join(BANNER_FOLDER, f"banner_{index}.{ext}")
    with open(filepath, "wb") as f:
        f.write(uploaded_file.getbuffer())
    trigger_global_refresh()
    return True


def send_email_notification(subject: str, body: str) -> bool:
    """Best-effort email send. Returns False (and logs to console) on failure
    instead of raising, so a flaky mail server never breaks the app for a
    customer placing an order."""
    if not EMAIL_READY:
        print(f"[email skipped — not configured] {subject}")
        return False
    msg = MIMEMultipart()
    msg["From"] = SENDER_EMAIL
    msg["To"] = RECEIVER_EMAIL
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))
    try:
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=10) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_string())
        return True
    except Exception as e:  # noqa: BLE001 — genuinely want to swallow any SMTP failure
        print(f"[email failed] {subject}: {e}")
        return False


def save_order(data: dict) -> str:
    df = load_orders()
    mask = (df["โต๊ะ"] == data["โต๊ะ"]) & (df["สถานะ"] == "waiting")
    if mask.any():
        i = df.index[mask][0]
        df.at[i, "รายการอาหาร"] = f"{df.at[i, 'รายการอาหาร']}, {data['รายการอาหาร']}"
        df.at[i, "ยอดรวม"] = float(df.at[i, "ยอดรวม"]) + float(data["ยอดรวม"])
        old_note = str(df.at[i, "หมายเหตุ"])
        old_note = "" if old_note == "nan" else old_note
        df.at[i, "หมายเหตุ"] = f"{old_note} | {data['หมายเหตุ']}" if data["หมายเหตุ"] else old_note
        df.at[i, "เวลา"] = data["เวลา"]
        df.to_csv(ORDER_CSV, index=False)
        status_result = "merged"
    else:
        cols = ["เวลา", "โต๊ะ", "ลูกค้า", "รายการอาหาร", "ยอดรวม", "หมายเหตุ", "สถานะ"]
        df_new = pd.DataFrame([data])[cols]
        if not os.path.exists(ORDER_CSV):
            df_new.to_csv(ORDER_CSV, index=False)
        else:
            df_new.to_csv(ORDER_CSV, mode="a", header=False, index=False)
        status_result = "new"

    if st.session_state.get("my_queue_id"):
        queue_df = load_queue()
        if not queue_df.empty and queue_df.iloc[0]["queue_id"] == st.session_state.my_queue_id:
            pop_queue()
            st.session_state.my_queue_id = None

    trigger_global_refresh()
    return status_result


def sanitize_link(link) -> str:
    link = str(link or "").strip()
    if not link:
        return ""
    if link.startswith("http://") or link.startswith("https://"):
        return link
    return "https://" + link


# ============================================================================
# 5. Shared data load + live-refresh watcher
# ============================================================================
daily_cleanup()

menu_df = load_menu()
tables_df = load_tables()
orders_df = load_orders()
contact_info = load_contacts()
queue_df = load_queue()
feedback_df = load_feedback()

waiting_orders = orders_df[orders_df["สถานะ"] == "waiting"]
busy_tables = {str(t) for t in waiting_orders["โต๊ะ"].unique().tolist()}
shared_tables = {str(t) for t in tables_df.loc[tables_df["is_shared"], "table_name"].tolist()}
kitchen_load = len(waiting_orders)

is_queue_mode = kitchen_load >= KITCHEN_LIMIT
can_order = not is_queue_mode
waiting_q_count = 0

if not queue_df.empty and st.session_state.my_queue_id:
    ids = queue_df["queue_id"].tolist()
    if st.session_state.my_queue_id in ids:
        waiting_q_count = ids.index(st.session_state.my_queue_id)
        if waiting_q_count == 0:
            can_order = kitchen_load < KITCHEN_LIMIT
            is_queue_mode = not can_order
        else:
            can_order, is_queue_mode = False, True
    else:
        # Our ticket is gone (served or the day rolled over) — drop it.
        st.session_state.my_queue_id = None


@st.fragment(run_every="4s")
def live_refresh_watcher():
    """Silently poll for menu/order changes and reload the whole app so every
    open browser tab (customers + kitchen) stays in sync without a manual
    refresh click."""
    if check_system_updates():
        st.rerun()


live_refresh_watcher()

# ============================================================================
# 6. Header
# ============================================================================
if os.path.exists("logo.png"):
    st.logo("logo.png", size="large")

header_logo, header_name, header_menu = st.columns([1.1, 2.3, 0.7], vertical_alignment="center")
with header_logo:
    if os.path.exists("logo.png"):
        st.image("logo.png", width="stretch")
    else:
        st.markdown("# 🍲")
with header_name:
    st.title("TimNoi Shabu", text_alignment="left")
    st.caption("ร้านนี้ไม่มีหมูเพราะที่เห็นเป็นเนื้อหมา")
    with st.container(horizontal=True):
        st.caption("🕒 เปิดบริการ 00:00 – 23:59 น.")
        st.caption(f"📞 {contact_info.get('phone', '-')}")
with header_menu:
    with st.popover("เมนู", icon=":material/menu:", width="stretch"):
        st.markdown("**เมนูหลัก**")
        if st.button("หน้าลูกค้า", icon=":material/storefront:", width="stretch"):
            st.session_state.app_mode = "customer"
            st.session_state.page = "menu"
            st.rerun()
        if st.button("เขียนติชม / สมุดเยี่ยม", icon=":material/rate_review:", width="stretch"):
            st.session_state.app_mode = "customer"
            st.session_state.page = "feedback"
            st.rerun()
        if st.button("จัดการร้าน (Admin)", icon=":material/admin_panel_settings:", width="stretch"):
            st.session_state.app_mode = "admin_login"
            st.session_state.login_phase = 1
            st.rerun()
        if st.button("รีเฟรชหน้านี้", icon=":material/refresh:", width="stretch"):
            st.rerun()
        st.markdown("---")
        st.markdown("**ช่องทางติดต่อ**")
        fb_url = sanitize_link(contact_info.get("facebook", ""))
        ig_url = sanitize_link(contact_info.get("instagram", ""))
        if fb_url:
            st.link_button("Facebook", fb_url, icon=":material/open_in_new:", width="stretch")
        if ig_url:
            st.link_button("Instagram", ig_url, icon=":material/open_in_new:", width="stretch")
        st.caption(f"LINE: {contact_info.get('line', '-')}")

st.divider()

# ============================================================================
# 7. Admin — login
# ============================================================================
if st.session_state.app_mode == "admin_login":
    st.subheader("เข้าสู่ระบบหลังร้าน", anchor=False, icon=":material/lock:")
    if st.button("กลับ", icon=":material/arrow_back:"):
        st.session_state.app_mode = "customer"
        st.rerun()

    if not ADMIN_READY:
        st.error(
            "ยังไม่ได้ตั้งค่ารหัสผ่านแอดมิน กรุณาสร้างไฟล์ .streamlit/secrets.toml "
            "จากตัวอย่างใน .streamlit/secrets.toml.example",
            icon=":material/error:",
        )
        st.stop()
    if not EMAIL_READY:
        st.warning(
            "ยังไม่ได้ตั้งค่าอีเมลระบบใน .streamlit/secrets.toml ระบบจะไม่สามารถส่งรหัส OTP "
            "ยืนยันตัวตนได้ จึงปิดการเข้าสู่ระบบแอดมินไว้ก่อนเพื่อความปลอดภัย",
            icon=":material/mail:",
        )
        st.stop()

    if st.session_state.login_phase == 1:
        with st.container(border=True):
            st.caption("ขั้นตอนที่ 1 จาก 2 — ยืนยันรหัสผ่าน")
            admin_device = st.text_input("ผู้ใช้งาน (ชื่อเล่น)", placeholder="ระบุชื่อผู้ใช้งาน...")
            password_input = st.text_input("รหัสผ่าน", type="password")

        if st.button("ขอเข้าสู่ระบบ", type="primary", icon=":material/login:"):
            if not password_input:
                st.error("กรุณาใส่รหัสผ่าน")
            elif hmac.compare_digest(password_input, ADMIN_PASSWORD):
                st.session_state.login_fail_count = 0
                otp_code = str(random.randint(100000, 999999))
                declared_name = admin_device if admin_device else "ไม่ระบุชื่อ"
                thai_now = get_thai_time().strftime("%d/%m/%Y %H:%M:%S")

                st.session_state.login_otp_ref = otp_code
                st.session_state.login_otp_expires = time.time() + OTP_TTL_SECONDS
                st.session_state.login_otp_attempts = 0
                st.session_state.login_temp_name = declared_name

                sent = send_email_notification(
                    f"คำขอเข้าใช้งาน Admin: {declared_name}",
                    f"OTP: {otp_code}\nUser: {declared_name}\nTime: {thai_now}",
                )
                if sent:
                    st.session_state.login_phase = 2
                    st.rerun()
                else:
                    st.error("ส่ง OTP ไม่สำเร็จ กรุณาลองใหม่อีกครั้ง", icon=":material/error:")
            else:
                st.session_state.login_fail_count += 1
                st.error("รหัสผ่านผิด", icon=":material/error:")
                save_login_log(admin_device, "Failed (Wrong Pass)")
                time.sleep(min(st.session_state.login_fail_count, 5))

    elif st.session_state.login_phase == 2:
        with st.container(border=True):
            st.caption("ขั้นตอนที่ 2 จาก 2 — ยืนยัน OTP")
            st.write(f"ส่งรหัส OTP ไปยังอีเมลเจ้าของร้านแล้ว สำหรับผู้ขอเข้าใช้: "
                     f"**{st.session_state.login_temp_name}**")
            remaining = max(0, int(st.session_state.login_otp_expires - time.time()))
            st.caption(f"รหัสจะหมดอายุใน {remaining // 60} นาที {remaining % 60} วินาที")
            otp_input = st.text_input("รหัส OTP 6 หลัก", max_chars=6)
            with st.container(horizontal=True):
                confirm = st.button("ยืนยัน", type="primary", icon=":material/check:", width="stretch")
                cancel = st.button("ยกเลิก", icon=":material/close:", width="stretch")

            if cancel:
                st.session_state.login_phase = 1
                st.rerun()

            if confirm:
                if time.time() > st.session_state.login_otp_expires:
                    st.error("OTP หมดอายุแล้ว กรุณาขอรหัสใหม่", icon=":material/schedule:")
                    st.session_state.login_phase = 1
                elif st.session_state.login_otp_attempts >= OTP_MAX_ATTEMPTS:
                    st.error("กรอกผิดเกินจำนวนที่กำหนด กรุณาขอรหัสใหม่", icon=":material/block:")
                    save_login_log(st.session_state.login_temp_name, "Failed (OTP Locked)")
                    st.session_state.login_phase = 1
                elif otp_input and hmac.compare_digest(otp_input, st.session_state.login_otp_ref):
                    save_login_log(st.session_state.login_temp_name, "Success (OTP Verified)")
                    st.success("สำเร็จ", icon=":material/check_circle:")
                    time.sleep(0.8)
                    st.session_state.app_mode = "admin_dashboard"
                    st.session_state.login_phase = 1
                    st.rerun()
                else:
                    st.session_state.login_otp_attempts += 1
                    left = OTP_MAX_ATTEMPTS - st.session_state.login_otp_attempts
                    st.error(f"OTP ไม่ถูกต้อง (เหลือ {left} ครั้ง)", icon=":material/error:")

# ============================================================================
# 8. Admin — dashboard
# ============================================================================
elif st.session_state.app_mode == "admin_dashboard":
    st.subheader("จัดการร้าน", anchor=False, icon=":material/settings:")
    with st.container(horizontal=True):
        if st.button("ออกจากระบบ", icon=":material/logout:"):
            st.session_state.app_mode = "customer"
            st.rerun()
        if st.button("รีเฟรชทุกอุปกรณ์", type="primary", icon=":material/sync:"):
            trigger_global_refresh()
            st.toast("ส่งคำสั่งรีเฟรชแล้ว", icon=":material/sync:")

    tab_kitchen, tab_promo, tab_stock, tab_menu, tab_sales, tab_contact, tab_reviews, tab_log = st.tabs(
        ["ครัว", "โปรโมชั่น", "สต็อก/โต๊ะ", "เมนู", "ยอดขาย", "ติดต่อ", "รีวิว", "ประวัติล็อกอิน"],
    )

    # ---- ครัว -------------------------------------------------------------
    with tab_kitchen:
        @st.dialog("ยกเลิกออเดอร์นี้?")
        def confirm_cancel_order(order_index, table_name):
            st.write(f"ยืนยันยกเลิกออเดอร์ของ **{table_name}** ใช่หรือไม่? การกระทำนี้ย้อนกลับไม่ได้")
            with st.container(horizontal=True):
                if st.button("ยกเลิกออเดอร์", type="primary", icon=":material/delete:"):
                    fresh = load_orders()
                    fresh.at[order_index, "สถานะ"] = "cancelled"
                    fresh.to_csv(ORDER_CSV, index=False)
                    trigger_global_refresh()
                    st.toast("ยกเลิกออเดอร์แล้ว", icon=":material/delete:")
                    st.rerun()
                if st.button("ปิด"):
                    st.rerun()

        @st.fragment(run_every="5s")
        def kitchen_board():
            live_orders = load_orders()
            live_waiting = live_orders[live_orders["สถานะ"] == "waiting"]
            load_now = len(live_waiting)

            with st.container(horizontal=True):
                st.metric("ออเดอร์ค้าง", f"{load_now}/{KITCHEN_LIMIT}", border=True)
                st.metric("สถานะครัว", "แน่น" if load_now >= KITCHEN_LIMIT else "ปกติ", border=True)
            st.progress(min(load_now / KITCHEN_LIMIT, 1.0))

            if load_now == 0:
                st.success("ไม่มีออเดอร์ค้าง", icon=":material/check_circle:")
                return

            for index, row in live_waiting.iterrows():
                with st.container(border=True):
                    c1, c2 = st.columns([3, 1])
                    with c1:
                        st.markdown(f"**{row['โต๊ะ']}** · {row['เวลา']}")
                        st.caption(f"ลูกค้า: {row['ลูกค้า']}")
                        st.write(thb(row["ยอดรวม"]))
                        with st.expander("รายการอาหาร", icon=":material/list_alt:"):
                            st.code(str(row["รายการอาหาร"]), language="text")
                        note = str(row["หมายเหตุ"])
                        if note not in ("nan", ""):
                            st.warning(note, icon=":material/sticky_note_2:")
                    with c2:
                        if st.button("รับเงิน", key=f"pay_{index}", type="primary",
                                      icon=":material/payments:", width="stretch"):
                            fresh = load_orders()
                            fresh.at[index, "สถานะ"] = "paid"
                            fresh.to_csv(ORDER_CSV, index=False)
                            trigger_global_refresh()
                            st.toast("รับเงินเรียบร้อย", icon=":material/check_circle:")
                            st.rerun(scope="fragment")
                        if st.button("ยกเลิก", key=f"cncl_{index}", icon=":material/cancel:",
                                      width="stretch"):
                            confirm_cancel_order(index, row["โต๊ะ"])

        kitchen_board()

    # ---- โปรโมชั่น ----------------------------------------------------------
    with tab_promo:
        st.write("อัปโหลดรูปแบนเนอร์โปรโมชั่น (สูงสุด 5 รูป) ระบบจะสลับแสดงให้ลูกค้าเห็นอัตโนมัติ")

        @st.dialog("ลบแบนเนอร์นี้?")
        def confirm_delete_banner(path):
            st.write("ยืนยันลบรูปแบนเนอร์นี้ใช่หรือไม่?")
            with st.container(horizontal=True):
                if st.button("ลบ", type="primary", icon=":material/delete:"):
                    os.remove(path)
                    trigger_global_refresh()
                    st.rerun()
                if st.button("ปิด"):
                    st.rerun()

        for i in range(1, BANNER_COUNT + 1):
            c1, c2 = st.columns([2, 1])
            with c1:
                uploaded = st.file_uploader(f"รูปที่ {i}", type=sorted(ALLOWED_IMAGE_EXT), key=f"ban_up_{i}")
                if uploaded and save_promo_banner(uploaded, i):
                    st.rerun()
            with c2:
                fp = find_banner_path(i)
                if fp:
                    st.image(fp, width="stretch")
                    if st.button("ลบ", key=f"del_ban_{i}", icon=":material/delete:"):
                        confirm_delete_banner(fp)

    # ---- สต็อก/โต๊ะ ---------------------------------------------------------
    with tab_stock:
        st.write("#### สต็อกสินค้า")
        edited = st.data_editor(
            menu_df[["name", "category", "price", "in_stock"]],
            disabled=["name", "category", "price"],
            hide_index=True,
            column_config={
                "name": "เมนู",
                "category": "หมวดหมู่",
                "price": st.column_config.NumberColumn("ราคา", format="%d ฿"),
                "in_stock": st.column_config.CheckboxColumn("มีสินค้า"),
            },
        )
        if st.button("บันทึกสต็อก", icon=":material/save:"):
            fresh = load_menu()
            fresh["in_stock"] = edited["in_stock"].values
            fresh.to_csv(MENU_CSV, index=False)
            st.toast("บันทึกสต็อกแล้ว", icon=":material/check_circle:")

        st.write("#### จัดการโต๊ะ")
        with st.form("add_tbl", border=False):
            new_t = st.text_input("ชื่อโต๊ะใหม่")
            is_shared_new = st.checkbox("โต๊ะนี้ไม่จำกัดจำนวนคนพร้อมกัน (เช่น กลับบ้าน/ซื้อกลับ)")
            if st.form_submit_button("เพิ่มโต๊ะ", icon=":material/add:"):
                new_t = clean_text(new_t, 40)
                if new_t and new_t not in tables_df["table_name"].astype(str).tolist():
                    new_row = pd.DataFrame([{"table_name": new_t, "is_shared": is_shared_new}])
                    pd.concat([tables_df, new_row], ignore_index=True).to_csv(TABLES_CSV, index=False)
                    trigger_global_refresh()
                    st.rerun()
                else:
                    st.error("กรุณาใส่ชื่อโต๊ะที่ยังไม่มีอยู่")

        @st.dialog("ลบโต๊ะนี้?")
        def confirm_delete_table(table_name):
            st.write(f"ยืนยันลบ **{table_name}** ใช่หรือไม่?")
            if table_name in busy_tables:
                st.warning("โต๊ะนี้กำลังมีออเดอร์ค้างอยู่ — ลบแล้วออเดอร์เดิมจะยังอยู่ในระบบแต่โต๊ะจะหายจากรายการ",
                           icon=":material/warning:")
            with st.container(horizontal=True):
                if st.button("ลบโต๊ะ", type="primary", icon=":material/delete:"):
                    fresh = load_tables()
                    fresh[fresh["table_name"] != table_name].to_csv(TABLES_CSV, index=False)
                    trigger_global_refresh()
                    st.rerun()
                if st.button("ปิด"):
                    st.rerun()

        del_t = st.selectbox("เลือกโต๊ะที่ต้องการลบ", ["-"] + tables_df["table_name"].tolist())
        if st.button("ลบโต๊ะ", icon=":material/delete:") and del_t != "-":
            confirm_delete_table(del_t)

    # ---- เมนู ---------------------------------------------------------------
    with tab_menu:
        st.write("#### เพิ่มเมนูใหม่")
        with st.form("add_m", border=False):
            n = st.text_input("ชื่อเมนู")
            p = st.number_input("ราคา", min_value=0, step=5)
            c = st.selectbox("หมวดหมู่", ["เนื้อสัตว์ (Meat)", "อาหารทะเล (Seafood)", "ผัก (Veggie)",
                                          "ของทานเล่น (Snack)", "เครื่องดื่ม (Drinks)", "อื่นๆ (Others)"])
            up_file = st.file_uploader("อัปโหลดรูป", type=sorted(ALLOWED_IMAGE_EXT))
            url_img = st.text_input("หรือใส่ URL รูปภาพ", PLACEHOLDER_IMG)
            if st.form_submit_button("บันทึกเมนู", icon=":material/save:"):
                n = clean_text(n, 60)
                if n:
                    final_path = save_image(up_file) if up_file else url_img
                    new_m = pd.DataFrame([{"name": n, "price": p, "img": final_path,
                                            "category": c, "in_stock": True}])
                    pd.concat([load_menu(), new_m], ignore_index=True).to_csv(MENU_CSV, index=False)
                    st.rerun()
                else:
                    st.error("กรุณาใส่ชื่อเมนู")

        st.write("#### ลบเมนู")
        menu_names = menu_df["name"].tolist()
        dupes = [n for n, count in Counter(menu_names).items() if count > 1]

        @st.dialog("ลบเมนูนี้?")
        def confirm_delete_menu(item_name, has_dupe):
            st.write(f"ยืนยันลบ **{item_name}** ใช่หรือไม่?")
            if has_dupe:
                st.warning("มีเมนูชื่อนี้มากกว่า 1 รายการ — จะลบทั้งหมดที่ชื่อตรงกัน", icon=":material/warning:")
            with st.container(horizontal=True):
                if st.button("ลบเมนู", type="primary", icon=":material/delete:"):
                    fresh = load_menu()
                    fresh[fresh["name"] != item_name].to_csv(MENU_CSV, index=False)
                    st.rerun()
                if st.button("ปิด"):
                    st.rerun()

        del_m = st.selectbox("เลือกเมนู", ["-"] + menu_names)
        if st.button("ลบเมนู", icon=":material/delete:") and del_m != "-":
            confirm_delete_menu(del_m, del_m in dupes)

    # ---- ยอดขาย -------------------------------------------------------------
    with tab_sales:
        today_date = get_thai_time().date()
        orders_df["ยอดรวม"] = pd.to_numeric(orders_df["ยอดรวม"], errors="coerce").fillna(0)
        paid = orders_df[orders_df["สถานะ"] == "paid"].copy()
        paid["_dt"] = pd.to_datetime(paid["เวลา"], format="%d/%m/%Y %H:%M", errors="coerce")
        daily = paid[paid["_dt"].dt.date == today_date]

        with st.container(horizontal=True):
            st.metric("ยอดขายวันนี้", thb(daily["ยอดรวม"].sum()), border=True)
            st.metric("จำนวนออเดอร์วันนี้", len(daily), border=True)
            avg = daily["ยอดรวม"].mean() if len(daily) else 0
            st.metric("ยอดเฉลี่ย/ออเดอร์", thb(avg), border=True)

        st.caption(f"วันที่ {today_date.strftime('%d/%m/%Y')}")
        st.dataframe(daily[["เวลา", "โต๊ะ", "ลูกค้า", "ยอดรวม"]], hide_index=True, width="stretch")

        last7 = pd.date_range(end=today_date, periods=7).date
        trend = paid.dropna(subset=["_dt"]).groupby(paid["_dt"].dt.date)["ยอดรวม"].sum()
        trend = trend.reindex(last7, fill_value=0)
        trend_df = pd.DataFrame({"วันที่": [d.strftime("%d/%m") for d in last7],
                                  "ยอดขาย": trend.values.astype(int)})
        st.write("#### ยอดขายย้อนหลัง 7 วัน")
        st.bar_chart(trend_df, x="วันที่", y="ยอดขาย")

    # ---- ติดต่อ -------------------------------------------------------------
    with tab_contact:
        st.subheader("ข้อมูลติดต่อ", anchor=False, icon=":material/contact_phone:")
        with st.form("contact", border=False):
            np_ = st.text_input("เบอร์โทร", contact_info.get("phone", ""))
            nl = st.text_input("LINE", contact_info.get("line", ""))
            nf = st.text_input("Facebook URL", contact_info.get("facebook", ""))
            ni = st.text_input("Instagram URL", contact_info.get("instagram", ""))
            if st.form_submit_button("บันทึก", icon=":material/save:"):
                save_contacts({"phone": clean_text(np_, 30), "line": clean_text(nl, 40),
                                "facebook": clean_text(nf, 200), "instagram": clean_text(ni, 200)})
                trigger_global_refresh()
                st.toast("บันทึกข้อมูลติดต่อแล้ว", icon=":material/check_circle:")
                st.rerun()

    # ---- รีวิว --------------------------------------------------------------
    with tab_reviews:
        st.subheader("ความคิดเห็นจากลูกค้า", anchor=False, icon=":material/rate_review:")

        @st.dialog("ลบความคิดเห็นนี้?")
        def confirm_delete_feedback(idx):
            st.write("ยืนยันลบความคิดเห็นนี้ใช่หรือไม่?")
            with st.container(horizontal=True):
                if st.button("ลบ", type="primary", icon=":material/delete:"):
                    delete_feedback_entry(idx)
                    st.rerun()
                if st.button("ปิด"):
                    st.rerun()

        if feedback_df.empty:
            st.caption("ยังไม่มีความคิดเห็น")
        for i, r in feedback_df[::-1].iterrows():
            with st.container(border=True):
                st.markdown(f"**{r['customer_name']}** · {r.get('timestamp', '')}")
                st.write(r["message"])
                if st.button("ลบ", key=f"dfb_{i}", icon=":material/delete:"):
                    confirm_delete_feedback(i)

    # ---- ประวัติล็อกอิน -------------------------------------------------------
    with tab_log:
        st.subheader("ประวัติการเข้าสู่ระบบ", anchor=False, icon=":material/history:")
        st.dataframe(load_login_log()[::-1], hide_index=True, width="stretch")

        @st.dialog("ล้างประวัติล็อกอินทั้งหมด?")
        def confirm_clear_log():
            st.write("ยืนยันล้างประวัติการเข้าสู่ระบบทั้งหมดใช่หรือไม่? การกระทำนี้ย้อนกลับไม่ได้")
            with st.container(horizontal=True):
                if st.button("ล้างประวัติ", type="primary", icon=":material/delete_forever:"):
                    pd.DataFrame(columns=["timestamp", "declared_name", "status"]).to_csv(
                        LOGIN_LOG_CSV, index=False
                    )
                    st.rerun()
                if st.button("ปิด"):
                    st.rerun()

        if st.button("ล้างประวัติ", icon=":material/delete_forever:"):
            confirm_clear_log()

# ============================================================================
# 9. Customer — identity screen
# ============================================================================
else:
    if not st.session_state.details_confirmed:
        st.header("ยินดีต้อนรับ", anchor=False, icon=":material/waving_hand:")
        with st.container(border=True):
            c_name_input = st.text_input("ชื่อลูกค้า (ชื่อเล่น)", value=st.session_state.user_name)

            existing_table = None
            is_returning = False
            if c_name_input:
                lookup = orders_df.copy()
                lookup["ลูกค้า"] = lookup["ลูกค้า"].astype(str)
                match = lookup[(lookup["ลูกค้า"] == c_name_input) & (lookup["สถานะ"] == "waiting")]
                if not match.empty:
                    existing_table = str(match.iloc[0]["โต๊ะ"])
                    is_returning = True
                    st.success(f"พบรายการสั่งค้างของ **{c_name_input}**", icon=":material/celebration:")
                    st.caption(f"ระบบเลือกโต๊ะ **{existing_table}** ให้อัตโนมัติ")

            table_input = None
            if is_returning:
                table_input = existing_table
                st.selectbox("โต๊ะของคุณ", [existing_table], disabled=True)
                if st.button("ไม่ใช่ฉัน / เปลี่ยนชื่อใหม่"):
                    st.session_state.user_name = ""
                    st.rerun()
            else:
                all_tables = tables_df["table_name"].astype(str).tolist()
                current_table = str(st.session_state.user_table)
                avail = [t for t in all_tables
                         if t in shared_tables or t not in busy_tables or t == current_table]
                if avail:
                    curr = avail.index(current_table) if current_table in avail else 0
                    table_input = st.selectbox("เลือกโต๊ะ", avail, index=curr)
                else:
                    st.warning("ตอนนี้โต๊ะเต็มทุกโต๊ะ กรุณารอสักครู่ หรือรับบัตรคิวด้านล่าง",
                               icon=":material/event_busy:")

            if st.button("ยืนยัน", type="primary", icon=":material/check:", width="stretch"):
                clean_name = clean_text(c_name_input, 40)
                if not clean_name or not table_input:
                    st.error("กรุณาระบุชื่อและเลือกโต๊ะให้ครบ")
                else:
                    st.session_state.user_name = clean_name
                    st.session_state.user_table = table_input
                    st.session_state.details_confirmed = True
                    st.query_params["name"] = clean_name
                    st.query_params["table"] = table_input
                    st.rerun()

        if is_queue_mode:
            st.warning(f"ครัวแน่น ({kitchen_load} ออเดอร์ในคิว)", icon=":material/warning:")
            q_name = st.text_input("จองคิว (ชื่อ)", key="q_name_precheck")
            if st.button("รับบัตรคิว", icon=":material/confirmation_number:"):
                q_name = clean_text(q_name, 40)
                if q_name:
                    qid, _ = add_to_queue(q_name)
                    st.session_state.my_queue_id = qid
                    st.success(f"บัตรคิวของคุณคือ {qid}")
                else:
                    st.error("กรุณาใส่ชื่อ")
        st.stop()

    # ========================================================================
    # 10. Customer — logged in
    # ========================================================================
    with st.container(horizontal=True, horizontal_alignment="distribute", border=True):
        st.write(f":material/person: **{st.session_state.user_name}**  ·  "
                 f":material/table_restaurant: **{st.session_state.user_table}**")
        if st.button("เปลี่ยนชื่อ/โต๊ะ", icon=":material/edit:"):
            st.session_state.details_confirmed = False
            st.query_params.clear()
            st.rerun()

    banner_paths = [p for i in range(1, BANNER_COUNT + 1) if (p := find_banner_path(i))]
    if banner_paths:
        @st.fragment(run_every="4s")
        def promo_banner(paths):
            idx = int(time.time() // 4) % len(paths)
            st.image(resolve_img_src(paths[idx]), width="stretch")
            if len(paths) > 1:
                dots = " ".join("●" if i == idx else "○" for i in range(len(paths)))
                st.caption(dots, text_alignment="center")

        promo_banner(banner_paths)

    # Queue gate ---------------------------------------------------------
    if is_queue_mode:
        if st.session_state.my_queue_id:
            if can_order:
                st.success("ถึงคิวของคุณแล้ว สั่งอาหารได้เลย", icon=":material/check_circle:")
            else:
                with st.container(border=True, horizontal_alignment="center"):
                    st.metric("บัตรคิวของคุณ", st.session_state.my_queue_id)
                    st.caption(f"เหลืออีก {waiting_q_count} คิวก่อนถึงคุณ")
                if st.button("เช็คสถานะคิว", icon=":material/refresh:"):
                    st.rerun()
                st.stop()
        else:
            st.warning("ครัวแน่น กรุณารับบัตรคิวก่อนสั่งอาหาร", icon=":material/warning:")
            qn = st.text_input("ชื่อสำหรับจองคิว")
            if st.button("รับบัตรคิว", icon=":material/confirmation_number:"):
                qn = clean_text(qn, 40)
                if qn:
                    qid, _ = add_to_queue(qn)
                    st.session_state.my_queue_id = qid
                    st.rerun()
                else:
                    st.error("กรุณาใส่ชื่อ")
            st.stop()

    # Kitchen status -------------------------------------------------------
    if not waiting_orders.empty:
        with st.status(f"กำลังปรุง: {waiting_orders.iloc[0]['โต๊ะ']}", state="running"):
            st.caption(f"คิวในครัวตอนนี้ {kitchen_load} ออเดอร์")
    else:
        with st.status("ครัวว่าง พร้อมรับออเดอร์", state="complete"):
            pass

    # Page content -----------------------------------------------------------
    if st.session_state.page == "feedback":
        if st.button("กลับ", icon=":material/arrow_back:"):
            st.session_state.page = "menu"
            st.rerun()
        st.subheader("เขียนติชม", anchor=False, icon=":material/rate_review:")
        with st.form("fb", border=False):
            m = st.text_area("ข้อความถึงร้าน", max_chars=500)
            if st.form_submit_button("ส่ง", icon=":material/send:"):
                m = clean_text(m, 500)
                if m:
                    save_feedback_entry(st.session_state.user_name, m)
                    st.success("ขอบคุณสำหรับความคิดเห็นครับ", icon=":material/check_circle:")
                    time.sleep(1)
                    st.session_state.page = "menu"
                    st.rerun()
                else:
                    st.error("กรุณาพิมพ์ข้อความก่อนส่ง")

    elif st.session_state.page == "menu":
        st.subheader("เมนู", anchor=False, icon=":material/menu_book:")
        categories = [c for c in menu_df["category"].dropna().unique().tolist() if str(c).strip()]
        if categories:
            tabs = st.tabs(categories)
            for tab, cat in zip(tabs, categories):
                with tab:
                    items = menu_df[menu_df["category"] == cat]
                    cols = st.columns(2)
                    for n, (idx, row) in enumerate(items.iterrows()):
                        with cols[n % 2]:
                            with st.container(border=True):
                                st.image(resolve_img_src(row["img"]), width="stretch")
                                st.markdown(f"**{row['name']}**")
                                if row["in_stock"]:
                                    st.caption(thb(row["price"]))
                                    if st.button("เพิ่มลงตะกร้า", key=f"add_{idx}",
                                                  icon=":material/add_shopping_cart:", width="stretch"):
                                        st.session_state.basket.append(row.to_dict())
                                        st.toast(f"เพิ่ม {row['name']} แล้ว", icon=":material/check_circle:")
                                else:
                                    st.badge("หมดสต็อก", icon=":material/block:", color="red")
                                    st.button("หมดสต็อก", key=f"no_{idx}", disabled=True, width="stretch")
        else:
            st.info("ยังไม่มีเมนูในระบบ", icon=":material/info:")

        if st.session_state.basket:
            with st.bottom:
                count = len(st.session_state.basket)
                total = sum(i["price"] for i in st.session_state.basket)
                with st.container(horizontal=True, vertical_alignment="center",
                                   horizontal_alignment="distribute"):
                    st.write(f":material/shopping_cart: **{count} รายการ** · {thb(total)}")
                    if st.button("ดูตะกร้า", type="primary", icon=":material/arrow_forward:"):
                        st.session_state.page = "cart"
                        st.rerun()

    elif st.session_state.page == "cart":
        if st.button("เลือกเพิ่ม", icon=":material/arrow_back:"):
            st.session_state.page = "menu"
            st.rerun()
        st.subheader("ตะกร้าสินค้า", anchor=False, icon=":material/shopping_cart:")

        if st.session_state.basket:
            counts = Counter(i["name"] for i in st.session_state.basket)
            uniq = {i["name"]: i for i in st.session_state.basket}
            total = 0
            for name, count in counts.items():
                item = uniq[name]
                subtotal = item["price"] * count
                total += subtotal
                with st.container(border=True):
                    c1, c2 = st.columns([1, 3], gap="small", wrap=False, vertical_alignment="center")
                    with c1:
                        st.image(resolve_img_src(item["img"]), width="stretch")
                    with c2:
                        st.markdown(f"**{name}**")
                        st.caption(f"{thb(item['price'])} x {count} = {thb(subtotal)}")
                    b1, b2, b3 = st.columns([1, 1, 1], gap="small", wrap=False)
                    with b1:
                        if st.button("−", key=f"d_{name}", help="ลดจำนวน", width="stretch"):
                            for i, x in enumerate(st.session_state.basket):
                                if x["name"] == name:
                                    del st.session_state.basket[i]
                                    break
                            st.rerun()
                    with b2:
                        st.markdown(f"**{count}**", text_alignment="center")
                    with b3:
                        if st.button("+", key=f"i_{name}", help="เพิ่มจำนวน", width="stretch"):
                            st.session_state.basket.append(item)
                            st.rerun()

            st.subheader(f"รวม {thb(total)}", anchor=False)
            note = st.text_area("หมายเหตุถึงร้าน (ถ้ามี)", max_chars=200)
            blocked = is_queue_mode and not can_order
            if blocked:
                st.caption("ยังไม่ถึงคิวของคุณ จึงยังสั่งอาหารไม่ได้ในตอนนี้")
            if st.button("ยืนยันการสั่ง", type="primary", icon=":material/send:",
                          width="stretch", disabled=blocked):
                now = get_thai_time().strftime("%d/%m/%Y %H:%M")
                items_str = ", ".join(f"{n}(x{c})" for n, c in counts.items())
                save_order({
                    "เวลา": now, "โต๊ะ": st.session_state.user_table,
                    "ลูกค้า": st.session_state.user_name, "รายการอาหาร": items_str,
                    "ยอดรวม": total, "หมายเหตุ": clean_text(note, 200), "สถานะ": "waiting",
                })
                send_email_notification(
                    f"ออเดอร์ใหม่: {st.session_state.user_table}",
                    f"Table: {st.session_state.user_table}\nItems: {items_str}\nTotal: {total}",
                )
                st.session_state.basket = []
                st.session_state.page = "menu"
                st.balloons()
                st.success("ส่งออเดอร์แล้ว ขอบคุณครับ", icon=":material/check_circle:")
                time.sleep(1.5)
                st.rerun()
        else:
            st.info("ตะกร้าว่าง", icon=":material/info:")
            if st.button("กลับไปเลือกเมนู", icon=":material/arrow_back:"):
                st.session_state.page = "menu"
                st.rerun()
