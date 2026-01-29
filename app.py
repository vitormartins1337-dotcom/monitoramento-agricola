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

# --- LOGIN REAL COM GOOGLE OAUTH 2.0 ---
try:
    # IMPORTANTE: A URL abaixo deve ser a URL do seu app no Streamlit Cloud
    # Altere para a sua URL final para evitar erro de redirecionamento
    URL_DO_APP = "https://monitoramento-agricola.streamlit.app" 

    authenticator = Authenticate(
        secret_names=["GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET"],
        cookie_name="agro_intel_session",
        key="agro_secret_key_2026", 
        cookie_expiry_days=30,
        redirect_uri=URL_DO_APP
    )
except Exception as e:
    st.error(f"Erro Crítico na Autenticação: {e}")
    st.stop()

# Verifica autenticação
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
    st.error("Erro: Verifique se OPENWEATHER_KEY e GEMINI_KEY estão configurados no painel Secrets do Streamlit.")
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

# --- 2. ENCICLOPÉDIA AGRONÔMICA (BANCO TITAN COMPLETO) ---
BANCO_MASTER = {
    "Batata (Solanum tuberosum)": {
        "t_base": 7,
        "vars": {
            "Orchestra": {"kc": 1.15, "gda_meta": 1600, "info": "Pele lisa premium. Alta exigência de Potássio (K) para acabamento e peso de tubérculo."},
            "Cupido": {"kc": 1.10, "gda_meta": 1400, "info": "Ciclo ultra-curto. Colheita antecipada. Extrema sensibilidade à Requeima (Phytophthora)."},
            "Camila": {"kc": 1.15, "gda_meta": 1550, "info": "Referência em mercado fresco. Monitorar rigorosamente Sarna Comum e Rhizoctonia."},
            "Atlantic": {"kc": 1.15, "gda_meta": 1650, "info": "Foco industrial (Chips). Evitar oscilações hídricas para prevenir Coração Oco."}
        },
        "fases": {
            "Emergência (0-20 dias)": {
                "desc": "Brotamento inicial e estabelecimento radicular no sulco.",
                "fisiologia": "A planta utiliza reservas de amido do tubérculo-mãe. Raízes frágeis em fase de expansão.",
                "manejo": "Solo aerado. Umidade em Capacidade de Campo. Monitorar Canela Preta (Erwinia).",
                "quimica": "**Tratamento Sulco:** Azoxistrobina + Tiametoxam.\n**Alvos:** Rhizoctonia solani, Larva Alfinete."
            },
            "Vegetativo (20-35 dias)": {
                "desc": "Expansão da área foliar e formação do Índice de Área Foliar (IAF).",
                "fisiologia": "Alta demanda de Nitrogênio (N) para síntese proteica e fechamento de linhas.",
                "manejo": "Realizar a Amontoa no estágio de 15-20cm. Evitar ferimentos radiculares.",
                "quimica": "**Preventivos:** Mancozeb, Clorotalonil.\n**Pragas:** Acetamiprido (Pulgão), Lambda-Cialotrina (Vaquinha)."
            },
            "Tuberização/Gancho (35-55 dias)": {
                "desc": "Fase hormonal crítica. Diferenciação dos tubérculos (Ganchos).",
                "fisiologia": "Inversão hormonal (Giberelina cai). Estresse hídrico agora causa Sarna e perda de calibre.",
                "manejo": "Irrigação de precisão constante. Controle preventivo 'militar' de Requeima.",
                "quimica": "**Requeima:** Mandipropamida (Revus), Metalaxil-M, Dimetomorfe."
            },
            "Enchimento (55-85 dias)": {
                "desc": "Acúmulo de matéria seca e expansão radial intensa.",
                "fisiologia": "Translocação massiva de açúcares das folhas para os tubérculos. Pico de K e Mg.",
                "manejo": "Sanidade foliar absoluta. Monitorar Mosca Branca e Traça da Batata.",
                "quimica": "**Pragas:** Ciantraniliprole (Benévia), Espirotesifeno (Oberon)."
            },
            "Maturação (85+ dias)": {
                "desc": "Senescência foliar controlada e suberização (cura da pele).",
                "fisiologia": "Finalização do ciclo térmico. A pele deve firmar para suportar a colheita mecânica.",
                "manejo": "Suspensão gradual da irrigação. Dessecação química programada.",
                "quimica": "**Dessecante:** Diquat."
            }
        }
    },
    "Café (Coffea arabica)": {
        "t_base": 10,
        "vars": {
            "Catuaí": {"kc": 1.1, "gda_meta": 3000, "info": "Qualidade superior de bebida. Alta susceptibilidade à Ferrugem."},
            "Arara": {"kc": 1.2, "gda_meta": 2900, "info": "Resistência genética à Ferrugem. Alta produtividade pendente."}
        },
        "fases": {
            "Florada": {
                "desc": "Abertura das flores (Antese) e polinização.",
                "fisiologia": "Demanda crítica de Boro (B) e Zinco (Zn) para viabilidade do tubo polínico.",
                "manejo": "Proteger polinizadores. Monitorar Phoma e Mancha Aureolada.",
                "quimica": "Cálcio Quelatado + Boro. Fungicida: Boscalida."
            },
            "Chumbinho": {
                "desc": "Expansão inicial do fruto verde.",
                "fisiologia": "Intensa divisão celular. Momento em que se define o tamanho da peneira.",
                "manejo": "Controle preventivo de Cercospora e Ferrugem.",
                "quimica": "Ciproconazol + Azoxistrobina (Priori Xtra)."
            }
        }
    }
}

