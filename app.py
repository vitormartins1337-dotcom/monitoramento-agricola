import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
import math
from datetime import datetime

# --- 1. CONFIGURAÇÃO DA PÁGINA (DESIGN) ---
st.set_page_config(
    page_title="Agro-Intel Command",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS PERSONALIZADO ---
st.markdown("""
<style>
    div[data-testid="metric-container"] {
        background-color: #f8f9fa;
        border: 1px solid #e9ecef;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.05);
    }
    h1, h2, h3 { color: #1e3a8a; font-family: 'Arial', sans-serif; }
    section[data-testid="stSidebar"] { background-color: #f1f5f9; }
</style>
""", unsafe_allow_html=True)

# --- DADOS ESTRATÉGICOS ---
# Nota: Mantivemos como string aqui por segurança, mas converteremos antes do mapa
FAZENDA = {"nome": "Ibicoara (Sede)", "lat": "-13.414", "lon": "-41.285"}
VIZINHOS = [
    {"nome": "Mucugê", "lat": "-13.005", "lon": "-41.371"},
    {"nome": "Barra da Estiva", "lat": "-13.623", "lon": "-41.326"},
    {"nome": "Piatã", "lat": "-13.154", "lon": "-41.773"},
    {"nome": "Cascavel (Distrito)", "lat": "-13.196", "lon": "-41.445"}
]
KC = 0.75

# --- CÉREBRO CIENTÍFICO ---
def calc_agro(temp, umid):
    es = 0.61078 * math.exp((17.27 * temp) / (temp + 237.3))
    ea = es * (umid / 100)
    vpd = round(es - ea, 2)
    tw = temp * math.atan(0.151977 * (umid + 8.313659)**0.5) + math.atan(temp + umid) - math.atan(umid - 1.676331) + 0.00391838 * (umid)**1.5 * math.atan(0.023101 * umid) - 4.686035
    dt = round(temp - tw, 1)
    return dt, vpd

def get_forecast(api_key, lat, lon):
    try:
        url = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={api_key}&units=metric&lang=pt_br"
        r = requests.get(url).json()
        dados = []
        for i in range(0, 40, 8):
            item = r['list'][i]
            dt, vpd = calc_agro(item['main']['temp'], item['main']['humidity'])
            chuva = sum([r['list'][i+j].get('rain', {}).get('3h', 0) for j in range(8) if i+j < len(r['list'])])
            et0 = 0.0023 * (item['main']['temp'] + 17.8) * (item['main']['temp'] ** 0.5) * 0.408
            
            dados.append({
                'Data': datetime.fromtimestamp(item['dt']).strftime('%d/%m'),
                'Temp': item['main']['temp'],
                'Chuva (mm)': round(chuva, 1),
                'VPD (kPa)': vpd,
                'Delta T': dt,
                'Umid (%)': item['main']['humidity'],
                'ETc (mm)': round(et0 * KC, 2)
            })
        return pd.DataFrame(dados)
    except: return pd.DataFrame()

# --- INTERFACE LATERAL ---
with st.sidebar:
    st.header("🎛️ Controle Operacional")
    api_key = st.text_input("🔑 Chave API OpenWeather", type="password")
    st.divider()
    st.subheader("🌱 Configuração da Cultura")
    fase = st.selectbox("Estágio Fenológico Atual:", 
                       ["Vegetativo (Crescimento)", "Florada/Pegamento", "Frutificação (Enchimento)", "Maturação"])
    st.info(f"📍 **Local Ativo:** {FAZENDA['nome']}")

# --- DASHBOARD PRINCIPAL ---
st.title("🛰️ Agro-Intel Command Center")

if api_key:
    df = get_forecast(api_key, FAZENDA['lat'], FAZENDA['lon'])
    
    if not df.empty:
        hoje = df.iloc[0]
        
        # 1. BLOCO DE KPIS
        col1, col2, col3, col4 = st.columns(4)
        
        delta_vpd = "off"
        if 0.4 <= hoje['VPD (kPa)'] <= 1.3: delta_vpd = "normal"
        elif hoje['VPD (kPa)'] > 1.3: delta_vpd = "inverse"
        
        col1.metric("🌡️ Temperatura", f"{hoje['Temp']} °C", f"Umid: {hoje['Umid (%)']}%")
        col2.metric("🌧️ Chuva (24h)", f"{hoje['Chuva (mm)']} mm", "Previsão Diária")
        col3.metric("💧 VPD (Pressão)", f"{hoje['VPD (kPa)']} kPa", 
                   "Ideal" if delta_vpd == "normal" else "Risco", delta_color=delta_vpd)
        col4.metric("🛡️ Delta T", f"{hoje['Delta T']} °C", 
                   "Pode Pulverizar" if 2 <= hoje['Delta T'] <= 8 else "Não Pulverizar")

        # 2. ABAS DE INTELIGÊNCIA
        tab_clima, tab_analise, tab_radar = st.tabs(["📊 Gráficos & Hídrico", "🔬 Análise Científica", "📡 Radar GPS"])

        with tab_clima:
            fig = go.Figure()
            fig.add_trace(go.Bar(x=df['Data'], y=df['Chuva (mm)'], name='Chuva (mm)', marker_color='#3498db'))
            fig.add_trace(go.Scatter(x=df['Data'], y=df['Temp'], name='Temp (°C)', yaxis='y2', line=dict(color='#e74c3c', width=3)))
            fig.update_layout(
                title="Meteograma de Precisão (7 Dias)",
                yaxis=dict(title='Chuva (mm)'),
                yaxis2=dict(title='Temperatura (°C)', overlaying='y', side='right'),
                legend=dict(orientation="h", y=1.1),
                height=350
            )
            st.plotly_chart(fig, use_container_width=True)

            chuva_acc = df['Chuva (mm)'].sum()
            etc_acc = df['ETc (mm)'].sum()
            balanco = chuva_acc - etc_acc
            
            c_bal1, c_bal2 = st.columns([1, 2])
            c_bal1.markdown(f"### 💧 Balanço Semanal\n- **Entrada (Chuva):** {chuva_acc} mm\n- **Saída (ETc):** {etc_acc} mm")
            if balanco > 0:
                c_bal2.success(f"### ✅ SUPERÁVIT: +{balanco:.1f} mm")
                c_bal2.caption("Solo saturado. Reduza a irrigação.")
            else:
                c_bal2.error(f"### ⚠️ DÉFICIT: {balanco:.1f} mm")
                c_bal2.caption("Aumente a irrigação.")

        with tab_analise:
            st.markdown("### 🧬 Diagnóstico Fisiológico & Nutricional")
            ca1, ca2 = st.columns(2)
            with ca1:
                st.subheader("1. Estado da Planta (VPD)")
                if 0.4 <= hoje['VPD (kPa)'] <= 1.3:
                    st.success("**OPERACIONAL (Zona Verde):** Estômatos abertos. Máxima fixação de Carbono.")
                elif hoje['VPD (kPa)'] > 1.3:
                    st.warning("**ESTRESSE HÍDRICO (Zona Seca):** Risco de cavitação no Xilema.")
                else:
                    st.error("**SATURAÇÃO (Zona Úmida):** Transpiração bloqueada.")
                
                st.subheader("2. Nutrição Sugerida (Fase Atual)")
                if "Vegetativo" in fase: st.info("**Foco: N + Mg.** Nitrogênio (Proteína) e Magnésio (Clorofila).")
                elif "Florada" in fase: st.info("**Foco: Ca + B.** Boro para tubo polínico e Cálcio para parede celular.")
                elif "Frutificação" in fase: st.info("**Foco: K.** Potássio para transporte de açúcares.")
            
            with ca2:
                st.subheader("3. Risco Sanitário")
                risco_alto = len(df[df['Umid (%)'] > 88])
                if risco_alto > 2: st.error(f"🚨 **ALERTA MÁXIMO:** {risco_alto} janelas de umidade > 88%. Risco de Botrytis.")
                else: st.success("✅ **BAIXO RISCO:** Umidade controlada.")

        with tab_radar:
            st.markdown("### 🛰️ Monitoramento da Vizinhança (GPS)")
            col_r = st.columns(len(VIZINHOS))
            for i, viz in enumerate(VIZINHOS):
                try:
                    r_viz = requests.get(f"https://api.openweathermap.org/data/2.5/weather?lat={viz['lat']}&lon={viz['lon']}&appid={api_key}&units=metric&lang=pt_br").json()
                    clima_desc = r_viz['weather'][0]['description'].title()
                    bg_color = "#ffebee" if "chuva" in clima_desc.lower() or r_viz.get('rain') else "#e8f5e9"
                    col_r[i].markdown(f"<div style='background-color: {bg_color}; padding: 10px; border-radius: 8px; border: 1px solid #ddd; text-align: center;'><strong>{viz['nome'].split()[0]}</strong><br><span style='font-size: 20px;'>{r_viz['main']['temp']:.0f}°C</span><br><small>{clima_desc}</small></div>", unsafe_allow_html=True)
                except: pass
            
            # --- CORREÇÃO DO MAPA AQUI ---
            st.caption("*Dados obtidos em tempo real via coordenadas de satélite.")
            
            # Criamos um DataFrame limpo e convertemos explicitamente para números (float)
            map_data = pd.DataFrame([FAZENDA] + VIZINHOS).rename(columns={"lat": "latitude", "lon": "longitude"})
            map_data['latitude'] = map_data['latitude'].astype(float)
            map_data['longitude'] = map_data['longitude'].astype(float)
            
            st.map(map_data, zoom=9)

    else:
        st.error("Erro ao carregar dados. Verifique sua conexão ou a Chave API.")
else:
    st.info("👈 **Para começar:** Insira a chave da API no menu lateral esquerdo.")
