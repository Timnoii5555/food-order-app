"""TimNoi Shabu — shared library for the multi-page app.

Every page under app_pages/ (and the tim.py entrypoint) imports from here:
constants, CSV-backed data helpers, the "why order here" content, the one
bit of scoped CSS the app uses, and the shared header/top-bar renderers.

Data lives in plain CSV files next to the entrypoint (see the *_CSV
constants) so the app needs no external database. Visual styling comes from
``.streamlit/config.toml`` (brand theme) plus native Streamlit widgets —
see the README for why almost no custom HTML/CSS is used.
"""

from __future__ import annotations

import base64
import hmac
import os
import random
import re
import smtplib
import time
from dataclasses import dataclass
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import pandas as pd
import pytz
import streamlit as st

# ============================================================================
# Session state
# ============================================================================
_DEFAULT_STATE = {
    "basket": [],
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
    "admin_authenticated": False,
}


def init_session_state() -> None:
    for key, value in _DEFAULT_STATE.items():
        st.session_state.setdefault(key, value)


def clean_text(value, max_len: int = 60) -> str:
    """Strip control characters/whitespace and cap length of user input."""
    if value is None:
        return ""
    value = re.sub(r"[\r\n\t\x00-\x1f]", " ", str(value)).strip()
    return value[:max_len]


def restore_identity_from_query_params() -> None:
    """Restore a returning customer's identity from the QR-code URL, if present."""
    if not st.session_state.user_name and "name" in st.query_params and "table" in st.query_params:
        name = clean_text(st.query_params.get("name", ""), 40)
        table = clean_text(st.query_params.get("table", ""), 60)
        if name and table:
            st.session_state.user_name = name
            st.session_state.user_table = table
            st.session_state.details_confirmed = True


# ============================================================================
# Secrets & constants
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
# Short, human-readable example the admin sees pre-filled in the "add menu
# item" form's URL field — kept separate from MISSING_IMG below, which is a
# much longer data: URI and would be unreadable clutter in a text input.
PLACEHOLDER_IMG = "https://placehold.co/400x400?text=TimNoi"
# On-brand fallback shown to CUSTOMERS whenever a menu/banner image is
# missing or fails to load — a small inline SVG (a bowl with steam) instead
# of a plain grey box, so an empty menu still looks designed rather than
# broken. No native Streamlit element draws this, so it's a plain <img>
# via a data: URI — no external request, no unsafe HTML, just an image src.
MISSING_IMG = (
    "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSI0MDAiIGhlaWdodD0iN"
    "DAwIiB2aWV3Qm94PSIwIDAgNDAwIDQwMCI+CiAgPGRlZnM+CiAgICA8bGluZWFyR3JhZGllbnQgaWQ9ImciIHgxPSIwIiB5MT0iMCIgeDI9I"
    "jEiIHkyPSIxIj4KICAgICAgPHN0b3Agb2Zmc2V0PSIwJSIgc3RvcC1jb2xvcj0iI0YyRTlEQyIvPgogICAgICA8c3RvcCBvZmZzZXQ9IjEwM"
    "CUiIHN0b3AtY29sb3I9IiNFNEQ1QkYiLz4KICAgIDwvbGluZWFyR3JhZGllbnQ+CiAgPC9kZWZzPgogIDxyZWN0IHdpZHRoPSI0MDAiIGhla"
    "WdodD0iNDAwIiBmaWxsPSJ1cmwoI2cpIi8+CiAgPGcgdHJhbnNmb3JtPSJ0cmFuc2xhdGUoMjAwLDIyNSkiIGZpbGw9Im5vbmUiIHN0cm9rZ"
    "T0iIzhENkU2MyIgc3Ryb2tlLXdpZHRoPSI5IiBzdHJva2UtbGluZWNhcD0icm91bmQiIHN0cm9rZS1saW5lam9pbj0icm91bmQiPgogICAgP"
    "HBhdGggZD0iTS03MiwtNiBhNzIsNTIgMCAxLDAgMTQ0LDAgWiIvPgogICAgPHBhdGggZD0iTS04NCwtNiBMODQsLTYiLz4KICAgIDxwYXRoI"
    "GQ9Ik0tNTgsMTAgcTAsMjAgMjAsMjAgaDc2IHEyMCwwIDIwLC0yMCIgb3BhY2l0eT0iMC41NSIvPgogIDwvZz4KICA8ZyBzdHJva2U9IiM4R"
    "DZFNjMiIHN0cm9rZS13aWR0aD0iNyIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBmaWxsPSJub25lIiBvcGFjaXR5PSIwLjQ1Ij4KICAgIDxwY"
    "XRoIGQ9Ik0xNzIsMTMwIHExMCwtMjIgLTQsLTM4IHEtMTIsLTE0IC0yLC0zNCIvPgogICAgPHBhdGggZD0iTTIwMCwxMjQgcTEwLC0yMiAtN"
    "CwtMzggcS0xMiwtMTQgLTIsLTM0Ii8+CiAgICA8cGF0aCBkPSJNMjI4LDEzMCBxMTAsLTIyIC00LC0zOCBxLTEyLC0xNCAtMiwtMzQiLz4KI"
    "CA8L2c+Cjwvc3ZnPg=="
)


