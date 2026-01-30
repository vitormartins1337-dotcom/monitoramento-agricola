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
import base64

# --- 1. CONFIGURAÇÃO VISUAL ---
st.set_page_config(page_title="Agro-Intel System", page_icon="🚜", layout="wide", initial_sidebar_state="collapsed")

# --- FUNÇÕES VISUAIS (BACKGROUND) ---
def get_base64_of_bin_file(bin_file):
    try:
        with open(bin_file, 'rb') as f: data = f.read()
        return base64.b64encode(data).decode()
    except: return None

def set_background(png_file):
    bin_str = get_base64_of_bin_file(png_file)
    if bin_str:
        img_url = f"data:image/png;base64,{bin_str}"
    else:
        img_url = "https://images.unsplash.com/photo-1625246333195-78d9c38ad449?q=80&w=1740&auto=format&fit=crop"

    st.markdown(f'''
    <style>
    .stApp {{
        background-image: linear-gradient(rgba(240,242,246,0.94), rgba(240,242,246,0.94)), url("{img_url}");
        background-size: cover;
        background-attachment: fixed;
    }}
    .control-panel {{ background-color: #ffffff; padding: 20px; border-radius: 10px; border-bottom: 4px solid #1565c0; box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-bottom: 20px; }}
    .header-title {{ color: #0d47a1; font-size: 2.2em; font-weight: 800; margin: 0; }}
    .header-subtitle {{ color: #546e7a; font-size: 1.1em; font-weight: 500; margin-bottom: 15px; }}
    .tech-card {{ background-color: #fff; padding: 25px; border-radius: 8px; border: 1px solid #cfd8dc; margin-bottom: 15px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }}
    .tech-header {{ color: #0277bd; font-weight: 700; font-size: 1.3em; border-bottom: 2px solid #e1f5fe; padding-bottom: 10px; margin-bottom: 15px; }}
    .tech-sub {{ color: #455a64; font-weight: 600; margin-top: 10px; font-size: 0.95em; text-transform: uppercase; letter-spacing: 0.5px; }}
    .alert-high {{ background-color: #ffebee; border-left: 6px solid #d32f2f; padding: 20px; border-radius: 6px; color: #b71c1c; }}
    .alert-low {{ background-color: #e8f5e9; border-left: 6px solid #2e7d32; padding: 20px; border-radius: 6px; color: #1b5e20; }}
    div[data-testid="metric-container"] {{ background-color: #fff; border: 1px solid #e0e0e0; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }}
    </style>
    ''', unsafe_allow_html=True)

set_background('fundo_agro.jpg')

