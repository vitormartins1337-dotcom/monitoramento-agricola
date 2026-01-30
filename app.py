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

# --- 1. CONFIGURAÇÃO VISUAL ---
st.set_page_config(page_title="Agro-Intel Enterprise", page_icon="🌱", layout="wide")

st.markdown("""
<style>
    .main { background-color: #f4f6f9; }
    
    /* Cabeçalho Unificado e Rico */
    .header-main { 
        background: linear-gradient(135deg, #1b5e20 0%, #2e7d32 100%); 
        padding: 20px; 
        border-radius: 12px; 
        color: white; 
        margin-bottom: 20px; 
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        display: flex;
        flex-direction: column;
    }
    .header-top { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(255,255,255,0.3); padding-bottom: 10px; margin-bottom: 10px; }
    .header-details { display: flex; gap: 20px; font-size: 0.95em; flex-wrap: wrap; }
    .tag-info { background: rgba(255,255,255,0.2); padding: 5px 10px; border-radius: 5px; font-weight: bold; }
    
    /* Métricas Compactas */
    div[data-testid="stMetric"] {
        background-color: white;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 10px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        text-align: center;
    }
    
    /* Cards Profissionais */
    .tech-card { background: white; padding: 20px; border-radius: 12px; border-left: 5px solid #1565c0; box-shadow: 0 2px 5px rgba(0,0,0,0.05); margin-bottom: 15px; }
    .chem-card { background: white; padding: 20px; border-radius: 12px; border-left: 5px solid #c62828; box-shadow: 0 2px 5px rgba(0,0,0,0.05); margin-bottom: 15px; }
    .bio-card { background: white; padding: 20px; border-radius: 12px; border-left: 5px solid #2e7d32; box-shadow: 0 2px 5px rgba(0,0,0,0.05); margin-bottom: 15px; }
    
    /* Tipografia */
    .pro-title { color: #1b5e20; font-weight: 800; font-size: 1.1em; text-transform: uppercase; margin-bottom: 10px; }
    .active-ingredient { font-weight: bold; color: #d32f2f; }
    .mechanism { font-style: italic; color: #555; font-size: 0.9em; }
</style>
""", unsafe_allow_html=True)

