import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
import math
import google.generativeai as genai
from PIL import Image
from datetime import datetime, date
import folium
from folium.plugins import LocateControl, Fullscreen
from streamlit_folium import st_folium

# --- 1. CONFIGURAÇÃO DE ALTO NÍVEL ---
st.set_page_config(page_title="Agro-Intel DSS", page_icon="🛰️", layout="wide")

# --- ESTILIZAÇÃO CSS PROFISSIONAL ---
st.markdown("""
<style>
    .main { background-color: #f8fafc; }
    .stMetric { background: white; padding: 20px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); border-left: 5px solid #2e7d32; }
    .header-box { background: linear-gradient(135deg, #1b5e20 0%, #388e3c 100%); color: white; padding: 30px; border-radius: 15px; margin-bottom: 25px; }
    .tech-card { background: white; padding: 25px; border-radius: 15px; border: 1px solid #e2e8f0; margin-bottom: 20px; }
    .tech-header { color: #1b5e20; font-weight: 800; font-size: 1.4em; border-bottom: 3px solid #f1f5f9; padding-bottom: 12px; margin-bottom: 20px; }
    .alert-high { background-color: #fef2f2; border-left: 6px solid #dc2626; padding: 20px; border-radius: 8px; color: #991b1b; font-weight: 600; }
    .alert-low { background-color: #f0fdf4; border-left: 6px solid #16a34a; padding: 20px; border-radius: 8px; color: #14532d; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

# --- 2. BANCO DE DADOS AGRONÔMICO UNIVERSAL (NÃO RESUMIDO) ---
BANCO_MASTER = {
    "Batata (Solanum tuberosum)": {
        "t_base": 7,
        "vars": {
            "Orchestra": {"kc": 1.15, "gda_meta": 1600, "info": "Pele lisa premium. Alta exigência de Potássio (K)."},
            "Cupido": {"kc": 1.10, "gda_meta": 1400, "info": "Ciclo ultra-curto. Extrema sensibilidade à Requeima."},
            "Camila": {"kc": 1.15, "gda_meta": 1550, "info": "Mercado fresco. Monitorar Sarna Comum."},
            "Atlantic": {"kc": 1.15, "gda_meta": 1650, "info": "Industrial (Chips). Cuidado com Coração Oco."}
        },
        "fases": {
            "Emergência (0-20d)": {"desc": "Brotamento inicial.", "fisio": "Dreno de reservas da batata-mãe.", "manejo": "Solo aerado. Monitorar Canela Preta.", "quim": "Azoxistrobina + Tiametoxam.", "bio": "EM-1 + Ácidos Húmicos."},
            "Vegetativo (20-35d)": {"desc": "Expansão foliar.", "fisio": "Alta demanda de N para IAF.", "manejo": "Amontoa técnica.", "quim": "Mancozeb + Clorotalonil.", "bio": "Bokashi líquido."},
            "Tuberização (35-50d)": {"desc": "Diferenciação de tubérculos.", "fisio": "Inversão hormonal crítica.", "manejo": "Irrigação de precisão constante.", "quim": "Revus + Metalaxil-M.", "bio": "Aminoácidos."},
            "Enchimento (50-80d)": {"desc": "Expansão radial.", "fisio": "Translocação Folha-Tubérculo. Dreno de K.", "manejo": "Sanidade foliar. Monitorar Mosca Branca.", "quim": "Benévia + Espirotesifeno.", "bio": "Algas + Potássio."},
            "Maturação (80d+)": {"desc": "Cura da pele.", "fisio": "Suberização térmica final.", "manejo": "Dessecação química.", "quim": "Diquat.", "bio": "Suspensão de N."}
        }
    },
    "Morango": {
        "t_base": 7,
        "vars": {"San Andreas": {"kc": 0.85, "gda_meta": 1200, "info": "Neutro."}, "Albion": {"kc": 0.85, "gda_meta": 1250, "info": "Qualidade."}},
        "fases": {"Florada": {"desc": "Pegamento.", "fisio": "Polinização.", "quim": "Iprodiona.", "bio": "Boro."}, "Colheita": {"desc": "Maturação.", "fisio": "Acúmulo de açúcar.", "quim": "Abamectina (se necessário).", "bio": "Potássio."}}
    },
    "Mirtilo": {
        "t_base": 7, "vars": {"Emerald": {"kc": 0.95, "gda_meta": 1800, "info": "pH 4.5."}, "Biloxi": {"kc": 0.90, "gda_meta": 1900, "info": "Ereta."}},
        "fases": {"Crescimento": {"desc": "Expansão.", "fisio": "Divisão celular.", "quim": "Sulfato de K.", "bio": "Ácidos Húmicos."}}
    }
}

# --- 3. MOTORES TÉCNICOS ---
def get_forecast(lat, lon, api_key, kc, t_base):
    try:
        url = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={api_key}&units=metric&lang=pt_br"
        r = requests.get(url).json()
        dados = []
        if 'list' in r:
            for i in range(0, 40, 8):
                item = r['list'][i]
                t, u = item['main']['temp'], item['main']['humidity']
                es = 0.61078 * math.exp((17.27 * t) / (t + 237.3))
                ea = es * (u / 100); vpd = round(es - ea, 2)
                et0 = 0.0023 * (t + 17.8) * (t ** 0.5) * 0.408
                dados.append({'Data': datetime.fromtimestamp(item['dt']).strftime('%d/%m'), 'Temp': t, 'Umid': u, 'VPD': vpd, 'Chuva': round(item.get('rain', {}).get('3h', 0), 1), 'GDA': max(0, t - t_base), 'ETc': round(et0 * kc, 2)})
            return pd.DataFrame(dados)
    except: return pd.DataFrame()

def get_radar(lat, lon, api_key):
    pontos = {"Norte": (lat+0.1, lon), "Sul": (lat-0.1, lon), "Leste": (lat, lon+0.1), "Oeste": (lat, lon-0.1)}
    res = []
    for d, c in pontos.items():
        try:
            r = requests.get(f"https://api.openweathermap.org/data/2.5/weather?lat={c[0]}&lon={c[1]}&appid={api_key}&units=metric").json()
            res.append({"Direção": d, "Temp": r['main']['temp'], "Chuva": "Sim" if "rain" in r else "Não"})
        except: pass
    return pd.DataFrame(res)

# --- 4. SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Configuração do Produtor")
    api_w = st.secrets.get("OPENWEATHER_KEY", "")
    api_g = st.secrets.get("GEMINI_KEY", "")
    
    st.divider()
    lat = st.number_input("Latitude da Propriedade:", value=-13.2000, format="%.4f")
    lon = st.number_input("Longitude da Propriedade:", value=-41.4000, format="%.4f")
    
    st.divider()
    cultura = st.selectbox("Cultura:", list(BANCO_MASTER.keys()))
    var = st.selectbox("Variedade:", list(BANCO_MASTER[cultura]['vars'].keys()))
    fase = st.selectbox("Fase Atual:", list(BANCO_MASTER[cultura]['fases'].keys()))
    d_plantio = st.date_input("Data de Início/Plantio:", date(2025, 11, 25))

# --- 5. DASHBOARD ---
st.markdown(f"""<div class="header-box"><h1>🛰️ Agro-Intel: Sistema de Tomada de Decisão</h1><p>Monitoramento: {cultura} | Coordenadas: {lat}, {lon}</p></div>""", unsafe_allow_html=True)

if api_w:
    v_info = BANCO_MASTER[cultura]['vars'][var]
    df = get_forecast(lat, lon, api_w, v_info['kc'], BANCO_MASTER[cultura]['t_base'])
    
    if not df.empty:
        hoje = df.iloc[0]; dias = (date.today() - d_plantio).days
        gda_atual = dias * df['GDA'].mean(); meta = v_info['gda_meta']

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("🌡️ Temp.", f"{hoje['Temp']:.1f}°C")
        c2.metric("💧 Umidade", f"{hoje['Umid']}%")
        c3.metric("💦 ETc (Consumo)", f"{hoje['ETc']} mm")
        c4.metric("📅 Idade", f"{dias} dias")

        t1, t2, t3, t4, t5 = st.tabs(["🎓 Consultoria", "📊 Clima", "📡 Radar", "👁️ IA Vision", "🗺️ Mapa"])

        with t1: # CONSULTORIA
            fase_data = BANCO_MASTER[cultura]['fases'][fase]
            
            
            st.markdown(f"### 🔥 Progresso Térmico: {gda_atual:.0f} / {meta} GDA")
            st.progress(min(1.0, gda_atual/meta))
            
            estilo = "alert-high" if hoje['Umid'] > 85 else "alert-low"
            msg = "🚨 ALERTA: Risco Fúngico Alto." if hoje['Umid'] > 85 else "✅ Condição Segura."
            
            
            
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown(f"<div class='tech-card'><b>🧬 Fisiologia:</b><br>{fase_data['fisio']}<br><br><b>Manejo Bio:</b><br>{fase_data['bio']}</div>", unsafe_allow_html=True)
                st.markdown(f"<div class='{estilo}'>{msg}</div>", unsafe_allow_html=True)
            with col_b:
                st.markdown(f"<div class='tech-card'><b>🛠️ Recomendações:</b><br>Manejo: {fase_data['manejo']}<hr>Químicos:<br>{fase_data['quim']}</div>", unsafe_allow_html=True)

        with t2: # CLIMA
            fig = go.Figure()
            fig.add_trace(go.Bar(x=df['Data'], y=df['Chuva'], name='Chuva', marker_color='#3b82f6'))
            fig.add_trace(go.Scatter(x=df['Data'], y=df['ETc'], name='Consumo', line=dict(color='#ef4444', width=3)))
            st.plotly_chart(fig, use_container_width=True)

        with t3: # RADAR
            st.markdown("### 📡 Radar Regional (15km)")
            df_radar = get_radar(lat, lon, api_w)
            if not df_radar.empty:
                cols = st.columns(4)
                for i, r in df_radar.iterrows():
                    cor = "#fef2f2" if r['Chuva'] == "Sim" else "#f0fdf4"
                    with cols[i]: st.markdown(f"<div class='tech-card' style='background:{cor}; text-align:center'><b>{r['Direção']}</b><br>{r['Temp']:.1f}°C<br>Chuva: {r['Chuva']}</div>", unsafe_allow_html=True)

        with t4: # IA
            if api_g:
                foto = st.camera_input("Scanner de Pragas")
                if foto:
                    genai.configure(api_key=api_g)
                    res = genai.GenerativeModel('gemini-1.5-flash').generate_content([f"Agrônomo Expert. Analise imagem de {cultura}. Fase {fase}.", Image.open(foto)])
                    st.success(res.text)

        with t5: # MAPA
            m = folium.Map(location=[lat, lon], zoom_start=14)
            folium.TileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', attr='Esri', name='Satélite').add_to(m)
            st_folium(m, width="100%", height=500)
else:
    st.error("⚠️ Insira as chaves de API nos Secrets.")
