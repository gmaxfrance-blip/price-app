import streamlit as st
from st_supabase_connection import SupabaseConnection
import pandas as pd
from datetime import date
import plotly.express as px

# --- 1. SETUP & CONFIGURATION ---
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

# CSS: Pink Theme + Hide Streamlit Menu for Speed
st.markdown(f"""
    <style>
    h1, h2, h3, .stMetric label {{ color: {GMAX_PINK} !important; font-weight: bold; }}
    div.stButton > button {{ background-color: {GMAX_PINK} !important; color: white !important; border-radius: 6px; border: none; font-weight: bold; }}
    /* Hide top padding to make it look faster/cleaner */
    .block-container {{ padding-top: 2rem; }}
    </style>
    """, unsafe_allow_html=True)

# --- 2. CACHED DATA FUNCTIONS (SPEED BOOST) ---
@st.cache_data(ttl=600)
def get_master_data():
    """Fetches simple lists of Products and Distributors. Cached for 10 mins."""
    p = conn.table("products").select("name").execute()
    d = conn.table("distributors").select("name").execute()
    return sorted([r['name'] for r in p.data]), sorted([r['name'] for r in d.data])

def get_price_logs():
    """Fetches price history. NOT cached heavily to ensure immediate updates."""
    # We order by date descending so the newest is always on top
    res = conn.table("price_logs").select("*").order("date", desc=True).execute()
    df = pd.DataFrame(res.data)
    if not df.empty:
        # Crucial: Convert to datetime objects for math, but we will format strings for display later
        df['date'] = pd.to_datetime(df['date'])
    return df

def clear_master_cache():
    """Clears cache only when new product/distributor is added"""
    get_master_data.clear()

# --- 3. LOGIN SYSTEM ---
if "role" not in st.session_state:
    c1, c2 = st.columns([1,2])
    with c1: st.title("🔐 Login")
    with c2:
        pwd = st.text_input("Password", type="password")
        if st.button("Enter"):
            if pwd == "admin123": st.session_state.role = "admin"
            elif pwd == "boss456": st.session_state.role = "viewer"
            else: st.error("Wrong Password")
            if "role" in st.session_state: st.rerun()
    st.stop()

# --- 4. SIDEBAR NAVIGATION (Fixes Redirect Issue) ---
# Using Sidebar ensures the app "remembers" which page you are on
st.sidebar.title("Navigation")
if st.session_state.role == "viewer":
    page = st.sidebar.radio("Go to:", ["🔍 Analyser"])
else:
    page = st.sidebar.radio("Go to:", ["📥 Entry", "📝 Register", "✏️ Manage", "🔍 Analyser"])

st.sidebar.markdown("---")
if st.sidebar.button("Logout"):
    st.session_state.clear()
    st.rerun()

# Load Master Data (Fast)
p_names, d_names = get_master_data()

