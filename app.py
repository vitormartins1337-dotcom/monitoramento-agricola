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
st.set_page_config(page_title="Agro-Intel System", page_icon="🌱", layout="wide", initial_sidebar_state="collapsed")

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
        # Imagem de backup (Drone/Agro) caso o arquivo local não exista
        img_url = "https://images.unsplash.com/photo-1625246333195-78d9c38ad449?q=80&w=1740&auto=format&fit=crop"

    st.markdown(f'''
    <style>
    .stApp {{
        background-image: linear-gradient(rgba(240,242,246,0.93), rgba(240,242,246,0.93)), url("{img_url}");
        background-size: cover;
        background-attachment: fixed;
    }}
    
    /* ESTILO DOS CARDS E PAINÉIS */
    .control-panel {{ background-color: #ffffff; padding: 20px; border-radius: 10px; border-bottom: 4px solid #1565c0; box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-bottom: 20px; }}
    .header-title {{ color: #0d47a1; font-size: 2.2em; font-weight: 800; margin: 0; }}
    .header-subtitle {{ color: #546e7a; font-size: 1.1em; font-weight: 500; margin-bottom: 15px; }}
    
    .tech-card {{ background-color: #fff; padding: 25px; border-radius: 8px; border: 1px solid #cfd8dc; margin-bottom: 15px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }}
    .tech-header {{ color: #0277bd; font-weight: 700; font-size: 1.3em; border-bottom: 2px solid #e1f5fe; padding-bottom: 10px; margin-bottom: 15px; }}
    .tech-sub {{ color: #455a64; font-weight: 600; margin-top: 10px; }}
    
    /* ALERTAS */
    .alert-high {{ background-color: #ffebee; border-left: 6px solid #d32f2f; padding: 20px; border-radius: 6px; color: #b71c1c; }}
    .alert-low {{ background-color: #e8f5e9; border-left: 6px solid #2e7d32; padding: 20px; border-radius: 6px; color: #1b5e20; }}
    
    /* KPI CARDS */
    div[data-testid="metric-container"] {{ background-color: #fff; border: 1px solid #e0e0e0; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }}
    </style>
    ''', unsafe_allow_html=True)

set_background('fundo_agro.jpg')

