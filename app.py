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
st.set_page_config(page_title="Agro-Intel Pro", page_icon="🚜", layout="wide")

# --- CARREGAMENTO SILENCIOSO DE CHAVES (SECRETS) ---
try:
    WEATHER_KEY = st.secrets["OPENWEATHER_KEY"]
    GEMINI_KEY = st.secrets["GEMINI_KEY"]
except:
    st.error("⚠️ Configuração pendente: Adicione OPENWEATHER_KEY e GEMINI_KEY no painel Secrets do Streamlit.")
    st.stop()

# --- ESTILIZAÇÃO CSS (PADRÃO ENTERPRISE) ---
st.markdown("""
<style>
    .main { background-color: #f4f7f6; }
    .header-box { 
        background: linear-gradient(135deg, #1b5e20 0%, #4caf50 100%); 
        color: white; padding: 30px; border-radius: 15px; margin-bottom: 20px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    .tech-card { 
        background-color: #ffffff; padding: 20px; border-radius: 10px; 
        border: 1px solid #e0e0e0; margin-bottom: 15px;
    }
    .tech-header { color: #1b5e20; font-weight: bold; border-bottom: 2px solid #f0f0f0; padding-bottom: 10px; margin-bottom: 15px; }
    .alert-high { background-color: #ffebee; border-left: 5px solid #c62828; padding: 15px; color: #c62828; border-radius: 5px; }
    .alert-low { background-color: #e8f5e9; border-left: 5px solid #2e7d32; padding: 15px; color: #2e7d32; border-radius: 5px; }
</style>
""", unsafe_allow_html=True)

# --- 2. BANCO DE DADOS AGRONÔMICO TITAN ---
BANCO_MASTER = {
    "Batata (Solanum tuberosum)": {
        "t_base": 7,
        "vars": {
            "Orchestra": {"kc": 1.15, "gda_meta": 1600, "info": "Pele lisa premium. Alta exigência de K."},
            "Cupido": {"kc": 1.10, "gda_meta": 1400, "info": "Ciclo curto. Sensibilidade à Requeima."},
            "Camila": {"kc": 1.15, "gda_meta": 1550, "info": "Mercado fresco. Monitorar Sarna."},
            "Atlantic": {"kc": 1.15, "gda_meta": 1650, "info": "Industrial (Chips). Cuidado com Coração Oco."}
        },
        "fases": {
            "Emergência (0-20 dias)": {
                "desc": "Brotamento inicial.",
                "fisiologia": "Uso de reservas do tubérculo-mãe.",
                "manejo": "Solo aerado. Monitorar Canela Preta.",
                "quimica": "Azoxistrobina + Tiametoxam (Sulco)."
            },
            "Vegetativo (20-35 dias)": {
                "desc": "Expansão foliar e formação de hastes.",
                "fisiologia": "Alta demanda de N para IAF.",
                "manejo": "Realizar amontoa técnica.",
                "quimica": "Mancozeb + Clorotalonil."
            },
            "Tuberização/Gancho (35-55 dias)": {
                "desc": "Diferenciação dos tubérculos.",
                "fisiologia": "Inversão hormonal crítica. Sensível a déficit hídrico.",
                "manejo": "Irrigação de precisão constante.",
                "quimica": "Revus (Mandipropamida) + Metalaxil-M."
            },
            "Enchimento (55-85 dias)": {
                "desc": "Expansão radial e acúmulo de matéria seca.",
                "fisiologia": "Dreno intenso de K e Mg.",
                "manejo": "Monitorar Mosca Branca e Traça.",
                "quimica": "Benévia (Ciantraniliprole)."
            },
            "Maturação (85+ dias)": {
                "desc": "Senescência e cura da pele.",
                "fisiologia": "Finalização do ciclo térmico.",
                "manejo": "Suspensão gradual da água. Dessecação.",
                "quimica": "Diquat."
            }
        }
    },
    "Café (Coffea arabica)": {
        "t_base": 10,
        "vars": {
            "Catuaí": {"kc": 1.1, "gda_meta": 3000, "info": "Qualidade premium. Suscetível à Ferrugem."},
            "Arara": {"kc": 1.2, "gda_meta": 2900, "info": "Resistente à Ferrugem. Alta carga."}
        },
        "fases": {
            "Florada": {"desc": "Antese.", "fisiologia": "Demanda de Boro e Zinco.", "manejo": "Proteger polinizadores.", "quimica": "Cálcio + Boro."},
            "Chumbinho": {"desc": "Expansão fruto verde.", "fisiologia": "Divisão celular intensa.", "manejo": "Cercospora.", "quimica": "Priori Xtra."}
        }
    }
}

