import streamlit as st
import pandas as pd
import datetime
import requests
import json

# --- CONFIGURATION ---
PUBLISHED_ID = "2PACX-1vRD_DZFeFRkKopWC7TQ3jQqLc_BzTIvlWrg1dwK9ZyKAiQLTDkWmMNvxn-sEoG1LytmWznR1pVtcM2P"
SCRIPT_URL = "https://google.com"

# YOUR VERIFIED TAB GID NUMBERS
GID_USERS = "1184024919"
GID_STUDENTS = "0"
GID_LOG = "761431643"

def load_data(gid_number):
    try:
        url = f"https://google.com{PUBLISHED_ID}/pub?output=csv&gid={gid_number}"
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
                    st.session_state.role = str(user_row['role'].values).strip()
                    st.rerun()
                else:
                    st.error("Invalid Email or Password. Please check your credentials in the Google Sheet.")
            else:
                st.error(f"Column mismatch! Found headers: {list(users_df.columns)}. Expected: email, password, role")
        else:
            st.error("Could not download User account database. Please try clicking Log In again in a moment.")

else:
    # --- LOGGED IN APP ---
    st.sidebar.write(f"Logged in as: **{st.session_state.email}** ({st.session_state.role})")
    if st.sidebar.button("Log Out"):
        st.session_state.logged_in = False
        st.session_state.email = ""
        st.session_state.role = ""
        st.rerun()

    students_df = load_data(GID_STUDENTS)

    if st.session_state.role.lower() == "admin":
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
            # 🆕 MECHANISM 1: "SELECT ALL / UNSELECT ALL" MASTER SWITCH
            select_all = st.checkbox("Toggle All Students (Check to select everyone as Present)", value=True)
            
            st.write("---")
            
            with st.form("attendance_form"):
                attendance_states = {}
                
                # Render student rows cleanly
                for student in filtered_students:
                    # Create two side-by-side columns: left for input checkbox, right for text status badge
                    left_col, right_col = st.columns([3, 1])
                    
                    with left_col:
                        # Link checkbox value directly to the master "select_all" checkbox state
                        attendance_states[student] = st.checkbox(student, value=select_all)
                    
                    with right_col:
                        # 🆕 MECHANISM 2: VISIBLE PRESENT/ABSENT VISUAL STATUS BADGE
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
        st.markdown(f"[👉 Open Google Spreadsheet Database](https://google.com{SHEET_ID}/edit)")

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
