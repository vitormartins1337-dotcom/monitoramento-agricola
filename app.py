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
st.set_page_config(page_title="Agro-Intel Field", page_icon="🚜", layout="wide", initial_sidebar_state="expanded")

# CSS Profissional
st.markdown("""
<style>
    .main { background-color: #f8f9fa; }
    div[data-testid="metric-container"] { background-color: #fff; border-left: 5px solid #1e3a8a; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
    .header-box { background: linear-gradient(135deg, #0f2027 0%, #203a43 50%, #2c5364 100%); color: white; padding: 25px; border-radius: 10px; margin-bottom: 20px; box-shadow: 0 4px 8px rgba(0,0,0,0.2); }
    .tech-card { background-color: #fff; padding: 20px; border-radius: 8px; border: 1px solid #e0e0e0; margin-bottom: 15px; }
    .tech-header { color: #1e3a8a; font-weight: 700; font-size: 1.1em; border-bottom: 2px solid #f0f0f0; padding-bottom: 10px; margin-bottom: 15px; }
    .alert-high { background-color: #fef2f2; border-left: 5px solid #ef4444; padding: 15px; border-radius: 5px; color: #991b1b; }
    .alert-low { background-color: #f0fdf4; border-left: 5px solid #22c55e; padding: 15px; border-radius: 5px; color: #166534; }
    h3 { margin-top: 0; }
</style>
""", unsafe_allow_html=True)

# --- 2. CÉREBRO AGRONÔMICO (DADOS MANTIDOS) ---
BANCO_MASTER = {
    "Batata (Solanum tuberosum)": {
        "t_base": 7,
        "vars": {
            "Orchestra": {"kc": 1.15, "info": "Pele lisa. Exige K para acabamento. Sensível a Pinta Preta."},
            "Cupido": {"kc": 1.10, "info": "Ciclo curto. Sensível à Requeima."},
            "Camila": {"kc": 1.15, "info": "Mercado fresco. Cuidado com Sarna."},
            "Atlantic": {"kc": 1.15, "info": "Indústria. Monitorar Coração Oco."}
        },
        "fases": {
            "Emergência": {"desc": "Brotamento.", "fisiologia": "Uso de reservas da mãe.", "manejo": "Solo aerado. Monitorar Rizoctonia.", "quimica": "Solo: Azoxistrobina. Foliar: Ciromazina."},
            "Vegetativo": {"desc": "Crescimento.", "fisiologia": "Alta demanda N.", "manejo": "Amontoa.", "quimica": "Mancozeb (Preventivo)."},
            "Tuberização": {"desc": "Fase Crítica.", "fisiologia": "Inversão hormonal.", "manejo": "Água constante.", "quimica": "Requeima: Metalaxil-M, Dimetomorfe."},
            "Enchimento": {"desc": "Engorda.", "fisiologia": "Dreno de K.", "manejo": "Monitorar Mosca Branca.", "quimica": "Mosca: Ciantraniliprole."},
            "Maturação": {"desc": "Pele.", "fisiologia": "Suberização.", "manejo": "Dessecação.", "quimica": "Diquat."}
        }
    },
    "Café (Coffea arabica)": {
        "t_base": 10,
        "vars": {"Catuaí": {"kc": 1.1, "info": "Suscetível a ferrugem."}, "Arara": {"kc": 1.2, "info": "Resistente a ferrugem."}},
        "fases": {
            "Dormência": {"desc": "Repouso.", "fisiologia": "Indução floral.", "manejo": "Poda.", "quimica": "Cobre."},
            "Florada": {"desc": "Antese.", "fisiologia": "Demanda Boro.", "manejo": "Proteger abelhas.", "quimica": "Ca + B + Zn."},
            "Chumbinho": {"desc": "Expansão.", "fisiologia": "Divisão celular.", "manejo": "Cercospora.", "quimica": "Priori Xtra."},
            "Granação": {"desc": "Enchimento.", "fisiologia": "Pico K/N.", "manejo": "Broca.", "quimica": "Ciantraniliprole."}
        }
    },
    "Tomate": {
        "t_base": 10,
        "vars": {"Italiano": {"kc": 1.2, "info": "Fundo Preto."}, "Grape": {"kc": 1.1, "info": "Rachadura."}},
        "fases": {
            "Vegetativo": {"desc": "Hastes.", "fisiologia": "Estrutura.", "manejo": "Desbrota.", "quimica": "Mancozeb."},
            "Florada": {"desc": "Cachos.", "fisiologia": "Polinização.", "manejo": "Cálcio Foliar.", "quimica": "Cálcio + Boro."},
            "Frutificação": {"desc": "Frutos.", "fisiologia": "Dreno K.", "manejo": "Traça (Tuta).", "quimica": "Clorfenapir."}
        }
    },
    "Mirtilo": {
        "t_base": 7,
        "vars": {"Emerald": {"kc": 0.95, "info": "pH 4.5."}, "Biloxi": {"kc": 0.90, "info": "Poda central."}},
        "fases": {
            "Brotação": {"desc": "Folhas.", "fisiologia": "Reservas.", "manejo": "Cochonilha.", "quimica": "Óleo Mineral."},
            "Florada": {"desc": "Flores.", "fisiologia": "Polinização.", "manejo": "Abelhas.", "quimica": "Fludioxonil."},
            "Fruto Verde": {"desc": "Crescimento.", "fisiologia": "Sem Nitrato.", "manejo": "Antracnose.", "quimica": "Azoxistrobina."}
        }
    },
    "Morango": {
        "t_base": 7,
        "vars": {"San Andreas": {"kc": 0.85, "info": "Ácaros."}, "Albion": {"kc": 0.85, "info": "Oídio."}},
        "fases": {
            "Vegetativo": {"desc": "Coroa.", "fisiologia": "Folhas.", "manejo": "Limpeza.", "quimica": "Enxofre."},
            "Florada": {"desc": "Flores.", "fisiologia": "Polinização.", "manejo": "Botrytis.", "quimica": "Ciprodinil."},
            "Frutificação": {"desc": "Colheita.", "fisiologia": "K/Ca.", "manejo": "Ácaro Rajado.", "quimica": "Etoxazol."}
        }
    },
    "Amora Preta": {
        "t_base": 7, "vars": {"Tupy": {"kc": 1.0, "info": "Frio."}, "Xingu": {"kc": 1.05, "info": "Sem espinho."}},
        "fases": {"Brotação": {"desc": "Hastes.", "fisiologia": "Vigor.", "manejo": "Ferrugem.", "quimica": "Tebuconazol."}, "Frutificação": {"desc": "Bagas.", "fisiologia": "Açúcar.", "manejo": "Drosófila.", "quimica": "Espinosade."}}
    },
    "Framboesa": {
        "t_base": 7, "vars": {"Heritage": {"kc": 1.1, "info": "Remontante."}, "Golden": {"kc": 1.05, "info": "Amarela."}},
        "fases": {"Brotação": {"desc": "Hastes.", "fisiologia": "Vigor.", "manejo": "Ácaro.", "quimica": "Abamectina."}, "Florada": {"desc": "Flores.", "fisiologia": "Chuva.", "manejo": "Podridão.", "quimica": "Iprodiona."}}
    }
}

