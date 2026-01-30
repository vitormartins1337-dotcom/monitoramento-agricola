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
from folium.plugins import LocateControl, Fullscreen, MiniMap, Draw
from streamlit_folium import st_folium
import base64
import random

# ==============================================================================
# 1. CONFIGURAÇÃO INICIAL E SISTEMA DE ARQUIVOS
# ==============================================================================
st.set_page_config(
    page_title="Agro-Intel Enterprise",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ==============================================================================
# 2. MOTOR VISUAL (CSS AVANÇADO & CONTRASTE)
# ==============================================================================
def get_base64_of_bin_file(bin_file):
    """Converte imagem local para Base64 para uso no CSS."""
    try:
        with open(bin_file, 'rb') as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except:
        return None

def set_background_and_style(png_file):
    """
    Define o background com sobreposição escura para contraste
    e estiliza os containers para parecerem um software desktop.
    """
    bin_str = get_base64_of_bin_file(png_file)
    if bin_str:
        img_url = f"data:image/png;base64,{bin_str}"
    else:
        # Fallback profissional (Imagem de Satélite/Agro)
        img_url = "https://images.unsplash.com/photo-1625246333195-78d9c38ad449?q=80&w=1740&auto=format&fit=crop"

    st.markdown(f'''
    <style>
    /* IMPORTANDO FONTES MODERNAS */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&display=swap');

    html, body, [class*="css"] {{
        font-family: 'Inter', sans-serif;
    }}

    /* FUNDO COM MÁSCARA ESCURA (CONTRASTE MÁXIMO) */
    .stApp {{
        background-image: linear-gradient(rgba(15, 23, 42, 0.85), rgba(15, 23, 42, 0.95)), url("{img_url}");
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
    }}

    /* CONTAINER PRINCIPAL (CONTROLE) */
    .control-panel {{
        background-color: #ffffff;
        padding: 25px;
        border-radius: 12px;
        border-top: 6px solid #1565c0;
        box-shadow: 0 10px 25px rgba(0,0,0,0.3);
        margin-bottom: 30px;
    }}

    /* CABEÇALHOS */
    .header-title {{
        color: #ffffff;
        font-size: 2.8em;
        font-weight: 800;
        text-shadow: 0px 2px 4px rgba(0,0,0,0.5);
        margin-bottom: 5px;
    }}
    .header-subtitle {{
        color: #94a3b8;
        font-size: 1.2em;
        font-weight: 400;
        margin-bottom: 25px;
    }}

    /* CARTÕES DE CONTEÚDO (ALTA OPACIDADE) */
    .tech-card {{
        background-color: rgba(255, 255, 255, 0.98); /* Quase sólido */
        padding: 30px;
        border-radius: 10px;
        border: 1px solid #e2e8f0;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        color: #0f172a; /* Texto Escuro */
    }}

    .tech-header {{
        color: #0369a1;
        font-weight: 800;
        font-size: 1.4em;
        border-bottom: 3px solid #f1f5f9;
        padding-bottom: 12px;
        margin-bottom: 20px;
    }}

    .tech-sub {{
        color: #475569;
        font-weight: 700;
        font-size: 1.0em;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-top: 20px;
        margin-bottom: 8px;
    }}

    .tech-text {{
        color: #334155;
        font-size: 1.05em;
        line-height: 1.6;
        text-align: justify;
    }}

    /* ALERTAS VISUAIS */
    .alert-high {{
        background-color: #fee2e2;
        border-left: 8px solid #dc2626;
        padding: 20px;
        border-radius: 6px;
        color: #7f1d1d;
        font-weight: 600;
    }}
    .alert-low {{
        background-color: #dcfce7;
        border-left: 8px solid #16a34a;
        padding: 20px;
        border-radius: 6px;
        color: #14532d;
        font-weight: 600;
    }}

    /* KPIs */
    div[data-testid="metric-container"] {{
        background-color: #ffffff;
        border: 1px solid #cbd5e1;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        border-radius: 8px;
        padding: 15px;
    }}
    
    label {{
        font-weight: 600 !important;
        color: #334155 !important;
    }}
    </style>
    ''', unsafe_allow_html=True)

# Aplica o estilo (Certifique-se de ter a imagem 'fundo_agro.jpg' ou ele usará a online)
set_background_and_style('fundo_agro.jpg')


# ==============================================================================
# 3. ENCICLOPÉDIA AGRONÔMICA DETALHADA (BASE DE DADOS ROBUSTA)
# ==============================================================================
# Expansão Massiva de Dados Químicos e Biológicos
BANCO_MASTER = {
    # -------------------------------------------------------------------------
    # GRUPO 1: COMMODITIES (GRÃOS & FIBRAS)
    # -------------------------------------------------------------------------
    "Soja (Glycine max)": {
        "t_base": 10,
        "vars": {
            "Intacta 2 Xtend": {
                "kc": 1.15, "gda_meta": 1400, 
                "info": "Tecnologia I2X. Resistência a lagartas e herbicida Dicamba. Exige refúgio estruturado."
            },
            "Brasmax": {
                "kc": 1.15, "gda_meta": 1350, 
                "info": "Alto teto produtivo. Exige perfil de solo corrigido (Sat. Bases > 60%)."
            },
            "Conkesta Enlist": {
                "kc": 1.15, "gda_meta": 1450, 
                "info": "Sistema Enlist (2,4-D Colina + Glifosato + Glufosinato). Tolerância a lagartas."
            }
        },
        "fases": {
            "Emergência (VE)": {
                "desc": "Cotilédones acima do solo.",
                "fisiologia": "Início da autotrofia. Radícula pivotante em descida rápida.",
                "manejo": "Monitorar Damping-off (Rhizoctonia/Pythium) e Lagarta Elasmo.",
                "quimica": [
                    {"Alvo": "Damping-off", "Ativo": "Carboxina + Tiram", "Grupo": "Carboxamida", "Tipo": "TS"},
                    {"Alvo": "Elasmo", "Ativo": "Fipronil", "Grupo": "Pirazol", "Tipo": "TS"}
                ]
            },
            "Vegetativo (V3-V6)": {
                "desc": "Desenvolvimento de nós e folhas trifolioladas.",
                "fisiologia": "Estabelecimento da FBN (Fixação Biológica de Nitrogênio). Não aplicar Nitrogênio mineral.",
                "manejo": "Aplicação de Glifosato (se RR). Monitorar Lagartas (Helicoverpa/Spodoptera).",
                "quimica": [
                    {"Alvo": "Lagartas", "Ativo": "Benzoato de Emamectina", "Grupo": "Avermectina", "Tipo": "Ingestão"},
                    {"Alvo": "Lagartas", "Ativo": "Clorantraniliprole", "Grupo": "Diamida", "Tipo": "Sistêmico"},
                    {"Alvo": "Buva", "Ativo": "Diclosulam", "Grupo": "ALS", "Tipo": "Herbicida"}
                ]
            },
            "Reprodutivo (R1-R2)": {
                "desc": "Início do florescimento pleno.",
                "fisiologia": "Dreno de fotoassimilados muda para as flores. Fase crítica para abortamento.",
                "manejo": "Entrada preventiva para Ferrugem Asiática (Phakopsora).",
                "quimica": [
                    {"Alvo": "Ferrugem", "Ativo": "Protioconazol + Trifloxistrobina", "Grupo": "Triazol + Estrobilurina", "Tipo": "Sistêmico"},
                    {"Alvo": "Ferrugem", "Ativo": "Mancozebe", "Grupo": "Ditiocarbamato", "Tipo": "Protetor"}
                ]
            },
            "Enchimento (R5)": {
                "desc": "Máxima formação de grãos.",
                "fisiologia": "Translocação intensa. Peso de Mil Grãos (PMG) é definido aqui.",
                "manejo": "Controle rigoroso de Percevejos (Marrom/Verde). Dano direto no grão.",
                "quimica": [
                    {"Alvo": "Percevejo", "Ativo": "Acefato", "Grupo": "Organofosforado", "Tipo": "Choque"},
                    {"Alvo": "Percevejo", "Ativo": "Tiametoxam + Lambda-Cialotrina", "Grupo": "Neo + Piretroide", "Tipo": "Sistêmico"}
                ]
            }
        }
    },
    
    # -------------------------------------------------------------------------
    # GRUPO 2: HF & ESPECIAIS (ALTO VALOR AGREGADO)
    # -------------------------------------------------------------------------
    "Batata (Solanum tuberosum)": {
        "t_base": 7,
        "vars": {
            "Orchestra": {"kc": 1.15, "gda_meta": 1600, "info": "Pele lisa. Exige K e Ca. Sensível a Alternaria."},
            "Cupido": {"kc": 1.10, "gda_meta": 1400, "info": "Ciclo curto. Sensibilidade extrema à Requeima."},
            "Atlantic": {"kc": 1.15, "gda_meta": 1650, "info": "Indústria (Chips). Monitorar Coração Oco."}
        },
        "fases": {
            "Emergência": {
                "desc": "Brotamento e Enraizamento.",
                "fisiologia": "Dreno de reservas da batata-mãe. Raízes frágeis.",
                "manejo": "Solo friável. Evitar encharcamento (Pectobacterium).",
                "quimica": [
                    {"Alvo": "Rizoctonia", "Ativo": "Azoxistrobina", "Grupo": "Estrobilurina", "Tipo": "Sulco"},
                    {"Alvo": "Minadora", "Ativo": "Ciromazina", "Grupo": "Regulador", "Tipo": "Foliar"}
                ]
            },
            "Estolonização": {
                "desc": "Crescimento vegetativo.",
                "fisiologia": "Alta demanda de N para IAF.",
                "manejo": "Amontoa. Monitorar Vaquinha (Diabrotica).",
                "quimica": [
                    {"Alvo": "Requeima", "Ativo": "Mancozeb", "Grupo": "Ditiocarbamato", "Tipo": "Protetor"},
                    {"Alvo": "Vaquinha", "Ativo": "Tiametoxam", "Grupo": "Neonicotinoide", "Tipo": "Sistêmico"}
                ]
            },
            "Tuberização": {
                "desc": "Início do Gancho (Crítico).",
                "fisiologia": "Queda de Giberelina. Estresse causa Sarna.",
                "manejo": "Irrigação constante. Controle de Requeima.",
                "quimica": [
                    {"Alvo": "Requeima", "Ativo": "Metalaxil-M", "Grupo": "Fenilamida", "Tipo": "Curativo"},
                    {"Alvo": "Requeima", "Ativo": "Mandipropamida", "Grupo": "Amida", "Tipo": "Translaminar"}
                ]
            },
            "Enchimento": {
                "desc": "Engorda dos tubérculos.",
                "fisiologia": "Dreno de K e Mg.",
                "manejo": "Monitorar Traça e Mosca Branca.",
                "quimica": [
                    {"Alvo": "Traça", "Ativo": "Clorfenapir", "Grupo": "Pirrol", "Tipo": "Ingestão"},
                    {"Alvo": "Mosca Branca", "Ativo": "Ciantraniliprole", "Grupo": "Diamida", "Tipo": "Sistêmico"}
                ]
            }
        }
    },

    "Tomate (Solanum lycopersicum)": {
        "t_base": 10,
        "vars": {
            "Italiano": {"kc": 1.2, "gda_meta": 1600, "info": "Determinado. Sensível a Fundo Preto."},
            "Grape": {"kc": 1.1, "gda_meta": 1450, "info": "Indeterminado. Sensível a Rachadura."}
        },
        "fases": {
            "Vegetativo": {
                "desc": "Crescimento de hastes.",
                "fisiologia": "Formação estrutural.",
                "manejo": "Desbrota. Tripes (TSWV).",
                "quimica": [
                    {"Alvo": "Tripes", "Ativo": "Espinetoram", "Grupo": "Espinocina", "Tipo": "Choque"},
                    {"Alvo": "Bacteriose", "Ativo": "Cobre + Kasugamicina", "Grupo": "Antibiótico", "Tipo": "Protetor"}
                ]
            },
            "Frutificação": {
                "desc": "Formação de frutos.",
                "fisiologia": "Alta demanda de Cálcio.",
                "manejo": "Traça (Tuta absoluta) e Requeima.",
                "quimica": [
                    {"Alvo": "Tuta absoluta", "Ativo": "Indoxacarbe", "Grupo": "Oxadiazina", "Tipo": "Ingestão"},
                    {"Alvo": "Requeima", "Ativo": "Zoxamida", "Grupo": "Benzamida", "Tipo": "Protetor Forte"}
                ]
            }
        }
    },

    # -------------------------------------------------------------------------
    # GRUPO 3: PERENES & FRUTAS (CAFÉ, CITROS, BERRIES)
    # -------------------------------------------------------------------------
    "Café (Coffea arabica)": {
        "t_base": 10,
        "vars": {
            "Catuaí": {"kc": 1.1, "gda_meta": 3000, "info": "Bebida fina. Suscetível a ferrugem."},
            "Arara": {"kc": 1.2, "gda_meta": 2900, "info": "Resistente a ferrugem. Alta carga."}
        },
        "fases": {
            "Florada": {
                "desc": "Antese.",
                "fisiologia": "Viabilidade do pólen (Boro).",
                "manejo": "Phoma e Mancha Aureolada.",
                "quimica": [
                    {"Alvo": "Phoma", "Ativo": "Boscalida", "Grupo": "Carboxamida", "Tipo": "Sistêmico"},
                    {"Alvo": "Florada", "Ativo": "Cálcio + Boro", "Grupo": "Nutrição", "Tipo": "Foliar"}
                ]
            },
            "Chumbinho": {
                "desc": "Expansão.",
                "fisiologia": "Divisão celular. Déficit hídrico fatal.",
                "manejo": "Ferrugem e Cercospora.",
                "quimica": [
                    {"Alvo": "Ferrugem", "Ativo": "Ciproconazol + Azoxistrobina", "Grupo": "Triazol+Estrobilurina", "Tipo": "Sistêmico"}
                ]
            },
            "Granação": {
                "desc": "Enchimento.",
                "fisiologia": "Dreno de N e K.",
                "manejo": "Broca e Bicho Mineiro.",
                "quimica": [
                    {"Alvo": "Broca", "Ativo": "Ciantraniliprole", "Grupo": "Diamida", "Tipo": "Sistêmico"},
                    {"Alvo": "Mineiro", "Ativo": "Clorpirifós", "Grupo": "Organofosforado", "Tipo": "Contato/Vapor"}
                ]
            }
        }
    },

    "Amora Preta (Blackberry)": {
        "t_base": 7,
        "vars": {
            "Tupy": {"kc": 1.0, "gda_meta": 1500, "info": "Exige frio. Espinhos."},
            "BRS Xingu": {"kc": 1.05, "gda_meta": 1400, "info": "Sem espinhos."}
        },
        "fases": {
            "Brotação": {
                "desc": "Hastes novas.",
                "fisiologia": "Vigor vegetativo.",
                "manejo": "Ferrugem.",
                "quimica": [
                    {"Alvo": "Ferrugem", "Ativo": "Tebuconazol", "Grupo": "Triazol", "Tipo": "Curativo"}
                ]
            },
            "Frutificação": {
                "desc": "Bagas.",
                "fisiologia": "Açúcar.",
                "manejo": "Drosófila (SWD).",
                "quimica": [
                    {"Alvo": "SWD", "Ativo": "Espinosade", "Grupo": "Espinocina", "Tipo": "Isca Tóxica"}
                ]
            }
        }
    },

    "Framboesa (Raspberry)": {
        "t_base": 7,
        "vars": {"Heritage": {"kc": 1.1, "gda_meta": 1300, "info": "Remontante."}},
        "fases": {
            "Brotação": {
                "desc": "Hastes.",
                "fisiologia": "Vigor.",
                "manejo": "Ácaro Vermelho.",
                "quimica": [{"Alvo": "Ácaro", "Ativo": "Abamectina", "Grupo": "Avermectina", "Tipo": "Translaminar"}]
            },
            "Florada": {
                "desc": "Flores.",
                "fisiologia": "Sensível chuva.",
                "manejo": "Podridão (Botrytis).",
                "quimica": [{"Alvo": "Botrytis", "Ativo": "Iprodiona", "Grupo": "Dicarboximida", "Tipo": "Contato"}]
            }
        }
    },

    "Mirtilo (Blueberry)": {
        "t_base": 7, "vars": {"Emerald": {"kc": 0.95, "gda_meta": 1800, "info": "pH 4.5."}},
        "fases": {
            "Florada": {
                "desc": "Polinização.", "fisiologia": "Abelhas.", "manejo": "Botrytis.",
                "quimica": [{"Alvo": "Botrytis", "Ativo": "Fludioxonil", "Grupo": "Fenilpirrol", "Tipo": "Contato"}]
            }
        }
    },
    
    "Citros": {
        "t_base": 13, "vars": {"Tahiti": {"kc": 0.75, "gda_meta": 2000, "info": "Limão Ácido."}},
        "fases": {
            "Fluxo Vegetativo": {
                "desc": "Folhas novas.", "fisiologia": "Atrativo para vetores.", "manejo": "Psilídeo (Greening).",
                "quimica": [{"Alvo": "Psilídeo", "Ativo": "Bifentrina + Imidacloprido", "Grupo": "Piretroide+Neo", "Tipo": "Sistêmico"}]
            }
        }
    },

    "Uva": {
        "t_base": 10, "vars": {"Vitoria": {"kc": 0.85, "gda_meta": 1500, "info": "Sem semente."}},
        "fases": {
            "Brotação": {
                "desc": "Gema.", "fisiologia": "Reservas.", "manejo": "Míldio e Oídio.",
                "quimica": [{"Alvo": "Míldio", "Ativo": "Metalaxil-M", "Grupo": "Fenilamida", "Tipo": "Sistêmico"}]
            }
        }
    }
}

# ==============================================================================
# 4. MOTOR DE CÁLCULO CIENTÍFICO (FÍSICA DE AMBIENTE)
# ==============================================================================
def calculate_saturation_vapor_pressure(temp):
    """Calcula Es (Pressão de Saturação) em kPa."""
    return 0.61078 * math.exp((17.27 * temp) / (temp + 237.3))

def calculate_actual_vapor_pressure(temp, humidity):
    """Calcula Ea (Pressão Atual) em kPa."""
    es = calculate_saturation_vapor_pressure(temp)
    return es * (humidity / 100)

def calculate_vpd(temp, humidity):
    """Déficit de Pressão de Vapor (kPa)."""
    es = calculate_saturation_vapor_pressure(temp)
    ea = calculate_actual_vapor_pressure(temp, humidity)
    return round(es - ea, 2)

def calculate_dew_point(temp, humidity):
    """Ponto de Orvalho (Dew Point)."""
    a = 17.27
    b = 237.7
    alpha = ((a * temp) / (b + temp)) + math.log(humidity / 100.0)
    return round((b * alpha) / (a - alpha), 1)

def calculate_delta_t(temp, humidity):
    """Delta T para Pulverização (°C)."""
    tw = temp * math.atan(0.151977 * (humidity + 8.313659)**0.5) + math.atan(temp + humidity) - math.atan(humidity - 1.676331) + 0.00391838 * (humidity)**1.5 * math.atan(0.023101 * humidity) - 4.686035
    return round(temp - tw, 1)

def calculate_gda(temp_avg, t_base):
    """Graus Dia Acumulados."""
    return max(0, temp_avg - t_base)

def calculate_etc(temp, kc):
    """Evapotranspiração da Cultura (Hargreaves-Samani simplificado)."""
    # ET0 Estimado para região tropical
    et0 = 0.0023 * (temp + 17.8) * (temp ** 0.5) * 0.408 * 25 # 25MJ aprox radiação
    return round(et0 * kc, 2)

# ==============================================================================
# 5. CONECTIVIDADE API (INTEGRAÇÃO EXTERNA)
# ==============================================================================
def get_credentials():
    return st.query_params.get("w_key", None), st.query_params.get("g_key", None)

def get_coords_from_city(city_name, api_key):
    try:
        url = f"http://api.openweathermap.org/geo/1.0/direct?q={city_name}&limit=1&appid={api_key}"
        r = requests.get(url, timeout=5).json()
        if r:
            return r[0]['lat'], r[0]['lon']
    except Exception as e:
        st.error(f"Erro na geolocalização: {e}")
    return None, None

def get_weather_forecast(api_key, lat, lon, kc, t_base):
    try:
        url = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={api_key}&units=metric&lang=pt_br"
        r = requests.get(url, timeout=5).json()
        
        data_list = []
        for i in range(0, 40, 8): # Pega um ponto por dia (aprox)
            item = r['list'][i]
            t = item['main']['temp']
            h = item['main']['humidity']
            
            # Cálculos avançados
            dt = calculate_delta_t(t, h)
            vpd = calculate_vpd(t, h)
            gda = calculate_gda(t, t_base)
            etc = calculate_etc(t, kc)
            
            # Chuva acumulada 24h (8 blocos de 3h)
            chuva_acc = 0
            for j in range(8):
                if i+j < len(r['list']):
                    chuva_acc += r['list'][i+j].get('rain', {}).get('3h', 0)
            
            data_list.append({
                'Data': datetime.fromtimestamp(item['dt']).strftime('%d/%m'),
                'Temp': t,
                'Umid': h,
                'Chuva': round(chuva_acc, 1),
                'VPD': vpd,
                'Delta T': dt,
                'GDA': gda,
                'ETc': etc
            })
        return pd.DataFrame(data_list)
    except:
        return pd.DataFrame()

def get_radar_simulation(api_key, lat, lon):
    """Simula dados de estações virtuais a 15km."""
    offsets = [
        ("Norte", 0.15, 0),
        ("Sul", -0.15, 0),
        ("Leste", 0, 0.15),
        ("Oeste", 0, -0.15)
    ]
    results = []
    for name, lat_off, lon_off in offsets:
        try:
            url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat+lat_off}&lon={lon+lon_off}&appid={api_key}&units=metric&lang=pt_br"
            r = requests.get(url, timeout=3).json()
            is_raining = "rain" in r or "chuva" in r['weather'][0]['description'].lower()
            results.append({
                "Direcao": name,
                "Temp": r['main']['temp'],
                "Condicao": r['weather'][0]['description'].title(),
                "Chuva": "Sim" if is_raining else "Não"
            })
        except:
            pass
    return pd.DataFrame(results)

