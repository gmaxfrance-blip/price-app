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

# --- 2. BRUTAL CSS (REMOVES SIDEBAR ARROW & FIXES UI) ---
st.markdown(f"""
    <style>
    .stApp {{ background-color: {DARK_BG}; }}
    
    /* Hide the sidebar toggle arrow button */
    button[kind="header"] {{ display: none !important; }}
    section[data-testid="stSidebar"] {{ min-width: 250px !important; }}

    .logo-container {{ display: flex; justify-content: center; padding: 10px; }}
    .logo-container img {{ max-width: 100%; height: auto; width: 120px; }}
    
    div[data-testid="stForm"] {{ background-color: {CARD_BG}; padding: 1.5rem; border-radius: 8px; border: 1px solid #333; }}
    
    /* Input Styling */
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
        p = st.selectbox("Search/Select Product", options=[""] + p_list)
        d = st.selectbox("Search/Select Distributor", options=[""] + d_list)
        pr = st.number_input("Price HT (€)", min_value=0.0, step=0.01)
        tx = st.selectbox("Tax %", ["5.5%", "20%", "No tax"])
        dt = st.date_input("Date", date.today())
        
        if st.form_submit_button("Submit Entry"):
            if p and d and pr > 0:
                conn.table("price_logs").insert({"product": p, "distributor": d, "price": pr, "tax_rate": tx, "date": str(dt)}).execute()
                st.success("Saved Successfully")
                st.cache_data.clear()
            else: st.error("Please fill all fields")

# --- PAGE: REGISTER (TYPE-TO-SEARCH LOGIC) ---
elif selected == "Register":
    st.markdown("<h3 style='text-align: center;'>Register Management</h3>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    
    with c1:
        st.write("**Register Product**")
        # DROPDOWN + INPUT LOGIC:
        # User types to search. If they want to add new, they use the text box below.
        existing_p = st.selectbox("Existing Products (Search here)", options=[""] + p_list, key="ex_p")
        new_p = st.text_input("New Product Name", placeholder="Type name here if not in dropdown...", key="in_p")
        
        if st.button("Add Product"):
            val = new_p if new_p else existing_p
            if val and val.strip() not in p_list:
                conn.table("products").insert({"name": val.strip().upper()}).execute()
                st.success(f"Added: {val}")
                st.cache_data.clear()
                st.rerun()
            else: st.warning("Item already exists or empty input")
        st.dataframe(p_list, columns=["Registered Products"], use_container_width=True)
            
    with c2:
        st.write("**Register Distributor**")
        existing_d = st.selectbox("Existing Distributors (Search here)", options=[""] + d_list, key="ex_d")
        new_d = st.text_input("New Distributor Name", placeholder="Type name here if not in dropdown...", key="in_d")
        
        if st.button("Add Distributor"):
            val_d = new_d if new_d else existing_d
            if val_d and val_d.strip() not in d_list:
                conn.table("distributors").insert({"name": val_d.strip().upper()}).execute()
                st.success(f"Added: {val_d}")
                st.cache_data.clear()
                st.rerun()
            else: st.warning("Item already exists or empty input")
        st.dataframe(d_list, columns=["Registered Distributors"], use_container_width=True)

# --- PAGE: MANAGE (FIXED VISIBILITY) ---
elif selected == "Manage":
    st.markdown("<h3 style='text-align: center;'>Database Management</h3>", unsafe_allow_html=True)
    df_manage = get_logs()
    
    if not df_manage.empty:
        st.write("Edit rows directly in the table below and click **Commit Changes**.")
        # We use a copy for the editor
        df_editor = df_manage.copy()
        
        edited_df = st.data_editor(
            df_editor,
            key="main_editor",
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
            column_config={
                "id": None, # Hide ID
                "product": st.column_config.SelectboxColumn("Product", options=p_list, required=True),
                "distributor": st.column_config.SelectboxColumn("Distributor", options=d_list, required=True),
                "tax_rate": st.column_config.SelectboxColumn("Tax %", options=["5.5%", "20%", "No tax"])
            }
        )
        
        if st.button("Commit Changes"):
            # Update Logic for edited rows
            state = st.session_state["main_editor"]
            # Handle Edits
            for idx, updates in state["edited_rows"].items():
                row_id = df_manage.iloc[idx]["id"]
                conn.table("price_logs").update(updates).eq("id", row_id).execute()
            # Handle Deletions
            for idx in state["deleted_rows"]:
                row_id = df_manage.iloc[idx]["id"]
                conn.table("price_logs").delete().eq("id", row_id).execute()
                
            st.success("Database Updated Successfully")
            st.cache_data.clear()
            st.rerun()
    else:
        st.info("No data found in database.")

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
            st.write(f"**Full History: {target}**")
            st.dataframe(df_sub[['date', 'distributor', 'price', 'tax_rate']], use_container_width=True, hide_index=True)

# --- PAGE: EXPORT ---
elif selected == "Export":
    st.markdown("<h3 style='text-align: center;'>Excel Export</h3>", unsafe_allow_html=True)
    df = get_logs()
    if not df.empty:
        c1, c2 = st.columns(2)
        with c1: start_d = st.date_input("From", date.today() - timedelta(days=30))
        with c2: end_d = st.date_input("To", date.today())
        
        filtered_df = df[(df['date'] >= start_d) & (df['date'] <= end_d)]
        
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            filtered_df.to_excel(writer, index=False)
        
        st.download_button(
            label=f"Download Report ({len(filtered_df)} records)",
            data=buffer.getvalue(),
            file_name=f"Gmax_Report_{start_d}_{end_d}.xlsx",
            use_container_width=True
        )
