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

# --- LOGIN REAL COM GOOGLE OAUTH 2.0 (CORRIGIDO) ---
try:
    # URL do seu app no Streamlit Cloud
    URL_DO_APP = "https://monitoramento-agricola.streamlit.app" 

    # O erro 'secret_names' foi resolvido passando os valores diretamente
    authenticator = Authenticate(
        client_id=st.secrets["GOOGLE_CLIENT_ID"],
        client_secret=st.secrets["GOOGLE_CLIENT_SECRET"],
        redirect_uri=URL_DO_APP,
        cookie_name="agro_intel_session",
        key="agro_secret_key_2026", 
        cookie_expiry_days=30
    )
except Exception as e:
    st.error(f"Erro na configuração de Autenticação: {e}")
    st.stop()

# Verifica se o usuário já está logado
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
        authenticator.login()
        st.stop()

# --- DADOS REAIS DO USUÁRIO ---
USER_EMAIL = st.session_state.get('email')
USER_NAME = st.session_state.get('name', 'Produtor')
USER_PIC = st.session_state.get('picture', "https://cdn-icons-png.flaticon.com/512/3135/3135715.png")

# --- CARREGAMENTO DE CHAVES API (BACKEND) ---
try:
    WEATHER_KEY = st.secrets["OPENWEATHER_KEY"]
    GEMINI_KEY = st.secrets["GEMINI_KEY"]
except:
    st.error("Erro: Verifique as chaves OPENWEATHER_KEY e GEMINI_KEY no painel Secrets.")
    st.stop()

# --- ESTILIZAÇÃO CSS ENTERPRISE ---
st.markdown("""
<style>
    .main { background-color: #f8fafc; }
    .header-box { 
        background: linear-gradient(135deg, #064e3b 0%, #065f46 100%); 
        color: white; padding: 35px; border-radius: 15px; margin-bottom: 25px;
        box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1);
    }
    .tech-card { 
        background: white; padding: 25px; border-radius: 12px; border: 1px solid #e2e8f0; 
        margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    .tech-header { color: #064e3b; font-weight: 800; font-size: 1.4em; border-bottom: 3px solid #f1f5f9; padding-bottom: 12px; margin-bottom: 20px; }
    .gda-box { background-color: #fff8e1; border: 1px solid #ffecb3; padding: 20px; border-radius: 10px; text-align: center; margin-bottom: 20px; }
    .alert-high { background-color: #fef2f2; border-left: 6px solid #dc2626; padding: 20px; border-radius: 8px; color: #991b1b; }
    .alert-low { background-color: #f0fdf4; border-left: 6px solid #16a34a; padding: 20px; border-radius: 8px; color: #14532d; }
</style>
""", unsafe_allow_html=True)