# ============================================================================
# Data helpers
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


# Streamlit Cloud (and multiple browser tabs) can run several sessions and
# auto-refresh fragments against these shared CSV files at the same moment.
# CSV_READ_ERRORS is what a reader can hit if it catches a file mid-write;
# atomic_write_csv is how every writer avoids ever producing that state.
CSV_READ_ERRORS = (OSError, pd.errors.ParserError, pd.errors.EmptyDataError)


def atomic_write_csv(df: pd.DataFrame, path: str) -> None:
    """Write a DataFrame to `path` atomically.

    Writes to a uniquely-named temp file first, then swaps it into place
    with os.replace() (atomic on both Windows and POSIX). A concurrent
    reader therefore always sees either the complete old file or the
    complete new one — never a half-written / empty one.
    """
    tmp_path = f"{path}.tmp-{os.getpid()}-{time.time_ns()}"
    df.to_csv(tmp_path, index=False)
    os.replace(tmp_path, path)


def check_system_updates() -> bool:
    """Return True (and update session state) if shared data changed on disk
    since this SESSION last checked.

    A session's very first check never reports a change: it just finished
    loading everything fresh, so there's nothing to "catch up" on yet — it
    only records the current signal/mtime as the baseline. Forcing a rerun
    on that first check (the old behavior, since the baseline started at
    0.0 and any real timestamp is greater) was harmless on its own, but it
    made every session's first render immediately trigger a second one —
    which, combined with st.navigation, made Streamlit lose track of the
    page a reload should land on. Only genuine *subsequent* changes (some
    other session saved something while this one was already open) should
    trigger a rerun.
    """
    should_rerun = False
    if os.path.exists(REFRESH_SIGNAL_FILE):
        try:
            with open(REFRESH_SIGNAL_FILE, "r") as f:
                signal_time = float(f.read().strip())
            if st.session_state.last_refresh_timestamp == 0.0:
                st.session_state.last_refresh_timestamp = signal_time
            elif signal_time > st.session_state.last_refresh_timestamp:
                st.session_state.last_refresh_timestamp = signal_time
                should_rerun = True
        except (OSError, ValueError):
            pass

    if os.path.exists(MENU_CSV):
        try:
            current_mtime = os.path.getmtime(MENU_CSV)
            if st.session_state.menu_mtime == 0.0:
                st.session_state.menu_mtime = current_mtime
            elif current_mtime > st.session_state.menu_mtime:
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
                    atomic_write_csv(df, ORDER_CSV)
        except CSV_READ_ERRORS:
            pass

    if os.path.exists(QUEUE_CSV):
        try:
            q_df = pd.read_csv(QUEUE_CSV)
            if not q_df.empty:
                q_date_str = str(q_df.iloc[0]["timestamp"]).split()[0]
                today_date_sys = get_thai_time().strftime("%Y-%m-%d")
                if q_date_str != today_date_sys:
                    atomic_write_csv(
                        pd.DataFrame(columns=["queue_id", "customer_name", "timestamp"]), QUEUE_CSV
                    )
        except (*CSV_READ_ERRORS, IndexError):
            pass


DEFAULT_MENU = [
    {"name": "หมูหมัก", "price": 120, "img": MISSING_IMG,
     "category": "เนื้อสัตว์ (Meat)", "in_stock": True},
    {"name": "ผักรวม", "price": 40, "img": MISSING_IMG,
     "category": "ผัก (Veggie)", "in_stock": True},
]

