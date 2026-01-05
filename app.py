import streamlit as st
from st_supabase_connection import SupabaseConnection
import pandas as pd
from datetime import date
import plotly.express as px

# --- 1. CONFIGURATION ---
# We define the Logo URL first so we can use it in the page config
LOGO_URL = "https://raw.githubusercontent.com/gmaxfrance-blip/price-app/a423573672203bc38f5fbcf5f5a56ac18380ebb3/dp%20logo.png"
GMAX_PINK = "#ff1774"
ITEMS_PER_PAGE = 20

st.set_page_config(
    page_title="Gmax Prix", 
    page_icon=LOGO_URL,  # <--- YOUR LOGO IS HERE AS TAB ICON
    layout="wide"
)

# Connect to Supabase
conn = st.connection("supabase", type=SupabaseConnection)

# CSS for Speed & Look
st.markdown(f"""
    <style>
    .stApp {{ background-color: #ffffff; }}
    h1, h2, h3, .stMetric label {{ color: {GMAX_PINK} !important; font-weight: bold; }}
    div.stButton > button {{ background-color: {GMAX_PINK} !important; color: white !important; border-radius: 6px; border: none; }}
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    </style>
    """, unsafe_allow_html=True)

# --- 2. FAST DATA LOADING (CACHED) ---
@st.cache_data(ttl=600)
def get_master_lists():
    p = conn.table("products").select("name").execute()
    d = conn.table("distributors").select("name").execute()
    return sorted([r['name'] for r in p.data]), sorted([r['name'] for r in d.data])

def get_recent_logs():
    res = conn.table("price_logs").select("*").order("date", desc=True).execute()
    df = pd.DataFrame(res.data)
    if not df.empty:
        df['date'] = pd.to_datetime(df['date'])
    return df

# --- 3. LOGIN ---
if "role" not in st.session_state:
    c1, c2 = st.columns([1,2])
    with c1:
        st.image(LOGO_URL, width=100) # <--- LOGO ON LOGIN SCREEN
    with c2:
        st.title("🔐 Gmax Login")
        pwd = st.text_input("Enter Key", type="password")
        if st.button("Login"):
            if pwd == "admin123": st.session_state.role = "admin"
            elif pwd == "boss456": st.session_state.role = "viewer"
            else: st.error("Access Denied")
            if "role" in st.session_state: st.rerun()
    st.stop()

# --- 4. SIDEBAR MENU ---
# <--- LOGO AT TOP OF SIDEBAR
st.sidebar.image(LOGO_URL, width=120) 
st.sidebar.title("Navigation")

if st.session_state.role == "viewer":
    options = ["🔍 Analyser"]
else:
    options = ["📥 Entry", "📝 Register", "✏️ Manage", "🔍 Analyser"]

selected_page = st.sidebar.radio("Go to", options)

if st.sidebar.button("Logout"):
    st.session_state.clear()
    st.rerun()

# Load Data Once
p_names, d_names = get_master_lists()

# --- PAGE: ENTRY ---
if selected_page == "📥 Entry":
    st.title("📥 New Price Entry")
    
    with st.form("entry_form", clear_on_submit=True):
        c1, c2, c3, c4 = st.columns(4)
        p = c1.selectbox("Product", ["Choose..."] + p_names)
        d = c2.selectbox("Distributor", ["Choose..."] + d_names)
        pr = c3.number_input("Price HT (€)", min_value=0.0, step=0.01)
        dt = c4.date_input("Date", date.today())
        
        if st.form_submit_button("Save Entry"):
            if p != "Choose..." and d != "Choose...":
                conn.table("price_logs").insert({
                    "product": p, "distributor": d, "price": pr, "date": str(dt)
                }).execute()
                st.success("✅ Saved!")
                st.cache_data.clear()
                st.rerun()
            else:
                st.error("Please select Product & Distributor")

    st.write("---")
    st.subheader("Recent Entries")
    df = get_recent_logs()
    
    if not df.empty:
        fc1, fc2 = st.columns(2)
        fp = fc1.multiselect("Filter Product", p_names)
        fd = fc2.multiselect("Filter Distributor", d_names)
        
        if fp: df = df[df['product'].
