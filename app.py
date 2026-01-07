import streamlit as st
from st_supabase_connection import SupabaseConnection
from streamlit_option_menu import option_menu
import pandas as pd
from datetime import date, timedelta
import io 

# --- 1. CONFIGURATION ---
LOGO_URL = "https://raw.githubusercontent.com/gmaxfrance-blip/price-app/a423573672203bc38f5fbcf5f5a56ac18380ebb3/dp%20logo.png"
PINK = "#ff1774"
DARK_BG = "#0e1117"
CARD_BG = "#262730"

st.set_page_config(page_title="Gmax Management", page_icon=LOGO_URL, layout="wide")
conn = st.connection("supabase", type=SupabaseConnection)

# --- 2. CSS ---
st.markdown(f"""
    <style>
    .stApp {{ background-color: {DARK_BG}; }}
    .logo-container {{ display: flex; justify-content: center; padding: 10px; }}
    .logo-container img {{ max-width: 100%; height: auto; width: 120px; }}
    div[data-testid="stForm"] {{ background-color: {CARD_BG}; padding: 1.5rem; border-radius: 8px; border: 1px solid #333; }}
    .stSelectbox div, .stNumberInput input, .stDateInput input, .stTextInput input {{
        background-color: #3b3d4a !important; color: white !important; border: 1px solid #555 !important;
    }}
    h1, h2, h3, h4, p, label {{ color: #ffffff !important; font-family: 'Arial', sans-serif; }}
    div.stButton > button {{ 
        background-color: {PINK} !important; color: white !important; border-radius: 4px; width: 100%; font-weight: bold; border: none;
    }}
    #MainMenu, footer, header {{visibility: hidden;}}
    </style>
    """, unsafe_allow_html=True)

# --- 3. DATA ---
@st.cache_data(ttl=600)
def get_master_data():
    p = conn.table("products").select("name").execute()
    d = conn.table("distributors").select("name").execute()
    return sorted([r['name'] for r in p.data]), sorted([r['name'] for r in d.data])

def get_logs():
    res = conn.table("price_logs").select("*").order("date", desc=True).execute()
    df = pd.DataFrame(res.data)
    if not df.empty:
        df['date'] = pd.to_datetime(df['date']).dt.date
    return df

# --- 4. AUTH ---
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

# --- 5. NAV ---
with st.sidebar:
    st.markdown(f'<div class="logo-container"><img src="{LOGO_URL}"></div>', unsafe_allow_html=True)
    opts = ["Entry", "Register", "Manage", "Analyser", "Export"] if st.session_state.role == "admin" else ["Analyser", "Export"]
    selected = option_menu(None, opts, icons=["plus", "list", "pencil", "search", "download"], default_index=0)
    if st.button("Logout"):
        st.session_state.clear()
        st.rerun()

p_list, d_list = get_master_data()
st.markdown(f'<div class="logo-container"><img src="{LOGO_URL}"></div>', unsafe_allow_html=True)

# --- ENTRY ---
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

# --- REGISTER (Autosuggest + New Add) ---
elif selected == "Register":
    st.markdown("<h3 style='text-align: center;'>Register Management</h3>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    
    with c1:
        st.write("**New Product Name**")
        # Text input allows brand new entries
        new_p = st.text_input("Type new product name...", key="np_input", help="Type 'coca' to see if variations exist below")
        
        # This acts as the "Dropdown" to show you what is already there
        if new_p:
            suggestions = [x for x in p_list if new_p.lower() in x.lower()]
            if suggestions:
                st.info(f"Existing similar items: {', '.join(suggestions[:5])}")
        
        if st.button("Add Product"):
            if new_p:
                if new_p.strip() in p_list:
                    st.warning("Already registered")
                else:
                    conn.table("products").insert({"name": new_p.strip()}).execute()
                    st.success(f"'{new_p}' Added")
                    st.cache_data.clear()
                    st.rerun()
        st.dataframe(pd.DataFrame(p_list, columns=["Registered Products"]), use_container_width=True, hide_index=True)
            
    with c2:
        st.write("**New Distributor Name**")
        new_d = st.text_input("Type new distributor name...", key="nd_input")
        
        if new_d:
            suggestions_d = [x for x in d_list if new_d.lower() in x.lower()]
            if suggestions_d:
                st.info(f"Existing similar: {', '.join(suggestions_d[:5])}")
                
        if st.button("Add Distributor"):
            if new_d:
                if new_d.strip() in d_list:
                    st.warning("Already registered")
                else:
                    conn.table("distributors").insert({"name": new_d.strip()}).execute()
                    st.success(f"'{new_d}' Added")
                    st.cache_data.clear()
                    st.rerun()
        st.dataframe(pd.DataFrame(d_list, columns=["Registered Distributors"]), use_container_width=True, hide_index=True)

# --- ANALYSER (Multiple Distributors Logic) ---
elif selected == "Analyser":
    st.markdown("<h3 style='text-align: center;'>Price Analysis</h3>", unsafe_allow_html=True)
    target = st.selectbox("Search Product", [""] + p_list)
    if target:
        df = get_logs()
        df_sub = df[df['product'] == target].copy()
        if not df_sub.empty:
            min_price = df_sub['price'].min()
            # Logic to find ALL distributors with this min price
            best_rows = df_sub[df_sub['price'] == min_price]
            all_best_dists = ", ".join(best_rows['distributor'].unique())
            
            st.markdown(f"""
            <div style='background-color:{CARD_BG}; padding:15px; border-radius:10px; border-left: 5px solid {PINK};'>
                <p style='margin:0; font-size:14px;'>BEST PRICE FOUND</p>
                <h2 style='margin:0; color:{PINK} !important;'>{min_price:.2f} €</h2>
                <p style='margin-top:10px; font-weight:bold;'>Available at: {all_best_dists}</p>
            </div>
            """, unsafe_allow_html=True)
            
            st.write("---")
            st.write(f"**Price History for {target}**")
            st.dataframe(df_sub[['date', 'distributor', 'price', 'tax_rate']].sort_values('date', ascending=False), use_container_width=True, hide_index=True)

# --- EXPORT (Date Filter Logic) ---
elif selected == "Export":
    st.markdown("<h3 style='text-align: center;'>Filtered Excel Export</h3>", unsafe_allow_html=True)
    df = get_logs()
    if not df.empty:
        col1, col2 = st.columns(2)
        with col1:
            d_start = st.date_input("From", date.today() - timedelta(days=30))
        with col2:
            d_end = st.date_input("To", date.today())
            
        filtered_df = df[(df['date'] >= d_start) & (df['date'] <= d_end)]
        st.write(f"Showing {len(filtered_df)} items in selected range.")
        
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            filtered_df.to_excel(writer, index=False)
        
        st.download_button(
            label=f"Download {d_start} to {d_end} (.xlsx)",
            data=buffer.getvalue(),
            file_name=f"Gmax_Report_{d_start}_{d_end}.xlsx",
            use_container_width=True
        )