# ==============================================================================
# 6. INTERFACE DE USUÁRIO (FRONTEND)
# ==============================================================================

# --- Setup de Sessão ---
url_w, url_g = get_credentials()
if 'loc_lat' not in st.session_state: st.session_state['loc_lat'] = -13.414
if 'loc_lon' not in st.session_state: st.session_state['loc_lon'] = -41.285
if 'pontos_mapa' not in st.session_state: st.session_state['pontos_mapa'] = []
if 'd_plantio' not in st.session_state: st.session_state['d_plantio'] = date(2025, 11, 25)

# --- Header ---
st.markdown('<div class="header-title">Agro-Intel System</div>', unsafe_allow_html=True)
st.markdown('<div class="header-subtitle">Plataforma Enterprise de Gestão Agronômica (v23.0)</div>', unsafe_allow_html=True)

# --- Bloqueio de Login ---
if not url_w:
    st.markdown('<div class="tech-card"><h3>🔒 Acesso Restrito</h3><p>Entre com suas credenciais corporativas.</p></div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([2, 2, 1])
    with c1: key_w = st.text_input("OpenWeather API Key", type="password")
    with c2: key_g = st.text_input("Gemini AI API Key", type="password")
    with c3:
        st.write("") # Spacer
        st.write("") 
        if st.button("Autenticar Sistema", type="primary"):
            st.query_params["w_key"] = key_w
            st.query_params["g_key"] = key_g
            st.rerun()
    st.stop()

# --- PAINEL DE COMANDO CENTRAL (DASHBOARD) ---
st.markdown('<div class="control-panel">', unsafe_allow_html=True)
col_local, col_cultura, col_ciclo = st.columns([1.5, 1.5, 1])

with col_local:
    st.subheader("📍 Geolocalização")
    t_city, t_gps = st.tabs(["Por Cidade", "Coordenadas"])
    with t_city:
        city_input = st.text_input("Cidade/Fazenda:", placeholder="Ex: Rio Verde, GO")
        if st.button("🔍 Buscar Local") and city_input:
            lat, lon = get_coords_from_city(city_input, url_w)
            if lat:
                st.session_state['loc_lat'], st.session_state['loc_lon'] = lat, lon
                st.success(f"Localizado: {lat:.4f}, {lon:.4f}")
                st.rerun()
    with t_gps:
        clat, clon = st.columns(2)
        nlat = clat.number_input("Latitude", value=st.session_state['loc_lat'], format="%.5f")
        nlon = clon.number_input("Longitude", value=st.session_state['loc_lon'], format="%.5f")
        if st.button("Atualizar Posição"):
            st.session_state['loc_lat'], st.session_state['loc_lon'] = nlat, nlon
            st.rerun()

with col_cultura:
    st.subheader("🚜 Configuração da Lavoura")
    lista_culturas = sorted(list(BANCO_MASTER.keys()))
    sel_cultura = st.selectbox("Cultura:", lista_culturas)
    
    col_v, col_f = st.columns(2)
    vars_disponiveis = list(BANCO_MASTER[sel_cultura]['vars'].keys())
    sel_var = col_v.selectbox("Variedade/Híbrido:", vars_disponiveis)
    
    fases_disponiveis = list(BANCO_MASTER[sel_cultura]['fases'].keys())
    sel_fase = col_f.selectbox("Estágio Fenológico:", fases_disponiveis)

with col_ciclo:
    st.subheader("📆 Cronograma")
    d_plantio = st.date_input("Data de Início:", st.session_state['d_plantio'])
    st.session_state['d_plantio'] = d_plantio
    dias_corridos = (date.today() - d_plantio).days
    st.metric("Idade da Lavoura", f"{dias_corridos} dias")

st.markdown('</div>', unsafe_allow_html=True)

# --- PROCESSAMENTO PRINCIPAL ---
info_cultura = BANCO_MASTER[sel_cultura]['vars'][sel_var]
dados_fase = BANCO_MASTER[sel_cultura]['fases'][sel_fase]

# Busca Previsão
df_previsao = get_weather_forecast(url_w, st.session_state['loc_lat'], st.session_state['loc_lon'], info_cultura['kc'], BANCO_MASTER[sel_cultura]['t_base'])

if not df_previsao.empty:
    hoje = df_previsao.iloc[0]
    
    # Cálculo GDA Acumulado Estimado
    gda_acumulado = dias_corridos * df_previsao['GDA'].mean()
    meta_gda = info_cultura.get('gda_meta', 1500)
    progresso_gda = min(1.0, gda_acumulado / meta_gda)

    # --- KPI STRIP ---
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("🌡️ Temperatura (Agora)", f"{hoje['Temp']:.1f}°C", f"Umid: {hoje['Umid']}%")
    
    delta_vpd = "Ideal" if 0.4 <= hoje['VPD'] <= 1.3 else "Estresse"
    k2.metric("💧 VPD (Pressão)", f"{hoje['VPD']} kPa", delta_vpd, delta_color="normal" if delta_vpd == "Ideal" else "inverse")
    
    k3.metric("💦 ETc (Demanda)", f"{hoje['ETc']} mm/dia", f"Kc: {info_cultura['kc']}")
    
    status_dt = "Ideal" if 2 <= hoje['Delta T'] <= 8 else "Inadequado"
    k4.metric("🛡️ Delta T (Pulverização)", f"{hoje['Delta T']}°C", status_dt, delta_color="normal" if status_dt == "Ideal" else "inverse")

    st.write("") # Spacer

    # --- NAVEGAÇÃO POR ABAS (MAIN CONTENT) ---
    tabs = st.tabs([
        "🎓 Consultoria Técnica", 
        "📊 Clima & Irrigação", 
        "📡 Radar Meteorológico", 
        "👁️ Diagnóstico IA", 
        "💰 Gestão de Custos", 
        "🗺️ Mapa Operacional"
    ])

    # --------------------------------------------------------------------------
    # ABA 1: CONSULTORIA TÉCNICA (CORE)
    # --------------------------------------------------------------------------
    with tabs[0]:
        # Barra de Progresso GDA
        st.markdown(f"**Progresso de Maturação Térmica (GDA):** {gda_acumulado:.0f} de {meta_gda} GDA acumulados.")
        st.progress(progresso_gda)
        
        # Alerta Fitossanitário Dinâmico
        risco_clima = "Baixo"
        if hoje['Umid'] > 85 or hoje['Chuva'] > 5:
            st.markdown("""
            <div class="alert-high">
                🚨 ALERTA CRÍTICO: Alta umidade detectada.
                <br>Condições favoráveis para esporulação fúngica e bacteriose.
                <br>Recomendação: Suspender produtos de contato. Utilizar sistêmicos/penetrantes.
            </div>
            """, unsafe_allow_html=True)
        elif hoje['Delta T'] < 2 or hoje['Delta T'] > 8:
             st.markdown("""
            <div class="alert-high">
                ⚠️ ALERTA DE APLICAÇÃO: Delta T fora da janela ideal.
                <br>Risco de deriva (DT < 2) ou evaporação rápida (DT > 8).
                <br>Aguarde horários mais amenos.
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="alert-low">
                ✅ JANELA DE APLICAÇÃO VERDE.
                <br>Clima favorável para pulverização.
                <br>Seguir cronograma de preventivos.
            </div>
            """, unsafe_allow_html=True)

        col_left, col_right = st.columns(2)
        
        with col_left:
            st.markdown(f"""
            <div class="tech-card">
                <div class="tech-header">🧬 Fisiologia da Fase</div>
                <div class="tech-sub">Descrição do Estádio:</div>
                <div class="tech-text">{dados_fase['desc']}</div>
                
                <div class="tech-sub">Dinâmica Interna da Planta:</div>
                <div class="tech-text">{dados_fase['fisiologia']}</div>
                
                <div class="tech-sub">Genética ({sel_var}):</div>
                <div class="tech-text">{info_cultura['info']}</div>
            </div>
            """, unsafe_allow_html=True)

        with col_right:
            # Renderização Dinâmica dos Produtos Químicos
            html_quimica = ""
            if isinstance(dados_fase['quimica'], list):
                for prod in dados_fase['quimica']:
                    html_quimica += f"""
                    <li style="margin-bottom:8px;">
                        <b>{prod['Alvo']}</b>: {prod['Ativo']} 
                        <span style="font-size:0.8em; color:#666;">({prod['Grupo']} - {prod['Tipo']})</span>
                    </li>
                    """
            else:
                html_quimica = dados_fase['quimica']

            st.markdown(f"""
            <div class="tech-card">
                <div class="tech-header">🛡️ Manejo Integrado</div>
                <div class="tech-sub">Práticas Culturais:</div>
                <div class="tech-text">{dados_fase['manejo']}</div>
                
                <hr style="margin: 20px 0; border-top: 1px solid #eee;">
                
                <div class="tech-sub">🧪 Farmácia Digital (Recomendação):</div>
                <ul class="tech-text">
                    {html_quimica}
                </ul>
            </div>
            """, unsafe_allow_html=True)

    # --------------------------------------------------------------------------
    # ABA 2: CLIMA & IRRIGAÇÃO
    # --------------------------------------------------------------------------
    with tabs[1]:
        st.markdown('<div class="tech-card">', unsafe_allow_html=True)
        st.subheader("📊 Balanço Hídrico (Previsão 5 Dias)")
        
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=df_previsao['Data'], 
            y=df_previsao['Chuva'], 
            name='Precipitação (mm)', 
            marker_color='#0288d1'
        ))
        fig.add_trace(go.Scatter(
            x=df_previsao['Data'], 
            y=df_previsao['ETc'], 
            name='Demanda Hídrica (mm)', 
            line=dict(color='#d32f2f', width=3),
            mode='lines+markers'
        ))
        
        fig.update_layout(
            template="plotly_white",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=20, r=20, t=50, b=20),
            height=400
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Resumo
        total_chuva = df_previsao['Chuva'].sum()
        total_etc = df_previsao['ETc'].sum()
        saldo = total_chuva - total_etc
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Chuva Acumulada", f"{total_chuva:.1f} mm")
        c2.metric("Demanda Total (ETc)", f"{total_etc:.1f} mm")
        c3.metric("Saldo Hídrico", f"{saldo:.1f} mm", delta_color="normal")
        st.markdown('</div>', unsafe_allow_html=True)

    # --------------------------------------------------------------------------
    # ABA 3: RADAR REGIONAL
    # --------------------------------------------------------------------------
    with tabs[2]:
        st.markdown('<div class="tech-card">', unsafe_allow_html=True)
        st.subheader("📡 Monitoramento de Vizinhança (Raio 15km)")
        st.write(f"Análise de estações virtuais ao redor do ponto: {st.session_state['loc_lat']:.4f}, {st.session_state['loc_lon']:.4f}")
        
        df_radar = get_radar_simulation(url_w, st.session_state['loc_lat'], st.session_state['loc_lon'])
        
        if not df_radar.empty:
            cols_radar = st.columns(4)
            for idx, row in df_radar.iterrows():
                # Cor dinâmica baseada na chuva
                bg_color = "#ffebee" if row['Chuva'] == "Sim" else "#f1f8e9"
                border_color = "#ef5350" if row['Chuva'] == "Sim" else "#aed581"
                
                with cols_radar[idx]:
                    st.markdown(f"""
                    <div style="background-color:{bg_color}; border:1px solid {border_color}; padding:15px; border-radius:8px; text-align:center;">
                        <h4 style="margin:0; color:#333;">{row['Direcao']}</h4>
                        <span style="font-size:2em; font-weight:bold; color:#444;">{row['Temp']:.0f}°C</span>
                        <p style="margin:5px 0;">{row['Condicao']}</p>
                        <hr style="margin:5px 0; border-color:rgba(0,0,0,0.1);">
                        <small>Chuva: <b>{row['Chuva']}</b></small>
                    </div>
                    """, unsafe_allow_html=True)
            
            if "Sim" in df_radar['Chuva'].values:
                st.warning("⚠️ Chuva detectada no perímetro! Risco de pancadas isoladas.")
            else:
                st.success("✅ Estabilidade climática na região.")
        st.markdown('</div>', unsafe_allow_html=True)

    # --------------------------------------------------------------------------
    # ABA 4: IA VISION (DIAGNÓSTICO)
    # --------------------------------------------------------------------------
    with tabs[3]:
        st.markdown('<div class="tech-card">', unsafe_allow_html=True)
        c_upload, c_result = st.columns([1, 2])
        
        with c_upload:
            st.subheader("📸 Captura de Imagem")
            img_file = st.camera_input("Fotografar Folha/Fruto")
            if not img_file:
                img_file = st.file_uploader("Ou faça upload", type=['jpg', 'png', 'jpeg'])

        with c_result:
            st.subheader("🧠 Análise do Agrônomo Virtual")
            if img_file and url_g:
                try:
                    img = Image.open(img_file)
                    st.image(img, width=300, caption="Imagem Analisada")
                    
                    genai.configure(api_key=url_g)
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    
                    prompt = f"""
                    Atue como um Engenheiro Agrônomo Fitopatologista Sênior.
                    Analise esta imagem da cultura: {sel_cultura}.
                    Estágio atual: {sel_fase}.
                    Condições atuais: Temperatura {hoje['Temp']}C, Umidade {hoje['Umid']}%.
                    
                    1. Identifique a praga, doença ou deficiência nutricional.
                    2. Explique a causa provável.
                    3. Sugira o ingrediente ativo químico para controle (com grupo químico).
                    4. Sugira uma alternativa biológica.
                    """
                    
                    with st.spinner("Processando diagnóstico neural..."):
                        response = model.generate_content([prompt, img])
                        st.markdown(response.text)
                        
                except Exception as e:
                    st.error(f"Erro na análise IA: {e}")
            elif not url_g:
                st.info("Conecte a chave da API Gemini no menu lateral para ativar este módulo.")
        st.markdown('</div>', unsafe_allow_html=True)

    # --------------------------------------------------------------------------
    # ABA 5: CUSTOS
    # --------------------------------------------------------------------------
    with tabs[4]:
        st.markdown('<div class="tech-card">', unsafe_allow_html=True)
        st.subheader("💰 Gestão de Custos da Safra")
        
        if 'custos' not in st.session_state: st.session_state['custos'] = []
        
        c_input1, c_input2, c_btn = st.columns([2, 1, 1])
        with c_input1: item_desc = st.text_input("Descrição do Insumo/Serviço")
        with c_input2: item_val = st.number_input("Valor (R$)", min_value=0.0, step=10.0)
        with c_btn:
            st.write("") 
            st.write("") 
            if st.button("➕ Adicionar Custo"):
                st.session_state['custos'].append({
                    "Data": date.today().strftime("%d/%m/%Y"),
                    "Item": item_desc,
                    "Valor": item_val
                })
                st.rerun()
        
        if st.session_state['custos']:
            df_custos = pd.DataFrame(st.session_state['custos'])
            st.dataframe(df_custos, use_container_width=True)
            
            total_custo = df_custos['Valor'].sum()
            st.metric("Custo Total Acumulado", f"R$ {total_custo:,.2f}")
        else:
            st.info("Nenhum custo lançado para esta safra.")
        st.markdown('</div>', unsafe_allow_html=True)

    # --------------------------------------------------------------------------
    # ABA 6: MAPA OPERACIONAL
    # --------------------------------------------------------------------------
    with tabs[5]:
        st.markdown('<div class="tech-card">', unsafe_allow_html=True)
        col_list, col_map = st.columns([1, 3])
        
        with col_list:
            st.subheader("📍 Pontos de Interesse")
            st.info("Clique no mapa para capturar coordenadas.")
            
            nome_ponto = st.text_input("Nome do Talhão/Pivô")
            
            # Mostra lat/lon do último clique se houver
            if st.session_state.get('last_click'):
                clicked_lat = st.session_state['last_click'][0]
                clicked_lon = st.session_state['last_click'][1]
                st.caption(f"Selecionado: {clicked_lat:.5f}, {clicked_lon:.5f}")
                
                if st.button("💾 Salvar Ponto") and nome_ponto:
                    st.session_state['pontos_mapa'].append({
                        "nome": nome_ponto,
                        "lat": clicked_lat,
                        "lon": clicked_lon
                    })
                    st.success("Salvo!")
                    st.rerun()
            
            st.divider()
            if st.session_state['pontos_mapa']:
                st.write("Locais Salvos:")
                for p in st.session_state['pontos_mapa']:
                    st.markdown(f"**📍 {p['nome']}**")
            
            if st.button("🗑️ Limpar Mapa"):
                st.session_state['pontos_mapa'] = []
                st.rerun()

        with col_map:
            m = folium.Map(location=[st.session_state['loc_lat'], st.session_state['loc_lon']], zoom_start=15)
            
            # Camada de Satélite Profissional (Esri)
            folium.TileLayer(
                tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
                attr='Esri',
                name='Satélite',
                overlay=False,
                control=True
            ).add_to(m)
            
            # Ferramentas
            LocateControl().add_to(m)
            Fullscreen().add_to(m)
            Draw(export=True).add_to(m) # Adiciona ferramentas de desenho de polígono
            
            # Marcador da Sede
            folium.Marker(
                [st.session_state['loc_lat'], st.session_state['loc_lon']], 
                popup="Sede / Atual", 
                icon=folium.Icon(color='red', icon='home')
            ).add_to(m)
            
            # Marcadores do Usuário
            for p in st.session_state['pontos_mapa']:
                folium.Marker(
                    [p['lat'], p['lon']], 
                    popup=p['nome'], 
                    icon=folium.Icon(color='green', icon='leaf')
                ).add_to(m)

            # Renderiza mapa e captura clique
            map_data = st_folium(m, height=600, width="100%", returned_objects=["last_clicked"])
            
            if map_data["last_clicked"]:
                st.session_state['last_click'] = (map_data["last_clicked"]["lat"], map_data["last_clicked"]["lng"])
                # Pequeno hack para atualizar a interface se for um clique novo
                # st.rerun() # Opcional: pode causar refresh excessivo

        st.markdown('</div>', unsafe_allow_html=True)

else:
    st.info("Aguardando conexão com servidor de clima...")
