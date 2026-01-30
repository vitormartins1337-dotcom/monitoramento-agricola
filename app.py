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
    
    /* CAPA DO APP (HEADER) */
    .app-cover { 
        background: linear-gradient(135deg, #006064 0%, #1b5e20 100%); 
        padding: 30px; 
        border-radius: 0 0 15px 15px; 
        color: white; 
        margin-top: -60px; 
        margin-left: -5rem; 
        margin-right: -5rem;
        padding-left: 5rem;
        padding-right: 5rem;
        margin-bottom: 0px; /* Colado na barra climática */
        box-shadow: 0 6px 20px rgba(0,0,0,0.15);
        border-bottom: 1px solid rgba(255,255,255,0.1);
    }
    .cover-title { font-size: 3em; font-weight: 900; margin: 0; letter-spacing: -1px; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); }
    .cover-subtitle { font-size: 1.3em; font-weight: 300; opacity: 0.95; margin-bottom: 25px; font-style: italic; border-bottom: 1px solid rgba(255,255,255,0.2); padding-bottom: 15px; display: inline-block; }
    .data-grid { display: flex; gap: 20px; flex-wrap: wrap; margin-top: 15px; }
    .info-tag { background: rgba(255,255,255,0.15); padding: 10px 20px; border-radius: 10px; font-weight: 600; font-size: 1em; backdrop-filter: blur(5px); border: 1px solid rgba(255,255,255,0.2); display: flex; align-items: center; gap: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }

    /* BARRA CLIMÁTICA HORIZONTAL (NOVIDADE) */
    .climate-strip {
        background: white;
        margin-left: -5rem;
        margin-right: -5rem;
        padding: 15px 5rem;
        display: flex;
        justify-content: space-around;
        align-items: center;
        border-bottom: 1px solid #e0e0e0;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        margin-bottom: 25px;
    }
    .climate-item { text-align: center; border-right: 1px solid #eee; flex: 1; }
    .climate-item:last-child { border-right: none; }
    .climate-label { font-size: 0.85em; color: #666; text-transform: uppercase; letter-spacing: 1px; }
    .climate-value { font-size: 1.4em; font-weight: 800; color: #2e7d32; }

    /* CARDS TÉCNICOS PROFISSIONAIS */
    .tech-card { background: white; padding: 25px; border-radius: 12px; border-left: 6px solid #1565c0; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 20px; }
    .chem-card { background: white; padding: 25px; border-radius: 12px; border-left: 6px solid #c62828; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 20px; }
    .bio-card { background: white; padding: 25px; border-radius: 12px; border-left: 6px solid #2e7d32; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 20px; }
    
    .agro-explanation { font-size: 0.9em; color: #555; margin-top: 8px; border-left: 2px solid #ddd; padding-left: 10px; font-style: italic; }
    .active-ingredient { color: #d32f2f; font-weight: 700; }
    
    /* ALERTA */
    .alert-box { padding: 15px; border-radius: 8px; font-weight: bold; margin-bottom: 15px; text-align: center; font-size: 1.1em; }
    .high-risk { background-color: #ffebee; color: #b71c1c; border: 1px solid #ef5350; }
    .low-risk { background-color: #e8f5e9; color: #1b5e20; border: 1px solid #66bb6a; }
</style>
""", unsafe_allow_html=True)

# --- 2. BANCO DE DADOS AGRONÔMICO (MANTIDO) ---
BANCO_MASTER = {
    "Batata (Solanum tuberosum)": {
        "t_base": 7, "t_teto": 29, # Adicionado Teto Térmico para cálculo preciso
        "vars": {
            "Orchestra": {"kc": 1.15, "gda_meta": 1600, "info": "Pele lisa, polpa amarela. Alta exigência de K e Boro."},
            "Cupido": {"kc": 1.10, "gda_meta": 1400, "info": "Ciclo ultra-curto (90 dias). Sensível a Metribuzin."},
            "Camila": {"kc": 1.15, "gda_meta": 1550, "info": "Mercado fresco. Exige manejo preventivo para Sarna."},
            "Atlantic": {"kc": 1.15, "gda_meta": 1650, "info": "Industrial (Chips). Monitorar Matéria Seca."}
        },
        "fases": {
            "Emergência (0-20 dias)": {
                "desc": "Brotamento e Enraizamento.", 
                "fisio": "A planta drena reservas do tubérculo-mãe. Raízes absorventes ainda são frágeis.", 
                "manejo": "Manter solo friável. Evitar crostas superficiais.", 
                "riscos": "Rhizoctonia (Canela Preta), Pectobacterium.",
                "quim": "**Azoxistrobina (Grupo 11):** Inibidor da respiração mitocondrial (QoI). Aplicação no sulco protege estolões.\n**Tiametoxam (Grupo 4A):** Neonicotinoide sistêmico via xilema para proteção inicial contra vetores.", 
                "bio": "**Trichoderma harzianum:** Coloniza a rizosfera, criando uma barreira física e enzimática contra patógenos de solo."
            },
            "Vegetativo (20-35 dias)": {
                "desc": "Expansão de Hastes.", 
                "fisio": "Alta taxa fotossintética. Demanda crítica de Nitrogênio e Magnésio.", 
                "manejo": "Amontoa técnica para estimular tuberização e proteger contra traça.", 
                "riscos": "Vaquinha (Diabrotica), Minadora.",
                "quim": "**Mancozeb (Grupo M03):** Multissítio de contato. Essencial para manejo de resistência (anti-resiliente).\n**Clorotalonil (Grupo M05):** Alta aderência e tenacidade à chuva.", 
                "bio": "**Beauveria bassiana:** Fungo entomopatogênico que infecta insetos mastigadores via contato."
            },
            "Tuberização (35-50 dias)": {
                "desc": "Início da Formação (Ganchos).", 
                "fisio": "Inversão hormonal (Giberelina cai, Citocinina sobe). Estresse hídrico agora causa 'bonecos' ou abortamento.", 
                "manejo": "Irrigação de precisão (evitar oscilações).", 
                "riscos": "Requeima (Phytophthora), Sarna.",
                "quim": "**Mandipropamida (Grupo 40):** Inibe a síntese de celulose nos Oomicetos. Alta afinidade com a cera.\n**Metalaxil-M (Grupo 4):** Sistêmico curativo (penetração rápida).", 
                "bio": "**Bacillus subtilis:** Produz iturinas e surfactinas que rompem a membrana de bactérias fitopatogênicas."
            },
            "Enchimento (50-80 dias)": {
                "desc": "Crescimento dos Tubérculos.", 
                "fisio": "Translocação intensa de açúcares. Dreno massivo de Potássio.", 
                "manejo": "Sanidade foliar total (Manter IAF).", 
                "riscos": "Mosca Branca, Traça, Pinta Preta.",
                "quim": "**Ciantraniliprole (Grupo 28):** Modulador de canais de rianodina. Paralisação muscular rápida.\n**Espirotesifeno (Grupo 23):** Inibe biossíntese de lipídios em ácaros/moscas.", 
                "bio": "**Extrato de Algas (Ascophyllum):** Rico em citocininas e betaínas para reduzir estresse térmico (efeito stay-green)."
            },
            "Maturação (80+ dias)": {
                "desc": "Senescência e Cura.", 
                "fisio": "Suberização da pele (casca). Conversão de sacarose em amido.", 
                "manejo": "Dessecação para uniformizar colheita.", 
                "riscos": "Podridão mole, Larva Alfinete.",
                "quim": "**Diquat (Grupo 22):** Desviador de elétrons (Fotossistema I). Ação de contato rápida.\n**Carfentrazona (Grupo 14):** Inibidor da PPO.", 
                "bio": "**Suspender Nitrogênio:** O excesso atrasa a pele e reduz qualidade pós-colheita."
            }
        }
    },
    "Tomate (Solanum lycopersicum)": {
        "t_base": 10, "t_teto": 32,
        "vars": {
            "Italiano": {"kc": 1.2, "gda_meta": 1600, "info": "Fruto alongado. Exige Cálcio."},
            "Grape": {"kc": 1.1, "gda_meta": 1450, "info": "Alto Brix. Sensível a rachaduras."}
        },
        "fases": {
            "Vegetativo": {
                "desc": "Crescimento Vertical.", 
                "fisio": "Formação de estrutura.", 
                "manejo": "Desbrota lateral.", 
                "riscos": "Tripes, Geminivírus.",
                "quim": "**Imidacloprido (Grupo 4A):** Sistêmico no gotejo.", 
                "bio": "**Micorrizas:** Aumenta exploração radicular."
            },
            "Florada": {
                "desc": "Emissão de Cachos.", 
                "fisio": "Viabilidade do pólen (sensível a calor).", 
                "manejo": "Vibração ou Hormônio.", 
                "riscos": "Oídio, Botrytis.",
                "quim": "**Azoxistrobina (Grupo 11):** Preventivo e anti-esporulante.", 
                "bio": "**Cálcio + Boro:** Essencial para tubo polínico."
            },
            "Frutificação": {
                "desc": "Engorda.", 
                "fisio": "Dreno de Potássio e Água.", 
                "manejo": "Condução vertical.", 
                "riscos": "Traça (Tuta), Requeima.",
                "quim": "**Clorfenapir (Grupo 13):** Desacoplador da fosforilação oxidativa (Choque).", 
                "bio": "**Bacillus thuringiensis:** Cristal proteico tóxico para lagartas."
            },
            "Colheita": {
                "desc": "Maturação.", 
                "fisio": "Síntese de Licopeno (Cor).", 
                "manejo": "Colheita delicada.", 
                "riscos": "Pós-colheita.",
                "quim": "**Cobre:** Bactericida multissítio.", 
                "bio": "**Óleo de Laranja:** Dessecante de contato."
            }
        }
    },
    "Café (Coffea arabica)": {
        "t_base": 10, "t_teto": 30,
        "vars": {
            "Catuaí": {"kc": 1.1, "gda_meta": 3000, "info": "Qualidade bebida. Sensível à Ferrugem."},
            "Arara": {"kc": 1.2, "gda_meta": 2900, "info": "Resistente à Ferrugem."}
        },
        "fases": {
            "Florada": {
                "desc": "Antese.", 
                "fisio": "Alta demanda energética. Antese sincronizada pela chuva.", 
                "manejo": "Não aplicar inseticidas (Abelhas).", 
                "riscos": "Phoma, Mancha Aureolada.",
                "quim": "**Boscalida (Grupo 7):** Carboxamida específica para Phoma.", 
                "bio": "**Extrato de Algas:** Redução de abortamento."
            },
            "Chumbinho": {
                "desc": "Expansão Inicial.", 
                "fisio": "Intensa divisão celular.", 
                "manejo": "Adubação Nitrogenada.", 
                "riscos": "Cercospora, Ferrugem.",
                "quim": "**Ciproconazol (Grupo 3):** Triazol com efeito sistêmico rápido.", 
                "bio": "**Cobre quelatado:** Fortalecimento da cutícula."
            },
            "Granação": {
                "desc": "Enchimento.", 
                "fisio": "Deposição de matéria seca.", 
                "manejo": "Adubação Potássica.", 
                "riscos": "Broca-do-Café.",
                "quim": "**Ciantraniliprole:** Sistêmico via xilema contra broca.", 
                "bio": "**Beauveria bassiana:** Infecção de adultos da broca."
            },
            "Maturação": {
                "desc": "Cereja.", 
                "fisio": "Açúcares redutores.", 
                "manejo": "Arruação.", 
                "riscos": "Queda de frutos.",
                "quim": "**Respeitar Carência Rigorosa.**", 
                "bio": "**Potássio Foliar:** Uniformização."
            }
        }
    },
    "Mirtilo (Blueberry)": {
        "t_base": 7, "t_teto": 28,
        "vars": {"Emerald": {"kc": 0.95, "gda_meta": 1800, "info": "pH 4.5. Vigorosa."}, "Biloxi": {"kc": 0.90, "gda_meta": 1900, "info": "Baixo frio. Rústica."}},
        "fases": {
            "Brotação": {"desc": "Fluxo Vegetativo.", "fisio": "Mobilização de reservas.", "manejo": "Correção de pH.", "riscos": "Cochonilhas.", "quim": "**Óleo Mineral:** Asfixia mecânica de cochonilhas.", "bio": "**Bokashi:** Estímulo à microbiota acidófila."},
            "Florada": {"desc": "Polinização.", "fisio": "Flor invertida protege pólen, mas requer vibração.", "manejo": "Abelhas (Bombus).", "riscos": "Botrytis (Mofo).", "quim": "**Fludioxonil (Grupo 12):** Inibidor da transdução de sinal (Switch).", "bio": "**Aminoácidos:** Viabilidade do grão de pólen."},
            "Fruto Verde": {"desc": "Crescimento.", "fisio": "Divisão celular.", "manejo": "Nutrição K.", "riscos": "Antracnose.", "quim": "**Difenoconazol:** Triazol de amplo espectro.", "bio": "**Ácidos Fúlvicos:** Complexação de cátions."},
            "Maturação": {"desc": "Mudança de Cor.", "fisio": "Síntese de Antocianinas.", "manejo": "Colheita.", "riscos": "Drosófila (SWD).", "quim": "**Espinosade (Grupo 5):** Modulador alostérico. Baixa carência.", "bio": "**Iscas Atrativas:** Monitoramento populacional."}
        }
    },
    "Framboesa (Rubus idaeus)": {
        "t_base": 7, "t_teto": 26,
        "vars": {"Heritage": {"kc": 1.1, "gda_meta": 1300, "info": "Remontante. Vermelha."}, "Golden": {"kc": 1.05, "gda_meta": 1250, "info": "Amarela. Suave."}},
        "fases": {
            "Brotação": {"desc": "Emissão de Hastes.", "fisio": "Crescimento vegetativo explosivo.", "manejo": "Seleção de hastes.", "riscos": "Ácaro Rajado.", "quim": "**Abamectina (Grupo 6):** Ativador do canal de cloro.", "bio": "**Enxofre:** Ação desalojante e fungistática."},
            "Florada": {"desc": "Botões Florais.", "fisio": "Alta sensibilidade à umidade.", "manejo": "Cobertura (Túnel).", "riscos": "Podridão Floral.", "quim": "**Iprodiona (Grupo 2):** Inibidor da transdução de sinal.", "bio": "**Cálcio Boro:** Firmeza do receptáculo floral."},
            "Frutificação": {"desc": "Formação de Bagas.", "fisio": "Fruto agregado (drupeletes).", "manejo": "Colheita frequente.", "riscos": "Ferrugem.", "quim": "**Azoxistrobina:** Preventivo sem resíduo visível.", "bio": "**Silício:** Barreira física na epiderme."},
            "Maturação": {"desc": "Colheita.", "fisio": "Fruto climatério, alta respiração.", "manejo": "Refrigeração imediata.", "riscos": "Fungos pós-colheita.", "quim": "**Não aplicar químicos sistêmicos.**", "bio": "**Quitosana:** Filme protetor comestível."}
        }
    },
    "Amora (Rubus spp.)": {
        "t_base": 7, "t_teto": 28,
        "vars": {"Tupy": {"kc": 1.0, "gda_meta": 1500, "info": "Preta. Exige poda."}, "Xingu": {"kc": 1.05, "gda_meta": 1400, "info": "Sem espinhos."}},
        "fases": {
            "Brotação": {"desc": "Quebra de Dormência.", "fisio": "Ativação metabólica de gemas.", "manejo": "Cianamida (se necessário).", "riscos": "Ferrugem da Amora.", "quim": "**Cobre:** Limpeza de ramos pós-poda.", "bio": "**Calda Sulfocálcica:** Tratamento de inverno."},
            "Florada": {"desc": "Cachos Florais.", "fisio": "Polinização cruzada.", "manejo": "Nutrição Boro.", "riscos": "Botrytis.", "quim": "**Captana (Grupo M04):** Protetor multissítio.", "bio": "**Extrato de Alho:** Repelência."},
            "Frutificação": {"desc": "Enchimento.", "fisio": "Acúmulo de água nas drupas.", "manejo": "Irrigação constante.", "riscos": "Ácaros.", "quim": "**Tebuconazol:** Triazol sistêmico.", "bio": "**Metarhizium:** Controle biológico de tripes."},
            "Maturação": {"desc": "Preto Brilhante.", "fisio": "Máximo teor de açúcar.", "manejo": "Colheita.", "riscos": "Drosófila.", "quim": "**Espinosade:** Controle de choque.", "bio": "**Armadilhas massais.**"}
        }
    },
    "Morango (Fragaria x ananassa)": {
        "t_base": 7, "t_teto": 26,
        "vars": {"San Andreas": {"kc": 0.85, "gda_meta": 1200, "info": "Dia neutro. Ácaros."}, "Albion": {"kc": 0.85, "gda_meta": 1250, "info": "Sabor. Oídio."}},
        "fases": {
            "Vegetativo": {"desc": "Coroa.", "fisio": "Emissão de novas folhas.", "manejo": "Limpeza sanitária.", "riscos": "Oídio, Ácaro.", "quim": "**Enxofre, Abamectina.**", "bio": "**Silício Foliar.**"},
            "Florada": {"desc": "Hastes.", "fisio": "Polinização (Fruto verdadeiro é o aquênio).", "manejo": "Ventilação.", "riscos": "Mofo Cinzento.", "quim": "**Ciprodinil:** Sistêmico (Grupo 9).", "bio": "**Clonostachys rosea:** Antagonista."},
            "Colheita": {"desc": "Fruto.", "fisio": "Açúcares e Aromas.", "manejo": "Diário.", "riscos": "Podridão.", "quim": "**Etoxazol (Grupo 10B):** Ovicida de ácaros.", "bio": "**Neoseiulus:** Ácaro predador."}
        }
    }
}

# --- 3. MOTORES DE CÁLCULO ---
def get_coords(city, key):
    try:
        url = f"http://api.openweathermap.org/geo/1.0/direct?q={city}&limit=1&appid={key}"
        r = requests.get(url).json()
        if r: return r[0]['lat'], r[0]['lon']
    except: return None, None

def calcular_gda_preciso(t_min, t_max, t_base, t_teto):
    # Método do Seno Simples ou Triangulação (Simplificado aqui pela média cortada)
    # Se a temperatura média estiver abaixo da base, GDA é 0.
    # Se estiver acima do teto, limita-se ao teto (estresse térmico não gera crescimento linear).
    t_media = (t_min + t_max) / 2
    if t_media < t_base:
        return 0
    elif t_media > t_teto:
        # Penalização por calor excessivo (Opcional, aqui mantemos o platô)
        return t_teto - t_base
    else:
        return t_media - t_base

def get_forecast(lat, lon, key, kc, t_base, t_teto=30):
    try:
        url = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={key}&units=metric&lang=pt_br"
        r = requests.get(url).json()
        dados = []
        if 'list' in r:
            for item in r['list']:
                t = item['main']['temp']
                t_min = item['main']['temp_min']
                t_max = item['main']['temp_max']
                u = item['main']['humidity']
                
                es = 0.61078 * math.exp((17.27 * t) / (t + 237.3))
                ea = es * (u / 100)
                vpd = max(0, round(es - ea, 2))
                
                # CÁLCULO GDA REGULADO (Por bloco de 3h, divide por 8 para ter a fração do dia)
                gda_bloco = calcular_gda_preciso(t_min, t_max, t_base, t_teto) / 8
                
                et0 = 0.0023 * (t + 17.8) * (t ** 0.5) * 0.408
                
                dados.append({
                    'Data': datetime.fromtimestamp(item['dt']),
                    'Temp': t,
                    'Umid': u,
                    'Chuva': item.get('rain', {}).get('3h', 0),
                    'VPD': vpd,
                    'GDA': gda_bloco,
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
    st.caption("Agro-Intel Enterprise v47.0")

# --- 5. LÓGICA DE INICIALIZAÇÃO ---
if 'lat' not in st.session_state: st.session_state.lat = -13.2000
if 'lon' not in st.session_state: st.session_state.lon = -41.4000

# ---------------------------------------------------------
#  ESTRUTURA DA PÁGINA (CAPA -> BARRA CLIMÁTICA -> PAINEL -> DADOS)
# ---------------------------------------------------------

# 1. ESPAÇO RESERVADO PARA A CAPA
header_placeholder = st.empty()

# 2. BARRA CLIMÁTICA HORIZONTAL (Placeholder)
climate_strip_placeholder = st.empty()

# 3. PAINEL DE CONTROLE
with st.container():
    st.markdown("<div class='control-panel'>", unsafe_allow_html=True)
    st.markdown("### ⚙️ Painel de Operação")
    c1, c2, c3 = st.columns(3)
    
    with c1:
        st.markdown("**📍 Localização da Propriedade**")
        tab_c, tab_g = st.tabs(["Cidade", "Coordenadas"])
        with tab_c:
            cid = st.text_input("Buscar Cidade:", placeholder="Ex: Mucugê, BA")
            if st.button("📍 Localizar") and api_w:
                nlat, nlon = get_coords(cid, api_w)
                if nlat: st.session_state.lat, st.session_state.lon = nlat, nlon; st.rerun()
        with tab_g:
            cl_a, cl_b = st.columns(2)
            st.session_state.lat = cl_a.number_input("Lat:", value=st.session_state.lat, format="%.4f")
            st.session_state.lon = cl_b.number_input("Lon:", value=st.session_state.lon, format="%.4f")
            
    with c2:
        st.markdown("**🌱 Configuração da Cultura**")
        cultura = st.selectbox("Selecione a Cultura:", list(BANCO_MASTER.keys()))
        variedade = st.selectbox("Variedade/Genética:", list(BANCO_MASTER[cultura]['vars'].keys()))
        fase = st.selectbox("Estágio Fenológico Atual:", list(BANCO_MASTER[cultura]['fases'].keys()))
        
    with c3:
        st.markdown("**📅 Planejamento**")
        dt_inicio = st.date_input("Data de Início/Plantio:", date(2025, 12, 1))
    st.markdown("</div>", unsafe_allow_html=True)

# 4. LÓGICA DE PROCESSAMENTO
if api_w:
    # Dados Seguros
    c_db = BANCO_MASTER[cultura]
    v_db = c_db['vars'][variedade]
    f_db = c_db['fases'][fase]
    
    # Previsão (Passando teto térmico agora)
    t_teto_crop = c_db.get('t_teto', 30) # Padrão 30 se não houver
    df = get_forecast(st.session_state.lat, st.session_state.lon, api_w, v_db['kc'], c_db['t_base'], t_teto_crop)
    
    if not df.empty:
        hoje = df.iloc[0]
        dias = (date.today() - dt_inicio).days
        gda_acum = dias * (df['GDA'].sum() / 5 * 8)
        
        # --- A. PREENCHER CAPA ---
        with header_placeholder.container():
            st.markdown(f"""
            <div class="app-cover">
                <h1 class="cover-title">Agro-Intel Enterprise</h1>
                <div class="cover-subtitle">Sistema Avançado de Suporte à Decisão Agronômica</div>
                <div class="data-grid">
                    <div class="info-tag">🌱 {cultura}</div>
                    <div class="info-tag">🧬 {variedade}</div>
                    <div class="info-tag">📅 {dias} dias de campo</div>
                    <div class="info-tag">🔥 {gda_acum:.0f} GDA (Calibrado)</div>
                </div>
                <div style="margin-top: 20px; font-size: 0.95em; opacity: 0.9; border-top: 1px solid rgba(255,255,255,0.2); padding-top: 15px;">
                    ℹ️ <b>Genética:</b> {v_db['info']}
                </div>
            </div>
            """, unsafe_allow_html=True)

        # --- B. PREENCHER BARRA CLIMÁTICA HORIZONTAL ---
        with climate_strip_placeholder.container():
            st.markdown(f"""
            <div class="climate-strip">
                <div class="climate-item">
                    <div class="climate-label">TEMPERATURA</div>
                    <div class="climate-value">{hoje['Temp']:.1f}°C</div>
                </div>
                <div class="climate-item">
                    <div class="climate-label">UMIDADE</div>
                    <div class="climate-value">{hoje['Umid']}%</div>
                </div>
                <div class="climate-item">
                    <div class="climate-label">CHUVA (3H)</div>
                    <div class="climate-value">{hoje['Chuva']} mm</div>
                </div>
                <div class="climate-item">
                    <div class="climate-label">DEMANDA (ETc)</div>
                    <div class="climate-value">{hoje['ETc']} mm</div>
                </div>
                 <div class="climate-item">
                    <div class="climate-label">VPD</div>
                    <div class="climate-value">{hoje['VPD']} kPa</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        # --- C. ABAS DE ANÁLISE ---
        tabs = st.tabs(["🎓 Consultoria Técnica", "📊 Clima & Água", "📡 Radar", "👁️ IA Vision", "🗺️ Mapa", "🚚 Logística"])

        # ABA 1: CONSULTORIA TÉCNICA
        with tabs[0]:
            st.markdown(f"### Diagnóstico Fenológico: {fase}")
            
            
            progresso = min(1.0, gda_acum/v_db['gda_meta'])
            st.progress(progresso)
            st.caption(f"Ciclo Térmico: {int(progresso*100)}% concluído")
            
            # Alerta de Risco com Lógica
            if hoje['Umid'] > 85:
                st.markdown(f"<div class='alert-box high-risk'>🚨 ALERTA CRÍTICO: Umidade > 85%. Condição favorável para doenças fúngicas severas.</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div class='alert-box low-risk'>✅ CONDIÇÃO SEGURA: Baixo risco de infecção no momento.</div>", unsafe_allow_html=True)
            
            

            col_esq, col_dir = st.columns(2)
            with col_esq:
                riscos_txt = f_db.get('riscos', 'Monitoramento Padrão')
                fisio_txt = f_db.get('fisio', 'Crescimento normal.')
                bio_txt = f_db.get('bio', 'Manter equilíbrio de solo.')
                
                st.markdown(f"""
                <div class="tech-card">
                    <h4>🧬 Fisiologia da Planta</h4>
                    <p>{fisio_txt}</p>
                    <p class="agro-explanation">Entender o processo interno da planta é vital para não aplicar produtos no momento errado.</p>
                    <hr>
                    <h4>⚠️ Principais Riscos</h4>
                    <p>{riscos_txt}</p>
                </div>
                <div class="bio-card">
                    <h4>🌿 Controle Biológico</h4>
                    <p>{bio_txt}</p>
                    <p class="agro-explanation">Estratégias para reduzir resistência de pragas.</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col_dir:
                desc_txt = f_db.get('desc', 'Fase atual.')
                manejo_txt = f_db.get('manejo', 'Monitorar irrigação.')
                quim_txt = f_db.get('quim', 'Consulte receituário agronômico.')
                
                st.markdown(f"""
                <div class="tech-card">
                    <h4>🚜 Ações Culturais</h4>
                    <p><b>Fase:</b> {desc_txt}</p>
                    <p><b>Prática Recomendada:</b> {manejo_txt}</p>
                </div>
                <div class="chem-card">
                    <h4>🧪 Controle Químico Profissional</h4>
                    <p>{quim_txt}</p>
                    <p class="agro-explanation">Princípios ativos sugeridos com base no alvo biológico e grupo químico.</p>
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
    # Caso não tenha chave, preenche o placeholder com capa genérica
    with header_placeholder.container():
        st.markdown(f"""
        <div class="app-cover">
            <h1 class="cover-title">Agro-Intel Enterprise</h1>
            <div class="cover-subtitle">Sistema Avançado de Suporte à Decisão Agronômica</div>
            <div style="margin-top:20px;">👈 Insira suas chaves de API para iniciar o monitoramento.</div>
        </div>
        """, unsafe_allow_html=True)
