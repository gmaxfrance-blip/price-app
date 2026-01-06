import streamlit as st
from st_supabase_connection import SupabaseConnection
from streamlit_option_menu import option_menu
import pandas as pd
from datetime import date
import plotly.express as px
import io 

# --- 1. CONFIGURATION & RESPONSIVE UI ---
LOGO_URL = "https://raw.githubusercontent.com/gmaxfrance-blip/price-app/a423573672203bc38f5fbcf5f5a56ac18380ebb3/dp%20logo.png"
PINK = "#ff1774"
DARK_BG = "#0e1117"
CARD_BG = "#262730"

st.set_page_config(page_title="Gmax Management", page_icon=LOGO_URL, layout="wide")
conn = st.connection("supabase", type=SupabaseConnection)

# --- 2. BRUTALLY CLEAN CSS (MOBILE & PC FLEXIBLE) ---
st.markdown(f"""
    <style>
    /* Flexible Container */
    .stApp {{ background-color: {DARK_BG}; }}
    
    /* Center Logo & Make it Responsive */
    .logo-container {{ display: flex; justify-content: center; padding: 10px; }}
    .logo-container img {{ max-width: 100%; height: auto; width: 120px; }}

    /* Responsive Grid for Forms */
    div[data-testid="stForm"] {{ 
        background-color: {CARD_BG}; 
        padding: 1.5rem; 
        border-radius: 8px; 
        border: 1px solid #333; 
    }}

    /* Mobile Text Adjustments */
    @media (max-width: 640px) {{
        h1, h2, h3 {{ font-size: 1.2rem !important; }}
        .stMetric label {{ font-size: 0.8rem !important; }}
    }}

    /* Professional Inputs */
    .stSelectbox div, .stNumberInput input, .stDateInput input, .stTextInput input {{
        background-color: #3b3d4a !important;
        color: white !important;
        border: 1px solid #555 !important;
    }}
    
    h1, h2, h3, h4, p, label {{ color: #ffffff !important; font-family: 'Arial', sans-serif; }}
    
    div.stButton > button {{ 
        background-color: {PINK} !important; 
        color: white !important; 
        border-radius: 4px; 
        width: 100%; 
        font-weight: bold; 
        border: none;
    }}
    
    #MainMenu, footer, header {{visibility: hidden;}}
    </style>
    """, unsafe_allow_html=True)

# --- 3. DATA LOGIC ---
@st.cache_data(ttl=600)
def get_master_data():
    """Live master list retrieval."""
    p = conn.table("products").select("name").execute()
    d = conn.table("distributors").select("name").execute()
    return sorted([r['name'] for r in p.data]), sorted([r['name'] for r in d.data])

def get_logs():
    """Live transaction log retrieval."""
    res = conn.table("price_logs").select("*").order("date", desc=True).execute()
    df = pd.DataFrame(res.data)
    if not df.empty:
        df['date'] = pd.to_datetime(df['date'])
        if 'tax_rate' not in df.columns: df['tax_rate'] = "No tax"
    return df