# --- 2. ENCICLOPÉDIA AGRONÔMICA COMPLETA ---
BANCO_MASTER = {
    "Batata (Solanum tuberosum)": {
        "t_base": 7,
        "vars": {
            "Orchestra": {"kc": 1.15, "gda_meta": 1600, "info": "Alta exigência de Potássio e Cálcio. Pele lisa premium. Atenção redobrada a Pinta Preta."},
            "Cupido": {"kc": 1.10, "gda_meta": 1400, "info": "Ciclo ultra-curto. Sensibilidade extrema à Requeima (Phytophthora). Colheita rápida necessária."},
            "Camila": {"kc": 1.15, "gda_meta": 1550, "info": "Mercado fresco. Sensível a Sarna Comum e Prateada. Evitar pH alcalino."},
            "Atlantic": {"kc": 1.15, "gda_meta": 1650, "info": "Indústria (Chips). Monitorar Matéria Seca e evitar estresse hídrico (Coração Oco)."}
        },
        "fases": {
            "Emergência (0-20 dias)": {
                "desc": "Brotamento e Enraizamento inicial.",
                "fisiologia": "A planta depende 100% das reservas nutricionais da batata-mãe. O sistema radicular é incipiente e exige solo aerado.",
                "manejo": "Manter solo úmido mas nunca encharcado (risco de Pectobacterium). Aplicação de enraizadores (Ácidos húmicos). Monitorar Rizoctonia (Cancro da Haste).",
                "quimica": "**Tratamento de Sulco:** Azoxistrobina (Rizoctonia) + Tiametoxam/Fipronil (Pragas de solo).\n**Foliar:** Ciromazina (Larva Minadora)."
            },
            "Estolonização (20-30 dias)": {
                "desc": "Crescimento Vegetativo e emissão de estolões.",
                "fisiologia": "Alta demanda de Nitrogênio para formação do Índice de Área Foliar (IAF). Fase de definição do número de hastes.",
                "manejo": "Realizar a **Amontoa** (Chegar terra). Monitorar Vaquinha (Diabrotica) e Pulgão (Vetor de Vírus).",
                "quimica": "**Fungicidas Preventivos (Multissítios):** Mancozeb, Clorotalonil, Propinebe.\n**Inseticidas:** Acetamiprido (Pulgão), Lambda-Cialotrina (Vaquinha)."
            },
            "Tuberização/Gancho (30-50 dias)": {
                "desc": "Início da formação dos tubérculos (Fase Crítica).",
                "fisiologia": "Inversão hormonal: Queda de Giberelina e aumento de Ácido Abscísico e Citocinina. Qualquer estresse hídrico agora causa Sarna Comum e abortamento de tubérculos.",
                "manejo": "Irrigação frequente com lâminas menores (Manter Capacidade de Campo). Controle 'militar' de Requeima.",
                "quimica": "**Requeima (Sistêmicos/Penetrantes):** Metalaxil-M, Dimetomorfe, Mandipropamida (Revus), Fluazinam, Cimoxanil.\n**Bacterioses:** Kasugamicina ou Cobre."
            },
            "Enchimento (50-85 dias)": {
                "desc": "Crescimento dos tubérculos.",
                "fisiologia": "A planta torna-se um dreno forte de Potássio (transporte de açúcares) e Magnésio (fotossíntese). Translocação intensa da folha para o tubérculo.",
                "manejo": "Monitorar Mosca Branca, Traça e Larva Alfinete. Evitar excesso de Nitrogênio (vicia em folha).",
                "quimica": "**Mosca Branca:** Ciantraniliprole (Benévia), Espirotesifeno (Oberon), Piriproxifem.\n**Traça:** Clorfenapir, Indoxacarbe, Espinosade.\n**Alternaria (Pinta Preta):** Tebuconazol, Boscalida, Metiram."
            },
            "Maturação/Senescência (85+ dias)": {
                "desc": "Amarelecimento natural e formação de pele.",
                "fisiologia": "Suberização (cura da pele). A planta para de enviar fotoassimilados.",
                "manejo": "Dessecação da rama. Evitar solo muito úmido para prevenir Podridão Mole e Sarna Prateada.",
                "quimica": "**Dessecante:** Diquat.\n**Monitoramento:** Traça da Batata no solo (furos no tubérculo)."
            }
        }
    },
    "Café (Coffea arabica)": {
        "t_base": 10,
        "vars": {"Catuaí": {"kc": 1.1, "gda_meta": 3000, "info": "Alta qualidade de bebida, mas suscetível a ferrugem."}, "Arara": {"kc": 1.2, "gda_meta": 2900, "info": "Alta produtividade e resistência a ferrugem."}},
        "fases": {
            "Dormência/Poda (Jul-Ago)": {"desc": "Repouso fisiológico.", "fisiologia": "Indução floral latente.", "manejo": "Poda de produção/esqueletamento. Correção de solo (Calagem/Gessagem).", "quimica": "Cobre (Preventivo Bacterioses/Phoma)."},
            "Florada (Set-Out)": {"desc": "Antese (Abertura floral).", "fisiologia": "Alta demanda de Boro e Zinco para viabilidade do tubo polínico.", "manejo": "Proteger polinizadores. Não aplicar inseticidas de choque.", "quimica": "**Foliar:** Ca + B + Zn.\n**Doenças:** Boscalida, Piraclostrobina (Phoma/Mancha Aureolada)."},
            "Chumbinho (Nov-Dez)": {"desc": "Expansão rápida do fruto.", "fisiologia": "Intensa divisão celular. Déficit hídrico gera 'peneira baixa' (grãos pequenos).", "manejo": "Controle preventivo de Cercospora e Ferrugem.", "quimica": "**Ferrugem/Cercospora:** Ciproconazol + Azoxistrobina (Priori Xtra), Tebuconazol, Epoxiconazol."},
            "Granação (Jan-Mar)": {"desc": "Enchimento de grão (sólidos).", "fisiologia": "Pico de extração de N e K. Risco de escaldadura e Die-back (Exaustão).", "manejo": "Monitorar Broca do Café e Bicho Mineiro.", "quimica": "**Broca:** Ciantraniliprole (Benévia), Clorantraniliprole (Voliam).\n**Bicho Mineiro:** Cartape, Clorpirifós."},
            "Maturação (Abr-Jun)": {"desc": "Mudança de cor (Cereja).", "fisiologia": "Acúmulo de açúcares.", "manejo": "Planejamento de colheita. Arruação.", "quimica": "Respeitar carência dos produtos."}
        }
    },
    "Tomate (Mesa/Indústria)": {
        "t_base": 10,
        "vars": {"Italiano": {"kc": 1.2, "gda_meta": 1600, "info": "Tipo Saladete. Sensível a Fundo Preto (Deficiência de Ca)."}, "Grape": {"kc": 1.1, "gda_meta": 1450, "info": "Tipo Cereja. Sensível a rachadura por oscilação hídrica."}},
        "fases": {
            "Transplante/Pegamento": {"desc": "Estabelecimento.", "fisiologia": "Enraizamento crítico.", "manejo": "Controle rigoroso de Tripes (Vira-Cabeça) e Mosca Branca (Geminivírus).", "quimica": "Imidacloprido (Drench), Tiametoxam, Acetamiprido."},
            "Vegetativo": {"desc": "Crescimento vertical.", "fisiologia": "Formação estrutural.", "manejo": "Desbrota lateral. Amarrio/Condução.", "quimica": "**Preventivo:** Mancozeb, Clorotalonil.\n**Bacteriose:** Cobre, Kasugamicina."},
            "Florada": {"desc": "Emissão de cachos.", "fisiologia": "Abortamento floral se T > 32°C ou T < 10°C.", "manejo": "Cálcio Foliar obrigatório semanalmente.", "quimica": "**Nutrição:** Cálcio Quelatado + Boro.\n**Oídio:** Enxofre, Metrafenona."},
            "Frutificação": {"desc": "Engorda dos frutos.", "fisiologia": "Forte dreno de Potássio.", "manejo": "Monitorar Tuta absoluta (Traça) e Requeima.", "quimica": "**Tuta absoluta:** Clorfenapir, Indoxacarbe, Teflubenzurom, Bacillus thuringiensis.\n**Requeima:** Mandipropamida, Zoxamida."}
        }
    },
    "Mirtilo (Blueberry)": {
        "t_base": 7,
        "vars": {"Emerald": {"kc": 0.95, "gda_meta": 1800, "info": "Vigorosa. Exige pH ácido (4.5)."}, "Biloxi": {"kc": 0.90, "gda_meta": 1900, "info": "Ereta. Poda de limpeza central necessária."}},
        "fases": {
            "Brotação": {"desc": "Emissão de folhas novas.", "fisiologia": "Uso de reservas radiculares.", "manejo": "Monitorar Cochonilha de carapaça.", "quimica": "Óleo Mineral + Imidacloprido."},
            "Florada": {"desc": "Abertura floral.", "fisiologia": "Polinização cruzada aumenta calibre.", "manejo": "Colocar colmeias (Bombus/Apis).", "quimica": "**Botrytis (Mofo):** Fludioxonil (Switch) aplicado à noite. Não aplicar inseticidas."},
            "Fruto Verde": {"desc": "Crescimento.", "fisiologia": "Evitar Nitrato (Usar Amônio).", "manejo": "Monitorar Antracnose e Ferrugem.", "quimica": "Azoxistrobina, Difenoconazol."}
        }
    },
    "Morango": {
        "t_base": 7,
        "vars": {"San Andreas": {"kc": 0.85, "gda_meta": 1200, "info": "Dia Neutro. Sensível a Ácaros."}, "Albion": {"kc": 0.85, "gda_meta": 1250, "info": "Fruto de sabor. Sensível a Oídio."}},
        "fases": {
            "Vegetativo": {"desc": "Desenvolvimento da Coroa.", "fisiologia": "Acúmulo de reservas.", "manejo": "Limpeza de folhas velhas. Retirada de estolões.", "quimica": "**Oídio:** Enxofre, Triflumizol.\n**Ácaro:** Abamectina."},
            "Florada": {"desc": "Emissão floral.", "fisiologia": "Polinização.", "manejo": "Controle de Mofo Cinzento (Botrytis).", "quimica": "**Botrytis:** Iprodiona, Procimidona, Ciprodinil."},
            "Colheita": {"desc": "Maturação contínua.", "fisiologia": "Alta demanda de K e Ca.", "manejo": "Colheita frequente. Controle de Ácaro Rajado.", "quimica": "**Ácaro:** Etoxazol, Acequinocil (Respeitar carência curta)."}
        }
    },
    "Amora Preta (Blackberry)": {
        "t_base": 7, "vars": {"Tupy": {"kc": 1.0, "gda_meta": 1500, "info": "Exige horas de frio."}, "Xingu": {"kc": 1.05, "gda_meta": 1400, "info": "Sem espinhos."}},
        "fases": {"Brotação": {"desc": "Emissão de hastes.", "fisiologia": "Crescimento vigoroso.", "manejo": "Controle de Ferrugem.", "quimica": "Tebuconazol."}, "Frutificação": {"desc": "Formação de bagas.", "fisiologia": "Acúmulo de açúcar.", "manejo": "Drosófila (SWD).", "quimica": "Espinosade (Isca tóxica)."}}
    },
    "Framboesa (Raspberry)": {
        "t_base": 7, "vars": {"Heritage": {"kc": 1.1, "gda_meta": 1300, "info": "Remontante."}, "Golden": {"kc": 1.05, "gda_meta": 1250, "info": "Fruto amarelo."}},
        "fases": {"Brotação": {"desc": "Hastes do ano.", "fisiologia": "Vigor.", "manejo": "Ácaro Vermelho.", "quimica": "Abamectina."}, "Florada": {"desc": "Flores brancas.", "fisiologia": "Sensível a chuva.", "manejo": "Podridão de frutos.", "quimica": "Iprodiona."}}
    }
}

