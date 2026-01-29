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
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- 1. CONFIGURAÇÃO DE SEGURANÇA (BACKEND) ---
# Em um app real, as chaves ficam escondidas no servidor.
# Se as chaves não estiverem nos 'Secrets', o app usa um modo de demonstração.
try:
    WEATHER_API_KEY = st.secrets["OPENWEATHER_KEY"]
    GEMINI_API_KEY = st.secrets["GEMINI_KEY"]
    IS_PRO_VERSION = True
except:
    WEATHER_API_KEY = None
    GEMINI_API_KEY = None
    IS_PRO_VERSION = False

# --- 2. CONFIGURAÇÃO VISUAL ---
st.set_page_config(page_title="Agro-Intel Pro", page_icon="🚜", layout="wide")

st.markdown("""
<style>
    .main { background-color: #f4f6f9; }
    .header-box { background: linear-gradient(135deg, #1b5e20 0%, #4caf50 100%); color: white; padding: 25px; border-radius: 12px; margin-bottom: 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }
    .stButton>button { width: 100%; border-radius: 20px; background-color: #1b5e20; color: white; }
    .login-card { max-width: 450px; margin: auto; padding: 40px; background: white; border-radius: 15px; box-shadow: 0 10px 25px rgba(0,0,0,0.1); text-align: center; }
</style>
""", unsafe_allow_html=True)

# --- 3. LÓGICA DE LOGIN ---
if 'auth_status' not in st.session_state: st.session_state['auth_status'] = False

