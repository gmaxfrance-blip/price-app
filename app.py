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
    .stSelectbox div, .stNumberInput input, .stDateInput input, .stTextInput input {{
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

# ==========================================
# PAGE: REGISTER (SMART AUTOCOMPLETE)
# ==========================================
elif selected == "Register":
    st.markdown("<h3 style='text-align: center;'>Register Management</h3>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    
    # Helper to handle selection click
    def handle_selection(key_prefix, matches):
        # Check if user clicked a row in the dataframe
        selection = st.session_state.get(f"{key_prefix}_selection")
        if selection and selection["selection"]["rows"]:
            idx = selection["selection"]["rows"][0]
            # Update the text input with the selected name
            st.session_state[f"{key_prefix}_input"] = matches[idx]

    # --- PRODUCT COLUMN ---
    with c1:
        st.write("**Products**")
        
        # 1. INPUT FIELD (Captured in Session State)
        if "p_reg_input" not in st.session_state: st.session_state.p_reg_input = ""
        
        p_val = st.text_input("Product Name", key="p_reg_input", placeholder="Type to search or add new...")
        
        # 2. FILTER LOGIC
        matches_p = []
        if p_val:
            matches_p = [x for x in p_list if p_val.lower() in x.lower()]
            
            # Show "Dropdown" Table if matches exist AND text isn't an exact match yet
            if matches_p and p_val.upper() not in p_list:
                st.caption("👇 Click below to select:")
                df_p = pd.DataFrame(matches_p, columns=["Suggestions"])
                
                # INTERACTIVE TABLE (Acts as Dropdown)
                st.dataframe(
                    df_p, 
                    use_container_width=True, 
                    hide_index=True, 
                    on_select="rerun", 
                    selection_mode="single-row",
                    key="p_reg_selection"
                )
                # Apply selection logic
                handle_selection("p_reg", matches_p)

        # 3. ACTION BUTTONS
        if p_val:
            if p_val.upper() in p_list:
                st.success(f"✅ '{p_val.upper()}' is already selected/registered.")
            else:
                # If no exact match (New Item), show Save Button
                if st.button(f"Save New Product: {p_val}"):
                    conn.table("products").insert({"name": p_val.strip().upper()}).execute()
                    st.success(f"Saved: {p_val}")
                    st.cache_data.clear()
                    st.rerun()

    # --- DISTRIBUTOR COLUMN ---
    with c2:
        st.write("**Distributors**")
        
        # 1. INPUT FIELD
        if "d_reg_input" not in st.session_state: st.session_state.d_reg_input = ""
        
        d_val = st.text_input("Distributor Name", key="d_reg_input", placeholder="Type to search or add new...")
        
        # 2. FILTER LOGIC
        matches_d = []
        if d_val:
            matches_d = [x for x in d_list if d_val.lower() in x.lower()]
            
            if matches_d and d_val.upper() not in d_list:
                st.caption("👇 Click below to select:")
                df_d = pd.DataFrame(matches_d, columns=["Suggestions"])
                
                st.dataframe(
                    df_d, 
                    use_container_width=True, 
                    hide_index=True, 
                    on_select="rerun", 
                    selection_mode="single-row",
                    key="d_reg_selection"
                )
                handle_selection("d_reg", matches_d)

        # 3. ACTION BUTTONS
        if d_val:
            if d_val.upper() in d_list:
                st.success(f"✅ '{d_val.upper()}' is already selected/registered.")
            else:
                if st.button(f"Save New Distributor: {d_val}"):
                    conn.table("distributors").insert({"name": d_val.strip().upper()}).execute()
                    st.success(f"Saved: {d_val}")
                    st.cache_data.clear()
                    st.rerun()

    # Full lists at bottom
    st.write("---")
    with st.expander("View Full Registered Lists"):
        col_a, col_b = st.columns(2)
        with col_a: st.dataframe(pd.DataFrame(p_list, columns=["All Products"]), use_container_width=True)
        with col_b: st.dataframe(pd.DataFrame(d_list, columns=["All Distributors"]), use_container_width=True)

# ==========================================
# PAGE: MANAGE
# ==========================================
elif selected == "Manage":
    st.markdown("<h3 style='text-align: center;'>Database Management</h3>", unsafe_allow_html=True)
    df_manage = get_logs()
    
    if not df_manage.empty:
        with st.expander("🔍 Search & Filters", expanded=True):
            col1, col2, col3 = st.columns(3)
            with col1: search_p = st.multiselect("Filter Product", options=p_list)
            with col2: search_d = st.multiselect("Filter Distributor", options=d_list)
            with col3: date_range = st.date_input("Filter Date", [])
        
        filtered_df = df_manage.copy()
        if search_p: filtered_df = filtered_df[filtered_df['product'].isin(search_p)]
        if search_d: filtered_df = filtered_df[filtered_df['distributor'].isin(search_d)]
        if len(date_range) == 2:
            filtered_df = filtered_df[(filtered_df['date'] >= date_range[0]) & (filtered_df['date'] <= date_range[1])]
            
        st.write(f"Showing **{len(filtered_df)}** records")
        
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
        
        if st.button("Commit Changes"):
            state = st.session_state["manage_editor"]
            # Map index back to filtered ID
            for idx, updates in state["edited_rows"].items():
                if idx < len(filtered_df):
                    row_id = filtered_df.iloc[idx]["id"]
                    conn.table("price_logs").update(updates).eq("id", row_id).execute()
            for idx in state["deleted_rows"]:
                if idx < len(filtered_df):
                    row_id = filtered_df.iloc[idx]["id"]
                    conn.table("price_logs").delete().eq("id", row_id).execute()
            st.success("Updated")
            st.cache_data.clear()
            st.rerun()
    else: st.warning("No records found.")

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
# PAGE: EXPORT
# ==========================================
elif selected == "Export":
    st.markdown("<h3 style='text-align: center;'>Excel Export</h3>", unsafe_allow_html=True)
    df = get_logs()
    if not df.empty:
        c1, c2 = st.columns(2)
        with c1: start_d = st.date_input("Start Date", date.today() - timedelta(days=30))
        with c2: end_d = st.date_input("End Date", date.today())
        
        filtered = df[(df['date'] >= start_d) & (df['date'] <= end_d)]
        
        st.write("---")
        st.caption(f"Preview: {len(filtered)} records found.")
        st.dataframe(filtered, use_container_width=True, hide_index=True)
        
        if not filtered.empty:
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                filtered.to_excel(writer, index=False)
            st.download_button("📥 Download Excel", data=buffer.getvalue(), file_name="Gmax_Report.xlsx", use_container_width=True)