# --- 3. FUNÇÕES DE SUPORTE ---
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
    resultados = []
    for direcao, coords in pontos.items():
        try:
            url = f"https://api.openweathermap.org/data/2.5/weather?lat={coords[0]}&lon={coords[1]}&appid={api_key}&units=metric&lang=pt_br"
            r = requests.get(url).json()
            resultados.append({"Direcao": direcao, "Temp": r['main']['temp'], "Clima": r['weather'][0]['description'].title(), "Chuva": "Sim" if "rain" in r or "chuva" in r['weather'][0]['description'] else "Não"})
        except: pass
    return pd.DataFrame(resultados)

# --- 4. CONFIGURAÇÃO (PAINEL SUPERIOR - FIM DO SIDEBAR) ---
url_w, url_g = get_credentials()

# Estado Global de Localização
if 'loc_lat' not in st.session_state: st.session_state['loc_lat'] = -13.414
if 'loc_lon' not in st.session_state: st.session_state['loc_lon'] = -41.285
if 'pontos_mapa' not in st.session_state: st.session_state['pontos_mapa'] = []

# --- CABEÇALHO E LOGIN ---
st.markdown('<h1 class="header-title">Agro-Intel System</h1>', unsafe_allow_html=True)
st.markdown('<p class="header-subtitle">Gestão Agronômica de Precisão</p>', unsafe_allow_html=True)