# --- 4. AUTHENTICATION ---
if "role" not in st.session_state:
    st.markdown(f'<div class="logo-container"><img src="{LOGO_URL}"></div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        pwd = st.text_input("Access Key", type="password")
        if st.button("Login"):
            if pwd == "admin123": st.session_state.role = "admin"
            elif pwd == "boss456": st.session_state.role = "viewer"
            else: st.error("Access Denied")
            if "role" in st.session_state: st.rerun()
    st.stop()

# --- 5. NAVIGATION ---
with st.sidebar:
    st.markdown(f'<div class="logo-container"><img src="{LOGO_URL}"></div>', unsafe_allow_html=True)
    opts = ["Entry", "Register", "Manage", "Analyser", "Export"] if st.session_state.role == "admin" else ["Analyser", "Export"]
    selected = option_menu(None, opts, icons=["plus", "list", "pencil", "search", "download"], default_index=0)
    if st.button("Logout"):
        st.session_state.clear()
        st.rerun()

p_list, d_list = get_master_data()
st.markdown(f'<div class="logo-container"><img src="{LOGO_URL}"></div>', unsafe_allow_html=True)

# --- PAGE: ENTRY ---
if selected == "Entry":
    st.markdown("<h3 style='text-align: center;'>New Price Entry</h3>", unsafe_allow_html=True)
    with st.form("entry_form", clear_on_submit=True):
        p = st.selectbox("Product", [""] + p_list)
        d = st.selectbox("Distributor", [""] + d_list)
        pr = st.number_input("Price HT (€)", min_value=0.0, step=0.01)
        tx = st.selectbox("Tax %", ["5.5%", "20%", "No tax"])
        dt = st.date_input("Date", date.today())
        
        if st.form_submit_button("Submit Entry"):
            if p and d and pr > 0:
                conn.table("price_logs").insert({"product": p, "distributor": d, "price": pr, "tax_rate": tx, "date": str(dt)}).execute()
                st.success("Saved Successfully")
                st.cache_data.clear()
            else: st.error("All fields required")

# --- PAGE: REGISTER ---
elif selected == "Register":
    st.markdown("<h3 style='text-align: center;'>Register Management</h3>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    
    with c1:
        st.write("**New Product Name**")
        new_p = st.text_input("Type Product Name", key="np", label_visibility="collapsed")
        # Live Check Logic
        if new_p:
            if new_p in p_list: st.error(f"'{new_p}' is already registered.")
            else: st.success(f"'{new_p}' is available.")
        
        if st.button("Add Product"):
            if new_p and new_p not in p_list:
                conn.table("products").insert({"name": new_p}).execute()
                st.cache_data.clear()
                st.rerun()

        st.dataframe(pd.DataFrame(p_list, columns=["Registered Products"]), use_container_width=True, hide_index=True)
            
    with c2:
        st.write("**New Distributor Name**")
        new_d = st.text_input("Type Distributor Name", key="nd", label_visibility="collapsed")
        # Live Check Logic
        if new_d:
            if new_d in d_list: st.error(f"'{new_d}' is already registered.")
            else: st.success(f"'{new_d}' is available.")
            
        if st.button("Add Distributor"):
            if new_d and new_d not in d_list:
                conn.table("distributors").insert({"name": new_d}).execute()
                st.cache_data.clear()
                st.rerun()

        st.dataframe(pd.DataFrame(d_list, columns=["Registered Distributors"]), use_container_width=True, hide_index=True)

# --- PAGE: MANAGE ---
elif selected == "Manage":
    st.markdown("<h3 style='text-align: center;'>Database Management</h3>", unsafe_allow_html=True)
    df = get_logs()
    if not df.empty:
        df['date'] = df['date'].dt.date
        edited = st.data_editor(df.rename(columns={'tax_rate': 'Tax %'}), key="editor", num_rows="dynamic", use_container_width=True, hide_index=True,
                               column_config={
                                   "id": None, 
                                   "product": st.column_config.SelectboxColumn("Product", options=p_list, required=True),
                                   "distributor": st.column_config.SelectboxColumn("Distributor", options=d_list, required=True),
                                   "Tax %": st.column_config.SelectboxColumn("Tax %", options=["5.5%", "20%", "No tax"], required=True)
                               })
        if st.button("Commit Changes"):
            for idx, updates in st.session_state["editor"]["edited_rows"].items():
                if "Tax %" in updates: updates["tax_rate"] = updates.pop("Tax %")
                conn.table("price_logs").update(updates).eq("id", df.iloc[idx]["id"]).execute()
            st.success("Updated")
            st.cache_data.clear()
            st.rerun()

# --- PAGE: ANALYSER ---
elif selected == "Analyser":
    st.markdown("<h3 style='text-align: center;'>Price Analysis</h3>", unsafe_allow_html=True)
    target = st.selectbox("Search Product", [""] + p_list)
    
    if target:
        df = get_logs()
        df_sub = df[df['product'] == target].copy()
        
        if not df_sub.empty:
            min_price = df_sub['price'].min()
            # Find all distributors at the lowest price
            best_distributors = df_sub[df_sub['price'] == min_price]['distributor'].unique()
            
            st.markdown(f"""
            <div style='background-color:{CARD_BG}; padding:15px; border-radius:10px; border-left: 5px solid {PINK};'>
                <p style='margin:0; font-size:14px;'>BEST PRIX FOUND</p>
                <h2 style='margin:0; color:{PINK} !important;'>{min_price:.2f} €</h2>
                <p style='margin-top:10px; font-weight:bold;'>Available at: {", ".join(best_distributors)}</p>
            </div>
            """, unsafe_allow_html=True)
            
            st.write("---")
            st.write("**Full History for this Product**")
            df_sub['date_str'] = df_sub['date'].dt.strftime('%d-%m-%Y')
            st.dataframe(df_sub[['date_str', 'distributor', 'price', 'tax_rate']].sort_values('date', ascending=False), use_container_width=True, hide_index=True)

# --- PAGE: EXPORT ---
elif selected == "Export":
    st.markdown("<h3 style='text-align: center;'>Excel Export</h3>", unsafe_allow_html=True)
    df = get_logs()
    if not df.empty:
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
        st.download_button("Download Full Database (.xlsx)", data=buffer.getvalue(), file_name="Gmax_Database.xlsx", use_container_width=True)
