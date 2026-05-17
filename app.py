import streamlit as st
import pandas as pd
import datetime
import requests
import json
from io import StringIO

# --- CONFIGURATION ---
SHEET_ID = "1p8GUD8x3CIy4X5u2t-TDCHPkqoGCn4DgCYTtiWq75E8"
SCRIPT_URL = "https://google.com"

GID_USERS = "1184024919"
GID_STUDENTS = "0"
GID_LOG = "761431643"

def load_data(gid_number):
    # This is our raw probe to see exactly what Google is doing
    url = f"https://google.com{SHEET_ID}/export?format=csv&gid={gid_number}"
    try:
        response = requests.get(url, timeout=10)
        
        # Save response metrics in session state so we can display them on screen
        st.session_state[f"status_code_{gid_number}"] = response.status_code
        st.session_state[f"response_text_{gid_number}"] = response.text[:500] # Get first 500 characters
        
        if response.status_code == 200:
            df = pd.read_csv(StringIO(response.text))
            df.columns = df.columns.astype(str).str.strip().str.lower()
            return df
        else:
            return pd.DataFrame()
    except Exception as e:
        st.session_state[f"status_code_{gid_number}"] = "CRASHED"
        st.session_state[f"response_text_{gid_number}"] = str(e)
        return pd.DataFrame()

# Initialize Session States
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "email" not in st.session_state:
    st.session_state.email = ""
if "role" not in st.session_state:
    st.session_state.role = ""

st.set_page_config(page_title="NGO Attendance Portal", page_icon="📝")
st.title("📝 PLAN A: Diagnostic Attendance Portal")

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
                    st.session_state.role = str(user_row['role'].values).strip().lower() if len(user_row) > 0 else "teacher"
                    st.rerun()
                else:
                    st.error("Invalid Email or Password. Please check your credentials in the Google Sheet.")
            else:
                st.error(f"Column mismatch! Expected: email, password, role")
        else:
            st.error("Connection lag detected. Please inspect the PLAN A Live Debugger Box below.")

    # --- PLAN A LIVE DEBUGGER BOX ---
    st.write("---")
    st.subheader("🕵️‍♂️ Plan A Live Network Debugger")
    st.info("Click the button below to force a live test call and see EXACTLY why Google is rejecting the link connection.")
    
    if st.button("🔍 Run Live Connection Diagnostics"):
        with st.spinner("Testing live tunnel..."):
            test_df = load_data(GID_USERS)
            
            st.metric(label="Google Server Status Code", value=str(st.session_state.get(f"status_code_{GID_USERS}", "No data")))
            
            st.write("**Raw Server Data Received from Google Sheets:**")
            raw_html_text = st.session_state.get(f"response_text_{GID_USERS}", "Empty response")
            st.code(raw_html_text)
            
            if "html" in raw_html_text.lower():
                st.warning("⚠️ Alert: Google is returning an HTML webpage (like a login or security block page) instead of raw text rows! This confirms a network block or permission reset.")

else:
    # --- LOGGED IN APP PANEL (Hidden until authenticated) ---
    st.sidebar.write(f"Logged in as: **{st.session_state.email}**")
    if st.sidebar.button("Log Out"):
        st.session_state.logged_in = False
        st.rerun()
    st.success("You are securely authenticated!")
