import streamlit as st
from st_supabase_connection import SupabaseConnection
from streamlit_option_menu import option_menu
import pandas as pd
from datetime import date
import plotly.express as px
import io 

# --- 1. SETUP & BRANDING ---
LOGO_URL = "https://raw.githubusercontent.com/gmaxfrance-blip/price-app/a423573672203bc38f5fbcf5f5a56ac18380ebb3/dp%20logo.png"
GMAX_PINK = "#ff1774"
ITEMS_PER_PAGE = 20

st.set_page_config(page_title="Gmax Prix", page_icon=LOGO_URL, layout="wide")
conn = st.connection("supabase", type=SupabaseConnection)

# --- 2. CUSTOM CSS (THE "BOOTSTRAP" LOOK) ---
st.markdown(f"""
    <style>
    /* Main Background */
    .stApp {{ background-color: #f8f9fa; }} /* Light Grey Bootstrap Background */
    
    /* Card Style Containers */
    div.block-container {{ padding-top: 2rem; }}
    
    /* Custom Card Class for styling */
    .css-card {{
        border-radius: 10px;
        padding: 20px;
        background-color: white;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin-bottom: 20px;
    }}
    
    /* Headings */
    h1, h2, h3 {{ color: {GMAX_PINK} !important; font-family: 'Segoe UI', sans-serif; font-weight: 700; }}
    
    /* Buttons */
    div.stButton > button {{ 
        background-color: {GMAX_PINK}; 
        color: white; 
        border: none; 
        border-radius: 5px; 
        padding: 0.5rem 1rem;
        font-weight: bold;
        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
    }}
    div.stButton > button:hover {{ background-color: #d90e5f; border: none; color: white; }}
    
    /* Hide Default Elements */
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    header {{visibility: hidden;}}
    </style>
    """, unsafe_allow_html=True)

# --- 3. CACHED DATA (SPEED) ---
@st.cache_data(ttl=600)
def get_master_lists():
    p = conn.table("products").select("name").execute()
    d = conn.table("distributors").select("name").execute()
    return sorted([r['name'] for r in p.data]), sorted([r['name'] for r in d.data])

def get_recent_logs():
    res = conn.table("price_logs").select("*").order("date", desc=True).execute()
    df = pd.DataFrame(res.data)
    if not df.empty: df['date'] = pd.to_datetime(df['date'])
    return df

# --- 4. AUTHENTICATION ---
if "role" not in st.session_state:
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown(f"<div style='text-align: center;'><img src='{LOGO_URL}' width='100'></div>", unsafe_allow_html=True)
        st.markdown("<h2 style='text-align: center;'>Login</h2>", unsafe_allow_html=True)
        pwd = st.text_input("Security Key", type="password", label_visibility="collapsed")
        if st.button("Access System", use_container_width=True):
            if pwd == "admin123": st.session_state.role = "admin"
            elif pwd == "boss456": st.session_state.role = "viewer"
            else: st.error("Access Denied")
            if "role" in st.session_state: st.rerun()
    st.stop()

