import streamlit as st
from st_supabase_connection import SupabaseConnection
import pandas as pd
from datetime import date, datetime
import plotly.express as px

# --- 1. CONFIGURATION & SETUP ---
st.set_page_config(
    page_title="Gmax Prix Distributors", 
    page_icon="📊", 
    layout="wide"
)

# Initialize Connection
conn = st.connection("supabase", type=SupabaseConnection)

# Constants
GMAX_PINK = "#ff1774"
ITEMS_PER_PAGE = 20

# Custom CSS
st.markdown(f"""
    <style>
    /* Global Pink Theme */
    h1, h2, h3, .stMetric label, .stMetric value {{ color: {GMAX_PINK} !important; font-weight: bold; }}
    div.stButton > button {{ background-color: {GMAX_PINK} !important; color: white !important; border-radius: 6px; border: none; font-weight: bold; }}
    .stTabs [aria-selected="true"] {{ background-color: {GMAX_PINK} !important; color: white !important; }}
    
    /* Compact Tables */
    .stDataFrame {{ font-size: 14px; }}
    </style>
    """, unsafe_allow_html=True)

# --- 2. HIGH-SPEED DATA FUNCTIONS (CACHED) ---
@st.cache_data(ttl=300) # Re-fetches data every 5 mins automatically
def fetch_master_lists():
    p = conn.table("products").select("name").execute()
    d = conn.table("distributors").select("name").execute()
    # Return simple sorted lists
    return sorted([r['name'] for r in p.data]), sorted([r['name'] for r in d.data])

@st.cache_data(ttl=60) # Caches price logs for speed
def fetch_price_logs():
    res = conn.table("price_logs").select("*").order("date", desc=True).execute()
    df = pd.DataFrame(res.data)
    return df

def clear_cache():
    st.cache_data.clear()

# --- 3. AUTHENTICATION ---
if "role" not in st.session_state:
    c1, c2 = st.columns([1,2])
    with c1: st.title("Gmax Login")
    with c2:
        pwd = st.text_input("Enter Security Key", type="password")
        if st.button("Access System"):
            if pwd == "admin123": st.session_state.role = "admin"
            elif pwd == "boss456": st.session_state.role = "viewer"
            else: st.error("Access Denied")
            if "role" in st.session_state: st.rerun()
    st.stop()

# --- 4. MAIN APP LAYOUT ---
st.title("💗 Gmax Prix Distributors")

# Fetch Data Once for Efficiency
p_list, d_list = fetch_master_lists()
df_main = fetch_price_logs()

# TAB ORDER: Entry -> Register -> Manage -> Analyser
if st.session_state.role == "viewer":
    tabs = st.tabs(["🔍 Analyser"])
    active_tab = "analyser"
else:
    tabs = st.tabs(["📥 Entry", "📝 Register", "✏️ Manage", "🔍 Analyser"])
    active_tab = "admin_mode"

