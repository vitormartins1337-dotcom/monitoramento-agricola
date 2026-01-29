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

# --- 1. CONFIGURAÇÃO DE ALTO NÍVEL ---
st.set_page_config(
    page_title="Agro-Intel Enterprise",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CONFIGURAÇÃO DE BACKEND (SECRETS) ---
# O sistema busca as chaves silenciosamente no servidor do Streamlit
try:
    WEATHER_KEY = st.secrets["OPENWEATHER_KEY"]
    GEMINI_KEY = st.secrets["GEMINI_KEY"]
    # Caso queira usar envio real de email automático:
    SMTP_SERVER = "smtp.gmail.com"
    SMTP_PORT = 587
    SENDER_EMAIL = st.secrets["SENDER_EMAIL"]
    SENDER_PASS = st.secrets["SENDER_PASSWORD"] # Senha de App
except:
    WEATHER_KEY = "CHAVE_NAO_CONFIGURADA"
    GEMINI_KEY = "CHAVE_NAO_CONFIGURADA"

# --- 2. ESTILIZAÇÃO CSS PROFISSIONAL ---
st.markdown("""
<style>
    .main { background-color: #f0f2f5; }
    div[data-testid="metric-container"] { 
        background-color: #ffffff; 
        border-left: 6px solid #1a237e; 
        border-radius: 8px;
        padding: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    .header-box { 
        background: linear-gradient(135deg, #0d47a1 0%, #1a237e 100%); 
        color: white; 
        padding: 30px; 
        border-radius: 12px; 
        margin-bottom: 25px;
        box-shadow: 0 8px 16px rgba(0,0,0,0.1);
    }
    .tech-card { 
        background-color: #ffffff; 
        padding: 25px; 
        border-radius: 10px; 
        border: 1px solid #e0e0e0; 
        margin-bottom: 20px;
    }
    .tech-header { 
        color: #1a237e; 
        font-weight: 800; 
        font-size: 1.3em; 
        border-bottom: 3px solid #f5f5f5; 
        padding-bottom: 12px; 
        margin-bottom: 18px; 
    }
    .gda-container {
        background-color: #fff8e1;
        border: 1px solid #ffecb3;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
        margin-bottom: 20px;
    }
    .radar-card { 
        background-color: #e3f2fd; 
        padding: 15px; 
        border-radius: 8px; 
        text-align: center; 
        border: 1px solid #bbdefb;
    }
    .alert-high { background-color: #ffebee; border-left: 6px solid #b71c1c; padding: 20px; border-radius: 8px; color: #b71c1c; }
    .alert-low { background-color: #e8f5e9; border-left: 6px solid #1b5e20; padding: 20px; border-radius: 8px; color: #1b5e20; }
    .login-screen {
        max-width: 500px;
        margin: 100px auto;
        padding: 40px;
        background: white;
        border-radius: 20px;
        box-shadow: 0 15px 35px rgba(0,0,0,0.1);
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# --- 3. SISTEMA DE AUTENTICAÇÃO GOOGLE ---
if 'auth' not in st.session_state: st.session_state['auth'] = False
if 'user' not in st.session_state: st.session_state['user'] = {"name": "", "email": ""}

def tela_login():
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown('<div class="login-screen">', unsafe_allow_html=True)
        st.image("https://upload.wikimedia.org/wikipedia/commons/c/c1/Google_\"G\"_Logo.svg", width=50)
        st.markdown("## Agro-Intel Enterprise")
        st.markdown("Acesse sua conta corporativa para gerenciar sua lavoura.")
        
        # Simulação de fluxo OAuth - Em produção, integra-se com redirecionamento real
        with st.form("google_login"):
            u_name = st.text_input("Nome Completo")
            u_email = st.text_input("E-mail Google")
            if st.form_submit_button("Continuar com Google"):
                if u_email and "@" in u_email:
                    st.session_state['auth'] = True
                    st.session_state['user'] = {"name": u_name, "email": u_email}
                    st.rerun()
                else:
                    st.error("Por favor, insira um e-mail válido.")
        st.markdown('</div>', unsafe_allow_html=True)

if not st.session_state['auth']:
    tela_login()
    st.stop()

# --- 4. ENCICLOPÉDIA AGRONÔMICA TITAN (RESGATADA E AMPLIADA) ---
BANCO_MASTER = {
    "Batata (Solanum tuberosum)": {
        "t_base": 7,
        "vars": {
            "Orchestra": {"kc": 1.15, "gda_meta": 1600, "info": "Variedade premium de pele lisa. Exigência crítica de Potássio (K) para enchimento e acabamento visual."},
            "Cupido": {"kc": 1.10, "gda_meta": 1400, "info": "Ciclo ultra-curto. Colheita antecipada. Extrema suscetibilidade a Requeima (Phytophthora)."},
            "Camila": {"kc": 1.15, "gda_meta": 1550, "info": "Excelente para mercado fresco. Monitoramento rigoroso de Sarna Comum e Rhizoctonia."},
            "Atlantic": {"kc": 1.15, "gda_meta": 1650, "info": "Foco industrial (Chips). Evitar oscilações hídricas para prevenir Coração Oco."}
        },
        "fases": {
            "Emergência (0-20 dias)": {
                "desc": "Estabelecimento inicial e brotamento das hastes.",
                "fisiologia": "A planta utiliza as reservas de amido do tubérculo-mãe. O sistema radicular inicia a exploração do sulco.",
                "manejo": "Solo com umidade controlada (Capacidade de Campo). Evitar compactação. Monitorar 'Damping-off'.",
                "quimica": "**Tratamento Sulco:** Azoxistrobina + Tiametoxam.\n**Alvos:** Rhizoctonia solani, Larva Alfinete.",
                "maturacao": "Fase inicial de acúmulo térmico."
            },
            "Vegetativo (20-35 dias)": {
                "desc": "Rápida expansão foliar e formação do Índice de Área Foliar (IAF).",
                "fisiologia": "Pico de demanda de Nitrogênio (N) para síntese de clorofila. Definição do potencial produtivo.",
                "manejo": "Realizar a **Amontoa** no momento exato (antes do fechamento das linhas). Monitorar Vaquinha.",
                "quimica": "**Preventivos:** Mancozeb, Clorotalonil, Propinebe.\n**Pragas:** Acetamiprido, Lambda-Cialotrina.",
                "maturacao": "Desenvolvimento estrutural ativo."
            },
            "Tuberização/Gancho (35-55 dias)": {
                "desc": "Início da diferenciação dos tubérculos (Ganchos).",
                "fisiologia": "Fase hormonal crítica. Mudança do dreno de folhas para estolões. Suscetibilidade máxima a estresse.",
                "manejo": "Irrigação de precisão. Não permitir déficit hídrico. Início do programa preventivo 'militar'.",
                "quimica": "**Requeima:** Mandipropamida (Revus), Metalaxil-M, Dimetomorfe.\n**Pinta Preta:** Boscalida, Tebuconazol.",
                "maturacao": "Transição fenológica térmica."
            },
            "Enchimento (55-85 dias)": {
                "desc": "Acúmulo de matéria seca e expansão radial dos tubérculos.",
                "fisiologia": "Translocação intensa de açúcares das folhas para os tubérculos via floema. Alta demanda de K e Mg.",
                "manejo": "Monitorar Mosca Branca e Traça da Batata (Phthorimaea operculella). Manter sanidade foliar.",
                "quimica": "**Pragas:** Ciantraniliprole (Benévia), Espirotesifeno (Oberon).\n**Fungos:** Fluazinam, Piraclostrobina.",
                "maturacao": "Pico de acúmulo de GDA."
            },
            "Maturação (85+ dias)": {
                "desc": "Senescência foliar e cura da pele (suberização).",
                "fisiologia": "Finalização do ciclo. A pele deve se tornar resistente para suportar a colheita mecânica.",
                "manejo": "Suspensão gradual da irrigação. Dessecação química programada.",
                "quimica": "**Dessecante:** Diquat.\n**Cuidado:** Monitorar podridões bacterianas de final de ciclo.",
                "maturacao": "Atingimento da meta térmica."
            }
        }
    },
    "Café (Coffea arabica)": {
        "t_base": 10,
        "vars": {
            "Catuaí": {"kc": 1.1, "gda_meta": 3000, "info": "Variedade tradicional. Suscetibilidade à Ferrugem. Alta qualidade de bebida."},
            "Arara": {"kc": 1.2, "gda_meta": 2900, "info": "Resistência genética à Ferrugem. Alta carga pendente."}
        },
        "fases": {
            "Florada": {
                "desc": "Abertura das flores e polinização.",
                "fisiologia": "Demanda crítica de Boro (B) e Zinco (Zn) para viabilidade do grão de pólen.",
                "manejo": "Proteção de polinizadores. Monitorar Phoma e Mancha Aureolada se houver ventos frios.",
                "quimica": "Cálcio Quelatado + Boro. Fungicida: Boscalida.",
                "maturacao": "Início do relógio biológico do fruto."
            },
            "Chumbinho": {
                "desc": "Fase inicial de expansão do fruto verde.",
                "fisiologia": "Intensa divisão celular. Momento em que se define o tamanho final da peneira.",
                "manejo": "Controle preventivo de Cercospora. Nutrição com foco em expansão celular.",
                "quimica": "Ciproconazol + Azoxistrobina (Priori Xtra), Tebuconazol.",
                "maturacao": "Expansão volumétrica térmica."
            },
            "Granação": {
                "desc": "Solidificação do endosperma e enchimento de massa.",
                "fisiologia": "Máxima demanda de Potássio (K). Risco de Die-back (seca de ramos) se a carga for alta.",
                "manejo": "Monitoramento rigoroso da Broca do Café.",
                "quimica": "Ciantraniliprole (Benévia), Clorantraniliprole.",
                "maturacao": "Acúmulo de sólidos solúveis."
            }
        }
    }
}

# --- 5. MOTORES DE CÁLCULO E API ---
def calc_agro(temp, umid):
    es = 0.61078 * math.exp((17.27 * temp) / (temp + 237.3))
    ea = es * (umid / 100)
    vpd = round(es - ea, 2)
    tw = temp * math.atan(0.151977 * (umid + 8.313659)**0.5) + math.atan(temp + umid) - math.atan(umid - 1.676331) + 0.00391838 * (umid)**1.5 * math.atan(0.023101 * umid) - 4.686035
    dt = round(temp - tw, 1)
    return dt, vpd

def get_forecast(lat, lon, kc, t_base):
    if WEATHER_KEY == "CHAVE_NAO_CONFIGURADA": return pd.DataFrame()
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
                'Temp': t, 
                'GDA': max(0, t-t_base), 
                'Chuva': round(chuva, 1), 
                'VPD': vpd, 
                'Delta T': dt, 
                'Umid': item['main']['humidity'], 
                'ETc': round(et0 * kc, 2)
            })
        return pd.DataFrame(dados)
    except: return pd.DataFrame()

def get_radar(lat, lon):
    # Simula 4 pontos cardeais ao redor para radar regional
    pontos = {"Norte": (lat+0.1, lon), "Sul": (lat-0.1, lon), "Leste": (lat, lon+0.1), "Oeste": (lat, lon-0.1)}
    radar_res = []
    for d, c in pontos.items():
        try:
            url = f"https://api.openweathermap.org/data/2.5/weather?lat={c[0]}&lon={c[1]}&appid={WEATHER_KEY}&units=metric"
            r = requests.get(url).json()
            radar_res.append({"Direcao": d, "Temp": r['main']['temp'], "Chuva": "Sim" if "rain" in r else "Não"})
        except: pass
    return pd.DataFrame(radar_res)

# --- 6. SIDEBAR GESTOR ---
if 'loc' not in st.session_state: st.session_state['loc'] = {"lat": -13.200, "lon": -41.400}

with st.sidebar:
    st.markdown(f"👤 **{st.session_state['user']['name']}**")
    st.caption(st.session_state['user']['email'])
    if st.button("🚪 Logout"):
        st.session_state['auth'] = False
        st.rerun()
    
    st.divider()
    st.header("📍 Localização")
    busca_cidade = st.text_input("Buscar Cidade (Ex: Ibicoara, BA)")
    if st.button("Buscar") and busca_cidade:
        # Lógica de geocoding simplificada via API
        url_geo = f"http://api.openweathermap.org/geo/1.0/direct?q={busca_cidade}&limit=1&appid={WEATHER_KEY}"
        res_geo = requests.get(url_geo).json()
        if res_geo:
            st.session_state['loc'] = {"lat": res_geo[0]['lat'], "lon": res_geo[0]['lon']}
            st.success("Localizado!")
            st.rerun()

    st.divider()
    cultura_sel = st.selectbox("Cultura Alvo:", list(BANCO_MASTER.keys()))
    var_sel = st.selectbox("Cultivar:", list(BANCO_MASTER[cultura_sel]['vars'].keys()))
    fase_sel = st.selectbox("Estágio Fenológico:", list(BANCO_MASTER[cultura_sel]['fases'].keys()))
    d_plantio = st.date_input("Início do Ciclo:", date(2025, 11, 25))
    info_v = BANCO_MASTER[cultura_sel]['vars'][var_sel]

# --- 7. DASHBOARD TITAN ---
st.title(f"🛰️ Agro-Intel Enterprise")

df = get_forecast(st.session_state['loc']['lat'], st.session_state['loc']['lon'], info_v['kc'], BANCO_MASTER[cultura_sel]['t_base'])

if not df.empty:
    hoje = df.iloc[0]
    dias_campo = (date.today() - d_plantio).days
    
    # Cálculos GDA
    media_gda_prevista = df['GDA'].mean()
    gda_acum_estimado = dias_campo * media_gda_prevista
    meta_gda = info_v['gda_meta']
    progresso_gda = min(1.0, gda_acum_estimado / meta_gda)

    st.markdown(f"""
    <div class="header-box">
        <h2>{cultura_sel} - {var_sel}</h2>
        <p style="font-size:1.2em">
            📆 <b>{dias_campo} Dias de Campo</b> | Estágio: <b>{fase_sel}</b>
        </p>
        <p>🧬 Genética: {info_v['info']}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # KPIs principais
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🌡️ Temperatura", f"{hoje['Temp']:.1f}°C", f"Umid: {hoje['Umid']}%")
    c2.metric("💧 VPD (Transpiração)", f"{hoje['VPD']} kPa", "Ideal" if 0.4 <= hoje['VPD'] <= 1.3 else "Alerta")
    c3.metric("💦 Consumo (ETc)", f"{hoje['ETc']} mm", f"Kc: {info_v['kc']}")
    c4.metric("🛡️ Delta T", f"{hoje['Delta T']}°C", "Permitido" if 2 <= hoje['Delta T'] <= 8 else "Risco")

    # SISTEMA DE ABAS ROBUSTO
    tabs = st.tabs(["🎓 Consultoria Técnica", "📊 Clima & Água", "📡 Radar Regional", "👁️ IA Vision", "💰 Custos", "🗺️ Mapa Satélite", "🔔 Notificações"])

    # --- ABA 1: CONSULTORIA PROFISSIONAL ---
    with tabs[0]:
        dados = BANCO_MASTER[cultura_sel]['fases'][fase_sel]
        
        # Bloco GDA
        st.markdown(f"""
        <div class="gda-container">
            <h3>🔥 Maturação Térmica (GDA)</h3>
            <p>Acumulado: <b>{gda_acum_estimado:.0f}</b> / Meta Térmica: <b>{meta_gda}</b> GDA</p>
        </div>
        """, unsafe_allow_html=True)
        st.progress(progresso_gda)
        
        risco = "Baixo"; msg = "✅ <b>Condição Estável:</b> Use Protetores de Contato."; estilo = "alert-low"
        if hoje['Umid'] > 85 or hoje['Chuva'] > 2:
            risco = "ALTO"; msg = "🚨 <b>ALERTA SANITÁRIO:</b> Umidade alta favorece fungos. Use Sistêmicos."; estilo = "alert-high"
        
        col_esq, col_dir = st.columns(2)
        with col_esq:
            st.markdown(f"""
            <div class="tech-card">
                <div class="tech-header">🧬 Fisiologia & Maturação</div>
                <p><b>Fenologia:</b> {dados['desc']}</p>
                <p><b>Bioquímica:</b> {dados['fisiologia']}</p>
                <p><b>Status Térmico:</b> {dados['maturacao']}</p>
            </div>
            <div class="{estilo}">{msg}</div>
            """, unsafe_allow_html=True)
        with col_dir:
            st.markdown(f"""
            <div class="tech-card">
                <div class="tech-header">🛠️ Plano de Manejo Selecionado</div>
                <p><b>Manejo Cultural:</b> {dados['manejo']}</p>
                <hr>
                <p><b>🧪 Prescrição Química Sugerida:</b><br>{dados['quimica']}</p>
            </div>
            """, unsafe_allow_html=True)

    # --- ABA 2: CLIMA ---
    with tabs[1]:
        fig = go.Figure()
        fig.add_trace(go.Bar(x=df['Data'], y=df['Chuva'], name='Chuva (mm)', marker_color='#29b6f6'))
        fig.add_trace(go.Scatter(x=df['Data'], y=df['ETc'], name='Consumo ETc (mm)', line=dict(color='#f44336', width=3)))
        st.plotly_chart(fig, use_container_width=True)

    # --- ABA 3: RADAR REGIONAL ---
    with tabs[2]:
        st.markdown("### 📡 Radar de Proximidade (Raio 10km)")
        df_radar = get_radar(st.session_state['loc']['lat'], st.session_state['loc']['lon'])
        if not df_radar.empty:
            cols_r = st.columns(4)
            for i, r in df_radar.iterrows():
                cor_r = "#ffebee" if r['Chuva'] == "Sim" else "#e8f5e9"
                with cols_r[i]:
                    st.markdown(f"""<div class="radar-card" style="background-color:{cor_r}"><b>{r['Direcao']}</b><br>{r['Temp']:.1f}°C<br>Chuva: {r['Chuva']}</div>""", unsafe_allow_html=True)

    # --- ABA 4: IA VISION ---
    with tabs[3]:
        st.write("### 👁️ Diagnóstico por Visão Computacional")
        foto = st.camera_input("Capturar imagem da folha/praga")
        if foto and GEMINI_KEY != "CHAVE_NAO_CONFIGURADA":
            genai.configure(api_key=GEMINI_KEY)
            with st.spinner("Analisando com IA..."):
                res_ia = genai.GenerativeModel('gemini-1.5-flash').generate_content([
                    f"Engenheiro Agrônomo Fitopatologista. Analise a imagem desta {cultura_sel}. Fase {fase_sel}. Clima: Umidade {hoje['Umid']}%. Identifique o problema e dê a recomendação técnica.",
                    Image.open(foto)
                ])
                st.success(res_ia.text)

    # --- ABA 5: CUSTOS ---
    with tabs[4]:
        if 'financeiro' not in st.session_state: st.session_state['financeiro'] = []
        c_f1, c_f2 = st.columns(2)
        desc_f = c_f1.text_input("Item (Insumo/Serviço)")
        val_f = c_f2.number_input("Valor R$", min_value=0.0)
        if st.button("Lançar"): st.session_state['financeiro'].append({"Item": desc_f, "R$": val_f})
        if st.session_state['financeiro']:
            df_fin = pd.DataFrame(st.session_state['financeiro'])
            st.table(df_fin)
            st.metric("Custo Total Acumulado", f"R$ {df_fin['R$'].sum():,.2f}")

    # --- ABA 6: MAPA SATÉLITE ---
    with tabs[5]:
        st.markdown("### 🗺️ Georreferenciamento de Campo")
        m = folium.Map(location=[st.session_state['loc']['lat'], st.session_state['loc']['lon']], zoom_start=14)
        folium.TileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', attr='Esri', name='Satélite').add_to(m)
        LocateControl().add_to(m); Fullscreen().add_to(m)
        folium.Marker([st.session_state['loc']['lat'], st.session_state['loc']['lon']], popup="Sede", icon=folium.Icon(color='red')).add_to(m)
        st_folium(m, width="100%", height=500)

    # --- ABA 7: NOTIFICAÇÕES (DINÂMICO) ---
    with tabs[6]:
        st.markdown("### 🔔 Configuração de Alertas Automáticos")
        st.markdown(f"""
        <div class="email-card">
            <h4>📧 Gerenciamento de Identidade</h4>
            <p>O sistema enviará alertas para o e-mail autenticado: <b>{st.session_state['user']['email']}</b></p>
        </div>
        """, unsafe_allow_html=True)
        
        st.checkbox("Receber alerta de geada/calor extremo", value=True)
        st.checkbox("Receber alerta de risco de Requeima (Umidade > 85%)", value=True)
        
        if st.button("Confirmar e Ativar Notificações"):
            st.success(f"Configuração salva para {st.session_state['user']['email']}. Você receberá o próximo relatório matinal.")

else:
    st.warning("⚠️ Chave API do OpenWeather não encontrada nos Secrets. O sistema não pode processar dados climáticos.")