# --- 3. FUNÇÕES (Cálculo, Geo, IA) ---
def get_credentials():
    return st.query_params.get("w_key", None), st.query_params.get("g_key", None)

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
            dados.append({'Data': datetime.fromtimestamp(item['dt']).strftime('%d/%m'), 'Temp': t, 'GDA': max(0, t-t_base), 'Chuva': round(chuva, 1), 'VPD': vpd, 'Delta T': dt, 'Umid': item['main']['humidity'], 'ETc': round(et0 * kc, 2)})
        return pd.DataFrame(dados)
    except: return pd.DataFrame()

# --- 4. CONFIGURAÇÃO & ESTADO ---
url_w, url_g = get_credentials()

# Inicialização de Estado do Mapa
if 'pontos_mapa' not in st.session_state: st.session_state['pontos_mapa'] = []
if 'click_lat' not in st.session_state: st.session_state['click_lat'] = None
if 'click_lon' not in st.session_state: st.session_state['click_lon'] = None
if 'centro_mapa' not in st.session_state: st.session_state['centro_mapa'] = [-13.414, -41.285] # Padrão Ibicoara

# SIDEBAR
with st.sidebar:
    st.header("⚙️ Configurações")
    with st.expander("🔑 Login / APIs", expanded=not url_w):
        val_w = st.text_input("OpenWeather Key", value=url_w if url_w else "", type="password")
        val_g = st.text_input("Gemini AI Key", value=url_g if url_g else "", type="password")
        if st.button("🔗 Salvar Acesso"): st.query_params["w_key"] = val_w; st.query_params["g_key"] = val_g; st.rerun()

    st.divider()
    nome_fazenda = st.text_input("Propriedade:", value="Minha Fazenda")
    cultura_sel = st.selectbox("Cultura:", list(BANCO_MASTER.keys()))
    var_sel = st.selectbox("Cultivar:", list(BANCO_MASTER[cultura_sel]['vars'].keys()))
    fase_sel = st.selectbox("Fase Atual:", list(BANCO_MASTER[cultura_sel]['fases'].keys()))
    if 'd_plantio' not in st.session_state: st.session_state['d_plantio'] = date(2025, 11, 25)
    d_plantio = st.date_input("Início do Ciclo:", st.session_state['d_plantio'])
    info_v = BANCO_MASTER[cultura_sel]['vars'][var_sel]
    st.info(f"📆 **Dias de Campo:** {(date.today()-d_plantio).days}")

