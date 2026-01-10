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

# --- 2. CSS STYLING ---
st.markdown(f"""
    <style>
    .stApp {{ background-color: {DARK_BG}; }}
    
    div[data-testid="stForm"] {{ background-color: {CARD_BG}; padding: 1.5rem; border-radius: 8px; border: 1px solid #333; }}
    
    .stSelectbox div, .stNumberInput input, .stDateInput input, .stTextInput input, .stMultiSelect div {{
        background-color: #3b3d4a !important; color: white !important; border: 1px solid #555 !important;
    }}
    
    h1, h2, h3, h4, p, label {{ color: #ffffff !important; font-family: 'Arial', sans-serif; }}
    
    div.stButton > button {{ 
        background-color: {PINK} !important; color: white !important; border-radius: 4px; width: 100%; font-weight: bold; border: none;
    }}
    
    .logo-container {{ display: flex; justify-content: center; padding: 20px 10px; }}
    .logo-container img {{ width: 140px; }}
    
    #MainMenu, footer {{visibility: hidden;}}
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

# --- 5. SIDEBAR NAVIGATION ---
with st.sidebar:
    st.image(LOGO_URL, width=100)
    selected = option_menu(
        menu_title="Main Menu", 
        options=["Entry", "Register", "Manage", "Analyser", "Export"] if st.session_state.role == "admin" else ["Analyser", "Export"], 
        icons=["plus", "list", "pencil", "search", "download"], 
        default_index=0,
        styles={"nav-link-selected": {"background-color": PINK}}
    )
    st.write("---")
    if st.button("Logout"):
        st.session_state.clear()
        st.rerun()

p_list, d_list = get_master_data()

# ==========================================
# PAGE: ENTRY
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
                st.rerun()
            else: st.error("Please fill all fields")

    st.write("---")
    st.subheader("Previous Entries")
    df_history = get_logs()
    if not df_history.empty:
        st.dataframe(df_history, use_container_width=True, hide_index=True)
    else:
        st.info("No entries found.")

# ==========================================
# PAGE: REGISTER
# ==========================================
elif selected == "Register":
    st.markdown("<h3 style='text-align: center;'>Register Management</h3>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    
    with c1:
        st.write("**Product Name**")
        p_input = st.text_input("Type Product Name", placeholder="Start typing...", key="p_in", label_visibility="collapsed")
        
        if p_input:
            matches = [x for x in p_list if p_input.lower() in x.lower()]
            if matches:
                st.caption(f"Found {len(matches)} matches:")
                st.dataframe(pd.DataFrame(matches, columns=["Suggested Products"]), use_container_width=True, hide_index=True)
                if p_input.upper() in p_list:
                    st.success(f"✅ '{p_input.upper()}' is already registered.")
                else:
                    if st.button(f"➕ Register New: '{p_input.upper()}'"):
                        conn.table("products").insert({"name": p_input.strip().upper()}).execute()
                        st.success("Registered!")
                        st.cache_data.clear()
                        st.rerun()
            else:
                st.info("No matches found. This is a new item.")
                if st.button(f"➕ Register New: '{p_input.upper()}'"):
                    conn.table("products").insert({"name": p_input.strip().upper()}).execute()
                    st.success("Registered!")
                    st.cache_data.clear()
                    st.rerun()

    with c2:
        st.write("**Distributor Name**")
        d_input = st.text_input("Type Distributor Name", placeholder="Start typing...", key="d_in", label_visibility="collapsed")
        
        if d_input:
            matches_d = [x for x in d_list if d_input.lower() in x.lower()]
            if matches_d:
                st.caption(f"Found {len(matches_d)} matches:")
                st.dataframe(pd.DataFrame(matches_d, columns=["Suggested Distributors"]), use_container_width=True, hide_index=True)
                if d_input.upper() in d_list:
                    st.success(f"✅ '{d_input.upper()}' is already registered.")
                else:
                    if st.button(f"➕ Register New: '{d_input.upper()}'"):
                        conn.table("distributors").insert({"name": d_input.strip().upper()}).execute()
                        st.success("Registered!")
                        st.cache_data.clear()
                        st.rerun()
            else:
                st.info("No matches found. This is a new item.")
                if st.button(f"➕ Register New: '{d_input.upper()}'"):
                    conn.table("distributors").insert({"name": d_input.strip().upper()}).execute()
                    st.success("Registered!")
                    st.cache_data.clear()
                    st.rerun()

# ==========================================
# PAGE: MANAGE (SEARCH + FILTER ADDED)
# ==========================================
elif selected == "Manage":
    st.markdown("<h3 style='text-align: center;'>Database Management</h3>", unsafe_allow_html=True)
    df_manage = get_logs()
    
    if not df_manage.empty:
        # --- FILTERS ---
        with st.expander("🔍 Search & Filters", expanded=True):
            col1, col2, col3 = st.columns(3)
            with col1:
                search_p = st.multiselect("Filter by Product", options=p_list)
            with col2:
                search_d = st.multiselect("Filter by Distributor", options=d_list)
            with col3:
                date_range = st.date_input("Filter by Date Range", [])
        
        # --- APPLY FILTER LOGIC ---
        filtered_df = df_manage.copy()
        
        if search_p:
            filtered_df = filtered_df[filtered_df['product'].isin(search_p)]
        if search_d:
            filtered_df = filtered_df[filtered_df['distributor'].isin(search_d)]
        if len(date_range) == 2:
            start_date, end_date = date_range
            filtered_df = filtered_df[(filtered_df['date'] >= start_date) & (filtered_df['date'] <= end_date)]
            
        st.write(f"Showing **{len(filtered_df)}** records matching criteria.")
        
        # --- EDITOR ---
        edited_df = st.data_editor(
            filtered_df,
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
            # To handle edits on filtered data, we map back via ID
            for idx, updates in state["edited_rows"].items():
                # We must find the correct ID from the FILTERED dataframe using the index
                if idx < len(filtered_df):
                    row_id = filtered_df.iloc[idx]["id"]
                    conn.table("price_logs").update(updates).eq("id", row_id).execute()
            
            for idx in state["deleted_rows"]:
                if idx < len(filtered_df):
                    row_id = filtered_df.iloc[idx]["id"]
                    conn.table("price_logs").delete().eq("id", row_id).execute()
                    
            st.success("Updated Successfully!")
            st.cache_data.clear()
            st.rerun()
    else:
        st.warning("No records found in database.")

# ==========================================
# PAGE: ANALYSER
# ==========================================
elif selected == "Analyser":
    st.markdown("<h3 style='text-align: center;'>Price Analysis</h3>", unsafe_allow_html=True)
    target = st.selectbox("Select Product", [""] + p_list)
    
    if target:
        df = get_logs()
        df_sub = df[df['product'] == target].copy()
        if not df_sub.empty:
            min_price = df_sub['price'].min()
            best_sellers = df_sub[df_sub['price'] == min_price]['distributor'].unique()
            
            st.markdown(f"""
            <div style='background-color:{CARD_BG}; padding:20px; border-radius:10px; border-left: 6px solid {PINK};'>
                <p style='margin:0; color:#888;'>BEST PRICE</p>
                <h1 style='margin:0; color:{PINK} !important;'>{min_price:.2f} €</h1>
                <p>Available at: <strong>{", ".join(best_sellers)}</strong></p>
            </div>
            """, unsafe_allow_html=True)
            
            st.write("---")
            st.dataframe(df_sub[['date', 'distributor', 'price', 'tax_rate']].sort_values('date', ascending=False), use_container_width=True, hide_index=True)

# ==========================================
# PAGE: EXPORT (AUTO VIEW TABLE + DOWNLOAD)
# ==========================================
elif selected == "Export":
    st.markdown("<h3 style='text-align: center;'>Excel Export</h3>", unsafe_allow_html=True)
    df = get_logs()
    if not df.empty:
        # 1. Date Filter Controls
        c1, c2 = st.columns(2)
        with c1: start_d = st.date_input("Start Date", date.today() - timedelta(days=30))
        with c2: end_d = st.date_input("End Date", date.today())
        
        # 2. Logic: Filter Data
        filtered = df[(df['date'] >= start_d) & (df['date'] <= end_d)]
        
        # 3. View Automatically (Table Display)
        st.write("---")
        st.subheader("Preview Data to Download")
        st.caption(f"Found {len(filtered)} records between {start_d} and {end_d}")
        
        if not filtered.empty:
            st.dataframe(filtered, use_container_width=True, hide_index=True)
            
            # 4. Download Button (Appears below table)
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                filtered.to_excel(writer, index=False)
                
            st.download_button(
                label="📥 Download This Table (.xlsx)", 
                data=buffer.getvalue(), 
                file_name=f"Gmax_{start_d}_{end_d}.xlsx", 
                use_container_width=True
            )
        else:
            st.warning("No data found in this date range.")
