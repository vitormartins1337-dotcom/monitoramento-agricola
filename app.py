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
st.set_page_config(page_title="Agro-Intel Titan Pro", page_icon="🛰️", layout="wide")

# --- ESTILIZAÇÃO CSS CORPORATIVA ---
st.markdown("""
<style>
    .main { background-color: #f8fafc; }
    .stMetric { background: white; padding: 20px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); border-left: 5px solid #065f46; }
    .header-box { background: linear-gradient(135deg, #064e3b 0%, #065f46 100%); color: white; padding: 40px; border-radius: 20px; margin-bottom: 30px; }
    .tech-card { background: white; padding: 25px; border-radius: 15px; border: 1px solid #e2e8f0; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.02); }
    .tech-header { color: #064e3b; font-weight: 800; font-size: 1.4em; border-bottom: 3px solid #f1f5f9; padding-bottom: 12px; margin-bottom: 20px; }
    .alert-high { background-color: #fef2f2; border-left: 6px solid #dc2626; padding: 20px; border-radius: 8px; color: #991b1b; font-weight: 600; }
    .alert-low { background-color: #f0fdf4; border-left: 6px solid #16a34a; padding: 20px; border-radius: 8px; color: #14532d; font-weight: 600; }
    .gda-card { background: #fffbeb; border: 1px solid #fef3c7; padding: 20px; border-radius: 12px; text-align: center; margin-bottom: 20px; }
</style>
""", unsafe_allow_html=True)

# --- 2. BANCO DE DADOS AGRONÔMICO TITAN (TODAS AS CULTURAS) ---
BANCO_MASTER = {
    "Batata (Solanum tuberosum)": {
        "t_base": 7,
        "vars": {
            "Orchestra": {"kc": 1.15, "gda_meta": 1600, "info": "Pele lisa premium. Exigente em Potássio (K)."},
            "Cupido": {"kc": 1.10, "gda_meta": 1400, "info": "Ciclo ultra-curto. Altamente sensível a Requeima."},
            "Camila": {"kc": 1.15, "gda_meta": 1550, "info": "Referência mercado fresco. Monitorar Sarna."},
            "Atlantic": {"kc": 1.15, "gda_meta": 1650, "info": "Foco industrial (Chips). Cuidado com Coração Oco."}
        },
        "fases": {
            "Emergência (0-20d)": {"desc": "Brotamento inicial.", "fisio": "Dreno de reservas da batata-mãe.", "manejo": "Solo aerado e úmido. Monitorar Canela Preta.", "quim": "Azoxistrobina + Tiametoxam.", "bio": "EM-1 + Ácidos Húmicos."},
            "Vegetativo (20-35d)": {"desc": "Expansão da área foliar.", "fisio": "Alta demanda de Nitrogênio (N) para fechar linhas.", "manejo": "Realizar amontoa técnica (15-20cm).", "quim": "Mancozeb + Clorotalonil.", "bio": "Bokashi líquido via fertirrigação."},
            "Tuberização/Gancho (35-55d)": {"desc": "Início da diferenciação dos tubérculos.", "fisio": "Inversão hormonal (queda de Giberelina).", "manejo": "Irrigação de precisão. Controle severo de Requeima.", "quim": "Revus (Mandipropamida) + Metalaxil-M.", "bio": "Aminoácidos."},
            "Enchimento (55-85d)": {"desc": "Acúmulo de matéria seca e expansão radial.", "fisio": "Translocação intensa Folha -> Tubérculo. Dreno de K.", "manejo": "Manter sanidade foliar. Monitorar Mosca Branca e Traça.", "quim": "Benévia + Espirotesifeno.", "bio": "Potássio orgânico + Algas."},
            "Maturação (85d+)": {"desc": "Senescência e cura da pele.", "fisio": "Suberização térmica final.", "manejo": "Suspensão gradual da água. Dessecação química.", "quim": "Diquat.", "bio": "Interromper Nitrogênio."}
        }
    },
    "Mirtilo (Blueberry)": {
        "t_base": 7, "vars": {"Emerald": {"kc": 0.95, "gda_meta": 1800, "info": "pH 4.5. Exigente em enxofre."}, "Biloxi": {"kc": 0.90, "gda_meta": 1900, "info": "Ideal para clima tropical."}},
        "fases": {"Florada": {"desc": "Polinização.", "fisio": "Pegamento.", "quim": "Switch (Botrytis).", "bio": "Boro + Zinco."}, "Crescimento": {"desc": "Expansão do fruto.", "fisio": "Divisão celular.", "quim": "Sulfato de Potássio.", "bio": "Ácidos fúlvicos."}}
    },
    "Framboesa/Amora": {
        "t_base": 7, "vars": {"Heritage": {"kc": 1.1, "gda_meta": 1300, "info": "Remontante."}},
        "fases": {"Frutificação": {"desc": "Maturação das bagas.", "fisio": "Acúmulo de açúcares.", "quim": "Espinosade (Drosófila).", "bio": "Bokashi (Estrutura)."}}
    }
}

