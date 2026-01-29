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
    .stMetric { background: white; padding: 20px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); border-left: 5px solid #1b5e20; }
    .header-box { background: linear-gradient(135deg, #064e3b 0%, #166534 100%); color: white; padding: 35px; border-radius: 15px; margin-bottom: 25px; }
    .tech-card { background: white; padding: 25px; border-radius: 12px; border: 1px solid #e2e8f0; margin-bottom: 20px; }
    .tech-header { color: #064e3b; font-weight: 800; font-size: 1.4em; border-bottom: 3px solid #f1f5f9; padding-bottom: 12px; margin-bottom: 20px; }
    .alert-high { background-color: #fef2f2; border-left: 6px solid #dc2626; padding: 20px; border-radius: 8px; color: #991b1b; font-weight: bold; }
    .alert-low { background-color: #f0fdf4; border-left: 6px solid #16a34a; padding: 20px; border-radius: 8px; color: #14532d; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# --- 2. BANCO DE DADOS AGRONÔMICO INTEGRAL ---
BANCO_MASTER = {
    "Batata (Solanum tuberosum)": {
        "t_base": 7,
        "vars": {
            "Orchestra": {"kc": 1.15, "gda_meta": 1600, "info": "Pele lisa premium. Foco em K."},
            "Cupido": {"kc": 1.10, "gda_meta": 1400, "info": "Ciclo ultra-curto. Alerta Requeima."},
            "Camila": {"kc": 1.15, "gda_meta": 1550, "info": "Mercado fresco. Sarna Comum."},
            "Atlantic": {"kc": 1.15, "gda_meta": 1650, "info": "Chips. Cuidado Coração Oco."}
        },
        "fases": {
            "Emergência (0-20d)": {"desc": "Brotamento inicial.", "fisio": "Dreno de reservas da batata-mãe.", "manejo": "Solo aerado.", "quim": "Azoxistrobina + Tiametoxam.", "bio": "EM-1 + Ácidos Húmicos."},
            "Vegetativo (20-35d)": {"desc": "Expansão IAF.", "fisio": "Alta demanda de N e Ca.", "manejo": "Amontoa técnica.", "quim": "Mancozeb.", "bio": "Bokashi líquido."},
            "Tuberização (35-50d)": {"desc": "Início ganchos.", "fisio": "Inversão hormonal.", "manejo": "Água constante.", "quim": "Revus + Metalaxil-M.", "bio": "Aminoácidos."},
            "Enchimento (50-80d)": {"desc": "Expansão radial.", "fisio": "Dreno de K e Mg.", "manejo": "Mosca Branca/Traça.", "quim": "Benévia.", "bio": "Potássio via Algas."},
            "Maturação (80d+)": {"desc": "Cura da pele.", "fisio": "Suberização térmica.", "manejo": "Dessecação.", "quim": "Diquat.", "bio": "Corte de N."}
        }
    },
    "Café (Coffea arabica)": {
        "t_base": 10,
        "vars": {"Catuaí": {"kc": 1.1, "gda_meta": 3000, "info": "Qualidade bebida."}, "Arara": {"kc": 1.2, "gda_meta": 2900, "info": "Resistente à ferrugem."}},
        "fases": {"Florada": {"desc": "Antese.", "fisio": "Pico de B e Zn.", "manejo": "Mancha Aureolada.", "quim": "Boscalida.", "bio": "Ca+B."}, "Chumbinho": {"desc": "Expansão.", "fisio": "Divisão celular.", "manejo": "Cercospora.", "quim": "Priori Xtra.", "bio": "K-amino."}}
    },
    "Mirtilo (Blueberry)": {
        "t_base": 7, "vars": {"Emerald": {"kc": 0.95, "gda_meta": 1800, "info": "pH 4.5."}, "Biloxi": {"kc": 0.90, "gda_meta": 1900, "info": "Ereta."}},
        "fases": {"Crescimento": {"desc": "Expansão baga.", "fisio": "Açúcares.", "manejo": "Antracnose.", "quim": "Azoxistrobina.", "bio": "Ácidos Fúlvicos."}}
    },
    "Tomate": {
        "t_base": 10, "vars": {"Italiano": {"kc": 1.2, "gda_meta": 1600, "info": "Fundo preto."}, "Grape": {"kc": 1.1, "gda_meta": 1450, "info": "Rachadura."}},
        "fases": {"Frutificação": {"desc": "Engorda.", "fisio": "Dreno de K.", "manejo": "Traça Tuta.", "quim": "Clorfenapir.", "bio": "Bokashi."}}
    },
    "Morango": {
        "t_base": 7, "vars": {"San Andreas": {"kc": 0.85, "gda_meta": 1200, "info": "Ácaros."}, "Albion": {"kc": 0.85, "gda_meta": 1250, "info": "Oídio."}},
        "fases": {"Colheita": {"desc": "Maturação.", "fisio": "Acúmulo Brix.", "manejo": "Botrytis.", "quim": "Ciprodinil.", "bio": "Silicato K."}}
    },
    "Amora/Framboesa": {
        "t_base": 7, "vars": {"Tupy": {"kc": 1.0, "gda_meta": 1500, "info": "Bagas grandes."}, "Heritage": {"kc": 1.1, "gda_meta": 1300, "info": "Remontante."}},
        "fases": {"Frutificação": {"desc": "Maturação.", "fisio": "Pigmentos.", "manejo": "Drosófila.", "quim": "Espinosade.", "bio": "Bokashi."}}
    }
}

# --- 3. MOTORES DE CÁLCULO ---
def get_forecast(lat, lon, api_key, kc, t_base):
    try:
        url = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={api_key}&units=metric&lang=pt_br"
        r = requests.get(url).json()
        dados = []
        if 'list' in r:
            for i in range(0, 40, 8):
                item = r['list'][i]
                t, u = item['main']['temp'], item['main']['humidity']
                es = 0.61078 * math.exp((17.27 * t) / (t + 237.3))
                ea = es * (u / 100); vpd = round(es - ea, 2)
                et0 = 0.0023 * (t + 17.8) * (t ** 0.5) * 0.408
                dados.append({'Data': datetime.fromtimestamp(item['dt']).strftime('%d/%m'), 'Temp': t, 'Umid': u, 'VPD': vpd, 'Chuva': round(item.get('rain', {}).get('3h', 0), 1), 'GDA': max(0, t - t_base), 'ETc': round(et0 * kc, 2)})
            return pd.DataFrame(dados)
    except: return pd.DataFrame()

def get_radar(lat, lon, api_key):
    pontos = {"Norte": (lat+0.1, lon), "Sul": (lat-0.1, lon), "Leste": (lat, lon+0.1), "Oeste": (lat, lon-0.1)}
    res = []
    for d, c in pontos.items():
        try:
            r = requests.get(f"https://api.openweathermap.org/data/2.5/weather?lat={c[0]}&lon={c[1]}&appid={api_key}&units=metric").json()
            res.append({"Direção": d, "Temp": r['main']['temp'], "Chuva": "Sim" if "rain" in r else "Não"})
        except: pass
    return pd.DataFrame(res)

# --- 4. SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Configuração")
    api_w = st.secrets.get("OPENWEATHER_KEY", "")
    api_g = st.secrets.get("GEMINI_KEY", "")
    st.divider()
    lat_f = st.number_input("Latitude:", value=-13.2000, format="%.4f")
    lon_f = st.number_input("Longitude:", value=-41.4000, format="%.4f")
    st.divider()
    cultura_sel = st.selectbox("Cultura:", list(BANCO_MASTER.keys()))
    var_sel = st.selectbox("Variedade:", list(BANCO_MASTER[cultura_sel]['vars'].keys()))
    fase_sel = st.selectbox("Fase Atual:", list(BANCO_MASTER[cultura_sel]['fases'].keys()))
    d_plantio = st.date_input("Início do Ciclo:", date(2025, 12, 1))

# --- 5. DASHBOARD ---
st.markdown(f"""<div class="header-box"><h1>Agro-Intel Titan Pro v32</h1><p>Monitoramento: {cultura_sel} | Cultivar: {var_sel}</p></div>""", unsafe_allow_html=True)

if api_w:
    crop_info = BANCO_MASTER[cultura_sel]
    v_info = crop_info['vars'][var_sel]
    f_info = crop_info['fases'][fase_sel]
    df = get_forecast(lat_f, lon_f, api_w, v_info['kc'], crop_info['t_base'])
    
    if not df.empty:
        hoje = df.iloc[0]; dias = (date.today() - d_plantio).days
        gda_atual = dias * df['GDA'].mean(); meta = v_info['gda_meta']
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("🌡️ Temp.", f"{hoje['Temp']:.1f}°C")
        c2.metric("💧 Umidade", f"{hoje['Umid']}%")
        c3.metric("💦 ETc", f"{hoje['ETc']} mm")
        c4.metric("📅 Idade", f"{dias} dias")

        tabs = st.tabs(["🎓 Consultoria", "📊 Clima & Água", "📡 Radar", "👁️ IA Vision", "💰 Custos", "🚚 Logística"])

        with tabs[0]:
            
            st.markdown(f"### 🔥 Acúmulo Térmico: {gda_atual:.0f} / {meta} GDA")
            st.progress(min(1.0, gda_atual/meta))
            estilo = "alert-high" if hoje['Umid'] > 85 else "alert-low"
            msg = "🚨 RISCO FÚNGICO ALTO" if hoje['Umid'] > 85 else "✅ CONDIÇÃO SEGURA"
            st.markdown(f"<div class='{estilo}'>{msg}</div>", unsafe_allow_html=True)
            
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown(f"<div class='tech-card'><b>🧬 Fisiologia:</b><br>{f_info['fisio']}<br><br><b>Biológico:</b><br>{f_info['bio']}</div>", unsafe_allow_html=True)
            with col_b:
                st.markdown(f"<div class='tech-card'><b>🧪 Prescrição:</b><br>Manejo: {f_info['manejo']}<hr>Química:<br>{f_info['quim']}</div>", unsafe_allow_html=True)

        with tabs[1]:
            fig = go.Figure()
            fig.add_trace(go.Bar(x=df['Data'], y=df['Chuva'], name='Chuva', marker_color='#3b82f6'))
            fig.add_trace(go.Scatter(x=df['Data'], y=df['ETc'], name='Consumo ETc', line=dict(color='#ef4444', width=3)))
            st.plotly_chart(fig, use_container_width=True)

        with tabs[2]:
            st.markdown("### 📡 Radar Regional (15km)")
            df_radar = get_radar(lat_f, lon_f, api_w)
            if not df_radar.empty:
                cols = st.columns(4)
                for idx, row in df_radar.iterrows():
                    with cols[idx]: st.info(f"**{row['Direção']}**\n\n{row['Temp']}°C\n\nChuva: {row['Chuva']}")

        with tabs[3]:
            if api_g:
                foto = st.camera_input("Escanear Sintoma")
                if foto:
                    genai.configure(api_key=api_g)
                    res = genai.GenerativeModel('gemini-1.5-flash').generate_content([f"Agrônomo Expert. Analise imagem de {cultura_sel}.", Image.open(foto)])
                    st.success(res.text)

        with tabs[5]:
            dist = 450; peso = st.slider("Carga (kg)", 100, 800, 400)
            custo = (dist/10)*6.20
            l1, l2 = st.columns(2)
            l1.metric("Custo Viagem", f"R$ {custo:.2f}")
            l2.metric("R$/kg", f"R$ {custo/peso:.2f}")
else:
    st.error("⚠️ Configure as chaves de API nos Secrets.")
