import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
import math
import google.generativeai as genai
from PIL import Image
from datetime import datetime, date

# --- 1. CONFIGURAÇÃO VISUAL DE ELITE ---
st.set_page_config(
    page_title="Agro-Intel 4.0",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS Profissional
st.markdown("""
<style>
    .main { background-color: #f8f9fa; }
    div[data-testid="metric-container"] { background-color: #ffffff; border: 1px solid #e0e0e0; padding: 15px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
    .genetica-header { background: linear-gradient(135deg, #1b5e20 0%, #4caf50 100%); color: white; padding: 20px; border-radius: 12px; margin-bottom: 25px; }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { height: 50px; white-space: pre-wrap; background-color: #fff; border-radius: 5px; border: 1px solid #ddd; }
    .stTabs [aria-selected="true"] { background-color: #e8f5e9; border-color: #2e7d32; color: #2e7d32; font-weight: bold; }
    .financeiro-box { border-left: 5px solid #fbc02d; background-color: #fffde7; padding: 15px; border-radius: 5px; }
</style>
""", unsafe_allow_html=True)

# --- 2. BANCO DE DADOS AGRONÔMICO (CHAPADA DIAMANTINA) ---
BANCO_AGRO = {
    "Batata": {
        "vars": {
            "Orchestra": {"kc": 1.15, "info": "Exigente em K. Cuidado com Pinta Preta."},
            "Cupido": {"kc": 1.10, "info": "Ciclo Curto. Sensível a Requeima."},
            "Camila": {"kc": 1.15, "info": "Pele sensível. Sarna."},
            "Atlantic": {"kc": 1.15, "info": "Chips. Coração Oco."}
        },
        "fases": ["Vegetativo", "Tuberização", "Enchimento", "Maturação"]
    },
    "Mirtilo": {
        "vars": {
            "Emerald": {"kc": 0.95, "info": "Vigorosa. pH ácido (4.5)."},
            "Biloxi": {"kc": 0.90, "info": "Poda de limpeza central."}
        },
        "fases": ["Brotação", "Florada", "Fruto Verde", "Colheita"]
    },
    "Morango": {
        "vars": {
            "San Andreas": {"kc": 0.85, "info": "Sensível a Ácaros."},
            "Albion": {"kc": 0.85, "info": "Qualidade de fruto."}
        },
        "fases": ["Vegetativo", "Florada", "Frutificação", "Colheita"]
    },
    "Café": {
        "vars": {"Catuaí": {"kc": 1.1, "info": "Ferrugem."}, "Arara": {"kc": 1.2, "info": "Cercospora."}},
        "fases": ["Vegetativo", "Florada", "Chumbinho", "Granação"]
    }
}

# --- 3. FUNÇÕES CIENTÍFICAS ---
def calc_agro(temp, umid):
    es = 0.61078 * math.exp((17.27 * temp) / (temp + 237.3))
    ea = es * (umid / 100)
    vpd = round(es - ea, 2)
    tw = temp * math.atan(0.151977 * (umid + 8.313659)**0.5) + math.atan(temp + umid) - math.atan(umid - 1.676331) + 0.00391838 * (umid)**1.5 * math.atan(0.023101 * umid) - 4.686035
    dt = round(temp - tw, 1)
    return dt, vpd

def get_forecast(api_key, lat, lon, kc):
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
                'ETc': round(et0 * kc, 2)
            })
        return pd.DataFrame(dados)
    except: return pd.DataFrame()

def analise_ia_gemini(api_key, imagem, cultura, contexto_clima):
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"""
        Você é um Engenheiro Agrônomo Sênior especialista em Fitopatologia.
        Analise esta imagem de uma folha de {cultura}.
        Contexto Climático atual: {contexto_clima}.
        1. Identifique a possível doença ou deficiência.
        2. Explique por que o clima atual favorece ou não isso.
        3. Sugira o ingrediente ativo (químico) e uma solução biológica.
        Seja direto e técnico.
        """
        response = model.generate_content([prompt, imagem])
        return response.text
    except Exception as e:
        return f"Erro na IA: {str(e)}. Verifique a Chave API."

