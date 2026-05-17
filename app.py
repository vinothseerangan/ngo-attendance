import streamlit as st
import pandas as pd
import datetime
import requests
import json
import time

# --- CONFIGURATION ---
PUBLISHED_ID = "2PACX-1vRD_DZFeFRkKopWC7TQ3jQqLc_BzTIvlWrg1dwK9ZyKAiQLTDkWmMNvxn-sEoG1LytmWznR1pVtcM2P"
SCRIPT_URL = "https://google.com"

# YOUR VERIFIED TAB GID NUMBERS
GID_USERS = "1184024919"
GID_STUDENTS = "0"
GID_LOG = "761431643"

# 🔒 FIXED BYPASS: ttl=0 tells Streamlit never to store this data in frozen memory
@st.cache_data(ttl=0)
def load_data(gid_number):
    try:
        # BUSTING THE CACHE WALL: Adding a live timestamp forces a fresh download from Google every second
        nocache_timestamp = int(time.time())
        url = f"https://google.com{PUBLISHED_ID}/pub?output=csv&gid={gid_number}&cb={nocache_timestamp}"
        df = pd.read_csv(url)
        df.columns = df.columns.astype(str).str.strip().str.lower()
        return df
    except Exception as e:
        return pd.DataFrame()

# Initialize Session States
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "email" not in st.session_state:
    st.session_state.email = ""
if "role" not in st.session_state:
    st.session_state.role = ""

st.set_page_config(page_title="NGO Attendance Portal", page_icon="📝")
st.title("📝 NGO Attendance Portal")

# --- LOGIN INTERFACE ---
if not st.session_state.logged_in:
    st.subheader("Login")
    email_input = st.text_input("Email Address")
    password_input = st.text_input("Password", type="password")
    
    if st.button("Log In"):
        users_df = load_data(GID_USERS)
        if not users_df.empty:
            clean_email = email_input.strip().lower()
            clean_pwd = password_input.strip()
            
            if 'email' in users_df.columns and 'password' in users_df.columns:
                users_df['email'] = users_df['email'].astype(str).str.strip().str.lower()
                users_df['password'] = users_df['password'].astype(str).str.strip()
                
                user_row = users_df[(users_df['email'] == clean_email) & (users_df['password'] == clean_pwd)]
                if not user_row.empty:
                    st.session_state.logged_in = True
                    st.session_state.email = email_input.strip()
                    # Fixed list output extraction bug
                    st.session_state.role = str(user_row['role'].values[0]).strip().lower() 
                    st.rerun()
                else:
                    st.error("Invalid Email or Password. Please check your credentials in the Google Sheet.")
            else:
                st.error(f"Column mismatch! Found headers: {list(users_df.columns)}. Expected: email, password, role")
        else:
            st.error("Connection lag detected. Please try clicking Log In again in a moment.")

    # --- CONNECTION DEBUG PANEL ---
    st.write("---")
    with st.expander("🛠️ Connection Debug Panel (Check Status Live)"):
        st.write("Fetching direct data package streams...")
        test_df = load_data(GID_USERS)
        if not test_df.empty:
            st.success("✅ Connection Successful! Tab isolated.")
            st.write("Headers found inside this specific tab:")
            st.code(list(test_df.columns))
            if 'email' in test_df.columns:
                st.dataframe(test_df[['email', 'role']].head(3))
        else:
            st.error("❌ Link connection pending. System re-sync required.")

