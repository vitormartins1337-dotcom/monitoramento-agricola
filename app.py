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

# --- 1. CONFIGURAÇÃO VISUAL ENTERPRISE ---
st.set_page_config(page_title="Agro-Intel Enterprise", page_icon="🌱", layout="wide")

st.markdown("""
<style>
    .main { background-color: #f0f2f6; }
    .header-main { background: linear-gradient(90deg, #166534 0%, #15803d 100%); padding: 30px; border-radius: 15px; color: white; margin-bottom: 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }
    .control-panel { background-color: white; padding: 25px; border-radius: 15px; border: 1px solid #e5e7eb; box-shadow: 0 2px 4px rgba(0,0,0,0.05); margin-bottom: 20px; }
    .metric-box { background: white; padding: 20px; border-radius: 10px; border-left: 5px solid #166534; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }
    .pest-card { background: white; border: 1px solid #fee2e2; border-left: 5px solid #dc2626; padding: 20px; border-radius: 10px; margin-bottom: 15px; }
    .pest-title { color: #991b1b; font-weight: bold; font-size: 1.2em; }
    .chem-tag { background-color: #fef2f2; color: #991b1b; padding: 2px 8px; border-radius: 4px; font-size: 0.9em; border: 1px solid #fecaca; }
    .bio-tag { background-color: #f0fdf4; color: #166534; padding: 2px 8px; border-radius: 4px; font-size: 0.9em; border: 1px solid #bbf7d0; }
    .info-text { font-size: 0.9em; color: #4b5563; margin-top: 5px; }
</style>
""", unsafe_allow_html=True)

