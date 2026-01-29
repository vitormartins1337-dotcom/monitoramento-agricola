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
    page_title="Agro-Intel Visual v10",
    page_icon="📸",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main { background-color: #f4f6f9; }
    div[data-testid="metric-container"] { background-color: #fff; border: 1px solid #e0e0e0; padding: 12px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .header-box { background: linear-gradient(to right, #283c86, #45a247); color: white; padding: 20px; border-radius: 12px; margin-bottom: 25px; }
    .protocolo-box { background-color: #e8f5e9; border-left: 5px solid #2e7d32; padding: 15px; border-radius: 8px; margin-bottom: 15px; }
    .quimica-box { background-color: #fff5f5; border-left: 5px solid #c62828; padding: 15px; border-radius: 8px; margin-bottom: 15px; }
    h3 { margin-top: 0; color: #283c86; }
    .img-caption { font-size: 0.8em; color: #666; text-align: center; }
</style>
""", unsafe_allow_html=True)

# --- 2. BANCO DE DADOS AGRONÔMICO VISUAL (CÉREBRO V10) ---
# Nota: Usando URLs públicas para demonstração. Para produção, hospede no GitHub.
BANCO_MASTER = {
    "Batata": {
        "vars": {
            "Orchestra": {"kc": 1.15, "alerta": "Alta exigência K. Pinta Preta."},
            "Cupido": {"kc": 1.10, "alerta": "Ciclo Curto. Requeima Severa."},
            "Camila": {"kc": 1.15, "alerta": "Pele sensível. Sarna."},
            "Atlantic": {"kc": 1.15, "alerta": "Chips. Coração Oco."}
        },
        "fases": {
            "Vegetativo": {
                "manejo": "Amontoa bem feita. Proteger estolões.",
                "imgs": [{"nome": "Larva Minadora", "src": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e3/Liriomyza_sativae_larva.jpg/320px-Liriomyza_sativae_larva.jpg"}, {"nome": "Rizoctonia (Cancro)", "src": "https://ars.els-cdn.com/content/image/3-s2.0-B9780128022344000097-f09-17-9780128022344.jpg?missing_image=http%3A%2F%2Fcdn.els-cdn.com%2Fsd%2Fmissing_image%2Fmissing_image.png"}],
                "moleculas": "Abamectina (Minadora), Azoxistrobina (Solo)."
            },
            "Tuberização": {
                "manejo": "Fase Crítica! Água constante. Preventivo forte.",
                "imgs": [{"nome": "Requeima (Phytophthora)", "src": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3a/Potato_late_blight_foliage.jpg/320px-Potato_late_blight_foliage.jpg"}, {"nome": "Pinta Preta (Alternaria)", "src": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/2c/Alternaria_solani_02.jpg/320px-Alternaria_solani_02.jpg"}],
                "moleculas": "**Preventivo:** Mancozeb.\n**Curativo:** Metalaxil-M, Dimetomorfe."
            },
            "Enchimento": {
                "manejo": "Aporte alto de K. Monitorar Mosca Branca.",
                "imgs": [{"nome": "Mosca Branca", "src": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a3/Bemisia_tabaci_on_Poinsettia_leaf.jpg/320px-Bemisia_tabaci_on_Poinsettia_leaf.jpg"}, {"nome": "Traça da Batata", "src": "https://live.staticflickr.com/65535/49926640946_f477002316_n.jpg"}],
                "moleculas": "Ciantraniliprole (Mosca), Espinosade (Traça)."
            },
            "Maturação": {
                "manejo": "Dessecação. Cuidado com danos.",
                "imgs": [{"nome": "Sarna Comum", "src": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/12/Potato_scab_1.jpg/320px-Potato_scab_1.jpg"}],
                "moleculas": "Diquat (Dessecação). Evitar excesso de umidade."
            }
        }
    },
    "Café (Arábica)": {
        "vars": {"Catuaí": {"kc": 1.1, "alerta": "Ferrugem."}, "Arara": {"kc": 1.2, "alerta": "Cercospora."}},
        "fases": {
            "Vegetativo": {
                "manejo": "Adubação nitrogenada. Monitorar Bicho Mineiro.",
                "imgs": [{"nome": "Bicho Mineiro", "src": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/ef/Leucoptera_coffeella_damage.jpg/320px-Leucoptera_coffeella_damage.jpg"}],
                "moleculas": "Clorantraniliprole, Tiametoxam."
            },
            "Florada": {
                "manejo": "Pulverização Boro/Zinco. Atenção a Phoma.",
                "imgs": [{"nome": "Phoma/Mancha de Aureolada", "src": "https://www.agrolink.com.br/upload/problemas/Phoma_costarricensis74.jpg"}],
                "moleculas": "Boscalida, Piraclostrobina."
            },
            "Chumbinho": {
                "manejo": "Expansão. Água crítica.",
                "imgs": [{"nome": "Ferrugem do Cafeeiro", "src": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5e/Hemileia_vastatrix_on_coffee_leaf.jpg/320px-Hemileia_vastatrix_on_coffee_leaf.jpg"}, {"nome": "Cercospora", "src": "https://www.agrolink.com.br/upload/problemas/Cercospora_coffeicola88.jpg"}],
                "moleculas": "Ciproconazol + Azoxistrobina."
            },
            "Granação": {
                "manejo": "Enchimento. Monitorar Broca.",
                "imgs": [{"nome": "Broca do Café", "src": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a8/Hypothenemus_hampei_Ferrari.jpg/320px-Hypothenemus_hampei_Ferrari.jpg"}],
                "moleculas": "Ciantraniliprole (Broca)."
            }
        }
    },
    "Tomate": {
        "vars": {"Italiano": {"kc": 1.2, "alerta": "Fundo Preto (Ca)."}, "Grape": {"kc": 1.1, "alerta": "Rachadura."}},
        "fases": {
            "Vegetativo": {
                "manejo": "Desbrota. Monitorar vetores de virose.",
                "imgs": [{"nome": "Tripes (Vetor Vira-Cabeça)", "src": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/22/Thrips_on_leaf.jpg/320px-Thrips_on_leaf.jpg"}, {"nome": "Mosca Branca", "src": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a3/Bemisia_tabaci_on_Poinsettia_leaf.jpg/320px-Bemisia_tabaci_on_Poinsettia_leaf.jpg"}],
                "moleculas": "Acetamiprido, Espinetoram."
            },
            "Florada": {
                "manejo": "Cálcio Foliar obrigatório.",
                "imgs": [{"nome": "Fundo Preto (Def. Cálcio)", "src": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a9/Blossom_end_rot_on_roma_tomatoes.jpg/320px-Blossom_end_rot_on_roma_tomatoes.jpg"}],
                "moleculas": "Cálcio Quelatado. Tebuconazol (Pinta)."
            },
            "Frutificação": {
                "manejo": "Monitorar Tuta absoluta.",
                "imgs": [{"nome": "Traça (Tuta absoluta)", "src": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e4/Tuta_absoluta_damage_on_tomato.jpg/320px-Tuta_absoluta_damage_on_tomato.jpg"}, {"nome": "Requeima", "src": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/73/Phytophthora_infestans_tomato.jpg/320px-Phytophthora_infestans_tomato.jpg"}],
                "moleculas": "Clorfenapir (Traça), Mandipropamida (Requeima)."
            }
        }
    },
    "Mirtilo": {
        "vars": {"Emerald": {"kc": 0.95, "alerta": "pH ácido."}, "Biloxi": {"kc": 0.90, "alerta": "Poda de limpeza."}},
        "fases": {
            "Brotação": {"manejo": "Estimular raiz.", "imgs": [{"nome": "Cochonilha", "src": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/86/Mealybug_on_hibiscus_plant.jpg/320px-Mealybug_on_hibiscus_plant.jpg"}], "moleculas": "Óleo Mineral."},
            "Florada": {"manejo": "Polinizadores.", "imgs": [{"nome": "Botrytis (Mofo)", "src": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/9d/Botrytis_cinerea_on_grapes.jpg/320px-Botrytis_cinerea_on_grapes.jpg"}], "moleculas": "Fludioxonil (Noite)."},
            "Frutificação": {"manejo": "Adubação Amoniacal.", "imgs": [{"nome": "Antracnose", "src": "https://www.agrolink.com.br/upload/problemas/Colletotrichum_gloeosporioides113.jpg"}], "moleculas": "Azoxistrobina."}
        }
    },
    "Amora Preta": {
        "vars": {"Tupy": {"kc": 1.0, "alerta": "Tradicional."}, "BRS Xingu": {"kc": 1.05, "alerta": "Sem espinhos."}},
        "fases": {
            "Brotação": {"manejo": "Seleção de hastes.", "imgs": [{"nome": "Ferrugem", "src": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/08/Phragmidium_violaceum01.jpg/320px-Phragmidium_violaceum01.jpg"}], "moleculas": "Tebuconazol."},
            "Frutificação": {"manejo": "Monitorar Mosca.", "imgs": [{"nome": "Drosófila (SWD)", "src": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/33/Drosophila_suzukii_male_top.jpg/320px-Drosophila_suzukii_male_top.jpg"}], "moleculas": "Espinosade (Isca)."}
        }
    },
    "Framboesa": {
        "vars": {"Heritage": {"kc": 1.1, "alerta": "Remontante."}, "Golden Bliss": {"kc": 1.05, "alerta": "Fruto amarelo."}},
        "fases": {
            "Brotação": {"manejo": "Poda de limpeza.", "imgs": [{"nome": "Ácaro Vermelho", "src": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/37/Tetranychus_urticae.jpg/320px-Tetranychus_urticae.jpg"}], "moleculas": "Abamectina."},
            "Florada/Fruto": {"manejo": "Colheita diária.", "imgs": [{"nome": "Podridão", "src": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/9d/Botrytis_cinerea_on_grapes.jpg/320px-Botrytis_cinerea_on_grapes.jpg"}], "moleculas": "Iprodiona."}
        }
    },
    "Morango": {
        "vars": {"San Andreas": {"kc": 0.85, "alerta": "Sensível a Ácaros."}, "Albion": {"kc": 0.85, "alerta": "Sensível a Oídio."}},
        "fases": {
            "Vegetativo": {"manejo": "Limpeza.", "imgs": [{"nome": "Oídio", "src": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/18/Erysiphe_necator_on_grapes.jpg/320px-Erysiphe_necator_on_grapes.jpg"}, {"nome": "Ácaro Rajado", "src": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/37/Tetranychus_urticae.jpg/320px-Tetranychus_urticae.jpg"}], "moleculas": "Enxofre, Abamectina."},
            "Frutificação": {"manejo": "Cálcio/Boro.", "imgs": [{"nome": "Botrytis", "src": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b3/Strawberry_Botrytis.jpg/320px-Strawberry_Botrytis.jpg"}], "moleculas": "Ciprodinil."}
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
        prompt = f"Engenheiro Agrônomo Fitopatologista. Analise imagem de {cultura}. Contexto: {contexto}. Identifique problema, indique químico (IA) e biológico. Seja direto."
        response = model.generate_content([prompt, imagem])
        return response.text
    except Exception as e: return f"Erro IA: {e}"

# --- 4. SIDEBAR ---
with st.sidebar:
    st.header("🎛️ Comando")
    with st.expander("🔑 Credenciais", expanded=True):
        weather_key = st.text_input("OpenWeather Key", type="password")
        gemini_key = st.text_input("Gemini AI Key", type="password")
    st.divider()
    cultura_sel = st.selectbox("Cultura:", list(BANCO_MASTER.keys()))
    var_sel = st.selectbox("Variedade:", list(BANCO_MASTER[cultura_sel]['vars'].keys()))
    lista_fases = list(BANCO_MASTER[cultura_sel]['fases'].keys())
    fase_sel = st.selectbox("Fase:", lista_fases, index=min(1, len(lista_fases)-1))
    if 'd_plantio' not in st.session_state: st.session_state['d_plantio'] = date(2025, 11, 25)
    d_plantio = st.date_input("Início:", st.session_state['d_plantio'])
    info_var = BANCO_MASTER[cultura_sel]['vars'][var_sel]
    st.info(f"Kc: {info_var['kc']} | Dias: {(date.today()-d_plantio).days}")

# --- 5. DASHBOARD VISUAL ---
st.title("🛰️ Agro-Intel Visual v10")
if weather_key:
    st.markdown(f"""<div class="header-box"><h3>🚜 {cultura_sel} - {var_sel} ({fase_sel})</h3><p>🚨 {info_var['alerta']}</p></div>""", unsafe_allow_html=True)
    lat, lon = "-13.414", "-41.285"
    df = get_forecast(weather_key, lat, lon, info_var['kc'])
    
    if not df.empty:
        hoje = df.iloc[0]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("🌡️ Temp", f"{hoje['Temp']}°C", f"Umid: {hoje['Umid']}%")
        c2.metric("💧 VPD", f"{hoje['VPD']} kPa", "Risco" if hoje['VPD'] > 1.3 else "Ideal")
        c3.metric("💦 ETc", f"{hoje['ETc']} mm", f"Kc: {info_var['kc']}")
        c4.metric("🛡️ Delta T", f"{hoje['Delta T']}°C", "Ok" if 2 <= hoje['Delta T'] <= 8 else "Ruim")

        tab_tec, tab_clima, tab_ia, tab_fin, tab_gps = st.tabs(["📚 Protocolo Visual", "📊 Clima", "👁️ IA Vision", "💰 Financeiro", "📡 GPS"])

        # --- ABA 1: PROTOCOLO VISUAL (O NOVO CÉREBRO) ---
        with tab_tec:
            dados_fase = BANCO_MASTER[cultura_sel]['fases'][fase_sel]
            
            risco_clima = "Baixo"
            rec_clima = "✅ Clima seco. Use Protetores (Contato)."
            if hoje['Umid'] > 85 or hoje['Chuva'] > 2:
                risco_clima = "ALTO"
                rec_clima = "⚠️ **UMIDADE ALTA:** Risco fúngico severo. Priorize **SISTÊMICOS**."

            col_man, col_quim = st.columns([1, 2])
            with col_man:
                st.markdown(f"""<div class="protocolo-box"><h4>🛠️ Manejo Cultural</h4><p>{dados_fase['manejo']}</p></div>""", unsafe_allow_html=True)
                st.info(f"**Status Climático:** {rec_clima}")
            
            with col_quim:
                st.markdown(f"""<div class="quimica-box"><h4>🧪 Farmácia Digital (Alvos da Fase)</h4></div>""", unsafe_allow_html=True)
                
                # LOOP VISUAL DE PRAGAS/DOENÇAS
                cols_imgs = st.columns(len(dados_fase['imgs']))
                for i, alvo in enumerate(dados_fase['imgs']):
                    with cols_imgs[i]:
                        st.image(alvo['src'], use_column_width=True)
                        st.caption(f"🔴 **{alvo['nome']}**")
                
                st.markdown("---")
                st.markdown(f"**💊 Moléculas Sugeridas:**\n\n{dados_fase['moleculas']}")

        # --- OUTRAS ABAS (Mantidas) ---
        with tab_clima:
            fig = go.Figure()
            fig.add_trace(go.Bar(x=df['Data'], y=df['Chuva'], name='Chuva', marker_color='#29b6f6'))
            fig.add_trace(go.Scatter(x=df['Data'], y=df['ETc'], name='ETc', line=dict(color='#ef5350', width=2)))
            st.plotly_chart(fig, use_container_width=True)
            st.info(f"Balanço: {df['Chuva'].sum() - df['ETc'].sum():.1f} mm")
        
        with tab_ia:
            img = st.camera_input("📸 Foto")
            if not img: img = st.file_uploader("Upload", type=['jpg', 'png'])
            if img and gemini_key:
                st.image(img, width=200)
                with st.spinner("Analisando..."):
                    st.success(analise_ia_gemini(gemini_key, Image.open(img), cultura_sel, f"Umidade {hoje['Umid']}%"))
        
        with tab_fin:
            if 'custos' not in st.session_state: st.session_state['custos'] = []
            c1, c2 = st.columns(2)
            i = c1.text_input("Item"); v = c2.number_input("R$");
            if st.button("Lançar"): st.session_state['custos'].append({"Item":i, "Valor":v}); st.success("Ok")
            if st.session_state['custos']: st.dataframe(pd.DataFrame(st.session_state['custos'])); st.metric("Total", f"R$ {pd.DataFrame(st.session_state['custos'])['Valor'].sum()}")

        with tab_gps:
            VIZ = [{"nome": "Mucugê", "lat": -13.005, "lon": -41.371}, {"nome": "Barra da Estiva", "lat": -13.623, "lon": -41.326}, {"nome": "Cascavel", "lat": -13.196, "lon": -41.445}]
            st.map(pd.DataFrame([{"lat": float(lat), "lon": float(lon)}] + VIZ), zoom=9)
else: st.warning("🔑 Insira a Chave API")
