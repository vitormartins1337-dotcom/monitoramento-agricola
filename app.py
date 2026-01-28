import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
import math
from datetime import datetime, date

# --- 1. CONFIGURAÇÃO VISUAL (DESIGN SISTÊMICO) ---
st.set_page_config(
    page_title="Agro-Intel Precision",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    /* Cards de KPI */
    div[data-testid="metric-container"] {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    /* Destaque da Cultura */
    .genetica-box {
        background: linear-gradient(to right, #1e3a8a, #3b82f6);
        color: white;
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 20px;
    }
    .genetica-box h3 { color: white; margin: 0; }
    .genetica-box p { opacity: 0.9; margin: 5px 0 0 0; }
</style>
""", unsafe_allow_html=True)

# --- 2. BANCO DE DADOS GENÉTICO (VARIEDADES REAIS DA CHAPADA) ---
BANCO_GENETICA = {
    "Batata (Solanum tuberosum)": {
        "variedades": {
            "Ágata (Mesa)": {
                "ciclo": 90, "t_base": 7, "kc_max": 1.15,
                "alerta": "Alta suscetibilidade à Requeima. Monitorar umidade > 90%.",
                "nutri": "Exigente em N no início. Tubérculo de pele sensível (cuidado na colheita)."
            },
            "Atlantic (Chips/Indústria)": {
                "ciclo": 100, "t_base": 7, "kc_max": 1.10,
                "alerta": "Sensível a Coração Oco. Manter Boro e Cálcio em dia.",
                "nutri": "Exige alto Potássio (K) para matéria seca (Chips crocante)."
            },
            "Asterix (Casca Rosa)": {
                "ciclo": 110, "t_base": 7, "kc_max": 1.15,
                "alerta": "Resistência moderada, mas exige água constante para calibre.",
                "nutri": "Equilíbrio N:K de 1:1.5."
            },
            "Batata da Serra (Nativa Chapada)": {
                "ciclo": 150, "t_base": 10, "kc_max": 0.95,
                "alerta": "Rústica. Baixa exigência hídrica. Evitar excesso de N.",
                "nutri": "Adubação orgânica recomendada. Baixo input químico."
            }
        },
        "fases": ["Emergência", "Vegetativo", "Tuberização (Crítico)", "Maturação"]
    },
    "Morango (Fragaria x ananassa)": {
        "variedades": {
            "San Andreas (Dia Neutro)": {
                "ciclo": 180, "t_base": 10, "kc_max": 0.85,
                "alerta": "Adaptada ao calor, mas sensível a ácaros. Monitorar Delta T.",
                "nutri": "Exige Ca constante para firmeza do fruto."
            },
            "Albion (Sabor)": {
                "ciclo": 180, "t_base": 10, "kc_max": 0.85,
                "alerta": "Susceptível a Podridão de Colo. Evite encharcamento.",
                "nutri": "Alto consumo de K na frutificação para °Brix."
            }
        },
        "fases": ["Plantio/Enraizamento", "Vegetativo", "Florada/Frutificação", "Colheita"]
    },
    "Café (Coffea arabica)": {
        "variedades": {
            "Catuaí (Vermelho/Amarelo)": {
                "ciclo": 365, "t_base": 10, "kc_max": 1.1,
                "alerta": "Susceptível a Ferrugem. Atenção ao VPD baixo.",
                "nutri": "Zinco e Boro essenciais na pré-florada."
            },
            "Arara (Resistente)": {
                "ciclo": 365, "t_base": 10, "kc_max": 1.2,
                "alerta": "Alta resistência a ferrugem. Foco em Cercospora.",
                "nutri": "Alta demanda nutricional devido à alta carga pendente."
            }
        },
        "fases": ["Dormência", "Vegetativo", "Florada (Set/Out)", "Chumbinho", "Granação"]
    },
    "Tomate (Solanum lycopersicum)": {
        "variedades": {
            "Italiano (Saladete)": {
                "ciclo": 110, "t_base": 10, "kc_max": 1.25,
                "alerta": "Risco alto de Fundo Preto (Deficiência de Ca).",
                "nutri": "Cálcio foliar semanal obrigatório na frutificação."
            },
            "Grape/Cereja (Mesa)": {
                "ciclo": 100, "t_base": 10, "kc_max": 1.2,
                "alerta": "Rachadura de frutos se houver oscilação hídrica.",
                "nutri": "Potássio alto para doçura (°Brix)."
            }
        },
        "fases": ["Transplante", "Vegetativo", "Florada", "Colheita"]
    }
}

# --- DADOS FIXOS ---
FAZENDA = {"nome": "Ibicoara (Sede)", "lat": "-13.414", "lon": "-41.285"}
VIZINHOS = [
    {"nome": "Mucugê", "lat": "-13.005", "lon": "-41.371"},
    {"nome": "Barra da Estiva", "lat": "-13.623", "lon": "-41.326"},
    {"nome": "Cascavel (Distrito)", "lat": "-13.196", "lon": "-41.445"}
]

# --- 3. CÉREBRO CIENTÍFICO ---
def calc_agro(temp, umid):
    es = 0.61078 * math.exp((17.27 * temp) / (temp + 237.3))
    ea = es * (umid / 100)
    vpd = round(es - ea, 2)
    tw = temp * math.atan(0.151977 * (umid + 8.313659)**0.5) + math.atan(temp + umid) - math.atan(umid - 1.676331) + 0.00391838 * (umid)**1.5 * math.atan(0.023101 * umid) - 4.686035
    dt = round(temp - tw, 1)
    return dt, vpd

def get_forecast(api_key, lat, lon, kc_max):
    try:
        url = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={api_key}&units=metric&lang=pt_br"
        r = requests.get(url).json()
        dados = []
        for i in range(0, 40, 8):
            item = r['list'][i]
            dt, vpd = calc_agro(item['main']['temp'], item['main']['humidity'])
            chuva = sum([r['list'][i+j].get('rain', {}).get('3h', 0) for j in range(8) if i+j < len(r['list'])])
            et0 = 0.0023 * (item['main']['temp'] + 17.8) * (item['main']['temp'] ** 0.5) * 0.408
            
            # Ajuste simples de Kc por fase (Protótipo usa Kc Max como base)
            etc_real = et0 * kc_max 

            dados.append({
                'Data': datetime.fromtimestamp(item['dt']).strftime('%d/%m'),
                'Temp': item['main']['temp'],
                'Chuva (mm)': round(chuva, 1),
                'VPD (kPa)': vpd,
                'Delta T': dt,
                'Umid (%)': item['main']['humidity'],
                'ETc (mm)': round(etc_real, 2)
            })
        return pd.DataFrame(dados)
    except: return pd.DataFrame()

# --- 4. INTERFACE DE CONTROLE (SIDEBAR) ---
with st.sidebar:
    st.header("🎛️ Configuração Genética")
    api_key = st.text_input("🔑 Chave API OpenWeather", type="password")
    st.divider()
    
    # SELEÇÃO EM CASCATA
    cultura = st.selectbox("1. Cultura Principal:", list(BANCO_GENETICA.keys()))
    
    # Carrega variedades específicas da cultura escolhida
    lista_vars = list(BANCO_GENETICA[cultura]['variedades'].keys())
    variedade = st.selectbox("2. Variedade / Cultivar:", lista_vars)
    
    # Carrega dados técnicos da variedade
    info_var = BANCO_GENETICA[cultura]['variedades'][variedade]
    
    data_plantio = st.date_input("3. Data de Plantio:", date(2025, 11, 25))
    dias_campo = (date.today() - data_plantio).days
    
    fase_atual = st.selectbox("4. Fase Fenológica:", BANCO_GENETICA[cultura]['fases'], index=1)
    
    st.info(f"""
    🧬 **Perfil Genético:**
    - **Ciclo:** {info_var['ciclo']} dias
    - **T. Base:** {info_var['t_base']}°C
    - **Kc Pico:** {info_var['kc_max']}
    """)

# --- 5. DASHBOARD PRINCIPAL ---
st.title("🛰️ Agro-Intel Precision v4.0")

if api_key:
    # CABEÇALHO DINÂMICO
    st.markdown(f"""
    <div class="genetica-box">
        <h3>🚜 Manejo: {cultura.split('(')[0]} - {variedade}</h3>
        <p><strong>Genética:</strong> {info_var['alerta']} | <strong>Fase:</strong> {fase_atual} ({dias_campo} dias)</p>
    </div>
    """, unsafe_allow_html=True)

    df = get_forecast(api_key, FAZENDA['lat'], FAZENDA['lon'], info_var['kc_max'])
    
    if not df.empty:
        hoje = df.iloc[0]
        
        # --- BLOCO 1: INDICADORES EM TEMPO REAL ---
        c1, c2, c3, c4 = st.columns(4)
        
        # GDA (Graus Dia Acumulados)
        gda_dia = max(0, hoje['Temp'] - info_var['t_base'])
        gda_total = dias_campo * 14.8 # Estimativa média
        
        c1.metric("🌡️ Temperatura", f"{hoje['Temp']} °C", f"Umid: {hoje['Umid (%)']}%")
        c2.metric("💧 VPD (Pressão)", f"{hoje['VPD (kPa)']} kPa", "Risco" if hoje['VPD (kPa)'] > 1.3 else "Ideal")
        c3.metric("💦 ETc (Consumo)", f"{hoje['ETc (mm)']} mm", f"Kc Ref: {info_var['kc_max']}")
        c4.metric("📈 Idade Térmica", f"{gda_total:.0f} GDA", f"Base {info_var['t_base']}°C")

        # --- BLOCO 2: PAINEL DE INTELIGÊNCIA ---
        tab1, tab2, tab3 = st.tabs(["📊 Clima & Irrigação", "🧬 Diagnóstico Genético", "📡 Radar & Mapa"])

        with tab1:
            fig = go.Figure()
            fig.add_trace(go.Bar(x=df['Data'], y=df['Chuva (mm)'], name='Chuva', marker_color='#3b82f6'))
            fig.add_trace(go.Scatter(x=df['Data'], y=df['ETc (mm)'], name='Consumo (ETc)', line=dict(color='#f97316', width=2, dash='dot')))
            fig.update_layout(title="Balanço Hídrico (Oferta x Demanda)", height=350, margin=dict(t=30, b=0, l=0, r=0))
            st.plotly_chart(fig, use_container_width=True)
            
            balanco = df['Chuva (mm)'].sum() - df['ETc (mm)'].sum()
            if balanco > 0: st.success(f"**SUPERÁVIT (+{balanco:.1f} mm):** Economize irrigação. Risco de doenças fúngicas se persistir.")
            else: st.error(f"**DÉFICIT ({balanco:.1f} mm):** Aumente a irrigação para evitar quebra de produtividade.")

        with tab2:
            c_diag1, c_diag2 = st.columns(2)
            
            with c_diag1:
                st.subheader(f"🛡️ Defesa da {variedade.split('(')[0]}")
                st.write(f"**Alerta Varietal:** {info_var['alerta']}")
                st.markdown("---")
                if len(df[df['Umid (%)'] > 88]) > 2:
                    st.error("🚨 **RISCO ALTO:** Umidade favorável a requeima/pinta-preta. Intervalo de aplicação deve ser reduzido.")
                else:
                    st.success("✅ **RISCO BAIXO:** Condições desfavoráveis a fungos.")
            
            with c_diag2:
                st.subheader("💊 Nutrição de Precisão")
                st.info(f"**Diretriz:** {info_var['nutri']}")
                
                vpd_status = "🟢 Ótimo" if 0.4 <= hoje['VPD (kPa)'] <= 1.3 else "🔴 Ruim"
                st.write(f"**Eficiência de Absorção Hoje:** {vpd_status}")
                if vpd_status == "🔴 Ruim":
                    st.caption("Evite fertirrigar agora. A planta não está transpirando (bomba desligada) ou está fechada (estresse).")

        with tab3:
            # Mapa e Radar
            col_gps = st.columns(len(VIZINHOS))
            for i, v in enumerate(VIZINHOS):
                try:
                    r = requests.get(f"https://api.openweathermap.org/data/2.5/weather?lat={v['lat']}&lon={v['lon']}&appid={api_key}&units=metric").json()
                    cor = "#fee2e2" if "rain" in str(r) else "#dcfce7"
                    col_gps[i].markdown(f"<div style='background:{cor};padding:10px;border-radius:5px;text-align:center'><b>{v['nome'].split()[0]}</b><br>{r['main']['temp']:.0f}°C</div>", unsafe_allow_html=True)
                except: pass
            
            map_data = pd.DataFrame([FAZENDA] + VIZINHOS).rename(columns={"lat": "latitude", "lon": "longitude"})
            map_data['latitude'] = map_data['latitude'].astype(float)
            map_data['longitude'] = map_data['longitude'].astype(float)
            st.map(map_data, zoom=9)

else:
    st.info("👈 Insira sua chave API no menu lateral para carregar o sistema.")
