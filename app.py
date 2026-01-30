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
    .header-main { 
        background: linear-gradient(90deg, #1b5e20 0%, #2e7d32 100%); 
        padding: 20px; 
        border-radius: 12px; 
        color: white; 
        margin-bottom: 20px; 
        box-shadow: 0 4px 10px rgba(0,0,0,0.1); 
    }
    .header-info { font-size: 1.1em; opacity: 0.9; margin-top: 5px; }
    .stMetric { background-color: white; border: 1px solid #e0e0e0; border-radius: 10px; padding: 15px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }
    .tech-card { background: white; padding: 20px; border-radius: 12px; border-left: 5px solid #2e7d32; box-shadow: 0 2px 5px rgba(0,0,0,0.05); margin-bottom: 15px; }
    .chem-card { background: white; padding: 20px; border-radius: 12px; border-left: 5px solid #d32f2f; box-shadow: 0 2px 5px rgba(0,0,0,0.05); margin-bottom: 15px; }
    .bio-card { background: white; padding: 20px; border-radius: 12px; border-left: 5px solid #fbc02d; box-shadow: 0 2px 5px rgba(0,0,0,0.05); margin-bottom: 15px; }
    h3 { color: #1b5e20; margin-bottom: 15px; }
</style>
""", unsafe_allow_html=True)

# --- 2. BANCO DE DADOS AGRONÔMICO (PADRONIZADO E COMPLETO) ---
# Chaves obrigatórias em todas as fases: 'desc', 'fisio', 'riscos', 'quim', 'bio', 'manejo'
BANCO_MASTER = {
    "Batata (Solanum tuberosum)": {
        "t_base": 7,
        "vars": {
            "Orchestra": {"kc": 1.15, "gda_meta": 1600, "info": "Pele lisa premium. Exige K e B."},
            "Cupido": {"kc": 1.10, "gda_meta": 1400, "info": "Ciclo ultra-curto. Sensível a Requeima."},
            "Camila": {"kc": 1.15, "gda_meta": 1550, "info": "Mercado fresco. Cuidado com Sarna."},
            "Atlantic": {"kc": 1.15, "gda_meta": 1650, "info": "Chips. Cuidado com Coração Oco."}
        },
        "fases": {
            "Emergência (0-20 dias)": {
                "desc": "Brotamento.", "fisio": "Uso de reservas da mãe.", "manejo": "Solo aerado.", 
                "riscos": "Rhizoctonia, Pectobacterium.",
                "quim": "Azoxistrobina + Tiametoxam.", "bio": "Trichoderma no sulco."
            },
            "Vegetativo (20-35 dias)": {
                "desc": "Expansão Foliar.", "fisio": "Alta demanda N.", "manejo": "Amontoa.", 
                "riscos": "Vaquinha, Minadora.",
                "quim": "Mancozeb, Clorotalonil.", "bio": "Beauveria bassiana."
            },
            "Tuberização (35-50 dias)": {
                "desc": "Ganchos.", "fisio": "Inversão hormonal.", "manejo": "Irrigação crítica.", 
                "riscos": "Requeima, Sarna.",
                "quim": "Revus, Metalaxil-M.", "bio": "Bacillus subtilis."
            },
            "Enchimento (50-80 dias)": {
                "desc": "Expansão.", "fisio": "Dreno de K.", "manejo": "Sanidade total.", 
                "riscos": "Mosca Branca, Traça, Pinta Preta.",
                "quim": "Benévia, Espirotesifeno.", "bio": "Extrato de Algas + K."
            },
            "Maturação (80+ dias)": {
                "desc": "Cura da pele.", "fisio": "Suberização.", "manejo": "Dessecação.", 
                "riscos": "Podridão mole.",
                "quim": "Diquat.", "bio": "Suspender Nitrogênio."
            }
        }
    },
    "Café (Coffea arabica)": {
        "t_base": 10,
        "vars": {
            "Catuaí": {"kc": 1.1, "gda_meta": 3000, "info": "Qualidade bebida. Sensível ferrugem."},
            "Arara": {"kc": 1.2, "gda_meta": 2900, "info": "Resistente ferrugem. Alta carga."}
        },
        "fases": {
            "Florada": {
                "desc": "Antese.", "fisio": "Demanda B e Zn.", "manejo": "Polinização.", 
                "riscos": "Phoma, Mancha Aureolada.",
                "quim": "Boscalida, Piraclostrobina.", "bio": "Cálcio e Boro foliar."
            },
            "Chumbinho": {
                "desc": "Expansão inicial.", "fisio": "Divisão celular.", "manejo": "Adubação N.", 
                "riscos": "Cercospora, Ferrugem.",
                "quim": "Priori Xtra, Cobre.", "bio": "Aminoácidos."
            },
            "Granação": {
                "desc": "Enchimento.", "fisio": "Dreno de potássio.", "manejo": "Monitorar Broca.", 
                "riscos": "Broca do Café.",
                "quim": "Ciantraniliprole.", "bio": "Beauveria bassiana."
            },
            "Maturação": {
                "desc": "Cereja.", "fisio": "Açúcares.", "manejo": "Pré-colheita.", 
                "riscos": "Queda de frutos.",
                "quim": "Nenhum (Carência).", "bio": "Potássio final."
            }
        }
    },
    "Tomate (Solanum lycopersicum)": {
        "t_base": 10,
        "vars": {
            "Italiano": {"kc": 1.2, "gda_meta": 1600, "info": "Fundo preto (Ca)."},
            "Grape": {"kc": 1.1, "gda_meta": 1450, "info": "Rachadura (Brix)."}
        },
        "fases": {
            "Vegetativo": {
                "desc": "Estruturação.", "fisio": "Enraizamento.", "manejo": "Desbrota.", 
                "riscos": "Tripes, Geminivírus.",
                "quim": "Imidacloprido, Espinetoram.", "bio": "Óleo de Neem."
            },
            "Florada": {
                "desc": "Pegamento.", "fisio": "Polinização.", "manejo": "Vibração.", 
                "riscos": "Oídio, Botrytis.",
                "quim": "Azoxistrobina.", "bio": "Cálcio Quelatado."
            },
            "Frutificação": {
                "desc": "Engorda.", "fisio": "Dreno K.", "manejo": "Condução.", 
                "riscos": "Traça (Tuta), Requeima.",
                "quim": "Clorfenapir, Dimetomorfe.", "bio": "Bacillus thuringiensis."
            },
            "Colheita": {
                "desc": "Maturação.", "fisio": "Etileno.", "manejo": "Colheita delicada.", 
                "riscos": "Pós-colheita.",
                "quim": "Carência curta.", "bio": "Conservantes naturais."
            }
        }
    },
    "Mirtilo (Blueberry)": {
        "t_base": 7,
        "vars": {
            "Emerald": {"kc": 0.95, "gda_meta": 1800, "info": "pH 4.5. Vigorosa."},
            "Biloxi": {"kc": 0.90, "gda_meta": 1900, "info": "Baixo frio. Rústica."}
        },
        "fases": {
            "Brotação": {
                "desc": "Folhas novas.", "fisio": "Reservas.", "manejo": "pH ácido.", 
                "riscos": "Cochonilhas.",
                "quim": "Óleo Mineral.", "bio": "Bokashi."
            },
            "Florada": {
                "desc": "Flores.", "fisio": "Sensível abortamento.", "manejo": "Polinizadores.", 
                "riscos": "Botrytis.",
                "quim": "Fludioxonil (Switch).", "bio": "Boro."
            },
            "Fruto Verde": {
                "desc": "Crescimento.", "fisio": "Divisão celular.", "manejo": "Nutrição K.", 
                "riscos": "Antracnose.",
                "quim": "Azoxistrobina.", "bio": "Ácidos Fúlvicos."
            },
            "Maturação": {
                "desc": "Cor (Blue).", "fisio": "Antocianinas.", "manejo": "Colheita.", 
                "riscos": "Drosófila.",
                "quim": "Espinosade.", "bio": "Iscas atrativas."
            }
        }
    },
    "Morango": {
        "t_base": 7,
        "vars": {
            "San Andreas": {"kc": 0.85, "gda_meta": 1200, "info": "Dia neutro. Ácaros."},
            "Albion": {"kc": 0.85, "gda_meta": 1250, "info": "Sabor. Oídio."}
        },
        "fases": {
            "Vegetativo": {
                "desc": "Coroa.", "fisio": "Folhas.", "manejo": "Limpeza.", 
                "riscos": "Oídio, Ácaro.",
                "quim": "Enxofre, Abamectina.", "bio": "Silício."
            },
            "Florada": {
                "desc": "Flores.", "fisio": "Polinização.", "manejo": "Ventilação.", 
                "riscos": "Mofo Cinzento.",
                "quim": "Iprodiona.", "bio": "Clonostachys rosea."
            },
            "Colheita": {
                "desc": "Fruto.", "fisio": "Açúcares.", "manejo": "Diário.", 
                "riscos": "Podridão.",
                "quim": "Ciprodinil.", "bio": "Cálcio."
            }
        }
    },
    "Amora": {
        "t_base": 7,
        "vars": {
            "Tupy": {"kc": 1.0, "gda_meta": 1500, "info": "Exige frio. Espinhos."},
            "Xingu": {"kc": 1.05, "gda_meta": 1400, "info": "Sem espinhos. Produtiva."}
        },
        "fases": {
            "Brotação": {
                "desc": "Hastes.", "fisio": "Vigor.", "manejo": "Tutoramento.", 
                "riscos": "Ferrugem.",
                "quim": "Tebuconazol.", "bio": "Calda Bordalesa."
            },
            "Florada": {
                "desc": "Flores.", "fisio": "Polinização.", "manejo": "Abelhas.", 
                "riscos": "Botrytis.",
                "quim": "Captana.", "bio": "Cálcio Boro."
            },
            "Frutificação": {
                "desc": "Bagas.", "fisio": "Açúcar.", "manejo": "Colheita.", 
                "riscos": "Drosófila.",
                "quim": "Espinosade.", "bio": "Armadilhas."
            }
        }
    },
    "Framboesa": {
        "t_base": 7,
        "vars": {
            "Heritage": {"kc": 1.1, "gda_meta": 1300, "info": "Vermelha. Remontante."},
            "Golden": {"kc": 1.05, "gda_meta": 1250, "info": "Amarela. Suave."}
        },
        "fases": {
            "Brotação": {
                "desc": "Hastes.", "fisio": "Vigor.", "manejo": "Desbaste.", 
                "riscos": "Ácaros.",
                "quim": "Abamectina.", "bio": "Enxofre."
            },
            "Florada": {
                "desc": "Flores.", "fisio": "Sensível chuva.", "manejo": "Túnel.", 
                "riscos": "Podridão.",
                "quim": "Iprodiona.", "bio": "Bioestimulante."
            },
            "Frutificação": {
                "desc": "Colheita.", "fisio": "Perecível.", "manejo": "Refrigeração.", 
                "riscos": "Fungos pós-colheita.",
                "quim": "Azoxistrobina.", "bio": "Quitosana."
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
                    'Desc': item['weather'][0]['description'].title()
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

# --- 4. SIDEBAR (CONFIGURAÇÕES) ---
with st.sidebar:
    st.header("⚙️ Configurações")
    api_w = st.secrets.get("OPENWEATHER_KEY", "")
    api_g = st.secrets.get("GEMINI_KEY", "")
    
    st.markdown("### 📍 Localização")
    tab_c, tab_g = st.tabs(["Cidade", "GPS"])
    
    if 'lat' not in st.session_state: st.session_state.lat = -13.2000
    if 'lon' not in st.session_state: st.session_state.lon = -41.4000
    
    with tab_c:
        cid = st.text_input("Cidade:", placeholder="Ex: Ibicoara, BA")
        if st.button("Buscar") and api_w:
            nlat, nlon = get_coords(cid, api_w)
            if nlat: 
                st.session_state.lat, st.session_state.lon = nlat, nlon
                st.rerun()
                
    with tab_g:
        st.session_state.lat = st.number_input("Lat:", value=st.session_state.lat, format="%.4f")
        st.session_state.lon = st.number_input("Lon:", value=st.session_state.lon, format="%.4f")
        
    st.divider()
    cultura = st.selectbox("Cultura:", list(BANCO_MASTER.keys()))
    variedade = st.selectbox("Variedade:", list(BANCO_MASTER[cultura]['vars'].keys()))
    fase = st.selectbox("Fase Atual:", list(BANCO_MASTER[cultura]['fases'].keys()))
    dt_inicio = st.date_input("Início Ciclo:", date(2025, 12, 1))

# --- 5. DASHBOARD PRINCIPAL (LAYOUT REVISADO) ---
if api_w:
    # 1. Carregar Dados
    c_db = BANCO_MASTER[cultura]
    v_db = c_db['vars'][variedade]
    f_db = c_db['fases'][fase]
    
    # 2. Previsão
    df = get_forecast(st.session_state.lat, st.session_state.lon, api_w, v_db['kc'], c_db['t_base'])
    
    if not df.empty:
        hoje = df.iloc[0]
        dias = (date.today() - dt_inicio).days
        gda_acum = dias * (df['GDA'].sum() / 5 * 8) # Estimativa
        
        # --- CABEÇALHO DINÂMICO ---
        st.markdown(f"""
        <div class="header-main">
            <h1 style="margin:0">Agro-Intel</h1>
            <div class="header-info">
                <b>{cultura} - {variedade}</b> | Idade: {dias} dias | GDA: {gda_acum:.0f}
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # --- METRICAS NO TOPO (PRIORIDADE) ---
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("🌡️ Temperatura", f"{hoje['Temp']:.1f}°C")
        m2.metric("💧 Umidade", f"{hoje['Umid']}%")
        m3.metric("💦 ETc (Demanda)", f"{hoje['ETc']} mm")
        m4.metric("🌧️ Chuva (3h)", f"{hoje['Chuva']} mm")
        
        # --- ABAS ---
        tabs = st.tabs(["🎓 Consultoria Técnica", "📊 Clima Detalhado", "📡 Radar", "👁️ IA Vision", "🗺️ Mapa", "🚚 Logística"])
        
        # ABA 1: CONSULTORIA (FIXED KEY ERROR)
        with tabs[0]:
            st.info(f"🧬 **Genética:** {v_db['info']}")
            
            
            st.markdown(f"**Progresso Térmico:** {gda_acum:.0f} / {v_db['gda_meta']} GDA")
            st.progress(min(1.0, gda_acum/v_db['gda_meta']))
            
            # Alerta de Risco
            risco = "BAIXO"
            cor = "alert-low"
            if hoje['Umid'] > 85: 
                risco = "ALTO (Fungos)"
                cor = "alert-high"
            
            st.markdown(f"<div class='{cor}'>RISCO FITOSSANITÁRIO: {risco}</div>", unsafe_allow_html=True)
            
            

            c_esq, c_dir = st.columns(2)
            with c_esq:
                st.markdown(f"""
                <div class="tech-card">
                    <h3>🧬 Fisiologia & Riscos</h3>
                    <p><b>O que ocorre:</b> {f_db['fisio']}</p>
                    <hr>
                    <p><b>⚠️ Principais Riscos:</b> {f_db['riscos']}</p>
                </div>
                <div class="bio-card">
                    <h3>🌿 Biológico & Nutrição</h3>
                    <p>{f_db['bio']}</p>
                </div>
                """, unsafe_allow_html=True)
            
            with c_dir:
                st.markdown(f"""
                <div class="tech-card">
                    <h3>🚜 Manejo Cultural</h3>
                    <p>{f_db['desc']}</p>
                    <p><b>Ação:</b> {f_db['manejo']}</p>
                </div>
                <div class="chem-card">
                    <h3>🧪 Controle Químico</h3>
                    <p>{f_db['quim']}</p>
                </div>
                """, unsafe_allow_html=True)

        # ABA 2: CLIMA
        with tabs[1]:
            fig = go.Figure()
            fig.add_trace(go.Bar(x=df['Data'], y=df['Chuva'], name='Chuva', marker_color='#2196f3'))
            fig.add_trace(go.Scatter(x=df['Data'], y=df['ETc'], name='ETc', line=dict(color='#d32f2f', width=3)))
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(df, use_container_width=True)

        # ABA 3: RADAR
        with tabs[2]:
            st.markdown("### 📡 Monitoramento Regional (15km)")
            r_df = get_radar(st.session_state.lat, st.session_state.lon, api_w)
            if not r_df.empty:
                cols = st.columns(4)
                for i, row in r_df.iterrows():
                    bg = "#ffebee" if row['Chuva'] == "SIM" else "#e8f5e9"
                    with cols[i]:
                        st.markdown(f"""
                        <div style="background:{bg}; padding:10px; border-radius:10px; text-align:center; border:1px solid #ccc">
                            <b>{row['Loc']}</b><br>{row['T']:.1f}°C<br>Chuva: {row['Chuva']}
                        </div>
                        """, unsafe_allow_html=True)

        # ABA 4: IA
        with tabs[3]:
            if api_g:
                foto = st.camera_input("Scanner Fitossanitário")
                if foto:
                    genai.configure(api_key=api_g)
                    res = genai.GenerativeModel('gemini-1.5-flash').generate_content([f"Agrônomo. Analise {cultura} {variedade} fase {fase}. Sintomas e Solução.", Image.open(foto)])
                    st.success(res.text)
            else: st.warning("Chave Gemini não configurada.")

        # ABA 5: MAPA
        with tabs[4]:
            m = folium.Map([st.session_state.lat, st.session_state.lon], zoom_start=15)
            folium.TileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', attr='Esri', name='Satélite').add_to(m)
            st_folium(m, width="100%", height=500)

        # ABA 6: LOGISTICA
        with tabs[5]:
            c_log1, c_log2 = st.columns(2)
            with c_log1:
                dist = st.number_input("Distância (km):", value=450)
                cons = st.number_input("Consumo (km/L):", value=10.0)
                prc = st.number_input("Preço Comb. (R$):", value=6.20)
                peso = st.slider("Carga (kg):", 100, 1000, 400)
            with c_log2:
                tot = (dist/cons)*prc
                st.metric("Custo Viagem", f"R$ {tot:.2f}")
                st.metric("Custo/Kg", f"R$ {tot/peso:.2f}")

else:
    st.info("👈 Configure a API OpenWeather no menu lateral.")
