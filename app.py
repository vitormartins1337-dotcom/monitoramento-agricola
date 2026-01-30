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
st.set_page_config(page_title="Agro-Intel", page_icon="🌱", layout="wide")

st.markdown("""
<style>
    .main { background-color: #f4f6f9; }
    
    /* Cabeçalho Principal */
    .header-main { 
        background: linear-gradient(90deg, #1b5e20 0%, #2e7d32 100%); 
        padding: 25px; 
        border-radius: 12px; 
        color: white; 
        margin-bottom: 20px; 
        box-shadow: 0 4px 10px rgba(0,0,0,0.1); 
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    
    /* Painel de Controle (Inputs) */
    .control-panel {
        background-color: white;
        padding: 20px;
        border-radius: 12px;
        border: 1px solid #e0e0e0;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        margin-bottom: 25px;
    }
    
    /* Cards de Informação */
    .tech-card { background: white; padding: 20px; border-radius: 12px; border-left: 5px solid #2e7d32; box-shadow: 0 2px 5px rgba(0,0,0,0.05); margin-bottom: 15px; }
    
    /* Estilos de Risco */
    .alert-high { background-color: #ffebee; border: 1px solid #ffcdd2; color: #b71c1c; padding: 15px; border-radius: 8px; font-weight: bold; }
    .alert-low { background-color: #e8f5e9; border: 1px solid #c8e6c9; color: #1b5e20; padding: 15px; border-radius: 8px; font-weight: bold; }
    
    /* Títulos e Textos */
    h4 { color: #1565c0; margin-top: 0; }
    .justification { font-size: 0.9em; color: #555; font-style: italic; margin-bottom: 10px; }
</style>
""", unsafe_allow_html=True)