# --- 2. ENCICLOPÉDIA AGRONÔMICA OMNI (EXPANDIDA) ---
BANCO_MASTER = {
    # --- GRANDES CULTURAS (COMMODITIES) ---
    "Soja (Glycine max)": {
        "t_base": 10,
        "vars": {
            "Intacta 2 Xtend": {"kc": 1.15, "gda_meta": 1400, "info": "Resistência a Dicamba e Lagartas. Ciclo ajustado à latitude."},
            "Brasmax": {"kc": 1.15, "gda_meta": 1350, "info": "Alto teto produtivo. Exige fertilidade de solo corrigida."},
            "Conkesta Enlist": {"kc": 1.15, "gda_meta": 1450, "info": "Resistência a 2,4-D Colina. Manejo de buva facilitado."}
        },
        "fases": {
            "Vegetativo (V1-Vn)": {"desc": "Desenvolvimento de nós e folhas.", "fisiologia": "Fixação Biológica de Nitrogênio (FBN) ativa nos nódulos. Alta demanda de P e K.", "manejo": "Manejo de plantas daninhas (Glifosato/Dicamba). Monitorar Lagartas (*Helicoverpa*, *Spodoptera*).", "quimica": "**Lagartas:** Benzoato de Emamectina, Clorantraniliprole.\n**Daninhas:** Clethodim (Gramíneas), Glifosato."},
            "Florada (R1-R2)": {"desc": "Início do Reprodutivo.", "fisiologia": "Definição do número de vagens. Abortamento se houver estresse hídrico/térmico.", "manejo": "Entrada de Fungicidas para Ferrugem Asiática (*Phakopsora*). Não aplicar inseticidas 'quentes'.", "quimica": "**Ferrugem:** Protioconazol + Trifloxistrobina (Fox), Mancozebe (Multissítio)."},
            "Enchimento (R5)": {"desc": "Máxima translocação.", "fisiologia": "Peso de mil grãos (PMG). Dreno intenso de nutrientes da folha para o grão.", "manejo": "Controle de Percevejos (*Euschistus*, *Nezara*) para evitar grão picado.", "quimica": "**Percevejos:** Acefato, Neonicotinoides + Piretroides (Engeo Pleno)."},
            "Maturação (R8)": {"desc": "Ponto de colheita.", "fisiologia": "Umidade do grão cai para <14%.", "manejo": "Dessecação para uniformizar.", "quimica": "Diquat, Glufosinato."}
        }
    },
    "Milho (Zea mays)": {
        "t_base": 10,
        "vars": {
            "Pioneer Bt": {"kc": 1.2, "gda_meta": 1600, "info": "Híbrido de alto investimento. Exige N parcelado."},
            "Dekalb": {"kc": 1.2, "gda_meta": 1650, "info": "Resiliência a estresse hídrico. Sabugo fino."}
        },
        "fases": {
            "Vegetativo (V3-V6)": {"desc": "Definição do potencial (Número de fileiras).", "fisiologia": "Ponto de crescimento ainda abaixo do solo até V6.", "manejo": "Controle de Cigarrinha (*Dalbulus maidis*) para evitar Enfezamentos. Adubação Nitrogenada de cobertura.", "quimica": "**Cigarrinha:** Clotianidina, Metomil, Acefato.\n**Daninhas:** Atrazina + Nicosulfuron."},
            "Pendoamento (VT)": {"desc": "Emissão do pendão.", "fisiologia": "Polinização. Fase mais sensível à falta de água.", "manejo": "Aplicação de Fungicida preventivo (Mancha Branca/Cercospora).", "quimica": "**Doenças:** Azoxistrobina + Ciproconazol (Priori Xtra)."},
            "Enchimento (R1-R4)": {"desc": "Grão leitoso a pastoso.", "fisiologia": "Acúmulo de amido.", "manejo": "Monitorar Pulgão do Milho.", "quimica": "**Pulgão:** Acetamiprido."}
        }
    },
    "Algodão (Gossypium hirsutum)": {
        "t_base": 15,
        "vars": {"FiberMax": {"kc": 1.15, "gda_meta": 2200, "info": "Qualidade de fibra."}, "TMG": {"kc": 1.15, "gda_meta": 2100, "info": "Resistência a Ramulária."}},
        "fases": {
            "Vegetativo": {"desc": "Estabelecimento.", "fisiologia": "Crescimento monopodial.", "manejo": "Bicudo (*Anthonomus grandis*) nas bordaduras. Regulador de crescimento (Pix).", "quimica": "**Bicudo:** Malation, Fipronil.\n**Regulador:** Cloreto de Mepiquat."},
            "Botão Floral": {"desc": "Emissão de maçãs.", "fisiologia": "Balanço hormonal.", "manejo": "Monitorar Lagartas e Ramulária.", "quimica": "**Ramulária:** Azoxistrobina + Difenoconazol."}
        }
    },
    "Cana-de-Açúcar (Saccharum spp.)": {
        "t_base": 12,
        "vars": {"RB867515": {"kc": 1.25, "gda_meta": 3500, "info": "Rústica. Adapta-se a solos pobres."}, "CTC 4": {"kc": 1.2, "gda_meta": 3200, "info": "Precoce. Alto teor de sacarose."}},
        "fases": {
            "Brotamento/Perfilhamento": {"desc": "Fechamento da entrelinha.", "fisiologia": "Emissão de perfilhos.", "manejo": "Herbicidas pré-emergentes. Broca (*Diatraea*).", "quimica": "**Broca:** Cotesia flavipes (Bio), Clorantraniliprole.\n**Daninhas:** Tebutiurom, Sulfentrazone."},
            "Grande Crescimento": {"desc": "Alongamento de colmos.", "fisiologia": "Máxima fotossíntese.", "manejo": "Cigarrinha-da-raiz (*Mahanarva*).", "quimica": "**Cigarrinha:** Tiametoxam, Metarhizium (Bio)."},
            "Maturação": {"desc": "Acúmulo de sacarose.", "fisiologia": "Estresse hídrico favorece ATR.", "manejo": "Maturadores químicos.", "quimica": "Glifosato (Subdose), Ethephon."}
        }
    },
    "Feijão (Phaseolus vulgaris)": {
        "t_base": 10,
        "vars": {"Carioca": {"kc": 1.15, "gda_meta": 1300, "info": "Mercado interno."}, "Preto": {"kc": 1.15, "gda_meta": 1300, "info": "Ciclo mais tolerante."}},
        "fases": {
            "Vegetativo (V4)": {"desc": "Ramificação.", "fisiologia": "FBN ativa.", "manejo": "Mosca Branca (Mosaico Dourado).", "quimica": "**Mosca Branca:** Piriproxifem, Ciantraniliprole."},
            "Florada (R6)": {"desc": "Flores abertas.", "fisiologia": "Abortamento fácil.", "manejo": "Antracnose e Mancha Angular.", "quimica": "**Doenças:** Piraclostrobina, Fluxapiroxade."}
        }
    },
    # --- HORTIFRUTI E ESPECIAIS (CHAPADA E GERAL) ---
    "Batata (Solanum tuberosum)": {
        "t_base": 7,
        "vars": {
            "Orchestra": {"kc": 1.15, "gda_meta": 1600, "info": "Pele lisa. Exige K."},
            "Cupido": {"kc": 1.10, "gda_meta": 1400, "info": "Sensível a Requeima."},
            "Atlantic": {"kc": 1.15, "gda_meta": 1650, "info": "Chips/Indústria."}
        },
        "fases": {
            "Vegetativo": {"desc": "Crescimento aéreo.", "fisiologia": "Demanda N.", "manejo": "Amontoa. Vaquinha/Minadora.", "quimica": "**Minadora:** Ciromazina.\n**Vaquinha:** Tiametoxam."},
            "Tuberização": {"desc": "Formação de tubérculos.", "fisiologia": "Crítica água.", "manejo": "Requeima (*Phytophthora*).", "quimica": "**Requeima:** Metalaxil-M, Mandipropamida, Fluazinam."},
            "Enchimento": {"desc": "Engorda.", "fisiologia": "Translocação.", "manejo": "Traça (*Phthorimaea*) e Mosca Branca.", "quimica": "**Traça:** Clorfenapir, Indoxacarbe."}
        }
    },
    "Café (Coffea arabica)": {
        "t_base": 10,
        "vars": {"Catuaí": {"kc": 1.1, "gda_meta": 3000, "info": "Bebida fina."}, "Arara": {"kc": 1.2, "gda_meta": 2900, "info": "Resistente."}},
        "fases": {
            "Florada": {"desc": "Antese.", "fisiologia": "Polinização.", "manejo": "Phoma e Mancha Aureolada.", "quimica": "Boscalida, Piraclostrobina."},
            "Chumbinho": {"desc": "Expansão.", "fisiologia": "Divisão celular.", "manejo": "Ferrugem (*Hemileia*) e Cercospora.", "quimica": "Ciproconazol + Azoxistrobina."},
            "Granação": {"desc": "Enchimento.", "fisiologia": "Dreno forte.", "manejo": "Broca (*Hypothenemus*) e Bicho Mineiro.", "quimica": "**Broca:** Ciantraniliprole.\n**Mineiro:** Clorpirifós, Cartape."}
        }
    },
    "Tomate (Solanum lycopersicum)": {
        "t_base": 10, "vars": {"Italiano": {"kc": 1.2, "gda_meta": 1600, "info": "Saladete."}, "Grape": {"kc": 1.1, "gda_meta": 1450, "info": "Doce."}},
        "fases": {
            "Vegetativo": {"desc": "Estrutura.", "fisiologia": "Crescimento.", "manejo": "Tripes e Vira-cabeça.", "quimica": "**Tripes:** Espinetoram."},
            "Frutificação": {"desc": "Produção.", "fisiologia": "Cálcio.", "manejo": "Traça (*Tuta absoluta*) e Requeima.", "quimica": "**Traça:** Clorfenapir, Teflubenzurom.\n**Requeima:** Zoxamida."}
        }
    },
    "Citros (Laranja/Limão)": {
        "t_base": 13,
        "vars": {"Pera Rio": {"kc": 0.75, "gda_meta": 2500, "info": "Indústria/Mesa."}, "Tahiti": {"kc": 0.75, "gda_meta": 2000, "info": "Exportação."}},
        "fases": {
            "Vegetativo/Fluxo": {"desc": "Brotação.", "fisiologia": "Folhas novas.", "manejo": "Psilídeo (*Diaphorina citri* - Greening) e Minadora.", "quimica": "**Psilídeo:** Imidacloprido, Bifentrina, Tamarixia (Bio)."},
            "Florada": {"desc": "Flores brancas.", "fisiologia": "Estrela (Podridão Floral).", "manejo": "Verrugose e Podridão Floral.", "quimica": "**Fungos:** Carbendazim, Tebuconazol."}
        }
    },
    "Mirtilo (Blueberry)": {
        "t_base": 7, "vars": {"Emerald": {"kc": 0.95, "gda_meta": 1800, "info": "pH ácido."}, "Biloxi": {"kc": 0.90, "gda_meta": 1900, "info": "Ereta."}},
        "fases": {"Florada": {"desc": "Polinização.", "fisiologia": "Abelhas.", "manejo": "Botrytis (Mofo).", "quimica": "Fludioxonil."}, "Fruto Verde": {"desc": "Engorda.", "fisiologia": "Sem Nitrato.", "manejo": "Antracnose.", "quimica": "Azoxistrobina."}}
    },
    "Uva (Vitis vinifera)": {
        "t_base": 10, "vars": {"Nubia": {"kc": 0.85, "gda_meta": 1600, "info": "Mesa com semente."}, "Vitoria": {"kc": 0.85, "gda_meta": 1500, "info": "Sem semente."}},
        "fases": {"Brotação": {"desc": "Gema algodonosa.", "fisiologia": "Vigor.", "manejo": "Míldio (*Plasmopara*) e Oídio.", "quimica": "**Míldio:** Metalaxil-M.\n**Oídio:** Enxofre."}, "Maturação": {"desc": "Véraison.", "fisiologia": "Açúcar.", "manejo": "Podridão do Cacho.", "quimica": "Iprodiona."}}
    },
    "Morango": {"t_base": 7, "vars": {"Albion": {"kc": 0.85, "gda_meta": 1250, "info": "Sabor."}}, "fases": {"Florada": {"desc": "Contínua.", "fisiologia": "Frio.", "manejo": "Botrytis/Ácaro.", "quimica": "Ciprodinil, Abamectina."}}}
}

