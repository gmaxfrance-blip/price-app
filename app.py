import streamlit as st
from st_supabase_connection import SupabaseConnection
import pandas as pd
from datetime import date
import plotly.express as px
import io 

# --- 1. CONFIGURATION ---
LOGO_URL = "https://raw.githubusercontent.com/gmaxfrance-blip/price-app/a423573672203bc38f5fbcf5f5a56ac18380ebb3/dp%20logo.png"
GMAX_PINK = "#ff1774"
ITEMS_PER_PAGE = 20

st.set_page_config(
    page_title="Gmax Prix", 
    page_icon=LOGO_URL,
    layout="wide"
)

# Connect to Supabase
conn = st.connection("supabase", type=SupabaseConnection)

# CSS for Speed & Look
st.markdown(f"""
    <style>
    .stApp {{ background-color: #ffffff; }}
    h1, h2, h3, .stMetric label {{ color: {GMAX_PINK} !important; font-weight: bold; }}
    div.stButton > button {{ background-color: {GMAX_PINK} !important; color: white !important; border-radius: 6px; border: none; }}
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    </style>
    """, unsafe_allow_html=True)

# --- 2. FAST DATA LOADING (CACHED) ---
@st.cache_data(ttl=600)
def get_master_lists():
    p = conn.table("products").select("name").execute()
    d = conn.table("distributors").select("name").execute()
    return sorted([r['name'] for r in p.data]), sorted([r['name'] for r in d.data])

def get_recent_logs():
    res = conn.table("price_logs").select("*").order("date", desc=True).execute()
    df = pd.DataFrame(res.data)
    if not df.empty:
        df['date'] = pd.to_datetime(df['date'])
    return df

# --- 3. LOGIN ---
if "role" not in st.session_state:
    c1, c2 = st.columns([1,2])
    with c1:
        st.image(LOGO_URL, width=100)
    with c2:
        st.title("🔐 Gmax Login")
        pwd = st.text_input("Enter Key", type="password")
        if st.button("Login"):
            if pwd == "admin123": st.session_state.role = "admin"
            elif pwd == "boss456": st.session_state.role = "viewer"
            else: st.error("Access Denied")
            if "role" in st.session_state: st.rerun()
    st.stop()

# --- 4. SIDEBAR MENU ---
st.sidebar.image(LOGO_URL, width=120) 
st.sidebar.title("Navigation")

if st.session_state.role == "viewer":
    options = ["🔍 Analyser", "📤 Export"] 
else:
    options = ["📥 Entry", "📝 Register", "✏️ Manage", "🔍 Analyser", "📤 Export"]

selected_page = st.sidebar.radio("Go to", options)

if st.sidebar.button("Logout"):
    st.session_state.clear()
    st.rerun()

# Load Data Once
p_names, d_names = get_master_lists()

