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
DARK_BG = "#0e1117"
CARD_BG = "#262730"
INPUT_BG = "#3b3d4a" # Slightly lighter for typing fields

st.set_page_config(page_title="Gmax Management", page_icon=LOGO_URL, layout="wide")
conn = st.connection("supabase", type=SupabaseConnection)

# --- 2. CSS THEME (FULL DARK & HIGH VISIBILITY) ---
st.markdown(f"""
    <style>
    .stApp {{ background-color: {DARK_BG}; }}
    .logo-container {{ display: flex; justify-content: center; margin-bottom: 20px; }}
    
    /* Input field visibility fix */
    .stSelectbox div, .stNumberInput input, .stDateInput input, .stTextInput input {{
        background-color: {INPUT_BG} !important;
        color: white !important;
        border: 1px solid #555 !important;
    }}
    
    div[data-testid="stForm"] {{ 
        background-color: {CARD_BG}; 
        padding: 25px; 
        border-radius: 8px; 
        border: 1px solid #333; 
    }}
    
    h1, h2, h3, h4, p, label {{ color: #ffffff !important; font-family: 'Arial', sans-serif; }}
    
    /* Submit Entry Button Styling */
    div.stButton > button {{ 
        background-color: {PINK} !important; 
        color: white !important; 
        border-radius: 4px; 
        width: 100%; 
        font-weight: bold; 
        border: none; 
        padding: 10px;
    }}
    
    /* Hide Default Elements */
    #MainMenu, footer, header {{visibility: hidden;}}
    </style>
    """, unsafe_allow_html=True)

# --- 3. DATA FUNCTIONS ---
@st.cache_data(ttl=600)
def get_master_data():
    p = conn.table("products").select("name").execute()
    d = conn.table("distributors").select("name").execute()
    return sorted([r['name'] for r in p.data]), sorted([r['name'] for r in d.data])

def get_logs():
    res = conn.table("price_logs").select("*").order("date", desc=True).execute()
    df = pd.DataFrame(res.data)
    if not df.empty:
        df['date'] = pd.to_datetime(df['date'])
    return df

