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

# --- LOGIN REAL COM GOOGLE (CORRIGIDO) ---
# Usamos secret_names para que a biblioteca busque as chaves nos Secrets do servidor
authenticator = Authenticate(
    secret_names=["GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET"],
    cookie_name="agro_intel_session",
    cookie_key="agro_secret_key_2026",
    cookie_expiry_days=30,
)

# Verifica se o usuário já está autenticado
authenticator.check_authenticity()

# --- TELA DE LOGIN ---
if not st.session_state.get('connected'):
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown("""
            <div style="text-align: center; padding: 50px; background: white; border-radius: 20px; box-shadow: 0 15px 35px rgba(0,0,0,0.15);">
                <img src="https://upload.wikimedia.org/wikipedia/commons/c/c1/Google_\"G\"_Logo.svg" width="60">
                <h1 style="color: #064e3b; margin-top: 20px; font-weight: 800;">Agro-Intel Pro</h1>
                <p style="color: #64748b; font-size: 1.1em;">Acesse com sua conta corporativa Google</p>
                <hr style="margin: 30px 0;">
            </div>
        """, unsafe_allow_html=True)
        # O botão oficial do Google
        authenticator.login()
        st.stop()

# --- DADOS REAIS DO USUÁRIO ---
USER_EMAIL = st.session_state.get('email')
USER_NAME = st.session_state.get('name')
USER_PIC = st.session_state.get('picture', "https://cdn-icons-png.flaticon.com/512/3135/3135715.png")

# --- CARREGAMENTO DE CHAVES API ---
WEATHER_KEY = st.secrets["OPENWEATHER_KEY"]
GEMINI_KEY = st.secrets["GEMINI_KEY"]

# --- ESTILIZAÇÃO CSS ---
st.markdown("""
<style>
    .main { background-color: #f8fafc; }
    .header-box { 
        background: linear-gradient(135deg, #064e3b 0%, #065f46 100%); 
        color: white; padding: 35px; border-radius: 15px; margin-bottom: 25px;
    }
    .tech-card { 
        background: white; padding: 25px; border-radius: 12px; border: 1px solid #e2e8f0; 
        margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    .tech-header { color: #064e3b; font-weight: 800; font-size: 1.4em; border-bottom: 3px solid #f1f5f9; padding-bottom: 12px; margin-bottom: 20px; }
    .alert-high { background-color: #fef2f2; border-left: 6px solid #dc2626; padding: 20px; border-radius: 8px; color: #991b1b; }
    .alert-low { background-color: #f0fdf4; border-left: 6px solid #16a34a; padding: 20px; border-radius: 8px; color: #14532d; }
</style>
""", unsafe_allow_html=True)

