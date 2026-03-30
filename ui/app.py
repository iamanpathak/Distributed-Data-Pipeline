import streamlit as st
import requests
import pandas as pd
import time

API_URL = "http://api:8000"

st.set_page_config(page_title="Data Pipeline UI", layout="wide")

st.markdown("""
<style>
    /* Clean normal green button */
    div[data-testid="stDownloadButton"] button {
        border: 1px solid rgba(250, 250, 250, 0.2) !important;
        background-color: transparent !important;
        transition: 0.3s;
    }
    div[data-testid="stDownloadButton"] button p {
        color: #28a745 !important; /* Normal Green Color */
        font-weight: bold !important;
    }
    div[data-testid="stDownloadButton"] button:hover {
        border: 1px solid #28a745 !important;
    }
</style>
""", unsafe_allow_html=True)

# --- SIDEBAR ---
with st.sidebar:
    st.title("Control Panel")
    st.markdown("Send tasks to the Celery workers.")
    st.divider()
    
    st.subheader("Submit a New Job")
    data_size = st.slider("Data Size (MB/Seconds)", min_value=1, max_value=10, value=5)
    
    if st.button("Fire Job!", use_container_width=True):
        with st.spinner("Sending to Queue..."):
            try:
                response = requests.post(f"{API_URL}/submit-job?data_size={data_size}")
                if response.status_code == 200:
                    job_id = response.json().get("job_id")
                    st.success(f"Job Sent! \nID: `{job_id[:8]}...`")
                elif response.status_code == 429:
                    st.error(f"{response.json().get('detail')}")
                else:
                    st.error(f"Oops! API Error: {response.status_code}")
            except Exception:
                st.error("Worker API is sleeping!")

# --- MAIN DASHBOARD ---
st.title("Distributed Data Pipeline")
st.markdown("Real-time monitoring of PostgreSQL Vault and Celery Workers.")
st.divider()

try:
    response = requests.get(f"{API_URL}/all-jobs")
    data = response.json().get("jobs_history", [])
except:
    data = []

if not data:
    st.info("The Vault is empty! Fire some jobs.")
else:
    df = pd.DataFrame(data)
    
    st.subheader("Live System Metrics")
    m1, m2, m3 = st.columns(3)
    with m1: st.metric("Total Jobs Processed", len(df))
    with m2: st.metric("Total Data Handled", f"{df[df['data_size'] > 0]['data_size'].sum()} MB")
    with m3: st.metric("System Health", f"{(len(df[df['status'] == 'SUCCESS']) / len(df)) * 100:.0f}%")
        
    st.divider()
    
    col_graph, col_table = st.columns([1.5, 1])
    
    with col_graph:
        # Adjusted column ratio to push the button further right
        g_col1, g_col2 = st.columns([6, 1])
        with g_col1: st.subheader("Processing Load Graph")
        with g_col2:
            if st.button("Refresh", use_container_width=True):
                st.toast("Dashboard Refreshed! 🔄") 
                time.sleep(1)
                st.rerun()
                
        # Render the processing load (Ignoring negative error test values)
        st.bar_chart(
            df[df['data_size'] > 0], 
            x="job_id", 
            y="data_size", 
            x_label="Job ID", 
            y_label="Data Size (MB)",
            height=400
        )
        
    with col_table:
        # Adjusted column ratio to push the export button further right
        t_col1, t_col2 = st.columns([3, 1])
        with t_col1: st.subheader("Vault Records")
        with t_col2:
            csv_data = df.to_csv(index=False).encode('utf-8')
            st.download_button(label="Export CSV", data=csv_data, file_name="vault_report.csv", mime="text/csv", use_container_width=True)
            
        st.dataframe(df.iloc[::-1], use_container_width=True, height=400)