DEFAULT_TABLES = [
    {"table_name": "โต๊ะ 1", "is_shared": False},
    {"table_name": "โต๊ะ 2", "is_shared": False},
    {"table_name": "โต๊ะ 3", "is_shared": False},
    {"table_name": "โต๊ะ 4", "is_shared": False},
    {"table_name": "กลับบ้าน", "is_shared": True},
]


def load_menu() -> pd.DataFrame:
    if not os.path.exists(MENU_CSV):
        atomic_write_csv(pd.DataFrame(DEFAULT_MENU), MENU_CSV)
    try:
        df = pd.read_csv(MENU_CSV)
        for col, default in (("name", ""), ("price", 0), ("img", ""),
                              ("category", "อื่นๆ (Others)"), ("in_stock", True)):
            if col not in df.columns:
                df[col] = default
    except CSV_READ_ERRORS:
        # The file exists but couldn't be parsed (e.g. another session's
        # write raced with this read). Heal it back to the defaults rather
        # than showing every customer an empty menu.
        df = pd.DataFrame(DEFAULT_MENU)
        atomic_write_csv(df, MENU_CSV)
    df["img"] = df["img"].astype(str)
    df["price"] = pd.to_numeric(df["price"], errors="coerce").fillna(0)
    df["in_stock"] = df["in_stock"].apply(to_bool, default=True)
    return df


def load_tables() -> pd.DataFrame:
    if not os.path.exists(TABLES_CSV):
        atomic_write_csv(pd.DataFrame(DEFAULT_TABLES), TABLES_CSV)
    try:
        df = pd.read_csv(TABLES_CSV)
    except CSV_READ_ERRORS:
        df = pd.DataFrame(DEFAULT_TABLES)
        atomic_write_csv(df, TABLES_CSV)
    if "is_shared" not in df.columns:
        df["is_shared"] = False
    df["is_shared"] = df["is_shared"].apply(to_bool, default=False)
    return df


def load_orders() -> pd.DataFrame:
    cols = ["เวลา", "โต๊ะ", "ลูกค้า", "รายการอาหาร", "ยอดรวม", "หมายเหตุ", "สถานะ"]
    if not os.path.exists(ORDER_CSV):
        df = pd.DataFrame(columns=cols)
        atomic_write_csv(df, ORDER_CSV)
        return df
    try:
        return pd.read_csv(ORDER_CSV)
    except CSV_READ_ERRORS:
        # Don't overwrite order_history.csv on a transient read glitch —
        # unlike menu/tables it isn't safe to regenerate, so just degrade
        # to "no orders this run" instead of risking real history.
        return pd.DataFrame(columns=cols)


def load_contacts() -> dict:
    default_contact = {"phone": "0XX-XXX-XXXX", "line": "@timnoishabu", "facebook": "", "instagram": ""}
    if not os.path.exists(CONTACT_CSV):
        atomic_write_csv(pd.DataFrame([default_contact]), CONTACT_CSV)
        return default_contact
    try:
        row = pd.read_csv(CONTACT_CSV).iloc[0].to_dict()
        return {**default_contact, **{k: v for k, v in row.items() if pd.notna(v)}}
    except (*CSV_READ_ERRORS, IndexError):
        return default_contact


def save_contacts(data: dict) -> None:
    atomic_write_csv(pd.DataFrame([data]), CONTACT_CSV)


def load_queue() -> pd.DataFrame:
    cols = ["queue_id", "customer_name", "timestamp"]
    if not os.path.exists(QUEUE_CSV):
        df = pd.DataFrame(columns=cols)
        atomic_write_csv(df, QUEUE_CSV)
        return df
    try:
        return pd.read_csv(QUEUE_CSV)
    except CSV_READ_ERRORS:
        return pd.DataFrame(columns=cols)


def datetime_now_str() -> str:
    return get_thai_time().strftime("%Y-%m-%d %H:%M:%S")


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
    atomic_write_csv(df, QUEUE_CSV)
    trigger_global_refresh()
    return new_id, False


def pop_queue() -> None:
    df = load_queue()
    if not df.empty:
        atomic_write_csv(df.iloc[1:], QUEUE_CSV)
        trigger_global_refresh()


