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
    
    .stSelectbox div, .stNumberInput input, .stDateInput input, .stTextInput input, .stMultiSelect div, .stTextArea textarea {{
        background-color: #3b3d4a !important; color: white !important; border: 1px solid #555 !important;
    }}
    
    h1, h2, h3, h4, p, label {{ color: #ffffff !important; font-family: 'Arial', sans-serif; }}
    
    div.stButton > button {{ 
        background-color: {PINK} !important; color: white !important; border-radius: 4px; width: 100%; font-weight: bold; border: none;
    }}
    
    /* Tabs Styling */
    button[data-baseweb="tab"] {{
        background-color: transparent !important;
        color: white !important;
        font-weight: bold;
    }}
    button[data-baseweb="tab"][aria-selected="true"] {{
        background-color: {PINK} !important;
        border-radius: 5px;
    }}

    /* CENTER SIDEBAR LOGO */
    [data-testid="stSidebar"] img {{
        display: block;
        margin-left: auto;
        margin-right: auto;
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

# LIVE STORAGE CHECK
def get_live_storage_mb():
    try:
        response = conn.client.rpc('get_db_size', {}).execute()
        if response.data:
            return round(response.data / (1024 * 1024), 1)
        return 0.0
    except:
        return 0.0

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
    st.image(LOGO_URL, width=140)
    selected = option_menu(
        menu_title="Main Menu", 
        options=["Entry", "Register", "Manage", "Analyser", "Export"] if st.session_state.role == "admin" else ["Analyser", "Export"], 
        icons=["plus", "list", "pencil", "search", "download"], 
        default_index=0,
        styles={"nav-link-selected": {"background-color": PINK}}
    )
    
    st.write("---")
    
    # LIVE STORAGE BAR
    used_mb = get_live_storage_mb()
    limit = 500
    pct = min(used_mb / limit, 1.0)
    
    st.caption("☁️ Storage Usage")
    st.progress(pct)
    st.write(f"**{used_mb} MB** / {limit} MB")
    if st.button("🔄 Refresh"):
        st.cache_data.clear()
        st.rerun()
    
    st.write("---")
    if st.button("Logout"):
        st.session_state.clear()
        st.rerun()

p_list, d_list = get_master_data()

# ==========================================
# PAGE: ENTRY (Added Qty & Comment)
# ==========================================
if selected == "Entry":
    st.markdown("<h3 style='text-align: center;'>New Price Entry</h3>", unsafe_allow_html=True)
    with st.form("entry_form", clear_on_submit=True):
        col_a, col_b = st.columns(2)
        with col_a:
            p = st.selectbox("Product", options=[""] + p_list)
            pr = st.number_input("Price HT (€)", min_value=0.0, step=0.01)
            # NEW: Quantity Column 1
            qty = st.number_input("Quantity", min_value=1, step=1, value=1)
            
        with col_b:
            d = st.selectbox("Distributor", options=[""] + d_list)
            tx = st.selectbox("Tax %", ["5.5%", "20%", "No tax"])
            # NEW: Comment Column 2
            cm = st.text_input("Comment (Optional)", placeholder="e.g. Broken box, promo...")
            
        dt = st.date_input("Date", date.today())
        
        if st.form_submit_button("Submit Entry"):
            if p and d and pr > 0 and qty > 0:
                conn.table("price_logs").insert({
                    "product": p, 
                    "distributor": d, 
                    "price": pr, 
                    "tax_rate": tx, 
                    "date": str(dt),
                    "quantity": qty,   # NEW
                    "comment": cm      # NEW
                }).execute()
                st.success("Saved Successfully")
                st.cache_data.clear()
                st.rerun()
            else: st.error("Please fill all mandatory fields (Product, Distributor, Price, Qty)")

    st.write("---")
    st.subheader("Previous Entries")
    df_history = get_logs()
    if not df_history.empty:
        st.dataframe(df_history, use_container_width=True, hide_index=True)

# ==========================================
# PAGE: REGISTER (Unchanged)
# ==========================================
elif selected == "Register":
    st.markdown("<h3 style='text-align: center;'>Register Management</h3>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    
    def handle_click(key_prefix, matches):
        sel = st.session_state.get(f"{key_prefix}_selection")
        if sel and sel["selection"]["rows"]:
            idx = sel["selection"]["rows"][0]
            st.session_state[f"{key_prefix}_input"] = matches[idx]

    # --- PRODUCT COLUMN ---
    with c1:
        st.write("**Products**")
        if "p_reg_input" not in st.session_state: st.session_state.p_reg_input = ""
        p_val = st.text_input("Product Name", key="p_reg_input", placeholder="Type to search...")
        
        matches_p = []
        if p_val:
            matches_p = [x for x in p_list if p_val.lower() in x.lower()]
            if matches_p and p_val.upper() not in p_list:
                st.caption("👇 Click below to select:")
                st.dataframe(pd.DataFrame(matches_p, columns=["Suggestions"]), use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row", key="p_reg_selection")
                handle_click("p_reg", matches_p)

        if p_val:
            if p_val.upper() in p_list:
                st.success(f"✅ Registered")
            else:
                if st.button(f"Save New: {p_val}"):
                    conn.table("products").insert({"name": p_val.strip().upper()}).execute()
                    st.success(f"Saved: {p_val}")
                    st.cache_data.clear()
                    st.rerun()

    # --- DISTRIBUTOR COLUMN ---
    with c2:
        st.write("**Distributors**")
        if "d_reg_input" not in st.session_state: st.session_state.d_reg_input = ""
        d_val = st.text_input("Distributor Name", key="d_reg_input", placeholder="Type to search...")
        
        matches_d = []
        if d_val:
            matches_d = [x for x in d_list if d_val.lower() in x.lower()]
            if matches_d and d_val.upper() not in d_list:
                st.caption("👇 Click below to select:")
                st.dataframe(pd.DataFrame(matches_d, columns=["Suggestions"]), use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row", key="d_reg_selection")
                handle_click("d_reg", matches_d)

        if d_val:
            if d_val.upper() in d_list:
                st.success(f"✅ Registered")
            else:
                if st.button(f"Save New: {d_val}"):
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
# PAGE: MANAGE (Updated columns)
# ==========================================
elif selected == "Manage":
    st.markdown("<h3 style='text-align: center;'>Database Management</h3>", unsafe_allow_html=True)
    df_manage = get_logs()
    
    if not df_manage.empty:
        with st.expander("🔍 Filter Options", expanded=True):
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
        
        filtered_df["Delete"] = False
        
        # Updated Editor with Qty and Comment
        edited_df = st.data_editor(
            filtered_df,
            key="manage_editor",
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
            column_config={
                "id": None,
                "Delete": st.column_config.CheckboxColumn("🗑️ Delete", help="Check to delete", default=False),
                "product": st.column_config.SelectboxColumn("Product", options=p_list, required=True),
                "distributor": st.column_config.SelectboxColumn("Distributor", options=d_list, required=True),
                "tax_rate": st.column_config.SelectboxColumn("Tax", options=["5.5%", "20%", "No tax"]),
                "quantity": st.column_config.NumberColumn("Qty", min_value=1, step=1, required=True),
                "comment": st.column_config.TextColumn("Comment")
            }
        )
        
        if st.button("Commit Changes"):
            state = st.session_state["manage_editor"]
            
            rows_to_delete = edited_df[edited_df["Delete"] == True]["id"].tolist()
            for idx in state["deleted_rows"]:
                if idx < len(filtered_df):
                    rows_to_delete.append(filtered_df.iloc[idx]["id"])
            
            if rows_to_delete:
                for rid in rows_to_delete:
                    conn.table("price_logs").delete().eq("id", rid).execute()
            
            for idx, updates in state["edited_rows"].items():
                if idx < len(filtered_df):
                    if "Delete" in updates: del updates["Delete"]
                    row_id = filtered_df.iloc[idx]["id"]
                    conn.table("price_logs").update(updates).eq("id", row_id).execute()
            
            st.success("Database Updated Successfully!")
            st.cache_data.clear()
            time.sleep(1)
            st.rerun()
            
    else: st.warning("No records found.")

# ==========================================
# PAGE: ANALYSER (SPLIT INTO 2 SECTIONS)
# ==========================================
elif selected == "Analyser":
    st.markdown("<h3 style='text-align: center;'>Analysis Center</h3>", unsafe_allow_html=True)
    
    # SPLIT INTO TABS
    tab1, tab2 = st.tabs(["💰 Price Analysis", "📦 Stock Analysis"])
    
    # --- SUB SECTION 1: PRICE ANALYSIS ---
    with tab1:
        target_p = st.selectbox("Select Product (Price)", [""] + p_list, key="price_target")
        
        if target_p:
            df = get_logs()
            df_sub = df[df['product'] == target_p].copy()
            
            if df_sub.empty:
                st.warning(f"⚠️ '{target_p}' has no data.")
            else:
                min_price = df_sub['price'].min()
                best_sellers = df_sub[df_sub['price'] == min_price]['distributor'].unique()
                
                st.markdown(f"""
                <div style='background-color:{CARD_BG}; padding:20px; border-radius:10px; border-left: 6px solid {PINK}; margin-bottom: 20px;'>
                    <p style='margin:0; color:#888;'>BEST PRICE FOUND</p>
                    <h1 style='margin:0; color:{PINK} !important;'>{min_price:.2f} €</h1>
                    <p>Available at: <strong>{", ".join(best_sellers)}</strong></p>
                </div>
                """, unsafe_allow_html=True)
                
                st.subheader("History Log")
                st.dataframe(df_sub[['date', 'distributor', 'price', 'quantity', 'comment']].sort_values('date', ascending=False), use_container_width=True, hide_index=True)
                
                st.write("---")
                st.subheader("TOTAL SPEND (SUMMED)")
                # Group by distributor -> Sum Price
                df_chart = df_sub.groupby('distributor')['price'].sum().reset_index()
                df_chart.columns = ['Distributor', 'Total Spend (€)']
                st.bar_chart(df_chart, x="Distributor", y="Total Spend (€)", color="Distributor", use_container_width=True)

    # --- SUB SECTION 2: STOCK ANALYSIS ---
    with tab2:
        target_s = st.selectbox("Select Product (Stock)", [""] + p_list, key="stock_target")
        
        if target_s:
            df = get_logs()
            df_stock = df[df['product'] == target_s].copy()
            
            if df_stock.empty:
                st.warning(f"⚠️ '{target_s}' has no stock data.")
            else:
                # 1. Calculate Stats
                total_qty = df_stock['quantity'].sum()
                
                # Group by distributor to find who supplied the most
                dist_qty = df_stock.groupby('distributor')['quantity'].sum().sort_values(ascending=False)
                top_dist = dist_qty.index[0] if not dist_qty.empty else "N/A"
                top_dist_qty = dist_qty.iloc[0] if not dist_qty.empty else 0
                
                # 2. UI CARD (Same Style)
                col_s1, col_s2 = st.columns(2)
                with col_s1:
                    st.markdown(f"""
                    <div style='background-color:{CARD_BG}; padding:20px; border-radius:10px; border-left: 6px solid #00d4ff; margin-bottom: 20px;'>
                        <p style='margin:0; color:#888;'>TOTAL LOGGED QTY</p>
                        <h1 style='margin:0; color:#00d4ff !important;'>{int(total_qty)} units</h1>
                    </div>
                    """, unsafe_allow_html=True)
                with col_s2:
                    st.markdown(f"""
                    <div style='background-color:{CARD_BG}; padding:20px; border-radius:10px; border-left: 6px solid #00d4ff; margin-bottom: 20px;'>
                        <p style='margin:0; color:#888;'>TOP SUPPLIER</p>
                        <h3 style='margin:0; color:white !important;'>{top_dist}</h3>
                        <p>Supplied: {int(top_dist_qty)} units</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                # 3. History
                st.subheader("Stock History")
                st.dataframe(df_stock[['date', 'distributor', 'quantity', 'comment']].sort_values('date', ascending=False), use_container_width=True, hide_index=True)
                
                st.write("---")
                
                # 4. Graph: Distributor vs Total Qty
                st.subheader("QUANTITY PER DISTRIBUTOR")
                df_qty_chart = df_stock.groupby('distributor')['quantity'].sum().reset_index()
                df_qty_chart.columns = ['Distributor', 'Total Quantity']
                st.bar_chart(df_qty_chart, x="Distributor", y="Total Quantity", color="Distributor", use_container_width=True)

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