# --- PAGE: ENTRY ---
if page == "📥 Entry":
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
                # We do NOT rerun here immediately to keep the form clean, 
                # but the table below will update on next interaction.
                # To force table update immediately without page jump:
                st.cache_data.clear() 
                st.rerun()
            else:
                st.error("Select Product & Distributor")

    st.write("### 🕒 Recent Entries")
    df = get_price_logs()
    if not df.empty:
        # PAGINATION & FILTERS
        col_f1, col_f2 = st.columns(2)
        fil_p = col_f1.multiselect("Filter Product", p_names)
        fil_d = col_f2.multiselect("Filter Distributor", d_names)
        
        # Apply Filters
        if fil_p: df = df[df['product'].isin(fil_p)]
        if fil_d: df = df[df['distributor'].isin(fil_d)]
        
        # DISPLAY: Force Date Format to DD-MM-YYYY String
        # This converts the date object to a text string "04-12-2025" for display
        df['date_str'] = df['date'].dt.strftime('%d-%m-%Y')
        
        # Pagination Logic
        rows = len(df)
        if rows > ITEMS_PER_PAGE:
            max_page = (rows // ITEMS_PER_PAGE) + 1
            cur_page = st.number_input("Page", 1, max_page)
            start = (cur_page - 1) * ITEMS_PER_PAGE
            end = start + ITEMS_PER_PAGE
            df_display = df.iloc[start:end]
        else:
            df_display = df

        # Show Table (Clean)
        st.dataframe(
            df_display[['date_str', 'product', 'distributor', 'price']],
            column_config={
                "date_str": "Date",
                "price": st.column_config.NumberColumn("Price HT (€)", format="%.2f €")
            },
            use_container_width=True,
            hide_index=True
        )

# --- PAGE: REGISTER ---
elif page == "📝 Register":
    st.title("📝 Register New Items")
    r1, r2 = st.columns(2)
    
    with r1:
        st.subheader("📦 Product")
        with st.form("reg_p"):
            np = st.text_input("New Product Name")
            if st.form_submit_button("Add Product"):
                if np and np not in p_names:
                    conn.table("products").insert({"name": np}).execute()
                    clear_master_cache()
                    st.success(f"Added {np}")
                    st.rerun()
                elif np in p_names:
                    st.warning("Already Registered")
        
        with st.expander("View All Products"):
            st.table(pd.DataFrame(p_names, columns=["Name"]))

    with r2:
        st.subheader("🚚 Distributor")
        with st.form("reg_d"):
            nd = st.text_input("New Distributor Name")
            if st.form_submit_button("Add Distributor"):
                if nd and nd not in d_names:
                    conn.table("distributors").insert({"name": nd}).execute()
                    clear_master_cache()
                    st.success(f"Added {nd}")
                    st.rerun()
                elif nd in d_names:
                    st.warning("Already Registered")

        with st.expander("View All Distributors"):
            st.table(pd.DataFrame(d_names, columns=["Name"]))

# --- PAGE: MANAGE ---
elif page == "✏️ Manage":
    st.title("✏️ Edit / Delete Data")
    df_m = get_price_logs()
    
    if not df_m.empty:
        # Filters
        mf1, mf2 = st.columns(2)
        m_p = mf1.multiselect("Find Product", p_names)
        m_d = mf2.multiselect("Find Distributor", d_names)
        
        if m_p: df_m = df_m[df_m['product'].isin(m_p)]
        if m_d: df_m = df_m[df_m['distributor'].isin(m_d)]
        
        # Prepare for Editor
        # We need actual date objects for the calendar picker to work in editing mode
        df_m['date'] = df_m['date'].dt.date
        
        edited = st.data_editor(
            df_m,
            key="editor",
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
            column_config={
                "id": None, # Hide ID
                "product": st.column_config.SelectboxColumn("Product", options=p_names, required=True),
                "distributor": st.column_config.SelectboxColumn("Distributor", options=d_names, required=True),
                "date": st.column_config.DateColumn("Date", format="DD-MM-YYYY"), # Editor format
                "price": st.column_config.NumberColumn("Price HT (€)", format="%.2f €")
            }
        )
        
        if st.button("💾 Save All Changes"):
            # 1. Handle Deletions
            for row in st.session_state["editor"]["deleted_rows"]:
                # Access ID safely using the original index
                del_id = df_m.iloc[row]["id"] 
                conn.table("price_logs").delete().eq("id", del_id).execute()
            
            # 2. Handle Edits
            for idx, updates in st.session_state["editor"]["edited_rows"].items():
                row_id = df_m.iloc[idx]["id"]
                # Convert date back to string for DB
                if "date" in updates: updates["date"] = str(updates["date"])
                conn.table("price_logs").update(updates).eq("id", row_id).execute()
            
            st.success("Updated!")
            st.rerun()

# --- PAGE: ANALYSER ---
elif page == "🔍 Analyser":
    st.title("🔍 Price Analyser")
    
    sel_p = st.selectbox("Select Product", ["Choose..."] + p_names)
    
    if sel_p != "Choose...":
        df_all = get_price_logs()
        df_an = df_all[df_all['product'] == sel_p].copy()
        
        if not df_an.empty:
            # Stats
            min_p = df_an['price'].min()
            best_rows = df_an[df_an['price'] == min_p]
            
            st.divider()
            st.markdown(f"### 🏆 Best Prix: **{min_p:.2f} €**")
            
            for _, r in best_rows.iterrows():
                # European Date Format Display
                d_txt = r['date'].strftime('%d-%m-%Y')
                st.info(f"📍 **{r['distributor']}** on {d_txt}")
            
            st.divider()
            
            # Graph
            c_g1, c_g2 = st.columns([2,1])
            with c_g1:
                st.subheader("💰 Spend by Distributor")
                grp = df_an.groupby("distributor")['price'].sum().reset_index()
                fig = px.bar(grp, x="distributor", y="price", color="distributor", 
                             text_auto='.2s', color_discrete_sequence=[GMAX_PINK])
                fig.update_layout(showlegend=False, yaxis_title="Total €", xaxis_title="")
                st.plotly_chart(fig, use_container_width=True)
            
            with c_g2:
                st.subheader("📜 History")
                df_an['date_str'] = df_an['date'].dt.strftime('%d-%m-%Y')
                st.dataframe(
                    df_an[['date_str', 'distributor', 'price']],
                    column_config={"date_str": "Date", "price": st.column_config.NumberColumn("Price", format="%.2f €")},
                    use_container_width=True, hide_index=True
                )