def load_feedback() -> pd.DataFrame:
    cols = ["timestamp", "customer_name", "message"]
    if not os.path.exists(FEEDBACK_CSV):
        df = pd.DataFrame(columns=cols)
        atomic_write_csv(df, FEEDBACK_CSV)
        return df
    try:
        return pd.read_csv(FEEDBACK_CSV)
    except CSV_READ_ERRORS:
        return pd.DataFrame(columns=cols)


def save_feedback_entry(name: str, message: str) -> None:
    df = load_feedback()
    new_entry = {"timestamp": get_thai_time().strftime("%d/%m/%Y %H:%M"),
                 "customer_name": name, "message": message}
    df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
    atomic_write_csv(df, FEEDBACK_CSV)


def delete_feedback_entry(index) -> None:
    df = load_feedback()
    try:
        atomic_write_csv(df.drop(index), FEEDBACK_CSV)
    except KeyError:
        pass


def load_login_log() -> pd.DataFrame:
    cols = ["timestamp", "declared_name", "status"]
    if not os.path.exists(LOGIN_LOG_CSV):
        df = pd.DataFrame(columns=cols)
        atomic_write_csv(df, LOGIN_LOG_CSV)
        return df
    try:
        return pd.read_csv(LOGIN_LOG_CSV)
    except CSV_READ_ERRORS:
        return pd.DataFrame(columns=cols)


def save_login_log(declared_name: str, status: str = "Success") -> None:
    df = load_login_log()
    new_entry = {"timestamp": get_thai_time().strftime("%d/%m/%Y %H:%M:%S"),
                 "declared_name": declared_name or "ไม่ระบุชื่อ", "status": status}
    df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
    atomic_write_csv(df, LOGIN_LOG_CSV)


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
    if path.startswith(("http://", "https://", "data:image/")):
        return path
    if path and os.path.exists(path):
        return get_image_base64(path) or MISSING_IMG
    return MISSING_IMG


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
        atomic_write_csv(df, ORDER_CSV)
        status_result = "merged"
    else:
        cols = ["เวลา", "โต๊ะ", "ลูกค้า", "รายการอาหาร", "ยอดรวม", "หมายเหตุ", "สถานะ"]
        df_new = pd.DataFrame([data])[cols]
        # Append onto the already-loaded `df` and rewrite the whole file
        # atomically, rather than a separate mode="a" append — one fewer
        # code path, and it can never leave a torn header/row behind.
        atomic_write_csv(pd.concat([df, df_new], ignore_index=True), ORDER_CSV)
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
# Shop-wide context: everything derived from the CSVs that more than one
# page needs (menu, tables, today's orders, kitchen load, queue position...).
# Each page calls this itself rather than receiving it from the entrypoint,
# so every page always sees the current, freshly-read state.
# ============================================================================
@dataclass
class ShopContext:
    menu_df: pd.DataFrame
    tables_df: pd.DataFrame
    orders_df: pd.DataFrame
    contact_info: dict
    queue_df: pd.DataFrame
    feedback_df: pd.DataFrame
    waiting_orders: pd.DataFrame
    busy_tables: set
    shared_tables: set
    kitchen_load: int
    is_queue_mode: bool
    can_order: bool
    waiting_q_count: int


def load_shop_context() -> ShopContext:
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

    if not queue_df.empty and st.session_state.get("my_queue_id"):
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

    return ShopContext(
        menu_df=menu_df, tables_df=tables_df, orders_df=orders_df, contact_info=contact_info,
        queue_df=queue_df, feedback_df=feedback_df, waiting_orders=waiting_orders,
        busy_tables=busy_tables, shared_tables=shared_tables, kitchen_load=kitchen_load,
        is_queue_mode=is_queue_mode, can_order=can_order, waiting_q_count=waiting_q_count,
    )


@st.fragment(run_every="4s")
def live_refresh_watcher() -> None:
    """Silently poll for menu/order changes and reload the whole app so every
    open browser tab (customers + kitchen) stays in sync without a manual
    refresh click."""
    if check_system_updates():
        st.rerun()