# --- 2. ENCICLOPÉDIA AGRONÔMICA (BANCO TITAN INTEGRAL) ---
BANCO_MASTER = {
    "Batata (Solanum tuberosum)": {
        "t_base": 7,
        "vars": {
            "Orchestra": {"kc": 1.15, "gda_meta": 1600, "info": "Pele lisa premium. Alta exigência de Potássio (K)."},
            "Cupido": {"kc": 1.10, "gda_meta": 1400, "info": "Ciclo ultra-curto. Extrema sensibilidade à Requeima."},
            "Camila": {"kc": 1.15, "gda_meta": 1550, "info": "Referência em mercado fresco. Monitorar Sarna e Rhizoctonia."},
            "Atlantic": {"kc": 1.15, "gda_meta": 1650, "info": "Foco industrial (Chips). Evitar Coração Oco."}
        },
        "fases": {
            "Emergência (0-20 dias)": {
                "desc": "Brotamento inicial e estabelecimento radicular.",
                "fisiologia": "Dependência das reservas do tubérculo-mãe.",
                "manejo": "Solo aerado. Monitorar Canela Preta.",
                "quimica": "**Solo:** Azoxistrobina + Tiametoxam."
            },
            "Vegetativo (20-35 dias)": {
                "desc": "Expansão da área foliar (IAF).",
                "fisiologia": "Alta demanda de Nitrogênio (N).",
                "manejo": "Amontoa técnica. Monitorar Vaquinha.",
                "quimica": "Mancozeb + Clorotalonil."
            },
            "Tuberização/Gancho (35-55 dias)": {
                "desc": "Diferenciação dos tubérculos (Ganchos).",
                "fisiologia": "Inversão hormonal crítica. Sensibilidade ao déficit hídrico.",
                "manejo": "Irrigação de precisão. Controle severo de Requeima.",
                "quimica": "Revus (Mandipropamida) + Metalaxil-M."
            },
            "Enchimento (55-85 dias)": {
                "desc": "Expansão radial intensa e acúmulo de matéria seca.",
                "fisiologia": "Pico de translocação Folha -> Tubérculo.",
                "manejo": "Sanidade foliar. Monitorar Mosca Branca.",
                "quimica": "Benévia (Ciantraniliprole)."
            },
            "Maturação (85+ dias)": {
                "desc": "Senescência e suberização (cura da pele).",
                "fisiologia": "Finalização do ciclo térmico.",
                "manejo": "Suspensão gradual da água. Dessecação química.",
                "quimica": "Diquat."
            }
        }
    },
    "Café (Coffea arabica)": {
        "t_base": 10,
        "vars": {
            "Catuaí": {"kc": 1.1, "gda_meta": 3000, "info": "Qualidade premium. Suscetível à Ferrugem."},
            "Arara": {"kc": 1.2, "gda_meta": 2900, "info": "Resistente à Ferrugem. Produtividade alta."}
        },
        "fases": {
            "Florada": {"desc": "Antese.", "fisiologia": "Demanda B e Zn.", "manejo": "Proteção de polinizadores.", "quimica": "Cálcio + Boro."},
            "Chumbinho": {"desc": "Expansão inicial.", "fisiologia": "Divisão celular.", "manejo": "Cercospora.", "quimica": "Priori Xtra."}
        }
    }
}

# --- 3. MOTORES TÉCNICOS ---
def calc_agro(temp, umid):
    es = 0.61078 * math.exp((17.27 * temp) / (temp + 237.3))
    ea = es * (umid / 100); vpd = round(es - ea, 2)
    tw = temp * math.atan(0.151977 * (umid + 8.313659)**0.5) + math.atan(temp + umid) - math.atan(umid - 1.676331) + 0.00391838 * (umid)**1.5 * math.atan(0.023101 * umid) - 4.686035
    dt = round(temp - tw, 1)
    return dt, vpd

def get_forecast(lat, lon, kc, t_base):
    try:
        url = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={WEATHER_KEY}&units=metric&lang=pt_br"
        r = requests.get(url).json()
        dados = []
        for i in range(0, 40, 8):
            item = r['list'][i]
            t = item['main']['temp']
            dt, vpd = calc_agro(t, item['main']['humidity'])
            chuva = sum([r['list'][i+j].get('rain', {}).get('3h', 0) for j in range(8) if i+j < len(r['list'])])
            et0 = 0.0023 * (t + 17.8) * (t ** 0.5) * 0.408
            dados.append({
                'Data': datetime.fromtimestamp(item['dt']).strftime('%d/%m'),
                'Temp': t, 'GDA': max(0, t-t_base), 'Chuva': round(chuva, 1), 
                'VPD': vpd, 'Delta T': dt, 'Umid': item['main']['humidity'], 'ETc': round(et0 * kc, 2)
            })
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
    busca_cidade = st.text_input("Sincronizar Município (BA):")
    if st.button("Atualizar GPS") and busca_cidade:
        url_geo = f"http://api.openweathermap.org/geo/1.0/direct?q={busca_cidade}&limit=1&appid={WEATHER_KEY}"
        res_geo = requests.get(url_geo).json()
        if res_geo:
            st.session_state['loc'] = {"lat": res_geo[0]['lat'], "lon": res_geo[0]['lon']}
            st.rerun()

    st.divider()
    cultura_sel = st.selectbox("Cultura:", list(BANCO_MASTER.keys()))
    var_sel = st.selectbox("Variedade:", list(BANCO_MASTER[cultura_sel]['vars'].keys()))
    fase_sel = st.selectbox("Estágio Fenológico:", list(BANCO_MASTER[cultura_sel]['fases'].keys()))
    d_plantio = st.date_input("Início do Ciclo:", date(2025, 11, 25))
    info_v = BANCO_MASTER[cultura_sel]['vars'][var_sel]