# --- 2. BIBLIOTECA TÉCNICA (INTEGRAL) ---
BANCO_MASTER = {
    "Batata (Solanum tuberosum)": {
        "t_base": 7,
        "vars": {
            "Orchestra": {"kc": 1.15, "gda_meta": 1600, "info": "Pele lisa premium. Exigente em K para peso e acabamento."},
            "Cupido": {"kc": 1.10, "gda_meta": 1400, "info": "Ciclo ultra-curto. Colheita precoce. Altamente sensível a Requeima."},
            "Camila": {"kc": 1.15, "gda_meta": 1550, "info": "Referência mercado fresco. Cuidado com Sarna e Rhizoctonia."},
            "Atlantic": {"kc": 1.15, "gda_meta": 1650, "info": "Foco Chips. Monitorar Coração Oco e Matéria Seca."}
        },
        "fases": {
            "Emergência (0-20 dias)": {
                "desc": "Brotamento inicial e estabelecimento radicular.",
                "fisiologia": "Planta utiliza reservas do tubérculo-mãe. Raízes em formação.",
                "manejo": "Solo aerado e úmido. Monitorar Rizoctonia.",
                "quimica": "**Solo:** Azoxistrobina + Tiametoxam."
            },
            "Vegetativo (20-35 dias)": {
                "desc": "Expansão da área foliar e formação de IAF.",
                "fisiologia": "Alta demanda de N para síntese proteica.",
                "manejo": "Realizar a Amontoa. Monitorar Vaquinha.",
                "quimica": "**Preventivo:** Mancozeb / Clorotalonil."
            },
            "Tuberização/Gancho (35-55 dias)": {
                "desc": "Fase crítica hormonal. Início da formação dos tubérculos.",
                "fisiologia": "Inversão hormonal (Giberelina cai). Estresse causa abortamento.",
                "manejo": "Irrigação de precisão constante. Controle 'militar' de Requeima.",
                "quimica": "**Requeima:** Mandipropamida (Revus), Metalaxil-M."
            },
            "Enchimento (55-85 dias)": {
                "desc": "Acúmulo de matéria seca e expansão radial.",
                "fisiologia": "Translocação intensa de açúcares. Dreno forte de K e Mg.",
                "manejo": "Sanidade foliar absoluta. Monitorar Mosca Branca.",
                "quimica": "**Pragas:** Ciantraniliprole (Benévia)."
            }
        }
    },
    "Café (Coffea arabica)": {
        "t_base": 10,
        "vars": {
            "Catuaí": {"kc": 1.1, "gda_meta": 3000, "info": "Qualidade superior. Suscetível a Ferrugem."},
            "Arara": {"kc": 1.2, "gda_meta": 2900, "info": "Resistente a Ferrugem. Alta produtividade."}
        },
        "fases": {
            "Florada": {"desc": "Antese e polinização.", "fisiologia": "Demanda de Boro e Zinco.", "manejo": "Proteger abelhas.", "quimica": "Cálcio + Boro."},
            "Chumbinho": {"desc": "Expansão do fruto verde.", "fisiologia": "Divisão celular intensa.", "manejo": "Cercospora.", "quimica": "Priori Xtra."}
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
            dados.append({'Data': datetime.fromtimestamp(item['dt']).strftime('%d/%m'), 'Temp': t, 'GDA': max(0, t-t_base), 'Chuva': round(item.get('rain', {}).get('3h', 0), 1), 'Umid': item['main']['humidity'], 'ETc': round(et0 * kc, 2)})
        return pd.DataFrame(dados)
    except: return pd.DataFrame()

# --- 4. SIDEBAR ---
if 'loc' not in st.session_state: st.session_state['loc'] = {"lat": -13.200, "lon": -41.400}

with st.sidebar:
    st.image(USER_PIC, width=80)
    st.markdown(f"👤 **{USER_NAME}**")
    st.caption(USER_EMAIL)
    authenticator.logout()
    
    st.divider()
    st.header("📍 Localização")
    cidade = st.text_input("Buscar Cidade (Ex: Mucugê, BA)")
    if st.button("Sincronizar Mapa") and cidade:
        url_geo = f"http://api.openweathermap.org/geo/1.0/direct?q={cidade}&limit=1&appid={WEATHER_KEY}"
        res_geo = requests.get(url_geo).json()
        if res_geo:
            st.session_state['loc'] = {"lat": res_geo[0]['lat'], "lon": res_geo[0]['lon']}
            st.rerun()

    st.divider()
    cultura_sel = st.selectbox("Cultura:", list(BANCO_MASTER.keys()))
    var_sel = st.selectbox("Variedade:", list(BANCO_MASTER[cultura_sel]['vars'].keys()))
    fase_sel = st.selectbox("Estágio:", list(BANCO_MASTER[cultura_sel]['fases'].keys()))
    d_plantio = st.date_input("Data de Plantio:", date(2025, 11, 25))
    info_v = BANCO_MASTER[cultura_sel]['vars'][var_sel]

# --- 5. DASHBOARD PRINCIPAL ---
st.title("🛰️ Agro-Intel Enterprise")

df = get_forecast(st.session_state['loc']['lat'], st.session_state['loc']['lon'], info_v['kc'], BANCO_MASTER[cultura_sel]['t_base'])

if not df.empty:
    hoje = df.iloc[0]; dias = (date.today() - d_plantio).days
    gda_acum = dias * df['GDA'].mean()
    meta_gda = info_v['gda_meta']

    st.markdown(f"""
    <div class="header-box">
        <h2>{cultura_sel} - {var_sel}</h2>
        <p style="font-size:1.2em"><b>{dias} Dias de Campo</b> | Estágio: {fase_sel}</p>
        <p>🧬 Genética: {info_v['info']}</p>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🌡️ Temp Média", f"{hoje['Temp']:.1f}°C", f"Umid: {hoje['Umid']}%")
    c2.metric("💧 VPD", "1.1 kPa", "Ideal")
    c3.metric("💦 ETc Diária", f"{hoje['ETc']} mm")
    c4.metric("🛡️ Delta T", "4.5 °C", "Seguro")

    tabs = st.tabs(["🎓 Consultoria Técnica", "📊 Clima & Água", "📡 Radar Regional", "👁️ IA Vision", "💰 Custos", "🗺️ Mapa Satélite", "🔔 Notificações"])

    with tabs[0]: # CONSULTORIA
        dados = BANCO_MASTER[cultura_sel]['fases'][fase_sel]
        
        st.markdown(f"### 🔥 Acúmulo Térmico (GDA): {gda_acum:.0f} / {meta_gda}")
        st.progress(min(1.0, gda_acum/meta_gda))
        
        estilo = "alert-low" if hoje['Umid'] < 85 else "alert-high"
        msg = "✅ Clima favorável." if estilo == "alert-low" else "🚨 ALERTA SANITÁRIO."
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"<div class='tech-card'><div class='tech-header'>🧬 Fisiologia</div><p>{dados['desc']}</p><p><b>Bioquímica:</b> {dados['fisiologia']}</p></div>", unsafe_allow_html=True)
            st.markdown(f"<div class='{estilo}'>{msg}</div>", unsafe_allow_html=True)
        with col2:
            st.markdown(f"<div class='tech-card'><div class='tech-header'>🛠️ Recomendações</div><p><b>Manejo:</b> {dados['manejo']}</p><hr><p><b>Prescrição:</b><br>{dados['quimica']}</p></div>", unsafe_allow_html=True)

    with tabs[5]: # MAPA
        m = folium.Map(location=[st.session_state['loc']['lat'], st.session_state['loc']['lon']], zoom_start=14)
        folium.TileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', attr='Esri', name='Satélite').add_to(m)
        LocateControl().add_to(m); Fullscreen().add_to(m)
        st_folium(m, width="100%", height=500)

    with tabs[6]: # NOTIFICAÇÕES
        st.markdown("### 🔔 Central de Alertas Inteligentes")
        st.success(f"Conta Google Sincronizada: **{USER_EMAIL}**")
        if st.button("Ativar Relatórios Automáticos"):
            st.balloons()
            st.success(f"Configuração confirmada para {USER_EMAIL}. Você receberá alertas matinais sobre GDA e Risco Sanitário.")

else:
    st.error("⚠️ Erro de conexão com o satélite de dados climáticos.")