# --- 2. BANCO DE DADOS AGRONÔMICO (COM EXPLICAÇÕES PROFISSIONAIS) ---
BANCO_MASTER = {
    "Batata (Solanum tuberosum)": {
        "t_base": 7,
        "vars": {
            "Orchestra": {"kc": 1.15, "gda_meta": 1600, "info": "Pele lisa premium. Alta exigência de Potássio (K) para acabamento."},
            "Cupido": {"kc": 1.10, "gda_meta": 1400, "info": "Ciclo ultra-curto. Extrema sensibilidade à Requeima."},
            "Camila": {"kc": 1.15, "gda_meta": 1550, "info": "Referência mercado fresco. Monitorar Sarna Comum."},
            "Atlantic": {"kc": 1.15, "gda_meta": 1650, "info": "Industrial (Chips). Cuidado com Coração Oco."}
        },
        "fases": {
            "Emergência (0-20 dias)": {
                "desc": "Brotamento e Enraizamento.", 
                "fisio": "A planta drena reservas do tubérculo-mãe. Raízes absorventes ainda são frágeis.", 
                "manejo": "Solo aerado. Evitar encharcamento para não sufocar lenticelas.", 
                "riscos": "Rhizoctonia (Canela Preta), Pectobacterium.",
                "quim": "**Azoxistrobina:** Estrobilurina sistêmica para controle preventivo de Rhizoctonia no sulco.\n**Tiametoxam:** Neonicotinoide para proteção inicial contra pulgões vetores.", 
                "bio": "**Trichoderma harzianum:** Coloniza o sistema radicular, competindo com patógenos de solo por espaço e nutrientes."
            },
            "Vegetativo (20-35 dias)": {
                "desc": "Expansão Foliar.", 
                "fisio": "Alta demanda de Nitrogênio para síntese de clorofila e expansão do IAF.", 
                "manejo": "Amontoa técnica para cobrir estolões.", 
                "riscos": "Vaquinha, Minadora, Míldio.",
                "quim": "**Mancozeb:** Fungicida multissítio protetor (Grupo M3). Essencial para manejo de resistência.\n**Clorotalonil:** Ação de contato com alta aderência foliar.", 
                "bio": "**Beauveria bassiana:** Fungo entomopatogênico que infecta insetos mastigadores (Vaquinha)."
            },
            "Tuberização (35-50 dias)": {
                "desc": "Início da Tuberização (Ganchos).", 
                "fisio": "Inversão hormonal crítica (Queda de Giberelina). Qualquer estresse hídrico agora causa abortamento.", 
                "manejo": "Irrigação de precisão (Turnos curtos).", 
                "riscos": "Requeima (Phytophthora), Sarna.",
                "quim": "**Mandipropamida (Revus):** Alta afinidade com a cera da folha, excelente contra Oomicetos.\n**Metalaxil-M:** Sistêmico curativo para Requeima (penetração rápida).", 
                "bio": "**Bacillus subtilis:** Produz lipopeptídeos que inibem o crescimento de bactérias (Sarna)."
            },
            "Enchimento (50-80 dias)": {
                "desc": "Expansão dos Tubérculos.", 
                "fisio": "Dreno intenso de Potássio e Magnésio. Translocação de fotoassimilados da folha para o tubérculo.", 
                "manejo": "Sanidade foliar total para maximizar fotossíntese.", 
                "riscos": "Mosca Branca, Traça, Pinta Preta.",
                "quim": "**Ciantraniliprole (Benévia):** Diamida que paralisa a alimentação de mastigadores e sugadores.\n**Espirotesifeno:** Inibidor de síntese de lipídios (Ácaros/Mosca).", 
                "bio": "**Extrato de Algas (Ascophyllum):** Fonte de citocininas naturais para manter a folha verde (Stay-green)."
            },
            "Maturação (80+ dias)": {
                "desc": "Senescência e Cura.", 
                "fisio": "Suberização da pele (casca). Conversão de açúcares em amido.", 
                "manejo": "Dessecação e suspensão da irrigação.", 
                "riscos": "Podridão mole, Larva Alfinete.",
                "quim": "**Diquat:** Dessecante de contato (Fotossistema I) para uniformizar a colheita.\n**Cuidado:** Respeitar o período de carência.", 
                "bio": "**Suspensão de N:** Cortar Nitrogênio para evitar rebrota e pele fina."
            }
        }
    },
    "Café (Coffea arabica)": {
        "t_base": 10,
        "vars": {
            "Catuaí": {"kc": 1.1, "gda_meta": 3000, "info": "Alta qualidade de bebida, mas suscetível à Ferrugem."},
            "Arara": {"kc": 1.2, "gda_meta": 2900, "info": "Resistente à Ferrugem. Alta produtividade e vigor."}
        },
        "fases": {
            "Florada": {
                "desc": "Antese.", "fisio": "Pico de demanda de Boro para formação do tubo polínico.", "manejo": "Não aplicar inseticidas tóxicos às abelhas.", "riscos": "Phoma, Mancha Aureolada.",
                "quim": "**Boscalida:** Inibidor da respiração (SDHI) eficaz contra Phoma.\n**Piraclostrobina:** Efeito fisiológico (AgCelence) melhorando o pegamento.", "bio": "**Cálcio + Boro:** Aplicação foliar para estruturação da flor."
            },
            "Chumbinho": {
                "desc": "Expansão dos frutos.", "fisio": "Divisão celular intensa.", "manejo": "Adubação Nitrogenada.", "riscos": "Cercospora, Ferrugem.",
                "quim": "**Priori Xtra (Ciproconazol + Azoxistrobina):** Combinação de Triazol (curativo) e Estrobilurina (preventivo).", "bio": "**Aminoácidos:** Redução do estresse térmico/hídrico."
            }
        }
    },
    "Tomate": {
        "t_base": 10,
        "vars": {
            "Italiano": {"kc": 1.2, "gda_meta": 1600, "info": "Fruto alongado. Atenção ao Fundo Preto (Cálcio)."},
            "Grape": {"kc": 1.1, "gda_meta": 1450, "info": "Alto teor de açúcar. Sensível a rachaduras."}
        },
        "fases": {
            "Frutificação": {
                "desc": "Engorda.", "fisio": "Alta demanda de K para transporte de açúcares.", "manejo": "Condução vertical.", "riscos": "Traça (Tuta), Requeima.",
                "quim": "**Clorfenapir:** Ação de choque contra lagartas.\n**Dimetomorfe:** Específico para Oomicetos (Requeima).", "bio": "**Bacillus thuringiensis:** Controle biológico de lagartas sem resíduo."
            }
        }
    },
    "Mirtilo (Blueberry)": {
        "t_base": 7,
        "vars": {"Emerald": {"kc": 0.95, "gda_meta": 1800, "info": "Vigorosa. pH ácido (4.5)."}, "Biloxi": {"kc": 0.90, "gda_meta": 1900, "info": "Ereta. Baixo frio."}},
        "fases": {
            "Crescimento": {
                "desc": "Expansão da Baga.", "fisio": "Acúmulo de água e sólidos solúveis.", "manejo": "Nutrição Potássica.", "riscos": "Antracnose.",
                "quim": "**Azoxistrobina:** Preventivo amplo espectro.\n**Difenoconazol:** Curativo para manchas foliares.", "bio": "**Ácidos Fúlvicos:** Melhoram a absorção de nutrientes em pH ácido."
            }
        }
    },
    "Morango": {
        "t_base": 7,
        "vars": {"San Andreas": {"kc": 0.85, "gda_meta": 1200, "info": "Dia neutro. Sensível a Ácaros."}, "Albion": {"kc": 0.85, "gda_meta": 1250, "info": "Sabor adocicado. Sensível a Oídio."}},
        "fases": {
            "Colheita": {
                "desc": "Maturação.", "fisio": "Síntese de antocianinas (cor vermelha).", "manejo": "Colheita diária.", "riscos": "Mofo Cinzento (Botrytis).",
                "quim": "**Ciprodinil:** Específico para Botrytis com curto período de carência.", "bio": "**Silicato de Potássio:** Endurece a parede celular, dificultando fungos."
            }
        }
    },
    "Amora/Framboesa": {
        "t_base": 7,
        "vars": {"Heritage": {"kc": 1.1, "gda_meta": 1300, "info": "Framboesa Remontante."}, "Tupy": {"kc": 1.0, "gda_meta": 1500, "info": "Amora Preta."}},
        "fases": {
            "Frutificação": {
                "desc": "Maturação.", "fisio": "Fruto muito perecível.", "manejo": "Refrigeração rápida.", "riscos": "Drosófila suzukii.",
                "quim": "**Espinosade:** Origem biológica, eficaz contra mosca-das-frutas.", "bio": "**Armadilhas:** Vinagre de maçã para monitoramento."
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
                gda = max(0, (t - t_base) / 8) # GDA por fração do dia (3h)
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
    st.image("https://cdn-icons-png.flaticon.com/512/2822/2822444.png", width=80)
    st.title("Acesso Seguro")
    api_w = st.secrets.get("OPENWEATHER_KEY", st.text_input("OpenWeather Key:", type="password"))
    api_g = st.secrets.get("GEMINI_KEY", st.text_input("Gemini API Key:", type="password"))
    st.divider()
    st.caption("Agro-Intel System v42.0")

# --- 5. PAINEL DE CONTROLE CENTRAL (TOPO) ---
st.markdown("""<div class="header-main"><h1>🛰️ Agro-Intel</h1><h3>Sistema de Suporte à Decisão</h3></div>""", unsafe_allow_html=True)

# Container de Configuração
with st.container():
    st.markdown("### ⚙️ Painel de Operação")
    
    # Inicialização
    if 'lat' not in st.session_state: st.session_state.lat = -13.2000
    if 'lon' not in st.session_state: st.session_state.lon = -41.4000
    
    col1, col2, col3 = st.columns(3)
    
    # Coluna 1: Localização
    with col1:
        st.markdown("**📍 Localização**")
        tab_c, tab_g = st.tabs(["Por Cidade", "GPS"])
        with tab_c:
            cidade = st.text_input("Cidade:", placeholder="Ex: Ibicoara, BA")
            if st.button("Buscar") and api_w:
                nlat, nlon = get_coords(cidade, api_w)
                if nlat: st.session_state.lat, st.session_state.lon = nlat, nlon; st.rerun()
        with tab_g:
            c_a, c_b = st.columns(2)
            st.session_state.lat = c_a.number_input("Lat:", value=st.session_state.lat, format="%.4f")
            st.session_state.lon = c_b.number_input("Lon:", value=st.session_state.lon, format="%.4f")

    # Coluna 2: Cultura
    with col2:
        st.markdown("**🌱 Cultura e Genética**")
        cultura = st.selectbox("Cultura:", list(BANCO_MASTER.keys()))
        variedade = st.selectbox("Variedade:", list(BANCO_MASTER[cultura]['vars'].keys()))
        fase = st.selectbox("Fase Atual:", list(BANCO_MASTER[cultura]['fases'].keys()))

    # Coluna 3: Calendário
    with col3:
        st.markdown("**📅 Ciclo Produtivo**")
        dt_inicio = st.date_input("Data de Plantio:", date(2025, 12, 1))

# --- 6. PROCESSAMENTO E EXIBIÇÃO ---
if api_w:
    # Dados Seguros
    c_db = BANCO_MASTER[cultura]
    v_db = c_db['vars'][variedade]
    f_db = c_db['fases'][fase]
    
    df = get_forecast(st.session_state.lat, st.session_state.lon, api_w, v_db['kc'], c_db['t_base'])
    
    if not df.empty:
        hoje = df.