# --- 2. BANCO DE DADOS AGRONÔMICO (ESTENDIDO E PROFISSIONAL) ---
BANCO_MASTER = {
    "Batata (Solanum tuberosum)": {
        "t_base": 7,
        "desc_cultura": "Cultura exigente em fotoperíodo e termoperíodo. Temperaturas noturnas acima de 20°C inibem a tuberização.",
        "vars": {
            "Orchestra": {"kc": 1.15, "gda_meta": 1600, "info": "Alta exigência de K. Ciclo médio. Resistente a vírus Y."},
            "Cupido": {"kc": 1.10, "gda_meta": 1400, "info": "Precoce. Baixa dormência. Sensível a Metribuzin."},
            "Camila": {"kc": 1.15, "gda_meta": 1550, "info": "Pele lavada. Exigente em Boro e Cálcio."},
            "Atlantic": {"kc": 1.15, "gda_meta": 1650, "info": "Matéria seca alta (Chips). Monitorar nível de Nitrogênio na maturação."}
        },
        "fases": {
            "Emergência (0-20d)": {"desc": "Estabelecimento.", "manejo": "Solo friável.", "quim": "Azoxistrobina.", "bio": "Trichoderma asperellum."},
            "Vegetativo (20-35d)": {"desc": "Expansão IAF.", "manejo": "Amontoa.", "quim": "Mancozeb.", "bio": "Bacillus subtilis."},
            "Tuberização (35-50d)": {"desc": "Ganchos.", "manejo": "Água crítica.", "quim": "Mandipropamida.", "bio": "Aminoácidos."},
            "Enchimento (50-80d)": {"desc": "Expansão.", "manejo": "Sanidade total.", "quim": "Ciantraniliprole.", "bio": "Potássio orgânico."},
            "Maturação (80d+)": {"desc": "Cura.", "manejo": "Dessecação.", "quim": "Diquat.", "bio": "Silicato."}
        },
        "pragas_doencas": {
            "Requeima (Phytophthora infestans)": {
                "sintomas": "Manchas oleosas nas folhas que evoluem para necrose. Micélio branco na face inferior em alta umidade.",
                "condicao": "Frio (12-20°C) + Umidade > 90%.",
                "quimico": "Metalaxil-M + Mancozeb, Mandipropamida (Revus), Fluazinam, Cimoxanil.",
                "biologico": "Bacillus subtilis (Serenade) preventivo, Extrato de Melaleuca."
            },
            "Pinta Preta (Alternaria solani)": {
                "sintomas": "Manchas necróticas em anéis concêntricos (alvo).",
                "condicao": "Alternância de umidade e calor (>25°C).",
                "quimico": "Tebuconazol, Azoxistrobina, Boscalida (Cantus).",
                "biologico": "Bacillus amyloliquefaciens."
            },
            "Vaquinha (Diabrotica speciosa)": {
                "sintomas": "Folhas perfuradas (adulto) e danos nos tubérculos (larva alfinete).",
                "condicao": "Todo o ciclo.",
                "quimico": "Lambda-Cialotrina, Acetamiprido, Tiametoxam.",
                "biologico": "Beauveria bassiana, Metarhizium anisopliae."
            },
            "Traça (Phthorimaea operculella)": {
                "sintomas": "Minas nas folhas e galerias nos tubérculos.",
                "condicao": "Clima seco e quente.",
                "quimico": "Clorfenapir, Indoxacarbe, Espinosade.",
                "biologico": "Bacillus thuringiensis kurstaki, Trichogramma pretiosum."
            }
        }
    },
    "Tomate (Solanum lycopersicum)": {
        "t_base": 10,
        "desc_cultura": "Hortaliça de fruto climatério. VPD ideal entre 0.8 e 1.2 kPa para evitar fundo preto.",
        "vars": {
            "Italiano": {"kc": 1.2, "gda_meta": 1600, "info": "Fruto alongado. Exigente em Cálcio."},
            "Grape": {"kc": 1.1, "gda_meta": 1450, "info": "Alto Brix. Sensível a rachaduras."}
        },
        "fases": {
            "Vegetativo": {"desc": "Crescimento.", "manejo": "Desbrota.", "quim": "Imidacloprido.", "bio": "Bokashi."},
            "Frutificação": {"desc": "Engorda.", "manejo": "Cálcio foliar.", "quim": "Cobre.", "bio": "Algas."}
        },
        "pragas_doencas": {
            "Traça do Tomateiro (Tuta absoluta)": {
                "sintomas": "Minas parenquimais nas folhas e frutos.",
                "condicao": "Alta temperatura.",
                "quimico": "Clorantraniliprole, Teflubenzurom, Abamectina.",
                "biologico": "Trichogramma pretiosum, Bacillus thuringiensis."
            },
            "Vira-Cabeça (Tospovirus)": {
                "sintomas": "Bronqueamento e necrose do topo. Transmitido por Tripes.",
                "condicao": "Presença do vetor (Tripes).",
                "quimico": "Espinetoram (Delegate), Formetanato (Controle do vetor).",
                "biologico": "Beauveria bassiana, Amblyseius (predador)."
            }
        }
    },
    "Café (Coffea arabica)": {
        "t_base": 10,
        "desc_cultura": "Perene. Indução floral depende de déficit hídrico seguido de chuva.",
        "vars": {
            "Catuaí": {"kc": 1.1, "gda_meta": 3000, "info": "Produtivo. Exige controle de ferrugem."},
            "Arara": {"kc": 1.2, "gda_meta": 2900, "info": "Resistente/Imune a ferrugem."}
        },
        "fases": {
            "Florada": {"desc": "Antese.", "manejo": "Polinização.", "quim": "Cálcio+Boro.", "bio": "Algas."},
            "Chumbinho": {"desc": "Expansão.", "manejo": "Adubação N.", "quim": "Fungicidas.", "bio": "Aminoácidos."}
        },
        "pragas_doencas": {
            "Ferrugem (Hemileia vastatrix)": {
                "sintomas": "Pústulas alaranjadas na face inferior das folhas.",
                "condicao": "Umidade alta e sombreamento.",
                "quimico": "Ciproconazol, Epoxiconazol, Piraclostrobina.",
                "biologico": "Bacillus subtilis (preventivo)."
            },
            "Broca do Café (Hypothenemus hampei)": {
                "sintomas": "Furos na região da coroa do fruto.",
                "condicao": "Frutos em trânsito/maturação.",
                "quimico": "Ciantraniliprole, Clorantraniliprole.",
                "biologico": "Beauveria bassiana (Aplicação em dias úmidos)."
            }
        }
    },
    "Mirtilo (Vaccinium spp.)": {
        "t_base": 7,
        "desc_cultura": "Exige solo ácido (pH 4.5-5.5) e rico em matéria orgânica. Sensível a nitratos.",
        "vars": {
            "Emerald": {"kc": 0.95, "gda_meta": 1800, "info": "Baixo frio. Vigorosa."},
            "Biloxi": {"kc": 0.90, "gda_meta": 1900, "info": "Rústica. Ereta."}
        },
        "fases": {
            "Florada": {"desc": "Polinização.", "manejo": "Abelhas.", "quim": "Sem inseticidas.", "bio": "Boro."},
            "Crescimento": {"desc": "Expansão.", "manejo": "pH água.", "quim": "Enxofre.", "bio": "Ácidos Húmicos."}
        },
        "pragas_doencas": {
            "Antracnose (Colletotrichum)": {
                "sintomas": "Manchas deprimidas nos frutos (maduros) e folhas.",
                "condicao": "Calor e chuva.",
                "quimico": "Azoxistrobina, Difenoconazol, Captana.",
                "biologico": "Bacillus amyloliquefaciens."
            },
            "Botrytis (Mofo Cinzento)": {
                "sintomas": "Fungo cinza nas flores e frutos.",
                "condicao": "Alta umidade na florada.",
                "quimico": "Fludioxonil + Ciprodinil (Switch), Iprodiona.",
                "biologico": "Clonostachys rosea, Ulocladium oudemansii."
            }
        }
    }
}

