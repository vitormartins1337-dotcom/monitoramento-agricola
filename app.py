import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
import math
import google.generativeai as genai
from PIL import Image
from datetime import datetime, date
import folium
from streamlit_folium import st_folium

# --- 1. CONFIGURAÇÃO VISUAL TITAN ---
st.set_page_config(
    page_title="Agro-Intel Titan",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilo Profissional de ERP
st.markdown("""
<style>
    .main { background-color: #f0f2f5; }
    div[data-testid="metric-container"] { background-color: #fff; border-left: 5px solid #1565c0; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
    .header-box { background: linear-gradient(135deg, #0d47a1 0%, #1976d2 100%); color: white; padding: 25px; border-radius: 10px; margin-bottom: 20px; box-shadow: 0 4px 10px rgba(0,0,0,0.2); }
    .tech-card { background-color: #fff; padding: 20px; border-radius: 8px; border: 1px solid #e0e0e0; margin-bottom: 15px; }
    .tech-header { color: #1565c0; font-weight: 700; font-size: 1.2em; border-bottom: 2px solid #f5f5f5; padding-bottom: 10px; margin-bottom: 15px; }
    .alert-high { background-color: #ffebee; border-left: 5px solid #d32f2f; padding: 15px; border-radius: 5px; color: #b71c1c; }
    .alert-low { background-color: #e8f5e9; border-left: 5px solid #2e7d32; padding: 15px; border-radius: 5px; color: #1b5e20; }
    .pivot-marker { font-size: 12px; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# --- 2. BANCO DE DADOS AGRONÔMICO COMPLETO (VARREDURA TOTAL) ---
BANCO_MASTER = {
    "Batata (Solanum tuberosum)": {
        "t_base": 7,
        "vars": {
            "Orchestra": {"kc": 1.15, "info": "Pele lisa premium. Exige K para acabamento. Sensível a Pinta Preta."},
            "Cupido": {"kc": 1.10, "info": "Ciclo ultra-curto. Colheita rápida. Extrema sensibilidade à Requeima."},
            "Camila": {"kc": 1.15, "info": "Mercado fresco. Cuidado com Sarna e danos mecânicos."},
            "Atlantic": {"kc": 1.15, "info": "Industrial (Chips). Monitorar Coração Oco e Matéria Seca."}
        },
        "fases": {
            "Emergência (0-15 dias)": {
                "desc": "Brotamento e estabelecimento inicial.",
                "fisiologia": "Dependência das reservas da batata-mãe. Raízes ainda explorando o sulco.",
                "manejo": "Não encharcar o solo (risco de apodrecimento da semente).",
                "quimica": "**Solo:** Azoxistrobina (Rizoctonia) + Tiametoxam (Pragas iniciais).\n**Foliar:** Ciromazina (Larva Minadora)."
            },
            "Vegetativo (15-35 dias)": {
                "desc": "Crescimento de hastes e folhas.",
                "fisiologia": "Alta demanda de N para índice de área foliar (IAF).",
                "manejo": "Realizar a **Amontoa** (Chegar terra). Monitorar Vaquinha.",
                "quimica": "Mancozeb/Clorotalonil (Preventivo). Acetamiprido (Vaquinha)."
            },
            "Tuberização/Gancho (35-50 dias)": {
                "desc": "Fase Crítica. Início da formação dos tubérculos.",
                "fisiologia": "Estresse hídrico agora causa Sarna Comum e abortamento. Queda de Giberelina.",
                "manejo": "Irrigação frequente e leve. Controle absoluto de Requeima.",
                "quimica": "**Requeima:** Metalaxil-M, Dimetomorfe, Mandipropamida (Revus), Fluazinam."
            },
            "Enchimento (50-80 dias)": {
                "desc": "Crescimento dos tubérculos.",
                "fisiologia": "Dreno forte de Potássio e Magnésio. Translocação intensa.",
                "manejo": "Monitorar Mosca Branca e Traça. Evitar excesso de N (folha em excesso).",
                "quimica": "**Mosca Branca:** Ciantraniliprole (Benévia), Espirotesifeno (Oberon).\n**Traça:** Clorfenapir, Espinosade."
            },
            "Maturação (80+ dias)": {
                "desc": "Senescência e pele.",
                "fisiologia": "Formação da suberina (pele).",
                "manejo": "Dessecação. Evitar solo úmido (Podridão Mole/Sarna).",
                "quimica": "Diquat (Dessecante)."
            }
        }
    },
    "Café (Coffea arabica)": {
        "t_base": 10,
        "vars": {
            "Catuaí": {"kc": 1.1, "info": "Suscetível a ferrugem. Alta qualidade de bebida."},
            "Arara": {"kc": 1.2, "info": "Resistente a ferrugem. Alta carga pendente (exige nutrição)."}
        },
        "fases": {
            "Dormência/Poda (Jul-Ago)": {
                "desc": "Repouso fisiológico.",
                "fisiologia": "Indução floral latente.",
                "manejo": "Poda de produção, calagem e gessagem.",
                "quimica": "Cobre (Preventivo Bacterioses)."
            },
            "Florada (Set-Out)": {
                "desc": "Abertura floral (Antese).",
                "fisiologia": "Alta demanda de Boro e Zinco.",
                "manejo": "Proteger polinizadores. Não aplicar inseticidas fortes.",
                "quimica": "Foliar: Ca + B + Zn."
            },
            "Chumbinho (Nov-Dez)": {
                "desc": "Expansão do fruto.",
                "fisiologia": "Divisão celular rápida. Déficit hídrico causa peneira baixa.",
                "manejo": "Controle de Cercospora e Ferrugem.",
                "quimica": "Ciproconazol + Azoxistrobina (Priori Xtra), Tebuconazol."
            },
            "Granação (Jan-Mar)": {
                "desc": "Enchimento de grão (Sólidos).",
                "fisiologia": "Pico de extração de K e N. Risco de escaldadura.",
                "manejo": "Monitorar Broca do Café.",
                "quimica": "**Broca:** Ciantraniliprole (Benévia), Clorantraniliprole (Voliam)."
            },
            "Maturação (Abr-Jun)": {
                "desc": "Mudança de cor (Cereja).",
                "fisiologia": "Acúmulo de açúcares.",
                "manejo": "Planejamento de colheita.",
                "quimica": "Evitar produtos com carência longa."
            }
        }
    },
    "Tomate (Mesa/Indústria)": {
        "t_base": 10,
        "vars": {
            "Italiano (Saladete)": {"kc": 1.2, "info": "Sensível a Fundo Preto (Cálcio)."},
            "Grape/Cereja": {"kc": 1.1, "info": "Sensível a rachadura por oscilação hídrica."}
        },
        "fases": {
            "Transplante/Pegamento": {
                "desc": "Estabelecimento.",
                "fisiologia": "Enraizamento.",
                "manejo": "Controle de Tripes (Vira-Cabeça) e Mosca Branca (Geminivírus).",
                "quimica": "Imidacloprido (Drench), Acetamiprido."
            },
            "Vegetativo": {
                "desc": "Crescimento vertical.",
                "fisiologia": "Formação de hastes.",
                "manejo": "Desbrota lateral. Condução.",
                "quimica": "Mancozeb (Preventivo)."
            },
            "Florada": {
                "desc": "Emissão de cachos.",
                "fisiologia": "Abortamento se T > 32°C.",
                "manejo": "Cálcio Foliar semanal.",
                "quimica": "Cálcio Quelatado. Azoxistrobina (Oídio)."
            },
            "Frutificação": {
                "desc": "Crescimento de frutos.",
                "fisiologia": "Dreno de Potássio.",
                "manejo": "Monitorar Tuta absoluta (Traça).",
                "quimica": "**Traça:** Clorfenapir, Indoxacarbe, Espinosade.\n**Requeima:** Mandipropamida."
            }
        }
    },
    "Mirtilo (Blueberry)": {
        "t_base": 7,
        "vars": {"Emerald": {"kc": 0.95, "info": "Vigorosa. pH 4.5."}, "Biloxi": {"kc": 0.90, "info": "Ereta. Poda central."}},
        "fases": {
            "Brotação": {"desc": "Fluxo vegetativo.", "fisiologia": "Reservas de raiz.", "manejo": "Monitorar Cochonilha.", "quimica": "Óleo Mineral + Imidacloprido."},
            "Florada": {"desc": "Polinização.", "fisiologia": "Abelhas aumentam calibre.", "manejo": "Colocar Bombus/Apis.", "quimica": "Fludioxonil (Switch) à noite (Botrytis)."},
            "Fruto Verde": {"desc": "Crescimento.", "fisiologia": "Não usar Nitrato.", "manejo": "Antracnose.", "quimica": "Azoxistrobina (Amistar)."},
            "Maturação": {"desc": "Cor Azul.", "fisiologia": "Brix.", "manejo": "Colheita delicada.", "quimica": "Biológicos (Bacillus)."}
        }
    },
    "Amora Preta (Blackberry)": {
        "t_base": 7,
        "vars": {"Tupy": {"kc": 1.0, "info": "Exige frio."}, "BRS Xingu": {"kc": 1.05, "info": "Sem espinhos."}},
        "fases": {
            "Brotação": {"desc": "Emissão de hastes.", "fisiologia": "Crescimento.", "manejo": "Ferrugem.", "quimica": "Tebuconazol."},
            "Florada": {"desc": "Flores.", "fisiologia": "Sensível a chuva.", "manejo": "Botrytis.", "quimica": "Iprodiona."},
            "Frutificação": {"desc": "Bagas.", "fisiologia": "Doce.", "manejo": "Drosófila (SWD).", "quimica": "Espinosade (Isca)."}
        }
    },
    "Framboesa (Raspberry)": {
        "t_base": 7,
        "vars": {"Heritage": {"kc": 1.1, "info": "Remontante."}, "Golden Bliss": {"kc": 1.05, "info": "Amarela."}},
        "fases": {
            "Brotação": {"desc": "Hastes do ano.", "fisiologia": "Vigor.", "manejo": "Ácaro Vermelho.", "quimica": "Abamectina."},
            "Florada": {"desc": "Flores brancas.", "fisiologia": "Polinização.", "manejo": "Podridão.", "quimica": "Ciprodinil."},
            "Colheita": {"desc": "Fruto maduro.", "fisiologia": "Perecível.", "manejo": "Colheita diária.", "quimica": "Nenhum (Carência)."}
        }
    },
    "Morango": {
        "t_base": 7,
        "vars": {"San Andreas": {"kc": 0.85, "info": "Dia Neutro."}, "Albion": {"kc": 0.85, "info": "Sabor."}},
        "fases": {
            "Plantio": {"desc": "Mudas.", "fisiologia": "Raiz.", "manejo": "Fungicida imersão.", "quimica": "Fosfito K."},
            "Vegetativo": {"desc": "Coroa.", "fisiologia": "Folhas.", "manejo": "Estolões.", "quimica": "Enxofre (Oídio)."},
            "Florada": {"desc": "Flores.", "fisiologia": "Polinização.", "manejo": "Botrytis.", "quimica": "Ciprodinil."},
            "Frutificação": {"desc": "Colheita.", "fisiologia": "K/Ca.", "manejo": "Ácaro Rajado.", "quimica": "Etoxazol (Ácaro)."}
        }
    }
}

# --- 3. FUNÇÕES CIENTÍFICAS E MAPA ---
def get_credentials():
    params = st.query_params
    return params.get("w_key", None), params.get("g_key", None)

def calc_agro(temp, umid):
    es = 0.61078 * math.exp((17.27 * temp) / (temp + 237.3))
    ea = es * (umid / 100)
    vpd = round(es - ea, 2)
    tw = temp * math.atan(0.151977 * (umid + 8.313659)**0.5) + math.atan(temp + umid) - math.atan(umid - 1.676331) + 0.00391838 * (umid)**1.5 * math.atan(0.023101 * umid) - 4.686035
    dt = round(temp - tw, 1)
    return dt, vpd

def get_forecast_detailed(api_key, lat, lon, kc, t_base):
    try:
        url = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={api_key}&units=metric&lang=pt_br"
        r = requests.get(url).json()
        dados = []
        for i in range(0, 40, 8):
            item = r['list'][i]
            t_media = item['main']['temp']
            gda_dia = max(0, t_media - t_base)
            dt, vpd = calc_agro(t_media, item['main']['humidity'])
            chuva = sum([r['list'][i+j].get('rain', {}).get('3h', 0) for j in range(8) if i+j < len(r['list'])])
            et0 = 0.0023 * (t_media + 17.8) * (t_media ** 0.5) * 0.408
            dados.append({'Data': datetime.fromtimestamp(item['dt']).strftime('%d/%m'), 'Temp': t_media, 'GDA': gda_dia, 'Chuva': round(chuva, 1), 'VPD': vpd, 'Delta T': dt, 'Umid': item['main']['humidity'], 'ETc': round(et0 * kc, 2)})
        return pd.DataFrame(dados)
    except: return pd.DataFrame()

# --- 4. SIDEBAR CONFIG ---
url_w, url_g = get_credentials()
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3058/3058995.png", width=70)
    st.header("🎛️ Centro de Comando")
    with st.expander("🔑 Acesso Rápido (Salvar Link)", expanded=not url_w):
        val_w = st.text_input("OpenWeather Key", value=url_w if url_w else "", type="password")
        val_g = st.text_input("Gemini AI Key", value=url_g if url_g else "", type="password")
        if st.button("🔗 Gerar Link Permanente"):
            st.query_params["w_key"] = val_w
            st.query_params["g_key"] = val_g
            st.success("Link gerado! Salve nos favoritos.")
            st.rerun()
    
    st.divider()
    cultura_sel = st.selectbox("Cultura:", list(BANCO_MASTER.keys()))
    var_sel = st.selectbox("Cultivar:", list(BANCO_MASTER[cultura_sel]['vars'].keys()))
    fase_sel = st.selectbox("Fase Fenológica:", list(BANCO_MASTER[cultura_sel]['fases'].keys()))
    
    if 'd_plantio' not in st.session_state: st.session_state['d_plantio'] = date(2025, 11, 25)
    d_plantio = st.date_input("Data Início/Poda:", st.session_state['d_plantio'])
    info_v = BANCO_MASTER[cultura_sel]['vars'][var_sel]
    
    # Edição de Pivôs para o Mapa
    with st.expander("📍 Configurar Pivôs (Mapa)"):
        if 'pivos' not in st.session_state:
            # Pivôs Exemplo - Fazenda Progresso (Simulados na região)
            st.session_state['pivos'] = [
                {"nome": "Pivô 01 - Batata", "lat": -13.200, "lon": -41.400},
                {"nome": "Pivô 02 - Café", "lat": -13.205, "lon": -41.405},
                {"nome": "Pivô 03 - Tomate", "lat": -13.210, "lon": -41.402}
            ]
        
        nome_p = st.text_input("Nome Pivô")
        lat_p = st.number_input("Lat", value=-13.200, format="%.5f")
        lon_p = st.number_input("Lon", value=-41.400, format="%.5f")
        if st.button("Adicionar Pivô"):
            st.session_state['pivos'].append({"nome": nome_p, "lat": lat_p, "lon": lon_p})
            st.success("Adicionado!")

# --- 5. DASHBOARD TITAN ---
st.title("🛰️ Agro-Intel Titan v14.0")

if val_w:
    lat_sede, lon_sede = "-13.200", "-41.400" # Coordenadas base da Fazenda Progresso (Aprox)
    df = get_forecast_detailed(val_w, lat_sede, lon_sede, info_v['kc'], BANCO_MASTER[cultura_sel]['t_base'])
    
    if not df.empty:
        hoje = df.iloc[0]
        st.markdown(f"""
        <div class="header-box">
            <h2>Fazenda Progresso - {cultura_sel} ({var_sel})</h2>
            <p>Fase: <b>{fase_sel}</b> | Atenção: {info_v['info']}</p>
        </div>
        """, unsafe_allow_html=True)
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("🌡️ Temperatura", f"{hoje['Temp']:.1f}°C", f"Umid: {hoje['Umid']}%")
        c2.metric("💧 VPD (Pressão)", f"{hoje['VPD']} kPa", "Ideal" if 0.4 <= hoje['VPD'] <= 1.3 else "Alerta")
        c3.metric("💦 Consumo (ETc)", f"{hoje['ETc']} mm", f"Kc: {info_v['kc']}")
        c4.metric("🛡️ Delta T", f"{hoje['Delta T']}°C", "Ok" if 2 <= hoje['Delta T'] <= 8 else "Ruim")
        
        # ABAS PRINCIPAIS
        tabs = st.tabs(["🗺️ Minha Fazenda (Mapa)", "🎓 Consultoria Técnica", "📊 Clima", "👁️ IA Vision", "💰 Custos"])
        
        # --- ABA 1: MAPA MINHA FAZENDA (NOVO!) ---
        with tabs[0]:
            st.markdown("### 🛰️ Mapeamento de Pivôs - Fazenda Progresso")
            st.write("Visão de satélite georreferenciada para localização e gerenciamento.")
            
            # Criação do Mapa Folium com Satélite (Esri WorldImagery)
            m = folium.Map(location=[st.session_state['pivos'][0]['lat'], st.session_state['pivos'][0]['lon']], zoom_start=14)
            folium.TileLayer(
                tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
                attr='Esri',
                name='Esri Satellite',
                overlay=False,
                control=True
            ).add_to(m)
            
            # Adicionar Marcadores dos Pivôs
            for pivo in st.session_state['pivos']:
                folium.Marker(
                    [pivo['lat'], pivo['lon']], 
                    popup=pivo['nome'], 
                    tooltip=pivo['nome'],
                    icon=folium.Icon(color='green', icon='leaf')
                ).add_to(m)
            
            # Renderizar no Streamlit
            st_folium(m, width="100%", height=500)
            
            st.info("💡 Dica: Use o menu lateral 'Configurar Pivôs' para adicionar as coordenadas exatas dos seus equipamentos.")

        # --- ABA 2: CONSULTORIA ---
        with tabs[1]:
            dados = BANCO_MASTER[cultura_sel]['fases'][fase_sel]
            
            # Matriz Climática
            risco = "Baixo"; msg = "Clima favorável. Use **Protetores (Mancozeb/Cobre)**."; estilo = "alert-low"
            if hoje['Umid'] > 85 or hoje['Chuva'] > 2: risco="ALTO"; msg="🚨 **UMIDADE ALTA:** Pressão severa. Use **SISTÊMICOS**."; estilo="alert-high"
            
            c_esq, c_dir = st.columns(2)
            with c_esq:
                st.markdown(f"""<div class="tech-card"><div class="tech-header">🧬 Fisiologia da Fase</div><p><b>Ocorrência:</b> {dados['desc']}</p><p><b>Internamente:</b> {dados['fisiologia']}</p></div>""", unsafe_allow_html=True)
                st.markdown(f"""<div class="{estilo}"><strong>☁️ Matriz Climática de Hoje</strong><br>{msg}</div>""", unsafe_allow_html=True)
            with c_dir:
                st.markdown(f"""<div class="tech-card"><div class="tech-header">🛠️ Plano de Manejo</div><p><b>Cultural:</b> {dados['manejo']}</p><hr><p><b>🧪 Químico:</b> {dados['quimica']}</p></div>""", unsafe_allow_html=True)

        # --- ABA 3: CLIMA ---
        with tabs[2]:
            fig = go.Figure()
            fig.add_trace(go.Bar(x=df['Data'], y=df['Chuva'], name='Chuva', marker_color='#29b6f6'))
            fig.add_trace(go.Scatter(x=df['Data'], y=df['ETc'], name='ETc', line=dict(color='#ef5350', width=3)))
            st.plotly_chart(fig, use_container_width=True)
            st.info(f"Balanço Hídrico Semanal: {df['Chuva'].sum() - df['ETc'].sum():.1f} mm")

        # --- ABA 4: IA ---
        with tabs[3]:
            st.write("Diagnóstico Fitopatológico")
            img = st.camera_input("Foto")
            if img and val_g:
                genai.configure(api_key=val_g)
                with st.spinner("Analisando..."):
                    st.success(genai.GenerativeModel('gemini-1.5-flash').generate_content([f"Agrônomo. Analise imagem de {cultura_sel}. Fase {fase_sel}. Diagnóstico e Solução.", Image.open(img)]).text)

        # --- ABA 5: CUSTOS ---
        with tabs[4]:
            if 'custos' not in st.session_state: st.session_state['custos'] = []
            c1, c2 = st.columns(2)
            i = c1.text_input("Item"); v = c2.number_input("R$")
            if c2.button("Lançar"): st.session_state['custos'].append({"Item": i, "Valor": v}); st.success("Ok")
            if st.session_state['custos']: st.dataframe(pd.DataFrame(st.session_state['custos'])); st.metric("Total", f"R$ {pd.DataFrame(st.session_state['custos'])['Valor'].sum()}")

else:
    st.warning("⚠️ Configure suas chaves no menu lateral e clique em 'Gerar Link'.")
