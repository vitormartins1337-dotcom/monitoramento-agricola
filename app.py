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

# --- 1. CONFIGURAÇÃO DE ALTO NÍVEL ---
st.set_page_config(
    page_title="Agro-Intel Ultimate",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- ESTILIZAÇÃO CSS ENTERPRISE ---
st.markdown("""
<style>
    .main { background-color: #f4f6f9; }
    .stMetric { background-color: #ffffff; border: 1px solid #e0e0e0; border-radius: 10px; padding: 15px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }
    .header-style { background: linear-gradient(90deg, #1b5e20 0%, #4caf50 100%); color: white; padding: 25px; border-radius: 15px; margin-bottom: 25px; }
    .tech-card { background: white; padding: 20px; border-radius: 12px; border-left: 5px solid #2e7d32; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 20px; }
    .chem-card { background: white; padding: 20px; border-radius: 12px; border-left: 5px solid #d32f2f; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 20px; }
    .radar-box { background-color: #e3f2fd; border: 1px solid #90caf9; padding: 15px; border-radius: 10px; text-align: center; }
    h3 { color: #1b5e20; }
</style>
""", unsafe_allow_html=True)

# --- 2. BANCO DE DADOS AGRONÔMICO COMPLETO (SEM RESUMOS) ---
BANCO_MASTER = {
    "Batata (Solanum tuberosum)": {
        "t_base": 7,
        "vars": {
            "Orchestra": {"kc": 1.15, "gda_meta": 1600, "info": "Pele lisa, polpa amarela. Alta exigência de Potássio (K) e Boro (B). Sensível a Pinta Preta."},
            "Cupido": {"kc": 1.10, "gda_meta": 1400, "info": "Ciclo ultra-curto (90 dias). Extrema sensibilidade à Requeima. Exige colheita rápida."},
            "Camila": {"kc": 1.15, "gda_meta": 1550, "info": "Referência em mercado fresco. Atenção redobrada com Sarna Comum e Rhizoctonia."},
            "Atlantic": {"kc": 1.15, "gda_meta": 1650, "info": "Padrão industrial (Chips). Monitorar Coração Oco (Cálcio) e Matéria Seca."}
        },
        "fases": {
            "Emergência (0-20 dias)": {
                "desc": "Brotamento e estabelecimento.",
                "fisio": "Dependência das reservas do tubérculo-mãe. Sistema radicular frágil.",
                "riscos": "Rhizoctonia (Canela Preta), Pectobacterium (Podridão Mole).",
                "quimica": "<b>Sulco de Plantio:</b> Azoxistrobina (Amistar) + Tiametoxam (Actara) ou Fipronil.\n<b>Herbicida:</b> Metribuzin (Sencor) em pré-emergência.",
                "bio": "<i>Trichoderma harzianum</i> no sulco + Ácidos Húmicos."
            },
            "Vegetativo (20-35 dias)": {
                "desc": "Fechamento de linhas.",
                "fisio": "Expansão de IAF (Índice de Área Foliar). Alta demanda de Nitrogênio.",
                "riscos": "Vaquinha (Diabrotica), Larva Minadora, Míldio inicial.",
                "quimica": "<b>Preventivos:</b> Mancozeb (Dithane), Clorotalonil (Bravonil).\n<b>Inseticidas:</b> Lambda-Cialotrina (Karate), Acetamiprido.",
                "bio": "<i>Beauveria bassiana</i> para insetos mastigadores + Bokashi líquido."
            },
            "Tuberização (35-50 dias)": {
                "desc": "Início dos ganchos.",
                "fisio": "Inversão Hormonal (Giberelina cai, Ácido Jasmônico sobe). Fase crítica para água.",
                "riscos": "Requeima (Phytophthora), Sarna (Streptomyces).",
                "quimica": "<b>Sistêmicos Requeima:</b> Mandipropamida (Revus), Metalaxil-M (Ridomil Gold), Fluazinam (Shirlan).\n<b>Bacteriose:</b> Kasugamicina.",
                "bio": "<i>Bacillus subtilis</i> (Serenade) para sanidade de solo."
            },
            "Enchimento (50-80 dias)": {
                "desc": "Expansão de tubérculos.",
                "fisio": "Dreno forte de K e Mg. Translocação de fotoassimilados.",
                "riscos": "Mosca Branca, Traça (Tuta/Phthorimaea), Alternaria (Pinta Preta).",
                "quimica": "<b>Mosca Branca:</b> Ciantraniliprole (Benévia), Espirotesifeno (Oberon).\n<b>Pinta Preta:</b> Tebuconazol (Folicur), Boscalida (Cantus).",
                "bio": "Extrato de Algas (Ascophyllum) + Potássio Foliar."
            },
            "Maturação (80+ dias)": {
                "desc": "Senescência e cura.",
                "fisio": "Suberização da pele. Conversão de açúcares em amido.",
                "riscos": "Podridão úmida pós-colheita, Larva Alfinete.",
                "quimica": "<b>Dessecação:</b> Diquat (Reglone) ou Carfentrazona.\n<b>Solo:</b> Monitorar pragas de solo.",
                "bio": "Suspender Nitrogênio. Aplicação de Silício."
            }
        }
    },
    "Café (Coffea arabica)": {
        "t_base": 10,
        "vars": {
            "Catuaí": {"kc": 1.1, "gda_meta": 3000, "info": "Qualidade de bebida excelente. Suscetível à Ferrugem e Nematoides."},
            "Arara": {"kc": 1.2, "gda_meta": 2900, "info": "Imune à Ferrugem. Alta produtividade. Maturação tardia."}
        },
        "fases": {
            "Florada": {
                "desc": "Antese e Pegamento.",
                "fisio": "Alta demanda de energia. Necessidade crítica de Boro e Zinco.",
                "riscos": "Phoma (Mancha de Phoma), Mancha Aureolada.",
                "quimica": "<b>Fungicidas:</b> Boscalida (Cantus), Piraclostrobina (Comet).\n<b>Nutrição:</b> Cálcio + Boro via foliar.",
                "bio": "Aminoácidos livres (anti-estresse)."
            },
            "Chumbinho": {
                "desc": "Expansão rápida.",
                "fisio": "Divisão celular intensa. Definição do tamanho da peneira.",
                "riscos": "Cercospora (Olho pardo), Ferrugem (se não for resistente).",
                "quimica": "<b>Sistêmicos:</b> Ciproconazol + Azoxistrobina (Priori Xtra), Epoxiconazol.\n<b>Foliar:</b> Cobre fixo.",
                "bio": "Bioestimulantes à base de Algas."
            }
        }
    },
    "Tomate": {
        "t_base": 10,
        "vars": {
            "Italiano": {"kc": 1.2, "gda_meta": 1600, "info": "Fruto alongado. Atenção ao Fundo Preto (Deficiência de Ca)."},
            "Grape": {"kc": 1.1, "gda_meta": 1450, "info": "Alto teor de açúcar (Brix). Sensível a rachaduras."}
        },
        "fases": {
            "Vegetativo": {"desc": "Formação de hastes.", "fisio": "Estruturação.", "riscos": "Tripes (Vira-cabeça), Geminivírus.", "quimica": "<b>Vetores:</b> Espinetoram (Delegate), Imidacloprido.", "bio": "Óleo de Neem + Enxofre."},
            "Frutificação": {"desc": "Engorda.", "fisio": "Dreno de Potássio.", "riscos": "Requeima, Traça do Tomateiro.", "quimica": "<b>Requeima:</b> Cimoxanil, Dimetomorfe.\n<b>Traça:</b> Clorfenapir, Indoxacarbe.", "bio": "<i>Bacillus thuringiensis</i> (Bt)."}
        }
    },
    "Mirtilo (Blueberry)": {
        "t_base": 7,
        "vars": {
            "Emerald": {"kc": 0.95, "gda_meta": 1800, "info": "Vigorosa. Exige pH ácido (4.5 - 5.0). Alta produtividade."},
            "Biloxi": {"kc": 0.90, "gda_meta": 1900, "info": "Baixa exigência de frio. Porte ereto. Rústica."}
        },
        "fases": {
            "Brotação": {"desc": "Fluxo vegetativo.", "fisio": "Mobilização de reservas.", "riscos": "Cochonilhas, Oídio.", "quimica": "Óleo Mineral, Enxofre.", "bio": "Bokashi sólido."},
            "Florada": {"desc": "Polinização.", "fisio": "Sensível a abortamento.", "riscos": "Botrytis (Mofo Cinzento).", "quimica": "<b>Botrytis:</b> Fludioxonil + Ciprodinil (Switch). Não aplicar inseticidas tóxicos às abelhas.", "bio": "Cálcio e Boro."},
            "Frutificação": {"desc": "Maturação.", "fisio": "Acúmulo de Antocianinas.", "riscos": "Antracnose (Glomerella).", "quimica": "Azoxistrobina, Difenoconazol.", "bio": "Sulfato de Potássio (Sabor)."}
        }
    },
    "Morango": {
        "t_base": 7,
        "vars": {
            "San Andreas": {"kc": 0.85, "gda_meta": 1200, "info": "Dia neutro. Precoce. Sensível a Ácaro Rajado."},
            "Albion": {"kc": 0.85, "gda_meta": 1250, "info": "Dia neutro. Frutos grandes. Sensível a Oídio."}
        },
        "fases": {
            "Florada": {"desc": "Florescimento contínuo.", "fisio": "Polinização.", "riscos": "Mofo Cinzento (Botrytis).", "quimica": "Iprodiona, Procimidona, Captafol.", "bio": "Clonostachys rosea."},
            "Colheita": {"desc": "Maturação.", "fisio": "Açúcares.", "riscos": "Ácaro Rajado, Drosophila.", "quimica": "<b>Ácaro:</b> Abamectina, Etoxazol.\n<b>Drosófila:</b> Espinosade (Trace).", "bio": "Predadores naturais (Neoseiulus)."}
        }
    },
    "Framboesa/Amora": {
        "t_base": 7,
        "vars": {
            "Heritage (Framboesa)": {"kc": 1.1, "gda_meta": 1300, "info": "Remontante. Produz no ano."},
            "Tupy (Amora)": {"kc": 1.0, "gda_meta": 1500, "info": "Exige poda drástica. Fruto equilibrado."}
        },
        "fases": {
            "Frutificação": {"desc": "Bagas.", "fisio": "Acúmulo de sólidos solúveis.", "riscos": "Ferrugem, Drosófila suzukii.", "quimica": "<b>Ferrugem:</b> Tebuconazol.\n<b>Mosca:</b> Espinosade, Isca tóxica.", "bio": "Armadilhas de vinagre."}
        }
    }
}

# --- 3. MOTORES DE CÁLCULO E API ---
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
            for item in r['list']: # Pega todos os pontos (3h em 3h)
                t = item['main']['temp']
                u = item['main']['humidity']
                dt_txt = datetime.fromtimestamp(item['dt'])
                
                # Cálculos Agronômicos
                es = 0.61078 * math.exp((17.27 * t) / (t + 237.3))
                ea = es * (u / 100)
                vpd = max(0, round(es - ea, 2))
                gda = max(0, (t - t_base) / 8) # GDA simplificado por período de 3h
                et0_aprox = 0.0023 * (t + 17.8) * (t ** 0.5) * 0.408
                
                dados.append({
                    'Data': dt_txt,
                    'Temp': t,
                    'Umid': u,
                    'Chuva': item.get('rain', {}).get('3h', 0),
                    'VPD': vpd,
                    'GDA': gda,
                    'ETc': round(et0_aprox * kc, 2),
                    'Descrição': item['weather'][0]['description']
                })
            return pd.DataFrame(dados)
    except Exception as e:
        st.error(f"Erro clima: {e}")
        return pd.DataFrame()

def get_radar_regional(lat, lon, key):
    # Monitora 15km em cruz
    pontos = {
        "Norte (15km)": (lat + 0.13, lon),
        "Sul (15km)": (lat - 0.13, lon),
        "Leste (15km)": (lat, lon + 0.13),
        "Oeste (15km)": (lat, lon - 0.13)
    }
    res = []
    for direcao, coords in pontos.items():
        try:
            url = f"https://api.openweathermap.org/data/2.5/weather?lat={coords[0]}&lon={coords[1]}&appid={key}&units=metric&lang=pt_br"
            r = requests.get(url).json()
            res.append({
                "Local": direcao,
                "Temp": r['main']['temp'],
                "Condição": r['weather'][0]['description'].title(),
                "Chuva": "SIM" if "rain" in r else "Não"
            })
        except: pass
    return pd.DataFrame(res)

# --- 4. SIDEBAR INTELIGENTE ---
with st.sidebar:
    st.header("⚙️ Painel de Controle")
    
    # Gerenciamento de Chaves (Secrets ou Manual)
    api_w = st.secrets.get("OPENWEATHER_KEY", st.text_input("OpenWeather Key:", type="password"))
    api_g = st.secrets.get("GEMINI_KEY", st.text_input("Gemini API Key:", type="password"))
    
    st.divider()
    st.markdown("### 📍 Localização")
    tab_city, tab_gps = st.tabs(["🏙️ Cidade", "🌐 GPS"])
    
    if 'lat' not in st.session_state: st.session_state.lat = -13.2000
    if 'lon' not in st.session_state: st.session_state.lon = -41.4000
    
    with tab_city:
        city_in = st.text_input("Cidade/UF:", placeholder="Ex: Mucugê, BA")
        if st.button("Buscar") and api_w:
            nlat, nlon = get_coords(city_in, api_w)
            if nlat:
                st.session_state.lat, st.session_state.lon = nlat, nlon
                st.success("Localizado!")
                st.rerun()

    with tab_gps:
        st.session_state.lat = st.number_input("Lat:", value=st.session_state.lat, format="%.4f")
        st.session_state.lon = st.number_input("Lon:", value=st.session_state.lon, format="%.4f")

    st.divider()
    # Seletores de Cultura Blindados
    cultura = st.selectbox("Cultura:", list(BANCO_MASTER.keys()))
    # O seletor de variedade atualiza baseado na cultura
    variedade = st.selectbox("Variedade:", list(BANCO_MASTER[cultura]['vars'].keys()))
    fase = st.selectbox("Estágio Atual:", list(BANCO_MASTER[cultura]['fases'].keys()))
    dt_plantio = st.date_input("Data de Início:", date(2025, 12, 1))
    
    st.divider()
    st.markdown("### 🚚 Logística")
    carga = st.slider("Carga (kg):", 100, 1000, 400)

# --- 5. DASHBOARD PRINCIPAL ---
st.markdown(f"""
<div class="header-style">
    <h1>🛰️ Agro-Intel Ultimate</h1>
    <p>Monitoramento Profissional | <b>{cultura} - {variedade}</b></p>
</div>
""", unsafe_allow_html=True)

if api_w:
    # Carregamento seguro dos dados
    crop_data = BANCO_MASTER[cultura]
    var_data = crop_data['vars'][variedade]
    phase_data = crop_data['fases'][fase]
    
    # Previsão
    df = get_forecast(st.session_state.lat, st.session_state.lon, api_w, var_data['kc'], crop_data['t_base'])
    
    if not df.empty:
        # Cálculos de KPI
        hoje_dados = df.iloc[0]
        dias_campo = (date.today() - dt_plantio).days
        gda_acum = dias_campo * (df['GDA'].sum() / 5) # Estimativa média diária baseada nos 5 dias
        gda_meta = var_data['gda_meta']
        
        # Exibição de KPIs
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("🌡️ Temperatura Agora", f"{hoje_dados['Temp']:.1f}°C")
        k2.metric("💧 Umidade Relativa", f"{hoje_dados['Umid']}%")
        k3.metric("💦 ETc (Demanda Hídrica)", f"{hoje_dados['ETc']} mm/3h")
        k4.metric("📅 Dias de Campo", f"{dias_campo}", f"Meta GDA: {gda_meta}")

        # --- ABAS DO SISTEMA ---
        tabs = st.tabs(["🎓 Consultoria Técnica", "📊 Clima & Chuva", "📡 Radar Regional", "👁️ IA Vision", "🗺️ Mapa", "🚚 Logística"])

        # 1. CONSULTORIA TÉCNICA
        with tabs[0]:
            col_left, col_right = st.columns([1, 1])
            
            with col_left:
                st.markdown(f"### 🔥 Status de Maturação")
                

                progresso = min(1.0, gda_acum / gda_meta)
                st.progress(progresso)
                st.caption(f"Acúmulo Térmico: {gda_acum:.0f} GDA (Estimado)")
                
                # Matriz de Risco
                st.markdown("### 🛡️ Matriz de Risco Fitossanitário")
                risco = "BAIXO"
                cor_risco = "alert-low"
                msg_risco = "Condições favoráveis. Manter preventivos."
                
                if hoje_dados['Umid'] > 85 and hoje_dados['Temp'] < 22:
                    risco = "CRÍTICO (Requeima/Mofo)"
                    cor_risco = "alert-high"
                    msg_risco = "🚨 ALERTA: Frio + Umidade Alta. Favorável a Oomicetos. Usar Sistêmicos."
                elif hoje_dados['Umid'] > 80 and hoje_dados['Temp'] > 25:
                    risco = "ALTO (Bacterioses/Alternária)"
                    cor_risco = "alert-high"
                    msg_risco = "🚨 ALERTA: Calor + Umidade. Risco de doenças bacterianas."
                
                st.markdown(f"""<div class="{cor_risco}">RISCO: {risco}<br>{msg_risco}</div>""", unsafe_allow_html=True)
                

                st.markdown(f"""
                <div class="tech-card">
                    <h4>🧬 Fisiologia da Fase: {fase}</h4>
                    <p>{phase_data['fisio']}</p>
                    <hr>
                    <p><b>🔍 Principais Riscos:</b> {phase_data['riscos']}</p>
                </div>
                """, unsafe_allow_html=True)
                
            with col_right:
                st.markdown(f"""
                <div class="tech-card">
                    <h4>🛠️ Manejo Técnico Recomendado</h4>
                    <p>{phase_data['desc']}</p>
                </div>
                <div class="chem-card">
                    <h4>🧪 Prescrição Química (Sugestão)</h4>
                    <p>{phase_data['quimica']}</p>
                </div>
                <div class="tech-card" style="border-left: 5px solid #ff9800;">
                    <h4>🌿 Manejo Biológico & Regenerativo</h4>
                    <p>{phase_data['bio']}</p>
                </div>
                """, unsafe_allow_html=True)

        # 2. CLIMA E CHUVA
        with tabs[1]:
            st.markdown("### 🌦️ Previsão Detalhada (5 Dias / 3h)")
            
            # Gráfico Combinado
            fig = go.Figure()
            fig.add_trace(go.Bar(x=df['Data'], y=df['Chuva'], name='Chuva (mm)', marker_color='#2196f3', yaxis='y'))
            fig.add_trace(go.Scatter(x=df['Data'], y=df['Temp'], name='Temp (°C)', line=dict(color='#ff9800', width=2), yaxis='y2'))
            
            fig.update_layout(
                yaxis=dict(title="Chuva (mm)", side="left"),
                yaxis2=dict(title="Temp (°C)", side="right", overlaying="y"),
                hovermode="x unified",
                template="plotly_white",
                height=500
            )
            st.plotly_chart(fig, use_container_width=True)
            
            st.dataframe(df[['Data', 'Temp', 'Umid', 'Chuva', 'VPD', 'Descrição']], use_container_width=True)

        # 3. RADAR REGIONAL
        with tabs[2]:
            st.markdown("### 📡 Monitoramento de Vizinhança (Raio 15km)")
            st.info("Monitoramento em tempo real dos pontos cardeais para antecipar frentes de chuva.")
            
            radar_df = get_radar_regional(st.session_state.lat, st.session_state.lon, api_w)
            
            if not radar_df.empty:
                c_rad = st.columns(4)
                for i, row in radar_df.iterrows():
                    cor_bg = "#ffcdd2" if row['Chuva'] == "SIM" else "#c8e6c9"
                    with c_rad[i]:
                        st.markdown(f"""
                        <div class="radar-box" style="background-color: {cor_bg};">
                            <h3>{row['Local']}</h3>
                            <h2>{row['Temp']:.1f}°C</h2>
                            <p>{row['Condição']}</p>
                            <p><b>Chuva: {row['Chuva']}</b></p>
                        </div>
                        """, unsafe_allow_html=True)
            else:
                st.warning("Não foi possível carregar os dados do radar. Verifique a conexão.")

        # 4. IA VISION
        with tabs[3]:
            st.markdown("### 👁️ Diagnóstico Fitossanitário com Gemini Pro")
            st.write("Tire uma foto da folha afetada ou do inseto. A IA analisará com base na cultura selecionada.")
            
            if api_g:
                img_file = st.camera_input("Capturar Imagem")
                if img_file:
                    image = Image.open(img_file)
                    st.image(image, caption="Imagem Capturada", width=300)
                    
                    with st.spinner("🔍 Analisando sintomas com Inteligência Artificial..."):
                        try:
                            genai.configure(api_key=api_g)
                            model = genai.GenerativeModel('gemini-1.5-flash')
                            prompt = f"""
                            Você é um Engenheiro Agrônomo Sênior. 
                            Analise esta imagem de {cultura} (Variedade: {variedade}).
                            Estágio atual: {fase}.
                            Identifique: 
                            1. Possíveis pragas ou doenças visíveis.
                            2. Deficiências nutricionais, se houver.
                            3. Recomende o controle químico e biológico imediato.
                            Seja técnico e direto.
                            """
                            response = model.generate_content([prompt, image])
                            st.success("Análise Concluída:")
                            st.markdown(response.text)
                        except Exception as e:
                            st.error(f"Erro na IA: {e}")
            else:
                st.warning("⚠️ Insira a chave da API Gemini no menu lateral para usar este recurso.")

        # 5. MAPA
        with tabs[4]:
            st.markdown("### 🗺️ Visualização de Satélite")
            m = folium.Map(location=[st.session_state.lat, st.session_state.lon], zoom_start=15)
            folium.TileLayer(
                tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
                attr='Esri',
                name='Esri Satélite',
                overlay=False,
                control=True
            ).add_to(m)
            
            folium.Marker(
                [st.session_state.lat, st.session_state.lon],
                popup="Sede / Ponto de Monitoramento",
                icon=folium.Icon(color="green", icon="leaf")
            ).add_to(m)
            
            LocateControl().add_to(m)
            Fullscreen().add_to(m)
            st_folium(m, width="100%", height=600)

        # 6. LOGÍSTICA
        with tabs[5]:
            st.markdown("### 🚚 Calculadora de Frete e Viagem")
            
            c_log1, c_log2 = st.columns(2)
            with c_log1:
                distancia = st.number_input("Distância (km):", value=450)
                consumo = st.number_input("Consumo Veículo (km/L):", value=10.0)
                preco_comb = st.number_input("Preço Combustível (R$):", value=6.20)
            
            with c_log2:
                custo_total = (distancia / consumo) * preco_comb
                custo_kg = custo_total / carga
                ocupacao = (carga / 800) * 100 # Baseado numa Doblò/Strada (800kg)
                
                st.metric("Custo Total da Viagem", f"R$ {custo_total:.2f}")
                st.metric("Custo por Kg Transportado", f"R$ {custo_kg:.3f}")
                
                if ocupacao > 100:
                    st.error(f"⚠️ Sobrecarga! {ocupacao:.1f}% da capacidade estimada (800kg).")
                else:
                    st.info(f"Ocupação de Carga: {ocupacao:.1f}%")

else:
    st.info("👈 Por favor, insira a chave da OpenWeather API no menu lateral para iniciar o sistema.")