# --- 3. MOTORES DE INTEGRAÇÃO (API) ---
def get_coords(city, key):
    try:
        url = f"http://api.openweathermap.org/geo/1.0/direct?q={city}&limit=1&appid={key}"
        r = requests.get(url).json()
        if r: return r[0]['lat'], r[0]['lon']
    except: return None, None

def get_forecast_full(lat, lon, key, t_base, kc):
    try:
        url = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={key}&units=metric&lang=pt_br"
        r = requests.get(url).json()
        dados = []
        if 'list' in r:
            for item in r['list']:
                t = item['main']['temp']
                u = item['main']['humidity']
                
                # Cálculos Agronômicos Precisos
                es = 0.61078 * math.exp((17.27 * t) / (t + 237.3))
                ea = es * (u / 100)
                vpd = max(0, round(es - ea, 2))
                
                # GDA (Graus-Dia) - Método da média simples por período
                gda_step = max(0, (t - t_base) / 8) # Dividido por 8 pois são blocos de 3h no dia
                
                # ETc (Penman-Monteith Simplificado Hargreaves)
                et0 = 0.0023 * (t + 17.8) * (t ** 0.5) * 0.408
                
                dados.append({
                    'Data': datetime.fromtimestamp(item['dt']),
                    'Temp': t,
                    'Umid': u,
                    'Chuva': round(item.get('rain', {}).get('3h', 0), 1),
                    'VPD': vpd,
                    'GDA': gda_step,
                    'ETc': round(et0 * kc, 2),
                    'Desc': item['weather'][0]['description'].title()
                })
            return pd.DataFrame(dados)
    except: return pd.DataFrame()

def get_radar_vizinhanca(lat, lon, key):
    # Monitoramento Cruzado (N, S, L, O) - 15km (~0.13 graus)
    pontos = {
        "Norte (15km)": (lat + 0.13, lon),
        "Sul (15km)": (lat - 0.13, lon),
        "Leste (15km)": (lat, lon + 0.13),
        "Oeste (15km)": (lat, lon - 0.13)
    }
    res = []
    for direcao, coords in pontos.items():
        try:
            r = requests.get(f"https://api.openweathermap.org/data/2.5/weather?lat={coords[0]}&lon={coords[1]}&appid={key}&units=metric").json()
            res.append({
                "Local": direcao,
                "Temp": r['main']['temp'],
                "Umid": r['main']['humidity'],
                "Chuva": "SIM" if "rain" in r else "Não",
                "Clima": r['weather'][0]['main']
            })
        except: pass
    return pd.DataFrame(res)

