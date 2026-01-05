import streamlit as st
from st_supabase_connection import SupabaseConnection
from streamlit_option_menu import option_menu
import pandas as pd
from datetime import date
import plotly.express as px
import io 

# --- 1. CONFIGURATION ---
LOGO_URL = "https://raw.githubusercontent.com/gmaxfrance-blip/price-app/a423573672203bc38f5fbcf5f5a56ac18380ebb3/dp%20logo.png"
PINK = "#ff1774"
HASH_WHITE = "#f8f9fa" # The "Hash White" you requested

st.set_page_config(page_title="Gmax Management", page_icon=LOGO_URL, layout="wide")
conn = st.connection("supabase", type=SupabaseConnection)

# --- 2. PROFESSIONAL CSS (PINK & WHITE THEME) ---
st.markdown(f"""
    <style>
    /* Main Background - Hash White */
    .stApp {{ background-color: {HASH_WHITE}; }}
    
    /* Clean Cards (White Blocks) */
    div.block-container {{ padding-top: 2rem; }}
    div[data-testid="stForm"] {{ background-color: white; padding: 20px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
    
    /* Text Colors */
    h1, h2, h3, h4 {{ color: #333333 !important; font-family: 'Arial', sans-serif; }}
    strong {{ color: {PINK}; }}
    
    /* Buttons - Pink & Fast */
    div.stButton > button {{ 
        background-color: {PINK}; 
        color: white; 
        border: none; 
        border-radius: 4px; 
        font-weight: bold;
    }}
    div.stButton > button:hover {{ background-color: #d0125f; }}
    
    /* Remove clutter */
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    header {{visibility: hidden;}}
    </style>
    """, unsafe_allow_html=True)

# --- 3. HIGH-SPEED CACHING ---
@st.cache_data(ttl=600)
def get_master_data():
    """Loads Products & Distributors instantly from memory."""
    p = conn.table("products").select("name").execute()
    d = conn.table("distributors").select("name").execute()
    return sorted([r['name'] for r in p.data]), sorted([r['name'] for r in d.data])

def get_logs():
    """Fetches logs live. No cache here so you see updates instantly."""
    res = conn.table("price_logs").select("*").order("date", desc=True).execute()
    df = pd.DataFrame(res.data)
    if not df.empty: df['date'] = pd.to_datetime(df['date'])
    return df

# --- 4. LOGIN SYSTEM ---
if "role" not in st.session_state:
    c1, c2, c3 = st.columns([1, 1, 1])
    with c2:
        st.image(LOGO_URL, width=120)
        st.markdown("<h3 style='text-align: center;'>System Access</h3>", unsafe_allow_html=True)
        pwd = st.text_input("Password", type="password", label_visibility="collapsed")
        if st.button("Login", use_container_width=True):
            if pwd == "admin123": st.session_state.role = "admin"
            elif pwd == "boss456": st.session_state.role = "viewer"
            else: st.error("Invalid Key")
            if "role" in st.session_state: st.rerun()
    st.stop()

