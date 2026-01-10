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

st.set_page_config(page_title="Gmax Management", page_icon=LOGO_URL, layout="wide", initial_sidebar_state="expanded")
conn = st.connection("supabase", type=SupabaseConnection)

# --- 2. CSS FIX (SIDEBAR & UI) ---
st.markdown(f"""
    <style>
    .stApp {{ background-color: {DARK_BG}; }}
    
    /* 1. LOCK SIDEBAR OPEN & HIDE TOGGLE */
    section[data-testid="stSidebar"] {{ 
        width: 300px !important; 
        display: block !important;
        visibility: visible !important;
    }}
    button[kind="header"] {{ display: none !important; }} /* Hides the collapse arrow */
    div[data-testid="collapsedControl"] {{ display: none !important; }} 

    /* 2. FORM & INPUT STYLING */
    div[data-testid="stForm"] {{ background-color: {CARD_BG}; padding: 1.5rem; border-radius: 8px; border: 1px solid #333; }}
    
    .stSelectbox div, .stNumberInput input, .stDateInput input, .stTextInput input {{
        background-color: #3b3d4a !important; color: white !important; border: 1px solid #555 !important;
    }}
    
    h1, h2, h3, h4, p, label {{ color: #ffffff !important; font-family: 'Arial', sans-serif; }}
    
    div.stButton > button {{ 
        background-color: {PINK} !important; color: white !important; border-radius: 4px; width: 100%; font-weight: bold; border: none;
    }}
    
    .logo-container {{ display: flex; justify-content: center; padding: 20px 10px; }}
    .logo-container img {{ width: 140px; }}
    
    /* Hide Streamlit Footer */
    #MainMenu, footer, header {{visibility: hidden;}}
    </style>
    """, unsafe_allow_html=True)

# --- 3. DATA FUNCTIONS ---
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

# --- 4. LOGIN ---
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

# --- 5. SIDEBAR NAVIGATION ---
with st.sidebar:
    st.markdown(f'<div class="logo-container"><img src="{LOGO_URL}"></div>', unsafe_allow_html=True)
    
    # NAVIGATION MENU
    # We removed the 'key' argument to prevent state-locking issues that freeze the menu
    selected = option_menu(
        menu_title=None, 
        options=["Entry", "Register", "Manage", "Analyser", "Export"] if st.session_state.role == "admin" else ["Analyser", "Export"], 
        icons=["plus", "list", "pencil", "search", "download"], 
        default_index=0,
        styles={
            "container": {"background-color": DARK_BG},
            "nav-link-selected": {"background-color": PINK},
        }
    )
    
    st.write("---")
    if st.button("Logout"):
        st.session_state.clear()
        st.rerun()

p_list, d_list = get_master_data()

# --- HEADER LOGO ON MAIN PAGE ---
st.markdown(f'<div class="logo-container"><img src="{LOGO_URL}"></div>', unsafe_allow_html=True)

# ==========================================
# PAGE: NEW PRICE ENTRY
# ==========================================
if selected == "Entry":
    st.markdown("<h3 style='text-align: center;'>New Price Entry</h3>", unsafe_allow_html=True)
    with st.form("entry_form", clear_on_submit=True):
        p = st.selectbox("Product", options=[""] + p_list)
        d = st.selectbox("Distributor", options=[""] + d_list)
        pr = st.number_input("Price HT (€)", min_value=0.0, step=0.01)
        tx = st.selectbox("Tax %", ["5.5%", "20%", "No tax"])
        dt = st.date_input("Date", date.today())
        
        if st.form_submit_button("Submit Entry"):
            if p and d and pr > 0:
                conn.table("price_logs").insert({"product": p, "distributor": d, "price": pr, "tax_rate": tx, "date": str(dt)}).execute()
                st.success("Saved Successfully")
                st.cache_data.clear()
            else: st.error("Please fill all fields")

