import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
import math
from datetime import datetime

# --- CONFIGURAÇÕES ---
st.set_page_config(page_title="Agro-Intel App", page_icon="🌱", layout="wide")

# Dados Fixos (Sua Fazenda)
FAZENDA = {"nome": "Ibicoara (Sede)", "lat": "-13.414", "lon": "-41.285"}
VIZINHOS = [
    {"nome": "Mucugê", "lat": "-13.005", "lon": "-41.371"},
    {"nome": "Barra da Estiva", "lat": "-13.623", "lon": "-41.326"},
    {"nome": "Cascavel (BA)", "lat": "-13.196", "lon": "-41.445"}
]
KC = 0.75

# --- FUNÇÕES ---
def calc_agro(temp, umid):
    es = 0.61078 * math.exp((17.27 * temp) / (temp + 237.3))
    ea = es * (umid / 100)
    vpd = round(es - ea, 2)
    tw = temp * math.atan(0.151977 * (umid + 8.313659)**0.5) + math.atan(temp + umid) - math.atan(umid - 1.676331) + 0.00391838 * (umid)**1.5 * math.atan(0.023101 * umid) - 4.686035
    dt = round(temp - tw, 1)
    return dt, vpd

def get_data(api_key):
    try:
        url = f"https://api.openweathermap.org/data/2.5/forecast?lat={FAZENDA['lat']}&lon={FAZENDA['lon']}&appid={api_key}&units=metric&lang=pt_br"
        r = requests.get(url).json()
        dados = []
        for i in range(0, 40, 8):
            item = r['list'][i]
            dt, vpd = calc_agro(item['main']['temp'], item['main']['humidity'])
            chuva = sum([r['list'][i+j].get('rain', {}).get('3h', 0) for j in range(8) if i+j < len(r['list'])])
            dados.append({
                'Data': datetime.fromtimestamp(item['dt']).strftime('%d/%m'),
                'Temp': item['main']['temp'],
                'Chuva': round(chuva, 1),
                'VPD': vpd,
                'Delta T': dt,
                'Umid': item['main']['humidity']
            })
        return pd.DataFrame(dados)
    except: return pd.DataFrame()

# --- O APLICATIVO VISUAL ---
st.title(f"🌱 Agro-Intel: {FAZENDA['nome']}")

# Menu Lateral para Senha
api_key = st.sidebar.text_input("Cole sua Chave OpenWeather aqui:", type="password")

if api_key:
    df = get_data(api_key)
    if not df.empty:
        hoje = df.iloc[0]
        
        # 1. Indicadores (KPIs)
        c1, c2, c3 = st.columns(3)
        c1.metric("Temperatura", f"{hoje['Temp']}°C", f"{hoje['Chuva']}mm Chuva")
        c2.metric("VPD (Pressão)", f"{hoje['VPD']} kPa", "Ideal" if 0.4 <= hoje['VPD'] <= 1.3 else "Risco")
        c3.metric("Delta T (Pulverização)", f"{hoje['Delta T']}°C", "Permitido" if 2 <= hoje['Delta T'] <= 8 else "Travado")

        # 2. Gráfico
        st.subheader("📊 Previsão Semanal")
        fig = go.Figure()
        fig.add_trace(go.Bar(x=df['Data'], y=df['Chuva'], name='Chuva (mm)'))
        fig.add_trace(go.Scatter(x=df['Data'], y=df['Temp'], name='Temp (°C)', yaxis='y2', line=dict(color='red')))
        fig.update_layout(yaxis=dict(title='Chuva'), yaxis2=dict(title='Temp', overlaying='y', side='right'))
        st.plotly_chart(fig, use_container_width=True)

        # 3. Radar Vizinhos
        st.subheader("🛰️ Radar Regional")
        cols = st.columns(len(VIZINHOS))
        for i, viz in enumerate(VIZINHOS):
            try:
                r = requests.get(f"https://api.openweathermap.org/data/2.5/weather?lat={viz['lat']}&lon={viz['lon']}&appid={api_key}&units=metric").json()
                status = "🌧️" if "rain" in str(r) else "☀️"
                cols[i].metric(viz['nome'].split()[0], f"{r['main']['temp']:.0f}°C", status)
            except: pass
    else:
        st.error("Chave inválida ou erro de conexão.")
else:
    st.info("👈 Insira a chave da API no menu lateral para carregar o sistema.")
