import streamlit as st
import pandas as pd
import altair as alt
import plotly.graph_objects as go

# 1. KONFIGURASI HALAMAN LENGKAP
st.set_page_config(page_title="PCI Oxygen Telemetry", layout="wide", page_icon="⚡")

# Sidebar untuk filter dan logo
with st.sidebar:
    st.title("⚡ GPI - System Control")
    st.caption("Monitoring Node: PCI-O2-Generator-Alpha")
    st.divider()
    st.markdown("**Status Koneksi:** 🟢 Online (CDN Delayed)")
    st.info("Dasbor ini menarik data telemetri dari node Edge Gateway di lapangan.")

st.title("Dasbor Pemantauan Generator Oksigen PCI")

# Ganti dengan URL CSV Anda yang asli
SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSegXE1uw1kZNNJN9iy4mmbxyy3KXM_6HrMBEq6Aq5hL_yPqH27Fpr3GfFtAOzHD4OsDzz6A01AZJVr/pub?gid=0&single=true&output=csv"

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
    latest_data = data.iloc[-1]
    previous_data = data.iloc[-2] if len(data) > 1 else latest_data
    
    # Notifikasi Kritis
    if latest_data['Status'] in ['FAULT', 'CRITICAL']:
        st.error(f"🚨 INTERVENSI DIBUTUHKAN: Sistem {latest_data['Status']} pada {latest_data['Timestamp']}")
    
    # Pemisahan Layout dengan TABS
    tab1, tab2 = st.tabs(["🎛️ Real-Time Monitoring", "📋 Historical Logs & Analytics"])
    
    with tab1:
        # TINGKAT 1: GAUGE CHART & METRIK UTAMA
        col_gauge, col_metrics = st.columns([1, 2])
        
        with col_gauge:
            # Plotly Gauge Chart untuk O2 Purity
            fig = go.Figure(go.Indicator(
                mode = "gauge+number+delta",
                value = latest_data['O2_Purity'],
                delta = {'reference': previous_data['O2_Purity']},
                title = {'text': "O2 Purity (%)"},
                gauge = {
                    'axis': {'range': [80, 100]},
                    'bar': {'color': "#00d2ff"},
                    'steps': [
                        {'range': [80, 89], 'color': "#ff4c4c"}, # Merah Kritis
                        {'range': [89, 92], 'color': "#fca311"}, # Kuning Warning
                        {'range': [92, 100], 'color': "#1e1e1e"} # Normal
                    ],
                    'threshold': {'line': {'color': "red", 'width': 4}, 'thickness': 0.75, 'value': 90}
                }
            ))
            fig.update_layout(height=250, margin=dict(l=10, r=10, t=40, b=10), paper_bgcolor="rgba(0,0,0,0)", font={'color': "white"})
            st.plotly_chart(fig, use_container_width=True)

        with col_metrics:
            st.markdown("<br>", unsafe_allow_html=True)
            m1, m2, m3 = st.columns(3)
            # Menghitung Delta (Perubahan dari menit sebelumnya)
            feed_delta = round(latest_data['Feed_Pressure'] - previous_data['Feed_Pressure'], 2)
            disc_delta = round(latest_data['Discharge_Pressure'] - previous_data['Discharge_Pressure'], 2)
            flow_delta = round(latest_data['Flow_Rate_LPM'] - previous_data['Flow_Rate_LPM'], 2)

            m1.metric("Feed Air Pressure", f"{latest_data['Feed_Pressure']} PSI", f"{feed_delta} PSI", delta_color="inverse")
            m2.metric("Discharge Pressure", f"{latest_data['Discharge_Pressure']} PSI", f"{disc_delta} PSI", delta_color="inverse")
            m3.metric("Flow Rate", f"{latest_data['Flow_Rate_LPM']} LPM", f"{flow_delta} LPM")
            
        st.divider()

        # TINGKAT 2: ANALITIK VISUAL (DUAL CHART)
        c1, c2 = st.columns(2)
        
        with c1:
            st.markdown("**Tren Kemurnian Oksigen**")
            chart_purity = alt.Chart(data).mark_area(
                line={'color':'#00d2ff'}, color=alt.Gradient(
                    gradient='linear', stops=[alt.GradientStop(color='rgba(0, 210, 255, 0.5)', offset=0), alt.GradientStop(color='rgba(0, 210, 255, 0)', offset=1)]
                )
            ).encode(
                x=alt.X("Timestamp:N", axis=alt.Axis(labels=False, title=None)), # Sembunyikan label X agar rapi
                y=alt.Y("O2_Purity:Q", scale=alt.Scale(domain=[85, 96]), title="% Purity"),
                tooltip=["Timestamp", "O2_Purity"]
            ).properties(height=250)
            st.altair_chart(chart_purity, use_container_width=True)
            
        with c2:
            st.markdown("**Analisis Kompresi (Feed vs Discharge)**")
            # Melt data agar bisa membuat multi-line chart di Altair
            df_melt = data.melt(id_vars=['Timestamp'], value_vars=['Feed_Pressure', 'Discharge_Pressure'], var_name='Sensor', value_name='Pressure')
            chart_pressure = alt.Chart(df_melt).mark_line().encode(
                x=alt.X("Timestamp:N", axis=alt.Axis(labels=False, title=None)),
                y=alt.Y("Pressure:Q", scale=alt.Scale(zero=False)),
                color=alt.Color("Sensor:N", scale=alt.Scale(range=['#fca311', '#ff4c4c'])),
                tooltip=["Timestamp", "Sensor", "Pressure"]
            ).properties(height=250)
            st.altair_chart(chart_pressure, use_container_width=True)

    with tab2:
        st.markdown("### Database Log Mentah")
        st.dataframe(data.style.applymap(
            lambda x: 'background-color: #ff4c4c; color: white' if x in ['FAULT', 'CRITICAL'] else '', subset=['Status']
        ), use_container_width=True, height=400)

except Exception as e:
    st.error(f"Sistem gagal mengekstraksi data: {e}")