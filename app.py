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

# --- 1. CONFIGURAÇÃO DE ALTO NÍVEL ---
st.set_page_config(
    page_title="Agro-Intel Enterprise", 
    page_icon="🛡️", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# --- 2. ESTILO CSS "GLASSMORPHISM" (VISUAL PROFISSIONAL) ---
def local_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Roboto', sans-serif;
    }

    /* FUNDO COM IMAGEM FIXA */
    .stApp {
        background-image: linear-gradient(rgba(10, 25, 47, 0.85), rgba(10, 25, 47, 0.90)), 
                          url("https://images.unsplash.com/photo-1625246333195-78d9c38ad449?q=80&w=1740&auto=format&fit=crop");
        background-size: cover;
        background-attachment: fixed;
    }

    /* CARD DE VIDRO (GLASSMORPHISM) */
    .glass-card {
        background: rgba(255, 255, 255, 0.95);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border-radius: 12px;
        border: 1px solid rgba(255, 255, 255, 0.3);
        padding: 24px;
        margin-bottom: 20px;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.15);
        color: #1e293b;
    }

    /* CABEÇALHO */
    .header-enterprise {
        background: linear-gradient(90deg, #0f2027 0%, #203a43 50%, #2c5364 100%);
        padding: 20px;
        border-radius: 12px;
        color: white;
        margin-bottom: 25px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
    }

    /* KPI BOXES CUSTOMIZADOS */
    .kpi-box {
        background-color: #ffffff;
        border-left: 5px solid #00c853;
        border-radius: 8px;
        padding: 15px;
        text-align: center;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }
    .kpi-title { font-size: 0.9em; color: #666; text-transform: uppercase; letter-spacing: 1px; }
    .kpi-value { font-size: 1.8em; font-weight: bold; color: #333; }
    .kpi-sub { font-size: 0.8em; color: #888; }

    /* ALERTAS */
    .alert-box-red { background: #ffebee; border: 1px solid #ffcdd2; color: #b71c1c; padding: 15px; border-radius: 8px; }
    .alert-box-green { background: #e8f5e9; border: 1px solid #c8e6c9; color: #1b5e20; padding: 15px; border-radius: 8px; }

    /* TEXTOS */
    h1, h2, h3 { color: #ffffff; }
    .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 { color: #0f172a; } /* Headers dentro dos cards ficam escuros */
    
    </style>
    """, unsafe_allow_html=True)

local_css()

# --- 3. BANCO DE DADOS GLOBAL (TODAS AS CULTURAS) ---
BANCO_MASTER = {
    # --- FRUTAS VERMELHAS (RESTAURADAS!) ---
    "Amora Preta (Blackberry)": {
        "t_base": 7,
        "vars": {
            "Tupy": {"kc": 1.0, "gda_meta": 1500, "info": "Exige frio (chilling). Alta produtividade. Espinhos presentes."},
            "BRS Xingu": {"kc": 1.05, "gda_meta": 1400, "info": "Sem espinhos. Facilita colheita e poda."}
        },
        "fases": {
            "Brotação": {"desc": "Emissão de novas hastes.", "fisiologia": "Alta demanda de N.", "manejo": "Seleção de hastes produtivas. Controle de Ferrugem.", "quimica": "**Ferrugem:** Tebuconazol (Triazol).\n**Cochonilha:** Óleo Mineral."},
            "Florada": {"desc": "Abertura floral.", "fisiologia": "Sensível a chuva.", "manejo": "Monitorar Botrytis.", "quimica": "**Botrytis:** Iprodiona (Dicarboximida)."},
            "Frutificação": {"desc": "Maturação.", "fisiologia": "Acúmulo de Brix.", "manejo": "Mosca-das-frutas (Drosófila).", "quimica": "**SWD:** Espinosade (Biológico/Espinocina) - Isca Tóxica."}
        }
    },
    "Framboesa (Raspberry)": {
        "t_base": 7,
        "vars": {
            "Heritage": {"kc": 1.1, "gda_meta": 1300, "info": "Remontante (Produz no ano). Rústica."},
            "Golden Bliss": {"kc": 1.05, "gda_meta": 1250, "info": "Fruto amarelo. Nicho de mercado."}
        },
        "fases": {
            "Vegetativo": {"desc": "Crescimento de canas.", "fisiologia": "Estruturação.", "manejo": "Ácaro Vermelho.", "quimica": "**Ácaro:** Abamectina (Avermectina)."},
            "Produção": {"desc": "Flores e Frutos.", "fisiologia": "Perecível.", "manejo": "Podridão Cinzenta.", "quimica": "**Fungos:** Ciprodinil + Fludioxonil (Switch)."}
        }
    },
    "Mirtilo (Blueberry)": {
        "t_base": 7, "vars": {"Emerald": {"kc": 0.95, "gda_meta": 1800, "info": "pH 4.5."}, "Biloxi": {"kc": 0.90, "gda_meta": 1900, "info": "Ereta."}},
        "fases": {"Florada": {"desc": "Polinização.", "fisiologia": "Abelhas.", "manejo": "Botrytis.", "quimica": "Fludioxonil."}, "Fruto Verde": {"desc": "Engorda.", "fisiologia": "Sem Nitrato.", "manejo": "Antracnose.", "quimica": "Azoxistrobina."}}
    },
    "Morango": {"t_base": 7, "vars": {"Albion": {"kc": 0.85, "gda_meta": 1250, "info": "Sabor."}}, "fases": {"Florada": {"desc": "Contínua.", "fisiologia": "Frio.", "manejo": "Botrytis/Ácaro.", "quimica": "Ciprodinil, Abamectina."}}},

    # --- GRANDES CULTURAS (COMMODITIES) ---
    "Soja": {
        "t_base": 10,
        "vars": {"Intacta 2 Xtend": {"kc": 1.15, "gda_meta": 1400, "info": "Resistência Dicamba."}, "Brasmax": {"kc": 1.15, "gda_meta": 1350, "info": "Produtiva."}},
        "fases": {
            "Vegetativo (V1-Vn)": {"desc": "Folhas.", "fisiologia": "FBN.", "manejo": "Lagartas/Daninhas.", "quimica": "Glifosato, Clorantraniliprole."},
            "Reprodutivo (R1-R5)": {"desc": "Vagens.", "fisiologia": "Enchimento.", "manejo": "Ferrugem/Percevejo.", "quimica": "Protioconazol, Acefato."}
        }
    },
    "Milho": {
        "t_base": 10, "vars": {"Pioneer Bt": {"kc": 1.2, "gda_meta": 1600, "info": "Alto teto."}, "Dekalb": {"kc": 1.2, "gda_meta": 1650, "info": "Rústico."}},
        "fases": {"V4-V8": {"desc": "Definição.", "fisiologia": "Nitrato.", "manejo": "Cigarrinha/Pulgão.", "quimica": "Clotianidina."}, "VT-R1": {"desc": "Pendoamento.", "fisiologia": "Polinização.", "manejo": "Fungos.", "quimica": "Azoxistrobina."}}
    },
    "Algodão": {
        "t_base": 15, "vars": {"FiberMax": {"kc": 1.15, "gda_meta": 2200, "info": "Fibra."}}, 
        "fases": {"Botão Floral": {"desc": "Maçãs.", "fisiologia": "Hormônios.", "manejo": "Bicudo/Ramulária.", "quimica": "Malation, Azoxistrobina."}}
    },
    "Cana-de-Açúcar": {"t_base": 12, "vars": {"RB867515": {"kc": 1.25, "gda_meta": 3500, "info": "Rústica."}}, "fases": {"Crescimento": {"desc": "Colmos.", "fisiologia": "Biomassa.", "manejo": "Broca/Cigarrinha.", "quimica": "Tiametoxam, Cotesia (Bio)."}}},
    "Feijão": {"t_base": 10, "vars": {"Carioca": {"kc": 1.15, "gda_meta": 1300, "info": "Mercado."}}, "fases": {"Vegetativo": {"desc": "Folhas.", "fisiologia": "FBN.", "manejo": "Mosca Branca.", "quimica": "Ciantraniliprole."}}},

    # --- HORTALIÇAS & PERENES ---
    "Batata": {
        "t_base": 7,
        "vars": {"Orchestra": {"kc": 1.15, "gda_meta": 1600, "info": "Pele lisa."}, "Cupido": {"kc": 1.10, "gda_meta": 1400, "info": "Ciclo curto."}},
        "fases": {
            "Tuberização": {"desc": "Gancho.", "fisiologia": "Crítica água.", "manejo": "Requeima.", "quimica": "Metalaxil-M, Fluazinam."},
            "Enchimento": {"desc": "Engorda.", "fisiologia": "Dreno K.", "manejo": "Traça/Mosca.", "quimica": "Clorfenapir, Espirotesifeno."}
        }
    },
    "Café": {
        "t_base": 10,
        "vars": {"Catuaí": {"kc": 1.1, "gda_meta": 3000, "info": "Bebida."}, "Arara": {"kc": 1.2, "gda_meta": 2900, "info": "Resistente."}},
        "fases": {
            "Chumbinho": {"desc": "Expansão.", "fisiologia": "Divisão.", "manejo": "Ferrugem/Cercospora.", "quimica": "Priori Xtra."},
            "Granação": {"desc": "Sólidos.", "fisiologia": "Enchimento.", "manejo": "Broca/Bicho Mineiro.", "quimica": "Benévia, Cartape."}
        }
    },
    "Tomate": {"t_base": 10, "vars": {"Italiano": {"kc": 1.2, "gda_meta": 1600, "info": "Mesa."}}, "fases": {"Frutificação": {"desc": "Cachos.", "fisiologia": "Cálcio.", "manejo": "Tuta/Requeima.", "quimica": "Clorfenapir, Mandipropamida."}}},
    "Uva": {"t_base": 10, "vars": {"Vitoria": {"kc": 0.85, "gda_meta": 1500, "info": "Sem semente."}}, "fases": {"Maturação": {"desc": "Açúcar.", "fisiologia": "Cor.", "manejo": "Podridão.", "quimica": "Iprodiona."}}},
    "Citros": {"t_base": 13, "vars": {"Tahiti": {"kc": 0.75, "gda_meta": 2000, "info": "Limão."}}, "fases": {"Vegetativo": {"desc": "Fluxo.", "fisiologia": "Folha.", "manejo": "Psilídeo/Minadora.", "quimica": "Imidacloprido, Abamectina."}}}
}

# --- 4. FUNÇÕES DE SUPORTE ---
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
    pontos = {"Norte": (lat+0.15, lon), "Sul": (lat-0.15, lon), "Leste": (lat, lon+0.15), "Oeste": (lat, lon-0.15)}
    res = []
    for d, c in pontos.items():
        try:
            r = requests.get(f"https://api.openweathermap.org/data/2.5/weather?lat={c[0]}&lon={c[1]}&appid={api_key}&units=metric").json()
            res.append({"Dir": d, "Temp": r['main']['temp'], "Chuva": "Sim" if "rain" in r else "Não"})
        except: pass
    return pd.DataFrame(res)

# --- 5. LÓGICA DE INTERFACE ---
url_w, url_g = get_credentials()

# Estado Global
if 'loc_lat' not in st.session_state: st.session_state['loc_lat'] = -13.414
if 'loc_lon' not in st.session_state: st.session_state['loc_lon'] = -41.285
if 'pontos_mapa' not in st.session_state: st.session_state['pontos_mapa'] = []

# --- MENU LATERAL (APENAS LOGIN E CONFIG BÁSICA) ---
with st.sidebar:
    st.markdown("### ⚙️ Sistema")
    if not url_w:
        val_w = st.text_input("OpenWeather Key", type="password")
        val_g = st.text_input("Gemini AI Key", type="password")
        if st.button("Conectar"): st.query_params["w_key"] = val_w; st.query_params["g_key"] = val_g; st.rerun()
    else:
        st.success("Conectado")
        if st.button("Desconectar"): st.query_params.clear(); st.rerun()
    st.divider()
    st.info("Agro-Intel Enterprise v22.0")

# --- CABEÇALHO DO DASHBOARD ---
if url_w:
    # --- BLOCO 1: SELETOR UNIFICADO (GLASS CARD) ---
    st.markdown('<div class="header-enterprise"><h1>🛡️ Agro-Intel Enterprise</h1><p>Gestão Agronômica de Precisão</p></div>', unsafe_allow_html=True)
    
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    c_loc, c_cult, c_date = st.columns([1.5, 1.5, 1])
    
    with c_loc:
        st.subheader("📍 Propriedade")
        t1, t2 = st.tabs(["Busca", "GPS"])
        with t1:
            cb = st.text_input("Cidade:", placeholder="Ex: Ibicoara, BA", label_visibility="collapsed")
            if st.button("🔍") and cb:
                nlat, nlon = get_coords_from_city(cb, url_w)
                if nlat: st.session_state['loc_lat'], st.session_state['loc_lon'] = nlat, nlon; st.rerun()
        with t2:
            st.caption(f"Lat: {st.session_state['loc_lat']:.4f} | Lon: {st.session_state['loc_lon']:.4f}")
            if st.button("📍 Atualizar GPS"): st.rerun()

    with c_cult:
        st.subheader("🚜 Lavoura")
        cult_sel = st.selectbox("Cultura", sorted(list(BANCO_MASTER.keys())))
        col_var, col_fase = st.columns(2)
        var_sel = col_var.selectbox("Variedade", list(BANCO_MASTER[cult_sel]['vars'].keys()))
        fase_sel = col_fase.selectbox("Fase", list(BANCO_MASTER[cult_sel]['fases'].keys()))

    with c_date:
        st.subheader("📆 Ciclo")
        if 'd_plantio' not in st.session_state: st.session_state['d_plantio'] = date(2025, 11, 25)
        d_plantio = st.date_input("Início", st.session_state['d_plantio'])
        dias = (date.today() - d_plantio).days
        st.markdown(f"<h2 style='color:#333; text-align:center;'>{dias} Dias</h2>", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # --- PROCESSAMENTO DE DADOS ---
    info = BANCO_MASTER[cult_sel]['vars'][var_sel]
    df = get_forecast(url_w, st.session_state['loc_lat'], st.session_state['loc_lon'], info['kc'], BANCO_MASTER[cult_sel]['t_base'])

    if not df.empty:
        hoje = df.iloc[0]
        gda_acum = dias * df['GDA'].mean()
        
        # --- BLOCO 2: KPIs (CUSTOM HTML) ---
        kp1, kp2, kp3, kp4 = st.columns(4)
        with kp1: st.markdown(f'<div class="kpi-box"><div class="kpi-title">Temperatura</div><div class="kpi-value">{hoje["Temp"]:.1f}°C</div><div class="kpi-sub">Umid: {hoje["Umid"]}%</div></div>', unsafe_allow_html=True)
        with kp2: 
            vpd_status = "Ideal" if 0.4 <= hoje['VPD'] <= 1.3 else "Alerta"
            color = "#00c853" if vpd_status == "Ideal" else "#d32f2f"
            st.markdown(f'<div class="kpi-box" style="border-left: 5px solid {color}"><div class="kpi-title">VPD (Pressão)</div><div class="kpi-value">{hoje["VPD"]}</div><div class="kpi-sub">{vpd_status}</div></div>', unsafe_allow_html=True)
        with kp3: st.markdown(f'<div class="kpi-box"><div class="kpi-title">ETc (Consumo)</div><div class="kpi-value">{hoje["ETc"]}</div><div class="kpi-sub">mm/dia (Kc {info["kc"]})</div></div>', unsafe_allow_html=True)
        with kp4: 
            dt_status = "Pulverizar" if 2 <= hoje['Delta T'] <= 8 else "Parar"
            color = "#00c853" if dt_status == "Pulverizar" else "#d32f2f"
            st.markdown(f'<div class="kpi-box" style="border-left: 5px solid {color}"><div class="kpi-title">Delta T</div><div class="kpi-value">{hoje["Delta T"]}°C</div><div class="kpi-sub">{dt_status}</div></div>', unsafe_allow_html=True)

        st.write("") # Espaçamento

        # --- BLOCO 3: ABAS DE CONTEÚDO (GLASS CARDS INTERNOS) ---
        tabs = st.tabs(["🎓 Consultoria", "📊 Clima", "📡 Radar", "👁️ IA Vision", "💰 Custos", "🗺️ Mapa"])

        # ABA 1: CONSULTORIA
        with tabs[0]:
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            dados = BANCO_MASTER[cult_sel]['fases'][fase_sel]
            
            # GDA
            st.write(f"**Maturação Térmica (GDA):** {gda_acum:.0f} / {info.get('gda_meta', 1500)}")
            st.progress(min(1.0, gda_acum / info.get('gda_meta', 1500)))

            # Alerta Climático
            if hoje['Umid'] > 85 or hoje['Chuva'] > 2:
                st.markdown('<div class="alert-box-red">🚨 <b>ALERTA DE DOENÇAS:</b> Alta umidade favorece infecção. Suspenda protetores, use <b>SISTÊMICOS</b>.</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="alert-box-green">✅ <b>JANELA SEGURA:</b> Clima favorável para fungicidas protetores.</div>', unsafe_allow_html=True)

            c_tec1, c_tec2 = st.columns(2)
            with c_tec1:
                st.subheader("🧬 Fisiologia")
                st.info(dados['desc'])
                st.write(f"**Detalhe:** {dados['fisiologia']}")
                st.caption(f"Genética: {info['info']}")
            with c_tec2:
                st.subheader("🛡️ Plano de Ação")
                st.write(f"**Cultural:** {dados['manejo']}")
                st.markdown("---")
                st.write(f"**🧪 Químico:** {dados['quimica']}")
            st.markdown('</div>', unsafe_allow_html=True)

        # ABA 2: CLIMA
        with tabs[1]:
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            fig = go.Figure()
            fig.add_trace(go.Bar(x=df['Data'], y=df['Chuva'], name='Chuva', marker_color='#4fc3f7'))
            fig.add_trace(go.Scatter(x=df['Data'], y=df['ETc'], name='ETc', line=dict(color='#ef5350', width=3)))
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='#333')
            st.plotly_chart(fig, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

        # ABA 3: RADAR
        with tabs[2]:
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            st.subheader("📡 Radar Regional (15km)")
            dfr = get_radar_data(url_w, st.session_state['loc_lat'], st.session_state['loc_lon'])
            if not dfr.empty:
                cols = st.columns(4)
                for i, r in dfr.iterrows():
                    bg = "#ffebee" if r['Chuva'] == "Sim" else "#e8f5e9"
                    with cols[i]: st.markdown(f'<div style="background:{bg}; padding:10px; border-radius:8px; text-align:center;"><b>{r["Dir"]}</b><br>{r["Temp"]:.0f}°C<br>Chuva: {r["Chuva"]}</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

        # ABA 4: IA
        with tabs[3]:
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            st.subheader("👁️ Diagnóstico Fitopatológico")
            img = st.camera_input("Foto")
            if img and url_g:
                genai.configure(api_key=url_g)
                with st.spinner("Analisando..."):
                    res = genai.GenerativeModel('gemini-1.5-flash').generate_content([f"Agrônomo. Cultura: {cult_sel}. Fase: {fase_sel}. Umidade: {hoje['Umid']}%. Diagnóstico e Tratamento.", Image.open(img)]).text
                    st.success(res)
            st.markdown('</div>', unsafe_allow_html=True)

        # ABA 5: CUSTOS
        with tabs[4]:
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            if 'custos' not in st.session_state: st.session_state['custos'] = []
            c1, c2 = st.columns(2)
            i = c1.text_input("Item"); v = c2.number_input("R$")
            if c2.button("💾 Salvar"): st.session_state['custos'].append({"Item": i, "Valor": v})
            if st.session_state['custos']: st.dataframe(pd.DataFrame(st.session_state['custos']), use_container_width=True); st.metric("Total", f"R$ {pd.DataFrame(st.session_state['custos'])['Valor'].sum():,.2f}")
            st.markdown('</div>', unsafe_allow_html=True)

        # ABA 6: MAPA
        with tabs[5]:
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            c_add, c_map = st.columns([1, 3])
            with c_add:
                st.info("Clique no mapa para marcar.")
                nm = st.text_input("Nome Talhão")
                if st.button("Salvar Ponto") and st.session_state.get('last_click'):
                    st.session_state['pontos_mapa'].append({"nome": nm, "lat": st.session_state['last_click'][0], "lon": st.session_state['last_click'][1]}); st.rerun()
                for p in st.session_state['pontos_mapa']: st.markdown(f"📍 **{p['nome']}**")
            with c_map:
                m = folium.Map(location=[st.session_state['loc_lat'], st.session_state['loc_lon']], zoom_start=15)
                folium.TileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', attr='Esri', name='Satélite').add_to(m)
                LocateControl().add_to(m); Fullscreen().add_to(m)
                for p in st.session_state['pontos_mapa']: folium.Marker([p['lat'], p['lon']], popup=p['nome'], icon=folium.Icon(color='green', icon='leaf')).add_to(m)
                out = st_folium(m, height=500, returned_objects=["last_clicked"])
                if out["last_clicked"]: st.session_state['last_click'] = (out["last_clicked"]["lat"], out["last_clicked"]["lng"]); st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
else:
    st.info("👈 Conecte-se no menu lateral para iniciar o sistema.")