# --- 5. MODERN SIDEBAR ---
with st.sidebar:
    st.image(LOGO_URL, width=100)
    
    # Define Menu Items based on Role
    if st.session_state.role == "viewer":
        menu_opts = ["Analyser", "Export"]
        menu_icons = ["graph-up-arrow", "cloud-download"]
    else:
        menu_opts = ["Entry", "Register", "Manage", "Analyser", "Export"]
        menu_icons = ["plus-circle", "list-task", "pencil-square", "graph-up-arrow", "cloud-download"]
        
    selected = option_menu(
        "Navigation", 
        menu_opts, 
        icons=menu_icons, 
        menu_icon="cast", 
        default_index=0,
        styles={
            "container": {"padding": "0!important", "background-color": "#fafafa"},
            "icon": {"color": GMAX_PINK, "font-size": "16px"}, 
            "nav-link": {"font-size": "16px", "text-align": "left", "margin":"0px", "--hover-color": "#eee"},
            "nav-link-selected": {"background-color": GMAX_PINK},
        }
    )
    
    st.write("---")
    if st.button("Logout", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# Load Data
p_names, d_names = get_master_lists()

# --- PAGE: ENTRY ---
if selected == "Entry":
    st.markdown("<h3>📥 New Price Entry</h3>", unsafe_allow_html=True)
    
    # CARD LAYOUT FOR FORM
    with st.container():
        st.write("Fill in the details below to add a new price.")
        with st.form("entry_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            p = c1.selectbox("Product", ["Choose..."] + p_names)
            d = c2.selectbox("Distributor", ["Choose..."] + d_names)
            
            c3, c4 = st.columns(2)
            pr = c3.number_input("Price HT (€)", min_value=0.0, step=0.01)
            dt = c4.date_input("Date", date.today())
            
            if st.form_submit_button("Save Record", use_container_width=True):
                if p != "Choose..." and d != "Choose...":
                    conn.table("price_logs").insert({"product": p, "distributor": d, "price": pr, "date": str(dt)}).execute()
                    st.success("✅ Saved Successfully!")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error("⚠️ Please select Product & Distributor")

    st.write("---")
    st.markdown("<h3>🕒 Recent Entries</h3>", unsafe_allow_html=True)
    
    df = get_recent_logs()
    if not df.empty:
        # FILTER SECTION
        with st.expander("🔎 Filter Data", expanded=False):
            fc1, fc2 = st.columns(2)
            fp = fc1.multiselect("Products", p_names)
            fd = fc2.multiselect("Distributors", d_names)
            if fp: df = df[df['product'].isin(fp)]
            if fd: df = df[df['distributor'].isin(fd)]

        # PAGINATION
        rows = len(df)
        if rows > ITEMS_PER_PAGE:
            max_p = (rows // ITEMS_PER_PAGE) + 1
            col_pag1, _ = st.columns([1,4])
            cur_p = col_pag1.number_input("Page", 1, max_p)
            df_show = df.iloc[(cur_p-1)*ITEMS_PER_PAGE : cur_p*ITEMS_PER_PAGE].copy()
        else:
            df_show = df.copy()

        df_show['date_str'] = df_show['date'].dt.strftime('%d-%m-%Y')
        st.dataframe(
            df_show[['date_str', 'product', 'distributor', 'price']],
            column_config={
                "date_str": "Date",
                "price": st.column_config.NumberColumn("Price (€)", format="%.2f €")
            },
            use_container_width=True, hide_index=True
        )

# --- PAGE: REGISTER ---
elif selected == "Register":
    st.markdown("<h3>📝 Register Items</h3>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    
    with c1:
        st.info("📦 **New Product**")
        new_p = st.text_input("Product Name", key="np")
        if st.button("Add Product", key="btn_p", use_container_width=True):
            if new_p and new_p not in p_names:
                conn.table("products").insert({"name": new_p}).execute()
                st.cache_data.clear()
                st.success(f"Added {new_p}")
                st.rerun()
            elif new_p: st.warning("Exists!")
            
    with c2:
        st.info("🚚 **New Distributor**")
        new_d = st.text_input("Distributor Name", key="nd")
        if st.button("Add Distributor", key="btn_d", use_container_width=True):
            if new_d and new_d not in d_names:
                conn.table("distributors").insert({"name": new_d}).execute()
                st.cache_data.clear()
                st.success(f"Added {new_d}")
                st.rerun()
            elif new_d: st.warning("Exists!")

# --- PAGE: MANAGE ---
elif selected == "Manage":
    st.markdown("<h3>✏️ Manage Data</h3>", unsafe_allow_html=True)
    df_m = get_recent_logs()
    
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
                "product": st.column_config.SelectboxColumn("Product", options=p_names, required=True),
                "distributor": st.column_config.SelectboxColumn("Distributor", options=d_names, required=True),
                "date": st.column_config.DateColumn("Date", format="DD-MM-YYYY"),
                "price": st.column_config.NumberColumn("Price (€)", format="%.2f €")
            }
        )
        if st.button("💾 Save Changes", use_container_width=True):
            for row in st.session_state["editor"]["deleted_rows"]:
                conn.table("price_logs").delete().eq("id", df_m.iloc[row]["id"]).execute()
            for idx, updates in st.session_state["editor"]["edited_rows"].items():
                if "date" in updates: updates["date"] = str(updates["date"])
                conn.table("price_logs").update(updates).eq("id", df_m.iloc[idx]["id"]).execute()
            st.success("Updated!")
            st.rerun()

# --- PAGE: ANALYSER ---
elif selected == "Analyser":
    st.markdown("<h3>🔍 Price Analyser</h3>", unsafe_allow_html=True)
    sel = st.selectbox("Select Product", ["Choose..."] + p_names)
    
    if sel != "Choose...":
        df = get_recent_logs()
        df_an = df[df['product'] == sel].copy()
        if not df_an.empty:
            min_p = df_an['price'].min()
            
            # KPI CARDS
            k1, k2 = st.columns(2)
            k1.metric("Best Price", f"{min_p:.2f} €")
            k2.metric("Total Records", len(df_an))
            
            st.markdown("#### Best Distributors")
            best = df_an[df_an['price'] == min_p]
            for _, r in best.iterrows():
                st.success(f"📍 **{r['distributor']}** - {r['date'].strftime('%d-%m-%Y')}")
            
            st.markdown("#### Spend Analysis")
            grp = df_an.groupby("distributor")['price'].sum().reset_index()
            fig = px.bar(grp, x="distributor", y="price", color="distributor", text_auto='.2s', color_discrete_sequence=[GMAX_PINK])
            fig.update_layout(showlegend=False, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True)

# --- PAGE: EXPORT ---
elif selected == "Export":
    st.markdown("<h3>📤 Export Data</h3>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    start_d = c1.date_input("Start", date(2025, 1, 1))
    end_d = c2.date_input("End", date.today())
    
    if st.button("Generate Excel", use_container_width=True):
        df_ex = get_recent_logs()
        if not df_ex.empty:
            mask = (df_ex['date'].dt.date >= start_d) & (df_ex['date'].dt.date <= end_d)
            df_filtered = df_ex[mask].sort_values("date", ascending=False)
            
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                export_clean = df_filtered[['date', 'product', 'distributor', 'price']].copy()
                export_clean['date'] = export_clean['date'].dt.strftime('%d-%m-%Y')
                export_clean.to_excel(writer, index=False)
            
            st.download_button("Download .xlsx", data=buffer, file_name="Gmax_Data.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
        else:
            st.warning("No data.")
