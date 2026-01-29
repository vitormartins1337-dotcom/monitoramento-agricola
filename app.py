import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
import math
from datetime import datetime, date

# --- 1. CONFIGURAÇÃO VISUAL ---
st.set_page_config(
    page_title="Agro-Intel Chapada Pro",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    div[data-testid="metric-container"] { background-color: #fff; border: 1px solid #ddd; padding: 10px; border-radius: 8px; }
    .genetica-box { background: linear-gradient(to right, #1565c0, #42a5f5); color: white; padding: 15px; border-radius: 8px; margin-bottom: 20px; }
    .alerta-box { background-color: #ffebee; border-left: 5px solid #d32f2f; padding: 15px; margin-top: 10px; border-radius: 5px; }
    .manejo-box { background-color: #e8f5e9; border-left: 5px solid #2e7d32; padding: 15px; margin-top: 10px; border-radius: 5px; }
    h3 { margin-top: 0; }
</style>
""", unsafe_allow_html=True)

# --- 2. CÉREBRO AGRONÔMICO (Manejo & Química) ---
BANCO_AGRONOMICO = {
    "Batata (Solanum tuberosum)": {
        "variedades": {
            "Orchestra": {"ciclo": 110, "kc": 1.15, "info": "Exigente em Potássio. Sensível a Pinta Preta."},
            "Cupido": {"ciclo": 90, "kc": 1.10, "info": "Ciclo curto. Altíssima sensibilidade a Requeima."},
            "Camila": {"ciclo": 100, "kc": 1.15, "info": "Pele sensível. Cuidado com sarna."},
            "Atlantic": {"ciclo": 105, "kc": 1.15, "info": "Chips. Evitar oscilação hídrica (Coração Oco)."}
        },
        "fases": {
            "Vegetativo": {
                "manejo": "Realizar a Amontoa (Chegar terra) para proteger estolões. Monitorar Larva Minadora.",
                "risco": ["Larva Minadora", "Rizoctonia"],
                "moleculas": "Abamectina (Minadora), Azoxistrobina (Solo)."
            },
            "Tuberização (Crítico)": {
                "manejo": "Irrigação constante. Fase crítica para definição de calibre. Não deixar faltar água.",
                "risco": ["Requeima (Phytophthora)", "Pinta Preta (Alternaria)"],
                "moleculas": "Preventivo: Mancozeb/Clorotalonil. Curativo: Metalaxil-M, Dimetomorfe, Mandipropamida."
            },
            "Maturação": {
                "manejo": "Dessecação da rama. Cuidado com danos mecânicos na colheita.",
                "risco": ["Traça da Batata", "Sarna"],
                "moleculas": "Cipermetrina (Traça). Evitar excesso de água para não dar Sarna."
            }
        }
    },
    "Mirtilo (Vaccinium spp.)": {
        "variedades": {
            "Emerald": {"ciclo": 150, "kc": 0.95, "info": "Vigorosa. Atenção ao pH (4.5-5.5)."},
            "Biloxi": {"ciclo": 160, "kc": 0.90, "info": "Ereta. Exige poda de limpeza central."}
        },
        "fases": {
            "Poda/Dormência": {
                "manejo": "Aplicação de Cianamida Hidrogenada (se necessário) para uniformizar brotação.",
                "risco": ["Cochonilhas"],
                "moleculas": "Óleo Mineral + Imidacloprido."
            },
            "Florada": {
                "manejo": "Introduzir abelhas (Bombus ou Apis). Evitar inseticidas fortes.",
                "risco": ["Botrytis (Mofo Cinzento)"],
                "moleculas": "Fludioxonil, Ciprodinil (Seguros para abelhas à noite)."
            },
            "Frutificação": {
                "manejo": "Fertirrigação sem Nitratos (usar Amônio). Monitorar Ferrugem.",
                "risco": ["Ferrugem", "Antracnose"],
                "moleculas": "Tebuconazol (Cuidado com carência), Azoxistrobina."
            }
        }
    },
    "Morango (Fragaria x ananassa)": {
        "variedades": {
            "San Andreas": {"ciclo": 180, "kc": 0.85, "info": "Dia neutro. Sensível a Ácaro Rajado."},
            "Albion": {"ciclo": 180, "kc": 0.85, "info": "Fruto doce. Sensível a Oídio."}
        },
        "fases": {
            "Vegetativo": {
                "manejo": "Retirada de estolões para focar em coroa. Limpeza de folhas velhas.",
                "risco": ["Oídio", "Pulgão"],
                "moleculas": "Enxofre (Oídio), Acetamiprido (Pulgão)."
            },
            "Frutificação": {
                "manejo": "Aplicação de Cálcio e Silício. Colheita frequente.",
                "risco": ["Botrytis", "Ácaro Rajado"],
                "moleculas": "Abamectina/Etoxazol (Ácaros). Iprodiona (Botrytis)."
            }
        }
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
                'Chuva': round(chuva, 1),
                'VPD': vpd,
                'Delta T': dt,
                'Umid': item['main']['humidity'],
                'ETc': round(et0 * kc_max, 2)
            })
        return pd.DataFrame(dados)
    except: return pd.DataFrame()

# --- 4. SIDEBAR ---
with st.sidebar:
    st.header("🎛️ Controle da Lavoura")
    api_key = st.text_input("🔑 Chave API", type="password")
    st.divider()
    
    cultura = st.selectbox("1. Cultura:", list(BANCO_AGRONOMICO.keys()))
    lista_vars = list(BANCO_AGRONOMICO[cultura]['variedades'].keys())
    variedade = st.selectbox("2. Cultivar:", lista_vars)
    
    # Busca Info
    info_cultura = BANCO_AGRONOMICO[cultura]
    info_var = info_cultura['variedades'][variedade]
    lista_fases = list(info_cultura['fases'].keys())
    
    data_plantio = st.date_input("3. Data Início:", date(2025, 11, 25))
    dias_campo = (date.today() - data_plantio).days
    
    fase_atual = st.selectbox("4. Fase Fenológica:", lista_fases, index=1)
    
    st.info(f"🧬 **{variedade}**\nIdade: {dias_campo} dias")

# --- 5. DASHBOARD ---
st.title("🛰️ Agro-Intel v6.0")

if api_key:
    # Dados da Fase Selecionada
    dados_fase = info_cultura['fases'][fase_atual]

    st.markdown(f"""
    <div class="genetica-box">
        <h3>🚜 {cultura.split('(')[0]} - {variedade} ({fase_atual})</h3>
        <p>{info_var['info']}</p>
    </div>
    """, unsafe_allow_html=True)

    df = get_forecast(api_key, FAZENDA['lat'], FAZENDA['lon'], info_var['kc'])
    
    if not df.empty:
        hoje = df.iloc[0]
        
        # KPIS
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("🌡️ Temperatura", f"{hoje['Temp']} °C", f"Umid: {hoje['Umid']}%")
        c2.metric("💧 VPD", f"{hoje['VPD']} kPa", "Ideal" if 0.4 <= hoje['VPD'] <= 1.3 else "Risco")
        c3.metric("💦 ETc (Consumo)", f"{hoje['ETc']} mm", f"Kc: {info_var['kc']}")
        c4.metric("🛡️ Delta T", f"{hoje['Delta T']} °C", "Ok" if 2 <= hoje['Delta T'] <= 8 else "Ruim")

        # ABAS PRINCIPAIS
        tab1, tab2, tab3 = st.tabs(["📚 Protocolo Agronômico", "📊 Clima & Irrigação", "📡 Radar GPS"])

        with tab1:
            st.markdown("### 📋 Planejamento Técnico da Semana")
            
            col_tec1, col_tec2 = st.columns(2)
            
            with col_tec1:
                st.markdown(f"""
                <div class="manejo-box">
                    <h4>🛠️ Manejo Cultural ({fase_atual})</h4>
                    <p>{dados_fase['manejo']}</p>
                </div>
                """, unsafe_allow_html=True)
                
                # Análise de Risco Climático para Doenças
                risco_clima = "Baixo"
                if hoje['Umid'] > 85 or hoje['Chuva'] > 2:
                    risco_clima = "ALTO (Umidade Elevada)"
                    cor_risco = "red"
                else:
                    cor_risco = "green"
                
                st.write(f"**Pressão Climática Hoje:** :{cor_risco}[{risco_clima}]")

            with col_tec2:
                st.markdown(f"""
                <div class="alerta-box">
                    <h4>💊 Farmácia Digital (Defensivos Sugeridos)</h4>
                    <p><b>Alvos Principais:</b> {', '.join(dados_fase['risco'])}</p>
                    <hr>
                    <p><b>🧪 Moléculas Indicadas:</b><br>{dados_fase['moleculas']}</p>
                </div>
                """, unsafe_allow_html=True)
                
                if risco_clima == "ALTO (Umidade Elevada)":
                    st.warning("⚠️ **Dica de Especialista:** Com a umidade alta detectada hoje, priorize produtos **SISTÊMICOS** ou de **PROFUNDIDADE**, pois produtos de contato podem ser lavados ou não ter eficácia curativa.")
                else:
                    st.success("✅ **Dica de Especialista:** Clima seco. Ótimo momento para produtos de **CONTATO/PROTETORES** (Mancozeb, Cobre, Enxofre) para blindar a planta.")

            st.caption("⚠️ Nota: As moléculas citadas são referências técnicas de Ingrediente Ativo. Consulte sempre um Receituário Agronômico para marcas comerciais e doses.")

        with tab2:
            fig = go.Figure()
            fig.add_trace(go.Bar(x=df['Data'], y=df['Chuva'], name='Chuva', marker_color='#29b6f6'))
            fig.add_trace(go.Scatter(x=df['Data'], y=df['ETc'], name='Consumo (ETc)', line=dict(color='#ef5350', width=2)))
            fig.update_layout(title="Balanço Hídrico", height=350)
            st.plotly_chart(fig, use_container_width=True)
            
            balanco = df['Chuva'].sum() - df['ETc'].sum()
            st.info(f"Balanço Semanal: {balanco:.1f} mm")

        with tab3:
            col_gps = st.columns(len(VIZINHOS))
            for i, v in enumerate(VIZINHOS):
                try:
                    r = requests.get(f"https://api.openweathermap.org/data/2.5/weather?lat={v['lat']}&lon={v['lon']}&appid={api_key}&units=metric").json()
                    cor = "#ffcdd2" if "rain" in str(r) else "#c8e6c9"
                    col_gps[i].markdown(f"<div style='background:{cor};padding:10px;border-radius:5px;text-align:center'><b>{v['nome'].split()[0]}</b><br>{r['main']['temp']:.0f}°C</div>", unsafe_allow_html=True)
                except: pass
            
            # Mapa (conversão segura)
            map_data = pd.DataFrame([FAZENDA] + VIZINHOS).rename(columns={"lat": "latitude", "lon": "longitude"})
            map_data['latitude'] = map_data['latitude'].astype(float)
            map_data['longitude'] = map_data['longitude'].astype(float)
            st.map(map_data, zoom=9)

else:
    st.info("👈 Insira sua chave API para iniciar.")
