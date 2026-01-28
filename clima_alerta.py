import requests
import os
import smtplib
import math
import csv
import random
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage

# --- 1. CONFIGURAÇÕES E FUSO HORÁRIO ---
DATA_PLANTIO = datetime(2025, 11, 25) 
T_BASE_BERRIES = 10.0 
GDA_ALVO_COLHEITA = 1200 
KC_ATUAL = 0.75
FUSO_BRASIL = timezone(timedelta(hours=-3))

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_KEY")
GMAIL_PASSWORD = os.getenv("GMAIL_PASSWORD")
EMAIL_DESTINO = "vitormartins1337@gmail.com"
CIDADE = "Ibicoara, BR"

# --- 2. BANCO DE INTELIGÊNCIA (FRASES E QUÍMICOS) ---

# Variações de frases para não ficar repetitivo (Humanização)
FRASES_DINAMICAS = {
    'vpd_alto': [
        "⚠️ O ar está 'roubando' água da planta. Os estômatos se fecharam para defesa.",
        "⚠️ Atmosfera com alta demanda hídrica. A fotossíntese pode estar paralisada agora.",
        "⚠️ Alerta de estresse: A planta parou de transpirar para não desidratar. Cálcio não sobe."
    ],
    'vpd_ideal': [
        "✅ Zona de conforto total. A 'bomba' de nutrientes está ligada no máximo.",
        "✅ Condição perfeita para produção de biomassa e enchimento de fruto.",
        "✅ Metabolismo acelerado. Ótimo momento para fertirrigação."
    ],
    'sanidade_risco': [
        "🍄 Atenção: O clima criou uma 'estufa' perfeita para fungos hoje.",
        "🍄 Alerta vermelho: Molhamento foliar prolongado favorece esporulação.",
        "🍄 Risco Fitossanitário: A folha não está secando rápido o suficiente."
    ],
    'sanidade_ok': [
        "🛡️ Ambiente hostil para fungos. O vento e a baixa umidade estão ajudando.",
        "🛡️ Baixo risco de infecção. As folhas estão secando rapidamente.",
        "🛡️ Sanidade favorecida pelo clima seco e ventilado."
    ]
}

# Banco de Defensivos (Ingredientes Ativos Comuns para Berries)
FARMACIA_AGRO = {
    'botrytis': "🧪 INDICAÇÃO QUÍMICA (Mofo Cinzento): Ingredientes comuns incluem **Fludioxonil**, **Ciprodinil** ou **Iprodiona**. Biológico: *Bacillus subtilis*.",
    'antracnose': "🧪 INDICAÇÃO QUÍMICA (Antracnose): Ingredientes comuns incluem **Azoxistrobina**, **Difenoconazol** ou **Mancozebe** (protetor).",
    'ferrugem': "🧪 INDICAÇÃO QUÍMICA (Ferrugem): Ingredientes comuns incluem **Tebuconazol** ou **Protioconazol**.",
    'oídio': "🧪 INDICAÇÃO QUÍMICA (Oídio): Ingredientes comuns incluem **Enxofre**, **Metil Tiofanato** ou **Difenoconazol**.",
    'ácaro': "🧪 INDICAÇÃO QUÍMICA (Ácaros): Ingredientes comuns incluem **Abamectina**, **Espirodiclofeno** ou **Propargite**.",
    'lagarta': "🧪 INDICAÇÃO QUÍMICA (Lagartas): Ingredientes comuns incluem **Spinosad**, **Clorantraniliprole** ou Biológico: *Bacillus thuringiensis* (Bt).",
    'tripes': "🧪 INDICAÇÃO QUÍMICA (Tripes): Ingredientes comuns incluem **Espinosade** ou **Imidacloprido** (Cuidado com abelhas!)."
}

# --- 3. CÁLCULOS FÍSICOS ---

def calcular_delta_t_e_vpd(temp, umidade):
    es = 0.61078 * math.exp((17.27 * temp) / (temp + 237.3))
    ea = es * (umidade / 100)
    vpd = round(es - ea, 2)
    tw = temp * math.atan(0.151977 * (umidade + 8.313659)**0.5) + \
         math.atan(temp + umidade) - math.atan(umidade - 1.676331) + \
         0.00391838 * (umidade)**1.5 * math.atan(0.023101 * umidade) - 4.686035
    delta_t = round(temp - tw, 1)
    return delta_t, vpd

# --- 4. INTERPRETAÇÃO E LEITURA ---

