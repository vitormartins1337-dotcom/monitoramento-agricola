import requests
import os
import smtplib
import math
import csv
import logging
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage

# --- 1. CONFIGURAÇÕES GERAIS (SETUP) ---
# True = Manda e-mail AGORA e não apaga o input (Para testar).
# False = Modo Produção (Respeita horários e limpa input).
MODO_TESTE = True 

DATA_PLANTIO = datetime(2025, 11, 25) 
KC_ATUAL = 0.75 
FUSO_BRASIL = timezone(timedelta(hours=-3))
CIDADE = "Ibicoara, BR"

# Credenciais
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_KEY")
GMAIL_PASSWORD = os.getenv("GMAIL_PASSWORD")
EMAIL_DESTINO = "vitormartins1337@gmail.com"

# Configuração de Logs (Para auditoria profissional)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- 2. BANCO DE CONHECIMENTO CIENTÍFICO (KNOWLEDGE BASE) ---
DB_CIENCIA = {
    'vpd_baixo': """
    ⚠️ **ANÁLISE TERMODINÂMICA (VPD < 0.4 kPa): BLOQUEIO HIDRÁULICO**
    • **Fisiologia:** Atmosfera saturada. Déficit de pressão de vapor nulo.
    • **Consequência:** A "bomba hidráulica" do xilema desliga. Sem transpiração, cessa o fluxo de massa.
    • **Impacto:** Cálcio e Boro (imóveis) não chegam aos frutos. Risco severo de doenças (Gutação).
    """,
    'vpd_alto': """
    🔥 **ANÁLISE TERMODINÂMICA (VPD > 1.4 kPa): ESTRESSE ATMOSFÉRICO**
    • **Fisiologia:** Alta demanda evaporativa.
    • **Reação:** Fechamento estomático imediato para evitar plasmólise.
    • **Impacto:** Interrupção da fotossíntese (sem CO2) e paralisação do ganho de biomassa.
    """,
    'vpd_ideal': """
    ✅ **ANÁLISE TERMODINÂMICA (VPD IDEAL): EFICIÊNCIA MÁXIMA**
    • **Fisiologia:** Equilíbrio térmico. Estômatos abertos.
    • **Impacto:** Transpiração (resfriamento) e Fixação de Carbono simultâneas. Máxima absorção de nutrientes.
    """,
    'nutri_raiz': """
    🛒 **NUTRIÇÃO: FASE DE ENRAIZAMENTO**
    • **Foco:** Fósforo (P) e Cálcio (Ca).
    • **Bioquímica:** P = ATP (Energia para divisão celular). Ca = Pectatos (Cimento da parede celular/Resistência).
    """,
    'nutri_veg': """
    🛒 **NUTRIÇÃO: FASE VEGETATIVA**
    • **Foco:** Nitrogênio (N) e Magnésio (Mg).
    • **Bioquímica:** N = Proteínas e Aminoácidos. Mg = Átomo central da Clorofila (Conversão de Luz em Energia).
    """,
    'nutri_fruto': """
    🛒 **NUTRIÇÃO: FASE DE FRUTIFICAÇÃO**
    • **Foco:** Potássio (K) e Boro (B).
    • **Bioquímica:** K = Transporte de açúcares (Floema). B = Viabilidade do tubo polínico e divisão celular no fruto.
    """
}

FARMACIA_AGRO = {
    'botrytis': "🦠 **PROTOCOLO (Botrytis):** *Fludioxonil*, *Ciprodinil* ou *Bacillus subtilis*.",
    'antracnose': "🦠 **PROTOCOLO (Antracnose):** *Azoxistrobina* + *Difenoconazol*.",
    'ferrugem': "🦠 **PROTOCOLO (Ferrugem):** *Tebuconazol* ou *Protioconazol*.",
    'ácaro': "🦠 **PROTOCOLO (Ácaros):** *Abamectina* ou *Espirodiclofeno*."
}

# --- 3. MOTOR DE CÁLCULO ---
def calcular_delta_t_e_vpd(temp, umidade):
    try:
        es = 0.61078 * math.exp((17.27 * temp) / (temp + 237.3))
        ea = es * (umidade / 100)
        vpd = round(es - ea, 2)
        tw = temp * math.atan(0.151977 * (umidade + 8.313659)**0.5) + \
             math.atan(temp + umidade) - math.atan(umidade - 1.676331) + \
             0.00391838 * (umidade)**1.5 * math.atan(0.023101 * umidade) - 4.686035
        delta_t = round(temp - tw, 1)
        return delta_t, vpd
    except Exception as e:
        logging.error(f"Erro matemático: {e}")
        return 0, 0

