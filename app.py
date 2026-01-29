import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
import math
import google.generativeai as genai
from PIL import Image
from datetime import datetime, date

# --- 1. CONFIGURAÇÃO VISUAL ---
st.set_page_config(
    page_title="Agro-Intel Omni",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main { background-color: #f0f2f6; }
    div[data-testid="metric-container"] { background-color: #fff; border: 1px solid #d1d5db; padding: 12px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .header-box { background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%); color: white; padding: 25px; border-radius: 12px; margin-bottom: 25px; }
    .protocolo-box { background-color: #ecfdf5; border-left: 5px solid #059669; padding: 15px; border-radius: 6px; margin-bottom: 10px; }
    .quimica-box { background-color: #fef2f2; border-left: 5px solid #dc2626; padding: 15px; border-radius: 6px; margin-bottom: 10px; }
    h3 { color: #1e3a8a; margin-top: 0; }
</style>
""", unsafe_allow_html=True)

# --- 2. BANCO DE DADOS AGRONÔMICO TOTAL (CHAPADA DIAMANTINA) ---
BANCO_MASTER = {
    "Batata": {
        "vars": {
            "Orchestra": {"kc": 1.15, "alerta": "Alta exigência de K. Sensível a Pinta Preta."},
            "Cupido": {"kc": 1.10, "alerta": "Ciclo Curto. Altíssima sensibilidade a Requeima."},
            "Camila": {"kc": 1.15, "alerta": "Pele sensível. Cuidado com Sarna."},
            "Atlantic": {"kc": 1.15, "alerta": "Chips. Evitar estresse hídrico (Coração Oco)."}
        },
        "fases": {
            "Vegetativo": {
                "manejo": "Amontoa para proteger estolões. Monitorar Vaquinha/Minadora.",
                "alvos": "Larva Minadora, Rizoctonia.",
                "moleculas": "Abamectina, Tiametoxam (Solo), Azoxistrobina."
            },
            "Tuberização": {
                "manejo": "Fase Crítica! Água constante. Início preventivo forte.",
                "alvos": "Requeima (Phytophthora), Pinta Preta.",
                "moleculas": "Mancozeb (Preventivo), Metalaxil-M/Dimetomorfe (Curativo)."
            },
            "Enchimento": {
                "manejo": "Aporte alto de Potássio. Monitorar Mosca Branca.",
                "alvos": "Mosca Branca, Traça.",
                "moleculas": "Ciantraniliprole (Mosca), Espinosade (Traça)."
            },
            "Maturação": {
                "manejo": "Dessecação. Cuidado com danos na colheita.",
                "alvos": "Sarna, Podridão Mole.",
                "moleculas": "Diquat (Dessecação). Evitar excesso de umidade."
            }
        }
    },
    "Café (Arábica)": {
        "vars": {
            "Catuaí": {"kc": 1.1, "alerta": "Susceptível a Ferrugem e Broca."},
            "Arara": {"kc": 1.2, "alerta": "Resistente a Ferrugem, mas olho na Cercospora."}
        },
        "fases": {
            "Vegetativo": {
                "manejo": "Adubação nitrogenada para enfolhamento.",
                "alvos": "Bicho Mineiro.",
                "moleculas": "Clorantraniliprole, Tiametoxam."
            },
            "Florada": {
                "manejo": "Pulverização com Boro e Zinco para pegamento.",
                "alvos": "Phoma, Mancha de Aureolada.",
                "moleculas": "Boscalida, Piraclostrobina."
            },
            "Chumbinho": {
                "manejo": "Início da expansão. Água crítica.",
                "alvos": "Cercospora, Ferrugem.",
                "moleculas": "Ciproconazol + Azoxistrobina (Via solo ou foliar)."
            },
            "Granação": {
                "manejo": "Enchimento. Monitorar Broca do Café.",
                "alvos": "Broca do Café.",
                "moleculas": "Ciantraniliprole (Broca)."
            }
        }
    },
    "Tomate": {
        "vars": {
            "Italiano (Saladete)": {"kc": 1.2, "alerta": "Fundo Preto (Deficiência de Ca)."},
            "Grape (Cereja)": {"kc": 1.1, "alerta": "Rachadura de frutos se oscilar água."}
        },
        "fases": {
            "Vegetativo": {
                "manejo": "Desbrota lateral. Condução.",
                "alvos": "Mosca Branca, Tripes (Vira-Cabeça).",
                "moleculas": "Acetamiprido, Espinetoram."
            },
            "Florada": {
                "manejo": "Cálcio Foliar obrigatório.",
                "alvos": "Botrytis, Oídio.",
                "moleculas": "Mancozeb, Tebuconazol."
            },
            "Frutificação": {
                "manejo": "Monitorar Tuta absoluta (Traça).",
                "alvos": "Traça do Tomateiro, Requeima.",
                "moleculas": "Clorfenapir (Traça), Mandipropamida (Requeima)."
            }
        }
    },
    "Mirtilo": {
        "vars": {
            "Emerald": {"kc": 0.95, "alerta": "pH ácido (4.5-5.5). Vigorosa."},
            "Biloxi": {"kc": 0.90, "alerta": "Poda de limpeza central."}
        },
        "fases": {
            "Brotação": {
                "manejo": "Estimular raiz. Monitorar Cochonilha.",
                "alvos": "Cochonilhas.",
                "moleculas": "Óleo Mineral + Imidacloprido."
            },
            "Florada": {
                "manejo": "Polinizadores (Abelhas). Cuidado com químicos.",
                "alvos": "Botrytis.",
                "moleculas": "Fludioxonil (Noite)."
            },
            "Frutificação": {
                "manejo": "Adubação sem Nitratos (Use Amônio).",
                "alvos": "Antracnose.",
                "moleculas": "Azoxistrobina."
            }
        }
    },
    "Amora Preta": {
        "vars": {
            "Tupy": {"kc": 1.0, "alerta": "Tradicional. Exige frio ou quebra de dormência."},
            "BRS Xingu": {"kc": 1.05, "alerta": "Sem espinhos. Exige tutoramento."}
        },
        "fases": {
            "Brotação": {
                "manejo": "Seleção de hastes produtivas.",
                "alvos": "Ferrugem da Amora.",
                "moleculas": "Tebuconazol."
            },
            "Frutificação": {
                "manejo": "Monitorar Drosófila (mosca da fruta).",
                "alvos": "Drosófila de Asa Manchada.",
                "moleculas": "Espinosade (Isca tóxica)."
            }
        }
    },
    "Framboesa": {
        "vars": {
            "Heritage": {"kc": 1.1, "alerta": "Remontante (Produz na ponta e base)."},
            "Golden Bliss": {"kc": 1.05, "alerta": "Fruto amarelo. Delicado."}
        },
        "fases": {
            "Brotação": {
                "manejo": "Poda de limpeza. Evitar adensamento.",
                "alvos": "Ácaro Vermelho.",
                "moleculas": "Abamectina."
            },
            "Florada/Fruto": {
                "manejo": "Colheita diária. Fruto perecível.",
                "alvos": "Botrytis, Podridão de Frutos.",
                "moleculas": "Iprodiona (Respeitar carência)."
            }
        }
    },
    "Morango": {
        "vars": {
            "San Andreas": {"kc": 0.85, "alerta": "Sensível a Ácaros."},
            "Albion": {"kc": 0.85, "alerta": "Sensível a Oídio."}
        },
        "fases": {
            "Vegetativo": {
                "manejo": "Retirada de estolões.",
                "alvos": "Oídio, Pulgão.",
                "moleculas": "Enxofre, Acetamiprido."
            },
            "Frutificação": {
                "manejo": "Cálcio/Boro. Colheita.",
                "alvos": "Ácaro Rajado, Botrytis.",
                "moleculas": "Etoxazol (Ácaro), Ciprodinil (Botrytis)."
            }
        }
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

def analise_ia_gemini(api_key, imagem, cultura, contexto):
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"""
        Você é um Engenheiro Agrônomo Sênior (Fitopatologista).
        Analise esta imagem de {cultura}.
        Contexto atual: {contexto}.
        1. Identifique a praga, doença ou deficiência.
        2. Indique o Ingrediente Ativo (químico) mais eficiente.
        3. Indique uma solução biológica/orgânica.
        Seja técnico.
        """
        response = model.generate_content([prompt, imagem])
        return response.text
    except Exception as e: return f"Erro IA: {e}"

# --- 4. SIDEBAR ---
with st.sidebar:
    st.header("🎛️ Centro de Comando")
    with st.expander("🔑 Credenciais (APIs)", expanded=True):
        weather_key = st.text_input("OpenWeather Key", type="password")
        gemini_key = st.text_input("Gemini AI Key", type="password")
    
    st.divider()
    cultura_sel = st.selectbox("Cultura:", list(BANCO_MASTER.keys()))
    vars_disponiveis = BANCO_MASTER[cultura_sel]['vars']
    var_sel = st.selectbox("Variedade:", list(vars_disponiveis.keys()))
    
    # Tratamento seguro para fases
    fases_disponiveis = BANCO_MASTER[cultura_sel]['fases']
    lista_fases = list(fases_disponiveis.keys())
    fase_sel = st.selectbox("Fase Fenológica:", lista_fases, index=min(1, len(lista_fases)-1))
    
    if 'data_plantio' not in st.session_state: st.session_state['data_plantio'] = date(2025, 11, 25)
    d_plantio = st.date_input("Data Início:", st.session_state['data_plantio'])
    dias_campo = (date.today() - d_plantio).days
    
    info_var = vars_disponiveis[var_sel]
    st.info(f"🧬 **{var_sel}** | Dias: {dias_campo} | Kc: {info_var['kc']}")

# --- 5. DASHBOARD ---
st.title("🛰️ Agro-Intel Omni v9.0")

if weather_key:
    st.markdown(f"""
    <div class="header-box">
        <h2 style="margin:0; color:white;">🚜 {cultura_sel} - {var_sel}</h2>
        <p style="margin:0; opacity:0.9;">Fase: {fase_sel} | 🧬 Ponto Crítico: {info_var['alerta']}</p>
    </div>
    """, unsafe_allow_html=True)

    lat, lon = "-13.414", "-41.285" # Ibicoara
    df = get_forecast(weather_key, lat, lon, info_var['kc'])
    
    if not df.empty:
        hoje = df.iloc[0]
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("🌡️ Temperatura", f"{hoje['Temp']}°C", f"Umid: {hoje['Umid']}%")
        c2.metric("💧 VPD", f"{hoje['VPD']} kPa", "Risco" if hoje['VPD'] > 1.3 else "Ideal")
        c3.metric("💦 ETc (Consumo)", f"{hoje['ETc']} mm", f"Kc: {info_var['kc']}")
        c4.metric("🛡️ Delta T", f"{hoje['Delta T']}°C", "Ok" if 2 <= hoje['Delta T'] <= 8 else "Ruim")

        tab_tec, tab_clima, tab_ia, tab_fin, tab_gps = st.tabs(["📚 Protocolo Técnico", "📊 Clima", "👁️ IA Vision", "💰 Financeiro", "📡 GPS"])

        # --- ABA 1: PROTOCOLO TÉCNICO COMPLETO ---
        with tab_tec:
            dados_fase = fases_disponiveis[fase_sel]
            
            # Inteligência Climática
            risco_txt = "Baixo"
            recomendacao_clima = "✅ Clima seco. Use Protetores (Contato)."
            if hoje['Umid'] > 85 or hoje['Chuva'] > 2:
                risco_txt = "ALTO"
                recomendacao_clima = "⚠️ **ALERTA DE UMIDADE:** Alta pressão de fungos. Use **SISTÊMICOS**."

            c_tec1, c_tec2 = st.columns(2)
            
            with c_tec1:
                st.markdown(f"""
                <div class="protocolo-box">
                    <h4>🛠️ Manejo Cultural ({fase_sel})</h4>
                    <p>{dados_fase['manejo']}</p>
                </div>
                """, unsafe_allow_html=True)
                st.info(f"**Status Climático:** {recomendacao_clima}")

            with c_tec2:
                st.markdown(f"""
                <div class="quimica-box">
                    <h4>🧪 Farmácia Digital</h4>
                    <p><b>Alvos:</b> {dados_fase['alvos']}</p>
                    <hr>
                    <p>{dados_fase['moleculas']}</p>
                </div>
                """, unsafe_allow_html=True)

        # --- ABA 2: CLIMA ---
        with tab_clima:
            fig = go.Figure()
            fig.add_trace(go.Bar(x=df['Data'], y=df['Chuva'], name='Chuva', marker_color='#29b6f6'))
            fig.add_trace(go.Scatter(x=df['Data'], y=df['ETc'], name='Consumo (ETc)', line=dict(color='#ef5350', width=2)))
            fig.update_layout(title="Balanço Hídrico Semanal", height=350)
            st.plotly_chart(fig, use_container_width=True)
            st.info(f"Balanço: {df['Chuva'].sum() - df['ETc'].sum():.1f} mm.")

        # --- ABA 3: IA VISION ---
        with tab_ia:
            st.write("Diagnóstico por Imagem (Gemini)")
            img = st.camera_input("📸 Foto")
            if not img: img = st.file_uploader("Upload", type=['jpg', 'png'])
            if img and gemini_key:
                st.image(img, width=200)
                ctx = f"Cultura: {cultura_sel}. Fase: {fase_sel}. Umidade: {hoje['Umid']}%."
                with st.spinner("Analisando..."):
                    st.success(analise_ia_gemini(gemini_key, Image.open(img), cultura_sel, ctx))

        # --- ABA 4: FINANCEIRO ---
        with tab_fin:
            if 'custos' not in st.session_state: st.session_state['custos'] = []
            c_f1, c_f2 = st.columns(2)
            item = c_f1.text_input("Item")
            valor = c_f2.number_input("Valor (R$)", min_value=0.0)
            if st.button("Lançar"):
                st.session_state['custos'].append({"Item": item, "Valor": valor})
                st.success("Salvo!")
            if st.session_state['custos']:
                df_f = pd.DataFrame(st.session_state['custos'])
                st.dataframe(df_f, use_container_width=True)
                st.metric("Total", f"R$ {df_f['Valor'].sum():,.2f}")

        # --- ABA 5: GPS ---
        with tab_gps:
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
    st.warning("👈 Insira a Chave OpenWeather para iniciar.")