# --- 3. FUNÇÕES TÉCNICAS E CÁLCULOS ---
def get_credentials():
    return st.query_params.get("w_key", None), st.query_params.get("g_key", None)

def get_coords_from_city(city_name, api_key):
    try:
        url = f"http://api.openweathermap.org/geo/1.0/direct?q={city_name}&limit=1&appid={api_key}"
        r = requests.get(url).json()
        if r: return r[0]['lat'], r[0]['lon']
    except: pass
    return None, None

def calc_agro(temp, umid):
    es = 0.61078 * math.exp((17.27 * temp) / (temp + 237.3)); ea = es * (umid / 100); vpd = round(es - ea, 2)
    tw = temp * math.atan(0.151977 * (umid + 8.313659)**0.5) + math.atan(temp + umid) - math.atan(umid - 1.676331) + 0.00391838 * (umid)**1.5 * math.atan(0.023101 * umid) - 4.686035
    dt = round(temp - tw, 1)
    return dt, vpd

def get_forecast(api_key, lat, lon, kc, t_base):
    try:
        url = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={api_key}&units=metric&lang=pt_br"
        r = requests.get(url).json()
        dados = []
        for i in range(0, 40, 8):
            item = r['list'][i]
            t = item['main']['temp']
            dt, vpd = calc_agro(t, item['main']['humidity'])
            chuva = sum([r['list'][i+j].get('rain', {}).get('3h', 0) for j in range(8) if i+j < len(r['list'])])
            et0 = 0.0023 * (t + 17.8) * (t ** 0.5) * 0.408
            dados.append({'Data': datetime.fromtimestamp(item['dt']).strftime('%d/%m %Hh'), 'Temp': t, 'GDA': max(0, t-t_base), 'Chuva': round(chuva, 1), 'VPD': vpd, 'Delta T': dt, 'Umid': item['main']['humidity'], 'ETc': round(et0 * kc, 2)})
        return pd.DataFrame(dados)
    except: return pd.DataFrame()