# --- 4. LOGIN ---
if "role" not in st.session_state:
    st.markdown(f'<div class="logo-container"><img src="{LOGO_URL}" width="150"></div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1, 1])
    with c2:
        pwd = st.text_input("Password", type="password")
        if st.button("Access"):
            if pwd == "admin123": st.session_state.role = "admin"
            elif pwd == "boss456": st.session_state.role = "viewer"
            else: st.error("Invalid")
            if "role" in st.session_state: st.rerun()
    st.stop()

# --- 5. NAVIGATION ---
with st.sidebar:
    st.markdown(f'<div class="logo-container"><img src="{LOGO_URL}" width="100"></div>', unsafe_allow_html=True)
    opts = ["Entry", "Register", "Manage", "Analyser", "Export"] if st.session_state.role == "admin" else ["Analyser", "Export"]
    selected = option_menu("Menu", opts, icons=["plus-square", "archive", "pencil", "graph-up", "download"], default_index=0)
    if st.button("Log Out"):
        st.session_state.clear()
        st.rerun()

p_list, d_list = get_master_data()
st.markdown(f'<div class="logo-container"><img src="{LOGO_URL}" width="120"></div>', unsafe_allow_html=True)

# --- PAGE: ENTRY ---
if selected == "Entry":
    st.markdown("<h3 style='text-align: center;'>New Price Entry</h3>", unsafe_allow_html=True)
    with st.form("entry_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        p = c1.selectbox("Product", [""] + p_list)
        d = c2.selectbox("Distributor", [""] + d_list)
        c3, c4 = st.columns(2)
        pr = c3.number_input("Price", min_value=0.0, step=0.01, format="%.2f")
        dt = c4.date_input("Date", date.today())
        
        if st.form_submit_button("Submit Entry"):
            if p == "" or d == "" or pr <= 0:
                st.error("Error: All fields must be filled.")
            else:
                conn.table("price_logs").insert({"product": p, "distributor": d, "price": pr, "date": str(dt)}).execute()
                st.success("Successfully Entered")
                st.cache_data.clear()
    
    st.write("### Recent Entries")
    df_recent = get_logs()
    if not df_recent.empty:
        df_recent['date_display'] = df_recent['date'].dt.strftime('%d-%m-%Y')
        st.dataframe(df_recent[['date_display', 'product', 'distributor', 'price']].head(10), 
                     use_container_width=True, hide_index=True)

# --- PAGE: REGISTER ---
elif selected == "Register":
    st.markdown("<h3 style='text-align: center;'>Register Items</h3>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        st.write("Register Product")
        new_p = st.text_input("Product Name", key="np")
        if st.button("Save Product"):
            if new_p and new_p not in p_list:
                conn.table("products").insert({"name": new_p}).execute()
                st.cache_data.clear()
                st.rerun()
        st.dataframe(pd.DataFrame(p_list, columns=["Registered Products"]), use_container_width=True, hide_index=True)
    with c2:
        st.write("Register Distributor")
        new_d = st.text_input("Distributor Name", key="nd")
        if st.button("Save Distributor"):
            if new_d and new_d not in d_list:
                conn.table("distributors").insert({"name": new_d}).execute()
                st.cache_data.clear()
                st.rerun()
        st.dataframe(pd.DataFrame(d_list, columns=["Registered Distributors"]), use_container_width=True, hide_index=True)

# --- PAGE: MANAGE ---
elif selected == "Manage":
    st.markdown("<h3 style='text-align: center;'>Manage Data</h3>", unsafe_allow_html=True)
    df = get_logs()
    if not df.empty:
        df['date'] = df['date'].dt.date
        edited = st.data_editor(df, key="editor", num_rows="dynamic", use_container_width=True, hide_index=True,
                               column_config={"id": None, "date": st.column_config.DateColumn(format="DD-MM-YYYY")})
        if st.button("Commit Changes"):
            for row in st.session_state["editor"]["deleted_rows"]:
                conn.table("price_logs").delete().eq("id", df.iloc[row]["id"]).execute()
            for idx, updates in st.session_state["editor"]["edited_rows"].items():
                if "date" in updates: updates["date"] = str(updates["date"])
                conn.table("price_logs").update(updates).eq("id", df.iloc[idx]["id"]).execute()
            st.success("Updated")
            st.cache_data.clear()
            st.rerun()

# --- PAGE: ANALYSER ---
elif selected == "Analyser":
    st.markdown("<h3 style='text-align: center;'>Price Analyser</h3>", unsafe_allow_html=True)
    target = st.selectbox("Select Product", [""] + p_list)
    if target:
        df = get_logs()
        df_sub = df[df['product'] == target].copy()
        if not df_sub.empty:
            st.metric("Lowest Price Found", f"{df_sub['price'].min():.2f} €")
            st.write("Price History & Distributor List:")
            
            # FIXED: date column handled correctly for sorting and display
            df_sub['date_display'] = df_sub['date'].dt.strftime('%d-%m-%Y')
            history_df = df_sub.sort_values('date', ascending=False)
            
            st.dataframe(history_df[['date_display', 'distributor', 'price']], 
                         use_container_width=True, hide_index=True,
                         column_config={"date_display": "Date", "price": st.column_config.NumberColumn(format="%.2f €")})
            
            fig = px.bar(df_sub.groupby("distributor")['price'].min().reset_index(), x="distributor", y="price", color_discrete_sequence=[PINK])
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="white")
            st.plotly_chart(fig, use_container_width=True)

# --- PAGE: EXPORT ---
elif selected == "Export":
    st.markdown("<h3 style='text-align: center;'>Export Data</h3>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    start = c1.date_input("From", date(2025, 1, 1))
    end = c2.date_input("To", date.today())
    if st.button("Download Excel"):
        df = get_logs()
        mask = (df['date'].dt.date >= start) & (df['date'].dt.date <= end)
        df_f = df[mask].sort_values("date", ascending=False)
        if not df_f.empty:
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df_export = df_f[['date', 'product', 'distributor', 'price']].copy()
                df_export['date'] = df_export['date'].dt.strftime('%d-%m-%Y')
                df_export.to_excel(writer, index=False)
            st.download_button("Click to Download", data=buffer.getvalue(), file_name=f"Gmax_Report.xlsx", use_container_width=True)
