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
    
    /* CAPA DO APP (HEADER) - TOPO ABSOLUTO */
    .app-cover { 
        background: linear-gradient(135deg, #0d47a1 0%, #1b5e20 100%); 
        padding: 30px; 
        border-radius: 0 0 15px 15px; /* Arredondado apenas em baixo */
        color: white; 
        margin-top: -60px; /* Força o topo ignorando padding padrão do Streamlit */
        margin-left: -5rem; /* Expande para laterais */
        margin-right: -5rem;
        padding-left: 5rem;
        padding-right: 5rem;
        margin-bottom: 30px; 
        box-shadow: 0 6px 20px rgba(0,0,0,0.15);
        border-bottom: 1px solid rgba(255,255,255,0.1);
    }
    .cover-title { 
        font-size: 3em; 
        font-weight: 900; 
        margin: 0; 
        letter-spacing: -1px;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
    }
    .cover-subtitle { 
        font-size: 1.3em; 
        font-weight: 300; 
        opacity: 0.95; 
        margin-bottom: 25px; 
        font-style: italic;
        border-bottom: 1px solid rgba(255,255,255,0.2);
        padding-bottom: 15px;
        display: inline-block;
    }
    .data-grid {
        display: flex;
        gap: 20px;
        flex-wrap: wrap;
        margin-top: 15px;
    }
    .info-tag { 
        background: rgba(255,255,255,0.15); 
        padding: 10px 20px; 
        border-radius: 10px; 
        font-weight: 600; 
        font-size: 1em; 
        backdrop-filter: blur(5px);
        border: 1px solid rgba(255,255,255,0.2);
        display: flex;
        align-items: center;
        gap: 8px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }

    /* PAINEL DE CONTROLE */
    .control-panel {
        background-color: white;
        padding: 25px;
        border-radius: 15px;
        border: 1px solid #e0e0e0;
        box-shadow: 0 4px 10px rgba(0,0,0,0.05);
        margin-bottom: 30px;
    }

    /* CARDS TÉCNICOS */
    .tech-card { background: white; padding: 25px; border-radius: 12px; border-left: 6px solid #1565c0; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 20px; }
    .chem-card { background: white; padding: 25px; border-radius: 12px; border-left: 6px solid #c62828; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 20px; }
    .bio-card { background: white; padding: 25px; border-radius: 12px; border-left: 6px solid #2e7d32; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 20px; }
    
    /* ALERTA */
    .alert-box { padding: 15px; border-radius: 8px; font-weight: bold; margin-bottom: 15px; text-align: center; font-size: 1.1em; }
    .high-risk { background-color: #ffebee; color: #b71c1c; border: 1px solid #ef5350; }
    .low-risk { background-color: #e8f5e9; color: #1b5e20; border: 1px solid #66bb6a; }

    /* TEXTOS DE APOIO */
    .agro-explanation { font-size: 0.85em; color: #616161; margin-top: 5px; font-style: italic; }
</style>
""", unsafe_allow_html=True)

# --- 2. BANCO DE DADOS AGRONÔMICO (MANTIDO INTACTO) ---
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
                "riscos": "Rhizoctonia (Canela Preta), Pectobacterium.",
                "quim": "**Azoxistrobina:** Aplicação no sulco. Inibe respiração mitocondrial de fungos.\n**Tiametoxam:** Proteção inicial contra vetores.", 
                "bio": "**Trichoderma harzianum:** Colonização da rizosfera."
            },
            "Vegetativo (20-35 dias)": {
                "desc": "Expansão de Hastes.", 
                "fisio": "Alta demanda de Nitrogênio e Magnésio.", 
                "manejo": "Amontoa técnica.", 
                "riscos": "Vaquinha (Diabrotica), Minadora.",
                "quim": "**Mancozeb:** Multissítio de contato.\n**Clorotalonil:** Alta aderência.", 
                "bio": "**Beauveria bassiana:** Controle de insetos mastigadores."
            },
            "Tuberização (35-50 dias)": {
                "desc": "Início da Formação (Ganchos).", 
                "fisio": "Inversão hormonal crítica. Estresse causa abortamento.", 
                "manejo": "Irrigação de precisão.", 
                "riscos": "Requeima (Phytophthora), Sarna.",
                "quim": "**Mandipropamida (Revus):** Específico para Oomicetos.\n**Metalaxil-M:** Sistêmico curativo.", 
                "bio": "**Bacillus subtilis:** Inibe crescimento de bactérias."
            },
            "Enchimento (50-80 dias)": {
                "desc": "Crescimento dos Tubérculos.", 
                "fisio": "Translocação intensa de açúcares. Dreno de Potássio.", 
                "manejo": "Sanidade foliar total.", 
                "riscos": "Mosca Branca, Traça, Pinta Preta.",
                "quim": "**Ciantraniliprole:** Paralisa musculatura de insetos.\n**Espirotesifeno:** Inibe lipídios (Ácaros).", 
                "bio": "**Extrato de Algas:** Efeito stay-green."
            },
            "Maturação (80+ dias)": {
                "desc": "Senescência e Cura.", 
                "fisio": "Suberização da pele.", 
                "manejo": "Dessecação e suspensão da irrigação.", 
                "riscos": "Podridão mole, Larva Alfinete.",
                "quim": "**Diquat:** Dessecante de contato.\n**Carfentrazona:** Opção para manejo de folhas largas.", 
                "bio": "**Suspender Nitrogênio:** Para evitar pele fina."
            }
        }
    },
    "Tomate (Solanum lycopersicum)": {
        "t_base": 10,
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
                "quim": "**Imidacloprido:** Sistêmico no gotejo.", 
                "bio": "**Micorrizas:** Absorção de P."
            },
            "Florada": {
                "desc": "Emissão de Cachos.", 
                "fisio": "Viabilidade do pólen.", 
                "manejo": "Vibração ou Hormônio.", 
                "riscos": "Oídio, Botrytis.",
                "quim": "**Azoxistrobina:** Preventivo amplo espectro.", 
                "bio": "**Cálcio + Boro:** Pegamento."
            },
            "Frutificação": {
                "desc": "Engorda.", 
                "fisio": "Dreno de Potássio.", 
                "manejo": "Condução.", 
                "riscos": "Traça (Tuta), Requeima.",
                "quim": "**Clorfenapir:** Ação de choque (Tuta).", 
                "bio": "**Bacillus thuringiensis:** Lagartas."
            },
            "Colheita": {
                "desc": "Maturação.", 
                "fisio": "Síntese de Licopeno.", 
                "manejo": "Colheita delicada.", 
                "riscos": "Pós-colheita.",
                "quim": "**Cobre:** Bactericida preventivo.", 
                "bio": "**Óleo de Laranja:** Dessecante."
            }
        }
    },
    "Café (Coffea arabica)": {
        "t_base": 10,
        "vars": {
            "Catuaí": {"kc": 1.1, "gda_meta": 3000, "info": "Qualidade bebida. Sensível à Ferrugem."},
            "Arara": {"kc": 1.2, "gda_meta": 2900, "info": "Resistente à Ferrugem."}
        },
        "fases": {
            "Florada": {
                "desc": "Antese.", 
                "fisio": "Demanda energética.", 
                "manejo": "Não aplicar inseticidas.", 
                "riscos": "Phoma, Mancha Aureolada.",
                "quim": "**Boscalida:** Controle de Phoma.", 
                "bio": "**Extrato de Algas:** Anti-estresse."
            },
            "Chumbinho": {
                "desc": "Expansão Inicial.", 
                "fisio": "Divisão celular.", 
                "manejo": "Adubação N.", 
                "riscos": "Cercospora, Ferrugem.",
                "quim": "**Ciproconazol:** Triazol curativo.", 
                "bio": "**Cobre quelatado:** Parede celular."
            },
            "Granação": {
                "desc": "Enchimento.", 
                "fisio": "Deposição de massa.", 
                "manejo": "Adubação K.", 
                "riscos": "Broca-do-Café.",
                "quim": "**Ciantraniliprole:** Controle de Broca.", 
                "bio": "**Beauveria bassiana:** Biológico."
            },
            "Maturação": {
                "desc": "Cereja.", 
                "fisio": "Açúcares.", 
                "manejo": "Arruação.", 
                "riscos": "Queda de frutos.",
                "quim": "**Respeitar Carência.**", 
                "bio": "**Potássio Foliar.**"
            }
        }
    },
    "Mirtilo (Blueberry)": {
        "t_base": 7,
        "vars": {"Emerald": {"kc": 0.95, "gda_meta": 1800, "info": "pH 4.5. Vigorosa."}, "Biloxi": {"kc": 0.90, "gda_meta": 1900, "info": "Baixo frio. Rústica."}},
        "fases": {
            "Brotação": {
                "desc": "Fluxo Vegetativo.", 
                "fisio": "Mobilização de reservas.", 
                "manejo": "Correção de pH.", 
                "riscos": "Cochonilhas.", 
                "quim": "**Óleo Mineral:** Controle físico.", 
                "bio": "**Bokashi:** Microbiota ácida."
            },
            "Florada": {
                "desc": "Polinização.", 
                "fisio": "Sensível a abortamento.", 
                "manejo": "Abelhas.", 
                "riscos": "Botrytis (Mofo).", 
                "quim": "**Fludioxonil (Switch):** Padrão Botrytis.", 
                "bio": "**Aminoácidos:** Viabilidade pólen."
            },
            "Fruto Verde": {
                "desc": "Crescimento.", 
                "fisio": "Divisão celular.", 
                "manejo": "Nutrição K.", 
                "riscos": "Antracnose.", 
                "quim": "**Difenoconazol:** Triazol.", 
                "bio": "**Ácidos Fúlvicos.**"
            },
            "Maturação": {
                "desc": "Mudança de Cor.", 
                "fisio": "Antocianinas.", 
                "manejo": "Colheita.", 
                "riscos": "Drosófila (SWD).", 
                "quim": "**Espinosade:** Baixa carência.", 
                "bio": "**Iscas Atrativas.**"
            }
        }
    },
    "Framboesa (Rubus idaeus)": {
        "t_base": 7,
        "vars": {"Heritage": {"kc": 1.1, "gda_meta": 1300, "info": "Remontante. Vermelha."}, "Golden": {"kc": 1.05, "gda_meta": 1250, "info": "Amarela. Suave."}},
        "fases": {
            "Brotação": {
                "desc": "Emissão de Hastes.", 
                "fisio": "Crescimento rápido.", 
                "manejo": "Seleção de hastes.", 
                "riscos": "Ácaro Rajado.", 
                "quim": "**Abamectina:** Acaricida.", 
                "bio": "**Enxofre:** Repelência."
            },
            "Florada": {
                "desc": "Botões Florais.", 
                "fisio": "Sensível à chuva.", 
                "manejo": "Cobertura (Túnel).", 
                "riscos": "Podridão Floral.", 
                "quim": "**Iprodiona:** Preventivo.", 
                "bio": "**Cálcio Boro:** Firmeza."
            },
            "Frutificação": {
                "desc": "Formação de Bagas.", 
                "fisio": "Fruto agregado.", 
                "manejo": "Colheita frequente.", 
                "riscos": "Ferrugem.", 
                "quim": "**Azoxistrobina:** Sem manchar fruto.", 
                "bio": "**Silício:** Barreira física."
            },
            "Maturação": {
                "desc": "Colheita.", 
                "fisio": "Perecível.", 
                "manejo": "Refrigeração.", 
                "riscos": "Fungos pós-colheita.", 
                "quim": "**Não aplicar químicos sistêmicos.**", 
                "bio": "**Quitosana:** Filme protetor."
            }
        }
    },
    "Amora (Rubus spp.)": {
        "t_base": 7,
        "vars": {"Tupy": {"kc": 1.0, "gda_meta": 1500, "info": "Preta. Exige poda."}, "Xingu": {"kc": 1.05, "gda_meta": 1400, "info": "Sem espinhos."}},
        "fases": {
            "Brotação": {
                "desc": "Quebra de Dormência.", 
                "fisio": "Ativação de gemas.", 
                "manejo": "Cianamida (se necessário).", 
                "riscos": "Ferrugem da Amora.", 
                "quim": "**Cobre:** Limpeza.", 
                "bio": "**Calda Sulfocálcica.**"
            },
            "Florada": {
                "desc": "Cachos Florais.", 
                "fisio": "Polinização.", 
                "manejo": "Nutrição Boro.", 
                "riscos": "Botrytis.", 
                "quim": "**Captana:** Protetor.", 
                "bio": "**Extrato de Alho.**"
            },
            "Frutificação": {
                "desc": "Enchimento.", 
                "fisio": "Acúmulo de água.", 
                "manejo": "Irrigação.", 
                "riscos": "Ácaros.", 
                "quim": "**Tebuconazol:** Ferrugem.", 
                "bio": "**Metarhizium.**"
            },
            "Maturação": {
                "desc": "Preto Brilhante.", 
                "fisio": "Máximo açúcar.", 
                "manejo": "Colheita.", 
                "riscos": "Drosófila.", 
                "quim": "**Espinosade.**", 
                "bio": "**Armadilhas massais.**"
            }
        }
    },
    "Morango (Fragaria x ananassa)": {
        "t_base": 7,
        "vars": {"San Andreas": {"kc": 0.85, "gda_meta": 1200, "info": "Dia neutro. Ácaros."}, "Albion": {"kc": 0.85, "gda_meta": 1250, "info": "Sabor. Oídio."}},
        "fases": {
            "Vegetativo": {
                "desc": "Coroa.", 
                "fisio": "Folhas.", 
                "manejo": "Limpeza.", 
                "riscos": "Oídio, Ácaro.", 
                "quim": "**Enxofre, Abamectina.**", 
                "bio": "**Silício.**"
            },
            "Florada": {
                "desc": "Hastes.", 
                "fisio": "Polinização.", 
                "manejo": "Ventilação.", 
                "riscos": "Mofo Cinzento.", 
                "quim": "**Ciprodinil.**", 
                "bio": "**Clonostachys rosea.**"
            },
            "Colheita": {
                "desc": "Fruto.", 
                "fisio": "Açúcares.", 
                "manejo": "Diário.", 
                "riscos": "Podridão.", 
                "quim": "**Etoxazol.**", 
                "bio": "**Neoseiulus.**"
            }
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

def get_forecast(lat, lon, key, kc, t_base):
    try:
        url = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={key}&units=metric&lang=pt_br"
        r = requests.get(url).json()
        dados = []
        if 'list' in r:
            for item in r['list']:
                t = item['main']['temp']
                u = item['main']['humidity']
                
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
    st.caption("Agro-Intel Enterprise v46.0")

# --- 5. LÓGICA DE INICIALIZAÇÃO ---
if 'lat' not in st.session_state: st.session_state.lat = -13.2000
if 'lon' not in st.session_state: st.session_state.lon = -41.4000

# ---------------------------------------------------------
#  ESTRUTURA DA PÁGINA (CAPA NO TOPO -> INPUTS -> RESULTADOS)
# ---------------------------------------------------------

# 1. ESPAÇO RESERVADO PARA A CAPA (NO TOPO ABSOLUTO)
header_placeholder = st.empty()

# 2. PAINEL DE CONTROLE (ABAIXO DA CAPA)
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

# 3. LÓGICA DE PROCESSAMENTO E PREENCHIMENTO
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
        
        # --- AQUI ESTÁ A MÁGICA: PREENCHE A CAPA NO TOPO AGORA ---
        with header_placeholder.container():
            st.markdown(f"""
            <div class="app-cover">
                <h1 class="cover-title">Agro-Intel Enterprise</h1>
                <div class="cover-subtitle">Sistema Avançado de Suporte à Decisão Agronômica</div>
                <div class="data-grid">
                    <div class="info-tag">🌱 {cultura}</div>
                    <div class="info-tag">🧬 {variedade}</div>
                    <div class="info-tag">📅 {dias} dias de campo</div>
                    <div class="info-tag">🔥 {gda_acum:.0f} GDA Acumulado</div>
                </div>
                <div style="margin-top: 20px; font-size: 0.95em; opacity: 0.9; border-top: 1px solid rgba(255,255,255,0.2); padding-top: 15px;">
                    ℹ️ <b>Perfil Genético:</b> {v_db['info']}
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        # --- RESULTADOS ABAIXO DO PAINEL DE CONTROLE ---
        
        # Métricas Compactas
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("🌡️ Temperatura", f"{hoje['Temp']:.1f}°C")
        m2.metric("💧 Umidade", f"{hoje['Umid']}%")
        m3.metric("🌧️ Chuva (3h)", f"{hoje['Chuva']} mm")
        m4.metric("💦 Demanda ETc", f"{hoje['ETc']} mm")

        # Abas de Análise
        tabs = st.tabs(["🎓 Consultoria Técnica", "📊 Clima & Água", "📡 Radar", "👁️ IA Vision", "🗺️ Mapa", "🚚 Logística"])

        # ABA 1: CONSULTORIA TÉCNICA
        with tabs[0]:
            st.markdown(f"### Diagnóstico Fenológico: {fase}")
            
            
            st.progress(min(1.0, gda_acum/v_db['gda_meta']))
            
            # Alerta de Risco com Lógica
            if hoje['Umid'] > 85:
                st.markdown(f"<div class='alert-box high-risk'>🚨 ALERTA CRÍTICO: Umidade > 85%. Condição favorável para doenças fúngicas severas.</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div class='alert-box low-risk'>✅ CONDIÇÃO SEGURA: Baixo risco de infecção no momento.</div>", unsafe_allow_html=True)
            
            

            col_esq, col_dir = st.columns(2)
            with col_esq:
                # Uso de .get() para segurança
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
                    <p class="agro-explanation">Princípios ativos sugeridos com base no alvo biológico.</p>
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