# --- 2. BANCO DE DADOS AGRONÔMICO COMPLETO (TODAS AS FASES) ---
BANCO_MASTER = {
    "Batata (Solanum tuberosum)": {
        "t_base": 7,
        "vars": {
            "Orchestra": {"kc": 1.15, "gda_meta": 1600, "info": "Pele lisa, polpa amarela. Alta exigência de K e Boro."},
            "Cupido": {"kc": 1.10, "gda_meta": 1400, "info": "Ciclo ultra-curto (90 dias). Sensível a Metribuzin."},
            "Camila": {"kc": 1.15, "gda_meta": 1550, "info": "Mercado fresco. Exige manejo preventivo para Sarna."},
            "Atlantic": {"kc": 1.15, "gda_meta": 1650, "info": "Industrial (Chips). Monitorar Matéria Seca."}
        },
        "fases": {
            "Emergência (0-20 dias)": {
                "desc": "Brotamento e Enraizamento.", 
                "fisio": "Dreno de reservas da semente. Baixa taxa fotossintética.", 
                "manejo": "Manter solo friável. Evitar crostas superficiais.", 
                "quim": "**Azoxistrobina (Estrobilurina):** Aplicação no sulco. Inibe respiração mitocondrial de fungos de solo (Rhizoctonia).\n**Tiametoxam:** Neonicotinoide sistêmico para proteção inicial contra vetores de virose.", 
                "bio": "**Trichoderma harzianum:** Colonização da rizosfera para competição por espaço e nutrientes contra patógenos."
            },
            "Vegetativo (20-35 dias)": {
                "desc": "Expansão de Hastes e Folhas.", 
                "fisio": "Alta demanda de Nitrogênio e Magnésio (Clorofila).", 
                "manejo": "Amontoa técnica para cobrir estolões e estimular tuberização.", 
                "quim": "**Mancozeb (Ditiocarbamato):** Multissítio de contato. Essencial para manejo de resistência.\n**Clorotalonil:** Alta aderência, fundamental em períodos chuvosos.", 
                "bio": "**Beauveria bassiana:** Controle de Vaquinha (Diabrotica) via contato com esporos."
            },
            "Tuberização (35-50 dias)": {
                "desc": "Início da Formação (Ganchos).", 
                "fisio": "Inversão hormonal (Giberelina cai, Citocinina sobe). Estresse hídrico causa abortamento.", 
                "manejo": "Irrigação frequente e leve. Monitoramento diário de Requeima.", 
                "quim": "**Mandipropamida (Revus):** Específico para Oomicetos. Alta afinidade com a cera cuticular.\n**Metalaxil-M:** Sistêmico de alta mobilidade (Xilema) para proteção de tecidos novos.", 
                "bio": "**Bacillus subtilis:** Produção de lipopeptídeos que protegem a pele do tubérculo contra Sarna."
            },
            "Enchimento (50-80 dias)": {
                "desc": "Crescimento dos Tubérculos.", 
                "fisio": "Translocação intensa de açúcares. Dreno de Potássio.", 
                "manejo": "Monitorar Mosca Branca e Traça. Manter área foliar sadia.", 
                "quim": "**Ciantraniliprole (Benévia):** Diamida. Paralisa musculatura de insetos sugadores/mastigadores.\n**Espirotesifeno:** Inibe biossíntese de lipídios (ação em ninfas de Mosca Branca).", 
                "bio": "**Extrato de Algas (Ascophyllum):** Fonte de hormônios para manter a planta ativa (efeito stay-green)."
            },
            "Maturação (80+ dias)": {
                "desc": "Senescência e Cura.", 
                "fisio": "Suberização (formação de casca). Conversão de açúcar em amido.", 
                "manejo": "Suspensão da irrigação. Dessecação.", 
                "quim": "**Diquat:** Herbicida de contato (Fotossistema I). Ação rápida para uniformizar colheita.", 
                "bio": "**Suspender Nitrogênio:** O excesso atrasa a pele e reduz qualidade pós-colheita."
            }
        }
    },
    "Tomate (Solanum lycopersicum)": {
        "t_base": 10,
        "vars": {
            "Italiano": {"kc": 1.2, "gda_meta": 1600, "info": "Fruto alongado. Exigente em Cálcio (Fundo Preto)."},
            "Grape": {"kc": 1.1, "gda_meta": 1450, "info": "Alto Brix. Sensível a rachaduras por oscilação hídrica."}
        },
        "fases": {
            "Vegetativo": {"desc": "Crescimento Vertical.", "fisio": "Formação de estrutura.", "manejo": "Desbrota lateral.", "quim": "**Imidacloprido:** Sistêmico no gotejo para controle de vetores (Tripes/Mosca).", "bio": "**Micorrizas:** Aumentar absorção de Fósforo."},
            "Florada": {"desc": "Emissão de Cachos.", "fisio": "Viabilidade do pólen.", "manejo": "Vibração ou Hormônio.", "quim": "**Azoxistrobina:** Preventivo amplo espectro (Oídio/Alternária).", "bio": "**Cálcio + Boro:** Essencial para pegamento."},
            "Frutificação": {"desc": "Engorda.", "fisio": "Dreno de Potássio.", "manejo": "Condução.", "quim": "**Clorfenapir:** Ação de choque e ingestão para Traça (Tuta absoluta).", "bio": "**Bacillus thuringiensis (Bt):** Específico para lagartas."},
            "Colheita": {"desc": "Maturação.", "fisio": "Síntese de Licopeno.", "manejo": "Colheita delicada.", "quim": "**Cobre:** Bactericida preventivo (Xanthomonas).", "bio": "**Óleo de Laranja:** Dessecante natural de insetos de corpo mole."}
        }
    },
    "Café (Coffea arabica)": {
        "t_base": 10,
        "vars": {
            "Catuaí": {"kc": 1.1, "gda_meta": 3000, "info": "Alta qualidade de bebida. Baixa resistência a doenças."},
            "Arara": {"kc": 1.2, "gda_meta": 2900, "info": "Alta carga produtiva. Resistente à Ferrugem."}
        },
        "fases": {
            "Florada": {"desc": "Abertura Floral.", "fisio": "Alta demanda energética.", "manejo": "Não aplicar inseticidas.", "quim": "**Boscalida:** Carboxamida para controle de Phoma em flores.", "bio": "**Extrato de Algas:** Redução de estresse oxidativo."},
            "Chumbinho": {"desc": "Expansão Inicial.", "fisio": "Divisão celular.", "manejo": "Adubação Nitrogenada.", "quim": "**Ciproconazol:** Triazol sistêmico para controle curativo de Ferrugem.", "bio": "**Cobre quelatado:** Fortalecimento da parede celular."},
            "Granação": {"desc": "Enchimento de Grão.", "fisio": "Deposição de matéria seca.", "manejo": "Adubação Potássica.", "quim": "**Ciantraniliprole:** Controle de Broca-do-Café via sistema vascular.", "bio": "**Beauveria bassiana:** Controle biológico da Broca."},
            "Maturação": {"desc": "Cereja.", "fisio": "Acúmulo de açúcares.", "manejo": "Arruação/Limpeza.", "quim": "**Respeitar Carência:** Evitar resíduos no grão.", "bio": "**Potássio Foliar:** Uniformização da maturação."}
        }
    },
    "Mirtilo (Blueberry)": {
        "t_base": 7,
        "vars": {"Emerald": {"kc": 0.95, "gda_meta": 1800, "info": "Vigorosa. Exige pH 4.5 a 5.0."}, "Biloxi": {"kc": 0.90, "gda_meta": 1900, "info": "Ereta. Rústica. Baixo frio."}},
        "fases": {
            "Brotação": {"desc": "Fluxo Vegetativo.", "fisio": "Mobilização de reservas.", "manejo": "Correção de pH.", "quim": "**Óleo Mineral:** Controle físico de Cochonilhas.", "bio": "**Bokashi:** Estímulo à microbiota ácida."},
            "Florada": {"desc": "Polinização.", "fisio": "Sensível a abortamento.", "manejo": "Introdução de Abelhas.", "quim": "**Fludioxonil (Switch):** Padrão ouro para Botrytis (Mofo Cinzento).", "bio": "**Aminoácidos:** Melhora viabilidade do pólen."},
            "Fruto Verde": {"desc": "Crescimento.", "fisio": "Divisão celular.", "manejo": "Nutrição via Ferti.", "quim": "**Difenoconazol:** Triazol para controle de Antracnose e Ferrugem.", "bio": "**Ácidos Fúlvicos:** Melhora absorção de nutrientes."},
            "Maturação": {"desc": "Mudança de Cor.", "fisio": "Síntese de Antocianinas.", "manejo": "Colheita seletiva.", "quim": "**Espinosade:** Controle de Drosófila (SWD) com baixa carência.", "bio": "**Iscas Atrativas:** Monitoramento de moscas."}
        }
    },
    "Framboesa (Rubus idaeus)": {
        "t_base": 7,
        "vars": {"Heritage": {"kc": 1.1, "gda_meta": 1300, "info": "Remontante (Produz na ponta e na lateral). Vermelha."}, "Golden": {"kc": 1.05, "gda_meta": 1250, "info": "Amarela. Sabor mais suave."}},
        "fases": {
            "Brotação": {"desc": "Emissão de Hastes.", "fisio": "Crescimento rápido.", "manejo": "Seleção de hastes.", "quim": "**Abamectina:** Controle de Ácaro Rajado.", "bio": "**Enxofre:** Repelência de ácaros."},
            "Florada": {"desc": "Botões Florais.", "fisio": "Sensível à chuva.", "manejo": "Cobertura (Túnel).", "quim": "**Iprodiona:** Controle preventivo de fungos de flor.", "bio": "**Cálcio Boro:** Firmeza do receptáculo."},
            "Frutificação": {"desc": "Formação de Bagas.", "fisio": "Fruto agregado.", "manejo": "Colheita frequente.", "quim": "**Azoxistrobina:** Controle de Ferrugem sem manchar fruto.", "bio": "**Silício:** Barreira física contra pragas."},
            "Maturação": {"desc": "Colheita.", "fisio": "Fruto climatério.", "manejo": "Resfriamento rápido.", "quim": "**Não aplicar químicos sistêmicos.**", "bio": "**Quitosana:** Filme protetor pós-colheita."}
        }
    },
    "Amora (Rubus spp.)": {
        "t_base": 7,
        "vars": {"Tupy": {"kc": 1.0, "gda_meta": 1500, "info": "Preta. Exige poda drástica de inverno."}, "Xingu": {"kc": 1.05, "gda_meta": 1400, "info": "Sem espinhos. Fácil manejo."}},
        "fases": {
            "Brotação": {"desc": "Quebra de Dormência.", "fisio": "Ativação de gemas.", "manejo": "Aplicação de Cianamida (se necessário).", "quim": "**Cobre:** Limpeza de ramos pós-poda.", "bio": "**Calda Sulfocálcica:** Tratamento de inverno."},
            "Florada": {"desc": "Cachos Florais.", "fisio": "Polinização.", "manejo": "Nutrição Boro.", "quim": "**Captana:** Fungicida protetor multissítio.", "bio": "**Extrato de Alho:** Repelência."},
            "Frutificação": {"desc": "Enchimento.", "fisio": "Acúmulo de água.", "manejo": "Irrigação.", "quim": "**Tebuconazol:** Controle de Ferrugem da Amora.", "bio": "**Metarhizium:** Controle biológico de tripes."},
            "Maturação": {"desc": "Preto Brilhante.", "fisio": "Máximo açúcar.", "manejo": "Colheita.", "quim": "**Espinosade:** Controle de Drosófila.", "bio": "**Armadilhas:** Monitoramento massal."}
        }
    },
    "Morango (Fragaria x ananassa)": {
        "t_base": 7,
        "vars": {"San Andreas": {"kc": 0.85, "gda_meta": 1200, "info": "Dia neutro. Alta produção."}, "Albion": {"kc": 0.85, "gda_meta": 1250, "info": "Sabor superior. Fruto cônico."}},
        "fases": {
            "Vegetativo": {"desc": "Desenvolvimento de Coroa.", "fisio": "Emissão de folhas.", "manejo": "Limpeza de folhas velhas.", "quim": "**Enxofre:** Preventivo de Oídio.", "bio": "**Silicato de Potássio:** Resistência mecânica."},
            "Florada": {"desc": "Emissão de Hastes.", "fisio": "Polinização.", "manejo": "Ventilação do túnel.", "quim": "**Ciprodinil + Fludioxonil:** Controle de Botrytis.", "bio": "**Clonostachys rosea:** Fungo antagonista a Botrytis."},
            "Colheita": {"desc": "Frutificação Contínua.", "fisio": "Maturação escalonada.", "manejo": "Colheita a cada 2 dias.", "quim": "**Etoxazol:** Controle de ovos de Ácaro.", "bio": "**Neoseiulus californicus:** Ácaro predador."}
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

def get_forecast(lat, lon, key, kc, t_base):
    try:
        url = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={key}&units=metric&lang=pt_br"
        r = requests.get(url).json()
        dados = []
        if 'list' in r:
            for item in r['list']:
                t = item['main']['temp']
                u = item['main']['humidity']
                
                # Cálculos Agronômicos
                es = 0.61078 * math.exp((17.27 * t) / (t + 237.3))
                ea = es * (u / 100)
                vpd = max(0, round(es - ea, 2))
                gda = max(0, (t - t_base) / 8) 
                et0 = 0.0023 * (t + 17.8) * (t ** 0.5) * 0.408
                
                dados.append({
                    'Data': datetime.fromtimestamp(item['dt']),
                    'Temp': t,
                    'Umid': u,
                    'Chuva': item.get('rain', {}).get('3h', 0),
                    'VPD': vpd,
                    'GDA': gda,
                    'ETc': round(et0 * kc, 2),
                    'Descrição': item['weather'][0]['description'].title()
                })
            return pd.DataFrame(dados)
    except: return pd.DataFrame()

def get_radar(lat, lon, key):
    pontos = {
        "Norte (15km)": (lat + 0.13, lon),
        "Sul (15km)": (lat - 0.13, lon),
        "Leste (15km)": (lat, lon + 0.13),
        "Oeste (15km)": (lat, lon - 0.13)
    }
    res = []
    for d, c in pontos.items():
        try:
            r = requests.get(f"https://api.openweathermap.org/data/2.5/weather?lat={c[0]}&lon={c[1]}&appid={key}&units=metric").json()
            res.append({"Loc": d, "T": r['main']['temp'], "Chuva": "SIM" if "rain" in r else "Não"})
        except: pass
    return pd.DataFrame(res)

# --- 4. SIDEBAR (APENAS LOGIN) ---
with st.sidebar:
    st.header("🔐 Acesso & APIs")
    api_w = st.secrets.get("OPENWEATHER_KEY", st.text_input("OpenWeather Key:", type="password"))
    api_g = st.secrets.get("GEMINI_KEY", st.text_input("Gemini API Key:", type="password"))
    st.divider()
    st.caption("Agro-Intel Enterprise v43.0")

# --- 5. PAINEL DE CONTROLE CENTRAL (INPUTS) ---
# Inicialização
if 'lat' not in st.session_state: st.session_state.lat = -13.2000
if 'lon' not in st.session_state: st.session_state.lon = -41.4000

# Container de Configuração (Topo da Página)
with st.container():
    st.markdown("### ⚙️ Painel de Operação")
    c1, c2, c3 = st.columns(3)
    
    with c1:
        st.markdown("**📍 Localização**")
        t_c, t_g = st.tabs(["Cidade", "Coordenadas"])
        with t_c:
            cid = st.text_input("Cidade:", placeholder="Ex: Mucugê, BA")
            if st.button("📍 Buscar") and api_w:
                nlat, nlon = get_coords(cid, api_w)
                if nlat: st.session_state.lat, st.session_state.lon = nlat, nlon; st.rerun()
        with t_g:
            cl_a, cl_b = st.columns(2)
            st.session_state.lat = cl_a.number_input("Lat:", value=st.session_state.lat, format="%.4f")
            st.session_state.lon = cl_b.number_input("Lon:", value=st.session_state.lon, format="%.4f")
            
    with c2:
        st.markdown("**🌱 Cultura e Genética**")
        cultura = st.selectbox("Cultura:", list(BANCO_MASTER.keys()))
        variedade = st.selectbox("Variedade:", list(BANCO_MASTER[cultura]['vars'].keys()))
        fase = st.selectbox("Fase Atual:", list(BANCO_MASTER[cultura]['fases'].keys()))
        
    with c3:
        st.markdown("**📅 Calendário**")
        dt_inicio = st.date_input("Data de Plantio:", date(2025, 12, 1))

# --- 6. PROCESSAMENTO E DASHBOARD ---
if api_w:
    # Dados Seguros
    c_db = BANCO_MASTER[cultura]
    v_db = c_db['vars'][variedade]
    f_db = c_db['fases'][fase]
    
    df = get_forecast(st.session_state.lat, st.session_state.lon, api_w, v_db['kc'], c_db['t_base'])
    
    if not df.empty:
        hoje = df.iloc[0]
        dias = (date.today() - dt_inicio).days
        gda_acum = dias * (df['GDA'].sum() / 5 * 8)
        
        # --- CABEÇALHO UNIFICADO E RICO ---
        st.markdown(f"""
        <div class="header-main">
            <div class="header-top">
                <h1 style="margin:0">Agro-Intel Enterprise</h1>
                <div class="tag-info">GDA Acumulado: {gda_acum:.0f}</div>
            </div>
            <div class="header-details">
                <span>🌱 <b>Cultura:</b> {cultura}</span>
                <span>🧬 <b>Variedade:</b> {variedade}</span>
                <span>📅 <b>Idade:</b> {dias} dias</span>
                <span>ℹ️ <b>Info Genética:</b> {v_db['info']}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # --- MÉTRICAS DE CLIMA (LADO A LADO) ---
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("🌡️ Temperatura", f"{hoje['Temp']:.1f}°C")
        m2.metric("💧 Umidade", f"{hoje['Umid']}%")
        m3.metric("🌧️ Chuva (3h)", f"{hoje['Chuva']} mm")
        m4.metric("💦 Demanda ETc", f"{hoje['ETc']} mm")

        # --- ABAS DE ANÁLISE ---
        tabs = st.tabs(["🎓 Consultoria Profissional", "📊 Clima & Balanço", "📡 Radar", "👁️ IA Vision", "🗺️ Mapa", "🚚 Logística"])

        # ABA 1: CONSULTORIA TÉCNICA
        with tabs[0]:
            st.markdown(f"<div class='pro-title'>Diagnóstico Fenológico: {fase}</div>", unsafe_allow_html=True)
            
            
            st.progress(min(1.0, gda_acum/v_db['gda_meta']))
            
            # Alerta de Risco
            if hoje['Umid'] > 85:
                st.markdown(f"<div class='alert-high'>🚨 ALERTA CRÍTICO: Umidade > 85%. Alto risco de doenças fúngicas/bacterianas.</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div class='alert-low'>✅ CONDIÇÃO SEGURA: Baixo risco de infecção.</div>", unsafe_allow_html=True)
            
            

            col_esq, col_dir = st.columns(2)
            with col_esq:
                st.markdown(f"""
                <div class="tech-card">
                    <h4>🧬 Fisiologia da Planta</h4>
                    <p>{f_db['fisio']}</p>
                    <hr>
                    <h4>🚜 Ações Culturais</h4>
                    <p>{f_db['manejo']}</p>
                </div>
                <div class="bio-card">
                    <h4>🌿 Controle Biológico Avançado</h4>
                    <p>{f_db['bio']}</p>
                    <p class="mechanism">Foco em equilíbrio microbiológico e resistência induzida.</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col_dir:
                st.markdown(f"""
                <div class="chem-card">
                    <h4>🧪 Controle Químico Profissional</h4>
                    <p>{f_db['quim']}</p>
                    <p class="mechanism">Sugestão baseada em grupos químicos e rotação de ativos.</p>
                </div>
                <div class="tech-card" style="border-left: 5px solid #ff9800;">
                    <h4>⚠️ Principais Alvos (Pragas/Doenças)</h4>
                    <p>{f_db['riscos']}</p>
                </div>
                """, unsafe_allow_html=True)

        # ABA 2: CLIMA
        with tabs[1]:
            st.markdown("### 📊 Precipitação vs. Demanda Hídrica")
            fig = go.Figure()
            fig.add_trace(go.Bar(x=df['Data'], y=df['Chuva'], name='Chuva (mm)', marker_color='#2196f3'))
            fig.add_trace(go.Scatter(x=df['Data'], y=df['ETc'], name='Consumo ETc (mm)', line=dict(color='#d32f2f', width=3)))
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(df, use_container_width=True)

        # ABA 3: RADAR
        with tabs[2]:
            st.markdown("### 📡 Monitoramento de Vizinhança (15km)")
            r_df = get_radar(st.session_state.lat, st.session_state.lon, api_w)
            if not r_df.empty:
                cols = st.columns(4)
                for i, r in r_df.iterrows():
                    bg = "#ffebee" if r['Chuva'] == "SIM" else "#e8f5e9"
                    with cols[i]:
                        st.markdown(f"""
                        <div style="background:{bg}; padding:15px; border-radius:10px; text-align:center; border:1px solid #ccc">
                            <b>{r['Loc']}</b><br>
                            <h2>{r['T']:.1f}°C</h2>
                            Chuva: {r['Chuva']}
                        </div>
                        """, unsafe_allow_html=True)

        # ABA 4: IA
        with tabs[3]:
            if api_g:
                foto = st.camera_input("Scanner Fitossanitário")
                if foto:
                    genai.configure(api_key=api_g)
                    res = genai.GenerativeModel('gemini-1.5-flash').generate_content([f"Agrônomo Expert. Analise {cultura} {variedade}. Sintomas e Solução.", Image.open(foto)])
                    st.success("Laudo Gerado:")
                    st.write(res.text)
            else: st.warning("Insira a chave Gemini na Sidebar.")

        # ABA 5: MAPA
        with tabs[4]:
            m = folium.Map([st.session_state.lat, st.session_state.lon], zoom_start=15)
            folium.TileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', attr='Esri', name='Satélite').add_to(m)
            st_folium(m, width="100%", height=500)
            
        # ABA 6: LOGISTICA
        with tabs[5]:
            c1, c2 = st.columns(2)
            with c1:
                d = st.number_input("Distância (km)", value=450)
                cons = st.number_input("Km/L", value=10.0)
                pr = st.number_input("Preço Comb.", value=6.20)
                p = st.slider("Carga (kg)", 100, 800, 400)
            with c2:
                tot = (d/cons)*pr
                st.metric("Custo Viagem", f"R$ {tot:.2f}")
                st.metric("Custo/Kg", f"R$ {tot/p:.2f}")

else:
    st.info("👈 Configure a API OpenWeather na barra lateral.")