# --- 3. MOTORES TÉCNICOS (CLIMA, RADAR E GDA) ---
def get_forecast(lat, lon, api_key, kc, t_base):
    try:
        url = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={api_key}&units=metric&lang=pt_br"
        r = requests.get(url).json()
        dados = []
        if 'list' in r:
            for i in range(0, 40, 8):
                item = r['list'][i]
                t = item['main']['temp']
                umid = item['main']['humidity']
                es = 0.61078 * math.exp((17.27 * t) / (t + 237.3))
                ea = es * (umid / 100); vpd = round(es - ea, 2)
                et0 = 0.0023 * (t + 17.8) * (t ** 0.5) * 0.408
                chuva = round(item.get('rain', {}).get('3h', 0), 1)
                dados.append({
                    'Data': datetime.fromtimestamp(item['dt']).strftime('%d/%m'),
                    'Temp': t, 'Umid': umid, 'VPD': vpd, 'Chuva': chuva,
                    'GDA': max(0, t - t_base), 'ETc': round(et0 * kc, 2)
                })
        return pd.DataFrame(dados)
    except: return pd.DataFrame()

def get_radar(lat, lon, api_key):
    pontos = {"Norte": (lat+0.1, lon), "Sul": (lat-0.1, lon), "Leste": (lat, lon+0.1), "Oeste": (lat, lon-0.1)}
    resultados = []
    for direcao, coords in pontos.items():
        try:
            url = f"https://api.openweathermap.org/data/2.5/weather?lat={coords[0]}&lon={coords[1]}&appid={api_key}&units=metric"
            r = requests.get(url).json()
            resultados.append({"Direção": direcao, "Temp": r['main']['temp'], "Chuva": "Sim" if "rain" in r else "Não"})
        except: pass
    return pd.DataFrame(resultados)

# --- 4. INTERFACE E SIDEBAR ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2822/2822444.png", width=100)
    st.title("Agro-Intel Titan Pro")
    
    # Chaves automáticas do cofre Secrets
    api_w = st.secrets.get("OPENWEATHER_KEY", "")
    api_g = st.secrets.get("GEMINI_KEY", "")
    
    st.divider()
    cultura_sel = st.selectbox("Selecione a Cultura:", list(BANCO_MASTER.keys()))
    var_sel = st.selectbox("Variedade/Cultivar:", list(BANCO_MASTER[cultura_sel]['vars'].keys()))
    fase_sel = st.selectbox("Estágio Fenológico Atual:", list(BANCO_MASTER[cultura_sel]['fases'].keys()))
    d_plantio = st.date_input("Data de Plantio/Início:", date(2025, 11, 25))
    
    st.divider()
    st.info("📍 Localização fixa: Fazenda Progresso (Ibicoara-BA)")
    peso_dobló = st.slider("Carga Doblò (kg):", 100, 800, 350)

# --- 5. DASHBOARD PRINCIPAL ---
st.markdown(f"""
<div class="header-box">
    <h1>🛰️ Inteligência Agronômica: {cultura_sel}</h1>
    <p>Monitoramento Enterprise - Variedade: <b>{var_sel}</b></p>
</div>
""", unsafe_allow_html=True)