# --- 5. CLEAN SIDEBAR ---
with st.sidebar:
    st.image(LOGO_URL, width=100)
    
    if st.session_state.role == "viewer":
        opts = ["Analyser", "Export"]
        icons = ["graph-up", "download"]
    else:
        opts = ["Entry", "Register", "Manage", "Analyser", "Export"]
        icons = ["plus-square", "archive", "pencil", "graph-up", "download"]
    
    selected = option_menu(
        "Menu", opts, icons=icons, default_index=0,
        styles={
            "container": {"padding": "0!important", "background-color": HASH_WHITE},
            "icon": {"color": PINK, "font-size": "14px"}, 
            "nav-link": {"font-size": "15px", "text-align": "left", "margin":"0px"},
            "nav-link-selected": {"background-color": PINK},
        }
    )
    
    st.write("---")
    if st.button("Log Out", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# Load Data
p_list, d_list = get_master_data()

# --- TAB: ENTRY ---
if selected == "Entry":
    st.subheader("New Price Entry")
    
    with st.form("entry_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        p = c1.selectbox("Product", ["Select..."] + p_list)
        d = c2.selectbox("Distributor", ["Select..."] + d_list)
        
        c3, c4 = st.columns(2)
        pr = c3.number_input("Price HT (EUR)", min_value=0.0, step=0.01)
        dt = c4.date_input("Date", date.today())
        
        if st.form_submit_button("Save Record", use_container_width=True):
            if p != "Select..." and d != "Select...":
                conn.table("price_logs").insert({"product": p, "distributor": d, "price": pr, "date": str(dt)}).execute()
                st.success("Saved")
                st.cache_data.clear()
                st.rerun()
            else:
                st.error("Missing Data")

    st.write("---")
    st.subheader("Recent Logs")
    df = get_logs()
    
    if not df.empty:
        # Filters
        fc1, fc2 = st.columns(2)
        fp = fc1.multiselect("Filter Product", p_list)
        fd = fc2.multiselect("Filter Distributor", d_list)
        if fp: df = df[df['product'].isin(fp)]
        if fd: df = df[df['distributor'].isin(fd)]

        # Table
        df['date_str'] = df['date'].dt.strftime('%d-%m-%Y')
        st.dataframe(
            df[['date_str', 'product', 'distributor', 'price']],
            column_config={
                "date_str": "Date",
                "price": st.column_config.NumberColumn("Price", format="%.2f €")
            },
            use_container_width=True, hide_index=True
        )

# --- TAB: REGISTER ---
elif selected == "Register":
    st.subheader("Register Items")
    c1, c2 = st.columns(2)
    
    with c1:
        st.write("**New Product**")
        new_p = st.text_input("Name", key="np", label_visibility="collapsed")
        if st.button("Add Product", use_container_width=True):
            if new_p and new_p not in p_list:
                conn.table("products").insert({"name": new_p}).execute()
                st.cache_data.clear()
                st.rerun()
            elif new_p: st.warning("Exists")

    with c2:
        st.write("**New Distributor**")
        new_d = st.text_input("Name", key="nd", label_visibility="collapsed")
        if st.button("Add Distributor", use_container_width=True):
            if new_d and new_d not in d_list:
                conn.table("distributors").insert({"name": new_d}).execute()
                st.cache_data.clear()
                st.rerun()
            elif new_d: st.warning("Exists")

# --- TAB: MANAGE ---
elif selected == "Manage":
    st.subheader("Edit Data")
    df_m = get_logs()
    
    if not df_m.empty:
        df_m['date'] = df_m['date'].dt.date
        edited = st.data_editor(
            df_m,
            key="editor",
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
            column_config={
                "id": None, 
                "product": st.column_config.SelectboxColumn("Product", options=p_list, required=True),
                "distributor": st.column_config.SelectboxColumn("Distributor", options=d_list, required=True),
                "date": st.column_config.DateColumn("Date", format="DD-MM-YYYY"),
                "price": st.column_config.NumberColumn("Price", format="%.2f €")
            }
        )
        if st.button("Commit Changes", use_container_width=True):
            # Delete
            for row in st.session_state["editor"]["deleted_rows"]:
                conn.table("price_logs").delete().eq("id", df_m.iloc[row]["id"]).execute()
            # Update
            for idx, updates in st.session_state["editor"]["edited_rows"].items():
                if "date" in updates: updates["date"] = str(updates["date"])
                conn.table("price_logs").update(updates).eq("id", df_m.iloc[idx]["id"]).execute()
            st.success("Database Updated")
            st.rerun()

# --- TAB: ANALYSER ---
elif selected == "Analyser":
    st.subheader("Market Analysis")
    target = st.selectbox("Product", ["Select..."] + p_list)
    
    if target != "Select...":
        df = get_logs()
        df_sub = df[df['product'] == target].copy()
        
        if not df_sub.empty:
            min_p = df_sub['price'].min()
            
            c1, c2 = st.columns(2)
            c1.metric("Best Price", f"{min_p:.2f} €")
            c2.metric("Total Entries", len(df_sub))
            
            st.write("### Best Distributors")
            best = df_sub[df_sub['price'] == min_p]
            for _, r in best.iterrows():
                st.info(f"{r['distributor']} - {r['date'].strftime('%d-%m-%Y')}")
            
            st.write("### Spend Overview")
            grp = df_sub.groupby("distributor")['price'].sum().reset_index()
            fig = px.bar(grp, x="distributor", y="price", color="distributor", 
                         text_auto='.2s', color_discrete_sequence=[PINK])
            fig.update_layout(showlegend=False, xaxis_title=None, yaxis_title=None, 
                              paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True)

# --- TAB: EXPORT ---
elif selected == "Export":
    st.subheader("Data Export")
    c1, c2 = st.columns(2)
    d_start = c1.date_input("From", date(2025, 1, 1))
    d_end = c2.date_input("To", date.today())
    
    if st.button("Generate Excel File", use_container_width=True):
        df = get_logs()
        mask = (df['date'].dt.date >= d_start) & (df['date'].dt.date <= d_end)
        df_final = df[mask].sort_values("date", ascending=False)
        
        if not df_final.empty:
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                out = df_final[['date', 'product', 'distributor', 'price']].copy()
                out['date'] = out['date'].dt.strftime('%d-%m-%Y')
                out.to_excel(writer, index=False)
            
            st.download_button("Download Now", data=buffer, file_name="Gmax_Report.xlsx", 
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", 
                               use_container_width=True)
        else:
            st.warning("No data in range")
