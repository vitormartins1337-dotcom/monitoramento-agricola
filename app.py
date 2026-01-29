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
st.set_page_config(page_title="Agro-Intel Enterprise", page_icon="🛰️", layout="wide")

# --- ESTILIZAÇÃO CSS (PADRÃO FAZENDA PROGRESSO) ---
st.markdown("""
<style>
    .main { background-color: #f8fafc; }
    .stMetric { background: white; padding: 20px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); border-left: 5px solid #065f46; }
    .header-box { background: linear-gradient(135deg, #064e3b 0%, #065f46 100%); color: white; padding: 40px; border-radius: 20px; margin-bottom: 30px; }
    .tech-card { background: white; padding: 25px; border-radius: 15px; border: 1px solid #e2e8f0; margin-bottom: 20px; }
    .tech-header { color: #064e3b; font-weight: 800; font-size: 1.4em; border-bottom: 3px solid #f1f5f9; padding-bottom: 12px; margin-bottom: 20px; }
    .alert-high { background-color: #fef2f2; border-left: 6px solid #dc2626; padding: 20px; border-radius: 8px; color: #991b1b; font-weight: 600; }
    .alert-low { background-color: #f0fdf4; border-left: 6px solid #16a34a; padding: 20px; border-radius: 8px; color: #14532d; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

# --- 2. BANCO DE DADOS AGRONÔMICO TOTAL (NÃO RESUMIDO) ---
BANCO_MASTER = {
    "Batata (Solanum tuberosum)": {
        "t_base": 7,
        "vars": {
            "Orchestra": {"kc": 1.15, "gda_meta": 1600, "info": "Pele lisa premium. Alta exigência de Potássio (K) para acabamento e peso."},
            "Cupido": {"kc": 1.10, "gda_meta": 1400, "info": "Ciclo ultra-curto. Extrema sensibilidade à Requeima (Phytophthora)."},
            "Camila": {"kc": 1.15, "gda_meta": 1550, "info": "Referência mercado fresco. Monitorar rigorosamente Sarna Comum."},
            "Atlantic": {"kc": 1.15, "gda_meta": 1650, "info": "Industrial (Chips). Evitar oscilações hídricas (Coração Oco)."}
        },
        "fases": {
            "Emergência (0-20 dias)": {"desc": "Brotamento inicial.", "fisiologia": "Uso de reservas do tubérculo-mãe. Raízes frágeis.", "manejo": "Solo aerado. Monitorar Canela Preta.", "quimica": "Azoxistrobina + Tiametoxam.", "bio": "EM-1 + Ácidos Húmicos."},
            "Vegetativo (20-35 dias)": {"desc": "Expansão da área foliar.", "fisiologia": "Alta demanda de N para IAF.", "manejo": "Realizar amontoa técnica (15-20cm).", "quimica": "Mancozeb + Clorotalonil.", "bio": "Bokashi líquido."},
            "Tuberização/Gancho (35-50 dias)": {"desc": "Diferenciação dos tubérculos.", "fisiologia": "Inversão hormonal crítica. Sensível a déficit hídrico.", "manejo": "Irrigação de precisão. Controle severo de Requeima.", "quimica": "Revus + Metalaxil-M.", "bio": "Aminoácidos."},
            "Enchimento (50-80 dias)": {"desc": "Expansão radial.", "fisiologia": "Translocação intensa Folha -> Tubérculo. Dreno de K.", "manejo": "Sanidade foliar absoluta. Monitorar Mosca Branca e Traça.", "quimica": "Benévia + Espirotesifeno.", "bio": "Potássio via Algas."},
            "Maturação (80+ dias)": {"desc": "Cura da pele.", "fisiologia": "Suberização térmica final.", "manejo": "Dessecação química.", "quimica": "Diquat.", "bio": "Corte de Nitrogênio."}
        }
    },
    "Mirtilo (Blueberry)": {
        "t_base": 7,
        "vars": {"Emerald": {"kc": 0.95, "gda_meta": 1800, "info": "pH 4.5. Alta produtividade."}, "Biloxi": {"kc": 0.90, "gda_meta": 1900, "info": "Exigente em drenagem."}},
        "fases": {
            "Florada": {"desc": "Polinização.", "fisiologia": "Demanda de Boro para tubo polínico.", "manejo": "Botrytis.", "quimica": "Switch.", "bio": "Aminoácidos."},
            "Fruto Verde": {"desc": "Expansão.", "fisiologia": "Divisão celular intensa.", "manejo": "Antracnose.", "quimica": "Azoxistrobina.", "bio": "Ácidos fúlvicos."}
        }
    },
    "Café (Coffea arabica)": {
        "t_base": 10,
        "vars": {"Catuaí": {"kc": 1.1, "gda_meta": 3000, "info": "Suscetível à ferrugem."}, "Arara": {"kc": 1.2, "gda_meta": 2900, "info": "Resistente à ferrugem."}},
        "fases": {
            "Florada": {"desc": "Antese.", "fisiologia": "Demanda de Ca e B.", "manejo": "Phoma.", "quimica": "Boscalida.", "bio": "Boro foliar."},
            "Chumbinho": {"desc": "Crescimento.", "fisiologia": "Expansão do fruto.", "manejo": "Cercospora.", "quimica": "Priori Xtra.", "bio": "Aminoácidos."}
        }
    }
}

# --- 3. MOTORES TÉCNICOS (PREVISÃO E RADAR) ---
def get_forecast(lat, lon, api_key, kc, t_base):
    try:
        url = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={api_key}&units=metric&lang=pt_br"
        r = requests.get(url).json()
        dados = []
        if 'list' in r:
            for i in range(0, 40, 8):
                item = r['list'][i]
                t = item['main']['temp']
                umid = item['main']['humidity']
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

def get_radar(lat, lon, api_key):
    pontos = {"Norte": (lat+0.12, lon), "Sul": (lat-0.12, lon), "Leste": (lat, lon+0.12), "Oeste": (lat, lon-0.12)}
    res = []
    for d, c in pontos.items():
        try:
            url = f"https://api.openweathermap.org/data/2.5/weather?lat={c[0]}&lon={c[1]}&appid={api_key}&units=metric"
            r = requests.get(url).json()
            res.append({"Direção": d, "Temp": r['main']['temp'], "Chuva": "Sim" if "rain" in r else "Não"})
        except: pass
    return pd.DataFrame(res)

# --- 4. SIDEBAR ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2822/2822444.png", width=100)
    st.title("Agro-Intel Pro v28")
    
    # Chaves automáticas do Secrets
    api_w = st.secrets.get("OPENWEATHER_KEY", "")
    api_g = st.secrets.get("GEMINI_KEY", "")
    
    st.divider()
    cultura_sel = st.selectbox("Cultura:", list(BANCO_MASTER.keys()))
    var_sel = st.selectbox("Variedade:", list(BANCO_MASTER[cultura_sel]['vars'].keys()))
    fase_sel = st.selectbox("Estágio:", list(BANCO_MASTER[cultura_sel]['fases'].keys()))
    d_plantio = st.date_input("Data de Plantio:", date(2025, 11, 25))
    
    st.divider()
    peso_carro = st.slider("Carga Doblò (kg):", 100, 800, 350)

# --- 5. DASHBOARD PRINCIPAL ---
st.markdown(f"""
<div class="header-box">
    <h1>🛰️ Inteligência Agronômica: {cultura_sel}</h1>
    <p>Fazenda Progresso - Chapada Diamantina-BA</p>
</div>
""", unsafe_allow_html=True)

if api_w:
    crop_db = BANCO_MASTER[cultura_sel]
    v_info = crop_db['vars'][var_sel]
    df_previsao = get_forecast("-13.200", "-41.400", api_w, v_info['kc'], crop_db['t_base'])
    
    if not df_previsao.empty:
        hoje = df_previsao.iloc[0]
        dias_ciclo = (date.today() - d_plantio).days
        gda_total = dias_ciclo * df_previsao['GDA'].mean()
        meta = v_info['gda_meta']
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("🌡️ Temperatura", f"{hoje['Temp']:.1f}°C")
        m2.metric("💧 Umidade Rel.", f"{hoje['Umid']}%")
        m3.metric("💦 ETc Diária", f"{hoje['ETc']} mm")
        m4.metric("📅 Idade Ciclo", f"{dias_ciclo} dias")

        tabs = st.tabs(["🎓 Consultoria Técnica", "📊 Balanço Hídrico", "📡 Radar Vizinhança", "👁️ IA Vision", "🗺️ Mapa Satélite", "🚚 Logística"])

        with tabs[0]: # CONSULTORIA
            fase_data = crop_db['fases'][fase_sel]
            
            
            st.markdown(f"### 🔥 Progresso Térmico: {gda_total:.0f} / {meta} GDA")
            st.progress(min(1.0, gda_total/meta))
            
            if hoje['Umid'] > 85:
                st.markdown(f'<div class="alert-high">🚨 ALERTA: Umidade em {hoje["Umid"]}%. Risco elevado de doenças fúngicas. Aplicar Sistêmicos.</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="alert-low">✅ CONDIÇÃO SANITÁRIA: Baixo risco. Manter preventivos.</div>', unsafe_allow_html=True)
            
            

            c1, c2 = st.columns(2)
            with c1:
                st.markdown(f"""<div class="tech-card"><div class="tech-header">🧬 Fisiologia da Fase</div>
                <p><b>Status:</b> {fase_data['desc']}</p>
                <p><b>Bioquímica:</b> {fase_data['fisiologia']}</p>
                <p><b>Manejo Bio:</b> {fase_data['bio']}</p></div>""", unsafe_allow_html=True)
            with c2:
                st.markdown(f"""<div class="tech-card"><div class="tech-header">🧪 Prescrição Profissional</div>
                <p><b>Tratos:</b> {fase_data['manejo']}</p><hr>
                <p><b>Químicos:</b><br>{fase_data['quimica']}</p></div>""", unsafe_allow_html=True)

        with tabs[1]: # GRÁFICOS
            fig = go.Figure()
            fig.add_trace(go.Bar(x=df_previsao['Data'], y=df_previsao['Chuva'], name='Chuva (mm)', marker_color='#3b82f6'))
            fig.add_trace(go.Scatter(x=df_previsao['Data'], y=df_previsao['ETc'], name='Consumo ETc (mm)', line=dict(color='#ef4444', width=3)))
            st.plotly_chart(fig, use_container_width=True)

        with tabs[2]: # RADAR
            df_radar = get_radar("-13.200", "-41.400", api_w)
            if not df_radar.empty:
                cols = st.columns(4)
                for i, r in df_radar.iterrows():
                    cor = "#ffebee" if r['Chuva'] == "Sim" else "#f0fdf4"
                    with cols[i]: st.markdown(f"""<div class="tech-card" style="background-color:{cor}; text-align:center"><b>{r['Direção']}</b><br>{r['Temp']:.1f}°C<br>Chuva: {r['Chuva']}</div>""", unsafe_allow_html=True)

        with tabs[3]: # IA VISION
            if api_g:
                foto = st.camera_input("Scanner Fitossanitário")
                if foto:
                    genai.configure(api_key=api_g)
                    modelo = genai.GenerativeModel('gemini-1.5-flash')
                    res = modelo.generate_content([f"Agrônomo Expert. Analise imagem de {cultura_sel} {var_sel}. Estágio {fase_sel}. Sintomas e Soluções.", Image.open(foto)])
                    st.success(res.text)

        with tabs[4]: # MAPA
            m = folium.Map(location=[-13.200, -41.400], zoom_start=14)
            folium.TileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', attr='Esri', name='Satélite').add_to(m)
            LocateControl().add_to(m); Fullscreen().add_to(m)
            st_folium(m, width="100%", height=500)

else:
    st.error("⚠️ Erro: OPENWEATHER_KEY não detectada nos Secrets.")
