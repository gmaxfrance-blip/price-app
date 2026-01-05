import streamlit as st
from st_supabase_connection import SupabaseConnection
from streamlit_option_menu import option_menu
import pandas as pd
from datetime import date
import plotly.express as px
import io 

# --- 1. CONFIGURATION ---
LOGO_URL = "https://raw.githubusercontent.com/gmaxfrance-blip/price-app/a423573672203bc38f5fbcf5f5a56ac18380ebb3/dp%20logo.png"
PINK = "#ff1774"
DARK_BG = "#0e1117"
CARD_BG = "#262730"
INPUT_BG = "#3b3d4a"

st.set_page_config(page_title="Gmax Management", page_icon=LOGO_URL, layout="wide")
conn = st.connection("supabase", type=SupabaseConnection)

# --- 2. CSS THEME (DARK & PROFESSIONAL) ---
st.markdown(f"""
    <style>
    .stApp {{ background-color: {DARK_BG}; }}
    .logo-container {{ display: flex; justify-content: center; margin-bottom: 20px; }}
    
    .stSelectbox div, .stNumberInput input, .stDateInput input, .stTextInput input {{
        background-color: {INPUT_BG} !important;
        color: white !important;
        border: 1px solid #555 !important;
    }}
    
    div[data-testid="stForm"] {{ 
        background-color: {CARD_BG}; 
        padding: 25px; 
        border-radius: 8px; 
        border: 1px solid #333; 
    }}
    
    h1, h2, h3, h4, p, label {{ color: #ffffff !important; font-family: 'Arial', sans-serif; }}
    
    div.stButton > button {{ 
        background-color: {PINK} !important; 
        color: white !important; 
        border-radius: 4px; 
        width: 100%; 
        font-weight: bold; 
        border: none; 
        padding: 10px;
    }}
    
    #MainMenu, footer, header {{visibility: hidden;}}
    </style>
    """, unsafe_allow_html=True)

# --- 3. DATA FUNCTIONS ---
@st.cache_data(ttl=600)
def get_master_data():
    """Loads Products & Distributors with caching for speed."""
    p = conn.table("products").select("name").execute()
    d = conn.table("distributors").select("name").execute()
    return sorted([r['name'] for r in p.data]), sorted([r['name'] for r in d.data])

def get_logs():
    """Fetches records from the database."""
    res = conn.table("price_logs").select("*").order("date", desc=True).execute()
    df = pd.DataFrame(res.data)
    if not df.empty:
        df['date'] = pd.to_datetime(df['date'])
        if 'tax_rate' not in df.columns:
            df['tax_rate'] = "No tax"
    return df

