import streamlit as st
import sqlite3
import pandas as pd
from datetime import date

# 1. DATABASE ENGINE
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

# 2. UI DESIGN
st.set_page_config(page_title="Price Intel Pro", layout="wide")
st.title("📊 Price Intel Dashboard")

t1, t2, t3, t4 = st.tabs(["📥 Data Entry", "📝 Register Items", "🔍 Price Analyser", "✏️ Edit/Manage"])

# TAB 1: ENTRY
with t1:
    prods_df = run_query("SELECT name FROM products")
    dists_df = run_query("SELECT name FROM distributors")
    if prods_df.empty or dists_df.empty:
        st.info("Please register products/distributors first.")
    else:
        with st.form("entry_form"):
            p_val = st.selectbox("Product", prods_df['name'])
            d_val = st.selectbox("Distributor", dists_df['name'])
            prc_val = st.number_input("Price", min_value=0.0)
            dt_val = st.date_input("Date", date.today())
            if st.form_submit_button("Submit"):
                run_query("INSERT INTO price_logs (product, distributor, price, date) VALUES (?,?,?,?)", 
                          (p_val, d_val, prc_val, dt_val), False)
                st.success("Saved!")

# TAB 2: REGISTER
with t2:
    col1, col2 = st.columns(2)
    with col1:
        new_p = st.text_input("New Product")
        if st.button("Add Product"):
            run_query("INSERT INTO products VALUES (?)", (new_p,), False)
            st.rerun()
    with col2:
        new_d = st.text_input("New Distributor")
        if st.button("Add Distributor"):
            run_query("INSERT INTO distributors VALUES (?)", (new_d,), False)
            st.rerun()

# TAB 3: ANALYSER
with t3:
    all_p = run_query("SELECT name FROM products")['name'].tolist()
    if all_p:
        target = st.selectbox("Search Item", all_p)
        history = run_query("SELECT distributor, price, date FROM price_logs WHERE product=? ORDER BY price ASC", (target,))
        if not history.empty:
            st.metric("Best Price", f"${history.iloc[0]['price']}", history.iloc[0]['distributor'])
            st.dataframe(history, use_container_width=True)
            st.line_chart(history, x='date', y='price')

# TAB 4: EDIT
with t4:
    logs = run_query("SELECT * FROM price_logs ORDER BY date DESC")
    if not logs.empty:
        selected_id = st.selectbox("ID to Delete", logs['id'].tolist())
        if st.button("Delete Entry", type="primary"):
            run_query("DELETE FROM price_logs WHERE id=?", (selected_id,), False)
            st.rerun()
        st.dataframe(logs, use_container_width=True)