# --- 4. SIDEBAR DE COMANDO ---
with st.sidebar:
    st.header("🎛️ Centro de Comando")
    
    with st.expander("🔑 Credenciais (APIs)", expanded=True):
        weather_key = st.text_input("OpenWeather Key", type="password")
        gemini_key = st.text_input("Google Gemini AI Key", type="password", help="Para o diagnóstico por foto")
    
    st.divider()
    
    cultura_sel = st.selectbox("Cultura:", list(BANCO_AGRO.keys()))
    var_sel = st.selectbox("Variedade:", list(BANCO_AGRO[cultura_sel]['vars'].keys()))
    fase_sel = st.selectbox("Fase Fenológica:", BANCO_AGRO[cultura_sel]['fases'], index=1)
    
    # Memória de Plantio (Session State)
    if 'data_plantio' not in st.session_state:
        st.session_state['data_plantio'] = date(2025, 11, 25)
    
    d_plantio = st.date_input("Data Plantio:", st.session_state['data_plantio'])
    dias_campo = (date.today() - d_plantio).days
    
    info = BANCO_AGRO[cultura_sel]['vars'][var_sel]
    st.info(f"🧬 **{var_sel}** | Idade: {dias_campo} dias | Kc: {info['kc']}")

# --- 5. DASHBOARD PRINCIPAL ---
st.title("🛰️ Agro-Intel System v7.0")