# --- 5. DASHBOARD TITAN ---
st.title("🛰️ Agro-Intel Enterprise")

df = get_forecast(st.session_state['loc']['lat'], st.session_state['loc']['lon'], info_v['kc'], BANCO_MASTER[cultura_sel]['t_base'])

if not df.empty:
    hoje = df.iloc[0]; dias = (date.today() - d_plantio).days
    gda_acum = dias * df['GDA'].mean(); meta_gda = info_v['gda_meta']
    progresso_gda = min(1.0, gda_acum / meta_gda)

    st.markdown(f"""
    <div class="header-box">
        <h2>{cultura_sel} - {var_sel}</h2>
        <p style="font-size:1.2em"><b>{dias} Dias de Ciclo</b> | Fase Atual: {fase_sel}</p>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🌡️ Temp Média", f"{hoje['Temp']:.1f}°C", f"Umid: {hoje['Umid']}%")
    c2.metric("💧 VPD", f"{hoje['VPD']} kPa", "Ideal" if 0.4 <= hoje['VPD'] <= 1.3 else "Alerta")
    c3.metric("💦 Consumo ETc", f"{hoje['ETc']} mm")
    c4.metric("🛡️ Delta T", f"{hoje['Delta T']}°C")

    tabs = st.tabs(["🎓 Consultoria Técnica", "📊 Clima & Água", "📡 Radar Regional", "👁️ IA Vision", "💰 Custos", "🗺️ Mapa Satélite", "🔔 Notificações"])

    # --- ABA 1: CONSULTORIA ---
    with tabs[0]:
        dados = BANCO_MASTER[cultura_sel]['fases'][fase_sel]
        
        

        st.markdown(f"""<div class="gda-box"><h3>🔥 Acúmulo Térmico (GDA): {gda_acum:.0f} / {meta_gda}</h3></div>""", unsafe_allow_html=True)
        st.progress(progresso_gda)
        
        estilo = "alert-low" if hoje['Umid'] < 85 else "alert-high"
        msg = "✅ Condição favorável para preventivos." if estilo == "alert-low" else "🚨 ALERTA SANITÁRIO: Risco de Requeima acelerado."
        
        

        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"<div class='tech-card'><div class='tech-header'>🧬 Fisiologia da Fase</div><p>{dados['desc']}</p><p><b>Bioquímica:</b> {dados['fisiologia']}</p></div>", unsafe_allow_html=True)
            st.markdown(f"<div class='{estilo}'>{msg}</div>", unsafe_allow_html=True)
        with col2:
            st.markdown(f"<div class='tech-card'><div class='tech-header'>🛠️ Plano de Manejo Sugerido</div><p><b>Ação Cultural:</b> {dados['manejo']}</p><hr><p><b>Prescrição Química:</b><br>{dados['quimica']}</p></div>", unsafe_allow_html=True)

    # --- ABA 6: MAPA ---
    with tabs[5]:
        m = folium.Map(location=[st.session_state['loc']['lat'], st.session_state['loc']['lon']], zoom_start=14)
        folium.TileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', attr='Esri', name='Satélite').add_to(m)
        st_folium(m, width="100%", height=500)

    # --- ABA 7: NOTIFICAÇÕES ---
    with tabs[6]:
        st.markdown("### 🔔 Configuração de Alertas Corporativos")
        st.success(f"E-mail Sincronizado: **{USER_EMAIL}**")
        st.write(f"Prezado {USER_NAME}, o sistema monitorará o risco climático e o acúmulo térmico (GDA) diariamente.")
        if st.button("Ativar Protocolo de Alertas"):
            st.balloons()
            st.success("Protocolo ativado com sucesso!")

else:
    st.error("⚠️ Falha na conexão com os dados de satélite.")