def ler_atividades_usuario():
    arquivo_input = 'input_atividades.txt'
    if os.path.exists(arquivo_input):
        with open(arquivo_input, 'r', encoding='utf-8') as f:
            conteudo = f.read().strip()
        if conteudo and conteudo != "Início do caderno de campo":
            with open(arquivo_input, 'w', encoding='utf-8') as f:
                f.write("")
            return conteudo
    return "Nenhum manejo registrado hoje."

def processar_gatilhos_inteligentes(texto):
    """Analisa texto buscando pragas específicas para sugerir quimicos."""
    analise_extra = ""
    texto_lower = texto.lower()
    
    # 1. Gatilhos de Chuva/Clima
    if any(p in texto_lower for p in ["chuva", "chovendo", "volume", "água"]):
        analise_extra += "⚠️ **ALERTA HÍDRICO:** Chuva relatada. Risco iminente de lixiviação de Nitrogênio/Potássio e asfixia radicular (anoxia).\n"

    # 2. Gatilhos de Nutrição
    if any(p in texto_lower for p in ["adubo", "fertirrigação", "cálcio", "nitrato"]):
        analise_extra += "🧪 **NUTRIÇÃO:** Aplicação registrada. Monitore a EC do solo para evitar salinização após a chuva.\n"

    # 3. Gatilhos Fitossanitários (A "Farmácia")
    encontrou_praga = False
    for praga, recomendacao in FARMACIA_AGRO.items():
        if praga in texto_lower:
            analise_extra += f"{recomendacao}\n"
            encontrou_praga = True
    
    if encontrou_praga:
        analise_extra += "⚠️ **NOTA LEGAL:** As sugestões de ativos baseiam-se na literatura da cultura. Consulte sempre um Engenheiro Agrônomo local para o receituário oficial da Bahia (ADAB).\n"

    return analise_extra if analise_extra else "✅ Operação nominal. Sem alertas críticos de interação no manejo reportado."

def gerar_conclusao_agronomo(hoje, anotacao, dias_campo):
    conclusao = "👨‍🔬 **PARECER TÉCNICO:**\n"
    if "chuva" in anotacao.lower():
        conclusao += "Cenário de excesso hídrico. Prioridade total para drenagem e fungicidas sistêmicos. "
    elif hoje['vpd'] > 1.3:
        conclusao += "Estresse térmico detectado. Planta em fechamento estomático. Evitar manejo que exija alta atividade metabólica. "
    else:
        conclusao += "Janela fisiológica excelente. Otimizar fertirrigação para ganho de calibre de fruto. "
    
    conclusao += f"Cultura com {dias_campo} dias: Monitorar vigor vegetativo vs. reprodutivo."
    return conclusao

# --- 5. GERAÇÃO DO RELATÓRIO DINÂMICO ---

def analisar_expert_educativo(previsoes, anotacao_usuario):
    hoje = previsoes[0]
    total_etc = sum(p['et0'] * KC_ATUAL for p in previsoes)
    dias_campo = (datetime.now(FUSO_BRASIL).date() - DATA_PLANTIO.date()).days
    
    # Processamento Inteligente
    analise_gatilho = processar_gatilhos_inteligentes(anotacao_usuario)
    conclusao_final = gerar_conclusao_agronomo(hoje, anotacao_usuario, dias_campo)
    
    # --- SELEÇÃO DE FRASES DINÂMICAS (Sorteio) ---
    frase_vpd = random.choice(FRASES_DINAMICAS['vpd_alto']) if hoje['vpd'] > 1.3 else (random.choice(FRASES_DINAMICAS['vpd_ideal']) if hoje['vpd'] >= 0.4 else "⚠️ VPD muito baixo. Risco de gutação.")
    
    horas_molhamento = sum(1 for p in previsoes if p['umidade'] > 88 and p['vento'] < 6)
    risco_sanidade = 'ALTO' if horas_molhamento > 2 else 'BAIXO'
    frase_sanidade = random.choice(FRASES_DINAMICAS['sanidade_risco']) if risco_sanidade == 'ALTO' else random.choice(FRASES_DINAMICAS['sanidade_ok'])

    # --- MONTAGEM DO TEXTO ---
    parecer = f"🚦 **DASHBOARD OPERACIONAL:**\n"
    parecer += f"• Delta T (Pulverização): {hoje['delta_t']}°C ({'🟢 IDEAL' if 2<=hoje['delta_t']<=8 else '🔴 CUIDADO'})\n"
    parecer += f"• VPD (Transpiração): {hoje['vpd']} kPa\n"
    parecer += f"💡 {frase_vpd}\n\n"
    
    parecer += f"📝 **SEU REGISTRO DE CAMPO:**\n"
    parecer += f"• Nota: \"{anotacao_usuario}\"\n"
    parecer += f"📢 **CONSULTORIA & FARMÁCIA:**\n{analise_gatilho}\n\n"

    parecer += f"🍄 **SANIDADE & MOLHAMENTO:**\n"
    parecer += f"• Risco Fúngico: {risco_sanidade} ({horas_molhamento} janelas de orvalho)\n"
    parecer += f"💡 {frase_sanidade}\n\n"

    gda_total = dias_campo * 14.8 
    progresso = min(round((gda_total / GDA_ALVO_COLHEITA) * 100, 1), 100)
    
    parecer += f"🧬 **FISIOLOGIA:**\n"
    parecer += f"• Idade: {dias_campo} dias | Safra: {progresso}% concluída\n"
    parecer += f"🛒 **NUTRIÇÃO SUGERIDA:** "
    if dias_campo < 90: parecer += "Foco em **Raiz e Estrutura** (P + Ca)."
    elif dias_campo < 180: parecer += "Foco em **Vegetação** (N + Mg)."
    else: parecer += "Foco em **Fruto e Brix** (K + B)."
    parecer += "\n\n"

    parecer += f"💧 **HÍDRICO:** Repor {total_etc:.1f} mm esta semana (ETc).\n"
    
    parecer += "------------------------------------------------------------\n"
    parecer += f"{conclusao_final}\n"

    return parecer, conclusao_final