# --- 4. SIDEBAR (APENAS LOGIN/API) ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/9131/9131546.png", width=80)
    st.title("Acesso Seguro")
    st.info("Insira suas chaves de API para desbloquear a inteligência do sistema.")
    
    api_w = st.secrets.get("OPENWEATHER_KEY", st.text_input("OpenWeather Key:", type="password"))
    api_g = st.secrets.get("GEMINI_KEY", st.text_input("Gemini AI Key:", type="password"))
    
    st.divider()
    st.caption("Agro-Intel System v40.0")

# --- 5. PAINEL DE CONTROLE PRINCIPAL (NOVO LAYOUT) ---
st.markdown("""
<div class="header-main">
    <h1>🛰️ Agro-Intel Enterprise: Sistema de Suporte à Decisão</h1>
    <p>Monitoramento Fisiológico e Climático em Tempo Real</p>
</div>
""", unsafe_allow_html=True)

# Container de Controles (Fora da Sidebar)
with st.container():
    st.markdown("### ⚙️ Parâmetros da Propriedade")
    col_geo, col_crop, col_date = st.columns([1.5, 1.5, 1])
    
    # Inicialização de Estado
    if 'lat' not in st.session_state: st.session_state.lat = -13.2000
    if 'lon' not in st.session_state: st.session_state.lon = -41.4000

    with col_geo:
        st.markdown("**📍 Localização**")
        tab_c, tab_g = st.tabs(["Por Cidade", "Coordenadas"])
        with tab_c:
            cidade_busca = st.text_input("Buscar Município:", placeholder="Ex: Ibicoara, BA")
            if st.button("📍 Localizar") and api_w:
                nlat, nlon = get_coords(cidade_busca, api_w)
                if nlat:
                    st.session_state.lat, st.session_state.lon = nlat, nlon
                    st.success("Coordenadas Atualizadas!")
                    st.rerun()
        with tab_g:
            c1, c2 = st.columns(2)
            st.session_state.lat = c1.number_input("Lat:", value=st.session_state.lat, format="%.4f")
            st.session_state.lon = c2.number_input("Lon:", value=st.session_state.lon, format="%.4f")

    with col_crop:
        st.markdown("**🌱 Cultura & Genética**")
        cultura_sel = st.selectbox("Selecione a Cultura:", list(BANCO_MASTER.keys()))
        var_sel = st.selectbox("Variedade/Cultivar:", list(BANCO_MASTER[cultura_sel]['vars'].keys()))
        fase_sel = st.selectbox("Estágio Fenológico:", list(BANCO_MASTER[cultura_sel]['fases'].keys()))

    with col_date:
        st.markdown("**📅 Calendário**")
        d_plantio = st.date_input("Data de Início:", date(2025, 12, 1))

