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
st.set_page_config(page_title="Agro-Intel Titan", page_icon="🛰️", layout="wide")

# --- ESTILIZAÇÃO CSS CUSTOMIZADA ---
st.markdown("""
<style>
    .main { background-color: #f0f2f5; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); border-left: 5px solid #1b5e20; }
    .header-box { background: linear-gradient(135deg, #0d47a1 0%, #1a237e 100%); color: white; padding: 30px; border-radius: 15px; margin-bottom: 25px; }
    .tech-card { background-color: #ffffff; padding: 25px; border-radius: 12px; border: 1px solid #e0e0e0; margin-bottom: 20px; }
    .tech-header { color: #1a237e; font-weight: 800; font-size: 1.3em; border-bottom: 3px solid #f5f5f5; padding-bottom: 12px; margin-bottom: 18px; }
    .alert-high { background-color: #ffebee; border-left: 6px solid #b71c1c; padding: 20px; border-radius: 8px; color: #b71c1c; font-weight: 600; }
    .alert-low { background-color: #e8f5e9; border-left: 6px solid #1b5e20; padding: 20px; border-radius: 8px; color: #1b5e20; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

# --- 2. INTELIGÊNCIA AGRONÔMICA EXPANDIDA ---
BANCO_MASTER = {
    "Batata (Solanum tuberosum)": {
        "t_base": 7,
        "vars": {
            "Orchestra": {"kc": 1.15, "gda_meta": 1600, "info": "Pele lisa premium. Foco em K e Magnésio."},
            "Cupido": {"kc": 1.10, "gda_meta": 1400, "info": "Ciclo curto. Alerta máximo para Requeima."},
            "Camila": {"kc": 1.15, "gda_meta": 1550, "info": "Mercado fresco. Resistência moderada a Sarna."},
            "Atlantic": {"kc": 1.15, "gda_meta": 1650, "info": "Chips. Evitar Coração Oco via Cálcio."}
        },
        "fases": {
            "Emergência (0-20d)": {"desc": "Brotamento.", "fisio": "Dreno de reservas da semente.", "quim": "Azoxistrobina + Tiametoxam.", "bio": "EM-1 + Ácidos Húmicos."},
            "Vegetativo (20-35d)": {"desc": "Expansão foliar.", "fisio": "IAF explosivo. Demanda N.", "quim": "Mancozeb + Boro.", "bio": "Bokashi líquido."},
            "Tuberização (35-55d)": {"desc": "Formação de ganchos.", "fisio": "Inversão hormonal (Giberelina).", "quim": "Revus + Potássio.", "bio": "Aminoácidos."},
            "Enchimento (55-85d)": {"desc": "Engorda.", "fisio": "Translocação Folha -> Tubérculo.", "quim": "Benévia + Magnésio.", "bio": "Extrato de Algas."},
            "Maturação (85d+)": {"desc": "Cura da pele.", "fisio": "Suberização térmica.", "quim": "Diquat (Dessecação).", "bio": "Suspensão de N."}
        }
    },
    "Mirtilo": {
        "t_base": 7, "vars": {"Emerald": {"kc": 0.95, "gda_meta": 1800, "info": "Variedade vigorosa."}, "Biloxi": {"kc": 0.90, "gda_meta": 1900, "info": "Baixa exigência frio."}},
        "fases": {"Florada": {"desc": "Pegamento.", "fisio": "Polinização.", "quim": "Switch (Botrytis).", "bio": "Mel."}, "Crescimento": {"desc": "Expansão.", "fisio": "Divisão celular.", "quim": "K-Sulphate.", "bio": "Ácido Cítrico (pH)."}}
    },
    "Framboesa": {
        "t_base": 7, "vars": {"Heritage": {"kc": 1.1, "gda_meta": 1300, "info": "Remontante."}},
        "fases": {"Frutificação": {"desc": "Maturação bagas.", "fisio": "Açúcares.", "quim": "Espinosade.", "bio": "Bokashi (Estrutura)."}}
    }
}

# --- 3. MOTORES TÉCNICOS ---
def calc_gda(df, t_base):
    # Fórmula: GDA = (Tmax + Tmin)/2 - Tbase
    return df['GDA'].sum()

def get_forecast(lat, lon, api_key, kc, t_base):
    try:
        url = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={api_key}&units=metric&lang=pt_br"
        r = requests.get(url).json()
        dados = []
        for i in range(0, 40, 8):
            item = r['list'][i]
            t = item['main']['temp']
            umid = item['main']['humidity']
            # Cálculos Agronômicos
            es = 0.61078 * math.exp((17.27 * t) / (t + 237.3))
            ea = es * (umid / 100); vpd = round(es - ea, 2)
            et0 = 0.0023 * (t + 17.8) * (t ** 0.5) * 0.408
            dados.append({
                'Data': datetime.fromtimestamp(item['dt']).strftime('%d/%m'),
                'Temp': t, 'Umid': umid, 'VPD': vpd, 'Chuva': round(item.get('rain', {}).get('3h', 0), 1),
                'GDA': max(0, t - t_base), 'ETc': round(et0 * kc, 2)
            })
        return pd.DataFrame(dados)
    except: return pd.DataFrame()

# --- 4. INTERFACE E SIDEBAR ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2822/2822444.png", width=100)
    st.title("Agro-Intel Titan")
    
    # Gerenciamento de Chaves (Prioridade Secrets)
    api_w = st.text_input("OpenWeather Key", value=st.secrets.get("OPENWEATHER_KEY", ""), type="password")
    api_g = st.text_input("Gemini Key", value=st.secrets.get("GEMINI_KEY", ""), type="password")
    
    st.divider()
    cultura = st.selectbox("Cultura Alvo:", list(BANCO_MASTER.keys()))
    var = st.selectbox("Cultivar:", list(BANCO_MASTER[cultura]['vars'].keys()))
    fase = st.selectbox("Fase Fenológica:", list(BANCO_MASTER[cultura]['fases'].keys()))
    d_plantio = st.date_input("Início do Ciclo:", date(2025, 11, 25))
    
    st.divider()
    st.markdown("### 🚛 Simulador Logístico")
    peso_carga = st.slider("Carga (kg):", 100, 800, 300)
    distancia = st.number_input("Distância (km) para Salvador:", value=450)

# --- 5. DASHBOARD PRINCIPAL ---
st.markdown(f"""
<div class="header-box">
    <h1>🛰️ Fazenda Progresso - Ibicoara/BA</h1>
    <p>Monitoramento Enterprise: <b>{cultura} - {var}</b></p>
</div>
""", unsafe_allow_html=True)

if api_w:
    df = get_forecast("-13.200", "-41.400", api_w, BANCO_MASTER[cultura]['vars'][var]['kc'], BANCO_MASTER[cultura]['t_base'])
    
    if not df.empty:
        hoje = df.iloc[0]
        dias_acum = (date.today() - d_plantio).days
        gda_total = dias_acum * df['GDA'].mean()
        meta = BANCO_MASTER[cultura]['vars'][var]['gda_meta']
        
        # KPIs
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("🌡️ Temperatura", f"{hoje['Temp']:.1f}°C")
        c2.metric("💧 VPD (kPa)", f"{hoje['VPD']}", "Transpiração OK" if 0.5 < hoje['VPD'] < 1.2 else "Alerta")
        c3.metric("💦 ETc Diária", f"{hoje['ETc']} mm")
        c4.metric("📅 GDA Acumulado", f"{gda_acum_total:.0f}", f"Meta: {meta}")

        tabs = st.tabs(["🎓 Consultoria Técnica", "📊 Balanço Hídrico", "👁️ IA Vision", "🗺️ Geo-Satélite", "🚚 Logística"])

        with tabs[0]: # CONSULTORIA
            dados_fase = BANCO_MASTER[cultura]['fases'][fase]
            
            

            st.markdown(f"### 🔥 Progresso de Maturação: {min(100.0, (gda_total/meta)*100):.1f}%")
            st.progress(min(1.0, gda_total/meta))
            
            # Alerta Sanitário
            if hoje['Umid'] > 85:
                st.markdown(f'<div class="alert-high">🚨 ALERTA DE REQUEIMA: Umidade em {hoje["Umid"]}%. Condição crítica para Phytophthora. Aplicar Sistêmicos imediatamente.</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="alert-low">✅ CONDIÇÃO SANITÁRIA: Baixo risco fúngico. Manter preventivos à base de Cobre/Mancozeb.</div>', unsafe_allow_html=True)
            
            

            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown(f"""<div class="tech-card"><div class="tech-header">🧬 Fisiologia & Manejo</div>
                <p><b>{fase}:</b> {dados_fase['desc']}</p>
                <p><b>Fisiologia:</b> {dados_fase['fisio']}</p>
                <p><b>Manejo Bio:</b> {dados_fase['bio']}</p></div>""", unsafe_allow_html=True)
            with col_b:
                st.markdown(f"""<div class="tech-card"><div class="tech-header">🧪 Prescrição Química</div>
                <p><b>Sugestão de Moléculas:</b><br>{dados_fase['quim']}</p>
                <p><small>*Sempre consulte o receituário agronômico antes da aplicação.</small></p></div>""", unsafe_allow_html=True)

        with tabs[1]: # GRÁFICOS
            fig = go.Figure()
            fig.add_trace(go.Bar(x=df['Data'], y=df['Chuva'], name='Chuva (mm)', marker_color='#0288d1'))
            fig.add_trace(go.Scatter(x=df['Data'], y=df['ETc'], name='Consumo ETc (mm)', line=dict(color='#d32f2f', width=3)))
            fig.update_layout(title="Previsão de Balanço Hídrico (5 Dias)", template="plotly_white")
            st.plotly_chart(fig, use_container_width=True)

        with tabs[2]: # IA
            if api_g:
                img_file = st.camera_input("Scanner de Pragas")
                if img_file:
                    genai.configure(api_key=api_g)
                    with st.spinner("Inteligência Titan analisando..."):
                        model = genai.GenerativeModel('gemini-1.5-flash')
                        res = model.generate_content([f"Agrônomo Expert. Analise sintomas em {cultura} {var} na fase {fase}. Recomende fungicida ou inseticida.", Image.open(img_file)])
                        st.write(res.text)

        with tabs[3]: # MAPA
            m = folium.Map(location=[-13.200, -41.400], zoom_start=14)
            folium.TileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', attr='Esri', name='Satélite').add_to(m)
            LocateControl().add_to(m); Fullscreen().add_to(m)
            st_folium(m, width="100%", height=500)

        with tabs[4]: # LOGISTICA
            st.markdown("### 🚚 Planejamento de Frete (Salvador)")
            consumo_carro = 10 # km/l (exemplo da Doblò carregada)
            preco_combustivel = 6.20
            custo_viagem = (distancia / consumo_carro) * preco_combustivel
            
            c_l1, c_l2 = st.columns(2)
            c_l1.metric("Custo Combustível (Estimado)", f"R$ {custo_viagem:.2f}")
            c_l2.metric("Custo por kg", f"R$ {custo_viagem/peso_carga:.2f}")
            
            st.info(f"Capacidade ocupada: {(peso_carga/800)*100:.1f}% da suspensão da Doblò Cargo.")

else:
    st.warning("⚠️ Insira a OpenWeather Key para carregar os dados climáticos.")