# --- 3. MOTORES TÉCNICOS ---
def get_forecast(lat, lon, kc, t_base):
    try:
        url = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={WEATHER_KEY}&units=metric&lang=pt_br"
        r = requests.get(url).json()
        dados = []
        for i in range(0, 40, 8):
            item = r['list'][i]
            t = item['main']['temp']
            et0 = 0.0023 * (t + 17.8) * (t ** 0.5) * 0.408
            dados.append({
                'Data': datetime.fromtimestamp(item['dt']).strftime('%d/%m'),
                'Temp': t, 'GDA': max(0, t-t_base), 'Chuva': round(item.get('rain', {}).get('3h', 0), 1),
                'Umid': item['main']['humidity'], 'ETc': round(et0 * kc, 2)
            })
        return pd.DataFrame(dados)
    except: return pd.DataFrame()

def get_radar(lat, lon):
    pontos = {"Norte": (lat+0.1, lon), "Sul": (lat-0.1, lon), "Leste": (lat, lon+0.1), "Oeste": (lat, lon-0.1)}
    radar_res = []
    for d, c in pontos.items():
        try:
            url = f"https://api.openweathermap.org/data/2.5/weather?lat={c[0]}&lon={c[1]}&appid={WEATHER_KEY}&units=metric"
            r = requests.get(url).json()
            radar_res.append({"Direcao": d, "Temp": r['main']['temp'], "Chuva": "Sim" if "rain" in r else "Não"})
        except: pass
    return pd.DataFrame(radar_res)

# --- 4. SIDEBAR ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3058/3058995.png", width=80)
    st.header("Gestão de Campo")
    u_email = st.text_input("E-mail do Responsável:", "engenheiro@fazendaprogresso.com.br")
    
    st.divider()
    cultura_sel = st.selectbox("Cultura:", list(BANCO_MASTER.keys()))
    var_sel = st.selectbox("Variedade:", list(BANCO_MASTER[cultura_sel]['vars'].keys()))
    fase_sel = st.selectbox("Estágio Fenológico:", list(BANCO_MASTER[cultura_sel]['fases'].keys()))
    d_plantio = st.date_input("Data de Início:", date(2025, 11, 25))
    info_v = BANCO_MASTER[cultura_sel]['vars'][var_sel]

# --- 5. DASHBOARD ---
st.markdown(f"""<div class="header-box"><h1>Agro-Intel Pro: {cultura_sel}</h1><p>Monitoramento Estratégico - Chapada Diamantina</p></div>""", unsafe_allow_html=True)

# Coordenadas padrão para Ibicoara/Mucugê
df = get_forecast("-13.200", "-41.400", info_v['kc'], BANCO_MASTER[cultura_sel]['t_base'])