if api_w:
    # Dados da Cultura Selecionada
    crop_db = BANCO_MASTER[cultura_sel]
    v_info = crop_db['vars'][var_sel]
    df_previsao = get_forecast("-13.200", "-41.400", api_w, v_info['kc'], crop_db['t_base'])
    
    if not df_previsao.empty:
        hoje = df_previsao.iloc[0]
        dias_ciclo = (date.today() - d_plantio).days
        gda_atual = dias_ciclo * df_previsao['GDA'].mean()
        meta_gda = v_info['gda_meta']
        
        # MÉTRICAS DE TOPO
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("🌡️ Temp. Atual", f"{hoje['Temp']:.1f}°C")
        m2.metric("💧 Umidade Rel.", f"{hoje['Umid']}%")
        m3.metric("💦 ETc (Consumo)", f"{hoje['ETc']} mm")
        m4.metric("📅 Dias de Campo", f"{dias_ciclo} dias")

        tabs = st.tabs(["🎓 Consultoria Profissional", "📊 Previsão & Balanço", "📡 Radar Regional", "👁️ IA Visual Vision", "🗺️ Mapa Satélite", "🚚 Logística"])

        with tabs[0]: # CONSULTORIA
            fase_data = crop_db['fases'][fase_sel]
            
            

            st.markdown(f"""
            <div class="gda-card">
                <h3>🔥 Acúmulo Térmico: {gda_atual:.0f} / {meta_gda} GDA</h3>
                <p>Progresso Biológico: <b>{min(100.0, (gda_atual/meta_gda)*100):.1f}%</b></p>
            </div>
            """, unsafe_allow_html=True)
            st.progress(min(1.0, gda_atual/meta_gda))
            
            # Alerta Sanitário Baseado em Umidade (Requeima/Botrytis)
            if hoje['Umid'] > 85:
                st.markdown(f'<div class="alert-high">🚨 ALERTA SANITÁRIO: Umidade elevada ({hoje["Umid"]}%). Risco crítico de patógenos fúngicos. Recomendado: Sistêmicos (Revus/Metalaxil).</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="alert-low">✅ CONDIÇÃO SANITÁRIA: Risco baixo. Manter cronograma de preventivos foliares.</div>', unsafe_allow_html=True)
            
            

            c_esq, c_dir = st.columns(2)
            with c_esq:
                st.markdown(f"""<div class="tech-card"><div class="tech-header">🧬 Fisiologia e Manejo</div>
                <p><b>Fase:</b> {fase_sel}</p>
                <p><b>Processo:</b> {fase_data['fisio']}</p>
                <p><b>Ação Cultural:</b> {fase_data['manejo']}</p>
                <p><b>Manejo Biológico:</b> {fase_data['bio']}</p></div>""", unsafe_allow_html=True)
            with c_dir:
                st.markdown(f"""<div class="tech-card"><div class="tech-header">🧪 Prescrição Química Profissional</div>
                <p><b>Moléculas e Alvos Sugeridos:</b><br>{fase_data['quim']}</p>
                <p><small>*Consulte sempre o receituário agronômico local.</small></p></div>""", unsafe_allow_html=True)

        with tabs[1]: # GRÁFICOS
            st.markdown("### 📊 Balanço Hídrico e Precipitação (5 Dias)")
            fig = go.Figure()
            fig.add_trace(go.Bar(x=df_previsao['Data'], y=df_previsao['Chuva'], name='Chuva (mm)', marker_color='#3b82f6'))
            fig.add_trace(go.Scatter(x=df_previsao['Data'], y=df_previsao['ETc'], name='Consumo ETc (mm)', line=dict(color='#dc2626', width=3)))
            st.plotly_chart(fig, use_container_width=True)

        with tabs[2]: # RADAR
            st.markdown("### 📡 Radar de Vizinhança (Raio 15km)")
            df_radar = get_radar("-13.200", "-41.400", api_w)
            if not df_radar.empty:
                cols = st.columns(4)
                for i, r in df_radar.iterrows():
                    cor = "#ffebee" if r['Chuva'] == "Sim" else "#f0fdf4"
                    with cols[i]: st.markdown(f"""<div class="tech-card" style="background-color:{cor}; text-align:center"><b>{r['Direção']}</b><br>{r['Temp']:.1f}°C<br>Chuva: {r['Chuva']}</div>""", unsafe_allow_html=True)

        with tabs[3]: # IA VISION
            st.markdown("### 👁️ IA Visual Vision - Diagnóstico Gemini")
            if api_g:
                foto = st.camera_input("Tire uma foto da praga ou sintoma na folha")
                if foto:
                    genai.configure(api_key=api_g)
                    with st.spinner("Analisando quadro fitossanitário..."):
                        modelo = genai.GenerativeModel('gemini-1.5-flash')
                        res = modelo.generate_content([f"Engenheiro Agrônomo. Analise imagem de {cultura_sel} {var_sel} na fase {fase_sel}. Identifique sintomas e recomende manejo técnico.", Image.open(foto)])
                        st.success(res.text)

        with tabs[4]: # MAPA
            st.markdown("### 🗺️ Georreferenciamento e Satélite (Esri)")
            m = folium.Map(location=[-13.200, -41.400], zoom_start=14)
            folium.TileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', attr='Esri', name='Satélite').add_to(m)
            LocateControl().add_to(m); Fullscreen().add_to(m)
            st_folium(m, width="100%", height=500)

        with tabs[5]: # LOGÍSTICA
            st.markdown("### 🚚 Logística de Escoamento (Salvador)")
            custo_frete = (450 / 10) * 6.20 # Cálculo estimado Ibicoara -> SSA
            col_l1, col_l2 = st.columns(2)
            col_l1.metric("Custo Combustível (Est.)", f"R$ {custo_frete:.2f}")
            col_l2.metric("Custo por kg", f"R$ {custo_frete/peso_dobló:.2f}")
            st.info(f"Ocupação da Suspensão: {(peso_dobló/800)*100:.1f}%")

else:
    st.error("⚠️ Erro: As chaves de API não foram detectadas no servidor. Verifique o painel Secrets.")