def get_radar_data(api_key, lat, lon):
    pontos = {"Norte (15km)": (lat + 0.15, lon), "Sul (15km)": (lat - 0.15, lon), "Leste (15km)": (lat, lon + 0.15), "Oeste (15km)": (lat, lon - 0.15)}
    res = []
    for d, c in pontos.items():
        try:
            r = requests.get(f"https://api.openweathermap.org/data/2.5/weather?lat={c[0]}&lon={c[1]}&appid={api_key}&units=metric&lang=pt_br").json()
            res.append({"Dir": d, "Temp": r['main']['temp'], "Chuva": "Sim" if "rain" in r or "chuva" in r['weather'][0]['description'] else "Não"})
        except: pass
    return pd.DataFrame(res)

# --- 4. CONFIGURAÇÃO (GLOBAL) ---
url_w, url_g = get_credentials()
if 'loc_lat' not in st.session_state: st.session_state['loc_lat'] = -13.414
if 'loc_lon' not in st.session_state: st.session_state['loc_lon'] = -41.285
if 'pontos_mapa' not in st.session_state: st.session_state['pontos_mapa'] = []

# --- CABEÇALHO ---
st.markdown('<h1 class="header-title">Agro-Intel System</h1>', unsafe_allow_html=True)
st.markdown('<p class="header-subtitle">Gestão Agronômica de Precisão v21.0 (Omni)</p>', unsafe_allow_html=True)