# --- 4. GESTÃO DE DADOS ---
def ler_atividades_usuario():
    arquivo = 'input_atividades.txt'
    if os.path.exists(arquivo):
        with open(arquivo, 'r', encoding='utf-8') as f:
            conteudo = f.read().strip()
        
        # Só limpa o arquivo se NÃO for teste e se for de manhã
        hora = datetime.now(FUSO_BRASIL).hour
        is_manhat = 5 <= hora <= 8
        
        if not MODO_TESTE and is_manhat and conteudo != "Início do caderno de campo":
            with open(arquivo, 'w', encoding='utf-8') as f: f.write("")
            logging.info("Input do usuário lido e limpo.")
        return conteudo
    return ""

def enviar_email(assunto, corpo):
    msg = EmailMessage()
    msg.set_content(corpo)
    msg['Subject'] = assunto
    msg['From'] = EMAIL_DESTINO
    msg['To'] = EMAIL_DESTINO
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(EMAIL_DESTINO, GMAIL_PASSWORD)
            smtp.send_message(msg)
        logging.info(f"✅ E-mail '{assunto}' enviado com sucesso!")
    except Exception as e:
        logging.error(f"❌ Falha crítica no envio de e-mail: {e}")

def get_agro_data():
    url = f"https://api.openweathermap.org/data/2.5/forecast?q={CIDADE}&appid={OPENWEATHER_API_KEY}&units=metric&lang=pt_br"
    try:
        r = requests.get(url); r.raise_for_status()
        return r.json()
    except Exception as e:
        logging.error(f"Erro na API OpenWeather: {e}")
        return None

# --- 5. INTELIGÊNCIA CENTRAL (DECISOR) ---
def gerar_laudo_tecnico(previsoes, anotacao):
    hoje = previsoes[0]
    dias_campo = (datetime.now(FUSO_BRASIL).date() - DATA_PLANTIO.date()).days
    
    # --- A. ANÁLISE CRUZADA (CLIMA x MANEJO) ---
    texto = anotacao.lower()
    analise_campo = ""
    
    usuario_relatou_chuva = any(x in texto for x in ["chuva", "água", "molhou", "temporal"])
    usuario_adubou = any(x in texto for x in ["adubo", "fertirrigação", "nitrato", "cálcio", "aplicação"])
    solo_saturado = hoje['chuva'] > 5.0 or usuario_relatou_chuva
    vpd_critico = hoje['vpd'] < 0.4
    
    if usuario_adubou and solo_saturado:
        analise_campo += "🔴 **DIAGNÓSTICO CRÍTICO:** Fertirrigação em solo saturado. Ocorre lixiviação (lavagem) e Anoxia Radicular.\n"
    elif not usuario_adubou and vpd_critico:
        analise_campo += "⛔ **DIRETRIZ DE BLOQUEIO:** Ar saturado. Planta não absorve. NÃO IRRIGUE HOJE.\n"
    elif usuario_adubou and vpd_critico:
         analise_campo += "🟡 **ALERTA DE INEFICIÊNCIA:** Adubação com VPD baixo. Nutriente não sobe para a folha.\n"
    else:
        analise_campo += "✅ **OPERAÇÃO NOMINAL:** Manejo preventivo padrão.\n"

    for praga, texto_tec in FARMACIA_AGRO.items():
        if praga in texto: analise_campo += f"{texto_tec}\n"

    # --- B. CONTEÚDO CIENTÍFICO ---
    if hoje['vpd'] > 1.4: texto_vpd = DB_CIENCIA['vpd_alto']
    elif hoje['vpd'] < 0.4: texto_vpd = DB_CIENCIA['vpd_baixo']
    else: texto_vpd = DB_CIENCIA['vpd_ideal']

    if dias_campo < 45: texto_nutri = DB_CIENCIA['nutri_raiz']
    elif dias_campo < 130: texto_nutri = DB_CIENCIA['nutri_veg']
    else: texto_nutri = DB_CIENCIA['nutri_fruto']

    gda_total = dias_campo * 14.8
    horas_orvalho = sum(1 for p in previsoes if p['umidade'] > 88)
    
    # --- C. MONTAGEM ---
    laudo = f"🏛️ **LAUDO TÉCNICO PROFISSIONAL**\n📍 Unidade: {CIDADE} | Idade: {dias_campo} dias\n\n"
    laudo += f"🔎 **1. ANÁLISE DE MANEJO:**\nRegistro: \"{anotacao}\"\n{analise_campo}"
    laudo += "-"*40 + "\n"
    laudo += f"🌡️ **2. FISIOLOGIA:**\n• VPD: {hoje['vpd']} kPa | Delta T: {hoje['delta_t']}°C\n{texto_vpd}\n"
    laudo += f"💊 **3. SANIDADE:**\n• Orvalho: {horas_orvalho} janelas. (Risco {'ALTO' if horas_orvalho > 2 else 'BAIXO'}).\n\n"
    laudo += f"{texto_nutri}\n"
    laudo += f"🧬 **4. METABOLISMO:**\n• GDA Acumulado: {gda_total:.0f}\n"
    
    return laudo