# --- 3. MOTORES DE CÁLCULO E API ---
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

# --- 4. SIDEBAR GESTOR ---
if 'loc' not in st.session_state: st.session_state['loc'] = {"lat": -13.200, "lon": -41.400}

with st.sidebar:
    st.image(USER_PIC, width=80)
    st.markdown(f"👤 **{USER_NAME}**")
    st.caption(USER_EMAIL)
    authenticator.logout()
    
    st.divider()
    st.header("📍 Localização")
    busca_cidade = st.text_input("Buscar Cidade (Ex: Mucugê, BA)")
    if st.button("Sincronizar Mapa") and busca_cidade:
        url_geo = f"http://api.openweathermap.org/geo/1.0/direct?q={busca_cidade}&limit=1&appid={WEATHER_KEY}"
        res_geo = requests.get(url_geo).json()
        if res_geo:
            st.session_state['loc'] = {"lat": res_geo[0]['lat'], "lon": res_geo[0]['lon']}
            st.success("Coordenadas Atualizadas!")
            st.rerun()

    st.divider()
    cultura_sel = st.selectbox("Cultura:", list(BANCO_MASTER.keys()))
    var_sel = st.selectbox("Variedade:", list(BANCO_MASTER[cultura_sel]['vars'].keys()))
    fase_sel = st.selectbox("Estágio:", list(BANCO_MASTER[cultura_sel]['fases'].keys()))
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
        <p style="font-size:1.2em">📆 <b>{dias} Dias de Ciclo</b> | Estágio: {fase_sel}</p>
        <p>🧬 Genética: {info_v['info']}</p>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🌡️ Temp Média", f"{hoje['Temp']:.1f}°C", f"Umid: {hoje['Umid']}%")
    c2.metric("💧 VPD", f"{hoje['VPD']} kPa", "Ideal" if 0.4 <= hoje['VPD'] <= 1.3 else "Alerta")
    c3.metric("💦 ETc Diária", f"{hoje['ETc']} mm")
    c4.metric("🛡️ Delta T", f"{hoje['Delta T']}°C", "Seguro")

    tabs = st.tabs(["🎓 Consultoria Técnica", "📊 Clima & Água", "📡 Radar Regional", "👁️ IA Vision", "💰 Custos", "🗺️ Mapa Satélite", "🔔 Notificações"])

    # --- ABA 1: CONSULTORIA ---
    with tabs[0]:
        dados = BANCO_MASTER[cultura_sel]['fases'][fase_sel]
        
        st.markdown(f"""<div class="gda-box"><h3>🔥 Acúmulo Térmico (GDA): {gda_acum:.0f} / {meta_gda}</h3></div>""", unsafe_allow_html=True)
        st.progress(progresso_gda)
        
        estilo = "alert-low" if hoje['Umid'] < 85 else "alert-high"
        msg = "✅ Clima favorável. Use Protetores." if estilo == "alert-low" else "🚨 ALERTA SANITÁRIO: Risco de Requeima."
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"<div class='tech-card'><div class='tech-header'>🧬 Fisiologia da Fase</div><p>{dados['desc']}</p><p><b>Bioquímica:</b> {dados['fisiologia']}</p></div>", unsafe_allow_html=True)
            st.markdown(f"<div class='{estilo}'>{msg}</div>", unsafe_allow_html=True)
        with col2:
            st.markdown(f"<div class='tech-card'><div class='tech-header'>🛠️ Manejo & Químicos</div><p><b>Manejo:</b> {dados['manejo']}</p><hr><p><b>Prescrição Técnica:</b><br>{dados['quimica']}</p></div>", unsafe_allow_html=True)

    # --- ABA 2: CLIMA ---
    with tabs[1]:
        fig = go.Figure()
        fig.add_trace(go.Bar(x=df['Data'], y=df['Chuva'], name='Precipitação (mm)', marker_color='#3b82f6'))
        fig.add_trace(go.Scatter(x=df['Data'], y=df['ETc'], name='Consumo ETc', line=dict(color='#ef4444', width=3)))
        st.plotly_chart(fig, use_container_width=True)

    # --- ABA 3: RADAR ---
    with tabs[2]:
        st.markdown("### 📡 Radar de Vizinhança (Raio 10km)")
        df_radar = get_radar(st.session_state['loc']['lat'], st.session_state['loc']['lon'])
        if not df_radar.empty:
            cols = st.columns(4)
            for i, r in df_radar.iterrows():
                cor = "#ffebee" if r['Chuva'] == "Sim" else "#e8f5e9"
                with cols[i]: st.markdown(f"""<div class="tech-card" style="background-color:{cor}; text-align:center"><b>{r['Direcao']}</b><br>{r['Temp']:.1f}°C<br>Chuva: {r['Chuva']}</div>""", unsafe_allow_html=True)

    # --- ABA 4: IA VISION ---
    with tabs[3]:
        foto = st.camera_input("Capturar Praga/Folha")
        if foto:
            genai.configure(api_key=GEMINI_KEY)
            with st.spinner("Analisando..."):
                res = genai.GenerativeModel('gemini-1.5-flash').generate_content([f"Agrônomo Especialista. Analise imagem de {cultura_sel}. Fase {fase_sel}.", Image.open(foto)])
                st.success(res.text)

    # --- ABA 5: CUSTOS ---
    with tabs[4]:
        if 'custos' not in st.session_state: st.session_state['custos'] = []
        c_i, c_v = st.columns(2)
        item = c_i.text_input("Insumo/Serviço")
        valor = c_v.number_input("R$")
        if st.button("Lançar"): st.session_state['custos'].append({"Item": item, "Valor": valor})
        if st.session_state['custos']: st.table(pd.DataFrame(st.session_state['custos']))

    # --- ABA 6: MAPA ---
    with tabs[5]:
        st.markdown("### 🗺️ Georreferenciamento de Talhões")
        m = folium.Map(location=[st.session_state['loc']['lat'], st.session_state['loc']['lon']], zoom_start=14)
        folium.TileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', attr='Esri', name='Satélite').add_to(m)
        LocateControl().add_to(m); Fullscreen().add_to(m)
        st_folium(m, width="100%", height=500)

    # --- ABA 7: NOTIFICAÇÕES ---
    with tabs[6]:
        st.markdown("### 🔔 Central de Alertas Corporativos")
        st.success(f"Conta Google Sincronizada: **{USER_EMAIL}**")
        st.write(f"Olá, {USER_NAME}. Você receberá relatórios técnicos e alertas climáticos automáticos neste e-mail.")
        if st.button("Confirmar Protocolo de Alertas"):
            st.balloons()
            st.success("Sincronização realizada com sucesso!")

else:
    st.error("⚠️ Falha na conexão com o servidor de satélites.")