# --- 6. EXECUÇÃO ---

def get_agro_data_ultimate():
    url = f"https://api.openweathermap.org/data/2.5/forecast?q={CIDADE}&appid={OPENWEATHER_API_KEY}&units=metric&lang=pt_br"
    try:
        response = requests.get(url); response.raise_for_status()
        data = response.json()
    except: return []

    previsoes = []
    for i in range(0, min(40, len(data['list'])), 8):
        item = data['list'][i]
        t, u = item['main']['temp'], item['main']['humidity']
        dt, vpd = calcular_delta_t_e_vpd(t, u)
        et0 = 0.0023 * (t + 17.8) * (t ** 0.5) * 0.408
        chuva = sum([data['list'][i+j].get('rain', {}).get('3h', 0) for j in range(8) if i+j < len(data['list'])])
        
        previsoes.append({'data': datetime.fromtimestamp(item['dt']).strftime('%d/%m'), 'temp': t, 'umidade': u, 'vpd': vpd, 'delta_t': dt, 'vento': item['wind']['speed']*3.6, 'chuva': round(chuva, 1), 'et0': round(et0, 2)})
    return previsoes

def registrar_log_master(previsoes, anotacao, conclusao):
    arquivo = 'caderno_de_campo_master.csv'
    data_br = datetime.now(FUSO_BRASIL).strftime('%d/%m/%Y')
    try:
        with open(arquivo, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            if not os.path.isfile(arquivo): writer.writerow(['Data', 'Temp', 'VPD', 'Manejo', 'Parecer'])
            writer.writerow([data_br, previsoes[0]['temp'], previsoes[0]['vpd'], anotacao, conclusao.replace("\n", " ")])
    except: pass

def enviar_email(conteudo):
    msg = EmailMessage()
    msg.set_content(conteudo)
    msg['Subject'] = f"💎 RELATÓRIO AGRO-INTEL: {datetime.now(FUSO_BRASIL).strftime('%d/%m')}"
    msg['From'] = EMAIL_DESTINO
    msg['To'] = EMAIL_DESTINO
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(EMAIL_DESTINO, GMAIL_PASSWORD)
            smtp.send_message(msg)
        print("✅ E-mail enviado!")
    except Exception as e: print(e)

if __name__ == "__main__":
    previsoes = get_agro_data_ultimate()
    if previsoes:
        anotacao = ler_atividades_usuario()
        analise, conclusao = analisar_expert_educativo(previsoes, anotacao)
        
        corpo = f"💎 CONSULTORIA AGRO-INTEL PREMIUM: IBICOARA/BA\n📅 {datetime.now(FUSO_BRASIL).strftime('%d/%m/%Y %H:%M')}\n"
        corpo += "-"*60 + "\n📈 PREVISÃO 5 DIAS:\n"
        for p in previsoes: corpo += f"{p['data']} | {p['temp']}°C | Chuva: {p['chuva']}mm | ETc: {round(p['et0']*KC_ATUAL,2)}mm\n"
        corpo += f"\n{analise}"
        
        enviar_email(corpo)
        registrar_log_master(previsoes, anotacao, conclusao)