# --- 6. PROCESSAMENTO E EXIBIÇÃO ---
if api_w:
    # Carregamento de Dados
    crop_db = BANCO_MASTER[cultura_sel]
    var_db = crop_db['vars'][var_sel]
    fase_db = crop_db['fases'][fase_sel]
    pragas_db = crop_db.get('pragas_doencas', {})
    
    # Previsão Climática
    df = get_forecast_full(st.session_state.lat, st.session_state.lon, api_w, crop_db['t_base'], var_db['kc'])
    
    if not df.empty:
        hoje = df.iloc[0]
        dias_ciclo = (date.today() - d_plantio).days
        gda_acum = dias_ciclo * (df['GDA'].sum() / 5 * 8) # Projeção GDA
        
        # --- MÉTRICAS DE TOPO (KPIs) COM EXPLICAÇÕES ---
        st.markdown("---")
        k1, k2, k3, k4 = st.columns(4)
        
        with k1:
            st.metric("🌡️ Temperatura", f"{hoje['Temp']:.1f}°C")
            st.markdown(f"<div class='info-text'>Base de crescimento: {crop_db['t_base']}°C</div>", unsafe_allow_html=True)
            
        with k2:
            st.metric("💧 VPD (Déficit Pressão)", f"{hoje['VPD']} kPa")
            status_vpd = "Ideal" if 0.4 <= hoje['VPD'] <= 1.2 else "Estresse"
            st.markdown(f"<div class='info-text'>Status: <b>{status_vpd}</b>. Indica a capacidade de transpiração da planta.</div>", unsafe_allow_html=True)
            
        with k3:
            st.metric("💦 ETc (Demanda)", f"{hoje['ETc']} mm/dia")
            st.markdown(f"<div class='info-text'>Kc da fase: {var_db['kc']}. Volume de água a repor via irrigação.</div>", unsafe_allow_html=True)
            
        with k4:
            st.metric("🔥 GDA Acumulado", f"{gda_acum:.0f}", f"Meta: {var_db['gda_meta']}")
            st.markdown(f"<div class='info-text'>Relógio biológico da planta para prever colheita.</div>", unsafe_allow_html=True)

        # --- ABAS DE ANÁLISE ---
        tabs = st.tabs([
            "🎓 Consultoria & Manejo", 
            "🦠 Biblioteca Fitossanitária (Pragas)", 
            "📊 Clima Detalhado", 
            "📡 Radar Vizinho", 
            "👁️ Diagnóstico IA", 
            "🚚 Logística"
        ])

        # 1. CONSULTORIA
        with tabs[0]:
            c_left, c_right = st.columns([1, 1])
            with c_left:
                st.markdown(f"### 🧬 Análise Fisiológica: {fase_sel}")
                st.info(f"**Descrição da Variedade:** {var_db['info']}")
                st.markdown(f"""
                <div class="tech-card">
                    <h4>O que acontece na planta agora?</h4>
                    <p>{fase_db['fisio']}</p>
                    <hr>
                    <p><b>Risco Climático Atual:</b></p>
                """, unsafe_allow_html=True)
                
                

                # Lógica de Risco
                if hoje['Umid'] > 85:
                    st.error("🚨 ALERTA ALTO: Umidade > 85%. Favorável a fungos e bactérias. Iniciar preventivos.")
                elif hoje['Temp'] > 30 and "Batata" in cultura_sel:
                    st.warning("⚠️ ALERTA TÉRMICO: Temp > 30°C. Parada de crescimento (Tuberização inibida).")
                else:
                    st.success("✅ Condições Climáticas Favoráveis.")
                st.markdown("</div>", unsafe_allow_html=True)

            with c_right:
                st.markdown("### 🛠️ Prescrição de Manejo")
                st.markdown(f"""
                <div class="tech-card">
                    <h4>🚜 Ações Culturais</h4>
                    <p>{fase_db['manejo']}</p>
                </div>
                <div class="chem-card">
                    <h4>🧪 Químicos Recomendados</h4>
                    <p>{fase_db['quim']}</p>
                </div>
                <div class="tech-card" style="border-left: 5px solid #ff9800;">
                    <h4>🌿 Biológicos & Nutrição</h4>
                    <p>{fase_db['bio']}</p>
                </div>
                """, unsafe_allow_html=True)

        # 2. BIBLIOTECA FITOSSANITÁRIA (NOVA ABA)
        with tabs[1]:
            st.markdown(f"### 🦠 Pragas e Doenças Principais: {cultura_sel}")
            st.markdown("Guia rápido de identificação e controle para a cultura selecionada.")
            
            if pragas_db:
                for praga, info in pragas_db.items():
                    with st.container():
                        st.markdown(f"""
                        <div class="pest-card">
                            <div class="pest-title">{praga}</div>
                            <p><b>🔍 Sintomas:</b> {info['sintomas']}</p>
                            <p><b>☁️ Condição Favorável:</b> {info['condicao']}</p>
                            <p><span class="chem-tag">QUÍMICO</span> {info['quimico']}</p>
                            <p><span class="bio-tag">BIOLÓGICO</span> {info['biologico']}</p>
                        </div>
                        """, unsafe_allow_html=True)
                    
            else:
                st.info("Selecione uma cultura para ver a biblioteca de pragas.")

        # 3. CLIMA
        with tabs[2]:
            st.markdown("### 🌧️ Previsão de Chuva e Balanço Hídrico")
            fig = go.Figure()
            fig.add_trace(go.Bar(x=df['Data'], y=df['Chuva'], name='Chuva (mm)', marker_color='#2196f3'))
            fig.add_trace(go.Scatter(x=df['Data'], y=df['ETc'], name='Consumo ETc (mm)', line=dict(color='#d32f2f', width=3)))
            fig.update_layout(height=400, template="plotly_white", margin=dict(l=20, r=20, t=40, b=20))
            st.plotly_chart(fig, use_container_width=True)
            
            st.dataframe(df[['Data', 'Temp', 'Umid', 'Chuva', 'VPD', 'GDA', 'Desc']], use_container_width=True)

        # 4. RADAR
        with tabs[3]:
            st.markdown("### 📡 Radar de Vizinhança (15km)")
            st.markdown("Monitoramento dos 4 pontos cardeais para antecipar chuvas localizadas.")
            df_radar = get_radar_vizinhanca(st.session_state.lat, st.session_state.lon, api_w)
            
            if not df_radar.empty:
                cols = st.columns(4)
                for i, row in df_radar.iterrows():
                    bg_color = "#fee2e2" if row['Chuva'] == "SIM" else "#dcfce7"
                    with cols[i]:
                        st.markdown(f"""
                        <div style="background-color:{bg_color}; padding:15px; border-radius:10px; text-align:center; border:1px solid #ddd;">
                            <h3>{row['Local']}</h3>
                            <h2>{row['Temp']:.1f}°C</h2>
                            <p>{row['Clima']}</p>
                            <p><b>Chuva: {row['Chuva']}</b></p>
                        </div>
                        """, unsafe_allow_html=True)

        # 5. IA VISION
        with tabs[4]:
            st.markdown("### 👁️ Diagnóstico Inteligente")
            st.write("Envie uma foto da folha ou fruto para análise instantânea via Gemini Pro.")
            
            if api_g:
                foto = st.camera_input("Escanear Problema")
                if foto:
                    image = Image.open(foto)
                    st.image(image, width=300)
                    with st.spinner("Analisando patógenos e deficiências..."):
                        genai.configure(api_key=api_g)
                        model = genai.GenerativeModel('gemini-1.5-flash')
                        res = model.generate_content([f"Agrônomo Sênior. Analise esta imagem de {cultura_sel} (Var: {var_sel}). Identifique pragas, doenças ou deficiências e recomende tratamento químico e biológico.", image])
                        st.success("Laudo Gerado:")
                        st.write(res.text)
            else:
                st.warning("Chave Gemini não configurada.")

        # 6. LOGÍSTICA
        with tabs[5]:
            st.markdown("### 🚚 Calculadora de Frete")
            c_l1, c_l2 = st.columns(2)
            with c_l1:
                dist = st.number_input("Distância (km):", value=450)
                cons = st.number_input("Consumo (km/L):", value=10.0)
                comb = st.number_input("Preço Diesel/Gasolina:", value=6.20)
                carga = st.slider("Carga Transportada (kg):", 100, 1000, 400)
            
            with c_l2:
                custo = (dist/cons) * comb
                st.metric("Custo Total Viagem", f"R$ {custo:.2f}")
                st.metric("Custo por Kg", f"R$ {custo/carga:.2f}")
                st.progress(min(1.0, carga/800))
                st.caption("Ocupação baseada em veículo utilitário leve (800kg)")

else:
    st.info("👈 Insira sua chave OpenWeather na barra lateral para ativar o sistema.")
