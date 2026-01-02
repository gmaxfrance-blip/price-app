import streamlit as st
import sqlite3
import pandas as pd
from datetime import date

# --- 1. DATABASE ENGINE ---
def init_db():
    conn = sqlite3.connect('price_tracker.db')
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS products (name TEXT UNIQUE)')
    c.execute('CREATE TABLE IF NOT EXISTS distributors (name TEXT UNIQUE)')
    c.execute('''CREATE TABLE IF NOT EXISTS price_logs 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, product TEXT, distributor TEXT, price REAL, date DATE)''')
    conn.commit()
    conn.close()

def run_query(query, params=(), is_select=True):
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

init_db()

# --- 2. MINIMAL UI DESIGN ---
st.set_page_config(page_title="Price Intel Pro", layout="wide")
st.markdown("""
    <style>
    .main { background-color: #f9f9f9; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { background-color: #f1f1f1; border-radius: 4px; padding: 8px 16px; }
    .stTabs [aria-selected="true"] { background-color: #000000 !important; color: white !important; }
    </style>
    """, unsafe_allow_html=True)

st.title("📊 Price Intel")
st.caption("Minimalist Distributor Tracking System")

t1, t2, t3, t4, t5 = st.tabs(["📥 Entry", "📝 Register", "🔍 Analyser", "✏️ Manage", "📂 Export"])

# --- TAB 1: DATA ENTRY ---
with t1:
    prods = run_query("SELECT name FROM products")
    dists = run_query("SELECT name FROM distributors")
    if prods.empty or dists.empty:
        st.info("Please register items first.")
    else:
        with st.form("entry", clear_on_submit=True):
            col1, col2 = st.columns(2)
            p = col1.selectbox("Product", prods['name'])
            d = col1.selectbox("Distributor", dists['name'])
            pr = col2.number_input("Price", min_value=0.0, format="%.2f")
            dt = col2.date_input("Date", date.today())
            if st.form_submit_button("Submit Price"):
                run_query("INSERT INTO price_logs (product, distributor, price, date) VALUES (?,?,?,?)", (p, d, pr, dt), False)
                st.success("Logged!")

# --- TAB 2: REGISTER (With Tables) ---
with t2:
    st.subheader("Master Lists")
    c1, c2 = st.columns(2)
    with c1:
        with st.form("reg_p", clear_on_submit=True):
            np = st.text_input("New Product")
            if st.form_submit_button("Add Product") and np:
                try: run_query("INSERT INTO products VALUES (?)", (np,), False)
                except: st.error("Exists")
        st.write("**Registered Products:**")
        st.dataframe(run_query("SELECT name as 'Product Name' FROM products"), use_container_width=True, hide_index=True)

    with c2:
        with st.form("reg_d", clear_on_submit=True):
            nd = st.text_input("New Distributor")
            if st.form_submit_button("Add Distributor") and nd:
                try: run_query("INSERT INTO distributors VALUES (?)", (nd,), False)
                except: st.error("Exists")
        st.write("**Registered Distributors:**")
        st.dataframe(run_query("SELECT name as 'Distributor Name' FROM distributors"), use_container_width=True, hide_index=True)

# --- TAB 3: ANALYSER ---
with t3:
    all_p = run_query("SELECT name FROM products")['name'].tolist()
    if all_p:
        target = st.selectbox("Compare:", all_p)
        history = run_query("SELECT distributor, price, date FROM price_logs WHERE product=? ORDER BY price ASC", (target,))
        if not history.empty:
            st.metric("Best Price", f"${history.iloc[0]['price']}", history.iloc[0]['distributor'])
            st.line_chart(history, x='date', y='price')

# --- TAB 4: EDIT & MANAGE ---
with t4:
    st.subheader("Edit or Delete Logs")
    logs = run_query("SELECT * FROM price_logs ORDER BY date DESC")
    if not logs.empty:
        log_id = st.selectbox("Select ID to Edit/Delete", logs['id'].tolist())
        current = logs[logs['id'] == log_id].iloc[0]
        
        with st.expander(f"Edit Entry #{log_id}"):
            new_pr = st.number_input("Change Price", value=float(current['price']))
            new_dt = st.date_input("Change Date", pd.to_datetime(current['date']))
            col_eb1, col_eb2 = st.columns(2)
            if col_eb1.button("💾 Save Changes"):
                run_query("UPDATE price_logs SET price=?, date=? WHERE id=?", (new_pr, new_dt, log_id), False)
                st.success("Updated!")
                st.rerun()
            if col_eb2.button("🗑️ Delete Entry", type="primary"):
                run_query("DELETE FROM price_logs WHERE id=?", (log_id,), False)
                st.rerun()
        st.dataframe(logs, use_container_width=True, hide_index=True)

# --- TAB 5: EXPORT ---
with t5:
    st.subheader("Daily Backup")
    all_data = run_query("SELECT * FROM price_logs")
    if not all_data.empty:
        st.dataframe(all_data, use_container_width=True, hide_index=True)
        csv = all_data.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download Excel (CSV)", csv, f"backup_{date.today()}.csv", "text/csv")
