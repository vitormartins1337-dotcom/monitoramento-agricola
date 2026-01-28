import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
import math
from datetime import datetime, date

# --- 1. CONFIGURAÇÃO DA PÁGINA (DESIGN CORPORATIVO) ---
st.set_page_config(
    page_title="Agro-Intel Manager",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS PERSONALIZADO ---
st.markdown("""
<style>
    div[data-testid="metric-container"] {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    h1, h2, h3 { color: #154c79; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
    .stAlert { border-radius: 6px; }
    /* Destaque para a cultura selecionada */
    .cultura-box {
        background-color: #e3f2fd;
        padding: 10px;
        border-radius: 5px;
        border-left: 5px solid #1565c0;
        margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. BANCO DE DADOS AGRONÔMICO (O CÉREBRO) ---
BANCO_CULTURAS = {
    "Batata (Solanum tuberosum)": {
        "t_base": 7, # Temperatura base para GDA
        "kc_fases": {"Inicial": 0.5, "Vegetativo": 0.8, "Tuberização": 1.15, "Maturação": 0.75},
        "ciclo": 120,
        "nutricao": {
            "Vegetativo": "Nitrogênio (N) alto para folhagem. Magnésio (Mg) para fotossíntese.",
            "Tuberização": "Potássio (K) crítico para transporte de açúcares. Boro (B) para evitar coração oco.",
            "Maturação": "Suspender N. Manter K moderado. Monitorar cálcio."
        }
    },
    "Morango (Fragaria x ananassa)": {
        "t_base": 10,
        "kc_fases": {"Inicial": 0.4, "Vegetativo": 0.7, "Florada/Fruto": 0.85, "Colheita": 0.9},
        "ciclo": 150, # Semiperene
        "nutricao": {
            "Vegetativo": "Equilíbrio N:K de 1:1. Foco em enraizamento (P).",
            "Florada/Fruto": "Aumentar K e Ca. Relação N:K de 1:1.5. Silício ajuda na resistência.",
            "Colheita": "Manter K alto para Brix e firmeza."
        }
    },
    "Café (Coffea arabica)": {
        "t_base": 10,
        "kc_fases": {"Vegetativo": 0.9, "Florada": 1.0, "Chumbinho": 1.1, "Granação": 1.2},
        "ciclo": 365,
        "nutricao": {
            "Vegetativo": "N e P para estruturação.",
            "Florada": "Boro e Zinco essenciais para pegamento.",
            "Granação": "Demanda máxima de K e N para enchimento de grão."
        }
    },
    "Tomate (Solanum lycopersicum)": {
        "t_base": 10,
        "kc_fases": {"Inicial": 0.6, "Vegetativo": 0.9, "Florada": 1.1, "Colheita": 1.25},
        "ciclo": 110,
        "nutricao": {
            "Vegetativo": "Cálcio via solo e foliar para evitar Fundo Preto.",
            "Florada": "Boro para viabilidade do pólen.",
            "Colheita": "Potássio para sabor e cor."
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

# --- 3. FUNÇÕES CIENTÍFICAS ---
def calc_agro(temp, umid):
    es = 0.61078 * math.exp((17.27 * temp) / (temp + 237.3))
    ea = es * (umid / 100)
    vpd = round(es - ea, 2)
    tw = temp * math.atan(0.151977 * (umid + 8.313659)**0.5) + math.atan(temp + umid) - math.atan(umid - 1.676331) + 0.00391838 * (umid)**1.5 * math.atan(0.023101 * umid) - 4.686035
    dt = round(temp - tw, 1)
    return dt, vpd

def get_forecast(api_key, lat, lon, kc_selecionado):
    try:
        url = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={api_key}&units=metric&lang=pt_br"
        r = requests.get(url).json()
        dados = []
        for i in range(0, 40, 8):
            item = r['list'][i]
            dt, vpd = calc_agro(item['main']['temp'], item['main']['humidity'])
            chuva = sum([r['list'][i+j].get('rain', {}).get('3h', 0) for j in range(8) if i+j < len(r['list'])])
            et0 = 0.0023 * (item['main']['temp'] + 17.8) * (item['main']['temp'] ** 0.5) * 0.408
            
            # GDA Diário Estimado ((Tmax + Tmin)/2) - Tbase (Simplificado usando Temp media do momento)
            # Para precisão total precisaria Tmax e Tmin do dia, usamos Temp do momento como proxy
            
            dados.append({
                'Data': datetime.fromtimestamp(item['dt']).strftime('%d/%m'),
                'Temp': item['main']['temp'],
                'Chuva (mm)': round(chuva, 1),
                'VPD (kPa)': vpd,
                'Delta T': dt,
                'Umid (%)': item['main']['humidity'],
                'ETc (mm)': round(et0 * kc_selecionado, 2)
            })
        return pd.DataFrame(dados)
    except: return pd.DataFrame()

# --- 4. SIDEBAR INTELIGENTE ---
with st.sidebar:
    st.header("🎛️ Painel de Controle")
    api_key = st.text_input("🔑 Chave API OpenWeather", type="password")
    
    st.divider()
    st.subheader("🌱 Configuração da Lavoura")
    
    # Seleção de Cultura
    cultura_sel = st.selectbox("Selecione a Cultura:", list(BANCO_CULTURAS.keys()))
    dados_cultura = BANCO_CULTURAS[cultura_sel]
    
    # Data de Plantio
    data_plantio = st.date_input("Data de Plantio:", date(2025, 11, 25))
    
    # Cálculo de Dias
    dias_campo = (date.today() - data_plantio).days
    
    # Sugestão Automática de Fase
    fases = list(dados_cultura['kc_fases'].keys())
    fase_sugerida = fases[0]
    
    # Lógica simples de estimativa de fase (pode ser refinada)
    progresso = dias_campo / dados_cultura['ciclo']
    if progresso < 0.2: fase_sugerida = fases[0]
    elif progresso < 0.5: fase_sugerida = fases[1]
    elif progresso < 0.8: fase_sugerida = fases[2]
    else: fase_sugerida = fases[-1] if len(fases) > 3 else fases[2]

    fase_atual = st.selectbox("Fase Fenológica (Ajuste se necessário):", fases, index=fases.index(fase_sugerida))
    
    # Pega o KC específico da fase
    kc_dinamico = dados_cultura['kc_fases'][fase_atual]
    
    st.info(f"""
    📊 **Status Calculado:**
    - **Dias de Campo:** {dias_campo} dias
    - **Kc Aplicado:** {kc_dinamico}
    - **Temp. Base:** {dados_cultura['t_base']}°C
    """)

# --- 5. DASHBOARD PRINCIPAL ---
st.title("🛰️ Agro-Intel Manager v3.0")

if api_key:
    # Cabeçalho da Cultura
    st.markdown(f"""
    <div class="cultura-box">
        <h3>🚜 Gestão Ativa: {cultura_sel.split('(')[0]}</h3>
        <p><strong>Fase Atual:</strong> {fase_atual} | <strong>Recomendação Principal:</strong> {dados_cultura['nutricao'].get(fase_atual, 'Seguir manejo padrão.')}</p>
    </div>
    """, unsafe_allow_html=True)

    df = get_forecast(api_key, FAZENDA['lat'], FAZENDA['lon'], kc_dinamico)
    
    if not df.empty:
        hoje = df.iloc[0]
        
        # --- KPIS ---
        c1, c2, c3, c4 = st.columns(4)
        
        # GDA Acumulado (Estimado)
        gda_acumulado = dias_campo * (hoje['Temp'] - dados_cultura['t_base']) # Simplificado
        gda_acumulado = max(gda_acumulado, 0) # Não pode ser negativo

        c1.metric("🌡️ Temperatura", f"{hoje['Temp']} °C", f"Umid: {hoje['Umid (%)']}%")
        c2.metric("💧 VPD (Pressão)", f"{hoje['VPD (kPa)']} kPa", "Risco" if hoje['VPD (kPa)'] > 1.3 else "Ideal")
        c3.metric("💦 ETc (Consumo Hoje)", f"{hoje['ETc (mm)']} mm", f"Kc: {kc_dinamico}")
        c4.metric("📈 GDA (Estimado)", f"{gda_acumulado:.0f}", f"Base {dados_cultura['t_base']}°C")

        # --- ABAS ---
        tab1, tab2, tab3, tab4 = st.tabs(["📊 Clima & Irrigação", "🧬 Fisiologia Específica", "🧪 Calculadora Ferti", "📡 Radar GPS"])

        # ABA 1: CLIMA
        with tab1:
            fig = go.Figure()
            fig.add_trace(go.Bar(x=df['Data'], y=df['Chuva (mm)'], name='Chuva (mm)'))
            fig.add_trace(go.Scatter(x=df['Data'], y=df['ETc (mm)'], name='Consumo Planta (ETc)', line=dict(color='orange', width=2, dash='dot')))
            fig.update_layout(title="Balanço Hídrico: Entrada (Chuva) vs Saída (Consumo)", height=350)
            st.plotly_chart(fig, use_container_width=True)
            
            balanco = df['Chuva (mm)'].sum() - df['ETc (mm)'].sum()
            st.caption(f"**Balanço Semanal:** {balanco:.1f} mm. (Positivo = Sobra, Negativo = Falta)")

        # ABA 2: FISIOLOGIA (DINÂMICA)
        with tab2:
            st.markdown(f"### 🔬 Análise para {cultura_sel}")
            col_a, col_b = st.columns(2)
            
            with col_a:
                st.info(f"**Recomendação Nutricional ({fase_atual}):**\n\n{dados_cultura['nutricao'].get(fase_atual, 'Manter equilíbrio NPK.')}")
                st.markdown("""
                **Interpretação Científica:**
                * **Nitrogênio:** Essencial para expansão foliar.
                * **Magnésio:** Central na fotossíntese.
                * **Potássio:** Transporte de carga (açúcar) no floema.
                """)
            
            with col_b:
                st.warning(f"**Pontos de Atenção (VPD {hoje['VPD (kPa)']} kPa):**")
                if hoje['VPD (kPa)'] > 1.3:
                    st.write("🔴 **VPD Alto:** Planta fechando estômatos. Absorção de Cálcio via fluxo de massa está comprometida. Risco de *Tip Burn* em folhas novas.")
                elif hoje['VPD (kPa)'] < 0.4:
                    st.write("🔵 **VPD Baixo:** Transpiração parada. Risco de doenças. Não irrigue em excesso agora.")
                else:
                    st.write("🟢 **VPD Ideal:** Taxa fotossintética máxima. Ótimo momento para aplicação foliar.")

        # ABA 3: CALCULADORA (NOVA!)
        with tab3:
            st.markdown("### 🧪 Calculadora Rápida de Fertirrigação")
            st.write("Ajuste a concentração baseada na fase atual.")
            
            col_calc1, col_calc2 = st.columns(2)
            with col_calc1:
                vol_tanque = st.number_input("Volume do Tanque (Litros):", value=1000)
                qtd_plantas = st.number_input("Número de Plantas:", value=5000)
            
            with col_calc2:
                meta_n = st.number_input("Meta de N (g/planta):", value=0.5)
                st.markdown("---")
                total_n = meta_n * qtd_plantas
                st.success(f"⚖️ **Total de Nitrogênio Puro necessário:** {total_n/1000:.2f} kg")
                st.caption("Nota: Divida pela % do adubo (ex: Ureia 45% -> Total / 0.45)")

        # ABA 4: RADAR
        with tab4:
            map_data = pd.DataFrame([FAZENDA] + VIZINHOS).rename(columns={"lat": "latitude", "lon": "longitude"})
            # Conversão forçada para float para evitar erro
            map_data['latitude'] = map_data['latitude'].astype(float)
            map_data['longitude'] = map_data['longitude'].astype(float)
            st.map(map_data, zoom=9)
            
            st.markdown("#### Monitoramento Vizinhos:")
            row = st.columns(len(VIZINHOS))
            for i, v in enumerate(VIZINHOS):
                try:
                    r = requests.get(f"https://api.openweathermap.org/data/2.5/weather?lat={v['lat']}&lon={v['lon']}&appid={api_key}&units=metric").json()
                    row[i].metric(v['nome'].split()[0], f"{r['main']['temp']:.0f}°C", r['weather'][0]['description'])
                except: pass

else:
    st.info("👈 Insira sua chave API no menu lateral para iniciar o sistema.")