if not url_w:
    st.warning("⚠️ Insira as chaves de acesso.")
    c1, c2, c3 = st.columns([2,2,1])
    vw = c1.text_input("OpenWeather", type="password"); vg = c2.text_input("Gemini AI", type="password")
    if c3.button("Login"): st.query_params["w_key"] = vw; st.query_params["g_key"] = vg; st.rerun()
    st.stop()

# --- PAINEL DE CONTROLE UNIFICADO ---
st.markdown('<div class="control-panel">', unsafe_allow_html=True)
c_loc, c_cult, c_data = st.columns([1.5, 1.5, 1])

with c_loc:
    st.markdown("### 📍 Localização")
    t1, t2 = st.tabs(["Busca", "GPS"])
    with t1:
        cb = st.text_input("Cidade:", placeholder="Ex: Rio Verde, GO", label_visibility="collapsed")
        if st.button("🔍") and cb:
            nlat, nlon = get_coords_from_city(cb, url_w)
            if nlat: st.session_state['loc_lat'], st.session_state['loc_lon'] = nlat, nlon; st.rerun()
    with t2:
        col_lat, col_lon = st.columns(2)
        nlat = col_lat.number_input("Lat", value=st.session_state['loc_lat'], format="%.4f")
        nlon = col_lon.number_input("Lon", value=st.session_state['loc_lon'], format="%.4f")
        if st.button("Atualizar"): st.session_state['loc_lat'], st.session_state['loc_lon'] = nlat, nlon; st.rerun()