# ==========================================
# PAGE: REGISTER (SINGLE FIELD LOGIC)
# ==========================================
elif selected == "Register":
    st.markdown("<h3 style='text-align: center;'>Register Management</h3>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    
    # PRODUCT SECTION
    with c1:
        st.write("**Product Registry**")
        # 1. INPUT FIELD: Type to search OR add new
        reg_p = st.text_input("Type Product Name", placeholder="Start typing to check if exists...", key="reg_p_input")
        
        # 2. AUTO-CHECK LOGIC (The "Dropdown" replacement)
        if reg_p:
            # Filter existing list based on typing
            matches = [x for x in p_list if reg_p.lower() in x.lower()]
            
            if matches:
                # If matches found, show them like a list so user knows it exists
                st.dataframe(pd.DataFrame(matches, columns=["Existing Matches"]), use_container_width=True, hide_index=True)
                if reg_p in p_list:
                    st.warning(f"'{reg_p}' is already registered.")
            else:
                # If NO matches, user is free to add
                st.info("New item! Click add below.")
                
            if st.button("Add New Product", disabled=(reg_p in p_list)):
                conn.table("products").insert({"name": reg_p.strip().upper()}).execute()
                st.success(f"Added: {reg_p}")
                st.cache_data.clear()
                st.rerun()
        else:
            # Show full list if nothing typed
            st.dataframe(pd.DataFrame(p_list, columns=["All Products"]), use_container_width=True, hide_index=True)

    # DISTRIBUTOR SECTION
    with c2:
        st.write("**Distributor Registry**")
        reg_d = st.text_input("Type Distributor Name", placeholder="Start typing to check...", key="reg_d_input")
        
        if reg_d:
            matches_d = [x for x in d_list if reg_d.lower() in x.lower()]
            
            if matches_d:
                st.dataframe(pd.DataFrame(matches_d, columns=["Existing Matches"]), use_container_width=True, hide_index=True)
                if reg_d in d_list:
                    st.warning(f"'{reg_d}' is already registered.")
            else:
                st.info("New distributor! Click add below.")
                
            if st.button("Add New Distributor", disabled=(reg_d in d_list)):
                conn.table("distributors").insert({"name": reg_d.strip().upper()}).execute()
                st.success(f"Added: {reg_d}")
                st.cache_data.clear()
                st.rerun()
        else:
            st.dataframe(pd.DataFrame(d_list, columns=["All Distributors"]), use_container_width=True, hide_index=True)

# ==========================================
# PAGE: MANAGE (EDIT & DELETE)
# ==========================================
elif selected == "Manage":
    st.markdown("<h3 style='text-align: center;'>Database Management</h3>", unsafe_allow_html=True)
    df_manage = get_logs()
    
    if not df_manage.empty:
        st.info("Tip: Select rows and hit 'Delete' on your keyboard to mark for deletion.")
        edited_df = st.data_editor(
            df_manage,
            key="manage_editor",
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
            column_config={
                "id": None,
                "product": st.column_config.SelectboxColumn("Product", options=p_list, required=True),
                "distributor": st.column_config.SelectboxColumn("Distributor", options=d_list, required=True),
                "tax_rate": st.column_config.SelectboxColumn("Tax", options=["5.5%", "20%", "No tax"])
            }
        )
        
        if st.button("Commit Changes (Update/Delete)"):
            state = st.session_state["manage_editor"]
            
            # 1. Handle Updates
            for idx, updates in state["edited_rows"].items():
                row_id = df_manage.iloc[idx]["id"]
                conn.table("price_logs").update(updates).eq("id", row_id).execute()
                
            # 2. Handle Deletions
            for idx in state["deleted_rows"]:
                row_id = df_manage.iloc[idx]["id"]
                conn.table("price_logs").delete().eq("id", row_id).execute()
                
            st.success("Database updated successfully!")
            st.cache_data.clear()
            st.rerun()
    else:
        st.warning("No records found.")

# ==========================================
# PAGE: ANALYSER (BEST PRICE + HISTORY)
# ==========================================
elif selected == "Analyser":
    st.markdown("<h3 style='text-align: center;'>Price Analysis</h3>", unsafe_allow_html=True)
    target = st.selectbox("Select Product to Analyze", [""] + p_list)
    
    if target:
        df = get_logs()
        df_sub = df[df['product'] == target].copy()
        
        if not df_sub.empty:
            min_price = df_sub['price'].min()
            # Get all distributors selling at the minimum price
            best_sellers = df_sub[df_sub['price'] == min_price]['distributor'].unique()
            best_sellers_str = ", ".join(best_sellers)
            
            st.markdown(f"""
            <div style='background-color:{CARD_BG}; padding:20px; border-radius:10px; border-left: 6px solid {PINK}; margin-bottom: 20px;'>
                <p style='margin:0; font-size:14px; text-transform:uppercase; color: #888;'>Best Market Price</p>
                <h1 style='margin:5px 0; color:{PINK} !important; font-size: 3rem;'>{min_price:.2f} €</h1>
                <p style='margin:0; font-size:16px;'>Available at: <strong style='color:white'>{best_sellers_str}</strong></p>
            </div>
            """, unsafe_allow_html=True)
            
            st.subheader(f"History: {target}")
            # Ensure sorting works by selecting columns AFTER sorting
            df_history = df_sub.sort_values(by='date', ascending=False)
            st.dataframe(
                df_history[['date', 'distributor', 'price', 'tax_rate']], 
                use_container_width=True, 
                hide_index=True
            )

# ==========================================
# PAGE: EXPORT (DATE FILTER)
# ==========================================
elif selected == "Export":
    st.markdown("<h3 style='text-align: center;'>Excel Export</h3>", unsafe_allow_html=True)
    df = get_logs()
    
    if not df.empty:
        c1, c2 = st.columns(2)
        with c1: start_d = st.date_input("Start Date", date.today() - timedelta(days=30))
        with c2: end_d = st.date_input("End Date", date.today())
        
        # Filter Data
        mask = (df['date'] >= start_d) & (df['date'] <= end_d)
        filtered_df = df[mask]
        
        st.write(f"**Records Found:** {len(filtered_df)}")
        
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            filtered_df.to_excel(writer, index=False)
            
        st.download_button(
            label="Download Excel File",
            data=buffer.getvalue(),
            file_name=f"Gmax_Report_{start_d}_{end_d}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
