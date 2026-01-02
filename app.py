import streamlit as st
import sqlite3
import pandas as pd
from datetime import date

# --- 1. DATABASE ENGINE ---
def init_db():
    """Initializes the database and creates tables if they don't exist."""
    conn = sqlite3.connect('price_tracker.db')
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS products (name TEXT UNIQUE)')
    c.execute('CREATE TABLE IF NOT EXISTS distributors (name TEXT UNIQUE)')
    c.execute('''CREATE TABLE IF NOT EXISTS price_logs 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  product TEXT, 
                  distributor TEXT, 
                  price REAL, 
                  date DATE)''')
    conn.commit()
    conn.close()

def run_query(query, params=(), is_select=True):
    """Helper to run SQL queries safely."""
    conn = sqlite3.connect('price_tracker.db')
    if is_select:
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        return df
    else:
        curr = conn.cursor()
        curr.execute(query, params)
        conn.commit()
        conn.close()

# Start the database
init_db()

# --- 2. PROFESSIONAL UI CONFIG ---
st.set_page_config(page_title="Price Intel Pro", layout="wide")

st.markdown("""
    <style>
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { 
        background-color: #f0f2f6; 
        border-radius: 5px; 
        padding: 10px 20px;
    }
    .stTabs [aria-selected="true"] { 
        background-color: #007bff !important; 
        color: white !important; 
    }
    </style>
    """, unsafe_allow_html=True)

st.title("📊 Price Intel Dashboard")
st.caption("Permanent Price Tracking & Distributor Comparison")

# --- 3. 5 TABS NAVIGATION ---
t1, t2, t3, t4, t5 = st.tabs([
    "📥 Data Entry", 
    "📝 Register Items", 
    "🔍 Price Analyser", 
    "✏️ Edit/Manage", 
    "📂 Export History"
])

# --- TAB 1: DATA ENTRY ---
with t1:
    st.subheader("Log New Price Entry")
    prods_df = run_query("SELECT name FROM products")
    dists_df = run_query("SELECT name FROM distributors")
    
    if prods_df.empty or dists_df.empty:
        st.info("⚠️ Please go to 'Register Items' first to add products and distributors.")
    else:
        # 'clear_on_submit=True' ensures fields disappear after adding
        with st.form("entry_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                p_val = st.selectbox("Product", prods_df['name'])
                d_val = st.selectbox("Distributor", dists_df['name'])
            with col2:
                prc_val = st.number_input("Price ($)", min_value=0.0, format="%.2f")
                dt_val = st.date_input("Date", date.today())
            
            if st.form_submit_button("Submit Price"):
                run_query("INSERT INTO price_logs (product, distributor, price, date) VALUES (?,?,?,?)", 
                          (p_val, d_val, prc_val, dt_val), is_select=False)
                st.success(f"Successfully recorded ${prc_val} for {p_val}")

# --- TAB 2: REGISTER DATA ---
with t2:
    st.subheader("Master List Management")
    c1, c2 = st.columns(2)
    with c1:
        with st.form("prod_form", clear_on_submit=True):
            new_p = st.text_input("New Product Name")
            if st.form_submit_button("Add Product") and new_p:
                try:
                    run_query("INSERT INTO products VALUES (?)", (new_p,), is_select=False)
                    st.success(f"Registered {new_p}")
                except: st.error("Exists!")
    with c2:
        with st.form("dist_form", clear_on_submit=True):
            new_d = st.text_input("New Distributor Name")
            if st.form_submit_button("Add Distributor") and new_d:
                try:
                    run_query("INSERT INTO distributors VALUES (?)", (new_d,), is_select=False)
                    st.success(f"Registered {new_d}")
                except: st.error("Exists!")

# --- TAB 3: PRICE ANALYSER ---
with t3:
    st.subheader("Better Price Finder")
    all_p = run_query("SELECT name FROM products")['name'].tolist()
    if all_p:
        target = st.selectbox("Search Product", all_p)
        history = run_query("SELECT distributor, price, date FROM price_logs WHERE product=? ORDER BY price ASC", (target,))
        
        if not history.empty:
            low_p = history.iloc[0]['price']
            low_d = history.iloc[0]['distributor']
            st.metric("Lowest Price Found", f"${low_p}", f"Supplier: {low_d}")
            st.write("#### Price Trend")
            st.line_chart(history, x='date', y='price')
            st.dataframe(history, use_container_width=True)
        else:
            st.warning("No price logs found for this item.")

# --- TAB 4: EDIT/DELETE ---
with t4:
    st.subheader("Manage Logs")
    logs = run_query("SELECT * FROM price_logs ORDER BY date DESC")
    if not logs.empty:
        selected_id = st.selectbox("Select ID to Action", logs['id'].tolist())
        current = logs[logs['id'] == selected_id].iloc[0]
        
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("Delete Entry Permanently", type="primary"):
                run_query("DELETE FROM price_logs WHERE id=?", (selected_id,), is_select=False)
                st.rerun()
        st.dataframe(logs, use_container_width=True)

# --- TAB 5: EXPORT HISTORY (CHOICE A: DAILY BACKUP) ---
with t5:
    st.subheader("Download & Backup")
    all_logs = run_query("SELECT * FROM price_logs ORDER BY date DESC")
    
    if not all_logs.empty:
        col_start, col_end = st.columns(2)
        start_date = col_start.date_input("Start Date", date.today())
        end_date = col_end.date_input("End Date", date.today())
        
        # Filter data for export
        filtered_df = all_logs[(all_logs['date'] >= str(start_date)) & (all_logs['date'] <= str(end_date))]
        st.dataframe(filtered_df, use_container_width=True)
        
        # Choice A: Daily Backup Button
        csv = filtered_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Daily Backup (Excel CSV)", 
            data=csv, 
            file_name=f"price_report_{date.today()}.csv", 
            mime='text/csv'
        )
    else:
        st.info("No data available to export.")