# ============================================================================
# "Why order here" — value-proposition content shown on the welcome screen
# and from the header menu, so both new and returning customers can see how
# this beats calling a server over / ordering through a third-party app.
# ============================================================================
WHY_US_POINTS = [
    (":material/bolt:", "สั่งตรงเข้าครัวทันที",
     "กดยืนยันปุ๊บ ออเดอร์เข้าระบบครัวทันที ไม่ต้องเรียกพนักงาน ไม่ต้องรอจด ไม่มีตกหล่น"),
    (":material/inventory_2:", "เห็นสต็อกจริงแบบเรียลไทม์",
     "เมนูไหนหมด ระบบขึ้น “หมดสต็อก” ให้ทันที ไม่ต้องสั่งแล้วผิดหวังทีหลัง"),
    (":material/sell:", "ไม่มีค่าคอมมิชชั่นแฝง",
     "ต่างจากแอปส่งอาหารทั่วไป ราคาที่เห็นในเมนูคือราคาที่จ่ายจริง ไม่มีค่าบริการบวกเพิ่ม"),
    (":material/privacy_tip:", "ไม่ต้องสมัครสมาชิก",
     "ใช้แค่ชื่อเล่นกับโต๊ะที่นั่ง ไม่ต้องโหลดแอป ไม่ต้องผูกบัตร ไม่เก็บข้อมูลเกินจำเป็น"),
    (":material/confirmation_number:", "มีระบบคิวให้อัตโนมัติ",
     "ช่วงครัวแน่นไม่ต้องยืนรอหน้าเคาน์เตอร์ รับบัตรคิวออนไลน์ แล้วเช็กสถานะจากมือถือได้เลย"),
    (":material/add_shopping_cart:", "สั่งเพิ่มได้เรื่อยๆ ในบิลเดียว",
     "อยากสั่งเพิ่มระหว่างมื้อ ระบบรวมเข้าออเดอร์เดิมของโต๊ะให้อัตโนมัติ เช็กบิลง่าย จ่ายทีเดียวจบ"),
]


def render_why_us_grid() -> None:
    # A single column, not st.columns(2): most visitors open this from a
    # phone (QR code at the table), and a 2-up grid re-orders column-major
    # once it stacks on a narrow screen — a single column keeps these in
    # the intended reading order on every screen size.
    for icon, title, desc in WHY_US_POINTS:
        with st.container(border=True):
            st.markdown(f"{icon} **{title}**")
            st.caption(desc)


# ============================================================================
# Small, targeted styling touch-up.
#
# Everything else in this app is styled through .streamlit/config.toml and
# native widgets on purpose (theming survives Streamlit upgrades; CSS
# selectors don't). A few visual details no native widget/param covers get
# scoped CSS each, targeted via st.container's `key=` (see Streamlit's own
# theming guide on the `.st-key-*` escape hatch):
#   - cropping photos of very different shapes/sizes to a consistent square,
#     which is what makes a hand-photographed menu (and the small cart
#     thumbnail) look like a proper product catalogue instead of a grid of
#     mismatched thumbnails.
#   - the cart thumbnail is placed in a horizontal flex row (not st.columns)
#     specifically because st.columns stacks to full width on a narrow
#     phone screen — which is what made the product photo balloon to
#     nearly the card's full width before; a flex row keeps it pinned to
#     its 56px width at every screen size.
#   - shrinking the cart's qty +/- buttons from full-size text buttons down
#     to small square icon-sized ones, so the row reads as one compact unit.
# ============================================================================
def inject_scoped_css() -> None:
    st.html("""
    <style>
    [class*="st-key-menu_card_"] { overflow: hidden; }
    [class*="st-key-menu_card_"] [data-testid="stImage"] img {
        aspect-ratio: 1 / 1;
        object-fit: cover;
        border-radius: 10px;
    }
    [class*="st-key-menu_card_"] { transition: box-shadow .15s ease, transform .15s ease; }
    [class*="st-key-menu_card_"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 24px rgba(193, 39, 45, .16);
    }
    [class*="st-key-cart_row_"] [data-testid="stImage"] {
        flex: 0 0 auto;
        width: 56px;
    }
    [class*="st-key-cart_row_"] [data-testid="stImage"] img {
        aspect-ratio: 1 / 1;
        object-fit: cover;
        border-radius: 8px;
    }
    [class*="st-key-qty_row_"] { gap: .5rem !important; }
    [class*="st-key-qty_row_"] [data-testid="stButton"] button {
        min-width: 2.1rem;
        width: 2.1rem;
        height: 2.1rem;
        padding: 0;
        font-size: .95rem;
    }
    </style>
    """)


