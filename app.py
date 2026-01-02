import streamlit as st
from st_supabase_connection import SupabaseConnection
import pandas as pd
from datetime import date

# --- 1. CLOUD CONNECTION ---
conn = st.connection("supabase", type=SupabaseConnection)

# --- 2. UI BRANDING & DYNAMIC COLOR (#ff1774) ---
LOGO_URL = "https://raw.githubusercontent.com/gmaxfrance-blip/price-app/a423573672203bc38f5fbcf5f5a56ac18380ebb3/dp%20logo.png"

st.set_page_config(
    page_title="Gmax Prix Distributors", 
    page_icon=LOGO_URL, 
    layout="wide"
)

# Custom CSS for Gmax Pink (#ff1774)
st.markdown(f"""
    <style>
    h1, h2, h3, .stMetric label {{ color: #ff1774 !important; font-weight: bold; }}
    div.stButton > button {{
        background-color: #ff1774 !important;
        color: white !important;
        border-radius: 8px !important;
        border: none !important;
    }}
    .stTabs [aria-selected="true"] {{
        background-color: #ff1774 !important;
        color: white !important;
    }}
    </style>
    """, unsafe_allow_html=True)

# --- 3. ACCESS CONTROL ---
if "role" not in st.session_state:
    st.image(LOGO_URL, width=120)
    st.title("Gmax Prix Login")
    pwd = st.text_input("Security Key", type="password")
    if st.button("Sign In"):
        if pwd == "admin123": st.session_state.role = "admin"
        elif pwd == "boss456": st.session_state.role = "viewer"
        else: st.error("Access Denied")
        if "role" in st.session_state: st.rerun()
    st.stop()

# --- 4. HEADER ---
st.image(LOGO_URL, width=80)
st.title("Gmax Prix Distributors")

# --- 5. TABS LOGIC ---
if st.session_state.role == "viewer":
    tabs_list = ["🔍 Analyser"]
else:
    tabs_list = ["📥 Entry", "🔍 Analyser", "📝 Register", "✏️ Manage"]

active_tabs = st.tabs(tabs_list)

# FETCH DATA HELPERS
prods = conn.table("products").select("name").execute()
dists = conn.table("distributors").select("name").execute()
p_names = sorted([r['name'] for r in prods.data])
d_names = sorted([r['name'] for r in dists.data])

# --- TAB 1: ENTRY (ADMIN ONLY) ---
if st.session_state.role == "admin":
    with active_tabs[0]:
        with st.form("entry_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            p = c1.selectbox("Product", ["Choose..."] + p_names)
            d = c1.selectbox("Distributor", ["Choose..."] + d_names)
            pr = c2.number_input("Price HT (€)", min_value=0.0, step=0.01, format="%.2f")
            dt = c2.date_input("Date", date.today())
            if st.form_submit_button("Add Price Entry"):
                if p != "Choose..." and d != "Choose...":
                    conn.table("price_logs").insert({"product": p, "distributor": d, "price": pr, "date": str(dt)}).execute()
                    st.success("Synchronized!")
                    st.rerun()

        st.write("### Recent Logs (Paginated)")
        logs_raw = conn.table("price_logs").select("*").order("date", desc=True).execute()
        if logs_raw.data:
            df_logs = pd.DataFrame(logs_raw.data)
            # Format Date to DMY
            df_logs['date'] = pd.to_datetime(df_logs['date']).dt.strftime('%d/%m/%Y')
            df_logs = df_logs.rename(columns={"price": "Price HT (€)"})
            # Automatic pagination via Streamlit dataframe
            st.dataframe(df_logs[['date', 'product', 'distributor', 'Price HT (€)']], use_container_width=True, hide_index=True)

# --- TAB 2: ANALYSER ---
analyser_idx = 0 if st.session_state.role == "viewer" else 1
with active_tabs[analyser_idx]:
    search_p = st.selectbox("Search Market Data", ["Choose Product..."] + p_names)
    if search_p != "Choose Product...":
        data = conn.table("price_logs").select("*").eq("product", search_p).execute()
        df = pd.DataFrame(data.data)
        if not df.empty:
            df['date'] = pd.to_datetime(df['date']).dt.strftime('%d/%m/%Y')
            min_p = df['price'].min()
            st.metric("Lowest Market Price", f"{min_p:.2f} €")
            st.dataframe(df[['date', 'distributor', 'price']].rename(columns={"price": "Price HT (€)"}), use_container_width=True, hide_index=True)

# --- TAB 4: MANAGE (ADMIN ONLY - EDIT/DELETE IN ROWS) ---
if st.session_state.role == "admin":
    with active_tabs[3]:
        st.subheader("Edit or Delete Row Data")
        st.caption("Instructions: Double-click a cell to edit. Select a row and press 'Delete' on your keyboard to remove.")
        
        # Data Editor implementation
        raw_m = conn.table("price_logs").select("*").order("date", desc=True).execute()
        df_m = pd.DataFrame(raw_m.data)
        
        if not df_m.empty:
            edited_df = st.data_editor(
                df_m,
                num_rows="dynamic",
                disabled=["id"],
                column_config={
                    "price": st.column_config.NumberColumn("Price HT (€)", format="%.2f €"),
                    "date": st.column_config.DateColumn("Date", format="DD/MM/YYYY")
                },
                use_container_width=True,
                hide_index=True,
                key="manage_editor"
            )

            if st.button("Save Changes to Cloud"):
                state = st.session_state["manage_editor"]
                
                # Handle Deletes
                for idx in state["deleted_rows"]:
                    row_id = df_m.iloc[idx]["id"]
                    conn.table("price_logs").delete().eq("id", row_id).execute()
                
                # Handle Edits
                for idx, updates in state["edited_rows"].items():
                    row_id = df_m.iloc[idx]["id"]
                    conn.table("price_logs").update(updates).eq("id", row_id).execute()
                
                st.success("Database Updated!")
                st.rerun()

st.sidebar.button("Logout", on_click=lambda: st.session_state.clear())