with c_cult:
    st.markdown("### 🚜 Cultura")
    cult_sel = st.selectbox("Cultura:", list(BANCO_MASTER.keys()))
    col_v, col_f = st.columns(2)
    var_sel = col_v.selectbox("Variedade:", list(BANCO_MASTER[cult_sel]['vars'].keys()))
    fase_sel = col_f.selectbox("Fase:", list(BANCO_MASTER[cult_sel]['fases'].keys()))

with c_data:
    st.markdown("### 📆 Ciclo")
    if 'd_plantio' not in st.session_state: st.session_state['d_plantio'] = date(2025, 11, 25)
    d_plantio = st.date_input("Início:", st.session_state['d_plantio'])
    dias = (date.today() - d_plantio).days
    st.markdown(f"**Idade: {dias} dias**")
st.markdown('</div>', unsafe_allow_html=True)

# --- 5. LÓGICA DO SISTEMA ---
info = BANCO_MASTER[cult_sel]['vars'][var_sel]
df = get_forecast(url_w, st.session_state['loc_lat'], st.session_state['loc_lon'], info['kc'], BANCO_MASTER[cult_sel]['t_base'])

if not df.empty:
    hoje = df.iloc[0]
    gda_acum = dias * df['GDA'].mean()
    progresso = min(1.0, gda_acum / info.get('gda_meta', 1500))

    kp1, kp2, kp3, kp4 = st.columns(4)
    kp1.metric("🌡️ Temp", f"{hoje['Temp']:.1f}°C", f"Umid: {hoje['Umid']}%")
    kp2.metric("💧 VPD", f"{hoje['VPD']} kPa", "Ideal" if 0.4 <= hoje['VPD'] <= 1.3 else "Estresse")
    kp3.metric("💦 ETc", f"{hoje['ETc']} mm", f"Kc: {info['kc']}")
    kp4.metric("🛡️ Delta T", f"{hoje['Delta T']}°C", "Pulverizar" if 2 <= hoje['Delta T'] <= 8 else "Parar")

    tabs = st.tabs(["🎓 Consultoria Técnica", "📊 Clima & Irrigação", "📡 Radar Chuva", "👁️ IA Vision", "💰 Custos", "🗺️ Mapa"])

    # ABA 1: CONSULTORIA (EXPANDIDA)
    with tabs[0]:
        dados = BANCO_MASTER[cult_sel]['fases'][fase_sel]
        st.write(f"**Maturação Térmica (GDA):** {gda_acum:.0f} / {info.get('gda_meta', 1500)}")
        st.progress(progresso)

        risco = "Baixo"; msg = "✅ **Janela de Aplicação Aberta:** Clima favorável para fungicidas protetores."; estilo = "alert-low"
        if hoje['Umid'] > 85 or hoje['Chuva'] > 2: risco="Alto"; msg="🚨 **ALERTA FITOSSANITÁRIO:** Alta umidade favorece fungos e bactérias. Priorize **SISTÊMICOS**."; estilo="alert-high"
        if hoje['Delta T'] < 2 or hoje['Delta T'] > 8: msg += " ⚠️ **DELTA T INADEQUADO:** Risco de deriva ou evaporação. Aguarde."; estilo="alert-high"

        c_esq, c_dir = st.columns([1,1])
        with c_esq:
            st.markdown(f"""<div class="tech-card"><div class="tech-header">🧬 Fisiologia Avançada</div><div class="tech-sub">Descrição Fenológica:</div><p>{dados['desc']}</p><div class="tech-sub">Processos Internos:</div><p>{dados['fisiologia']}</p><div class="tech-sub">Genética ({var_sel}):</div><p>{info['info']}</p></div>""", unsafe_allow_html=True)
            st.markdown(f"""<div class="{estilo}"><strong>☁️ Matriz de Decisão (Hoje)</strong><br>{msg}</div>""", unsafe_allow_html=True)
        with c_dir:
            st.markdown(f"""<div class="tech-card"><div class="tech-header">🛡️ Manejo Integrado</div><div class="tech-sub">Práticas Culturais:</div><p>{dados['manejo']}</p><hr><div class="tech-sub">🧪 Farmácia Digital (Ingredientes Ativos):</div><p>{dados['quimica']}</p></div>""", unsafe_allow_html=True)

    # ABA 2: CLIMA
    with tabs[1]:
        fig = go.Figure()
        fig.add_trace(go.Bar(x=df['Data'], y=df['Chuva'], name='Chuva', marker_color='#29b6f6'))
        fig.add_trace(go.Scatter(x=df['Data'], y=df['ETc'], name='ETc', line=dict(color='#ef5350', width=3)))
        st.plotly_chart(fig, use_container_width=True)
        st.info(f"Balanço (7 dias): {df['Chuva'].sum() - df['ETc'].sum():.1f} mm")

    # ABA 3: RADAR
    with tabs[2]:
        st.markdown("### 📡 Radar Meteorológico Virtual (15km)")
        df_r = get_radar_data(url_w, st.session_state['loc_lat'], st.session_state['loc_lon'])
        if not df_r.empty:
            cols = st.columns(4)
            for i, r in df_r.iterrows():
                cor = "#ffcdd2" if r['Chuva'] == "Sim" else "#c8e6c9"
                with cols[i]: st.markdown(f"""<div style="background:{cor}; padding:10px; border-radius:5px; text-align:center;"><b>{r['Dir']}</b><br>{r['Temp']:.0f}°C<br>Chuva: {r['Chuva']}</div>""", unsafe_allow_html=True)

    # ABA 4: IA
    with tabs[3]:
        img = st.camera_input("Foto")
        if img and url_g:
            genai.configure(api_key=url_g)
            with st.spinner("Analisando..."):
                st.success(genai.GenerativeModel('gemini-1.5-flash').generate_content([f"Agrônomo Sênior. Analise {cult_sel}. Fase {fase_sel}. Diagnóstico detalhado (Praga/Doença) e Controle Químico/Biológico.", Image.open(img)]).text)

    # ABA 5: CUSTOS
    with tabs[4]:
        if 'custos' not in st.session_state: st.session_state['custos'] = []
        c1, c2 = st.columns(2)
        i = c1.text_input("Item"); v = c2.number_input("R$")
        if c2.button("Lançar"): st.session_state['custos'].append({"Item": i, "Valor": v})
        if st.session_state['custos']: st.dataframe(pd.DataFrame(st.session_state['custos'])); st.metric("Total", f"R$ {pd.DataFrame(st.session_state['custos'])['Valor'].sum():,.2f}")

    # ABA 6: MAPA
    with tabs[5]:
        st.markdown("### 🗺️ Gestão Territorial")
        c_add, c_map = st.columns([1,3])
        with c_add:
            nm = st.text_input("Nome Ponto"); 
            if st.button("Salvar") and st.session_state.get('last_click'): 
                st.session_state['pontos_mapa'].append({"nome": nm, "lat": st.session_state['last_click'][0], "lon": st.session_state['last_click'][1]}); st.rerun()
            for p in st.session_state['pontos_mapa']: st.write(f"📍 {p['nome']}")
        with c_map:
            m = folium.Map(location=[st.session_state['loc_lat'], st.session_state['loc_lon']], zoom_start=14)
            folium.TileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', attr='Esri', name='Satélite').add_to(m)
            LocateControl().add_to(m); Fullscreen().add_to(m)
            for p in st.session_state['pontos_mapa']: folium.Marker([p['lat'], p['lon']], popup=p['nome']).add_to(m)
            out = st_folium(m, height=500, returned_objects=["last_clicked"])
            if out["last_clicked"]: st.session_state['last_click'] = (out["last_clicked"]["lat"], out["last_clicked"]["lng"]); st.rerun()
