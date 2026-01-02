import streamlit as st
from st_supabase_connection import SupabaseConnection
import pandas as pd
from datetime import date

# --- 1. CLOUD CONNECTION ---
conn = st.connection("supabase", type=SupabaseConnection)

# --- 2. UI BRANDING & DYNAMIC COLOR (#ff1774) ---
LOGO_URL = "https://raw.githubusercontent.com/gmaxfrance-blip/price-app/a423573672203bc38f5fbcf5f5a56ac18380ebb3/dp%20logo.png"

st.set_page_config(
    page_title="Gmax Prix Distributors", 
    page_icon=LOGO_URL, 
    layout="wide"
)

# Custom CSS for the specific #ff1774 Pink Theme
st.markdown(f"""
    <style>
    /* Headers and Metrics */
    h1, h2, h3, .stMetric label {{ color: #ff1774 !important; font-weight: bold; }}
    
    /* Buttons */
    div.stButton > button {{
        background-color: #ff1774 !important;
        color: white !important;
        border-radius: 8px !important;
        border: none !important;
        font-weight: bold;
    }}
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {{ gap: 8px; }}
    .stTabs [aria-selected="true"] {{
        background-color: #ff1774 !important;
        color: white !important;
    }}
    
    /* Sidebar and Input Labels */
    .stSelectbox label, .stNumberInput label, .stDateInput label {{ 
        color: #ff1774; 
        font-weight: 600; 
    }}
    </style>
    """, unsafe_allow_html=True)

# --- 3. ACCESS CONTROL ---
if "role" not in st.session_state:
    st.image(LOGO_URL, width=150)
    st.title("Gmax Prix Login")
    pwd = st.text_input("Security Key", type="password", placeholder="Enter Password...")
    if st.button("Sign In"):
        if pwd == "admin123":
            st.session_state.role = "admin"
            st.rerun()
        elif pwd == "boss456":
            st.session_state.role = "viewer"
            st.rerun()
        else: 
            st.error("Invalid Security Key")
    st.stop()

# --- 4. BRANDED HEADER ---
col_logo, col_title = st.columns([1, 6])
with col_logo:
    st.image(LOGO_URL, width=90)
with col_title:
    st.title("Gmax Prix Distributors")
    st.caption(f"Logged in as: {st.session_state.role.upper()}")

# --- 5. DYNAMIC TAB LOGIC ---
# If viewer (Boss), show only Analyser. If admin, show all.
if st.session_state.role == "viewer":
    tabs_list = ["🔍 Analyser"]
else:
    tabs_list = ["📥 Entry", "🔍 Analyser", "📝 Register", "✏️ Manage"]

active_tabs = st.tabs(tabs_list)

# DATA FETCHING (MASTER LISTS)
prods = conn.table("products").select("name").execute()
dists = conn.table("distributors").select("name").execute()
p_names = [r['name'] for r in prods.data]
d_names = [r['name'] for r in dists.data]

# --- TAB CONTENT ---

# ENTRY (ADMIN ONLY)
if st.session_state.role == "admin":
    with active_tabs[0]:
        with st.form("entry_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            p = c1.selectbox("Product", ["Choose Product..."] + p_names)
            d = c1.selectbox("Distributor", ["Choose Distributor..."] + d_names)
            pr = c2.number_input("Price ($)", min_value=0.0, step=0.01)
            dt = c2.date_input("Transaction Date", date.today())
            if st.form_submit_button("Save Price Log"):
                if p != "Choose Product..." and d != "Choose Distributor...":
                    conn.table("price_logs").insert({"product": p, "distributor": d, "price": pr, "date": str(dt)}).execute()
                    st.success("Entry synchronized to cloud!")
                else: 
                    st.error("Please select both Product and Distributor.")

# ANALYSER (AVAILABLE TO ALL)
# Adjust index based on role
analyser_idx = 0 if st.session_state.role == "viewer" else 1
with active_tabs[analyser_idx]:
    search_p = st.selectbox("Search Market Data", ["Choose Product..."] + p_names)
    if search_p != "Choose Product...":
        data = conn.table("price_logs").select("*").eq("product", search_p).execute()
        df = pd.DataFrame(data.data)
        if not df.empty:
            # Highlight Best Price
            min_p = df['price'].min()
            best = df[df['price'] == min_p]
            st.write("### 🏆 Market Leader(s)")
            cols = st.columns(len(best))
            for i, row in enumerate(best.itertuples()):
                cols[i].metric(row.distributor, f"${row.price}", f"Update: {row.date}")
            
            st.write("### Detailed Price History")
            st.dataframe(df.sort_values("date", ascending=False), use_container_width=True, hide_index=True)
        else: 
            st.info("No pricing records found for this item.")

# REGISTER (ADMIN ONLY)
if st.session_state.role == "admin":
    with active_tabs[2]:
        reg1, reg2 = st.columns(2)
        with reg1:
            with st.form("reg_p", clear_on_submit=True):
                np = st.text_input("New Product Name")
                if st.form_submit_button("Register Product") and np:
                    conn.table("products").insert({"name": np}).execute()
                    st.rerun()
            st.write("**Registered Products:**")
            st.dataframe(pd.DataFrame(p_names, columns=["Name"]), use_container_width=True)
        with reg2:
            with st.form("reg_d", clear_on_submit=True):
                nd = st.text_input("New Distributor Name")
                if st.form_submit_button("Register Distributor") and nd:
                    conn.table("distributors").insert({"name": nd}).execute()
                    st.rerun()
            st.write("**Registered Distributors:**")
            st.dataframe(pd.DataFrame(d_names, columns=["Name"]), use_container_width=True)

# MANAGE (ADMIN ONLY)
if st.session_state.role == "admin":
    with active_tabs[3]:
        all_logs = conn.table("price_logs").select("*").execute()
        df_all = pd.DataFrame(all_logs.data)
        if not df_all.empty:
            st.write("### Database Maintenance")
            del_id = st.selectbox("Select ID to Delete", df_all['id'].tolist())
            if st.button("Confirm Permanent Deletion", type="primary"):
                conn.table("price_logs").delete().eq("id", del_id).execute()
                st.rerun()
            st.dataframe(df_all, use_container_width=True)

# Sidebar Logout
st.sidebar.markdown("---")
if st.sidebar.button("Logout"):
    st.session_state.clear()
    st.rerun()
