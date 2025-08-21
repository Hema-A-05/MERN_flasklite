import streamlit as st
import requests
import json
import pandas as pd

API_URL = "http://localhost:5000"

if 'token' not in st.session_state:
    st.session_state['token'] = None

st.set_page_config(layout="wide")

def login_form():
    st.header("Admin Login")
    with st.form("login_form"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        submit_button = st.form_submit_button("Login")

        if submit_button:
            payload = {"email": email, "password": password}
            try:
                response = requests.post(f"{API_URL}/login", json=payload)
                if response.status_code == 200:
                    token = response.json().get('token')
                    st.session_state['token'] = token
                    st.success("Login successful!")
                    st.experimental_rerun()
                else:
                    st.error(f"Login failed: {response.json().get('message')}")
            except requests.exceptions.ConnectionError:
                st.error("Could not connect to the backend. Please ensure the backend server is running.")

def dashboard():
    st.title("Admin Dashboard")
    st.markdown("---")

    # --- Add Agent Section ---
    with st.expander("Add New Agent"):
        with st.form("add_agent_form"):
            name = st.text_input("Name")
            email = st.text_input("Email")
            mobile = st.text_input("Mobile Number")
            password = st.text_input("Password", type="password")
            add_agent_button = st.form_submit_button("Add Agent")

            if add_agent_button:
                payload = {"name": name, "email": email, "mobile": mobile, "password": password}
                headers = {"x-access-token": st.session_state['token']}
                response = requests.post(f"{API_URL}/agents", json=payload, headers=headers)
                if response.status_code == 201:
                    st.success("Agent added successfully!")
                else:
                    st.error(f"Error adding agent: {response.json().get('message')}")

    # --- Upload CSV Section ---
    st.markdown("---")
    with st.expander("Upload and Distribute CSV"):
        uploaded_file = st.file_uploader("Choose a file (CSV, XLSX, XLS)", type=["csv", "xlsx", "xls"])
        upload_button = st.button("Distribute Tasks")

        if upload_button and uploaded_file is not None:
            files = {'file': uploaded_file.getvalue()}
            headers = {"x-access-token": st.session_state['token']}

            try:
                response = requests.post(f"{API_URL}/upload-csv", files=files, headers=headers)
                if response.status_code == 200:
                    st.success("Tasks distributed successfully!")
                    st.json(response.json()['distributed_lists'])
                else:
                    st.error(f"Error distributing tasks: {response.json().get('message')}")
            except Exception as e:
                st.error(f"An error occurred: {e}")

    # --- Display Distributed Lists ---
    st.markdown("---")
    st.header("Distributed Lists")
    if st.button("Refresh Lists"):
        headers = {"x-access-token": st.session_state['token']}
        response = requests.get(f"{API_URL}/distributed-lists", headers=headers)
        if response.status_code == 200:
            lists = response.json()
            for item in lists:
                st.subheader(f"Agent ID: {item['agent_id']}")
                df = pd.DataFrame(item['tasks'])
                st.dataframe(df)
                st.write(f"Date: {item['upload_date']}")
        else:
            st.error("Failed to retrieve distributed lists.")

# --- Main App Logic ---
if st.session_state['token']:
    dashboard()
else:
    login_form()