if not url_w:
    st.warning("⚠️ Sistema bloqueado. Insira suas credenciais abaixo.")
    c_login1, c_login2, c_login3 = st.columns([2,2,1])
    val_w = c_login1.text_input("OpenWeather Key", type="password")
    val_g = c_login2.text_input("Gemini AI Key", type="password")
    if c_login3.button("Acessar Sistema"):
        st.query_params["w_key"] = val_w
        st.query_params["g_key"] = val_g
        st.rerun()
    st.stop()

# --- PAINEL DE CONTROLE (NO TOPO, VISÍVEL) ---
st.markdown('<div class="control-panel">', unsafe_allow_html=True)
col_local, col_cultura, col_data = st.columns([1.5, 1.5, 1])

with col_local:
    st.markdown("### 📍 Localização")
    tab_b, tab_c = st.tabs(["Cidade", "GPS"])
    with tab_b:
        cid_busca = st.text_input("Cidade:", placeholder="Ex: Mucugê, BA", label_visibility="collapsed")
        if st.button("Buscar Local") and cid_busca:
            nlat, nlon = get_coords_from_city(cid_busca, url_w)
            if nlat: 
                st.session_state['loc_lat'], st.session_state['loc_lon'] = nlat, nlon
                st.success(f"📍 {cid_busca}")
                st.rerun()
    with tab_c:
        c_lat, c_lon = st.columns(2)
        nlat = c_lat.number_input("Lat:", value=st.session_state['loc_lat'], format="%.4f")
        nlon = c_lon.number_input("Lon:", value=st.session_state['loc_lon'], format="%.4f")
        if st.button("Atualizar GPS"):
            st.session_state['loc_lat'], st.session_state['loc_lon'] = nlat, nlon
            st.rerun()

with col_cultura:
    st.markdown("### 🚜 Cultura e Fase")
    cultura_sel = st.selectbox("Cultura:", list(BANCO_MASTER.keys()))
    c_var, c_fase = st.columns(2)
    var_sel = c_var.selectbox("Variedade:", list(BANCO_MASTER[cultura_sel]['vars'].keys()))
    fase_sel = c_fase.selectbox("Fase Fenológica:", list(BANCO_MASTER[cultura_sel]['fases'].keys()))