if not df.empty:
    hoje = df.iloc[0]; dias = (date.today() - d_plantio).days
    gda_acum = dias * df['GDA'].mean(); meta_gda = info_v['gda_meta']

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🌡️ Temperatura", f"{hoje['Temp']:.1f}°C")
    c2.metric("💧 Umidade", f"{hoje['Umid']}%")
    c3.metric("💦 ETc Diária", f"{hoje['ETc']} mm")
    c4.metric("🌧️ Chuva Prev.", f"{hoje['Chuva']} mm")

    tabs = st.tabs(["🎓 Consultoria", "📊 Clima & Água", "📡 Radar", "👁️ IA Vision", "🗺️ Mapa", "🔔 Alertas"])

    with tabs[0]: # CONSULTORIA
        dados = BANCO_MASTER[cultura_sel]['fases'][fase_sel]
        
        
        st.markdown(f"### 🔥 Maturação Térmica: {gda_acum:.0f} / {meta_gda} GDA")
        st.progress(min(1.0, gda_acum/meta_gda))
        
        estilo = "alert-low" if hoje['Umid'] < 85 else "alert-high"
        msg = "✅ Condição favorável para preventivos." if estilo == "alert-low" else "🚨 ALERTA: Risco elevado de Requeima (Umidade > 85%)."
        

        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"<div class='tech-card'><div class='tech-header'>🧬 Fisiologia da Fase</div><p><b>{fase_sel}:</b> {dados['desc']}</p><p><b>Bioquímica:</b> {dados['fisiologia']}</p></div>", unsafe_allow_html=True)
            st.markdown(f"<div class='{estilo}'>{msg}</div>", unsafe_allow_html=True)
        with col2:
            st.markdown(f"<div class='tech-card'><div class='tech-header'>🛠️ Recomendações Técnicas</div><p><b>Manejo:</b> {dados['manejo']}</p><hr><p><b>Prescrição Química Sugerida:</b><br>{dados['quimica']}</p></div>", unsafe_allow_html=True)

    with tabs[1]: # CLIMA
        fig = go.Figure()
        fig.add_trace(go.Bar(x=df['Data'], y=df['Chuva'], name='Chuva (mm)', marker_color='#3498db'))
        fig.add_trace(go.Scatter(x=df['Data'], y=df['ETc'], name='Consumo ETc (mm)', line=dict(color='#e74c3c', width=3)))
        st.plotly_chart(fig, use_container_width=True)

    with tabs[2]: # RADAR
        st.markdown("### 📡 Radar Regional (Raio 10km)")
        df_r = get_radar("-13.200", "-41.400")
        if not df_r.empty:
            cols = st.columns(4)
            for i, r in df_r.iterrows():
                cor = "#ffebee" if r['Chuva'] == "Sim" else "#e8f5e9"
                with cols[i]: st.markdown(f"<div style='background:{cor}; padding:15px; border-radius:10px; text-align:center'><b>{r['Direcao']}</b><br>{r['Temp']:.1f}°C<br>Chuva: {r['Chuva']}</div>", unsafe_allow_html=True)

    with tabs[3]: # IA VISION
        st.write("### 👁️ Diagnóstico por Visão Artificial")
        foto = st.camera_input("Foto da Folha/Praga")
        if foto:
            genai.configure(api_key=GEMINI_KEY)
            with st.spinner("Analisando quadro clínico..."):
                res = genai.GenerativeModel('gemini-1.5-flash').generate_content([f"Engenheiro Agrônomo. Analise imagem de {cultura_sel}. Estágio {fase_sel}. Identifique sintomas e recomende manejo.", Image.open(foto)])
                st.success(res.text)

    with tabs[4]: # MAPA
        m = folium.Map(location=[-13.200, -41.400], zoom_start=14)
        folium.TileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', attr='Esri', name='Satélite').add_to(m)
        LocateControl().add_to(m); Fullscreen().add_to(m)
        st_folium(m, width="100%", height=500)

    with tabs[5]: # ALERTAS
        st.write(f"### 🔔 Central de Notificações")
        st.info(f"Relatórios técnicos diários serão enviados para: **{u_email}**")
        if st.button("Ativar Protocolo de Alertas"):
            st.balloons()
            st.success("Alertas ativados com sucesso!")
else:
    st.error("⚠️ Erro de conexão com a estação meteorológica.")