def login_com_google():
    # Simulação de fluxo OAuth. 
    # Para o botão real, você usaria bibliotecas como 'streamlit-google-auth'
    st.markdown("""
    <div class="login-card">
        <img src="https://upload.wikimedia.org/wikipedia/commons/c/c1/Google_\"G\"_Logo.svg" width="50" style="margin-bottom:20px;">
        <h2>Bem-vindo ao Agro-Intel</h2>
        <p>Sua plataforma de inteligência na Chapada Diamantina</p>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("Continuar com Google"):
        # Aqui o sistema buscaria o e-mail real via Google API
        st.session_state['auth_status'] = True
        st.session_state['user_email'] = "usuario.exemplo@gmail.com"
        st.session_state['user_name'] = "Engenheiro Agrônomo"
        st.success("Logado com sucesso!")
        st.rerun()

if not st.session_state['auth_status']:
    login_com_google()
    st.stop()

# ==============================================================================
# SISTEMA PRINCIPAL (Puxando dados do Backend sem pedir chaves)
# ==============================================================================

# --- BANCO DE DADOS (MANTIDO E PROTEGIDO) ---
BANCO_MASTER = {
    "Batata (Solanum tuberosum)": {
        "t_base": 7,
        "vars": {
            "Orchestra": {"kc": 1.15, "gda_meta": 1600, "info": "Pele lisa. Exige K."},
            "Cupido": {"kc": 1.10, "gda_meta": 1400, "info": "Ciclo curto. Sensível à Requeima."},
            "Camila": {"kc": 1.15, "gda_meta": 1550, "info": "Cuidado com Sarna."},
            "Atlantic": {"kc": 1.15, "gda_meta": 1650, "info": "Chips. Evitar Coração Oco."}
        },
        "fases": {
            "Emergência (0-20 dias)": {"desc": "Brotamento inicial.", "fisiologia": "Uso de reservas da semente.", "manejo": "Solo aerado.", "quimica": "Azoxistrobina no sulco."},
            "Vegetativo (20-35 dias)": {"desc": "Crescimento foliar.", "fisiologia": "Demanda por N e Ca.", "manejo": "Amontoa.", "quimica": "Clorotalonil."},
            "Tuberização/Gancho (35-50 dias)": {"desc": "Fase Crítica.", "fisiologia": "Inversão hormonal.", "manejo": "Água constante.", "quimica": "Mandipropamida."},
            "Enchimento (50-80 dias)": {"desc": "Engorda.", "fisiologia": "Dreno de Potássio.", "manejo": "Mosca Branca/Traça.", "quimica": "Benévia."},
            "Maturação (80+ dias)": {"desc": "Pele.", "fisiologia": "Suberização.", "manejo": "Dessecação.", "quimica": "Diquat."}
        }
    },
    "Café (Coffea arabica)": {
        "t_base": 10,
        "vars": {"Catuaí": {"kc": 1.1, "gda_meta": 3000, "info": "Susceptível ferrugem."}, "Arara": {"kc": 1.2, "gda_meta": 2900, "info": "Resistente ferrugem."}},
        "fases": {
            "Florada": {"desc": "Antese.", "fisiologia": "Demanda Boro.", "manejo": "Proteger abelhas.", "quimica": "Boro+Cálcio."},
            "Chumbinho": {"desc": "Expansão fruto.", "fisiologia": "Divisão celular.", "manejo": "Cercospora.", "quimica": "Priori Xtra."},
            "Granação": {"desc": "Enchimento.", "fisiologia": "Dreno K.", "manejo": "Broca.", "quimica": "Benévia."}
        }
    }
}

# --- FUNÇÕES TÉCNICAS (USANDO CHAVES INTERNAS) ---
def get_forecast(lat, lon, kc, t_base):
    if not WEATHER_API_KEY: return pd.DataFrame() # Proteção
    url = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={WEATHER_API_KEY}&units=metric&lang=pt_br"
    try:
        r = requests.get(url).json()
        dados = []
        for i in range(0, 40, 8):
            item = r['list'][i]
            t = item['main']['temp']
            et0 = 0.0023 * (t + 17.8) * (t ** 0.5) * 0.408
            dados.append({'Data': datetime.fromtimestamp(item['dt']).strftime('%d/%m'), 'Temp': t, 'GDA': max(0, t-t_base), 'Chuva': round(item.get('rain', {}).get('3h', 0), 1), 'Umid': item['main']['humidity'], 'ETc': round(et0 * kc, 2)})
        return pd.DataFrame(dados)
    except: return pd.DataFrame()

# --- SIDEBAR PROFISSIONAL ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3058/3058995.png", width=80)
    st.write(f"🚜 **{st.session_state['user_name']}**")
    st.caption(f"📧 {st.session_state['user_email']}")
    
    if st.button("🚪 Sair"):
        st.session_state['auth_status'] = False
        st.rerun()
    
    st.divider()
    cultura_sel = st.selectbox("Cultura:", list(BANCO_MASTER.keys()))
    var_sel = st.selectbox("Cultivar:", list(BANCO_MASTER[cultura_sel]['vars'].keys()))
    fase_sel = st.selectbox("Fase:", list(BANCO_MASTER[cultura_sel]['fases'].keys()))
    d_plantio = st.date_input("Data de Início:", date(2025, 11, 25))
    info_v = BANCO_MASTER[cultura_sel]['vars'][var_sel]

# --- DASHBOARD ---
if not IS_PRO_VERSION:
    st.warning("⚠️ O sistema está em modo de demonstração. As chaves de API do servidor não foram configuradas.")

df = get_forecast("-13.414", "-41.285", info_v['kc'], BANCO_MASTER[cultura_sel]['t_base'])

if not df.empty:
    hoje = df.iloc[0]
    dias = (date.today() - d_plantio).days
    
    st.markdown(f"""<div class="header-box"><h2>{cultura_sel} - {var_sel}</h2><p>Lote com <b>{dias} dias</b> | Estágio: <b>{fase_sel}</b></p></div>""", unsafe_allow_html=True)
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🌡️ Temp", f"{hoje['Temp']:.1f}°C")
    c2.metric("💦 ETc (Consumo)", f"{hoje['ETc']} mm")
    c3.metric("📅 GDA Acumulado", f"{dias * hoje['GDA']:.0f}")
    c4.metric("🌧️ Prob. Chuva", f"{hoje['Chuva']} mm")

    tabs = st.tabs(["🎓 Consultoria Técnica", "📊 Balanço Hídrico", "📡 Radar", "👁️ IA Vision", "🗺️ Mapa", "🔔 Notificações"])

    with tabs[0]: # CONSULTORIA
        dados = BANCO_MASTER[cultura_sel]['fases'][fase_sel]
        col_a, col_b = st.columns(2)
        with col_a:
            st.info(f"**Fisiologia:** {dados['fisiologia']}")
        with col_b:
            st.success(f"**Manejo Sugerido:** {dados['manejo']}")
        st.warning(f"**Sugestão Química:** {dados['quimica']}")

    with tabs[3]: # IA
        if GEMINI_API_KEY:
            img = st.camera_input("Foto da Folha")
            if img:
                genai.configure(api_key=GEMINI_API_KEY)
                st.write("Analisando com IA do servidor...")
        else:
            st.error("IA desativada: Chave mestra não encontrada no servidor.")

    with tabs[5]: # NOTIFICAÇÕES (Puxando e-mail do login!)
        st.markdown("### 🔔 Configurar Alertas")
        st.write(f"Os alertas serão enviados para: **{st.session_state['user_email']}**")
        if st.button("Ativar Relatórios Diários"):
            st.success(f"Alertas ativados para {st.session_state['user_email']}")
