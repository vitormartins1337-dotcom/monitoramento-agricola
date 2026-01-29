import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
import math
from datetime import datetime, date

# --- 1. CONFIGURAÇÃO VISUAL PREMIUM (COM BACKGROUND) ---
st.set_page_config(
    page_title="Agro-Intel Premium",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- SELETOR DE TEMA VISUAL (NOVO!) ---
# Definimos os temas e as URLs das imagens de fundo
TEMAS = {
    "Tecnologia (Drone)": "https://images.unsplash.com/photo-1625246333195-78d9c38ad449?q=80&w=1740&auto=format&fit=crop",
    "Chapada (Montanhas)": "https://images.unsplash.com/photo-1500382017468-9049fed747ef?q=80&w=1932&auto=format&fit=crop",
    "Futuro (Dados)": "https://images.unsplash.com/photo-1551288049-bebda4e38f71?q=80&w=2070&auto=format&fit=crop"
}

# Menu lateral para escolha (antes do resto do código para carregar o CSS certo)
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3058/3058995.png", width=60)
    st.header("🎛️ Configuração")
    tema_selecionado = st.selectbox("🎨 Tema Visual de Fundo:", list(TEMAS.keys()))
    url_fundo = TEMAS[tema_selecionado]

# CSS DINÂMICO COM BACKGROUND
st.markdown(f"""
<style>
    /* APLICANDO A IMAGEM DE FUNDO COM EFEITO VIDRO */
    .stApp {{
        background-image: linear-gradient(rgba(255,255,255,0.92), rgba(255,255,255,0.92)), url("{url_fundo}");
        background-attachment: fixed;
        background-size: cover;
    }}

    /* AJUSTE DOS CONTAINERS PARA FICAREM MAIS ELEVADOS */
    .main {{ background-color: transparent; }}
    div[data-testid="metric-container"] {{ background-color: rgba(255, 255, 255, 0.95); border-left: 5px solid #1e3a8a; box-shadow: 0 4px 6px rgba(0,0,0,0.1); backdrop-filter: blur(5px); }}
    
    /* CAIXAS DE CONTEÚDO */
    .header-box {{ background: linear-gradient(135deg, #1e3a8a 0%, #0d47a1 100%); color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 4px 8px rgba(0,0,0,0.2); }}
    .tech-card {{ background-color: rgba(255, 255, 255, 0.98); padding: 20px; border-radius: 8px; border: 1px solid #e5e7eb; margin-bottom: 15px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }}
    
    /* OUTROS ESTILOS */
    .tech-title {{ color: #1e3a8a; font-weight: bold; font-size: 1.1em; border-bottom: 2px solid #e5e7eb; padding-bottom: 10px; margin-bottom: 10px; }}
    .alert-high {{ background-color: #fee2e2; border-left: 5px solid #dc2626; padding: 15px; border-radius: 4px; color: #991b1b; }}
    .alert-low {{ background-color: #dcfce7; border-left: 5px solid #16a34a; padding: 15px; border-radius: 4px; color: #166534; }}
    h3 {{ margin-top: 0; }}
    .stTabs [data-baseweb="tab-list"] {{ gap: 5px; background-color: rgba(255,255,255,0.5); padding: 5px; border-radius: 10px; }}
    .stTabs [data-baseweb="tab"] {{ height: 45px; background-color: rgba(255,255,255,0.8); border: none; border-radius: 5px; }}
    .stTabs [aria-selected="true"] {{ background-color: #1e3a8a; color: white; font-weight: bold; }}
</style>
""", unsafe_allow_html=True)

# --- 2. BANCO DE DADOS AGRONÔMICO ---
BANCO_MASTER = {
    "Batata (Solanum tuberosum)": {
        "t_base": 7,
        "vars": {
            "Orchestra": {"kc": 1.15, "info": "Exigente em K. Acabamento de pele visual."},
            "Cupido": {"kc": 1.10, "info": "Ciclo Curto. Sensibilidade extrema a Requeima."},
            "Camila": {"kc": 1.15, "info": "Referência de mercado. Cuidado com Sarna."},
            "Atlantic": {"kc": 1.15, "info": "Indústria (Chips). Evitar estresse hídrico."}
        },
        "fases": {
            "Emergência/Estabelecimento": {"desc": "Desenvolvimento inicial.", "fisiologia": "Dreno de reservas da mãe. Raiz incipiente.", "manejo": "Monitorar Rizoctonia e Minadora.", "quimica": "Solo: Azoxistrobina. Foliar: Ciromazina."},
            "Estolonização (Vegetativo)": {"desc": "Crescimento de hastes.", "fisiologia": "Alta demanda de N para IAF.", "manejo": "Realizar a Amontoa.", "quimica": "Preventivo: Clorotalonil ou Mancozebe."},
            "Início de Tuberização (Gancho)": {"desc": "Fase crítica.", "fisiologia": "Inversão hormonal (Giberelina cai). Estresse causa aborto.", "manejo": "Irrigação frequente. Controle Requeima.", "quimica": "Curativo: Metalaxil-M, Dimetomorfe."},
            "Enchimento de Tubérculos": {"desc": "Translocação.", "fisiologia": "Dreno forte de K e Mg.", "manejo": "Monitorar Mosca Branca/Traça.", "quimica": "Traça: Clorantraniliprole. Mosca: Espirotesifeno."},
            "Maturação/Senescência": {"desc": "Formação de pele.", "fisiologia": "Suberização.", "manejo": "Dessecação.", "quimica": "Diquat."}
        }
    },
    "Café (Coffea arabica)": {
        "t_base": 10,
        "vars": {"Catuaí": {"kc": 1.1, "info": "Padrão. Susceptível a ferrugem."}, "Arara": {"kc": 1.2, "info": "Resistente a ferrugem."}},
        "fases": {
            "Dormência/Poda": {"desc": "Período seco.", "fisiologia": "Indução floral latente.", "manejo": "Poda.", "quimica": "Cobre."},
            "Florada Principal": {"desc": "Antese.", "fisiologia": "Demanda de Boro.", "manejo": "Proteger polinizadores.", "quimica": "Foliar: Ca+B+Zn."},
            "Chumbinho (Expansão)": {"desc": "Fruto pequeno.", "fisiologia": "Divisão celular. Água crítica.", "manejo": "Controle Cercospora/Ferrugem.", "quimica": "Priori Xtra."},
            "Granação (Enchimento)": {"desc": "Solidificação.", "fisiologia": "Pico de K e N.", "manejo": "Monitorar Broca.", "quimica": "Ciantraniliprole."}
        }
    },
    "Morango": {
        "t_base": 7,
        "vars": {"San Andreas": {"kc": 0.85, "info": "Dia Neutro."}, "Albion": {"kc": 0.85, "info": "Qualidade."}},
        "fases": {
            "Plantio/Enraizamento": {"desc": "Estabelecimento.", "fisiologia": "Emissão de raízes.", "manejo": "Imersão em fungicida.", "quimica": "Fosfito K."},
            "Desenvolvimento de Coroa": {"desc": "Vegetativo.", "fisiologia": "Reservas na coroa.", "manejo": "Retirada estolões.", "quimica": "Oídio: Enxofre. Ácaro: Abamectina."},
            "Florada/Frutificação": {"desc": "Produção.", "fisiologia": "Alta demanda K/Ca.", "manejo": "Fertirrigação diária.", "quimica": "Botrytis: Ciprodinil."}
        }
    },
     "Mirtilo": {
        "t_base": 7,
        "vars": {"Emerald": {"kc": 0.95, "info": "pH 4.5."}, "Biloxi": {"kc": 0.90, "info": "Poda central."}},
        "fases": {
            "Brotação": {"desc": "Fluxo de seiva.", "fisiologia": "Reservas de raiz.", "manejo": "Controle Cochonilha.", "quimica": "Óleo Mineral."},
            "Florada": {"desc": "Abertura.", "fisiologia": "Polinização define tamanho.", "manejo": "Abelhas (Bombus).", "quimica": "Fludioxonil (Noite)."},
            "Crescimento Fruto": {"desc": "Fase verde.", "fisiologia": "Evitar Nitrato.", "manejo": "Monitorar Antracnose.", "quimica": "Azoxistrobina."}
        }
    }
}

# --- 3. SISTEMA DE PERSISTÊNCIA ---
def get_credentials():
    params = st.query_params
    return params.get("w_key", None), params.get("g_key", None)

# --- 4. CÁLCULOS CIENTÍFICOS ---
def calc_agro(temp, umid):
    es = 0.61078 * math.exp((17.27 * temp) / (temp + 237.3))
    ea = es * (umid / 100)
    vpd = round(es - ea, 2)
    tw = temp * math.atan(0.151977 * (umid + 8.313659)**0.5) + math.atan(temp + umid) - math.atan(umid - 1.676331) + 0.00391838 * (umid)**1.5 * math.atan(0.023101 * umid) - 4.686035
    dt = round(temp - tw, 1)
    return dt, vpd

def get_forecast_detailed(api_key, lat, lon, kc, t_base):
    try:
        url = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={api_key}&units=metric&lang=pt_br"
        r = requests.get(url).json()
        dados = []
        for i in range(0, 40, 8):
            item = r['list'][i]
            t_media = item['main']['temp']
            gda_dia = max(0, t_media - t_base)
            dt, vpd = calc_agro(t_media, item['main']['humidity'])
            chuva = sum([r['list'][i+j].get('rain', {}).get('3h', 0) for j in range(8) if i+j < len(r['list'])])
            et0 = 0.0023 * (t_media + 17.8) * (t_media ** 0.5) * 0.408
            dados.append({
                'Data': datetime.fromtimestamp(item['dt']).strftime('%d/%m'),
                'Temp': t_media, 'GDA': gda_dia, 'Chuva': round(chuva, 1),
                'VPD': vpd, 'Delta T': dt, 'Umid': item['main']['humidity'],
                'ETc': round(et0 * kc, 2)
            })
        return pd.DataFrame(dados)
    except: return pd.DataFrame()

# --- 5. SIDEBAR ---
url_w, url_g = get_credentials()
with st.sidebar:
    with st.expander("🔑 Acesso (Salvar Link)", expanded=not url_w):
        val_w = st.text_input("OpenWeather Key", value=url_w if url_w else "", type="password")
        val_g = st.text_input("Gemini AI Key", value=url_g if url_g else "", type="password")
        if st.button("🔗 Gerar Link"):
            st.query_params["w_key"] = val_w
            st.query_params["g_key"] = val_g
            st.rerun()
    st.divider()
    cultura_sel = st.selectbox("Cultura:", list(BANCO_MASTER.keys()))
    var_sel = st.selectbox("Cultivar:", list(BANCO_MASTER[cultura_sel]['vars'].keys()))
    fases_crop = BANCO_MASTER[cultura_sel]['fases']
    fase_sel = st.selectbox("Estágio Atual:", list(fases_crop.keys()))
    if 'd_plantio' not in st.session_state: st.session_state['d_plantio'] = date(2025, 11, 25)
    d_plantio = st.date_input("Data Início:", st.session_state['d_plantio'])
    info_v = BANCO_MASTER[cultura_sel]['vars'][var_sel]
    st.info(f"🧬 **{var_sel}** | Dias: {(date.today()-d_plantio).days}")

# --- 6. DASHBOARD ---
st.title("🛰️ Agro-Intel Premium")
if val_w:
    lat, lon = "-13.414", "-41.285"
    t_base_crop = BANCO_MASTER[cultura_sel]['t_base']
    df = get_forecast_detailed(val_w, lat, lon, info_v['kc'], t_base_crop)
    if not df.empty:
        hoje = df.iloc[0]
        gda_acum = df['GDA'].sum()
        st.markdown(f"""<div class="header-box"><h2>{cultura_sel} - {var_sel}</h2><p>Fase: <b>{fase_sel}</b> | GDA (7d): <b>{gda_acum:.0f}</b></p></div>""", unsafe_allow_html=True)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("🌡️ Temp", f"{hoje['Temp']:.1f}°C", f"Umid: {hoje['Umid']}%")
        c2.metric("💧 VPD", f"{hoje['VPD']} kPa", "Ideal" if 0.4 <= hoje['VPD'] <= 1.3 else "Alerta")
        c3.metric("💦 ETc", f"{hoje['ETc']} mm", f"Kc: {info_v['kc']}")
        c4.metric("🛡️ Delta T", f"{hoje['Delta T']}°C", "Ok" if 2 <= hoje['Delta T'] <= 8 else "Ruim")
        
        tabs = st.tabs(["🎓 Consultoria", "📊 Clima", "👁️ IA Vision", "💰 Gestão"])
        
        with tabs[0]:
            dados = fases_crop[fase_sel]
            risco = "Baixo"; msg = "Clima favorável. Use **Protetores**."; estilo = "alert-low"
            if hoje['Umid'] > 85 or hoje['Chuva'] > 2: risco="ALTO"; msg="🚨 **ALERTA UMIDADE:** Use **SISTÊMICOS**."; estilo="alert-high"
            c_esq, c_dir = st.columns([1, 1])
            with c_esq:
                st.markdown(f"""<div class="tech-card"><div class="tech-title">🧬 Fisiologia</div><p><b>O que ocorre:</b> {dados['desc']}</p><p><b>Internamente:</b> {dados['fisiologia']}</p></div>""", unsafe_allow_html=True)
                st.markdown(f"""<div class="{estilo}"><strong>☁️ Matriz Climática Hoje</strong><br>{msg}</div>""", unsafe_allow_html=True)
            with c_dir:
                st.markdown(f"""<div class="tech-card"><div class="tech-title">🛠️ Plano de Ação</div><p><b>Manejo:</b> {dados['manejo']}</p><hr><div class="tech-title">🧪 Prescrição Química</div><p>{dados['quimica']}</p></div>""", unsafe_allow_html=True)
        
        with tabs[1]:
            fig = go.Figure()
            fig.add_trace(go.Bar(x=df['Data'], y=df['Chuva'], name='Chuva', marker_color='#3b82f6'))
            fig.add_trace(go.Scatter(x=df['Data'], y=df['ETc'], name='ETc', line=dict(color='#ef4444', width=2)))
            st.plotly_chart(fig, use_container_width=True)
        
        with tabs[2]:
            img = st.camera_input("Foto")
            if img and val_g:
                st.image(img, width=200)
                genai.configure(api_key=val_g)
                with st.spinner("Analisando..."):
                    st.success(genai.GenerativeModel('gemini-1.5-flash').generate_content([f"Agrônomo. Analise imagem. Cultura: {cultura_sel}. Fase: {fase_sel}. Umidade: {hoje['Umid']}%. Diagnostico e Tratamento.", Image.open(img)]).text)
        
        with tabs[3]:
            if 'custos' not in st.session_state: st.session_state['custos'] = []
            c_f1, c_f2 = st.columns(2)
            i = c_f1.text_input("Item"); v = c_f2.number_input("R$")
            if c_f2.button("Lançar"): st.session_state['custos'].append({"Item": i, "Valor": v})
            if st.session_state['custos']: st.dataframe(pd.DataFrame(st.session_state['custos'])); st.metric("Total", f"R$ {pd.DataFrame(st.session_state['custos'])['Valor'].sum()}")
else: st.warning("⚠️ Configure suas chaves no menu lateral e clique em 'Gerar Link'.")
