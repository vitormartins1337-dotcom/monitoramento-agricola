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
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- 1. CONFIGURAÇÃO VISUAL ---
st.set_page_config(page_title="Agro-Intel Notificações", page_icon="🔔", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    .main { background-color: #f4f6f9; }
    div[data-testid="metric-container"] { background-color: #fff; border-left: 5px solid #0277bd; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
    .header-box { background: linear-gradient(135deg, #01579b 0%, #0288d1 100%); color: white; padding: 25px; border-radius: 10px; margin-bottom: 20px; }
    .tech-card { background-color: #fff; padding: 20px; border-radius: 8px; border: 1px solid #cfd8dc; margin-bottom: 15px; }
    .gda-box { background-color: #fff3e0; border: 1px solid #ffe0b2; padding: 15px; border-radius: 8px; margin-bottom: 15px; text-align: center; }
    .radar-card { background-color: #e1f5fe; padding: 10px; border-radius: 5px; text-align: center; border: 1px solid #b3e5fc; }
    .email-card { background-color: #f3e5f5; border: 1px solid #e1bee7; padding: 20px; border-radius: 8px; }
    .alert-high { background-color: #ffebee; border-left: 5px solid #c62828; padding: 15px; border-radius: 5px; color: #b71c1c; }
    .alert-low { background-color: #e8f5e9; border-left: 5px solid #2e7d32; padding: 15px; border-radius: 5px; color: #1b5e20; }
    h3 { margin-top: 0; }
</style>
""", unsafe_allow_html=True)

# --- 2. ENCICLOPÉDIA AGRONÔMICA (INTACTA) ---
BANCO_MASTER = {
    "Batata (Solanum tuberosum)": {
        "t_base": 7,
        "vars": {
            "Orchestra": {"kc": 1.15, "gda_meta": 1600, "info": "Pele lisa. Exige K para acabamento. Sensível a Pinta Preta."},
            "Cupido": {"kc": 1.10, "gda_meta": 1400, "info": "Ciclo curto. Extrema sensibilidade à Requeima."},
            "Camila": {"kc": 1.15, "gda_meta": 1550, "info": "Mercado fresco. Cuidado com Sarna Comum/Prateada."},
            "Atlantic": {"kc": 1.15, "gda_meta": 1650, "info": "Indústria. Monitorar Coração Oco e Matéria Seca."}
        },
        "fases": {
            "Emergência (0-20 dias)": {"desc": "Brotamento e enraizamento.", "fisiologia": "A planta drena reservas da batata-mãe. Raízes frágeis.", "manejo": "Solo deve estar friável. Não encharcar (risco de Pectobacterium).", "quimica": "**Solo:** Azoxistrobina (Rizoctonia) + Tiametoxam/Fipronil (Pragas).\n**Foliar:** Ciromazina (Minadora), Metribuzin (Herbicida pós-emergente)."},
            "Vegetativo (20-35 dias)": {"desc": "Crescimento explosivo da parte aérea.", "fisiologia": "Alta demanda de Nitrogênio e Cálcio. Definição do número de hastes.", "manejo": "Realizar a Amontoa. Monitorar Vaquinha (Diabrotica) e Pulgão.", "quimica": "**Preventivos:** Mancozeb, Clorotalonil, Propinebe.\n**Inseticidas:** Acetamiprido (Pulgão), Lambda-Cialotrina (Vaquinha)."},
            "Tuberização/Gancho (35-50 dias)": {"desc": "Início da formação dos tubérculos.", "fisiologia": "Inversão hormonal (Giberelina cai). Estresse hídrico causa Sarna e abortamento.", "manejo": "Fase Crítica! Água constante e leve. Controle 'militar' de Requeima.", "quimica": "**Requeima (Sistêmicos):** Metalaxil-M, Dimetomorfe, Mandipropamida, Fluazinam, Cimoxanil.\n**Bacterioses:** Kasugamicina."},
            "Enchimento (50-80 dias)": {"desc": "Crescimento dos tubérculos.", "fisiologia": "Dreno forte de Potássio e Magnésio. Translocação Folha -> Tubérculo.", "manejo": "Monitorar Mosca Branca, Traça e Larva Alfinete.", "quimica": "**Mosca Branca:** Ciantraniliprole, Espirotesifeno, Piriproxifem.\n**Traça:** Clorfenapir, Indoxacarbe, Espinosade.\n**Alternaria:** Tebuconazol, Boscalida."},
            "Maturação (80+ dias)": {"desc": "Senescência e formação de pele.", "fisiologia": "Suberização (cura da pele).", "manejo": "Dessecação. Evitar solo úmido (Podridão Mole/Sarna).", "quimica": "Dessecante: Diquat. Monitorar Traça no solo."}
        }
    },
    "Café (Coffea arabica)": {
        "t_base": 10,
        "vars": {"Catuaí": {"kc": 1.1, "gda_meta": 3000, "info": "Suscetível a ferrugem."}, "Arara": {"kc": 1.2, "gda_meta": 2900, "info": "Resistente a ferrugem."}},
        "fases": {
            "Florada (Set/Out)": {"desc": "Antese.", "fisiologia": "Alta demanda de Boro e Zinco para o tubo polínico.", "manejo": "Proteger polinizadores. Monitorar Phoma e Mancha Aureolada.", "quimica": "Foliar: Ca+B+Zn. Fungicida: Boscalida, Piraclostrobina."},
            "Chumbinho (Nov/Dez)": {"desc": "Expansão do fruto.", "fisiologia": "Intensa divisão celular. Déficit hídrico gera grãos pequenos.", "manejo": "Controle preventivo de Cercospora e Ferrugem.", "quimica": "**Ferrugem/Cercospora:** Ciproconazol + Azoxistrobina (Priori Xtra), Tebuconazol, Epoxiconazol."},
            "Granação (Jan/Mar)": {"desc": "Enchimento de grão (sólidos).", "fisiologia": "Pico de extração de N e K. Risco de escaldadura.", "manejo": "Monitorar Broca do Café e Bicho Mineiro.", "quimica": "**Broca:** Ciantraniliprole (Benévia), Clorantraniliprole.\n**Bicho Mineiro:** Cartape, Clorpirifós."}
        }
    },
    "Tomate": {
        "t_base": 10,
        "vars": {"Italiano": {"kc": 1.2, "gda_meta": 1600, "info": "Fundo Preto."}, "Grape": {"kc": 1.1, "gda_meta": 1450, "info": "Rachadura."}},
        "fases": {
            "Vegetativo": {"desc": "Crescimento de hastes.", "fisiologia": "Estruturação.", "manejo": "Desbrota. Monitorar Tripes (Vira-cabeça).", "quimica": "**Tripes:** Espinetoram, Formetanato.\n**Doenças:** Mancozeb, Cobre (Bacteriose)."},
            "Florada": {"desc": "Pegamento.", "fisiologia": "Abortamento se T>32°C.", "manejo": "Cálcio Foliar obrigatório. Monitorar Oídio.", "quimica": "**Oídio:** Enxofre, Metrafenona.\n**Nutrição:** Cálcio Quelatado."},
            "Frutificação": {"desc": "Engorda.", "fisiologia": "Dreno de K.", "manejo": "Monitorar Traça (Tuta) e Requeima.", "quimica": "**Tuta absoluta:** Clorfenapir, Teflubenzurom, Bacillus thuringiensis.\n**Requeima:** Mandipropamida, Zoxamida."}
        }
    },
    "Mirtilo (Blueberry)": {
        "t_base": 7,
        "vars": {"Emerald": {"kc": 0.95, "gda_meta": 1800, "info": "pH 4.5."}, "Biloxi": {"kc": 0.90, "gda_meta": 1900, "info": "Ereta."}},
        "fases": {
            "Brotação": {"desc": "Folhas novas.", "fisiologia": "Reservas.", "manejo": "Cochonilha.", "quimica": "Óleo Mineral + Imidacloprido."},
            "Florada": {"desc": "Polinização.", "fisiologia": "Abelhas.", "manejo": "Botrytis.", "quimica": "Fludioxonil (Switch) à noite. Não aplicar inseticida."},
            "Fruto Verde": {"desc": "Crescimento.", "fisiologia": "Sem Nitrato.", "manejo": "Antracnose/Ferrugem.", "quimica": "Azoxistrobina, Difenoconazol."}
        }
    },
    "Morango": {
        "t_base": 7,
        "vars": {"San Andreas": {"kc": 0.85, "gda_meta": 1200, "info": "Ácaros."}, "Albion": {"kc": 0.85, "gda_meta": 1250, "info": "Oídio."}},
        "fases": {
            "Vegetativo": {"desc": "Coroa.", "fisiologia": "Folhas.", "manejo": "Limpeza.", "quimica": "**Oídio:** Enxofre, Triflumizol.\n**Ácaro:** Abamectina."},
            "Florada": {"desc": "Flores.", "fisiologia": "Polinização.", "manejo": "Mofo Cinzento.", "quimica": "**Botrytis:** Iprodiona, Procimidona, Ciprodinil."},
            "Colheita": {"desc": "Fruto.", "fisiologia": "Açúcar.", "manejo": "Ácaro Rajado.", "quimica": "**Ácaro:** Etoxazol, Acequinocil (Carência curta)."}
        }
    },
    "Amora Preta": {
        "t_base": 7, "vars": {"Tupy": {"kc": 1.0, "gda_meta": 1500, "info": "Frio."}, "Xingu": {"kc": 1.05, "gda_meta": 1400, "info": "Sem espinho."}},
        "fases": {"Brotação": {"desc": "Hastes.", "fisiologia": "Vigor.", "manejo": "Ferrugem.", "quimica": "Tebuconazol."}, "Frutificação": {"desc": "Bagas.", "fisiologia": "Açúcar.", "manejo": "Drosófila.", "quimica": "Espinosade."}}
    },
    "Framboesa": {
        "t_base": 7, "vars": {"Heritage": {"kc": 1.1, "gda_meta": 1300, "info": "Remontante."}, "Golden": {"kc": 1.05, "gda_meta": 1250, "info": "Amarela."}},
        "fases": {"Brotação": {"desc": "Hastes.", "fisiologia": "Vigor.", "manejo": "Ácaro.", "quimica": "Abamectina."}, "Florada": {"desc": "Flores.", "fisiologia": "Chuva.", "manejo": "Podridão.", "quimica": "Iprodiona."}}
    }
}

# --- 3. FUNÇÕES (GEO, CÁLCULO, IA, EMAIL) ---
def get_credentials():
    return st.query_params.get("w_key", None), st.query_params.get("g_key", None)

def get_coords_from_city(city_name, api_key):
    try:
        url = f"http://api.openweathermap.org/geo/1.0/direct?q={city_name}&limit=1&appid={api_key}"
        r = requests.get(url).json()
        if r: return r[0]['lat'], r[0]['lon']
    except: pass
    return None, None

def calc_agro(temp, umid):
    es = 0.61078 * math.exp((17.27 * temp) / (temp + 237.3)); ea = es * (umid / 100); vpd = round(es - ea, 2)
    tw = temp * math.atan(0.151977 * (umid + 8.313659)**0.5) + math.atan(temp + umid) - math.atan(umid - 1.676331) + 0.00391838 * (umid)**1.5 * math.atan(0.023101 * umid) - 4.686035
    dt = round(temp - tw, 1)
    return dt, vpd

def get_forecast(api_key, lat, lon, kc, t_base):
    try:
        url = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={api_key}&units=metric&lang=pt_br"
        r = requests.get(url).json()
        dados = []
        for i in range(0, 40, 8):
            item = r['list'][i]
            t = item['main']['temp']
            dt, vpd = calc_agro(t, item['main']['humidity'])
            chuva = sum([r['list'][i+j].get('rain', {}).get('3h', 0) for j in range(8) if i+j < len(r['list'])])
            et0 = 0.0023 * (t + 17.8) * (t ** 0.5) * 0.408
            dados.append({'Data': datetime.fromtimestamp(item['dt']).strftime('%d/%m %Hh'), 'Temp': t, 'GDA': max(0, t-t_base), 'Chuva': round(chuva, 1), 'VPD': vpd, 'Delta T': dt, 'Umid': item['main']['humidity'], 'ETc': round(et0 * kc, 2)})
        return pd.DataFrame(dados)
    except: return pd.DataFrame()

def get_radar_data(api_key, lat, lon):
    pontos = {"Norte (15km)": (lat + 0.15, lon), "Sul (15km)": (lat - 0.15, lon), "Leste (15km)": (lat, lon + 0.15), "Oeste (15km)": (lat, lon - 0.15)}
    resultados = []
    for direcao, coords in pontos.items():
        try:
            url = f"https://api.openweathermap.org/data/2.5/weather?lat={coords[0]}&lon={coords[1]}&appid={api_key}&units=metric&lang=pt_br"
            r = requests.get(url).json()
            resultados.append({"Direcao": direcao, "Temp": r['main']['temp'], "Clima": r['weather'][0]['description'].title(), "Chuva": "Sim" if "rain" in r or "chuva" in r['weather'][0]['description'] else "Não"})
        except: pass
    return pd.DataFrame(resultados)

def enviar_notificacao(destinatario, assunto, corpo, smtp_email, smtp_senha):
    if not smtp_email or not smtp_senha:
        return False, "Configure o SMTP no menu lateral para enviar e-mails reais."
    try:
        msg = MIMEMultipart()
        msg['From'] = smtp_email
        msg['To'] = destinatario
        msg['Subject'] = assunto
        msg.attach(MIMEText(corpo, 'plain'))
        
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(smtp_email, smtp_senha)
        text = msg.as_string()
        server.sendmail(smtp_email, destinatario, text)
        server.quit()
        return True, "E-mail enviado com sucesso!"
    except Exception as e:
        return False, f"Erro no envio: {str(e)}"

# --- 4. CONFIGURAÇÃO (SIDEBAR) ---
url_w, url_g = get_credentials()

if 'loc_lat' not in st.session_state: st.session_state['loc_lat'] = -13.414
if 'loc_lon' not in st.session_state: st.session_state['loc_lon'] = -41.285
if 'pontos_mapa' not in st.session_state: st.session_state['pontos_mapa'] = []

with st.sidebar:
    st.header("⚙️ Configurações")
    with st.expander("🔑 Login / APIs", expanded=not url_w):
        val_w = st.text_input("OpenWeather Key", value=url_w if url_w else "", type="password")
        val_g = st.text_input("Gemini AI Key", value=url_g if url_g else "", type="password")
        if st.button("🔗 Salvar"): st.query_params["w_key"] = val_w; st.query_params["g_key"] = val_g; st.rerun()
    
    # NOVA CONFIGURAÇÃO DE E-MAIL
    with st.expander("📧 Configuração SMTP (Opcional)"):
        st.caption("Para envio real de e-mails (Gmail)")
        smtp_user = st.text_input("Seu Gmail:", placeholder="exemplo@gmail.com")
        smtp_pass = st.text_input("Senha de App:", type="password", help="Use a 'Senha de App' do Google, não a sua senha normal.")

    st.divider()
    
    st.markdown("### 📍 Localização da Propriedade")
    tab_busca, tab_coord = st.tabs(["🔍 Cidade", "🌐 Coordenadas"])
    with tab_busca:
        cidade = st.text_input("Buscar Cidade:", placeholder="Ex: Mucugê, BA")
        if st.button("Buscar") and cidade and val_w:
            nlat, nlon = get_coords_from_city(cidade, val_w)
            if nlat: 
                st.session_state['loc_lat'], st.session_state['loc_lon'] = nlat, nlon
                st.success("Localizado!")
                st.rerun()
    with tab_coord:
        nlat = st.number_input("Latitude:", value=st.session_state['loc_lat'], format="%.5f")
        nlon = st.number_input("Longitude:", value=st.session_state['loc_lon'], format="%.5f")
        if st.button("Atualizar GPS"):
            st.session_state['loc_lat'], st.session_state['loc_lon'] = nlat, nlon
            st.rerun()

    st.divider()
    cultura_sel = st.selectbox("Cultura:", list(BANCO_MASTER.keys()))
    var_sel = st.selectbox("Cultivar:", list(BANCO_MASTER[cultura_sel]['vars'].keys()))
    fase_sel = st.selectbox("Fase Atual:", list(BANCO_MASTER[cultura_sel]['fases'].keys()))
    
    if 'd_plantio' not in st.session_state: st.session_state['d_plantio'] = date(2025, 11, 25)
    d_plantio = st.date_input("Início do Ciclo:", st.session_state['d_plantio'])
    info_v = BANCO_MASTER[cultura_sel]['vars'][var_sel]

# --- 5. DASHBOARD ---
st.title("🛰️ Agro-Intel Notificações v19.0")

if val_w:
    df = get_forecast(val_w, st.session_state['loc_lat'], st.session_state['loc_lon'], info_v['kc'], BANCO_MASTER[cultura_sel]['t_base'])
    
    if not df.empty:
        hoje = df.iloc[0]
        dias_campo = (date.today() - d_plantio).days
        media_gda_dia = df['GDA'].mean()
        gda_acumulado_estimado = dias_campo * media_gda_dia
        gda_meta = info_v.get('gda_meta', 1500)
        progresso_maturacao = min(1.0, gda_acumulado_estimado / gda_meta)

        st.markdown(f"""
        <div class="header-box">
            <h2>Gestão: {cultura_sel} - {var_sel}</h2>
            <p style="font-size:1.2em">
                📆 <b>Idade: {dias_campo} dias</b> | Fase: <b>{fase_sel}</b>
            </p>
            <p>🧬 Genética: {info_v['info']}</p>
        </div>
        """, unsafe_allow_html=True)
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("🌡️ Temp", f"{hoje['Temp']:.1f}°C", f"Umid: {hoje['Umid']}%")
        c2.metric("💧 VPD", f"{hoje['VPD']} kPa", "Ideal" if 0.4 <= hoje['VPD'] <= 1.3 else "Alerta")
        c3.metric("💦 ETc", f"{hoje['ETc']} mm", f"Kc: {info_v['kc']}")
        c4.metric("🛡️ Delta T", f"{hoje['Delta T']}°C", "Ok" if 2 <= hoje['Delta T'] <= 8 else "Ruim")

        # ADICIONADA A NOVA ABA DE NOTIFICAÇÕES (Sétima Aba)
        tabs = st.tabs(["🎓 Consultoria Técnica", "📊 Clima & Água", "📡 Radar Regional", "👁️ IA Vision", "💰 Custos", "🗺️ Mapa da Fazenda", "🔔 Notificações"])

        # ABA 1: CONSULTORIA
        with tabs[0]:
            dados = BANCO_MASTER[cultura_sel]['fases'][fase_sel]
            st.markdown(f"""<div class="gda-box"><h4>🔥 Maturação Térmica (GDA)</h4><p>Acumulado Estimado: <b>{gda_acumulado_estimado:.0f}</b> / Meta: <b>{gda_meta}</b> GDA</p></div>""", unsafe_allow_html=True)
            st.progress(progresso_maturacao)
            
            risco = "Baixo"; msg = "✅ <b>Clima Seco:</b> Use Protetores (Mancozeb/Cobre)."; estilo = "alert-low"
            if hoje['Umid'] > 85 or hoje['Chuva'] > 2: risco="ALTO"; msg="🚨 <b>ALERTA UMIDADE:</b> Risco severo. Use <b>SISTÊMICOS</b>."; estilo="alert-high"
            
            c_esq, c_dir = st.columns(2)
            with c_esq:
                st.markdown(f"""<div class="tech-card"><div class="tech-header">🧬 Fisiologia da Fase</div><p><b>Resumo:</b> {dados['desc']}</p><p><b>Detalhe:</b> {dados['fisiologia']}</p></div>""", unsafe_allow_html=True)
                st.markdown(f"""<div class="{estilo}"><strong>☁️ Matriz de Decisão (Hoje)</strong><br>{msg}</div>""", unsafe_allow_html=True)
            with c_dir:
                st.markdown(f"""<div class="tech-card"><div class="tech-header">🛠️ Plano de Manejo</div><p><b>Cultural:</b> {dados['manejo']}</p><hr><p><b>🧪 Químico:</b><br>{dados['quimica']}</p></div>""", unsafe_allow_html=True)

        # ABA 2: CLIMA
        with tabs[1]:
            fig = go.Figure()
            fig.add_trace(go.Bar(x=df['Data'], y=df['Chuva'], name='Chuva', marker_color='#3b82f6'))
            fig.add_trace(go.Scatter(x=df['Data'], y=df['ETc'], name='ETc', line=dict(color='#ef4444', width=2)))
            st.plotly_chart(fig, use_container_width=True)

        # ABA 3: RADAR
        with tabs[2]:
            st.markdown("### 📡 Monitoramento de Vizinhança (Raio 15km)")
            df_radar = get_radar_data(val_w, st.session_state['loc_lat'], st.session_state['loc_lon'])
            if not df_radar.empty:
                cols = st.columns(4)
                for idx, row in df_radar.iterrows():
                    cor = "#ffebee" if row['Chuva'] == "Sim" else "#e8f5e9"
                    with cols[idx]:
                        st.markdown(f"""<div class="radar-card" style="background-color: {cor}"><b>{row['Direcao']}</b><br><span style="font-size: 1.5em">{row['Temp']:.0f}°C</span><br>{row['Clima']}<br><small>Chuva: {row['Chuva']}</small></div>""", unsafe_allow_html=True)

        # ABA 4: IA
        with tabs[3]:
            img = st.camera_input("Foto da Folha")
            if img and val_g:
                genai.configure(api_key=val_g)
                with st.spinner("Analisando..."):
                    st.success(genai.GenerativeModel('gemini-1.5-flash').generate_content([f"Agrônomo. Analise {cultura_sel}. Fase {fase_sel}. Umidade {hoje['Umid']}%. Diagnóstico e Solução.", Image.open(img)]).text)

        # ABA 5: CUSTOS
        with tabs[4]:
            if 'custos' not in st.session_state: st.session_state['custos'] = []
            c1, c2 = st.columns(2)
            i = c1.text_input("Item"); v = c2.number_input("R$")
            if c2.button("Lançar"): st.session_state['custos'].append({"Item": i, "Valor": v}); st.success("Salvo")
            if st.session_state['custos']: st.dataframe(pd.DataFrame(st.session_state['custos'])); st.metric("Total", f"R$ {pd.DataFrame(st.session_state['custos'])['Valor'].sum()}")

        # ABA 6: MAPA
        with tabs[5]:
            st.markdown("### 🗺️ Mapa da Propriedade")
            c_add_pt, c_mapa = st.columns([1, 3])
            with c_add_pt:
                nome_pt = st.text_input("Nome do Talhão")
                if st.session_state.get('last_click'):
                    st.caption(f"Lat: {st.session_state['last_click'][0]:.4f}, Lon: {st.session_state['last_click'][1]:.4f}")
                    if st.button("💾 Salvar Ponto") and nome_pt:
                        st.session_state['pontos_mapa'].append({"nome": nome_pt, "lat": st.session_state['last_click'][0], "lon": st.session_state['last_click'][1]})
                        st.success("Salvo!")
                        st.rerun()
                if st.session_state['pontos_mapa']:
                    st.divider(); st.write("**Pontos Salvos:**")
                    for p in st.session_state['pontos_mapa']: st.write(f"📍 {p['nome']}")
            with c_mapa:
                m = folium.Map(location=[st.session_state['loc_lat'], st.session_state['loc_lon']], zoom_start=14)
                folium.TileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', attr='Esri', name='Satélite').add_to(m)
                LocateControl().add_to(m); Fullscreen().add_to(m)
                folium.Marker([st.session_state['loc_lat'], st.session_state['loc_lon']], popup="Sede", icon=folium.Icon(color='red', icon='home')).add_to(m)
                for p in st.session_state['pontos_mapa']: folium.Marker([p['lat'], p['lon']], popup=p['nome'], icon=folium.Icon(color='green', icon='leaf')).add_to(m)
                out = st_folium(m, width="100%", height=500, returned_objects=["last_clicked"])
                if out["last_clicked"]: st.session_state['last_click'] = (out["last_clicked"]["lat"], out["last_clicked"]["lng"]); st.rerun()

        # --- ABA 7: NOTIFICAÇÕES (NOVA!) ---
        with tabs[6]:
            st.markdown("### 🔔 Configuração de Alertas Automáticos")
            st.write("Receba os relatórios do Agro-Intel diretamente no seu e-mail todas as manhãs.")
            
            c_email, c_check = st.columns([2, 1])
            
            with c_email:
                st.markdown("""
                <div class="email-card">
                    <h4>📧 Inscrição</h4>
                    <p>O sistema enviará alertas de <b>Risco Climático (Requeima/Umidade)</b> e <b>Resumo Semanal</b>.</p>
                </div>
                """, unsafe_allow_html=True)
                email_destinatario = st.text_input("Seu E-mail para receber alertas:", placeholder="produtor@fazenda.com")
            
            with c_check:
                st.write("**Selecione os Tópicos:**")
                check_clima = st.checkbox("⛈️ Alertas Climáticos (Diário)", value=True)
                check_praga = st.checkbox("🐛 Alertas de Pragas (Semanal)", value=True)
                check_fin = st.checkbox("💰 Fechamento Financeiro (Mensal)", value=False)
            
            st.divider()
            
            if st.button("💾 Salvar e Enviar Teste"):
                if email_destinatario:
                    # Tenta enviar e-mail real se tiver configurado
                    sucesso, msg = enviar_notificacao(
                        email_destinatario, 
                        "Bem-vindo ao Agro-Intel Alertas", 
                        f"Olá!\n\nSeu cadastro foi confirmado para a cultura de {cultura_sel}.\nVocê receberá alertas quando houver risco de Requeima ou alta umidade.\n\nAtenciosamente,\nEquipe Agro-Intel",
                        smtp_user,
                        smtp_pass
                    )
                    
                    if sucesso:
                        st.success(f"✅ {msg}")
                    else:
                        st.warning(f"⚠️ {msg}")
                        st.info("💡 Dica: Configure o SMTP no menu lateral para o envio funcionar de verdade. Por enquanto, seu cadastro foi salvo localmente.")
                else:
                    st.error("Por favor, digite um e-mail válido.")

else:
    st.warning("⚠️ Configure suas chaves no menu lateral para iniciar.")
