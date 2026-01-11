import streamlit as st
from st_supabase_connection import SupabaseConnection
from streamlit_option_menu import option_menu
import pandas as pd
from datetime import date, timedelta
import io 
import time

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
    
    /* Buttons */
    div.stButton > button {{ 
        background-color: {PINK} !important; color: white !important; border-radius: 4px; width: 100%; font-weight: bold; border: none;
    }}
    
    /* Dialog & Sidebar Stats */
    div[data-testid="stDialog"] {{ background-color: {CARD_BG}; border: 1px solid {PINK}; }}
    
    .stat-box {{
        background-color: #1e1e1e;
        padding: 8px;
        border-radius: 5px;
        margin-bottom: 5px;
        border-left: 3px solid {PINK};
        font-size: 0.8rem;
    }}
    .stat-title {{ font-weight: bold; color: white; text-transform: uppercase; }}
    .stat-detail {{ color: #aaa; }}

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

# LIVE STATS (Rows & Columns) - NO CACHE
def get_detailed_stats():
    try:
        # 1. Table Stats (Rows, Cols)
        response = conn.client.rpc('get_detailed_stats', {}).execute()
        stats = response.data if response.data else []
        # 2. Total MB 
        size_res = conn.client.rpc('get_db_size', {}).execute()
        total_mb = round(size_res.data / (1024 * 1024), 1) if size_res.data else 0.0
        return stats, total_mb
    except:
        return [], 0.0

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
    
    # --- LIVE TABLE STATISTICS ---
    st.markdown("<p style='font-size:14px; font-weight:bold; margin-bottom:10px;'>📦 DATABASE STATUS</p>", unsafe_allow_html=True)
    table_stats, total_mb = get_detailed_stats()
    
    if table_stats:
        for t in table_stats:
            st.markdown(f"""
            <div class='stat-box'>
                <div class='stat-title'>{t['table_name']}</div>
                <div class='stat-detail'>{t['total_rows']} Rows • {t['total_cols']} Cols</div>
            </div>
            """, unsafe_allow_html=True)
        st.caption(f"☁️ Total Storage: {total_mb} MB")
    else:
        st.error("Stats unavailable. Run SQL scripts.")

    if st.button("🔄 Refresh Stats"):
        st.cache_data.clear()
        st.rerun()
    
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
    st.subheader("Recent Entries")
    df_history = get_logs()
    if not df_history.empty:
        st.dataframe(df_history, use_container_width=True, hide_index=True)

# ==========================================
# PAGE: REGISTER (SMART AUTOCOMPLETE)
# ==========================================
elif selected == "Register":
    st.markdown("<h3 style='text-align: center;'>Register Management</h3>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    
    # --- AUTO-FILL HELPER ---
    def auto_fill(key_prefix, matches):
        # Triggered when user clicks a row in the suggestion table
        sel = st.session_state.get(f"{key_prefix}_selection")
        if sel and sel["selection"]["rows"]:
            idx = sel["selection"]["rows"][0]
            st.session_state[f"{key_prefix}_input"] = matches[idx]

    # --- PRODUCT COLUMN ---
    with c1:
        st.write("**Product Name**")
        # 1. Text Input (Bound to session state for auto-fill)
        if "p_reg_input" not in st.session_state: st.session_state.p_reg_input = ""
        p_val = st.text_input("Type Product", key="p_reg_input", placeholder="Type 'coca' to search...")
        
        # 2. Logic: Search & Show Dropdown
        matches_p = []
        if p_val:
            matches_p = [x for x in p_list if p_val.lower() in x.lower()]
            # Only show table if text is not an exact match yet
            if matches_p and p_val.upper() not in p_list:
                st.caption("👇 Suggestions (Click to autofill):")
                st.dataframe(
                    pd.DataFrame(matches_p, columns=["Found"]), 
                    use_container_width=True, hide_index=True, 
                    on_select="rerun", selection_mode="single-row", 
                    key="p_reg_selection"
                )
                auto_fill("p_reg", matches_p)

        # 3. Logic: Add Button or Success Message
        if p_val:
            if p_val.upper() in p_list:
                st.success(f"✅ '{p_val.upper()}' is registered.")
            else:
                st.info("New Item detected.")
                if st.button(f"➕ Save New Product: {p_val}"):
                    conn.table("products").insert({"name": p_val.strip().upper()}).execute()
                    st.success(f"Saved: {p_val}")
                    st.cache_data.clear()
                    st.rerun()

    # --- DISTRIBUTOR COLUMN ---
    with c2:
        st.write("**Distributor Name**")
        if "d_reg_input" not in st.session_state: st.session_state.d_reg_input = ""
        d_val = st.text_input("Type Distributor", key="d_reg_input", placeholder="Type name...")
        
        matches_d = []
        if d_val:
            matches_d = [x for x in d_list if d_val.lower() in x.lower()]
            if matches_d and d_val.upper() not in d_list:
                st.caption("👇 Suggestions (Click to autofill):")
                st.dataframe(
                    pd.DataFrame(matches_d, columns=["Found"]), 
                    use_container_width=True, hide_index=True, 
                    on_select="rerun", selection_mode="single-row", 
                    key="d_reg_selection"
                )
                auto_fill("d_reg", matches_d)

        if d_val:
            if d_val.upper() in d_list:
                st.success(f"✅ '{d_val.upper()}' is registered.")
            else:
                st.info("New Item detected.")
                if st.button(f"➕ Save New Distributor: {d_val}"):
                    conn.table("distributors").insert({"name": d_val.strip().upper()}).execute()
                    st.success(f"Saved: {d_val}")
                    st.cache_data.clear()
                    st.rerun()

    st.write("---")
    with st.expander("View Full Registered Lists"):
        col_a, col_b = st.columns(2)
        with col_a: st.dataframe(pd.DataFrame(p_list, columns=["All Products"]), use_container_width=True)
        with col_b: st.dataframe(pd.DataFrame(d_list, columns=["All Distributors"]), use_container_width=True)

# ==========================================
# PAGE: MANAGE (DELETE + POPUP)
# ==========================================
elif selected == "Manage":
    st.markdown("<h3 style='text-align: center;'>Database Management</h3>", unsafe_allow_html=True)
    df_manage = get_logs()
    
    # --- CONFIRMATION DIALOG ---
    @st.dialog("⚠️ CONFIRM DELETION")
    def confirm_delete(row_ids):
        st.warning(f"Deleting {len(row_ids)} row(s) permanently.")
        c1, c2 = st.columns(2)
        if c1.button("✅ Yes, Delete"):
            for rid in row_ids:
                conn.table("price_logs").delete().eq("id", rid).execute()
            st.success("Deleted.")
            st.cache_data.clear()
            time.sleep(1)
            st.rerun()
        if c2.button("❌ Cancel"):
            st.rerun()

    if not df_manage.empty:
        # Filters
        with st.expander("🔍 Filter Options", expanded=True):
            c1, c2, c3 = st.columns(3)
            with c1: search_p = st.multiselect("Product", options=p_list)
            with c2: search_d = st.multiselect("Distributor", options=d_list)
            with c3: date_range = st.date_input("Date", [])
        
        filtered_df = df_manage.copy()
        if search_p: filtered_df = filtered_df[filtered_df['product'].isin(search_p)]
        if search_d: filtered_df = filtered_df[filtered_df['distributor'].isin(search_d)]
        if len(date_range) == 2:
            filtered_df = filtered_df[(filtered_df['date'] >= date_range[0]) & (filtered_df['date'] <= date_range[1])]
            
        filtered_df["Delete"] = False # Checkbox column
        
        st.write(f"Showing **{len(filtered_df)}** records")
        
        edited_df = st.data_editor(
            filtered_df,
            key="manage_editor",
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
            column_config={
                "id": None,
                "Delete": st.column_config.CheckboxColumn("🗑️", width="small"),
                "product": st.column_config.SelectboxColumn("Product", options=p_list, required=True),
                "distributor": st.column_config.SelectboxColumn("Distributor", options=d_list, required=True),
                "tax_rate": st.column_config.SelectboxColumn("Tax", options=["5.5%", "20%", "No tax"])
            }
        )
        
        if st.button("💾 Save Changes"):
            state = st.session_state["manage_editor"]
            
            # Find rows marked for deletion
            rows_to_delete = edited_df[edited_df["Delete"] == True]["id"].tolist()
            for idx in state["deleted_rows"]:
                if idx < len(filtered_df):
                    rows_to_delete.append(filtered_df.iloc[idx]["id"])
            
            # Action
            if rows_to_delete:
                confirm_delete(list(set(rows_to_delete)))
            else:
                for idx, updates in state["edited_rows"].items():
                    if idx < len(filtered_df):
                        if "Delete" in updates: del updates["Delete"]
                        row_id = filtered_df.iloc[idx]["id"]
                        conn.table("price_logs").update(updates).eq("id", row_id).execute()
                st.success("Updates Saved!")
                st.cache_data.clear()
                time.sleep(1)
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
        c