# --- PAGE: ENTRY ---
if selected_page == "📥 Entry":
    st.title("📥 New Price Entry")
    
    with st.form("entry_form", clear_on_submit=True):
        c1, c2, c3, c4 = st.columns(4)
        p = c1.selectbox("Product", ["Choose..."] + p_names)
        d = c2.selectbox("Distributor", ["Choose..."] + d_names)
        pr = c3.number_input("Price HT (€)", min_value=0.0, step=0.01)
        dt = c4.date_input("Date", date.today())
        
        if st.form_submit_button("Save Entry"):
            if p != "Choose..." and d != "Choose...":
                conn.table("price_logs").insert({
                    "product": p, "distributor": d, "price": pr, "date": str(dt)
                }).execute()
                st.success("✅ Saved!")
                st.cache_data.clear()
                st.rerun()
            else:
                st.error("Please select Product & Distributor")

    st.write("---")
    st.subheader("Recent Entries")
    df = get_recent_logs()
    
    if not df.empty:
        fc1, fc2 = st.columns(2)
        fp = fc1.multiselect("Filter Product", p_names)
        fd = fc2.multiselect("Filter Distributor", d_names)
        
        # --- FIX: THIS IS WHERE YOUR ERROR WAS ---
        if fp: df = df[df['product'].isin(fp)]
        if fd: df = df[df['distributor'].isin(fd)]
        # -----------------------------------------
        
        # Pagination
        rows = len(df)
        if rows > ITEMS_PER_PAGE:
            max_p = (rows // ITEMS_PER_PAGE) + 1
            cur_p = st.number_input("Page", 1, max_p)
            df_show = df.iloc[(cur_p-1)*ITEMS_PER_PAGE : cur_p*ITEMS_PER_PAGE].copy()
        else:
            df_show = df.copy()
            
        df_show['date_str'] = df_show['date'].dt.strftime('%d-%m-%Y')
        
        st.dataframe(
            df_show[['date_str', 'product', 'distributor', 'price']],
            column_config={
                "date_str": "Date",
                "price": st.column_config.NumberColumn("Price HT (€)", format="%.2f €")
            },
            use_container_width=True, hide_index=True
        )

# --- PAGE: REGISTER ---
elif selected_page == "📝 Register":
    st.title("📝 Register New Items")
    c1, c2 = st.columns(2)
    
    with c1:
        st.subheader("Add Product")
        new_p = st.text_input("Name", key="np")
        if st.button("Save Product"):
            if new_p and new_p not in p_names:
                conn.table("products").insert({"name": new_p}).execute()
                st.cache_data.clear()
                st.success(f"Added {new_p}")
                st.rerun()
            elif new_p in p_names:
                st.warning("Already exists")
        st.dataframe(pd.DataFrame(p_names, columns=["Products"]), use_container_width=True)

    with c2:
        st.subheader("Add Distributor")
        new_d = st.text_input("Name", key="nd")
        if st.button("Save Distributor"):
            if new_d and new_d not in d_names:
                conn.table("distributors").insert({"name": new_d}).execute()
                st.cache_data.clear()
                st.success(f"Added {new_d}")
                st.rerun()
            elif new_d in d_names:
                st.warning("Already exists")
        st.dataframe(pd.DataFrame(d_names, columns=["Distributors"]), use_container_width=True)

# --- PAGE: MANAGE ---
elif selected_page == "✏️ Manage":
    st.title("✏️ Manage Data")
    df_m = get_recent_logs()
    
    if not df_m.empty:
        # Fix date type for editor
        df_m['date'] = df_m['date'].dt.date 
        
        edited = st.data_editor(
            df_m,
            key="editor",
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
            column_config={
                "id": None, 
                "product": st.column_config.SelectboxColumn("Product", options=p_names, required=True),
                "distributor": st.column_config.SelectboxColumn("Distributor", options=d_names, required=True),
                "date": st.column_config.DateColumn("Date", format="DD-MM-YYYY"),
                "price": st.column_config.NumberColumn("Price (€)", format="%.2f €")
            }
        )
        
        if st.button("💾 Save Changes"):
            for row in st.session_state["editor"]["deleted_rows"]:
                del_id = df_m.iloc[row]["id"]
                conn.table("price_logs").delete().eq("id", del_id).execute()
            for idx, updates in st.session_state["editor"]["edited_rows"].items():
                rid = df_m.iloc[idx]["id"]
                if "date" in updates: updates["date"] = str(updates["date"])
                conn.table("price_logs").update(updates).eq("id", rid).execute()
            
            st.success("Updated!")
            st.rerun()

# --- PAGE: ANALYSER ---
elif selected_page == "🔍 Analyser":
    st.title("🔍 Analyser")
    sel = st.selectbox("Select Product", ["Choose..."] + p_names)
    
    if sel != "Choose...":
        df = get_recent_logs()
        df_an = df[df['product'] == sel].copy()
        
        if not df_an.empty:
            min_p = df_an['price'].min()
            st.markdown(f"### 🏆 Best Prix: **{min_p:.2f} €**")
            
            best = df_an[df_an['price'] == min_p]
            for _, r in best.iterrows():
                d_str = r['date'].strftime('%d-%m-%Y')
                st.info(f"📍 **{r['distributor']}** ({d_str})")
            
            st.divider()
            
            c1, c2 = st.columns([2,1])
            with c1:
                st.subheader("Spend Analysis")
                grp = df_an.groupby("distributor")['price'].sum().reset_index()
                fig = px.bar(grp, x="distributor", y="price", color="distributor", text_auto='.2s', color_discrete_sequence=[GMAX_PINK])
                fig.update_layout(showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
            
            with c2:
                st.subheader("History")
                df_an['date_str'] = df_an['date'].dt.strftime('%d-%m-%Y')
                st.dataframe(df_an[['date_str', 'distributor', 'price']], use_container_width=True, hide_index=True)

# --- PAGE: EXPORT (NEW!) ---
elif selected_page == "📤 Export":
    st.title("📤 Export to Excel")
    st.info("Select a date range to download your data for backup or accounting.")
    
    # Date Range Selectors
    c1, c2 = st.columns(2)
    start_d = c1.date_input("Start Date", date(2025, 1, 1))
    end_d = c2.date_input("End Date", date.today())
    
    if st.button("Generate Preview"):
        df_ex = get_recent_logs()
        
        if not df_ex.empty:
            # Sort by Date descending (Newest first)
            # Filter by Date Range mask
            mask = (df_ex['date'].dt.date >= start_d) & (df_ex['date'].dt.date <= end_d)
            df_filtered = df_ex[mask].sort_values("date", ascending=False)
            
            st.write(f"### Found {len(df_filtered)} records")
            
            # Show Preview Table
            df_display = df_filtered.copy()
            df_display['date'] = df_display['date'].dt.strftime('%d-%m-%Y')
            st.dataframe(df_display[['date', 'product', 'distributor', 'price']], use_container_width=True)
            
            # Create Excel File in Memory
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                # Clean up for export
                export_clean = df_filtered[['date', 'product', 'distributor', 'price']].copy()
                # Format date in Excel as DD-MM-YYYY string for compatibility
                export_clean['date'] = export_clean['date'].dt.strftime('%d-%m-%Y')
                export_clean.to_excel(writer, index=False, sheet_name='Gmax_Data')
                
            # Download Button
            st.download_button(
                label="📥 Download Excel File",
                data=buffer,
                file_name=f"Gmax_Export_{start_d}_{end_d}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.warning("No data found in database.")
