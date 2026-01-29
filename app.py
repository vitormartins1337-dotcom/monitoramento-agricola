import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
import math
from datetime import datetime, date

# --- 1. CONFIGURAÇÃO VISUAL (TEXT-HEAVY PROFISSIONAL) ---
st.set_page_config(
    page_title="Agro-Intel Sênior",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Design focado em legibilidade de texto técnico
st.markdown("""
<style>
    .main { background-color: #f8f9fa; }
    div[data-testid="metric-container"] { background-color: #fff; border-left: 5px solid #1e3a8a; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
    .header-box { background: #1e3a8a; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
    .tech-card { background-color: #fff; padding: 20px; border-radius: 8px; border: 1px solid #e5e7eb; margin-bottom: 15px; }
    .tech-title { color: #1e3a8a; font-weight: bold; font-size: 1.1em; border-bottom: 2px solid #e5e7eb; padding-bottom: 10px; margin-bottom: 10px; }
    .alert-high { background-color: #fee2e2; border-left: 5px solid #dc2626; padding: 15px; border-radius: 4px; color: #991b1b; }
    .alert-low { background-color: #dcfce7; border-left: 5px solid #16a34a; padding: 15px; border-radius: 4px; color: #166534; }
    h3 { margin-top: 0; }
</style>
""", unsafe_allow_html=True)

# --- 2. BANCO DE DADOS AGRONÔMICO (FENOLOGIA CORRIGIDA & DETALHADA) ---
BANCO_MASTER = {
    "Batata (Solanum tuberosum)": {
        "t_base": 7, # Temp base para GDA
        "vars": {
            "Orchestra": {"kc": 1.15, "info": "Exigente em K. Acabamento de pele visual."},
            "Cupido": {"kc": 1.10, "info": "Ciclo Curto. Sensibilidade extrema a Requeima."},
            "Camila": {"kc": 1.15, "info": "Referência de mercado. Cuidado com Sarna."},
            "Atlantic": {"kc": 1.15, "info": "Indústria (Chips). Evitar estresse hídrico (Coração Oco)."}
        },
        "fases": {
            "Emergência/Estabelecimento": {
                "desc": "Brotamento e desenvolvimento inicial da haste principal.",
                "fisiologia": "A planta drena reservas da batata-mãe. O sistema radicular é incipiente e exige solo aerado (não encharcar).",
                "manejo": "Monitorar Rizoctonia (Cancro de Haste) e Larva Minadora nos primeiros folíolos.",
                "quimica": "Solo: Azoxistrobina/Tiametoxam. Foliar: Ciromazina (Minadora)."
            },
            "Estolonização (Vegetativo)": {
                "desc": "Crescimento de hastes laterais e emissão de estolões.",
                "fisiologia": "Alta demanda de Nitrogênio para expansão foliar (IAF).",
                "manejo": "Realizar a Amontoa. Não atrasar para não cortar raízes.",
                "quimica": "Preventivo: Clorotalonil ou Mancozebe (Multissítios)."
            },
            "Início de Tuberização (Gancho)": {
                "desc": "Fase mais crítica. A ponta do estolão incha.",
                "fisiologia": "Inversão hormonal (Giberelina cai, Ácido Abscísico sobe). Estresse hídrico causa abortamento ou sarna.",
                "manejo": "Irrigação frequente e leve. Controle absoluto de Requeima.",
                "quimica": "Curativo: Metalaxil-M, Dimetomorfe, Cimoxanil."
            },
            "Enchimento de Tubérculos": {
                "desc": "Translocação de fotoassimilados.",
                "fisiologia": "Dreno forte. Potássio e Magnésio são vitais. Excesso de N 'aboa' a planta.",
                "manejo": "Monitorar Mosca Branca e Traça.",
                "quimica": "Traça: Clorantraniliprole. Mosca: Espirotesifeno."
            },
            "Maturação/Senescência": {
                "desc": "Amarelecimento natural.",
                "fisiologia": "Formação da pele (suberização).",
                "manejo": "Suspender N. Dessecação.",
                "quimica": "Dessecante: Diquat."
            }
        }
    },
    "Café (Coffea arabica)": {
        "t_base": 10,
        "vars": {
            "Catuaí": {"kc": 1.1, "info": "Padrão de qualidade. Susceptível a ferrugem."},
            "Arara": {"kc": 1.2, "info": "Resistente a ferrugem, produtivo."}
        },
        "fases": {
            "Dormência/Poda": {
                "desc": "Período seco/frio. Metabolismo lento.",
                "fisiologia": "Indução floral latente.",
                "manejo": "Poda de produção e esqueletamento.",
                "quimica": "Cobre (Bacteriose/Phoma)."
            },
            "Florada Principal": {
                "desc": "Abertura das flores (Antese).",
                "fisiologia": "Alta demanda de Boro para tubo polínico.",
                "manejo": "Não aplicar inseticidas agressivos (proteger polinizadores).",
                "quimica": "Foliar: Cálcio + Boro + Zinco."
            },
            "Chumbinho (Expansão)": {
                "desc": "Fruto pequeno, intensa divisão celular.",
                "fisiologia": "Fase onde se define o tamanho da peneira. Déficit hídrico é irreversível.",
                "manejo": "Controle de Cercospora e Ferrugem.",
                "quimica": "Priori Xtra (Ciproconazol + Azoxistrobina)."
            },
            "Granação (Enchimento)": {
                "desc": "Solidificação do endosperma.",
                "fisiologia": "Dreno de reservas das folhas para o grão (risco de Die-back/Escaldadura).",
                "manejo": "Monitorar Broca do Café.",
                "quimica": "Broca: Ciantraniliprole (Benévia)."
            }
        }
    },
    "Mirtilo (Vaccinium spp.)": {
        "t_base": 7,
        "vars": {
            "Emerald": {"kc": 0.95, "info": "Vigorosa. pH ácido (4.5-5.5)."},
            "Biloxi": {"kc": 0.90, "info": "Ereta. Poda de limpeza central."}
        },
        "fases": {
            "Brotação/Dormência": {
                "desc": "Início do fluxo de seiva.",
                "fisiologia": "Mobilização de reservas de raiz.",
                "manejo": "Controle de Cochonilha de carapaça.",
                "quimica": "Óleo Mineral + Imidacloprido."
            },
            "Florada": {
                "desc": "Abertura floral.",
                "fisiologia": "Polinização cruzada define tamanho do fruto.",
                "manejo": "Introdução de abelhas (Bombus).",
                "quimica": "Botrytis: Fludioxonil (Noite)."
            },
            "Crescimento de Fruto": {
                "desc": "Fase verde.",
                "fisiologia": "Divisão celular. Evitar Nitrato (Usar Amônio).",
                "manejo": "Monitorar Antracnose (Glomerella).",
                "quimica": "Azoxistrobina."
            },
            "Maturação/Colheita": {
                "desc": "Mudança de cor (Véraison).",
                "fisiologia": "Acúmulo de açúcar. Pele sensível.",
                "manejo": "Colheita frequente.",
                "quimica": "Não aplicar produtos com carência longa."
            }
        }
    },
    "Morango": {
        "t_base": 7,
        "vars": {"San Andreas": {"kc": 0.85, "info": "Dia Neutro."}, "Albion": {"kc": 0.85, "info": "Qualidade."}},
        "fases": {
            "Plantio/Enraizamento": {
                "desc": "Estabelecimento de mudas.",
                "fisiologia": "Emissão de raízes novas.",
                "manejo": "Imersão de mudas em fungicida.",
                "quimica": "Fosfito de Potássio (Enraizamento)."
            },
            "Desenvolvimento de Coroa": {
                "desc": "Fase vegetativa antes da flor.",
                "fisiologia": "Acúmulo de reservas na coroa.",
                "manejo": "Retirada de estolões. Limpeza sanitária.",
                "quimica": "Oídio: Enxofre. Ácaro: Abamectina."
            },
            "Florada/Frutificação": {
                "desc": "Produção contínua.",
                "fisiologia": "Alta demanda de K e Ca.",
                "manejo": "Fertirrigação diária.",
                "quimica": "Botrytis: Ciprodinil."
            }
        }
    }
}

# --- 3. SISTEMA DE PERSISTÊNCIA (LINK MÁGICO) ---
def get_credentials():
    # Tenta pegar da URL primeiro
    params = st.query_params
    url_weather = params.get("w_key", None)
    url_gemini = params.get("g_key", None)
    return url_weather, url_gemini

# --- 4. CÁLCULOS CIENTÍFICOS ---
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
            t_max = item['main']['temp_max']
            t_min = item['main']['temp_min']
            t_media = item['main']['temp']
            
            # CÁLCULO GDA REAL (Graus Dia)
            gda_dia = max(0, t_media - t_base)
            
            dt, vpd = calc_agro(t_media, item['main']['humidity'])
            chuva = sum([r['list'][i+j].get('rain', {}).get('3h', 0) for j in range(8) if i+j < len(r['list'])])
            et0 = 0.0023 * (t_media + 17.8) * (t_media ** 0.5) * 0.408
            
            dados.append({
                'Data': datetime.fromtimestamp(item['dt']).strftime('%d/%m'),
                'Temp': t_media,
                'GDA': gda_dia,
                'Chuva': round(chuva, 1),
                'VPD': vpd,
                'Delta T': dt,
                'Umid': item['main']['humidity'],
                'ETc': round(et0 * kc, 2)
            })
        return pd.DataFrame(dados)
    except: return pd.DataFrame()

# --- 5. SIDEBAR (CONFIGURAÇÃO) ---
url_w, url_g = get_credentials()

with st.sidebar:
    st.header("⚙️ Configuração")
    
    # Sistema de Login Persistente
    with st.expander("🔑 Acesso (Salvar Link)", expanded=not url_w):
        val_w = st.text_input("OpenWeather Key", value=url_w if url_w else "", type="password")
        val_g = st.text_input("Gemini AI Key", value=url_g if url_g else "", type="password")
        
        if st.button("🔗 Gerar Link de Acesso Rápido"):
            st.query_params["w_key"] = val_w
            st.query_params["g_key"] = val_g
            st.success("Link atualizado! Salve esta página nos favoritos.")
            st.rerun()

    st.divider()
    cultura_sel = st.selectbox("Cultura:", list(BANCO_MASTER.keys()))
    var_sel = st.selectbox("Cultivar:", list(BANCO_MASTER[cultura_sel]['vars'].keys()))
    
    # Fases Específicas da Cultura
    fases_crop = BANCO_MASTER[cultura_sel]['fases']
    fase_sel = st.selectbox("Estágio Atual:", list(fases_crop.keys()))
    
    if 'd_plantio' not in st.session_state: st.session_state['d_plantio'] = date(2025, 11, 25)
    d_plantio = st.date_input("Data Início:", st.session_state['d_plantio'])
    dias = (date.today() - d_plantio).days
    
    info_v = BANCO_MASTER[cultura_sel]['vars'][var_sel]
    st.info(f"🧬 **{var_sel}** | Idade: {dias} dias")

# --- 6. DASHBOARD ---
st.title("🛰️ Agro-Intel Sênior v12.0")

if val_w:
    lat, lon = "-13.414", "-41.285"
    t_base_crop = BANCO_MASTER[cultura_sel]['t_base']
    df = get_forecast_detailed(val_w, lat, lon, info_v['kc'], t_base_crop)
    
    if not df.empty:
        hoje = df.iloc[0]
        gda_acum_semana = df['GDA'].sum()
        
        # CABEÇALHO
        st.markdown(f"""
        <div class="header-box">
            <h2>{cultura_sel} - {var_sel}</h2>
            <p>Fase: <b>{fase_sel}</b> | GDA Acumulado (7d): <b>{gda_acum_semana:.0f} GDA</b> (Base {t_base_crop}°C)</p>
        </div>
        """, unsafe_allow_html=True)
        
        # KPIS
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("🌡️ Temperatura", f"{hoje['Temp']:.1f}°C", f"Umid: {hoje['Umid']}%")
        c2.metric("💧 VPD (Transpiração)", f"{hoje['VPD']} kPa", "Ideal" if 0.4 <= hoje['VPD'] <= 1.3 else "Alerta")
        c3.metric("💦 Consumo (ETc)", f"{hoje['ETc']} mm", f"Kc: {info_v['kc']}")
        c4.metric("🛡️ Delta T (Gota)", f"{hoje['Delta T']}°C", "Ok" if 2 <= hoje['Delta T'] <= 8 else "Ruim")

        # ABAS
        tabs = st.tabs(["🎓 Consultoria Técnica", "📊 Clima & Hídrico", "👁️ IA Vision", "💰 Gestão"])

        # ABA 1: CONSULTORIA PROFUNDA (SEM IMAGENS, SÓ CIÊNCIA)
        with tabs[0]:
            dados_fase = fases_crop[fase_sel]
            
            # Matriz Climática de Decisão
            risco = "Baixo"
            msg_clima = "Clima favorável. Use **Protetores/Multissítios** para baixo custo."
            estilo_alerta = "alert-low"
            
            if hoje['Umid'] > 85 or hoje['Chuva'] > 2:
                risco = "ALTO"
                msg_clima = "🚨 **ALERTA DE UMIDADE:** Alta pressão de infecção. Suspenda protetores. Use **SISTÊMICOS/PENETRANTES**."
                estilo_alerta = "alert-high"
            
            c_esq, c_dir = st.columns([1, 1])
            
            with c_esq:
                st.markdown(f"""
                <div class="tech-card">
                    <div class="tech-title">🧬 Fisiologia da Fase</div>
                    <p><b>O que acontece na planta:</b> {dados_fase['desc']}</p>
                    <p><b>Fisiologia Interna:</b> {dados_fase['fisiologia']}</p>
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown(f"""
                <div class="{estilo_alerta}">
                    <strong>☁️ Matriz Climática de Hoje</strong><br>
                    {msg_clima}
                </div>
                """, unsafe_allow_html=True)

            with c_dir:
                st.markdown(f"""
                <div class="tech-card">
                    <div class="tech-title">🛠️ Plano de Ação</div>
                    <p><b>Manejo Cultural:</b> {dados_fase['manejo']}</p>
                    <hr>
                    <div class="tech-title">🧪 Prescrição Química</div>
                    <p>{dados_fase['quimica']}</p>
                </div>
                """, unsafe_allow_html=True)

        # ABA 2: CLIMA
        with tabs[1]:
            fig = go.Figure()
            fig.add_trace(go.Bar(x=df['Data'], y=df['Chuva'], name='Chuva', marker_color='#3b82f6'))
            fig.add_trace(go.Scatter(x=df['Data'], y=df['ETc'], name='ETc', line=dict(color='#ef4444', width=2)))
            st.plotly_chart(fig, use_container_width=True)
            st.info(f"Balanço Hídrico Semanal: {df['Chuva'].sum() - df['ETc'].sum():.1f} mm")

        # ABA 3: IA
        with tabs[2]:
            st.write("Diagnóstico Fitopatológico (Gemini 1.5 Pro)")
            img = st.camera_input("Foto da Folha")
            if img and val_g:
                st.image(img, width=200)
                genai.configure(api_key=val_g)
                model = genai.GenerativeModel('gemini-1.5-flash')
                with st.spinner("Analisando..."):
                    res = model.generate_content([f"Agrônomo. Analise {cultura_sel}. Contexto: Fase {fase_sel}, Umidade {hoje['Umid']}%. Identifique praga/doença e tratamento.", Image.open(img)])
                    st.success(res.text)

        # ABA 4: FINANCEIRO
        with tabs[3]:
            if 'custos' not in st.session_state: st.session_state['custos'] = []
            c1, c2 = st.columns(2)
            i = c1.text_input("Item"); v = c2.number_input("Valor R$")
            if c2.button("Lançar"): st.session_state['custos'].append({"Item": i, "Valor": v})
            if st.session_state['custos']: 
                st.dataframe(pd.DataFrame(st.session_state['custos']))
                st.metric("Total", f"R$ {pd.DataFrame(st.session_state['custos'])['Valor'].sum()}")

else:
    st.warning("⚠️ Configure suas chaves no menu lateral e clique em 'Gerar Link'.")
