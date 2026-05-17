# streamlit_app_live_checkboxes.py
import streamlit as st
import pandas as pd
import datetime
import requests
import json
import time
import re
from io import StringIO
from typing import Dict

# --- CONFIGURATION (update these) ---
SHEET_ID = "1p8GUD8x3CIy4X5u2t-TDCHPkqoGCn4DgCYTtiWq75E8"
SCRIPT_URL = "https://script.google.com/macros/s/your-script-id/exec"  # <-- replace with your Apps Script URL

GID_USERS = "1184024919"
GID_STUDENTS = "0"
GID_LOG = "761431643"

# --- SAFE RERUN HELPER ---
def safe_rerun():
    try:
        st.experimental_rerun()
    except Exception:
        try:
            params = st.experimental_get_query_params()
            params["_rerun_ts"] = int(time.time())
            st.experimental_set_query_params(**params)
            return
        except Exception:
            st.session_state["_force_rerun_marker"] = int(time.time())
            return

# --- NETWORK HELPERS ---
def build_sheet_export_url(sheet_id: str, gid_number: str) -> str:
    return f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid_number}"

def http_get_with_retries(url: str, timeout: int = 10, retries: int = 2, backoff: float = 1.0):
    last_exc = None
    for attempt in range(retries + 1):
        try:
            resp = requests.get(url, timeout=timeout)
            return resp
        except Exception as e:
            last_exc = e
            if attempt < retries:
                time.sleep(backoff * (attempt + 1))
            else:
                raise
    raise last_exc

@st.cache_data(ttl=300)
def fetch_csv_from_sheet(gid_number: str) -> Dict:
    url = build_sheet_export_url(SHEET_ID, gid_number)
    try:
        resp = http_get_with_retries(url, timeout=10, retries=2, backoff=1.0)
        status = resp.status_code
        text_snippet = resp.text[:500]
        if status == 200:
            df = pd.read_csv(StringIO(resp.text))
            df.columns = df.columns.astype(str).str.strip().str.lower()
            return {"df": df, "status_code": status, "response_text": text_snippet, "url": url}
        else:
            return {"df": pd.DataFrame(), "status_code": status, "response_text": text_snippet, "url": url}
    except Exception as e:
        return {"df": pd.DataFrame(), "status_code": "CRASHED", "response_text": str(e), "url": url}

# --- UTILITIES ---
def slugify_key(s: str) -> str:
    if s is None:
        return "unknown"
    s = str(s).strip().lower()
    s = re.sub(r'\s+', '_', s)
    s = re.sub(r'[^0-9a-zA-Z_]', '_', s)
    s = re.sub(r'_+', '_', s)
    return s or "unknown"

def unique_keys(names):
    counts = {}
    mapping = {}
    for name in names:
        base = slugify_key(name)
        counts.setdefault(base, 0)
        counts[base] += 1
        if counts[base] == 1:
            mapping[name] = base
        else:
            mapping[name] = f"{base}_{counts[base]}"
    return mapping

# --- SESSION STATE INIT ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "email" not in st.session_state:
    st.session_state.email = ""
if "role" not in st.session_state:
    st.session_state.role = ""
if "debug_mode" not in st.session_state:
    st.session_state.debug_mode = False
if "last_payload" not in st.session_state:
    st.session_state.last_payload = None

st.set_page_config(page_title="NGO Attendance Portal", page_icon="📝", layout="wide")
st.title("📝 NGO Attendance Portal")

# --- LOGIN UI ---
if not st.session_state.logged_in:
    st.subheader("Login")
    email_input = st.text_input("Email Address")
    password_input = st.text_input("Password", type="password")

    if st.button("Log In"):
        result = fetch_csv_from_sheet(GID_USERS)
        users_df = result["df"]
        st.session_state[f"debug_url_{GID_USERS}"] = result["url"]
        st.session_state[f"status_code_{GID_USERS}"] = result["status_code"]
        st.session_state[f"response_text_{GID_USERS}"] = result["response_text"]

        if not users_df.empty:
            clean_email = email_input.strip().lower()
            clean_pwd = password_input.strip()

            if 'email' in users_df.columns and 'password' in users_df.columns:
                users_df['email'] = users_df['email'].astype(str).str.strip().str.lower()
                users_df['password'] = users_df['password'].astype(str).str.strip()

                user_row = users_df[(users_df['email'] == clean_email) & (users_df['password'] == clean_pwd)]
                if not user_row.empty:
                    st.session_state.logged_in = True
                    st.session_state.email = clean_email

                    if 'role' in user_row.columns and len(user_row) > 0:
                        role_value = user_row['role'].iloc[0]
                    else:
                        role_value = "teacher"
                    if pd.isna(role_value):
                        role_value = "teacher"

                    st.session_state.role = str(role_value).strip().lower()
                    safe_rerun()
                else:
                    st.error("Invalid Email or Password. Please check your credentials in the Google Sheet.")
            else:
                st.error("Column mismatch! Expected columns: email, password, role")
        else:
            st.error("Unable to read Users sheet. Open the Connection Debug Panel for details.")

    st.write("---")
    with st.expander("🛠️ Connection Debug Panel"):
        st.write("Testing connection to your 'Users' sheet tab...")
        result = fetch_csv_from_sheet(GID_USERS)
        if not result["df"].empty:
            st.success("✅ Connection Successful")
            st.write("Headers found:")
            st.code(list(result["df"].columns))
            if 'email' in result["df"].columns:
                st.dataframe(result["df"][['email', 'role']].head(5))
        else:
            st.error("❌ Could not fetch Users sheet. Check sharing settings and the Sheet ID.")

        if st.button("🔍 Run Live Connection Diagnostics"):
            st.metric(label="Google Server Status Code", value=str(result.get("status_code", "No data")))
            st.code(result.get("response_text", "Empty response"))
            st.write("Constructed URL:")
            st.code(result.get("url", "No URL built yet"))

