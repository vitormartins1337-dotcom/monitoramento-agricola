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
st.set_page_config(page_title="Agro-Intel Titan", page_icon="🛰️", layout="wide")

# --- ESTILIZAÇÃO CSS ---
st.markdown("""
<style>
    .main { background-color: #f0f2f5; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); border-left: 5px solid #1b5e20; }
    .header-box { background: linear-gradient(135deg, #0d47a1 0%, #1a237e 100%); color: white; padding: 30px; border-radius: 15px; margin-bottom: 25px; }
    .tech-card { background-color: #ffffff; padding: 25px; border-radius: 12px; border: 1px solid #e0e0e0; margin-bottom: 20px; }
    .tech-header { color: #1a237e; font-weight: 800; font-size: 1.3em; border-bottom: 3px solid #f5f5f5; padding-bottom: 12px; margin-bottom: 18px; }
    .alert-high { background-color: #ffebee; border-left: 6px solid #b71c1c; padding: 20px; border-radius: 8px; color: #b71c1c; font-weight: 600; }
    .alert-low { background-color: #e8f5e9; border-left: 6px solid #1b5e20; padding: 20px; border-radius: 8px; color: #1b5e20; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

# --- 2. BANCO DE DADOS AGRONÔMICO (ESTRUTURA COMPLETA) ---
BANCO_MASTER = {
    "Batata (Solanum tuberosum)": {
        "t_base": 7,
        "vars": {
            "Orchestra": {"kc": 1.15, "gda_meta": 1600, "info": "Pele lisa premium."},
            "Cupido": {"kc": 1.10, "gda_meta": 1400, "info": "Ciclo curto. Alerta Requeima."},
            "Camila": {"kc": 1.15, "gda_meta": 1550, "info": "Mercado fresco."},
            "Atlantic": {"kc": 1.15, "gda_meta": 1650, "info": "Indústria (Chips)."}
        },
        "fases": {
            "Emergência (0-20d)": {"desc": "Brotamento.", "fisio": "Dreno de reservas.", "quim": "Azoxistrobina.", "bio": "EM-1."},
            "Vegetativo (20-35d)": {"desc": "Expansão foliar.", "fisio": "IAF explosivo.", "quim": "Mancozeb.", "bio": "Bokashi."},
            "Tuberização (35-55d)": {"desc": "Ganchos.", "fisio": "Inversão hormonal.", "quim": "Revus.", "bio": "Aminoácidos."},
            "Enchimento (55-85d)": {"desc": "Engorda.", "fisio": "Translocação intensa.", "quim": "Benévia.", "bio": "Extrato de Algas."},
            "Maturação (85d+)": {"desc": "Cura da pele.", "fisio": "Suberização.", "quim": "Diquat.", "bio": "Suspensão de N."}
        }
    },
    "Mirtilo": {
        "t_base": 7, 
        "vars": {"Emerald": {"kc": 0.95, "gda_meta": 1800, "info": "Vigorosa."}, "Biloxi": {"kc": 0.90, "gda_meta": 1900, "info": "Baixo frio."}},
        "fases": {"Florada": {"desc": "Polinização.", "fisio": "Pegamento.", "quim": "Switch.", "bio": "Boro."}, "Crescimento": {"desc": "Expansão.", "fisio": "Divisão celular.", "quim": "Potássio.", "bio": "Ácidos Húmicos."}}
    },
    "Framboesa": {
        "t_base": 7, 
        "vars": {"Heritage": {"kc": 1.1, "gda_meta": 1300, "info": "Remontante."}},
        "fases": {"Frutificação": {"desc": "Bagas.", "fisio": "Açúcares.", "quim": "Espinosade.", "bio": "Potássio."}}
    }
}

# --- 3. MOTOR DE PREVISÃO ---
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
                dados.append({
                    'Data': datetime.fromtimestamp(item['dt']).strftime('%d/%m'),
                    'Temp': t, 'Umid': umid, 'VPD': vpd, 'Chuva': round(item.get('rain', {}).get('3h', 0), 1),
                    'GDA': max(0, t - t_base), 'ETc': round(et0 * kc, 2)
                })
            return pd.DataFrame(dados)
    except: return pd.DataFrame()

# --- 4. SIDEBAR ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2822/2822444.png", width=100)
    st.title("Agro-Intel Titan")
    api_w = st.secrets.get("OPENWEATHER_KEY", "")
    api_g = st.secrets.get("GEMINI_KEY", "")
    
    st.divider()
    cultura = st.selectbox("Cultura Alvo:", list(BANCO_MASTER.keys()))
    var = st.selectbox("Cultivar:", list(BANCO_MASTER[cultura]['vars'].keys()))
    fase = st.selectbox("Fase Fenológica:", list(BANCO_MASTER[cultura]['fases'].keys()))
    d_plantio = st.date_input("Início do Ciclo:", date(2025, 11, 25))
    
    st.divider()
    peso_carga = st.slider("Carga Doblò (kg):", 100, 800, 300)

# --- 5. DASHBOARD PRINCIPAL ---
st.markdown(f"""<div class="header-box"><h1>🛰️ Fazenda Progresso - Ibicoara/BA</h1><p>Monitoramento Enterprise: <b>{cultura} - {var}</b></p></div>""", unsafe_allow_html=True)

if api_w:
    # Extração segura de dados do banco
    base_dados = BANCO_MASTER[cultura]
    v_info = base_dados['vars'][var]
    t_base_crop = base_dados['t_base']
    kc_crop = v_info['kc']
    meta_gda_crop = v_info['gda_meta']

    df_previsao = get_forecast("-13.200", "-41.400", api_w, kc_crop, t_base_crop)
    
    if not df_previsao.empty:
        hoje = df_previsao.iloc[0]
        dias_no_campo = (date.today() - d_plantio).days
        # RESOLVENDO NAMEERROR: Unificando cálculo de GDA
        gda_acumulado_hoje = dias_no_campo * df_previsao['GDA'].mean()
        
        # MÉTRICAS TOPO
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("🌡️ Temperatura", f"{hoje['Temp']:.1f}°C")
        m2.metric("💧 VPD (kPa)", f"{hoje['VPD']}", "Ideal" if 0.5 < hoje['VPD'] < 1.3 else "Atenção")
        m3.metric("💦 ETc Diária", f"{hoje['ETc']} mm")
        m4.metric("📅 GDA Acumulado", f"{gda_acumulado_hoje:.0f}", f"Meta: {meta_gda_crop}")

        abas = st.tabs(["🎓 Consultoria Técnica", "📊 Gráficos", "👁️ IA Vision", "🗺️ Mapa", "🚚 Logística"])

        with abas[0]: # CONSULTORIA
            fase_data = base_dados['fases'][fase]
            
            

            st.markdown(f"### 🔥 Maturação Térmica: {min(100.0, (gda_acumulado_hoje/meta_gda_crop)*100):.1f}%")
            st.progress(min(1.0, gda_acumulado_hoje/meta_gda_crop))
            
            if hoje['Umid'] > 85:
                st.markdown(f'<div class="alert-high">🚨 ALERTA SANITÁRIO: Umidade elevada ({hoje["Umid"]}%). Risco crítico de Requeima. Aplicar Sistêmicos.</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="alert-low">✅ CONDIÇÃO SANITÁRIA: Risco baixo. Manter fungicidas protetores.</div>', unsafe_allow_html=True)
            
            

            c_a, c_b = st.columns(2)
            with c_a:
                st.markdown(f"""<div class="tech-card"><div class="tech-header">🧬 Fisiologia & Manejo</div>
                <p><b>Estágio:</b> {fase}</p>
                <p><b>Processo:</b> {fase_data['fisio']}</p>
                <p><b>Bio-Regenerativo:</b> {fase_data['bio']}</p></div>""", unsafe_allow_html=True)
            with c_b:
                st.markdown(f"""<div class="tech-card"><div class="tech-header">🧪 Prescrição Técnica</div>
                <p><b>Moléculas Sugeridas:</b><br>{fase_data['quim']}</p></div>""", unsafe_allow_html=True)

        with abas[1]: # GRÁFICOS
            f_clima = go.Figure()
            f_clima.add_trace(go.Bar(x=df_previsao['Data'], y=df_previsao['Chuva'], name='Chuva (mm)', marker_color='#0288d1'))
            f_clima.add_trace(go.Scatter(x=df_previsao['Data'], y=df_previsao['ETc'], name='ETc (mm)', line=dict(color='#d32f2f', width=3)))
            st.plotly_chart(f_clima, use_container_width=True)

        with abas[4]: # LOGÍSTICA
            st.markdown("### 🚚 Planejamento Doblò Cargo")
            custo_viagem = (450 / 10) * 6.20 # Ibicoara -> Salvador
            l1, l2 = st.columns(2)
            l1.metric("Custo Combustível (Est.)", f"R$ {custo_viagem:.2f}")
            l2.metric("Custo/kg", f"R$ {custo_viagem/peso_carga:.2f}")
            st.info(f"Ocupação: {(peso_carga/800)*100:.1f}% da suspensão.")

else:
    st.error("⚠️ Erro: OPENWEATHER_KEY não encontrada nos Secrets.")
