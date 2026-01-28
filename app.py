import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
import math
from datetime import datetime, date

# --- 1. CONFIGURAÇÃO VISUAL ---
st.set_page_config(
    page_title="Agro-Intel Chapada",
    page_icon="🍓",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    div[data-testid="metric-container"] { background-color: #ffffff; border: 1px solid #e0e0e0; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .genetica-box { background: linear-gradient(to right, #2e7d32, #66bb6a); color: white; padding: 15px; border-radius: 8px; margin-bottom: 20px; }
    .genetica-box h3 { color: white; margin: 0; }
    .stAlert { border-radius: 6px; }
</style>
""", unsafe_allow_html=True)

# --- 2. BANCO DE DADOS GENÉTICO (CHAPADA DIAMANTINA) ---
BANCO_GENETICA = {
    "Batata (Solanum tuberosum)": {
        "variedades": {
            "Orchestra (Pele Lisa)": {
                "ciclo": 110, "t_base": 7, "kc_max": 1.15,
                "alerta": "Alta produtividade exige K elevado. Monitorar Pinta Preta.",
                "nutri": "Relação N:K de 1:1.6. Exige Magnésio extra para fotossíntese."
            },
            "Cupido (Precoce)": {
                "ciclo": 90, "t_base": 7, "kc_max": 1.10,
                "alerta": "Sensível à Requeima e Esverdeamento. Colheita rápida.",
                "nutri": "Nitrogênio moderado para evitar excesso de folha. Foco em Calibre."
            },
            "Camila (Mesa)": {
                "ciclo": 100, "t_base": 7, "kc_max": 1.15,
                "alerta": "Pele sensível. Cuidado com dano mecânico e Sarna.",
                "nutri": "Cálcio via solo e foliar essencial para resistência da pele."
            },
            "Atlantic (Chips)": {
                "ciclo": 105, "t_base": 7, "kc_max": 1.15,
                "alerta": "Monitorar Coração Oco. Exige Boro.",
                "nutri": "Potássio Sulfato preferencial para matéria seca (Chips)."
            }
        },
        "fases": ["Emergência", "Vegetativo", "Tuberização (Início)", "Enchimento", "Maturação"]
    },
    "Mirtilo (Vaccinium spp.)": {
        "variedades": {
            "Emerald (Vigorosa)": {
                "ciclo": 150, "t_base": 10, "kc_max": 0.95,
                "alerta": "Baixa exigência de frio. Risco de Phytophthora em solo encharcado.",
                "nutri": "Nitrogênio Amoniacal (Sulfato de Amônio). pH ideal 4.5-5.2."
            },
            "Biloxi (Ereta)": {
                "ciclo": 160, "t_base": 10, "kc_max": 0.90,
                "alerta": "Alta densidade. Poda de limpeza essencial para entrada de luz.",
                "nutri": "Sensível a excesso de N. Adubação parcelada frequente."
            }
        },
        "fases": ["Poda/Dormência", "Brotação", "Florada", "Frutificação (Verde)", "Colheita"]
    },
    "Amora Preta (Rubus spp.)": {
        "variedades": {
            "Tupy (Tradicional)": {
                "ciclo": 130, "t_base": 10, "kc_max": 1.0,
                "alerta": "Exige tutoramento. Rustica, mas sensível a Antracnose.",
                "nutri": "Nitrogênio na brotação. Potássio no enchimento."
            },
            "BRS Xingu (Sem Espinho)": {
                "ciclo": 140, "t_base": 10, "kc_max": 1.05,
                "alerta": "Maturação mais tardia. Facilidade de colheita.",
                "nutri": "Cálcio para firmeza pós-colheita."
            }
        },
        "fases": ["Poda", "Crescimento de Hastes", "Florada", "Maturação"]
    },
    "Framboesa (Rubus idaeus)": {
        "variedades": {
            "Heritage (Vermelha)": {
                "ciclo": 120, "t_base": 9, "kc_max": 1.1,
                "alerta": "Remontante (produz na ponta). Poda drástica ou seletiva.",
                "nutri": "Ferro e Manganês via foliar se o solo for alcalino."
            },
            "Golden Bliss (Amarela)": {
                "ciclo": 125, "t_base": 9, "kc_max": 1.05,
                "alerta": "Fruto delicado. Colheita diária obrigatória.",
                "nutri": "Potássio alto para Brix."
            }
        },
        "fases": ["Brotação", "Florada", "Frutificação", "Colheita"]
    },
    "Morango (Fragaria x ananassa)": {
        "variedades": {
            "San Andreas": {"ciclo": 180, "t_base": 10, "kc_max": 0.85, "alerta": "Sensível a Ácaros.", "nutri": "Cálcio constante."},
            "Albion": {"ciclo": 180, "t_base": 10, "kc_max": 0.85, "alerta": "Sabor premium. Poda de estolões.", "nutri": "K elevado."}
        },
        "fases": ["Plantio", "Vegetativo", "Florada", "Colheita"]
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
            
            dados.append({
                'Data': datetime.fromtimestamp(item['dt']).strftime('%d/%m'),
                'Temp': item['main']['temp'],
                'Chuva (mm)': round(chuva, 1),
                'VPD (kPa)': vpd,
                'Delta T': dt,
                'Umid (%)': item['main']['humidity'],
                'ETc (mm)': round(et0 * kc_max, 2)
            })
        return pd.DataFrame(dados)
    except: return pd.DataFrame()

# --- 4. SIDEBAR ---
with st.sidebar:
    st.header("🎛️ Configuração da Lavoura")
    api_key = st.text_input("🔑 Chave API OpenWeather", type="password")
    st.divider()
    
    # SELEÇÃO DE CULTURA E VARIEDADE
    cultura = st.selectbox("1. Cultura:", list(BANCO_GENETICA.keys()))
    lista_vars = list(BANCO_GENETICA[cultura]['variedades'].keys())
    variedade = st.selectbox("2. Cultivar:", lista_vars)
    
    info_var = BANCO_GENETICA[cultura]['variedades'][variedade]
    
    data_plantio = st.date_input("3. Data Início/Poda:", date(2025, 11, 25))
    dias_campo = (date.today() - data_plantio).days
    
    fase_atual = st.selectbox("4. Fase Fenológica:", BANCO_GENETICA[cultura]['fases'], index=1)
    
    st.info(f"🧬 **{variedade}**\nCiclo: {info_var['ciclo']} dias | Kc Pico: {info_var['kc_max']}")

# --- 5. DASHBOARD ---
st.title("🛰️ Agro-Intel Chapada v5.0")

if api_key:
    st.markdown(f"""
    <div class="genetica-box">
        <h3>🚜 Manejo: {cultura.split('(')[0]} - {variedade.split('(')[0]}</h3>
        <p><strong>Ponto Crítico:</strong> {info_var['alerta']} | <strong>Idade:</strong> {dias_campo} dias</p>
    </div>
    """, unsafe_allow_html=True)

    df = get_forecast(api_key, FAZENDA['lat'], FAZENDA['lon'], info_var['kc_max'])
    
    if not df.empty:
        hoje = df.iloc[0]
        
        # KPIS
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("🌡️ Temperatura", f"{hoje['Temp']} °C", f"Umid: {hoje['Umid (%)']}%")
        c2.metric("💧 VPD (Pressão)", f"{hoje['VPD (kPa)']} kPa", "Ideal" if 0.4 <= hoje['VPD (kPa)'] <= 1.3 else "Risco")
        c3.metric("💦 ETc (Consumo)", f"{hoje['ETc (mm)']} mm", f"Kc: {info_var['kc_max']}")
        gda_estimado = dias_campo * 12 # Média simples
        c4.metric("📈 GDA Acumulado", f"{gda_estimado} GDA", f"Base {info_var['t_base']}°C")

        # ABAS
        tab1, tab2, tab3 = st.tabs(["📊 Balanço Hídrico", "🧬 Diagnóstico & Nutrição", "📡 Radar GPS"])

        with tab1:
            fig = go.Figure()
            fig.add_trace(go.Bar(x=df['Data'], y=df['Chuva (mm)'], name='Chuva', marker_color='#29b6f6'))
            fig.add_trace(go.Scatter(x=df['Data'], y=df['ETc (mm)'], name='Consumo (ETc)', line=dict(color='#ef5350', width=2, dash='dot')))
            fig.update_layout(title="Oferta (Chuva) vs Demanda (Transpiração)", height=350)
            st.plotly_chart(fig, use_container_width=True)
            
            balanco = df['Chuva (mm)'].sum() - df['ETc (mm)'].sum()
            if balanco > 0: st.info(f"**SUPERÁVIT (+{balanco:.1f} mm):** Solo úmido. Atenção a doenças de raiz.")
            else: st.warning(f"**DÉFICIT ({balanco:.1f} mm):** Necessário irrigar para manter turgidez.")

        with tab2:
            c_diag1, c_diag2 = st.columns(2)
            with c_diag1:
                st.subheader("🛡️ Alerta Fitossanitário")
                if "Batata" in cultura and len(df[df['Umid (%)'] > 85]) > 2:
                    st.error("🚨 **ALERTA DE REQUEIMA:** Alta umidade detectada. Reduza intervalo de fungicida sistêmico.")
                elif "Mirtilo" in cultura and balanco > 10:
                    st.error("🚨 **ALERTA DE RAIZ:** Solo saturado. Risco de Phytophthora. Melhore a drenagem.")
                else:
                    st.success("✅ Condições climáticas sob controle.")
                
                st.write(f"**VPD Hoje:** {hoje['VPD (kPa)']} kPa")

            with c_diag2:
                st.subheader("💊 Nutrição Específica")
                st.info(f"**Diretriz ({variedade}):** {info_var['nutri']}")
                if "Tuberização" in fase_atual or "Frutificação" in fase_atual:
                    st.markdown("**Dica:** Fase de enchimento. Aumente o Potássio (K) para ganho de peso e Brix.")

        with tab3:
            col_gps = st.columns(len(VIZINHOS))
            for i, v in enumerate(VIZINHOS):
                try:
                    r = requests.get(f"https://api.openweathermap.org/data/2.5/weather?lat={v['lat']}&lon={v['lon']}&appid={api_key}&units=metric").json()
                    cor = "#ffcdd2" if "rain" in str(r) else "#c8e6c9"
                    col_gps[i].markdown(f"<div style='background:{cor};padding:10px;border-radius:5px;text-align:center'><b>{v['nome'].split()[0]}</b><br>{r['main']['temp']:.0f}°C</div>", unsafe_allow_html=True)
                except: pass
            
            map_data = pd.DataFrame([FAZENDA] + VIZINHOS).rename(columns={"lat": "latitude", "lon": "longitude"})
            map_data['latitude'] = map_data['latitude'].astype(float)
            map_data['longitude'] = map_data['longitude'].astype(float)
            st.map(map_data, zoom=9)

else:
    st.info("👈 Insira sua chave API para iniciar.")
