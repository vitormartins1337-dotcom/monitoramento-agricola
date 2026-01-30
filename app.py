import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import requests
import math
import google.generativeai as genai
from PIL import Image
from datetime import datetime, date, timedelta
import folium
from folium.plugins import LocateControl, Fullscreen, Draw, MiniMap
from streamlit_folium import st_folium
import base64
import io

# ==============================================================================
# 1. ARQUITETURA E CONFIGURAÇÃO DO SISTEMA
# ==============================================================================
st.set_page_config(
    page_title="Agro-Intel Titan",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- CLASSE DE UTILITÁRIOS VISUAIS ---
class UIAssets:
    @staticmethod
    def get_base64(bin_file):
        try:
            with open(bin_file, 'rb') as f: data = f.read()
            return base64.b64encode(data).decode()
        except: return None

    @staticmethod
    def apply_enterprise_css(bg_image):
        bin_str = UIAssets.get_base64(bg_image)
        img_url = f"data:image/png;base64,{bin_str}" if bin_str else "https://images.unsplash.com/photo-1625246333195-78d9c38ad449?q=80&w=1740&auto=format&fit=crop"

        st.markdown(f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700;900&display=swap');
        
        /* RESET E FONTE GLOBAL */
        html, body, [class*="css"] {{
            font-family: 'Roboto', sans-serif;
            color: #1e293b;
        }}

        /* FUNDO COM SOBREPOSIÇÃO ESCURA PARA CONTRASTE */
        .stApp {{
            background-image: linear-gradient(rgba(15, 23, 42, 0.92), rgba(15, 23, 42, 0.96)), url("{img_url}");
            background-size: cover;
            background-attachment: fixed;
            background-position: center;
        }}

        /* CABEÇALHO TITANIUM */
        .titan-header {{
            background: linear-gradient(135deg, #0f2027 0%, #203a43 50%, #2c5364 100%);
            padding: 30px;
            border-radius: 12px;
            border-bottom: 6px solid #00e676;
            box-shadow: 0 10px 30px rgba(0,0,0,0.5);
            margin-bottom: 30px;
            text-align: center;
        }}
        .titan-title {{
            color: #fff; font-size: 3.5em; font-weight: 900; letter-spacing: -1px; margin: 0; text-transform: uppercase;
            text-shadow: 0 4px 10px rgba(0,0,0,0.3);
        }}
        .titan-sub {{ color: #b0bec5; font-size: 1.2em; font-weight: 400; letter-spacing: 2px; margin-top: 10px; }}

        /* CONTAINER DE CONTROLE (BRANCO SÓLIDO - ZERO TRANSPARÊNCIA) */
        .control-panel {{
            background-color: #ffffff;
            padding: 25px;
            border-radius: 10px;
            border: 1px solid #e2e8f0;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }}
        .panel-label {{ color: #64748b; font-size: 0.85em; font-weight: 700; text-transform: uppercase; margin-bottom: 5px; }}

        /* CARD DE DADOS TÉCNICOS (SOLID WHITE) */
        .tech-card {{
            background-color: #ffffff !important;
            opacity: 1 !important;
            padding: 30px;
            border-radius: 12px;
            border-left: 5px solid #0288d1;
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
            margin-bottom: 20px;
        }}
        
        .tech-header {{
            font-size: 1.5em; color: #0f172a; font-weight: 800; border-bottom: 2px solid #f1f5f9;
            padding-bottom: 15px; margin-bottom: 20px;
        }}

        .info-label {{ color: #64748b; font-size: 0.9em; font-weight: 700; text-transform: uppercase; margin-top: 15px; }}
        .info-value {{ color: #334155; font-size: 1.1em; line-height: 1.6; font-weight: 400; text-align: justify; }}

        /* LISTA QUÍMICA PROFISSIONAL */
        ul.chem-list {{ list-style: none; padding: 0; }}
        li.chem-item {{
            background: #f8fafc; border: 1px solid #e2e8f0; padding: 12px; margin-bottom: 8px; border-radius: 6px;
            display: flex; justify-content: space-between; align-items: center;
        }}
        .chem-name {{ font-weight: 700; color: #1e293b; }}
        .chem-meta {{ font-size: 0.85em; color: #64748b; background: #e2e8f0; padding: 2px 8px; border-radius: 12px; }}

        /* ALERTS */
        .alert-box {{ padding: 20px; border-radius: 8px; margin-bottom: 20px; font-weight: 500; }}
        .alert-danger {{ background: #fee2e2; color: #991b1b; border-left: 8px solid #ef4444; }}
        .alert-success {{ background: #dcfce7; color: #166534; border-left: 8px solid #22c55e; }}

        /* KPI CARDS */
        div[data-testid="metric-container"] {{
            background-color: #ffffff; border: 1px solid #cbd5e1; box-shadow: 0 4px 6px rgba(0,0,0,0.05);
            border-radius: 8px; padding: 15px;
        }}
        label[data-testid="stMetricLabel"] {{ color: #475569 !important; font-weight: 700 !important; }}
        div[data-testid="stMetricValue"] {{ color: #0f172a !important; font-weight: 800 !important; }}
        </style>
        """, unsafe_allow_html=True)

# Aplica CSS
UIAssets.apply_enterprise_css('fundo_agro.jpg')

# ==============================================================================
# 2. BANCO DE DADOS AGRONÔMICO OMNI (EXPANDIDO)
# ==============================================================================
# Estrutura completa para evitar erros de renderização
BANCO_TITAN = {
    # --- GRÃOS (COMMODITIES) ---
    "Soja (Glycine max)": {
        "t_base": 10,
        "vars": {
            "Intacta 2 Xtend": {"kc": 1.15, "gda_meta": 1400, "info": "Tecnologia I2X. Resistência a lagartas e herbicida Dicamba. Refúgio obrigatório."},
            "Brasmax": {"kc": 1.15, "gda_meta": 1350, "info": "Alto teto produtivo. Exige fertilidade corrigida (Sat. Bases > 60%)."},
            "Conkesta Enlist": {"kc": 1.15, "gda_meta": 1450, "info": "Sistema Enlist (2,4-D Colina). Tolerância a lagartas complexas."}
        },
        "fases": {
            "Emergência (VE)": {
                "desc": "Cotilédones acima do solo.",
                "fisiologia": "Início da autotrofia. Radícula pivotante em descida rápida. Sensível a compactação.",
                "manejo": "Monitorar Damping-off (Rhizoctonia/Pythium) e Lagarta Elasmo em solos arenosos.",
                "quimica": [
                    {"Alvo": "Damping-off", "Ativo": "Carboxina + Tiram", "Grupo": "Carboxamida", "Tipo": "Tratamento Sementes"},
                    {"Alvo": "Elasmo", "Ativo": "Fipronil", "Grupo": "Pirazol", "Tipo": "TS / Sulco"}
                ]
            },
            "Vegetativo (V3-V6)": {
                "desc": "Desenvolvimento de nós e folhas trifolioladas.",
                "fisiologia": "Estabelecimento da FBN (Fixação Biológica). Alta demanda de P e K.",
                "manejo": "Manejo de daninhas (Glifosato/Dicamba). Monitorar Lagartas (Helicoverpa/Spodoptera).",
                "quimica": [
                    {"Alvo": "Lagartas", "Ativo": "Benzoato de Emamectina", "Grupo": "Avermectina", "Tipo": "Ingestão"},
                    {"Alvo": "Lagartas", "Ativo": "Clorantraniliprole", "Grupo": "Diamida", "Tipo": "Sistêmico"},
                    {"Alvo": "Buva", "Ativo": "Diclosulam", "Grupo": "ALS", "Tipo": "Herbicida"}
                ]
            },
            "Reprodutivo (R1-R2)": {
                "desc": "Florescimento pleno.",
                "fisiologia": "Definição do número de vagens. Estresse hídrico causa abortamento severo.",
                "manejo": "Entrada de Fungicidas para Ferrugem Asiática (Phakopsora pachyrhizi).",
                "quimica": [
                    {"Alvo": "Ferrugem", "Ativo": "Protioconazol + Trifloxistrobina", "Grupo": "Triazol + Estrobilurina", "Tipo": "Sistêmico"},
                    {"Alvo": "Manchas", "Ativo": "Mancozebe", "Grupo": "Ditiocarbamato", "Tipo": "Protetor Multissítio"}
                ]
            },
            "Enchimento (R5)": {
                "desc": "Formação de grãos.",
                "fisiologia": "Máxima translocação. Definição do PMG (Peso de Mil Grãos).",
                "manejo": "Controle de Percevejos (Marrom/Verde) para evitar grão picado e retenção foliar.",
                "quimica": [
                    {"Alvo": "Percevejo", "Ativo": "Acefato", "Grupo": "Organofosforado", "Tipo": "Choque"},
                    {"Alvo": "Percevejo", "Ativo": "Tiametoxam + Lambda", "Grupo": "Neo + Piretroide", "Tipo": "Sistêmico"}
                ]
            }
        }
    },
    
    # --- FRUTAS VERMELHAS (BERRIES) ---
    "Amora Preta (Blackberry)": {
        "t_base": 7,
        "vars": {
            "Tupy": {"kc": 1.0, "gda_meta": 1500, "info": "Exige horas de frio. Alta produtividade. Presença de espinhos."},
            "BRS Xingu": {"kc": 1.05, "gda_meta": 1400, "info": "Cultivar sem espinhos. Facilita manejo e colheita."}
        },
        "fases": {
            "Brotação": {
                "desc": "Emissão de novas hastes produtivas.",
                "fisiologia": "Alta demanda de Nitrogênio para vigor.",
                "manejo": "Seleção de hastes. Monitoramento de Ferrugem.",
                "quimica": [
                    {"Alvo": "Ferrugem", "Ativo": "Tebuconazol", "Grupo": "Triazol", "Tipo": "Curativo"},
                    {"Alvo": "Cochonilha", "Ativo": "Óleo Mineral", "Grupo": "Físico", "Tipo": "Contato"}
                ]
            },
            "Frutificação": {
                "desc": "Formação e maturação de bagas.",
                "fisiologia": "Acúmulo de sólidos solúveis (Brix).",
                "manejo": "Controle de Drosophila suzukii (SWD) e Botrytis.",
                "quimica": [
                    {"Alvo": "SWD (Mosca)", "Ativo": "Espinosade", "Grupo": "Espinocina", "Tipo": "Isca Biológica"},
                    {"Alvo": "Botrytis", "Ativo": "Iprodiona", "Grupo": "Dicarboximida", "Tipo": "Contato"}
                ]
            }
        }
    },
    "Framboesa (Raspberry)": {
        "t_base": 7, "vars": {"Heritage": {"kc": 1.1, "gda_meta": 1300, "info": "Remontante (Produz na haste do ano)."}},
        "fases": {
            "Vegetativo": {"desc": "Crescimento de canas.", "fisiologia": "Estruturação.", "manejo": "Ácaro Vermelho.", "quimica": [{"Alvo": "Ácaro", "Ativo": "Abamectina", "Grupo": "Avermectina", "Tipo": "Translaminar"}]},
            "Produção": {"desc": "Flores e Frutos.", "fisiologia": "Sensível a chuva na flor.", "manejo": "Podridão Cinzenta.", "quimica": [{"Alvo": "Botrytis", "Ativo": "Ciprodinil + Fludioxonil", "Grupo": "Switch", "Tipo": "Sistêmico Local"}]}
        }
    },
    "Mirtilo (Blueberry)": {
        "t_base": 7, "vars": {"Emerald": {"kc": 0.95, "gda_meta": 1800, "info": "Exige pH ácido (4.5)."}},
        "fases": {
            "Florada": {"desc": "Polinização.", "fisiologia": "Dependente de mamangavas (Bombus).", "manejo": "Botrytis.", "quimica": [{"Alvo": "Botrytis", "Ativo": "Fludioxonil", "Grupo": "Fenilpirrol", "Tipo": "Contato"}]}
        }
    },
    "Morango": {
        "t_base": 7, "vars": {"Albion": {"kc": 0.85, "gda_meta": 1250, "info": "Dia neutro. Sabor excelente."}},
        "fases": {
            "Colheita": {"desc": "Produção contínua.", "fisiologia": "Alta extração K e Ca.", "manejo": "Ácaro Rajado e Mofo Cinzento.", "quimica": [{"Alvo": "Ácaro", "Ativo": "Etoxazol", "Grupo": "Inibidor de Crescimento", "Tipo": "Contato"}, {"Alvo": "Oídio", "Ativo": "Enxofre", "Grupo": "Inorgânico", "Tipo": "Protetor"}]}
        }
    },

    # --- HORTIFRUTI (HF) ---
    "Batata (Solanum tuberosum)": {
        "t_base": 7,
        "vars": {
            "Orchestra": {"kc": 1.15, "gda_meta": 1600, "info": "Pele lisa premium. Exige K para acabamento."},
            "Cupido": {"kc": 1.10, "gda_meta": 1400, "info": "Ciclo curto. Sensibilidade extrema à Requeima."},
            "Atlantic": {"kc": 1.15, "gda_meta": 1650, "info": "Indústria (Chips)."}
        },
        "fases": {
            "Estolonização": {
                "desc": "Crescimento vegetativo.",
                "fisiologia": "Alta demanda N.",
                "manejo": "Amontoa. Vaquinha (Diabrotica).",
                "quimica": [{"Alvo": "Vaquinha", "Ativo": "Tiametoxam", "Grupo": "Neonicotinoide", "Tipo": "Sistêmico"}]
            },
            "Tuberização": {
                "desc": "Início do Gancho.",
                "fisiologia": "Inversão hormonal. Crítico água.",
                "manejo": "Requeima (Phytophthora infestans).",
                "quimica": [
                    {"Alvo": "Requeima", "Ativo": "Metalaxil-M + Mancozeb", "Grupo": "Sistêmico + Protetor", "Tipo": "Curativo"},
                    {"Alvo": "Requeima", "Ativo": "Mandipropamida", "Grupo": "CAA", "Tipo": "Translaminar"}
                ]
            },
            "Enchimento": {
                "desc": "Engorda.",
                "fisiologia": "Translocação.",
                "manejo": "Traça (Phthorimaea) e Mosca Branca.",
                "quimica": [{"Alvo": "Traça", "Ativo": "Clorfenapir", "Grupo": "Pirrol", "Tipo": "Ingestão"}]
            }
        }
    },
    
    # --- CULTURAS TROPICAIS ---
    "Café (Coffea arabica)": {
        "t_base": 10, "vars": {"Catuaí": {"kc": 1.1, "gda_meta": 3000, "info": "Suscetível a ferrugem."}, "Arara": {"kc": 1.2, "gda_meta": 2900, "info": "Resistente a ferrugem."}},
        "fases": {
            "Chumbinho": {"desc": "Expansão rápida.", "fisiologia": "Divisão celular.", "manejo": "Ferrugem e Cercospora.", "quimica": [{"Alvo": "Ferrugem", "Ativo": "Ciproconazol + Azoxistrobina", "Grupo": "Triazol+Estrob", "Tipo": "Sistêmico"}]},
            "Granação": {"desc": "Enchimento de grão.", "fisiologia": "Sólidos.", "manejo": "Broca e Bicho Mineiro.", "quimica": [{"Alvo": "Broca", "Ativo": "Ciantraniliprole", "Grupo": "Diamida", "Tipo": "Sistêmico"}]}
        }
    },
    "Citros (Limão/Laranja)": {
        "t_base": 13, "vars": {"Tahiti": {"kc": 0.75, "gda_meta": 2000, "info": "Limão Ácido."}},
        "fases": {
            "Fluxo Vegetativo": {"desc": "Brotação.", "fisiologia": "Folhas novas.", "manejo": "Psilídeo (Greening) e Minadora.", "quimica": [{"Alvo": "Psilídeo", "Ativo": "Imidacloprido + Bifentrina", "Grupo": "Neo+Piretroide", "Tipo": "Choque"}]}
        }
    },
    "Manga": {
        "t_base": 13, "vars": {"Palmer": {"kc": 0.9, "gda_meta": 2800, "info": "Fibrosa."}},
        "fases": {
            "Florada": {"desc": "Panícula.", "fisiologia": "Polinização.", "manejo": "Oídio e Antracnose.", "quimica": [{"Alvo": "Oídio", "Ativo": "Enxofre", "Grupo": "Inorgânico", "Tipo": "Protetor"}]}
        }
    },
    "Uva": {
        "t_base": 10, "vars": {"Vitoria": {"kc": 0.85, "gda_meta": 1500, "info": "Sem semente."}},
        "fases": {
            "Maturação": {"desc": "Véraison (Mudança de cor).", "fisiologia": "Acúmulo de açúcar.", "manejo": "Podridão do Cacho.", "quimica": [{"Alvo": "Podridão", "Ativo": "Iprodiona", "Grupo": "Dicarboximida", "Tipo": "Contato"}]}
        }
    }
}

# ==============================================================================
# 3. MOTOR CIENTÍFICO (FÍSICA DE AMBIENTE)
# ==============================================================================
class AgroMath:
    @staticmethod
    def calc_vpd(temp, umid):
        es = 0.61078 * math.exp((17.27 * temp) / (temp + 237.3))
        ea = es * (umid / 100)
        return round(es - ea, 2)

    @staticmethod
    def calc_delta_t(temp, umid):
        tw = temp * math.atan(0.151977 * (umid + 8.313659)**0.5) + math.atan(temp + umid) - math.atan(umid - 1.676331) + 0.00391838 * (umid)**1.5 * math.atan(0.023101 * umid) - 4.686035
        return round(temp - tw, 1)

    @staticmethod
    def calc_etc(temp, kc):
        # Hargreaves-Samani adaptado para trópicos
        et0 = 0.0023 * (temp + 17.8) * (temp ** 0.5) * 0.408 * 23
        return round(et0 * kc, 2)

# ==============================================================================
# 4. CONECTIVIDADE & INTEGRAÇÃO
# ==============================================================================
def get_credentials():
    return st.query_params.get("w_key", None), st.query_params.get("g_key", None)

def get_coords(city, key):
    try:
        r = requests.get(f"http://api.openweathermap.org/geo/1.0/direct?q={city}&limit=1&appid={key}", timeout=5).json()
        if r: return r[0]['lat'], r[0]['lon']
    except: pass
    return None, None

def get_forecast(key, lat, lon, kc, t_base):
    try:
        r = requests.get(f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={key}&units=metric&lang=pt_br", timeout=5).json()
        data = []
        for i in range(0, 40, 8):
            item = r['list'][i]
            t = item['main']['temp']
            h = item['main']['humidity']
            data.append({
                'Data': datetime.fromtimestamp(item['dt']).strftime('%d/%m %Hh'),
                'Temp': t,
                'Umid': h,
                'VPD': AgroMath.calc_vpd(t, h),
                'Delta T': AgroMath.calc_delta_t(t, h),
                'ETc': AgroMath.calc_etc(t, kc),
                'GDA': max(0, t - t_base),
                'Chuva': sum([r['list'][i+j].get('rain', {}).get('3h', 0) for j in range(8) if i+j < len(r['list'])])
            })
        return pd.DataFrame(data)
    except: return pd.DataFrame()

def get_radar(key, lat, lon):
    pts = {"Norte": (lat+0.15, lon), "Sul": (lat-0.15, lon), "Leste": (lat, lon+0.15), "Oeste": (lat, lon-0.15)}
    res = []
    for d, c in pts.items():
        try:
            r = requests.get(f"https://api.openweathermap.org/data/2.5/weather?lat={c[0]}&lon={c[1]}&appid={key}&units=metric", timeout=3).json()
            res.append({"Dir": d, "Temp": r['main']['temp'], "Chuva": "Sim" if "rain" in r else "Não"})
        except: pass
    return pd.DataFrame(res)

def generate_pdf_report(cultura, variedade, fase, dias, hoje_data, recomendacoes):
    """Gera um relatório técnico PDF simplificado (Mockup funcional para o exemplo)"""
    # Em produção, usaria FPDF, mas aqui simulamos a lógica de exportação
    buffer = io.BytesIO()
    report_content = f"""
    RELATÓRIO TÉCNICO AGRO-INTEL TITAN
    ----------------------------------
    Data: {date.today()}
    Propriedade: Fazenda Progresso (Simulada)
    
    CULTURA: {cultura}
    VARIEDADE: {variedade}
    FASE ATUAL: {fase}
    IDADE: {dias} Dias
    
    CONDIÇÕES CLIMÁTICAS HOJE ({hoje_data['Data']}):
    - Temperatura: {hoje_data['Temp']} C
    - Umidade: {hoje_data['Umid']} %
    - VPD: {hoje_data['VPD']} kPa
    - Delta T: {hoje_data['Delta T']} C
    
    RECOMENDAÇÃO TÉCNICA:
    {recomendacoes}
    
    Gerado por Agro-Intel System v25.0
    """
    buffer.write(report_content.encode('utf-8'))
    buffer.seek(0)
    return buffer

# ==============================================================================
# 5. UI/UX PRINCIPAL
# ==============================================================================
url_w, url_g = get_credentials()

# --- HEADER EMPRESARIAL ---
st.markdown("""
<div class="titan-header">
    <h1 class="titan-title">Agro-Intel Titan</h1>
    <div class="titan-sub">Platforma de Inteligência Agronômica Integrada v25.0</div>
</div>
""", unsafe_allow_html=True)

# --- LOCK SCREEN (LOGIN) ---
if not url_w:
    st.markdown('<div class="tech-card" style="text-align:center;"><h3>🔒 Acesso Corporativo</h3><p>Insira suas credenciais de API para desbloquear o ERP.</p></div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([2,2,1])
    with c1: kw = st.text_input("OpenWeather Key", type="password")
    with c2: kg = st.text_input("Gemini AI Key", type="password")
    with c3: 
        st.write(""); st.write("")
        if st.button("AUTENTICAR", type="primary"): st.query_params["w_key"] = kw; st.query_params["g_key"] = kg; st.rerun()
    st.stop()

# --- PAINEL DE COMANDO ---
st.markdown('<div class="control-panel">', unsafe_allow_html=True)
c_loc, c_cult, c_time = st.columns([1.5, 1.5, 1])

# Estado Inicial
if 'loc_lat' not in st.session_state: st.session_state['loc_lat'] = -13.414
if 'loc_lon' not in st.session_state: st.session_state['loc_lon'] = -41.285
if 'pontos_mapa' not in st.session_state: st.session_state['pontos_mapa'] = []

with c_loc:
    st.markdown('<div class="panel-label">📍 GEOLOCALIZAÇÃO</div>', unsafe_allow_html=True)
    t1, t2 = st.tabs(["Busca", "Coordenadas"])
    with t1:
        city = st.text_input("Fazenda/Cidade:", placeholder="Ex: Cristalina, GO", label_visibility="collapsed")
        if st.button("Buscar") and city:
            lat, lon = get_coords(city, url_w)
            if lat: st.session_state['loc_lat'], st.session_state['loc_lon'] = lat, lon; st.rerun()
    with t2:
        c_lat, c_lon = st.columns(2)
        nlat = c_lat.number_input("Lat", value=st.session_state['loc_lat'], format="%.5f")
        nlon = c_lon.number_input("Lon", value=st.session_state['loc_lon'], format="%.5f")
        if st.button("Atualizar GPS"): st.session_state['loc_lat'], st.session_state['loc_lon'] = nlat, nlon; st.rerun()

with c_cult:
    st.markdown('<div class="panel-label">🚜 UNIDADE PRODUTIVA</div>', unsafe_allow_html=True)
    cult_sel = st.selectbox("Cultura", sorted(list(BANCO_TITAN.keys())))
    cv, cf = st.columns(2)
    var_sel = cv.selectbox("Material Genético", list(BANCO_TITAN[cult_sel]['vars'].keys()))
    fase_sel = cf.selectbox("Estágio Fenológico", list(BANCO_TITAN[cult_sel]['fases'].keys()))

with c_time:
    st.markdown('<div class="panel-label">📆 CRONOGRAMA</div>', unsafe_allow_html=True)
    if 'd_plantio' not in st.session_state: st.session_state['d_plantio'] = date(2025, 11, 25)
    dp = st.date_input("Início Safra", st.session_state['d_plantio'])
    dias = (date.today() - dp).days
    st.markdown(f"<h2 style='text-align:center; color:#333; margin:0;'>{dias} DIAS</h2>", unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# --- ENGINE DE PROCESSAMENTO ---
info = BANCO_TITAN[cult_sel]['vars'][var_sel]
dados = BANCO_TITAN[cult_sel]['fases'][fase_sel]
df = get_forecast(url_w, st.session_state['loc_lat'], st.session_state['loc_lon'], info['kc'], BANCO_TITAN[cult_sel]['t_base'])

if not df.empty:
    hoje = df.iloc[0]
    gda_acum = dias * df['GDA'].mean()
    progresso = min(1.0, gda_acum / info.get('gda_meta', 1500))
    
    # KPI STRIP
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("🌡️ Temperatura", f"{hoje['Temp']:.1f}°C", f"Umid: {hoje['Umid']}%")
    k2.metric("💧 VPD (Pressão)", f"{hoje['VPD']} kPa", "Estresse" if hoje['VPD'] > 1.3 else "Ideal", delta_color="inverse")
    k3.metric("💦 ETc (Demanda)", f"{hoje['ETc']} mm", f"Kc: {info['kc']}")
    k4.metric("🛡️ Delta T", f"{hoje['Delta T']}°C", "Não Aplicar" if hoje['Delta T'] < 2 or hoje['Delta T'] > 8 else "Aplicar", delta_color="inverse")
    
    # NAVIGATION
    tabs = st.tabs(["🎓 CONSULTORIA", "📊 CLIMATOLOGIA", "📡 RADAR", "👁️ IA VISION", "💰 CUSTOS", "🗺️ GIS MAP", "📄 RELATÓRIOS"])
    
    # --- ABA 1: CONSULTORIA TÉCNICA (DETALHADA) ---
    with tabs[0]:
        # Barra GDA
        st.write(f"**Acúmulo Térmico (GDA):** {gda_acum:.0f} / {info.get('gda_meta', 1500)}")
        st.progress(progresso)
        
        # Alertas Dinâmicos
        if hoje['Umid'] > 85 or hoje['Chuva'] > 2:
            st.markdown('<div class="alert-box alert-danger">🚨 ALERTA FITOSSANITÁRIO: Alta umidade favorece patógenos. Priorize fungicidas sistêmicos.</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="alert-box alert-success">✅ JANELA DE APLICAÇÃO: Condições favoráveis para protetores.</div>', unsafe_allow_html=True)

        c_left, c_right = st.columns(2)
        
        with c_left:
            st.markdown(f"""
            <div class="tech-card">
                <div class="tech-header">🧬 FISIOLOGIA & DESENVOLVIMENTO</div>
                <div class="info-label">DESCRIÇÃO DA FASE</div>
                <div class="info-value">{dados['desc']}</div>
                <div class="info-label">DINÂMICA FISIOLÓGICA</div>
                <div class="info-value">{dados['fisiologia']}</div>
                <div class="info-label">GENÉTICA ({var_sel})</div>
                <div class="info-value">{info['info']}</div>
            </div>
            """, unsafe_allow_html=True)
            
        with c_right:
            # Renderizador Seguro de Lista Química
            chem_html = ""
            if isinstance(dados['quimica'], list):
                for item in dados['quimica']:
                    chem_html += f"""
                    <li class="chem-item">
                        <div>
                            <span class="chem-name">{item['Alvo']}:</span> {item['Ativo']}
                        </div>
                        <span class="chem-meta">{item['Grupo']}</span>
                    </li>
                    """
            else:
                chem_html = f"<li>{dados['quimica']}</li>"

            st.markdown(f"""
            <div class="tech-card">
                <div class="tech-header">🛡️ ESTRATÉGIA DE MANEJO</div>
                <div class="info-label">MANEJO CULTURAL</div>
                <div class="info-value">{dados.get('manejo', '-')}</div>
                <hr style="margin:20px 0; border:0; border-top:1px solid #e2e8f0;">
                <div class="info-label">🧪 FARMÁCIA DIGITAL</div>
                <ul class="chem-list">{chem_html}</ul>
            </div>
            """, unsafe_allow_html=True)

    # --- ABA 2: CLIMATOLOGIA AVANÇADA ---
    with tabs[1]:
        st.markdown('<div class="tech-card">', unsafe_allow_html=True)
        fig = go.Figure()
        fig.add_trace(go.Bar(x=df['Data'], y=df['Chuva'], name='Precipitação (mm)', marker_color='#0288d1'))
        fig.add_trace(go.Scatter(x=df['Data'], y=df['ETc'], name='Evapotranspiração (mm)', line=dict(color='#d32f2f', width=3)))
        fig.update_layout(title="Balanço Hídrico (5 Dias)", template="plotly_white", height=400)
        st.plotly_chart(fig, use_container_width=True)
        
        col_res1, col_res2 = st.columns(2)
        col_res1.metric("Acumulado Chuva", f"{df['Chuva'].sum():.1f} mm")
        col_res2.metric("Déficit Hídrico", f"{df['Chuva'].sum() - df['ETc'].sum():.1f} mm")
        st.markdown('</div>', unsafe_allow_html=True)

    # --- ABA 3: RADAR REGIONAL ---
    with tabs[2]:
        st.markdown('<div class="tech-card">', unsafe_allow_html=True)
        st.markdown("### 📡 Estações Virtuais (Raio 15km)")
        dfr = get_radar(url_w, st.session_state['loc_lat'], st.session_state['loc_lon'])
        if not dfr.empty:
            cols = st.columns(4)
            for i, r in dfr.iterrows():
                bg = "#ffebee" if r['Chuva'] == "Sim" else "#e8f5e9"
                with cols[i]: st.markdown(f'<div style="background:{bg}; padding:20px; border-radius:10px; text-align:center; border:1px solid #ddd;"><b>{r["Dir"]}</b><br><span style="font-size:1.5em; font-weight:bold;">{r["Temp"]:.0f}°C</span><br>Chuva: {r["Chuva"]}</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # --- ABA 4: DIAGNÓSTICO IA ---
    with tabs[3]:
        st.markdown('<div class="tech-card">', unsafe_allow_html=True)
        c_cam, c_res = st.columns([1,2])
        with c_cam:
            img = st.camera_input("Capturar Imagem")
        with c_res:
            if img and url_g:
                genai.configure(api_key=url_g)
                with st.spinner("Processando diagnóstico neural..."):
                    res = genai.GenerativeModel('gemini-1.5-flash').generate_content([f"Agrônomo Sênior. Cultura {cult_sel}. Fase {fase_sel}. Identifique praga/doença com base visual e sugira controle.", Image.open(img)]).text
                    st.markdown(res)
        st.markdown('</div>', unsafe_allow_html=True)

    # --- ABA 5: GESTÃO DE CUSTOS ---
    with tabs[4]:
        st.markdown('<div class="tech-card">', unsafe_allow_html=True)
        if 'custos' not in st.session_state: st.session_state['custos'] = []
        c1, c2, c3 = st.columns([3, 1, 1])
        i = c1.text_input("Descrição do Insumo")
        v = c2.number_input("Valor (R$)", min_value=0.0)
        if c3.button("Lançar Custo"): 
            st.session_state['custos'].append({"Data": date.today(), "Item": i, "Valor": v})
            st.rerun()
        
        if st.session_state['custos']:
            df_custos = pd.DataFrame(st.session_state['custos'])
            st.dataframe(df_custos, use_container_width=True)
            st.metric("CUSTO TOTAL", f"R$ {df_custos['Valor'].sum():,.2f}")
        st.markdown('</div>', unsafe_allow_html=True)

    # --- ABA 6: MAPA GIS ---
    with tabs[5]:
        st.markdown('<div class="tech-card">', unsafe_allow_html=True)
        c1, c2 = st.columns([1,3])
        with c1:
            nm = st.text_input("Nome do Talhão")
            if st.button("Salvar Ponto") and st.session_state.get('last_click'):
                st.session_state['pontos_mapa'].append({"nome": nm, "lat": st.session_state['last_click'][0], "lon": st.session_state['last_click'][1]})
                st.rerun()
            for p in st.session_state['pontos_mapa']: st.write(f"📍 {p['nome']}")
            if st.button("Limpar Mapa"): st.session_state['pontos_mapa'] = []; st.rerun()
        
        with c2:
            m = folium.Map(location=[st.session_state['loc_lat'], st.session_state['loc_lon']], zoom_start=15)
            folium.TileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', attr='Esri', name='Satélite').add_to(m)
            LocateControl().add_to(m); Draw(export=True).add_to(m); Fullscreen().add_to(m)
            for p in st.session_state['pontos_mapa']: folium.Marker([p['lat'], p['lon']], popup=p['nome']).add_to(m)
            out = st_folium(m, height=500, returned_objects=["last_clicked"])
            if out["last_clicked"]: st.session_state['last_click'] = (out["last_clicked"]["lat"], out["last_clicked"]["lng"])
        st.markdown('</div>', unsafe_allow_html=True)

    # --- ABA 7: RELATÓRIOS (NOVO) ---
    with tabs[6]:
        st.markdown('<div class="tech-card">', unsafe_allow_html=True)
        st.subheader("📄 Emissão de Laudo Técnico")
        rec_text = f"Manejo: {dados.get('manejo', '')}. Químicos: {dados['quimica']}"
        pdf_file = generate_pdf_report(cult_sel, var_sel, fase_sel, dias, hoje, rec_text)
        
        st.download_button(
            label="⬇️ Baixar Laudo PDF",
            data=pdf_file,
            file_name=f"Laudo_{cult_sel}_{date.today()}.txt", # txt simulando PDF para demo
            mime="text/plain"
        )
        st.markdown('</div>', unsafe_allow_html=True)