# --- 4. LOGIN SYSTEM ---
if "role" not in st.session_state:
    st.markdown(f'<div class="logo-container"><img src="{LOGO_URL}" width="150"></div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1, 1])
    with c2:
        pwd = st.text_input("Password", type="password", label_visibility="collapsed")
        if st.button("Access"):
            if pwd == "admin123": st.session_state.role = "admin"
            elif pwd == "boss456": st.session_state.role = "viewer"
            else: st.error("Invalid Key")
            if "role" in st.session_state: st.rerun()
    st.stop()

# --- 5. NAVIGATION ---
with st.sidebar:
    st.markdown(f'<div class="logo-container"><img src="{LOGO_URL}" width="100"></div>', unsafe_allow_html=True)
    opts = ["Entry", "Register", "Manage", "Analyser", "Export"] if st.session_state.role == "admin" else ["Analyser", "Export"]
    selected = option_menu("Menu", opts, icons=["plus-square", "archive", "pencil", "graph-up", "download"], default_index=0)
    if st.button("Log Out"):
        st.session_state.clear()
        st.rerun()

p_list, d_list = get_master_data()
tax_options = ["5.5%", "20%", "No tax"]
st.markdown(f'<div class="logo-container"><img src="{LOGO_URL}" width="120"></div>', unsafe_allow_html=True)

# --- PAGE: ENTRY ---
if selected == "Entry":
    st.markdown("<h3 style='text-align: center;'>New Price Entry</h3>", unsafe_allow_html=True)
    with st.form("entry_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        p = c1.selectbox("Product", [""] + p_list)
        d = c2.selectbox("Distributor", [""] + d_list)
        
        c3, c4, c5 = st.columns([2, 1, 2])
        pr = c3.number_input("Price HT", min_value=0.0, step=0.01, format="%.2f")
        tx = c4.selectbox("Tax %", tax_options)
        dt = c5.date_input("Date", date.today())
        
        if st.form_submit_button("Submit Entry"):
            if p == "" or d == "" or pr <= 0:
                st.error("Please fill all fields.")
            else:
                conn.table("price_logs").insert({"product": p, "distributor": d, "price": pr, "tax_rate": tx, "date": str(dt)}).execute()
                st.success("Record Saved")
                st.cache_data.clear()
    
    st.write("### Recent Entries")
    df_recent = get_logs()
    if not df_recent.empty:
        df_recent['date_display'] = df_recent['date'].dt.strftime('%d-%m-%Y')
        st.dataframe(df_recent[['date_display', 'product', 'distributor', 'price', 'tax_rate']].rename(columns={'tax_rate': 'Tax %'}).head(10), 
                     use_container_width=True, hide_index=True)

# --- PAGE: REGISTER ---
elif selected == "Register":
    st.markdown("<h3 style='text-align: center;'>Register Items</h3>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        st.write("#### Products")
        # Searchable Dropdown for checking existence
        st.selectbox("Search/View Registered Products", [""] + p_list, key="search_p")
        new_p = st.text_input("Add New Product Name", key="np")
        if st.button("Save Product"):
            if new_p and new_p not in p_list:
                conn.table("products").insert({"name": new_p}).execute()
                st.cache_data.clear()
                st.rerun()
            elif new_p in p_list: st.warning("Product already registered.")
            
    with c2:
        st.write("#### Distributors")
        # Searchable Dropdown for checking existence
        st.selectbox("Search/View Registered Distributors", [""] + d_list, key="search_d")
        new_d = st.text_input("Add New Distributor Name", key="nd")
        if st.button("Save Distributor"):
            if new_d and new_d not in d_list:
                conn.table("distributors").insert({"name": new_d}).execute()
                st.cache_data.clear()
                st.rerun()
            elif new_d in d_list: st.warning("Distributor already registered.")

# --- PAGE: MANAGE ---
elif selected == "Manage":
    st.markdown("<h3 style='text-align: center;'>Manage Data</h3>", unsafe_allow_html=True)
    df = get_logs()
    if not df.empty:
        df['date'] = df['date'].dt.date
        df_display = df.rename(columns={'tax_rate': 'Tax %'})
        
        edited = st.data_editor(df_display, key="editor", num_rows="dynamic", use_container_width=True, hide_index=True,
                               column_config={
                                   "id": None, 
                                   "product": st.column_config.SelectboxColumn("Product", options=p_list, required=True),
                                   "distributor": st.column_config.SelectboxColumn("Distributor", options=d_list, required=True),
                                   "date": st.column_config.DateColumn(format="DD-MM-YYYY"),
                                   "Tax %": st.column_config.SelectboxColumn("Tax %", options=tax_options, required=True)
                               })
        if st.button("Commit Changes"):
            for row in st.session_state["editor"]["deleted_rows"]:
                conn.table("price_logs").delete().eq("id", df.iloc[row]["id"]).execute()
            for idx, updates in st.session_state["editor"]["edited_rows"].items():
                if "date" in updates: updates["date"] = str(updates["date"])
                if "Tax %" in updates: updates["tax_rate"] = updates.pop("Tax %")
                conn.table("price_logs").update(updates).eq("id", df.iloc[idx]["id"]).execute()
            st.success("Database Updated")
            st.cache_data.clear()
            st.rerun()

# --- PAGE: ANALYSER ---
elif selected == "Analyser":
    st.markdown("<h3 style='text-align: center;'>Price Analyser</h3>", unsafe_allow_html=True)
    target = st.selectbox("Search Product", [""] + p_list)
    if target:
        df = get_logs()
        df_sub = df[df['product'] == target].copy()
        if not df_sub.empty:
            st.metric("Lowest Price Found", f"{df_sub['price'].min():.2f} €")
            df_sub['date_display'] = df_sub['date'].dt.strftime('%d-%m-%Y')
            history_df = df_sub.sort_values('date', ascending=False).rename(columns={'tax_rate': 'Tax %'})
            st.dataframe(history_df[['date_display', 'distributor', 'price', 'Tax %']], use_container_width=True, hide_index=True)
            
            fig = px.bar(df_sub.groupby("distributor")['price'].min().reset_index(), x="distributor", y="price", color_discrete_sequence=[PINK])
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="white")
            st.plotly_chart(fig, use_container_width=True)

# --- PAGE: EXPORT ---
elif selected == "Export":
    st.markdown("<h3 style='text-align: center;'>Export Data</h3>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    start = c1.date_input("Start Date", date(2025, 1, 1))
    end = c2.date_input("End Date", date.today())
    if st.button("Download Excel Report"):
        df = get_logs()
        mask = (df['date'].dt.date >= start) & (df['date'].dt.date <= end)
        df_f = df[mask].sort_values("date", ascending=False).rename(columns={'tax_rate': 'Tax %'})
        if not df_f.empty:
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df_f[['date', 'product', 'distributor', 'price', 'Tax %']].to_excel(writer, index=False)
            st.download_button("Click to Download", data=buffer.getvalue(), file_name="Gmax_Report.xlsx", use_container_width=True)
