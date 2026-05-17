import streamlit as st
import pandas as pd
import datetime
import requests
import json

# --- CONFIGURATION ---
SHEET_ID = "1p8GUD8x3CIy4X5u2t-TDCHPkqoGCn4DgCYTtiWq75E8"
SCRIPT_URL = "https://google.com"

# PLUGGED IN YOUR EXACT TAB GID NUMBERS
GID_USERS = "1184024919"
GID_STUDENTS = "0"
GID_LOG = "761431643"

def load_data(gid_number):
    try:
        # Strict URL targeting using your exact tab GID numbers
        url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={gid_number}"
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
                    st.session_state.role = str(user_row.iloc['role']).strip()
                    st.rerun()
                else:
                    st.error("Invalid Email or Password. Please check your credentials in the Google Sheet.")
            else:
                st.error(f"Column mismatch! Found headers: {list(users_df.columns)}. Expected: email, password, role")
        else:
            st.error("Could not process account authorization rules. Check your GID numbers.")

    # --- CONNECTION DEBUG PANEL ---
    st.write("---")
    with st.expander("🛠️ Connection Debug Panel"):
        st.write("Testing clean target connection to your 'Users' sheet tab...")
        test_df = load_data(GID_USERS)
        if not test_df.empty:
            st.success("✅ Connection Fixed! Streamlit can isolate your proper 'Users' tab layout.")
            st.write("Headers found inside this specific tab:")
            st.code(list(test_df.columns))
            if 'email' in test_df.columns:
                st.dataframe(test_df[['email', 'role']].head(3))
        else:
            st.error("❌ Link connection pending. Please verify your tab GID numbers on Lines 12-14 match your sheets.")

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
            with st.form("attendance_form"):
                attendance_states = {}
                for student in filtered_students:
                    attendance_states[student] = st.checkbox(student, value=True)
                
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
        st.markdown(f"[👉 Open Google Spreadsheet Database](https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit)")

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
