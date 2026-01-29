import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
import math
import google.generativeai as genai
from PIL import Image
from datetime import datetime, date

# --- 1. CONFIGURAÇÃO VISUAL DE ALTO NÍVEL ---
st.set_page_config(
    page_title="Agro-Intel Ultimate",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS para criar interface de Software Corporativo
st.markdown("""
<style>
    .main { background-color: #f8f9fa; }
    div[data-testid="metric-container"] { background-color: #ffffff; border: 1px solid #d1d5db; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .header-box { background: linear-gradient(135deg, #1565c0 0%, #0d47a1 100%); color: white; padding: 25px; border-radius: 12px; margin-bottom: 25px; }
    .fisiologia-box { background-color: #e3f2fd; border-left: 5px solid #1565c0; padding: 20px; border-radius: 6px; margin-bottom: 15px; }
    .manejo-box { background-color: #e8f5e9; border-left: 5px solid #2e7d32; padding: 20px; border-radius: 6px; margin-bottom: 15px; }
    .alerta-box { background-color: #ffebee; border-left: 5px solid #c62828; padding: 20px; border-radius: 6px; margin-bottom: 15px; }
    .quimica-card { background-color: #fff; border: 1px solid #ddd; padding: 10px; border-radius: 8px; margin-bottom: 10px; }
    h3, h4 { color: #0d47a1; margin-top: 0; }
    .caption-text { font-size: 0.9em; color: #555; font-style: italic; }
</style>
""", unsafe_allow_html=True)

# --- 2. CÉREBRO AGRONÔMICO (TEXTOS ROBUSTOS + IMAGENS) ---
BANCO_MASTER = {
    "Batata (Solanum tuberosum)": {
        "vars": {
            "Orchestra": {"kc": 1.15, "info": "Alta exigência de K. Variedade de pele lisa, exige acabamento visual perfeito."},
            "Cupido": {"kc": 1.10, "info": "Ciclo Curto. Altíssima sensibilidade a Requeima. Requer colheita rápida após maturação."},
            "Camila": {"kc": 1.15, "info": "Referência de mercado. Cuidado extremo com Sarna e Rhizoctonia."},
            "Atlantic": {"kc": 1.15, "info": "Chips. Evitar oscilação hídrica para prevenir Coração Oco e manter Matéria Seca."}
        },
        "fases": {
            "Vegetativo": {
                "desc_tecnica": "Fase de estabelecimento do estande e desenvolvimento radicular. A planta define seu potencial produtivo agora.",
                "fisiologia": "O Nitrogênio é crucial para síntese de proteínas e expansão foliar (IAF). O Fósforo atua na energia (ATP) para enraizamento. O estresse hídrico agora reduz o número de hastes.",
                "manejo": "Realizar a **Amontoa** (Chegar terra) para proteger os estolões da luz (evita esverdeamento). Monitorar pragas de solo.",
                "imgs": [
                    {"nome": "Larva Minadora", "src": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e3/Liriomyza_sativae_larva.jpg/320px-Liriomyza_sativae_larva.jpg", "desc": "Liriomyza spp. Faz galerias nas folhas, reduzindo área fotossintética."},
                    {"nome": "Rizoctonia (Cancro)", "src": "https://ars.els-cdn.com/content/image/3-s2.0-B9780128022344000097-f09-17-9780128022344.jpg?missing_image=http%3A%2F%2Fcdn.els-cdn.com%2Fsd%2Fmissing_image%2Fmissing_image.png", "desc": "Ataca a base da haste e estolões."}
                ],
                "quimica": "**Controle Minadora:** Abamectina (Translaminar) ou Ciromazina (Regulador de crescimento).\n**Solo:** Azoxistrobina (Sistêmico) no sulco de plantio."
            },
            "Tuberização": {
                "desc_tecnica": "Início da formação dos tubérculos (Gancho). Fase mais crítica do ciclo.",
                "fisiologia": "Mudança hormonal: Queda de Giberelina e aumento de Ácido Abscísico. A planta para de crescer folha e foca no tubérculo. Qualquer estresse hídrico causa Sarna Comum e abortamento.",
                "manejo": "Irrigação frequente e leve. Início do programa preventivo de fungicidas (fechamento das linhas gera microclima úmido).",
                "imgs": [
                    {"nome": "Requeima (Phytophthora)", "src": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3a/Potato_late_blight_foliage.jpg/320px-Potato_late_blight_foliage.jpg", "desc": "O 'Cancro' da batata. Destrói a lavoura em 3 dias se chover."},
                    {"nome": "Pinta Preta (Alternaria)", "src": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/2c/Alternaria_solani_02.jpg/320px-Alternaria_solani_02.jpg", "desc": "Doença de estresse e senescência."}
                ],
                "quimica": "**Preventivo (Sem chuva):** Mancozeb ou Clorotalonil (Multissítios).\n**Curativo (Com chuva):** Metalaxil-M (Sistêmico), Dimetomorfe ou Mandipropamida (Penetrantes)."
            },
            "Enchimento": {
                "desc_tecnica": "Translocação de fotoassimilados das folhas para os tubérculos.",
                "fisiologia": "Alta demanda de **Potássio (K)** para transporte de açúcares (Floema). Magnésio é vital para manter a clorofila ativa. Excesso de Nitrogênio agora 'aboa' a batata (menos peso).",
                "manejo": "Monitorar Mosca Branca (vetor de virose) e Traça. Manter sanidade foliar até o fim.",
                "imgs": [
                    {"nome": "Mosca Branca", "src": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a3/Bemisia_tabaci_on_Poinsettia_leaf.jpg/320px-Bemisia_tabaci_on_Poinsettia_leaf.jpg", "desc": "Vetor de Geminivírus e causadora de fumagina."},
                    {"nome": "Traça da Batata", "src": "https://live.staticflickr.com/65535/49926640946_f477002316_n.jpg", "desc": "Larva fura o tubérculo."}
                ],
                "quimica": "**Mosca Branca:** Ciantraniliprole ou Espirotesifeno.\n**Traça:** Clorfenapir ou Espinosade."
            },
            "Maturação": {
                "desc_tecnica": "Senescência natural e formação da pele (suberina).",
                "fisiologia": "A pele precisa firmar para resistir à colheita. O excesso de umidade impede a cura da pele e favorece bactérias.",
                "manejo": "Suspensão da irrigação. Dessecação química da rama.",
                "imgs": [{"nome": "Sarna Comum", "src": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/12/Potato_scab_1.jpg/320px-Potato_scab_1.jpg", "desc": "Lesões corticosas na pele."}],
                "moleculas": "Diquat para dessecação rápida."
            }
        }
    },
    "Café (Coffea arabica)": {
        "vars": {"Catuaí": {"kc": 1.1, "info": "Padrão de qualidade. Susceptível a Ferrugem."}, "Arara": {"kc": 1.2, "info": "Alta produtividade e resistência a Ferrugem."}},
        "fases": {
            "Chumbinho": {
                "desc_tecnica": "Expansão rápida dos frutos. Alta demanda hídrica.",
                "fisiologia": "Divisão celular intensa no fruto. Cálcio e Boro são fundamentais para parede celular elástica (evita rachaduras).",
                "manejo": "Controle preventivo de Cercospora e Ferrugem.",
                "imgs": [{"nome": "Ferrugem", "src": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5e/Hemileia_vastatrix_on_coffee_leaf.jpg/320px-Hemileia_vastatrix_on_coffee_leaf.jpg", "desc": "Hemileia vastatrix. Causa desfolha intensa."}],
                "quimica": "**Sistêmicos:** Ciproconazol + Azoxistrobina (Via Solo ou Foliar)."
            },
            "Granação": {
                "desc_tecnica": "Enchimento de grão (Formação de massa sólida).",
                "fisiologia": "Pico de demanda de Potássio e Nitrogênio. A planta drena as reservas das folhas (Die-back se não estiver bem nutrida).",
                "manejo": "Monitoramento rigoroso da Broca do Café.",
                "imgs": [{"nome": "Broca do Café", "src": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a8/Hypothenemus_hampei_Ferrari.jpg/320px-Hypothenemus_hampei_Ferrari.jpg", "desc": "Fura o grão, depreciando qualidade."}],
                "quimica": "**Broca:** Ciantraniliprole (Benévia) ou Clorantraniliprole (Voliam)."
            }
        }
    },
    "Tomate": {
        "vars": {"Italiano": {"kc": 1.2, "info": "Saladete. Atenção Fundo Preto."}, "Grape": {"kc": 1.1, "info": "Adocicado. Atenção Rachadura."}},
        "fases": {
            "Florada": {
                "desc_tecnica": "Emissão de cachos florais e pegamento.",
                "fisiologia": "O Boro viabiliza o tubo polínico. O clima muito quente (>32°C) ou muito frio (<10°C) causa abortamento.",
                "manejo": "Aplicações semanais de Cálcio via foliar.",
                "imgs": [{"nome": "Fundo Preto", "src": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a9/Blossom_end_rot_on_roma_tomatoes.jpg/320px-Blossom_end_rot_on_roma_tomatoes.jpg", "desc": "Deficiência de Cálcio induzida por falta de água."}],
                "quimica": "Cálcio Quelatado (Aminoácido) + Boro."
            },
            "Frutificação": {
                "desc_tecnica": "Crescimento de frutos.",
                "fisiologia": "Alta demanda de K. Risco máximo de Tuta absoluta.",
                "manejo": "Alternância de princípios ativos para Traça.",
                "imgs": [{"nome": "Traça (Tuta)", "src": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e4/Tuta_absoluta_damage_on_tomato.jpg/320px-Tuta_absoluta_damage_on_tomato.jpg", "desc": "Mina as folhas e fura frutos."}],
                "quimica": "**Traça:** Clorfenapir, Espinosade, Indoxacarbe."
            }
        }
    },
    "Mirtilo": {
        "vars": {"Emerald": {"kc": 0.95, "info": "pH 4.5-5.2."}, "Biloxi": {"kc": 0.90, "info": "Poda central necessária."}},
        "fases": {
            "Brotação": {"desc_tecnica": "Emissão de folhas novas.", "fisiologia": "Reserva de Carboidratos da raiz sendo usada.", "manejo": "Monitorar Cochonilha.", "imgs": [{"nome": "Cochonilha", "src": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/86/Mealybug_on_hibiscus_plant.jpg/320px-Mealybug_on_hibiscus_plant.jpg", "desc": "Suga seiva."}], "quimica": "Óleo Mineral + Imidacloprido."},
            "Florada": {"desc_tecnica": "Abertura floral.", "fisiologia": "Polinização cruzada aumenta tamanho do fruto.", "manejo": "Colocar colmeias.", "imgs": [{"nome": "Botrytis", "src": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/9d/Botrytis_cinerea_on_grapes.jpg/320px-Botrytis_cinerea_on_grapes.jpg", "desc": "Mofo Cinzento."}], "quimica": "Fludioxonil (Switch) à noite."}
        }
    },
    "Morango": {
        "vars": {"San Andreas": {"kc": 0.85, "info": "Dia Neutro."}, "Albion": {"kc": 0.85, "info": "Qualidade."}},
        "fases": {
            "Vegetativo": {"desc_tecnica": "Formação de coroa.", "fisiologia": "Balanço hormonal.", "manejo": "Retirar estolões.", "imgs": [{"nome": "Ácaro Rajado", "src": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/37/Tetranychus_urticae.jpg/320px-Tetranychus_urticae.jpg", "desc": "Teia na face inferior."}], "quimica": "Abamectina, Etoxazol."},
            "Frutificação": {"desc_tecnica": "Produção.", "fisiologia": "K para Brix.", "manejo": "Colheita.", "imgs": [{"nome": "Botrytis", "src": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b3/Strawberry_Botrytis.jpg/320px-Strawberry_Botrytis.jpg", "desc": "Podridão."}], "quimica": "Iprodiona, Procimidona."}
        }
    },
    "Amora Preta": {
        "vars": {"Tupy": {"kc": 1.0, "info": "Exige frio."}, "Xingu": {"kc": 1.05, "info": "Sem espinho."}},
        "fases": {"Frutificação": {"desc_tecnica": "Maturação.", "fisiologia": "Acúmulo de açúcar.", "manejo": "Monitorar SWD.", "imgs": [{"nome": "Drosófila", "src": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/33/Drosophila_suzukii_male_top.jpg/320px-Drosophila_suzukii_male_top.jpg", "desc": "Larva na fruta."}], "quimica": "Espinosade (Tracer)."}}
    },
    "Framboesa": {
        "vars": {"Heritage": {"kc": 1.1, "info": "Remontante."}, "Golden": {"kc": 1.05, "info": "Amarela."}},
        "fases": {"Florada": {"desc_tecnica": "Florescimento.", "fisiologia": "Sensível a chuva.", "manejo": "Proteger de chuva.", "imgs": [{"nome": "Podridão", "src": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/9d/Botrytis_cinerea_on_grapes.jpg/320px-Botrytis_cinerea_on_grapes.jpg", "desc": "Botrytis."}], "quimica": "Iprodiona."}}
    }
}

# --- 3. CÁLCULOS & API ---
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
        prompt = f"Engenheiro Agrônomo Sênior. Analise imagem de {cultura}. Contexto: {contexto}. Diagnostique o problema (praga/doença/deficiência). Explique a causa. Recomende Ingrediente Ativo Químico e Manejo Biológico."
        response = model.generate_content([prompt, imagem])
        return response.text
    except Exception as e: return f"Erro IA: {e}"

# --- 4. SIDEBAR ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3058/3058995.png", width=70)
    st.header("🎛️ Centro de Comando")
    with st.expander("🔑 Chaves de Acesso (API)", expanded=True):
        weather_key = st.text_input("OpenWeather API Key", type="password")
        gemini_key = st.text_input("Google Gemini AI Key", type="password")
    
    st.divider()
    cultura_sel = st.selectbox("Cultura:", list(BANCO_MASTER.keys()))
    
    # Tratamento de erro caso a cultura mude e a variedade antiga não exista na nova
    vars_list = list(BANCO_MASTER[cultura_sel]['vars'].keys())
    var_sel = st.selectbox("Variedade:", vars_list)
    
    fases_list = list(BANCO_MASTER[cultura_sel]['fases'].keys())
    fase_sel = st.selectbox("Fase Fenológica:", fases_list)
    
    if 'd_plantio' not in st.session_state: st.session_state['d_plantio'] = date(2025, 11, 25)
    d_plantio = st.date_input("Data Início:", st.session_state['d_plantio'])
    dias = (date.today() - d_plantio).days
    
    info_v = BANCO_MASTER[cultura_sel]['vars'][var_sel]
    st.info(f"📅 **Idade:** {dias} dias\n💧 **Kc:** {info_v['kc']}")

# --- 5. DASHBOARD ---
st.title("🛰️ Agro-Intel Ultimate v11.0")

if weather_key:
    # CABEÇALHO INTELIGENTE
    st.markdown(f"""
    <div class="header-box">
        <h2 style="margin:0; color:white;">🚜 {cultura_sel} - {var_sel}</h2>
        <p style="margin:5px 0 0 0; opacity:0.9; font-size:1.1em;">Fase Atual: <b>{fase_sel}</b> | 🧬 Ponto de Atenção Genético: {info_v['info']}</p>
    </div>
    """, unsafe_allow_html=True)

    lat, lon = "-13.414", "-41.285" # Ibicoara/Cascavel
    df = get_forecast(weather_key, lat, lon, info_v['kc'])
    
    if not df.empty:
        hoje = df.iloc[0]
        
        # KPIS
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("🌡️ Temperatura", f"{hoje['Temp']}°C", f"Umid: {hoje['Umid']}%")
        c2.metric("💧 VPD (Atividade)", f"{hoje['VPD']} kPa", "Ideal" if 0.4 <= hoje['VPD'] <= 1.3 else "Estresse")
        c3.metric("💦 Consumo (ETc)", f"{hoje['ETc']} mm", f"Kc: {info_v['kc']}")
        c4.metric("🛡️ Delta T (Pulverização)", f"{hoje['Delta T']}°C", "Permitido" if 2 <= hoje['Delta T'] <= 8 else "Risco")

        # NAVEGAÇÃO
        tabs = st.tabs(["🎓 Consultoria Técnica", "🧪 Farmácia Visual", "📊 Clima & Hídrico", "👁️ IA Vision", "💰 Gestão", "📡 Radar GPS"])

        # --- ABA 1: CONSULTORIA PROFUNDA ---
        with tabs[0]:
            dados_fase = BANCO_MASTER[cultura_sel]['fases'].get(fase_sel, {})
            if dados_fase:
                c_fisio, c_clima = st.columns(2)
                
                with c_fisio:
                    st.markdown(f"""
                    <div class="fisiologia-box">
                        <h3>🧬 Fisiologia da Fase ({fase_sel})</h3>
                        <p><b>O que está acontecendo na planta?</b><br>{dados_fase.get('desc_tecnica', '')}</p>
                        <p><b>Bioquímica & Nutrição:</b><br>{dados_fase.get('fisiologia', '')}</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                with c_clima:
                    # Lógica Climática Reativa
                    recomendacao_clima = "✅ <b>Clima Seco/Estável:</b> A pressão de doenças fúngicas é menor. Use Fungicidas Protetores (Mancozeb, Cobre, Clorotalonil) para blindar a planta com baixo custo."
                    alerta_clima = "Baixo Risco"
                    cor_alerta = "#e8f5e9" # Verde
                    
                    if hoje['Umid'] > 85 or hoje['Chuva'] > 2:
                        recomendacao_clima = "⚠️ <b>ALERTA DE UMIDADE:</b> Condição perfeita para esporulação de fungos (Requeima/Botrytis). <b>Suspenda Protetores.</b> Use Sistêmicos Curativos e Penetrantes imediatamente."
                        alerta_clima = "ALTO RISCO SANITÁRIO"
                        cor_alerta = "#ffebee" # Vermelho
                    
                    st.markdown(f"""
                    <div class="alerta-box" style="background-color: {cor_alerta}; border-color: {'red' if 'ALTO' in alerta_clima else 'green'};">
                        <h3>☁️ Análise Climática de Hoje</h3>
                        <h4>Status: {alerta_clima}</h4>
                        <p>{recomendacao_clima}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    st.markdown(f"""
                    <div class="manejo-box">
                        <h3>🛠️ Manejo Cultural Recomendado</h3>
                        <p>{dados_fase.get('manejo', '')}</p>
                    </div>
                    """, unsafe_allow_html=True)

        # --- ABA 2: FARMÁCIA VISUAL ---
        with tabs[1]:
            st.markdown("### 🔬 Identificação e Controle (Farmácia Digital)")
            dados_fase = BANCO_MASTER[cultura_sel]['fases'].get(fase_sel, {})
            
            if 'imgs' in dados_fase:
                cols_pragas = st.columns(len(dados_fase['imgs']))
                for i, alvo in enumerate(dados_fase['imgs']):
                    with cols_pragas[i]:
                        # Card Visual
                        st.markdown(f"""
                        <div class="quimica-card">
                            <h4 style="text-align:center; margin-bottom:5px;">🔴 {alvo['nome']}</h4>
                            <img src="{alvo['src']}" style="width:100%; border-radius:5px;">
                            <p class="caption-text">{alvo['desc']}</p>
                        </div>
                        """, unsafe_allow_html=True)
                
                st.divider()
                st.markdown("### 💊 Prescrição Química & Biológica")
                st.info(f"{dados_fase.get('quimica', 'Consulte um agrônomo.')}")
            else:
                st.warning("Selecione uma fase com dados cadastrados.")

        # --- ABA 3: CLIMA ---
        with tabs[2]:
            fig = go.Figure()
            fig.add_trace(go.Bar(x=df['Data'], y=df['Chuva'], name='Chuva (mm)', marker_color='#29b6f6'))
            fig.add_trace(go.Scatter(x=df['Data'], y=df['ETc'], name='Consumo ETc (mm)', line=dict(color='#ef5350', width=3)))
            fig.update_layout(title="Balanço Hídrico (Oferta x Demanda)", height=400)
            st.plotly_chart(fig, use_container_width=True)
            
            balanco = df['Chuva'].sum() - df['ETc'].sum()
            st.metric("Balanço Semanal (Saldo)", f"{balanco:.1f} mm", delta="Sobra" if balanco>0 else "Falta")

        # --- ABA 4: IA VISION ---
        with tabs[3]:
            st.markdown("### 👁️ Diagnóstico Fitopatológico (IA)")
            c_ia1, c_ia2 = st.columns([1, 2])
            with c_ia1:
                img = st.camera_input("Tirar Foto")
                if not img: img = st.file_uploader("Upload Imagem", type=['jpg', 'png'])
            
            with c_ia2:
                if img and gemini_key:
                    st.image(img, width=250)
                    ctx = f"Cultura: {cultura_sel}. Fase: {fase_sel}. Clima: Umidade {hoje['Umid']}%, Temp {hoje['Temp']}C."
                    with st.spinner("🤖 O Agrônomo Virtual está analisando..."):
                        res = analise_ia_gemini(gemini_key, Image.open(img), cultura_sel, ctx)
                        st.success(res)

        # --- ABA 5: FINANCEIRO ---
        with tabs[4]:
            st.markdown("### 💰 Controle de Custos (Safra)")
            if 'custos' not in st.session_state: st.session_state['custos'] = []
            
            c_fin1, c_fin2, c_fin3 = st.columns(3)
            item = c_fin1.text_input("Descrição (Ex: Ureia)")
            valor = c_fin2.number_input("Valor (R$)", min_value=0.0, step=10.0)
            if c_fin3.button("💾 Lançar Custo"):
                st.session_state['custos'].append({"Data": date.today(), "Item": item, "Valor": valor})
                st.success("Lançado!")
            
            if st.session_state['custos']:
                df_fin = pd.DataFrame(st.session_state['custos'])
                st.dataframe(df_fin, use_container_width=True)
                st.metric("Custo Total Acumulado", f"R$ {df_fin['Valor'].sum():,.2f}")

        # --- ABA 6: GPS ---
        with tabs[5]:
            VIZ = [{"nome": "Mucugê", "lat": -13.005, "lon": -41.371}, {"nome": "Barra da Estiva", "lat": -13.623, "lon": -41.326}, {"nome": "Cascavel", "lat": -13.196, "lon": -41.445}]
            st.map(pd.DataFrame([{"lat": float(lat), "lon": float(lon)}] + VIZ), zoom=9)
            
            row = st.columns(3)
            for i, v in enumerate(VIZ):
                try:
                    r = requests.get(f"https://api.openweathermap.org/data/2.5/weather?lat={v['lat']}&lon={v['lon']}&appid={weather_key}&units=metric").json()
                    row[i].metric(v['nome'], f"{r['main']['temp']:.0f}°C", r['weather'][0]['description'])
                except: pass

else:
    st.warning("⚠️ Insira a Chave OpenWeather no menu lateral para ativar o sistema.")