with col_data:
    st.markdown("### 📆 Ciclo")
    if 'd_plantio' not in st.session_state: st.session_state['d_plantio'] = date(2025, 11, 25)
    d_plantio = st.date_input("Data Início:", st.session_state['d_plantio'])
    dias_campo = (date.today() - d_plantio).days
    st.markdown(f"**Idade: {dias_campo} dias**")

st.markdown('</div>', unsafe_allow_html=True)

# --- 5. LÓGICA PRINCIPAL ---
info_v = BANCO_MASTER[cultura_sel]['vars'][var_sel]
df = get_forecast(url_w, st.session_state['loc_lat'], st.session_state['loc_lon'], info_v['kc'], BANCO_MASTER[cultura_sel]['t_base'])

if not df.empty:
    hoje = df.iloc[0]
    
    # CÁLCULO GDA
    media_gda_dia = df['GDA'].mean()
    gda_acum = dias_campo * media_gda_dia
    gda_meta = info_v.get('gda_meta', 1500)
    progresso = min(1.0, gda_acum / gda_meta)

    # KPIS PRINCIPAIS
    kp1, kp2, kp3, kp4 = st.columns(4)
    kp1.metric("🌡️ Temp Atual", f"{hoje['Temp']:.1f}°C", f"Umid: {hoje['Umid']}%")
    kp2.metric("💧 VPD (Pressão)", f"{hoje['VPD']} kPa", "Ideal" if 0.4 <= hoje['VPD'] <= 1.3 else "Alerta")
    kp3.metric("💦 ETc (Consumo)", f"{hoje['ETc']} mm", f"Kc: {info_v['kc']}")
    kp4.metric("🛡️ Delta T", f"{hoje['Delta T']}°C", "Ok" if 2 <= hoje['Delta T'] <= 8 else "Ruim")

    # ABAS DE CONTEÚDO
    tabs = st.tabs(["🎓 Consultoria Técnica", "📊 Clima & Irrigação", "📡 Radar Chuva", "👁️ IA Vision", "💰 Custos", "🗺️ Mapa"])

    # --- ABA 1: CONSULTORIA TÉCNICA (EXPANDIDA) ---
    with tabs[0]:
        dados = BANCO_MASTER[cultura_sel]['fases'][fase_sel]
        
        # GDA Bar
        st.write(f"**Progresso de Maturação Térmica (GDA):** {gda_acum:.0f} / {gda_meta}")
        st.progress(progresso)

        # Lógica Climática
        risco = "Baixo"; msg = "✅ <b>Clima Seco:</b> Use Protetores (Mancozeb/Cobre). Baixo risco de infecção."; estilo = "alert-low"
        if hoje['Umid'] > 85 or hoje['Chuva'] > 2: risco="ALTO"; msg="🚨 <b>ALERTA UMIDADE:</b> Risco severo de fungos. Use <b>SISTÊMICOS/PENETRANTES</b> imediatamente."; estilo="alert-high"

        col_left, col_right = st.columns([1, 1])
        
        with col_left:
            st.markdown(f"""
            <div class="tech-card">
                <div class="tech-header">🧬 Fisiologia & Desenvolvimento</div>
                <div class="tech-sub">O que está acontecendo?</div>
                <p>{dados['desc']}</p>
                <div class="tech-sub">Detalhe Fisiológico:</div>
                <p>{dados['fisiologia']}</p>
                <div class="tech-sub">Genética ({var_sel}):</div>
                <p>{info_v['info']}</p>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown(f"""<div class="{estilo}"><strong>☁️ Matriz de Decisão Climática (Hoje)</strong><br>{msg}</div>""", unsafe_allow_html=True)

        with col_right:
            st.markdown(f"""
            <div class="tech-card">
                <div class="tech-header">🛡️ Estratégia de Manejo</div>
                <div class="tech-sub">Manejo Cultural:</div>
                <p>{dados['manejo']}</p>
                <hr>
                <div class="tech-sub">🧪 Farmácia Digital (Prescrição):</div>
                <p>{dados['quimica']}</p>
            </div>
            """, unsafe_allow_html=True)

    # --- ABA 2: CLIMA ---
    with tabs[1]:
        fig = go.Figure()
        fig.add_trace(go.Bar(x=df['Data'], y=df['Chuva'], name='Chuva (mm)', marker_color='#29b6f6'))
        fig.add_trace(go.Scatter(x=df['Data'], y=df['ETc'], name='Consumo ETc (mm)', line=dict(color='#ef5350', width=3)))
        st.plotly_chart(fig, use_container_width=True)
        st.info(f"Balanço Hídrico (7 dias): {df['Chuva'].sum() - df['ETc'].sum():.1f} mm (Positivo = Sobra / Negativo = Déficit)")

    # --- ABA 3: RADAR ---
    with tabs[2]:
        st.markdown("### 📡 Monitoramento Regional (Raio 15km)")
        df_radar = get_radar_data(url_w, st.session_state['loc_lat'], st.session_state['loc_lon'])
        if not df_radar.empty:
            cols = st.columns(4)
            for idx, row in df_radar.iterrows():
                cor = "#ffebee" if row['Chuva'] == "Sim" else "#e8f5e9"
                with cols[idx]:
                    st.markdown(f"""<div class="radar-card" style="background-color: {cor}"><b>{row['Direcao']}</b><br><span style="font-size: 1.5em">{row['Temp']:.0f}°C</span><br>{row['Clima']}<br><small>Chuva: {row['Chuva']}</small></div>""", unsafe_allow_html=True)

    # --- ABA 4: IA ---
    with tabs[3]:
        st.write("Diagnóstico por Foto (Fitopatologia)")
        img = st.camera_input("Tirar Foto")
        if img and url_g:
            genai.configure(api_key=url_g)
            with st.spinner("O Agrônomo Virtual está analisando..."):
                res = genai.GenerativeModel('gemini-1.5-flash').generate_content([f"Atue como Agrônomo Sênior. Analise {cultura_sel}. Fase {fase_sel}. Umidade atual {hoje['Umid']}%. Identifique praga/doença e sugira controle.", Image.open(img)]).text
                st.success(res)

    # --- ABA 5: CUSTOS ---
    with tabs[4]:
        if 'custos' not in st.session_state: st.session_state['custos'] = []
        c1, c2 = st.columns(2)
        i = c1.text_input("Item Despesa"); v = c2.number_input("Valor R$")
        if c2.button("Lançar"): st.session_state['custos'].append({"Item": i, "Valor": v}); st.success("Salvo")
        if st.session_state['custos']: st.dataframe(pd.DataFrame(st.session_state['custos'])); st.metric("Total Acumulado", f"R$ {pd.DataFrame(st.session_state['custos'])['Valor'].sum():,.2f}")

    # --- ABA 6: MAPA ---
    with tabs[5]:
        st.markdown("### 🗺️ Gestão Territorial")
        c_add_pt, c_mapa = st.columns([1, 3])
        with c_add_pt:
            st.info("Clique no mapa para marcar um ponto.")
            nome_pt = st.text_input("Nome do Talhão")
            if st.session_state.get('last_click'):
                st.caption(f"Lat: {st.session_state['last_click'][0]:.4f}, Lon: {st.session_state['last_click'][1]:.4f}")
                if st.button("💾 Salvar Local") and nome_pt:
                    st.session_state['pontos_mapa'].append({"nome": nome_pt, "lat": st.session_state['last_click'][0], "lon": st.session_state['last_click'][1]})
                    st.success("Salvo!")
                    st.rerun()
            if st.session_state['pontos_mapa']:
                st.divider(); st.write("**Locais Salvos:**")
                for p in st.session_state['pontos_mapa']: st.write(f"📍 {p['nome']}")

        with c_mapa:
            m = folium.Map(location=[st.session_state['loc_lat'], st.session_state['loc_lon']], zoom_start=14)
            folium.TileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', attr='Esri', name='Satélite').add_to(m)
            LocateControl().add_to(m); Fullscreen().add_to(m)
            folium.Marker([st.session_state['loc_lat'], st.session_state['loc_lon']], popup="Sede", icon=folium.Icon(color='red', icon='home')).add_to(m)
            for p in st.session_state['pontos_mapa']: folium.Marker([p['lat'], p['lon']], popup=p['nome'], icon=folium.Icon(color='green', icon='leaf')).add_to(m)
            out = st_folium(m, width="100%", height=500, returned_objects=["last_clicked"])
            if out["last_clicked"]: st.session_state['last_click'] = (out["last_clicked"]["lat"], out["last_clicked"]["lng"]); st.rerun()