# --- 6. SISTEMA DE VIGILÂNCIA (SENTINELA DA TARDE) ---
def ronda_vigilancia(previsoes):
    logging.info("🔭 Iniciando Ronda de Vigilância Climática...")
    # Analisa próximas 9 horas
    chuva_prox = sum(p['chuva'] for p in previsoes[:3])
    vento_max = max(p['vento'] for p in previsoes[:3])
    
    if chuva_prox > 5.0 or vento_max > 25:
        alerta = f"🚨 **ALERTA DE MUDANÇA BRUSCA DE CENÁRIO**\n\n"
        alerta += f"Alteração crítica não prevista pela manhã.\n"
        alerta += f"• Chuva Iminente: {chuva_prox}mm\n"
        alerta += f"• Vento: {vento_max} km/h\n\n"
        alerta += "⚠️ **AÇÃO:** Suspenda aplicações foliares e fertirrigação."
        enviar_email(f"🚨 ALERTA URGENTE: {datetime.now(FUSO_BRASIL).strftime('%H:%M')}", alerta)
    else:
        logging.info("✅ Vigilância: Sem alterações críticas.")

# --- 7. EXECUTOR MESTRE ---
if __name__ == "__main__":
    logging.info("🚀 Iniciando Sistema Agro-Intel...")
    raw = get_agro_data()
    
    if raw:
        # Processamento de Dados (ETL)
        previsoes = []
        for i in range(0, min(40, len(raw['list'])), 8):
            item = raw['list'][i]
            t, u = item['main']['temp'], item['main']['humidity']
            dt, vpd = calcular_delta_t_e_vpd(t, u)
            et0 = 0.0023 * (t + 17.8) * (t ** 0.5) * 0.408
            chuva = sum([raw['list'][i+j].get('rain', {}).get('3h', 0) for j in range(8) if i+j < len(raw['list'])])
            previsoes.append({'data': datetime.fromtimestamp(item['dt']).strftime('%d/%m'), 'temp': t, 'umidade': u, 'vpd': vpd, 'delta_t': dt, 'vento': item['wind']['speed']*3.6, 'chuva': round(chuva, 1), 'et0': round(et0, 2)})

        hora = datetime.now(FUSO_BRASIL).hour
        
        # --- LÓGICA DE ROTINA ---
        # Se for teste OU horário da manhã (05-08h) -> Relatório Completo
        if MODO_TESTE or (5 <= hora <= 8):
            logging.info("📝 Gerando Relatório Matinal Completo...")
            anotacao = ler_atividades_usuario()
            laudo = gerar_laudo_tecnico(previsoes, anotacao)
            
            # Tabela Resumo
            header = f"💎 CONSULTORIA AGRO-INTEL PREMIUM\n📅 {datetime.now(FUSO_BRASIL).strftime('%d/%m/%Y %H:%M')}\n"
            header += "-"*60 + "\n"
            for p in previsoes:
                header += f"{p['data']} | {p['temp']}°C | 🌧️ {p['chuva']}mm | 💧 {round(p['et0']*KC_ATUAL, 2)}mm\n"
            
            enviar_email(f"💎 LAUDO TÉCNICO: {datetime.now(FUSO_BRASIL).strftime('%d/%m')}", header + "\n" + laudo)
            
            # Salvar no Histórico (CSV)
            try:
                with open('caderno_de_campo_master.csv', 'a', newline='', encoding='utf-8') as f:
                    csv.writer(f).writerow([datetime.now().strftime('%d/%m/%Y'), previsoes[0]['temp'], anotacao, "Laudo Enviado"])
            except Exception as e: logging.error(f"Erro CSV: {e}")
            
        else:
            # Se for tarde e não for teste -> Vigilância
            ronda_vigilancia(previsoes)
            
    else:
        logging.error("❌ Falha na conexão com API de Clima.")