else:
    display_role = st.session_state.role.title() if st.session_state.role else "Teacher"
    st.sidebar.write(f"Logged in as: **{st.session_state.email}** ({display_role})")

    if "admin" in st.session_state.role.lower():
        st.sidebar.checkbox("Debug Mode", value=st.session_state.debug_mode, key="debug_mode")
    if st.sidebar.button("Log Out"):
        keys_to_clear = [k for k in st.session_state.keys() if k.startswith("check_") or k.startswith("debug_url_") or k in ("logged_in","email","role","last_payload")]
        for k in keys_to_clear:
            del st.session_state[k]
        st.session_state.logged_in = False
        safe_rerun()

    students_result = fetch_csv_from_sheet(GID_STUDENTS)
    students_df = students_result["df"]
    st.session_state[f"debug_url_{GID_STUDENTS}"] = students_result["url"]
    st.session_state[f"status_code_{GID_STUDENTS}"] = students_result["status_code"]
    st.session_state[f"response_text_{GID_STUDENTS}"] = students_result["response_text"]

    if "admin" in st.session_state.role.lower():
        menu = st.sidebar.selectbox("Navigation", ["Take Attendance", "Admin Sheet Link", "Absenteeism Analytics"])
    else:
        menu = "Take Attendance"
        st.sidebar.info("Teacher Panel: Profile edits are locked.")

    # --- TAKE ATTENDANCE (LIVE CHECKBOXES, no st.form) ---
    if menu == "Take Attendance":
        st.header("Session Setup")

        available_batches = []
        if not students_df.empty and 'batch' in students_df.columns:
            available_batches = list(students_df['batch'].dropna().astype(str).str.strip().unique())
        if not available_batches:
            available_batches = ["Batch A"]

        col1, col2 = st.columns(2)
        with col1:
            selected_batch = st.selectbox("Select Batch", available_batches)
            selected_subject = st.selectbox("Select Subject", ["Math", "English", "Science", "Computers"])
        with col2:
            selected_date = st.date_input("Date", datetime.date.today())
            selected_teacher = st.text_input("Incharge Teacher Name", value=st.session_state.email)

        st.write("---")
        st.header(f"Roster for {selected_batch}")

        filtered_students = []
        if not students_df.empty and 'student_name' in students_df.columns and 'batch' in students_df.columns:
            students_df['batch'] = students_df['batch'].astype(str).str.strip()
            filtered_students = students_df[students_df['batch'] == str(selected_batch).strip()]['student_name'].astype(str).tolist()
        elif not students_df.empty and 'student_name' in students_df.columns:
            filtered_students = students_df['student_name'].astype(str).tolist()

        if filtered_students:
            name_to_key = unique_keys(filtered_students)

            # Bulk mark buttons
            col_b1, col_b2 = st.columns(2)
            with col_b1:
                if st.button("✅ Mark All Present"):
                    for name, key in name_to_key.items():
                        st.session_state[f"check_{key}"] = True
                    safe_rerun()
            with col_b2:
                if st.button("❌ Mark All Absent"):
                    for name, key in name_to_key.items():
                        st.session_state[f"check_{key}"] = False
                    safe_rerun()

            st.write("---")

            # Render live checkboxes (outside a form) so toggles update immediately
            for student in filtered_students:
                key_fragment = name_to_key[student]
                key_name = f"check_{key_fragment}"
                if key_name not in st.session_state:
                    st.session_state[key_name] = True  # default present

                left_col, right_col = st.columns([3,1])
                with left_col:
                    # checkbox returns the current value but we bind it to session_state key
                    current = st.checkbox(student, value=st.session_state.get(key_name, True), key=key_name)
                with right_col:
                    if st.session_state.get(key_name, False):
                        st.markdown("<div style='text-align:right'><span style='color:green; font-weight:bold; background-color:#e6f4ea; padding:6px 10px; border-radius:6px;'>🟢 PRESENT</span></div>", unsafe_allow_html=True)
                    else:
                        st.markdown("<div style='text-align:right'><span style='color:red; font-weight:bold; background-color:#fce8e6; padding:6px 10px; border-radius:6px;'>🔴 ABSENT</span></div>", unsafe_allow_html=True)

            st.write("")
            # Submit button outside form — reads live session_state values
            if st.button("Submit Attendance to Google Sheet"):
                now_timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                payload = []
                for student in filtered_students:
                    key_fragment = name_to_key[student]
                    is_present = st.session_state.get(f"check_{key_fragment}", False)
                    payload.append({
                        "Date": str(selected_date),
                        "Batch": str(selected_batch),
                        "Teacher": str(selected_teacher),
                        "Subject": str(selected_subject),
                        "Timestamp": now_timestamp,
                        "StudentName": str(student),
                        "Status": "Present" if is_present else "Absent"
                    })

                st.session_state.last_payload = payload
                try:
                    headers = {"Content-Type": "application/json"}
                    resp = requests.post(SCRIPT_URL, data=json.dumps(payload), headers=headers, timeout=10)
                    if resp.status_code == 200:
                        st.success("🎉 Attendance logged successfully into your Google Sheet!")
                    else:
                        st.error(f"Spreadsheet error (Status Code: {resp.status_code})")
                        if st.session_state.debug_mode:
                            st.code(resp.text[:1000])
                except Exception as e:
                    st.error("Connection Error: Check your Apps Script Link configuration and network.")
                    if st.session_state.debug_mode:
                        st.exception(e)

        else:
            st.warning("No students listed under this batch name yet. Add students to your Students sheet or check the batch name.")

    # --- ADMIN CONTROLS ---
    elif menu == "Admin Sheet Link":
        st.header("Admin Management")
        st.write("As an Admin, click below to open the Google Spreadsheet database to add or edit students and users.")
        st.markdown(f"[👉 Open Google Spreadsheet Database](https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit)")

    # --- ANALYTICS ---
    elif menu == "Absenteeism Analytics":
        st.header("🔍 Search Absenteeism History")
        log_result = fetch_csv_from_sheet(GID_LOG)
        log_data = log_result["df"]
        st.session_state[f"debug_url_{GID_LOG}"] = log_result["url"]
        st.session_state[f"status_code_{GID_LOG}"] = log_result["status_code"]
        st.session_state[f"response_text_{GID_LOG}"] = log_result["response_text"]

        if not log_data.empty and 'student_name' in log_data.columns:
            search_name = st.selectbox("Select Student to Check", sorted(log_data['student_name'].unique()))
            st.write("Filter Date Range:")
            start_dt = st.date_input("Start Date", datetime.date(2026, 4, 1))
            end_dt = st.date_input("End Date", datetime.date(2026, 5, 31))

            if 'date' in log_data.columns:
                try:
                    log_data['date'] = pd.to_datetime(log_data['date']).dt.date
                except Exception:
                    st.warning("Could not parse date column in log; ensure it is in a standard date format.")
            history = log_data[(log_data['student_name'] == search_name) & (log_data['date'] >= start_dt) & (log_data['date'] <= end_dt)]

            st.subheader(f"History for {search_name}")
            if not history.empty:
                st.dataframe(history)
                absents = len(history[history['status'].str.lower() == 'absent']) if 'status' in history.columns else 0
                st.metric(label="Total Days Missed", value=absents)
            else:
                st.info("No records match this date range for this student.")
        else:
            st.info("No entries found in your Attendance_Log tab yet or the sheet is missing the expected columns.")

    # --- DEBUG PANEL FOR ADMINS ---
    if st.session_state.debug_mode:
        st.write("---")
        st.subheader("Debug Information")
        st.write("Last payload (preview):")
        st.code(json.dumps(st.session_state.get("last_payload", []), indent=2)[:2000])
        st.write("Last fetch statuses:")
        for gid in (GID_USERS, GID_STUDENTS, GID_LOG):
            st.write(f"Sheet GID {gid}:")
            st.write("URL:", st.session_state.get(f"debug_url_{gid}", "n/a"))
            st.write("Status:", st.session_state.get(f"status_code_{gid}", "n/a"))
            st.code(st.session_state.get(f"response_text_{gid}", "n/a")[:1000])
        st.write("Session keys snapshot (some keys omitted):")
        keys = {k: str(v)[:200] for k, v in st.session_state.items() if k.startswith("check_") or k in ("email","role")}
        st.json(keys)