# ============================================================================
# Header + sidebar — shared across every page. Navigation itself is
# Streamlit's own sidebar page list (st.navigation(position="sidebar") in
# tim.py) rather than anything built here — the previous "เมนู" popover
# doubled as both "food menu" and "navigation menu", which was confusing,
# and a real sidebar is also the standard, more discoverable place for site
# navigation. render_sidebar_extras() adds the non-navigation bits (contact
# links, a manual refresh) below Streamlit's auto-generated page list.
# ============================================================================
def render_header(contact_info: dict) -> None:
    header_logo, header_name = st.columns([1.1, 3], vertical_alignment="center")
    with header_logo:
        if os.path.exists("logo.png"):
            st.image("logo.png", width="stretch")
        else:
            st.markdown("# 🍲")
    with header_name:
        st.title("TimNoi Shabu", text_alignment="left")
        st.caption("หมูพรีเมียมสดสะอาด คัดคุณภาพทุกวัน")
        with st.container(horizontal=True):
            st.caption("🕒 เปิดบริการ 00:00 – 23:59 น.")
            st.caption(f"📞 {contact_info.get('phone', '-')}")
    st.divider()


def render_sidebar_extras(contact_info: dict) -> None:
    if os.path.exists("logo.png"):
        st.logo("logo.png", size="large")
    with st.sidebar:
        if st.button("รีเฟรชหน้านี้", icon=":material/refresh:", width="stretch"):
            st.rerun()
        st.markdown("---")
        st.caption("ช่องทางติดต่อ")
        fb_url = sanitize_link(contact_info.get("facebook", ""))
        ig_url = sanitize_link(contact_info.get("instagram", ""))
        if fb_url:
            st.link_button("Facebook", fb_url, icon=":material/open_in_new:", width="stretch")
        if ig_url:
            st.link_button("Instagram", ig_url, icon=":material/open_in_new:", width="stretch")
        line_id = contact_info.get("line", "")
        if line_id:
            st.caption(f"LINE: {line_id}")


def require_customer_identity() -> None:
    """Guard for customer pages other than menu.py: if the visitor hasn't
    confirmed their name/table yet (e.g. they hit /cart directly), send them
    to the identity screen instead of showing a broken partial page."""
    if not st.session_state.details_confirmed:
        st.info("กรุณายืนยันชื่อและโต๊ะที่หน้าเมนูก่อนครับ", icon=":material/info:")
        if st.button("ไปหน้าเมนู", icon=":material/storefront:"):
            st.switch_page("app_pages/menu.py")
        st.stop()


def render_customer_topbar(ctx: "ShopContext", *, apply_queue_gate: bool, show_cart_badge: bool) -> None:
    """Identity bar, promo banner, queue gate, and kitchen status — shown at
    the top of every customer-facing page once identity is confirmed."""
    with st.container(horizontal=True, horizontal_alignment="distribute",
                       vertical_alignment="center", border=True):
        st.write(f":material/person: **{st.session_state.user_name}**  ·  "
                 f":material/table_restaurant: **{st.session_state.user_table}**")
        with st.container(horizontal=True, vertical_alignment="center"):
            cart_count = len(st.session_state.basket)
            if cart_count and show_cart_badge:
                if st.button(f"ตะกร้า ({cart_count})", icon=":material/shopping_cart:",
                              type="primary"):
                    st.switch_page("app_pages/cart.py")
            if st.button("เปลี่ยนชื่อ/โต๊ะ", icon=":material/edit:"):
                st.session_state.details_confirmed = False
                st.query_params.clear()
                st.switch_page("app_pages/menu.py")

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

    if apply_queue_gate and ctx.is_queue_mode:
        if st.session_state.my_queue_id:
            if ctx.can_order:
                st.success("ถึงคิวของคุณแล้ว สั่งอาหารได้เลย", icon=":material/check_circle:")
            else:
                with st.container(border=True, horizontal_alignment="center"):
                    st.metric("บัตรคิวของคุณ", st.session_state.my_queue_id)
                    st.caption(f"เหลืออีก {ctx.waiting_q_count} คิวก่อนถึงคุณ")
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

    if not ctx.waiting_orders.empty:
        with st.status(f"กำลังปรุง: {ctx.waiting_orders.iloc[0]['โต๊ะ']}", state="running"):
            st.caption(f"คิวในครัวตอนนี้ {ctx.kitchen_load} ออเดอร์")
    else:
        with st.status("ครัวว่าง พร้อมรับออเดอร์", state="complete"):
            pass