# --- 5. DASHBOARD PRINCIPAL ---
st.title(f"🚜 Agro-Intel: {nome_fazenda}")

if val_w:
    # Usa a coordenada do último clique ou o centro padrão para previsão do tempo
    lat_previsao = st.session_state['click_lat'] if st.session_state['click_lat'] else st.session_state['centro_mapa'][0]
    lon_previsao = st.session_state['click_lon'] if st.session_state['click_lon'] else st.session_state['centro_mapa'][1]

    df = get_forecast(val_w, lat_previsao, lon_previsao, info_v['kc'], BANCO_MASTER[cultura_sel]['t_base'])
    
    if not df.empty:
        hoje = df.iloc[0]
        
        # Header
        st.markdown(f"""
        <div class="header-box">
            <h2>Gestão Técnica: {cultura_sel} - {var_sel}</h2>
            <p style="font-size:1.1em">Fase: <b>{fase_sel}</b> | 🧬 Genética: {info_v['info']}</p>
        </div>
        """, unsafe_allow_html=True)
        
        # KPIs
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("🌡️ Temperatura", f"{hoje['Temp']:.1f}°C", f"Umid: {hoje['Umid']}%")
        c2.metric("💧 VPD (Pressão)", f"{hoje['VPD']} kPa", "Ideal" if 0.4 <= hoje['VPD'] <= 1.3 else "Alerta")
        c3.metric("💦 Consumo (ETc)", f"{hoje['ETc']} mm", f"Kc: {info_v['kc']}")
        c4.metric("🛡️ Delta T", f"{hoje['Delta T']}°C", "Ok" if 2 <= hoje['Delta T'] <= 8 else "Ruim")

        # NAVEGAÇÃO
        tabs = st.tabs(["🗺️ Mapa Interativo", "🎓 Consultoria Técnica", "📊 Clima & Água", "👁️ IA Vision", "💰 Custos"])

        # --- ABA 1: MAPA INTERATIVO (CLICK & GPS) ---
        with tabs[0]:
            col_map, col_ctrl = st.columns([3, 1])
            
            with col_ctrl:
                st.markdown("### 📍 Gerenciar Pontos")
                st.info("💡 **Como usar:** Clique no mapa onde deseja marcar um pivô ou área. Ou use o botão de GPS (canto superior esquerdo do mapa) para achar sua localização.")
                
                # Se o usuário clicou no mapa, mostra opção de salvar
                if st.session_state['click_lat']:
                    st.write(f"**Ponto Selecionado:**")
                    st.caption(f"Lat: {st.session_state['click_lat']:.4f}, Lon: {st.session_state['click_lon']:.4f}")
                    nome_novo_ponto = st.text_input("Nome do Local (Ex: Pivô 12):")
                    if st.button("💾 Salvar Marcador"):
                        st.session_state['pontos_mapa'].append({
                            "nome": nome_novo_ponto, 
                            "lat": st.session_state['click_lat'], 
                            "lon": st.session_state['click_lon']
                        })
                        st.success("Salvo com sucesso!")
                        st.session_state['click_lat'] = None # Limpa seleção para não duplicar
                        st.rerun()
                
                # Lista de Pontos Salvos
                if st.session_state['pontos_mapa']:
                    st.divider()
                    st.write("**Locais Salvos:**")
                    for p in st.session_state['pontos_mapa']:
                        st.markdown(f"- 📍 {p['nome']}")
                    
                    if st.button("🗑️ Limpar Mapa"):
                        st.session_state['pontos_mapa'] = []
                        st.rerun()

            with col_map:
                # Configuração do Mapa
                m = folium.Map(location=st.session_state['centro_mapa'], zoom_start=14)
                
                # 1. Camada de Satélite (Esri World Imagery)
                folium.TileLayer(
                    tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
                    attr='Esri', name='Satélite', overlay=False
                ).add_to(m)

                # 2. Botão de GPS (Locate Control)
                LocateControl(
                    auto_start=False,
                    strings={"title": "Mostrar minha localização atual"},
                    flyTo=True
                ).add_to(m)
                
                # 3. Tela Cheia
                Fullscreen().add_to(m)

                # 4. Marcadores Salvos
                for p in st.session_state['pontos_mapa']:
                    folium.Marker(
                        [p['lat'], p['lon']], 
                        popup=p['nome'], 
                        tooltip=p['nome'],
                        icon=folium.Icon(color='green', icon='leaf')
                    ).add_to(m)
                
                # 5. Renderização com Captura de Clique
                mapa_output = st_folium(m, width="100%", height=500, returned_objects=["last_clicked"])

                # Lógica de Captura de Clique
                if mapa_output["last_clicked"]:
                    lat_click = mapa_output["last_clicked"]["lat"]
                    lon_click = mapa_output["last_clicked"]["lng"]
                    
                    # Só atualiza se for um clique novo (evita loop infinito)
                    if lat_click != st.session_state['click_lat']:
                        st.session_state['click_lat'] = lat_click
                        st.session_state['click_lon'] = lon_click
                        st.rerun()

        # --- ABA 2: CONSULTORIA ---
        with tabs[1]:
            dados = BANCO_MASTER[cultura_sel]['fases'][fase_sel]
            risco = "Baixo"; msg = "✅ <b>Clima Seco:</b> Use Protetores (Mancozeb/Cobre) para baixo custo."; estilo = "alert-low"
            if hoje['Umid'] > 85 or hoje['Chuva'] > 2: risco="ALTO"; msg="🚨 <b>UMIDADE ALTA:</b> Risco severo. Use <b>SISTÊMICOS</b> agora."; estilo="alert-high"
            
            c_esq, c_dir = st.columns(2)
            with c_esq:
                st.markdown(f"""<div class="tech-card"><div class="tech-header">🧬 Fisiologia da Fase</div><p><b>Resumo:</b> {dados['desc']}</p><p><b>Detalhe Técnico:</b> {dados['fisiologia']}</p></div>""", unsafe_allow_html=True)
                st.markdown(f"""<div class="{estilo}"><strong>☁️ Matriz de Decisão (Hoje)</strong><br>{msg}</div>""", unsafe_allow_html=True)
            with c_dir:
                st.markdown(f"""<div class="tech-card"><div class="tech-header">🛠️ Plano de Ação</div><p><b>Cultural:</b> {dados['manejo']}</p><hr><p><b>🧪 Químico:</b> {dados['quimica']}</p></div>""", unsafe_allow_html=True)

        # --- ABA 3: CLIMA ---
        with tabs[2]:
            fig = go.Figure()
            fig.add_trace(go.Bar(x=df['Data'], y=df['Chuva'], name='Chuva', marker_color='#3b82f6'))
            fig.add_trace(go.Scatter(x=df['Data'], y=df['ETc'], name='ETc', line=dict(color='#ef4444', width=2)))
            st.plotly_chart(fig, use_container_width=True)
            st.info(f"Balanço Hídrico (7 dias): {df['Chuva'].sum() - df['ETc'].sum():.1f} mm")

        # --- ABA 4: IA ---
        with tabs[3]:
            img = st.camera_input("Foto da Folha")
            if img and val_g:
                genai.configure(api_key=val_g)
                with st.spinner("Analisando..."):
                    res = genai.GenerativeModel('gemini-1.5-flash').generate_content([f"Agrônomo. Analise {cultura_sel}. Fase {fase_sel}. Umidade {hoje['Umid']}%. Diagnóstico e Solução.", Image.open(img)])
                    st.success(res.text)

        # --- ABA 5: CUSTOS ---
        with tabs[4]:
            if 'custos' not in st.session_state: st.session_state['custos'] = []
            c1, c2 = st.columns(2)
            i = c1.text_input("Item"); v = c2.number_input("R$")
            if c2.button("Lançar"): st.session_state['custos'].append({"Item": i, "Valor": v}); st.success("Salvo")
            if st.session_state['custos']: st.dataframe(pd.DataFrame(st.session_state['custos'])); st.metric("Total", f"R$ {pd.DataFrame(st.session_state['custos'])['Valor'].sum()}")

else:
    st.warning("⚠️ Configure suas chaves no menu lateral para iniciar.")
