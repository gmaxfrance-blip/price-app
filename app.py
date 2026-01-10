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

# --- 2. REFINED CSS (FIXES SIDEBAR INTERACTION) ---
st.markdown(f"""
    <style>
    .stApp {{ background-color: {DARK_BG}; }}
    
    /* Hide the sidebar toggle arrow to keep UI fixed */
    button[kind="header"] {{ display: none !important; }}
    
    /* Ensure the sidebar container doesn't block clicks */
    section[data-testid="stSidebar"] {{ 
        min-width: 250px !important; 
        z-index: 100;
    }}

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
    
    /* Hide default Streamlit elements */
    #MainMenu, footer, header {{visibility: hidden;}}
    </style>
    """, unsafe_allow_html=True)

# --- 3. DATA LOGIC ---
@st.cache_data(ttl=300)
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

# --- 5. NAVIGATION (Fixed logic) ---
with st.sidebar:
    st.markdown(f'<div class="logo-container"><img src="{LOGO_URL}"></div>', unsafe_allow_html=True)
    opts = ["Entry", "Register", "Manage", "Analyser", "Export"] if st.session_state.role == "admin" else ["Analyser", "Export"]
    
    # Using a key helps Streamlit track state changes in the menu
    selected = option_menu(
        menu_title=None, 
        options=opts, 
        icons=["plus", "list", "pencil", "search", "download"], 
        default_index=0,
        key="main_nav_menu"
    )
    
    st.write("---")
    if st.button("Logout"):
        st.session_state.clear()
        st.rerun()

p_list, d_list = get_master_data()
# Center logo on main content area
st.markdown(f'<div class="logo-container"><img src="{LOGO_URL}"></div>', unsafe_allow_html=True)

# --- PAGE: ENTRY ---
if selected == "Entry":
    st.markdown("<h3 style='text-align: center;'>New Price Entry</h3>", unsafe_allow_html=True)
    with st.form("entry_form", clear_on_submit=True):
        p = st.selectbox("Select Product", options=[""] + p_list)
        d = st.selectbox("Select Distributor", options=[""] + d_list)
        pr = st.number_input("Price HT (€)", min_value=0.0, step=0.01)
        tx = st.selectbox("Tax %", ["5.5%", "20%", "No tax"])
        dt = st.date_input("Date", date.today())
        
        if st.form_submit_button("Submit Entry"):
            if p and d and pr > 0:
                conn.table("price_logs").insert({"product": p, "distributor": d, "price": pr, "tax_rate": tx, "date": str(dt)}).execute()
                st.success("Saved Successfully")
                st.cache_data.clear()
            else: st.error("Please fill all fields")

# --- PAGE: REGISTER (FIXED DROPDOWN + INPUT) ---
elif selected == "Register":
    st.markdown("<h3 style='text-align: center;'>Register Management</h3>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    
    with c1:
        st.write("**Register Product**")
        # Search while typing logic
        search_p = st.selectbox("Search existing...", options=[""] + p_list, key="search_p")
        new_p = st.text_input("Type NEW product name:", value=search_p, key="input_p")
        
        if st.button("Add Product"):
            final_p = new_p.strip().upper()
            if final_p and final_p not in p_list:
                conn.table("products").insert({"name": final_p}).execute()
                st.success(f"Added: {final_p}")
                st.cache_data.clear()
                st.rerun()
            else: st.warning("Item already exists or empty.")
        st.dataframe(p_list, columns=["Registered Products"], use_container_width=True)
            
    with c2:
        st.write("**Register Distributor**")
        search_d = st.selectbox("Search existing...", options=[""] + d_list, key="search_d")
        new_d = st.text_input("Type NEW distributor name:", value=search_d, key="input_d")
        
        if st.button("Add Distributor"):
            final_d = new_d.strip().upper()
            if final_d and final_d not in d_list:
                conn.table("distributors").insert({"name": final_d}).execute()
                st.success(f"Added: {final_d}")
                st.cache_data.clear()
                st.rerun()
            else: st.warning("Item already exists or empty.")
        st.dataframe(d_list, columns=["Registered Distributors"], use_container_width=True)

# --- PAGE: MANAGE ---
elif selected == "Manage":
    st.markdown("<h3 style='text-align: center;'>Database Management</h3>", unsafe_allow_html=True)
    df_manage = get_logs()
    
    if not df_manage.empty:
        st.info("Edit cells below and click 'Commit Changes'")
        edited_df = st.data_editor(
            df_manage,
            key="db_editor",
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
            column_config={
                "id": None,
                "product": st.column_config.SelectboxColumn("Product", options=p_list),
                "distributor": st.column_config.SelectboxColumn("Distributor", options=d_list),
                "tax_rate": st.column_config.SelectboxColumn("Tax", options=["5.5%", "20%", "No tax"])
            }
        )
        
        if st.button("Commit Changes"):
            state = st.session_state["db_editor"]
            # Handle Edits
            for idx, updates in state["edited_rows"].items():
                conn.table("price_logs").update(updates).eq("id", df_manage.iloc[idx]["id"]).execute()
            # Handle Deletes
            for idx in state["deleted_rows"]:
                conn.table("price_logs").delete().eq("id", df_manage.iloc[idx]["id"]).execute()
                
            st.success("Updated")
            st.cache_data.clear()
            st.rerun()
    else:
        st.warning("No data found.")

# --- PAGE: ANALYSER ---
elif selected == "Analyser":
    st.markdown("<h3 style='text-align: center;'>Price Analysis</h3>", unsafe_allow_html=True)
    target = st.selectbox("Search Product", [""] + p_list)
    if target:
        df = get_logs()
        df_sub = df[df['product'] == target].copy()
        if not df_sub.empty:
            min_price = df_sub['price'].min()
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
            st.dataframe(df_sub[['date', 'distributor', 'price', 'tax_rate']].sort_values('date', ascending=False), use_container_width=True, hide_index=True)

# --- PAGE: EXPORT ---
elif selected == "Export":
    st.markdown("<h3 style='text-align: center;'>Excel Export</h3>", unsafe_allow_html=True)
    df = get_logs()
    if not df.empty:
        c1, c2 = st.columns(2)
        with c1: start_d = st.date_input("From", date.today() - timedelta(days=30))
        with c2: end_d = st.date_input("To", date.today())
        
        filtered = df[(df['date'] >= start_d) & (df['date'] <= end_d)]
        
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            filtered.to_excel(writer, index=False)
        
        st.download_button(
            label="Download Excel Report",
            data=buffer.getvalue(),
            file_name=f"Gmax_Export.xlsx",
            use_container_width=True
        )