else:
    # --- LOGGED IN APP ---
    st.sidebar.write(f"Logged in as: **{st.session_state.email}** ({st.session_state.role})")
    if st.sidebar.button("Log Out"):
        st.session_state.logged_in = False
        st.session_state.email = ""
        st.session_state.role = ""
        st.cache_data.clear() # Clears session cache completely on logout
        st.rerun()

    students_df = load_data(GID_STUDENTS)

    if st.session_state.role.lower() == "admin" or "admin" in st.session_state.role:
        menu = st.sidebar.selectbox("Navigation", ["Take Attendance", "Admin Sheet Link", "Absenteeism Analytics"])
    else:
        menu = "Take Attendance"
        st.sidebar.info("Teacher Panel: Profile edits are locked.")

    # --- TAKE ATTENDANCE ---
    if menu == "Take Attendance":
        st.header("Session Setup")
        
        available_batches = list(students_df['batch'].dropna().unique()) if not students_df.empty and 'batch' in students_df.columns else ["Batch A"]
        
        col1, col2 = st.columns(2)
        with col1:
            selected_batch = st.selectbox("Select Batch", available_batches)
            selected_subject = st.selectbox("Select Subject", ["Math", "English", "Science", "Computers"])
        with col2:
            selected_date = st.date_input("Date", datetime.date.today())
            selected_teacher = st.text_input("Incharge Teacher Name", value=st.session_state.email)

        st.write("---")
        st.header(f"Roster for {selected_batch}")

        if not students_df.empty and 'student_name' in students_df.columns:
            students_df['batch'] = students_df['batch'].astype(str).str.strip()
            filtered_students = students_df[students_df['batch'] == str(selected_batch).strip()]['student_name'].tolist()
        else:
            filtered_students = []

        if filtered_students:
            col_b1, col_b2 = st.columns(2)
            with col_b1:
                if st.button("✅ Mark All Present"):
                    for s in filtered_students:
                        st.session_state[f"check_{s}"] = True
            with col_b2:
                if st.button("❌ Mark All Absent"):
                    for s in filtered_students:
                        st.session_state[f"check_{s}"] = False

            st.write("---")
            
            with st.form("attendance_form"):
                attendance_states = {}
                for student in filtered_students:
                    key_name = f"check_{student}"
                    if key_name not in st.session_state:
                        st.session_state[key_name] = True
                    
                    left_col, right_col = st.columns(2)
                    with left_col:
                        # Individual checkboxes bind strictly to session state keys
                        attendance_states[student] = st.checkbox(student, key=key_name)
                    with right_col:
                        if attendance_states[student]:
                            st.markdown("<span style='color:green; font-weight:bold; background-color:#e6f4ea; padding:4px 8px; border-radius:4px;'>🟢 PRESENT</span>", unsafe_allow_html=True)
                        else:
                            st.markdown("<span style='color:red; font-weight:bold; background-color:#fce8e6; padding:4px 8px; border-radius:4px;'>🔴 ABSENT</span>", unsafe_allow_html=True)
                
                st.write("")
                submit_btn = st.form_submit_button("Submit Attendance to Google Sheet")
                
                if submit_btn:
                    now_timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    payload = []
                    for student, is_present in attendance_states.items():
                        payload.append({
                            "Date": str(selected_date),
                            "Batch": str(selected_batch),
                            "Teacher": str(selected_teacher),
                            "Subject": str(selected_subject),
                            "Timestamp": now_timestamp,
                            "StudentName": str(student),
                            "Status": "Present" if is_present else "Absent"
                        })
                    
                    try:
                        response = requests.post(SCRIPT_URL, data=json.dumps(payload))
                        if response.status_code == 200:
                            st.success("🎉 Attendance logged successfully into your Google Sheet!")
                        else:
                            st.error(f"Spreadsheet error (Status Code: {response.status_code})")
                    except Exception as e:
                        st.error("Connection Error: Check your Apps Script Link configuration.")
        else:
            st.warning("No students listed under this batch name yet.")

    # --- ADMIN CONTROLS ---
    elif menu == "Admin Sheet Link":
        st.header("Admin Management")
        st.write("As an Admin, click below to add new students, update teacher passwords, or add batches:")
        st.markdown(f"[👉 Open Google Spreadsheet Database](https://google.com)")

    # --- ANALYTICS ---
    elif menu == "Absenteeism Analytics":
        st.header("🔍 Search Absenteeism History")
        log_data = load_data(GID_LOG)
        
        if not log_data.empty:
            if 'student_name' in log_data.columns:
                search_name = st.selectbox("Select Student to Check", log_data['student_name'].unique())
                
                st.write("Filter Date Range:")
                start_dt = st.date_input("Start Date", datetime.date(2026, 4, 1))
                end_dt = st.date_input("End Date", datetime.date(2026, 5, 31))
                
                log_data['date'] = pd.to_datetime(log_data['date']).dt.date
                history = log_data[(log_data['student_name'] == search_name) & (log_data['date'] >= start_dt) & (log_data['date'] <= end_dt)]
                
                st.subheader(f"History for {search_name}")
                if not history.empty:
                    st.dataframe(history)
                    absents = len(history[history['status'].str.lower() == 'absent']) if 'status' in history.columns else 0
                    st.metric(label="Total Days Missed", value=absents)
                else:
                    st.info("No records match this date range for this student.")
            else:
                st.info("Submit your first entry to populate analytics schema.")
        else:
            st.info("No entries found in your Attendance_Log tab yet.")
