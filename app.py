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
from streamlit_google_auth import Authenticate

# --- 1. CONFIGURAÇÃO DE ALTO NÍVEL ---
st.set_page_config(page_title="Agro-Intel Enterprise", page_icon="🛰️", layout="wide")

# --- LOGIN REAL COM GOOGLE (CALIBRAÇÃO POSICIONAL) ---
try:
    # URL oficial do seu app (Certifique-se que no Google Console está igual!)
    URL_DO_APP = "https://monitoramento-agricola.streamlit.app" 

    # Se a biblioteca rejeita nomes de argumentos, passamos os valores na ordem exata:
    # 1. ID, 2. Secret, 3. Redirect URI, 4. Cookie Name, 5. Cookie Key, 6. Expiry
    authenticator = Authenticate(
        st.secrets["GOOGLE_CLIENT_ID"],
        st.secrets["GOOGLE_CLIENT_SECRET"],
        URL_DO_APP,
        "agro_intel_session",
        "agro_secret_key_2026",
        30
    )
except Exception as e:
    st.error(f"Erro na configuração: {e}. Verifique se os nomes no painel Secrets estão corretos.")
    st.stop()

# Tenta validar o login
authenticator.check_authenticity()

if not st.session_state.get('connected'):
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown("""
            <div style="text-align: center; padding: 50px; background: white; border-radius: 20px; box-shadow: 0 15px 35px rgba(0,0,0,0.15);">
                <img src="https://upload.wikimedia.org/wikipedia/commons/c/c1/Google_\"G\"_Logo.svg" width="60">
                <h1 style="color: #064e3b; margin-top: 20px; font-weight: 800;">Agro-Intel Pro</h1>
                <p style="color: #64748b;">Acesse com sua conta oficial Google</p>
                <hr style="margin: 30px 0;">
            </div>
        """, unsafe_allow_html=True)
        authenticator.login()
        st.stop()

# --- VARIÁVEIS DE AMBIENTE ---
USER_EMAIL = st.session_state.get('email')
USER_NAME = st.session_state.get('name', 'Engenheiro Agrônomo')
USER_PIC = st.session_state.get('picture', "https://cdn-icons-png.flaticon.com/512/3135/3135715.png")

# Carregamento das chaves de inteligência
WEATHER_KEY = st.secrets["OPENWEATHER_KEY"]
GEMINI_KEY = st.secrets["GEMINI_KEY"]

# --- ESTILIZAÇÃO CSS ---
st.markdown("""
<style>
    .main { background-color: #f8fafc; }
    .header-box { background: linear-gradient(135deg, #064e3b 0%, #065f46 100%); color: white; padding: 35px; border-radius: 15px; margin-bottom: 25px; }
    .tech-card { background: white; padding: 25px; border-radius: 12px; border: 1px solid #e2e8f0; margin-bottom: 20px; }
    .alert-high { background-color: #fef2f2; border-left: 6px solid #dc2626; padding: 20px; border-radius: 8px; color: #991b1b; }
    .alert-low { background-color: #f0fdf4; border-left: 6px solid #16a34a; padding: 20px; border-radius: 8px; color: #14532d; }
</style>
""", unsafe_allow_html=True)