if weather_key:
    # CABEÇALHO
    st.markdown(f"""
    <div class="genetica-header">
        <h2 style="margin:0; color:white;">🚜 {cultura_sel} - {var_sel}</h2>
        <p style="margin:0; opacity:0.9;">Fase: {fase_sel} | Ponto de Atenção: {info['info']}</p>
    </div>
    """, unsafe_allow_html=True)

    # DADOS CLIMÁTICOS
    lat, lon = "-13.414", "-41.285" # Ibicoara
    df = get_forecast(weather_key, lat, lon, info['kc'])
    
    if not df.empty:
        hoje = df.iloc[0]
        
        # KPIS
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("🌡️ Temperatura", f"{hoje['Temp']}°C", f"Umid: {hoje['Umid']}%")
        c2.metric("💧 VPD (Pressão)", f"{hoje['VPD']} kPa", "Risco" if hoje['VPD'] > 1.3 else "Ideal")
        c3.metric("💦 ETc (Consumo)", f"{hoje['ETc']} mm", f"Kc: {info['kc']}")
        c4.metric("🛡️ Delta T", f"{hoje['Delta T']}°C", "Pulverizar" if 2 <= hoje['Delta T'] <= 8 else "Parar")

        # NAVEGAÇÃO
        tab1, tab2, tab3, tab4 = st.tabs(["📊 Clima & Hídrico", "👁️ IA Vision (Diagnóstico)", "💰 Gestão Financeira", "📡 Radar GPS"])

        # --- ABA 1: CLIMA ---
        with tab1:
            fig = go.Figure()
            fig.add_trace(go.Bar(x=df['Data'], y=df['Chuva'], name='Chuva', marker_color='#29b6f6'))
            fig.add_trace(go.Scatter(x=df['Data'], y=df['ETc'], name='Consumo (ETc)', line=dict(color='#ef5350', width=2)))
            fig.update_layout(title="Balanço Hídrico Semanal", height=350)
            st.plotly_chart(fig, use_container_width=True)
            
            balanco = df['Chuva'].sum() - df['ETc'].sum()
            st.info(f"Balanço: {balanco:.1f} mm. (Positivo = Sobra, Negativo = Falta).")

        # --- ABA 2: IA VISION (GEMINI) ---
        with tab2:
            st.markdown("### 🔬 Diagnóstico Fitopatológico com IA")
            st.write("Tire uma foto da folha ou carregue uma imagem para análise imediata.")
            
            col_cam, col_res = st.columns([1, 2])
            
            with col_cam:
                img_file = st.camera_input("📸 Tirar Foto da Folha")
                if not img_file:
                    img_file = st.file_uploader("Ou carregue da galeria", type=['jpg', 'png', 'jpeg'])

            with col_res:
                if img_file and gemini_key:
                    st.success("Imagem capturada! Analisando...")
                    image = Image.open(img_file)
                    st.image(image, caption="Imagem Analisada", width=200)
                    
                    # Contexto para a IA ser precisa
                    contexto = f"Umidade {hoje['Umid']}%, VPD {hoje['VPD']} kPa, Temperatura {hoje['Temp']}C. Fase {fase_sel}."
                    
                    with st.spinner("Consultando Banco de Dados Agronômico..."):
                        resultado = analise_ia_gemini(gemini_key, image, cultura_sel, contexto)
                        st.markdown(f"### 🩺 Laudo da IA:\n{resultado}")
                elif img_file and not gemini_key:
                    st.warning("⚠️ Insira a chave do Google Gemini no menu lateral para ativar a IA.")
                else:
                    st.info("Aguardando imagem...")

        # --- ABA 3: FINANCEIRO ---
        with tab3:
            st.markdown("### 💰 Controle de Custos (Safra Atual)")
            
            # Inicializa Sessão Financeira
            if 'custos' not in st.session_state: st.session_state['custos'] = []
            
            c_input1, c_input2, c_input3 = st.columns(3)
            with c_input1: item = st.text_input("Item (Ex: Ureia, Fungicida)")
            with c_input2: valor = st.number_input("Valor Total (R$)", min_value=0.0)
            with c_input3: 
                st.write("") # Espaço
                st.write("") 
                if st.button("➕ Adicionar Custo"):
                    if item and valor > 0:
                        st.session_state['custos'].append({"Item": item, "Valor": valor, "Data": date.today()})
                        st.success("Lançado!")

            # Tabela e Totais
            if st.session_state['custos']:
                df_fin = pd.DataFrame(st.session_state['custos'])
                st.dataframe(df_fin, use_container_width=True)
                
                total = df_fin['Valor'].sum()
                estimativa_saca = st.number_input("Produtividade Esperada (Sacas/cx):", value=1000)
                custo_un = total / estimativa_saca if estimativa_saca > 0 else 0
                
                st.markdown(f"""
                <div class="financeiro-box">
                    <h3>💵 Custo Total: R$ {total:,.2f}</h3>
                    <p>Custo por Saca/Cx Estimado: <b>R$ {custo_un:,.2f}</b></p>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.info("Nenhum custo lançado hoje.")

        # --- ABA 4: RADAR ---
        with tab4:
            VIZINHOS = [{"nome": "Mucugê", "lat": -13.005, "lon": -41.371}, {"nome": "Barra da Estiva", "lat": -13.623, "lon": -41.326}, {"nome": "Cascavel", "lat": -13.196, "lon": -41.445}]
            map_data = pd.DataFrame([{"nome": "Sede", "lat": float(lat), "lon": float(lon)}] + VIZINHOS)
            st.map(map_data.rename(columns={"lat":"latitude", "lon":"longitude"}), zoom=9)
            
            row = st.columns(3)
            for i, v in enumerate(VIZINHOS):
                try:
                    r = requests.get(f"https://api.openweathermap.org/data/2.5/weather?lat={v['lat']}&lon={v['lon']}&appid={weather_key}&units=metric").json()
                    row[i].metric(v['nome'], f"{r['main']['temp']:.0f}°C", r['weather'][0]['description'])
                except: pass

else:
    st.warning("👈 Insira a Chave OpenWeather no menu lateral para iniciar o sistema.")
