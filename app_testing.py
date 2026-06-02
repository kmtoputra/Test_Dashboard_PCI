import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# 1. KONFIGURASI HALAMAN LENGKAP
st.set_page_config(page_title="PCI Oxygen Telemetry", layout="wide", page_icon="⚡")

# Sidebar Statis
with st.sidebar:
    st.title("⚡ GPI - System Control")
    st.divider()
    st.markdown("**Status Koneksi:** 🟢 Online (CDN Delayed)")
    st.info("Dasbor ini menarik data telemetri dari node Edge Gateway di lapangan.")

st.title("Dasbor Pemantauan Generator Oksigen PCI")

# Tautan Database CSV
SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQ_PEXEeuVaFt9C2ijQhN1uVn-jIxO6GP9QsTQkmyJUObmHKGzLRjhbPRmx3bVoVb42DqInLTrN1TFs/pub?gid=1474132913&single=true&output=csv"

@st.cache_data(ttl=10)
def load_data():
    df = pd.read_csv(SHEET_CSV_URL, engine='python', on_bad_lines='skip')
    
    # Sanitasi Data Massal
    kolom_numerik = ['O2_Purity', 'Feed_Pressure', 'Discharge_Pressure', 'Flow_Rate_LPM']
    for col in kolom_numerik:
        if col in df.columns:
            df[col] = df[col].astype(str).str.replace(',', '.', regex=False)
            df[col] = pd.to_numeric(df[col], errors='coerce')
            
    df["Timestamp"] = df["Timestamp"].astype(str)
    df = df.dropna(subset=['Timestamp', 'O2_Purity'])
    return df

try:
    data = load_data()
    
    # Validasi Arsitektur Database
    if 'Machine_ID' not in data.columns:
        st.error("🚨 Kolom 'Machine_ID' tidak ditemukan di database.")
        st.stop()
        
    list_mesin = data['Machine_ID'].unique().tolist()
    
    st.markdown("### 🌐 Command Center: All Units Overview")
    
    # Membagi layar maksimal 4 kolom per baris
    NUM_COLS = 4
    
    # Looping Grid Berbaris
    for i in range(0, len(list_mesin), NUM_COLS):
        kolom_grid = st.columns(NUM_COLS)
        for j in range(NUM_COLS):
            if i + j < len(list_mesin):
                mesin = list_mesin[i + j]
                
                with kolom_grid[j]:
                    df_mesin = data[data['Machine_ID'] == mesin].copy()
                    latest = df_mesin.iloc[-1]
                    prev = df_mesin.iloc[-2] if len(df_mesin) > 1 else latest
                    
                    with st.container(border=True):
                        st.markdown(f"<h4 style='text-align: center; margin-bottom: 0px;'>Unit: {mesin}</h4>", unsafe_allow_html=True)
                        st.markdown("<br>", unsafe_allow_html=True)
                        
                        # Indikator Status Warna
                        if latest['Status'] in ['FAULT', 'CRITICAL']:
                            st.markdown(f"<p style='text-align: center; color: #ff4c4c; font-weight: bold;'>🚨 STATUS: {latest['Status']}</p>", unsafe_allow_html=True)
                        elif latest['Status'] == 'WARNING':
                            st.markdown(f"<p style='text-align: center; color: #fca311; font-weight: bold;'>⚠️ STATUS: {latest['Status']}</p>", unsafe_allow_html=True)
                        else:
                            st.markdown(f"<p style='text-align: center; color: #00d2ff; font-weight: bold;'>🟢 STATUS: {latest['Status']}</p>", unsafe_allow_html=True)
                        
                        # Gauge Chart
                        fig = go.Figure(go.Indicator(
                            mode = "gauge+number+delta",
                            value = latest['O2_Purity'],
                            delta = {'reference': prev['O2_Purity']},
                            title = {'text': "O2 Purity (%)", 'font': {'size': 14}},
                            gauge = {
                                'axis': {'range': [80, 100]},
                                'bar': {'color': "#00d2ff"},
                                'steps': [
                                    {'range': [80, 89], 'color': "#ff4c4c"}, 
                                    {'range': [89, 92], 'color': "#fca311"}, 
                                    {'range': [92, 100], 'color': "#1e1e1e"} 
                                ],
                                'threshold': {'line': {'color': "red", 'width': 3}, 'thickness': 0.75, 'value': 90}
                            }
                        ))
                        fig.update_layout(height=180, margin=dict(l=20, r=20, t=30, b=10), paper_bgcolor="rgba(0,0,0,0)", font={'color': "white"})
                        st.plotly_chart(fig, use_container_width=True)
                        
                        # Metrik Tambahan
                        st.divider()
                        m1, m2 = st.columns(2)
                        m1.metric("Feed (PSI)", f"{latest['Feed_Pressure']}")
                        m2.metric("Flow (LPM)", f"{latest['Flow_Rate_LPM']}")

    # Database Log Mentah Expandable
    st.divider()
    with st.expander("📋 Lihat Database Log Mentah (Semua Mesin)"):
        st.dataframe(data.style.map(
            lambda x: 'background-color: #ff4c4c; color: white' if x in ['FAULT', 'CRITICAL'] else '', subset=['Status']
        ), use_container_width=True, height=300)

except Exception as e:
    st.error(f"Sistem gagal mengekstraksi data: {e}")