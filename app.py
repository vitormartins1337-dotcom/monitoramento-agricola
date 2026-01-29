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
st.set_page_config(page_title="Agro-Intel", page_icon="🚜", layout="wide")

# --- ESTILIZAÇÃO CSS ---
st.markdown("""
<style>
    .main { background-color: #f8fafc; }
    .stMetric { background: white; padding: 20px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); border-left: 5px solid #065f46; }
    .header-box { background: linear-gradient(135deg, #064e3b 0%, #166534 100%); color: white; padding: 30px; border-radius: 15px; margin-bottom: 25px; }
    .tech-card { background: white; padding: 25px; border-radius: 12px; border: 1px solid #e2e8f0; margin-bottom: 20px; height: 100%; }
    .alert-high { background-color: #fef2f2; border-left: 6px solid #dc2626; padding: 15px; border-radius: 8px; color: #991b1b; font-weight: bold; }
    .alert-low { background-color: #f0fdf4; border-left: 6px solid #16a34a; padding: 15px; border-radius: 8px; color: #14532d; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# --- 2. BANCO DE DADOS AGRONÔMICO ---
BANCO_MASTER = {
    "Batata (Solanum tuberosum)": {
        "t_base": 7,
        "vars": {
            "Orchestra": {"kc": 1.15, "gda_meta": 1600, "info": "Pele lisa premium. Foco em K."},
            "Cupido": {"kc": 1.10, "gda_meta": 1400, "info": "Ciclo ultra-curto. Alerta Requeima."},
            "Camila": {"kc": 1.15, "gda_meta": 1550, "info": "Mercado fresco. Sarna Comum."},
            "Atlantic": {"kc": 1.15, "gda_meta": 1650, "info": "Chips. Cuidado Coração Oco."}
        },
        "fases": {
            "Emergência (0-20d)": {"desc": "Brotamento inicial.", "fisio": "Dreno de reservas da batata-mãe.", "manejo": "Solo aerado.", "quim": "Azoxistrobina + Tiametoxam.", "bio": "EM-1 + Ácidos Húmicos."},
            "Vegetativo (20-35d)": {"desc": "Expansão IAF.", "fisio": "Alta demanda de N e Ca.", "manejo": "Amontoa técnica.", "quim": "Mancozeb.", "bio": "Bokashi líquido."},
            "Tuberização (35-50d)": {"desc": "Início ganchos.", "fisio": "Inversão hormonal.", "manejo": "Água constante.", "quim": "Revus + Metalaxil-M.", "bio": "Aminoácidos."},
            "Enchimento (50-80d)": {"desc": "Expansão radial.", "fisio": "Dreno de K e Mg.", "manejo": "Mosca Branca/Traça.", "quim": "Benévia.", "bio": "Potássio via Algas."},
            "Maturação (80d+)": {"desc": "Cura da pele.", "fisio": "Suberização térmica.", "manejo": "Dessecação.", "quim": "Diquat.", "bio": "Corte de N."}
        }
    },
    "Café (Coffea arabica)": {
        "t_base": 10,
        "vars": {"Catuaí": {"kc": 1.1, "gda_meta": 3000, "info": "Qualidade bebida."}, "Arara": {"kc": 1.2, "gda_meta": 2900, "info": "Resistente à ferrugem."}},
        "fases": {"Florada": {"desc": "Antese.", "fisio": "Pico de B e Zn.", "manejo": "Mancha Aureolada.", "quim": "Boscalida.", "bio": "Ca+B."}, "Chumbinho": {"desc": "Expansão.", "fisio": "Divisão celular.", "manejo": "Cercospora.", "quim": "Priori Xtra.", "bio": "K-amino."}}
    },
    "Mirtilo (Blueberry)": {
        "t_base": 7, "vars": {"Emerald": {"kc": 0.95, "gda_meta": 1800, "info": "pH 4.5."}, "Biloxi": {"kc": 0.90, "gda_meta": 1900, "info": "Ereta."}},
        "fases": {"Crescimento": {"desc": "Expansão baga.", "fisio": "Açúcares.", "manejo": "Antracnose.", "quim": "Azoxistrobina.", "bio": "Ácidos Fúlvicos."}}
    },
    "Tomate": {
        "t_base": 10, "vars": {"Italiano": {"kc": 1.2, "gda_meta": 1600, "info": "Fundo preto."}, "Grape": {"kc": 1.1, "gda_meta": 1450, "info": "Rachadura."}},
        "fases": {"Frutificação": {"desc": "Engorda.", "fisio": "Dreno de K.", "manejo": "Traça Tuta.", "quim": "Clorfenapir.", "bio": "Bokashi."}}
    }
}

# --- 3. MOTORES TÉCNICOS ---
def get_coords_from_city(city_name, api_key):
    try:
        url = f"http://api.openweathermap.org/geo/1.0/direct?q={city_name}&limit=1&appid={api_key}"
        r = requests.get(url).json()
        if r: return r[0]['lat'], r[0]['lon']
    except: return None, None

def get_forecast(lat, lon, api_key, kc, t_base):
    try:
        url = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={api_key}&units=metric&lang=pt_br"
        r = requests.get(url).json()
        dados = []
        if 'list' in r:
            for i in range(0, 40, 8):
                item = r['list'][i]
                t, u = item['main']['temp'], item['main']['humidity']
                et0 = 0.0023 * (t + 17.8) * (t ** 0.5) * 0.408
                dados.append({'Data': datetime.fromtimestamp(item['dt']).strftime('%d/%m'), 'Temp': t, 'Umid': u, 'Chuva': round(item.get('rain', {}).get('3h', 0), 1), 'GDA': max(0, t - t_base), 'ETc': round(et0 * kc, 2)})
            return pd.DataFrame(dados)
    except: return pd.DataFrame()

# --- 4. SIDEBAR ---
if 'lat' not in st.session_state: st.session_state.lat = -13.2000
if 'lon' not in st.session_state: st.session_state.lon = -41.4000

with st.sidebar:
    st.header("⚙️ Configuração")
    api_w = st.secrets.get("OPENWEATHER_KEY", "")
    api_g = st.secrets.get("GEMINI_KEY", "")
    
    st.divider()
    st.markdown("### 📍 Localização")
    t_cidade, t_gps = st.tabs(["🏙️ Buscar Cidade", "🌐 GPS/Manual"])
    
    with t_cidade:
        cidade_input = st.text_input("Cidade, Estado:", placeholder="Ex: Ibicoara, Bahia")
        if st.button("Buscar Local"):
            nlat, nlon = get_coords_from_city(cidade_input, api_w)
            if nlat:
                st.session_state.lat, st.session_state.lon = nlat, nlon
                st.success(f"Localizado: {cidade_input}")
                st.rerun()
                
    with t_gps:
        st.session_state.lat = st.number_input("Lat:", value=st.session_state.lat, format="%.4f")
        st.session_state.lon = st.number_input("Lon:", value=st.session_state.lon, format="%.4f")
    
    st.divider()
    cultura_sel = st.selectbox("Cultura:", list(BANCO_MASTER.keys()))
    var_sel = st.selectbox("Variedade:", list(BANCO_MASTER[cultura_sel]['vars'].keys()))
    fase_sel = st.selectbox("Fase Atual:", list(BANCO_MASTER[cultura_sel]['fases'].keys()))
    d_plantio = st.date_input("Início do Ciclo:", date(2025, 12, 1))

# --- 5. DASHBOARD ---
st.markdown(f"""<div class="header-box"><h1>Agro-Intel</h1><p>Monitoramento Enterprise: {cultura_sel} | Cultivar: {var_sel}</p></div>""", unsafe_allow_html=True)

if api_w:
    crop_info = BANCO_MASTER[cultura_sel]
    v_info = crop_info['vars'][var_sel]
    f_info = crop_info['fases'][fase_sel]
    
    df = get_forecast(st.session_state.lat, st.session_state.lon, api_w, v_info['kc'], crop_info['t_base'])
    
    if not df.empty:
        hoje = df.iloc[0]; dias = (date.today() - d_plantio).days
        gda_atual = dias * df['GDA'].mean(); meta = v_info['gda_meta']
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("🌡️ Temp.", f"{hoje['Temp']:.1f}°C")
        c2.metric("💧 Umidade", f"{hoje['Umid']}%")
        c3.metric("💦 ETc", f"{hoje['ETc']} mm")
        c4.metric("📅 Idade", f"{dias} dias")

        tabs = st.tabs(["🎓 Consultoria Técnica", "📊 Clima & Água", "👁️ IA Vision", "🗺️ Mapa Satélite"])

        with tabs[0]:
            # Cabeçalho da Variedade e Ciclo
            st.markdown(f"### 🧬 Características da Variedade: {var_sel}")
            st.info(f"**Descrição Genética:** {v_info['info']}")
            
            
            st.markdown(f"**🔥 Progresso Térmico:** {gda_atual:.0f} / {meta} GDA")
            st.progress(min(1.0, gda_atual/meta))
            
            estilo = "alert-high" if hoje['Umid'] > 85 else "alert-low"
            msg = "🚨 RISCO FÚNGICO ALTO" if hoje['Umid'] > 85 else "✅ CONDIÇÃO SEGURA"
            st.markdown(f"<div class='{estilo}'>{msg}</div>", unsafe_allow_html=True)
            
            

            # DADOS LADO A LADO
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown(f"<div class='tech-card'><div class='tech-header'>🧬 Fisiologia da Fase: {fase_sel}</div><p><b>Resumo:</b> {f_info['desc']}</p><p><b>Processo:</b> {f_info['fisio']}</p><p><b>Manejo Biológico:</b> {f_info['bio']}</p></div>", unsafe_allow_html=True)
            with col_b:
                st.markdown(f"<div class='tech-card'><div class='tech-header'>🧪 Prescrição de Manejo</div><p><b>Ação de Campo:</b> {f_info['manejo']}</p><hr><p><b>Sugestão Química:</b><br>{f_info['quim']}</p></div>", unsafe_allow_html=True)

        with tabs[1]:
            fig = go.Figure()
            fig.add_trace(go.Bar(x=df['Data'], y=df['Chuva'], name='Chuva', marker_color='#3b82f6'))
            fig.add_trace(go.Scatter(x=df['Data'], y=df['ETc'], name='Consumo ETc', line=dict(color='#ef4444', width=3)))
            st.plotly_chart(fig, use_container_width=True)

        with tabs[3]:
            m = folium.Map(location=[st.session_state.lat, st.session_state.lon], zoom_start=14)
            folium.TileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', attr='Esri', name='Satélite').add_to(m)
            LocateControl().add_to(m); Fullscreen().add_to(m)
            st_folium(m, width="100%", height=500)
else:
    st.error("⚠️ Configure as chaves de API nos Secrets.")
