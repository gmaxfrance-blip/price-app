import streamlit as st
from st_supabase_connection import SupabaseConnection
import pandas as pd
from datetime import date

# --- 1. CLOUD CONNECTION ---
# Connects to your permanent Supabase vault
conn = st.connection("supabase", type=SupabaseConnection)

# --- 2. PINK MINIMAL UI ---
st.set_page_config(page_title="Gmax Prix Distributors", layout="wide")
st.markdown("""
    <style>
    .stButton>button { background-color: #f1774c; color: white; border-radius: 6px; width: 100%; border: none; }
    .stTabs [aria-selected="true"] { background-color: #f1774c !important; color: white !important; }
    h1, h2, h3 { color: #f1774c; }
    .stSelectbox label, .stNumberInput label { color: #f1774c; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. ACCESS CONTROL ---
if "role" not in st.session_state:
    st.title("🔐 Gmax Prix Login")
    pwd = st.text_input("Password", type="password", placeholder="Enter Password...")
    if st.button("Login"):
        if pwd == "admin123":
            st.session_state.role = "admin"
            st.rerun()
        elif pwd == "boss456":
            st.session_state.role = "viewer"
            st.rerun()
        else: st.error("Wrong Password")
    st.stop()

st.title("💗 Gmax Prix Distributors")

# --- 4. TABS NAVIGATION ---
tabs = ["📥 Entry", "🔍 Analyser"]
if st.session_state.role == "admin": tabs += ["📝 Register", "✏️ Manage"]
t1, t2, t3, t4 = st.tabs(tabs + ([""] * (4-len(tabs))))

# FETCH MASTER DATA (Updates automatically on rerun)
prods = conn.table("products").select("name").execute()
dists = conn.table("distributors").select("name").execute()
p_names = [r['name'] for r in prods.data]
d_names = [r['name'] for r in dists.data]

# TAB 1: DATA ENTRY
with t1:
    with st.form("entry", clear_on_submit=True):
        c1, c2 = st.columns(2)
        p = c1.selectbox("Product", ["Choose Product..."] + p_names)
        d = c1.selectbox("Distributor", ["Choose Distributor..."] + d_names)
        pr = c2.number_input("Price ($)", min_value=0.0, step=0.01)
        dt = c2.date_input("Date", date.today())
        if st.form_submit_button("Submit Entry"):
            if p != "Choose Product..." and d != "Choose Distributor...":
                conn.table("price_logs").insert({"product": p, "distributor": d, "price": pr, "date": str(dt)}).execute()
                st.success("Saved to Cloud!")
            else: st.error("Please select a Product and Distributor")
    
    st.write("### Recent Pricing Activity")
    hist = conn.table("price_logs").select("*").order("date", desc=True).limit(10).execute()
    st.dataframe(pd.DataFrame(hist.data), use_container_width=True, hide_index=True)

# TAB 2: ANALYSER
with t2:
    search_p = st.selectbox("Search Item History", ["Choose Product..."] + p_names)
    if search_p != "Choose Product...":
        data = conn.table("price_logs").select("*").eq("product", search_p).execute()
        df = pd.DataFrame(data.data)
        if not df.empty:
            min_p = df['price'].min()
            best_options = df[df['price'] == min_p]
            st.write("### 🏆 Best Found Price(s)")
            cols = st.columns(len(best_options))
            for i, row in enumerate(best_options.itertuples()):
                cols[i].metric(row.distributor, f"${row.price}", f"Date: {row.date}")
            st.dataframe(df.sort_values("date", ascending=False), use_container_width=True, hide_index=True)

# TAB 3: REGISTER (ADMIN ONLY)
if st.session_state.role == "admin":
    with t3:
        col_reg1, col_reg2 = st.columns(2)
        
        # --- PRODUCT SECTION ---
        with col_reg1:
            st.subheader("Register Products")
            with st.form("reg_p", clear_on_submit=True):
                np = st.text_input("New Product Name")
                if st.form_submit_button("Add Product") and np:
                    conn.table("products").insert({"name": np}).execute()
                    st.success(f"Registered {np}")
                    st.rerun() # Forces the table below to refresh immediately
            
            # AUTOMATIC TABLE LISTING
            st.write("**Registered Products List:**")
            if p_names:
                st.dataframe(pd.DataFrame(p_names, columns=["Product Name"]), use_container_width=True, hide_index=True)
            else:
                st.info("No products registered yet.")

        # --- DISTRIBUTOR SECTION ---
        with col_reg2:
            st.subheader("Register Distributors")
            with st.form("reg_d", clear_on_submit=True):
                nd = st.text_input("New Distributor Name")
                if st.form_submit_button("Add Distributor") and nd:
                    conn.table("distributors").insert({"name": nd}).execute()
                    st.success(f"Registered {nd}")
                    st.rerun() # Forces the table below to refresh immediately
            
            # AUTOMATIC TABLE LISTING
            st.write("**Registered Distributors List:**")
            if d_names:
                st.dataframe(pd.DataFrame(d_names, columns=["Distributor Name"]), use_container_width=True, hide_index=True)
            else:
                st.info("No distributors registered yet.")

# TAB 4: MANAGE (ADMIN ONLY)
if st.session_state.role == "admin":
    with t4:
        st.subheader("Delete Pricing Logs")
        all_logs = conn.table("price_logs").select("*").execute()
        df_all = pd.DataFrame(all_logs.data)
        if not df_all.empty:
            del_id = st.selectbox("Select ID to Delete", df_all['id'].tolist())
            if st.button("Delete Entry Permanently", type="primary"):
                conn.table("price_logs").delete().eq("id", del_id).execute()
                st.success("Deleted!")
                st.rerun()
            st.dataframe(df_all, use_container_width=True)