# --- 2. BANCO DE DADOS AGRONÔMICO (BATATA E CAFÉ) ---
BANCO_MASTER = {
    "Batata (Solanum tuberosum)": {
        "t_base": 7,
        "vars": {
            "Orchestra": {"kc": 1.15, "gda_meta": 1600, "info": "Pele lisa premium."},
            "Cupido": {"kc": 1.10, "gda_meta": 1400, "info": "Ciclo ultra-curto."},
            "Camila": {"kc": 1.15, "gda_meta": 1550, "info": "Referência mercado fresco."},
            "Atlantic": {"kc": 1.15, "gda_meta": 1650, "info": "Indústria (Chips)."}
        },
        "fases": {
            "Emergência (0-20 dias)": {"desc": "Brotamento inicial.", "fisiologia": "Uso de reservas do tubérculo.", "manejo": "Solo aerado.", "quimica": "Azoxistrobina + Tiametoxam."},
            "Vegetativo (20-35 dias)": {"desc": "Expansão foliar.", "fisiologia": "Demanda de N.", "manejo": "Amontoa técnica.", "quimica": "Mancozeb."},
            "Tuberização/Gancho (35-55 dias)": {"desc": "Diferenciação de tubérculos.", "fisiologia": "Inversão hormonal.", "manejo": "Irrigação de precisão.", "quimica": "Revus."},
            "Enchimento (55-85 dias)": {"desc": "Acúmulo de matéria seca.", "fisiologia": "Dreno de K e Mg.", "manejo": "Sanidade foliar.", "quimica": "Benévia."},
            "Maturação (85+ dias)": {"desc": "Cura da pele.", "fisiologia": "Finalização térmica.", "manejo": "Dessecação.", "quimica": "Diquat."}
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

# --- 4. SIDEBAR ---
with st.sidebar:
    st.image(USER_PIC, width=80)
    st.markdown(f"👤 **{USER_NAME}**")
    st.caption(USER_EMAIL)
    if st.button("🚪 Logout"):
        authenticator.logout()
    
    st.divider()
    cultura_sel = st.selectbox("Cultura:", list(BANCO_MASTER.keys()))
    var_sel = st.selectbox("Variedade:", list(BANCO_MASTER[cultura_sel]['vars'].keys()))
    fase_sel = st.selectbox("Estágio Fenológico:", list(BANCO_MASTER[cultura_sel]['fases'].keys()))
    d_plantio = st.date_input("Data de Plantio:", date(2025, 11, 25))
    info_v = BANCO_MASTER[cultura_sel]['vars'][var_sel]

# --- 5. DASHBOARD ---
st.title("🛰️ Agro-Intel Enterprise")

df = get_forecast("-13.200", "-41.400", info_v['kc'], BANCO_MASTER[cultura_sel]['t_base'])

if not df.empty:
    hoje = df.iloc[0]; dias = (date.today() - d_plantio).days
    gda_acum = dias * df['GDA'].mean(); meta_gda = info_v['gda_meta']

    st.markdown(f"""
    <div class="header-box">
        <h2>{cultura_sel} - {var_sel}</h2>
        <p style="font-size:1.1em"><b>{dias} Dias de Ciclo</b> | Estágio: {fase_sel}</p>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🌡️ Temperatura", f"{hoje['Temp']:.1f}°C")
    c2.metric("💧 Umidade", f"{hoje['Umid']}%")
    c3.metric("💦 ETc Diária", f"{hoje['ETc']} mm")
    c4.metric("🛡️ Chuva", f"{hoje['Chuva']} mm")

    tabs = st.tabs(["🎓 Consultoria Técnica", "📊 Clima", "👁️ IA Vision", "🗺️ Mapa", "🔔 Notificações"])

    with tabs[0]:
        dados = BANCO_MASTER[cultura_sel]['fases'][fase_sel]
        
        
        
        st.markdown(f"### 🔥 Acúmulo Térmico (GDA): {gda_acum:.0f} / {meta_gda}")
        st.progress(min(1.0, gda_acum/meta_gda))
        
        estilo = "alert-low" if hoje['Umid'] < 85 else "alert-high"
        msg = "✅ Condição desfavorável a fungos." if estilo == "alert-low" else "🚨 ALERTA: Risco elevado de Requeima."
        
        

        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"<div class='tech-card'><b>🧬 Fisiologia:</b><br>{dados['desc']}</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='{estilo}'>{msg}</div>", unsafe_allow_html=True)
        with col2:
            st.markdown(f"<div class='tech-card'><b>🛠️ Manejo Sugerido:</b><br>{dados['manejo']}<br><hr><b>Prescrição:</b><br>{dados['quimica']}</div>", unsafe_allow_html=True)

    with tabs[4]:
        st.markdown(f"### 🔔 Central de Alertas")
        st.info(f"Sincronizado com: **{USER_EMAIL}**")
        if st.button("Ativar Relatórios Automáticos"):
            st.success(f"Protocolo ativo para {USER_EMAIL}!")
else:
    st.error("⚠️ Erro ao carregar dados de satélite.")