# --- TAB 1: ENTRY ---
if st.session_state.role == "admin":
    with tabs[0]:
        st.subheader("New Price Entry")
        with st.form("entry_form", clear_on_submit=True):
            c1, c2, c3, c4 = st.columns(4)
            p_input = c1.selectbox("Product", ["Choose..."] + p_list)
            d_input = c2.selectbox("Distributor", ["Choose..."] + d_list)
            price_input = c3.number_input("Price HT (€)", min_value=0.0, step=0.01)
            date_input = c4.date_input("Date", date.today())
            
            if st.form_submit_button("💾 Save Entry"):
                if p_input != "Choose..." and d_input != "Choose...":
                    conn.table("price_logs").insert({
                        "product": p_input, 
                        "distributor": d_input, 
                        "price": price_input, 
                        "date": str(date_input)
                    }).execute()
                    clear_cache() # Reset cache so table updates immediately
                    st.success("Saved!")
                    st.rerun()
                else:
                    st.error("Please choose a Product and Distributor.")

        st.markdown("---")
        st.subheader("Recent Entries (Paginated)")
        
        # 1. Filters for Table
        if not df_main.empty:
            # FORCE DATE CONVERSION FOR DISPLAY
            df_display = df_main.copy()
            df_display['date'] = pd.to_datetime(df_display['date'])

            fc1, fc2, fc3 = st.columns(3)
            f_prod = fc1.multiselect("Filter Product", p_list)
            f_dist = fc2.multiselect("Filter Distributor", d_list)
            f_date = fc3.date_input("Filter Date", [])

            # Apply Logic
            if f_prod: df_display = df_display[df_display['product'].isin(f_prod)]
            if f_dist: df_display = df_display[df_display['distributor'].isin(f_dist)]
            if isinstance(f_date, tuple) and len(f_date) == 2:
                start_d, end_d = f_date
                df_display = df_display[(df_display['date'].dt.date >= start_d) & (df_display['date'].dt.date <= end_d)]
            elif isinstance(f_date, date): # Single date selected
                 df_display = df_display[df_display['date'].dt.date == f_date]

            # 2. Pagination Logic
            total_rows = len(df_display)
            total_pages = max(1, (total_rows // ITEMS_PER_PAGE) + (1 if total_rows % ITEMS_PER_PAGE > 0 else 0))
            
            col_pag1, col_pag2 = st.columns([1, 4])
            current_page = col_pag1.number_input("Page", min_value=1, max_value=total_pages, step=1)
            col_pag2.info(f"Showing page {current_page} of {total_pages} ({total_rows} total entries)")
            
            # Slice Data
            start_idx = (current_page - 1) * ITEMS_PER_PAGE
            end_idx = start_idx + ITEMS_PER_PAGE
            df_page = df_display.iloc[start_idx:end_idx].copy()
            
            # Convert to pure date object for cleaner display
            df_page['date'] = df_page['date'].dt.date

            # 3. Display Table
            st.dataframe(
                df_page,
                column_config={
                    "date": st.column_config.DateColumn("Date", format="DD MM YYYY"),
                    "price": st.column_config.NumberColumn("Price HT (€)", format="%.2f €")
                },
                use_container_width=True,
                hide_index=True
            )

# --- TAB 2: REGISTER ---
if st.session_state.role == "admin":
    with tabs[1]:
        rc1, rc2 = st.columns(2)
        
        # Product Registration
        with rc1:
            st.write("### 📦 Products")
            new_p = st.text_input("Type Product Name", key="p_reg")
            
            # Auto-check logic
            if new_p:
                if new_p in p_list:
                    st.warning(f"⚠️ '{new_p}' is already registered!")
                else:
                    if st.button("Add Product"):
                        conn.table("products").insert({"name": new_p}).execute()
                        clear_cache()
                        st.success(f"Added {new_p}")
                        st.rerun()
            
            with st.expander("See Registered Products"):
                st.dataframe(pd.DataFrame(p_list, columns=["Name"]), use_container_width=True)

        # Distributor Registration
        with rc2:
            st.write("### 🚚 Distributors")
            new_d = st.text_input("Type Distributor Name", key="d_reg")
            
            if new_d:
                if new_d in d_list:
                    st.warning(f"⚠️ '{new_d}' is already registered!")
                else:
                    if st.button("Add Distributor"):
                        conn.table("distributors").insert({"name": new_d}).execute()
                        clear_cache()
                        st.success(f"Added {new_d}")
                        st.rerun()

            with st.expander("See Registered Distributors"):
                st.dataframe(pd.DataFrame(d_list, columns=["Name"]), use_container_width=True)

# --- TAB 3: MANAGE ---
if st.session_state.role == "admin":
    with tabs[2]:
        st.subheader("✏️ Edit or Delete Entries")
        
        if not df_main.empty:
            # FIX FOR DATE ERROR: Ensure column is definitely datetime objects
            df_edit = df_main.copy()
            df_edit['date'] = pd.to_datetime(df_edit['date']).dt.date
            
            # Filters
            mc1, mc2, mc3 = st.columns(3)
            m_prod = mc1.multiselect("Filter Product", p_list, key="m_p")
            m_dist = mc2.multiselect("Filter Distributor", d_list, key="m_d")
            
            if m_prod: df_edit = df_edit[df_edit['product'].isin(m_prod)]
            if m_dist: df_edit = df_edit[df_edit['distributor'].isin(m_dist)]

            st.info("💡 Edit cells directly. Product/Distributor changes are restricted to registered items.")
            
            changes = st.data_editor(
                df_edit,
                num_rows="dynamic",
                use_container_width=True,
                hide_index=True,
                key="editor_manage",
                column_config={
                    "id": None, # Hide ID
                    "product": st.column_config.SelectboxColumn("Product", options=p_list, required=True),
                    "distributor": st.column_config.SelectboxColumn("Distributor", options=d_list, required=True),
                    "price": st.column_config.NumberColumn("Price HT (€)", format="%.2f €"),
                    "date": st.column_config.DateColumn("Date", format="DD MM YYYY")
                }
            )

            if st.button("💾 Save All Changes"):
                # 1. Deletes
                if st.session_state["editor_manage"]["deleted_rows"]:
                    for row in st.session_state["editor_manage"]["deleted_rows"]:
                        del_id = df_edit.iloc[row]["id"]
                        conn.table("price_logs").delete().eq("id", del_id).execute()
                
                # 2. Edits
                if st.session_state["editor_manage"]["edited_rows"]:
                    for row_idx, updates in st.session_state["editor_manage"]["edited_rows"].items():
                        edit_id = df_edit.iloc[row_idx]["id"]
                        # Fix date serialization
                        if "date" in updates: updates["date"] = str(updates["date"])
                        conn.table("price_logs").update(updates).eq("id", edit_id).execute()
                
                clear_cache()
                st.success("Database Updated Successfully!")
                st.rerun()

# --- TAB 4: ANALYSER ---
analyser_tab_idx = 0 if st.session_state.role == "viewer" else 3
with tabs[analyser_tab_idx]:
    st.subheader("📊 Price Analytics")
    
    target_p = st.selectbox("Select Product to Analyze", ["Choose..."] + p_list)
    
    if target_p != "Choose...":
        # Filter data for this product
        df_an = df_main[df_main['product'] == target_p].copy()
        
        if not df_an.empty:
            df_an['date'] = pd.to_datetime(df_an['date'])
            
            # 1. Best Prix Section
            min_price = df_an['price'].min()
            best_rows = df_an[df_an['price'] == min_price]
            
            st.divider()
            st.markdown(f"### 🏆 Best Prix: {min_price:.2f} €")
            
            # List all distributors with this best price
            for _, row in best_rows.iterrows():
                d_date = row['date'].strftime("%d %m %Y")
                st.success(f"📍 **{row['distributor']}** on {d_date}")

            st.divider()
            
            # 2. Spend Analysis Graph
            c_g1, c_g2 = st.columns([2, 1])
            
            with c_g1:
                st.markdown("### 💰 Spend by Distributor")
                spend_df = df_an.groupby("distributor")["price"].sum().reset_index()
                fig = px.bar(
                    spend_df, 
                    x="distributor", 
                    y="price", 
                    text_auto='.2s',
                    color="distributor",
                    color_discrete_sequence=[GMAX_PINK, "#ff5c9d", "#ff8fb9"]
                )
                fig.update_layout(showlegend=False, xaxis_title=None, yaxis_title="Total (€)")
                st.plotly_chart(fig, use_container_width=True)

            with c_g2:
                st.markdown("### 📜 History")
                # Format date for display
                df_an['date'] = df_an['date'].dt.date
                st.dataframe(
                    df_an[['date', 'distributor', 'price']].sort_values('date', ascending=False),
                    column_config={
                        "date": st.column_config.DateColumn("Date", format="DD MM YYYY"),
                        "price": st.column_config.NumberColumn("Price (€)", format="%.2f €")
                    },
                    use_container_width=True,
                    hide_index=True
                )
        else:
            st.info("No data found for this product.")
