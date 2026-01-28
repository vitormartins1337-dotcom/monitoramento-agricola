import requests
import os
import smtplib
import math
import csv
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage

# --- 1. CONFIGURAÇÕES ---
DATA_PLANTIO = datetime(2025, 11, 25) 
T_BASE_BERRIES = 10.0 
KC_ATUAL = 0.75 # Coeficiente da cultura atual
FUSO_BRASIL = timezone(timedelta(hours=-3))
CIDADE = "Ibicoara, BR"

# Segredos
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_KEY")
GMAIL_PASSWORD = os.getenv("GMAIL_PASSWORD")
EMAIL_DESTINO = "vitormartins1337@gmail.com"

# --- 2. BANCO DE DADOS TÉCNICO ---
FARMACIA_AGRO = {
    'botrytis': "💊 **TRATAMENTO (Botrytis):** *Fludioxonil*, *Ciprodinil* ou *Bacillus subtilis*.",
    'antracnose': "💊 **TRATAMENTO (Antracnose):** *Azoxistrobina* + *Difenoconazol*.",
    'ferrugem': "💊 **TRATAMENTO (Ferrugem):** *Tebuconazol*.",
    'ácaro': "💊 **TRATAMENTO (Ácaros):** *Abamectina* ou *Espirodiclofeno*."
}

# --- 3. CÁLCULOS ---
def calcular_delta_t_e_vpd(temp, umidade):
    es = 0.61078 * math.exp((17.27 * temp) / (temp + 237.3))
    ea = es * (umidade / 100)
    vpd = round(es - ea, 2)
    tw = temp * math.atan(0.151977 * (umidade + 8.313659)**0.5) + \
         math.atan(temp + umidade) - math.atan(umidade - 1.676331) + \
         0.00391838 * (umidade)**1.5 * math.atan(0.023101 * umidade) - 4.686035
    delta_t = round(temp - tw, 1)
    return delta_t, vpd

# --- 4. LEITURA ---
def ler_atividades_usuario():
    arquivo_input = 'input_atividades.txt'
    if os.path.exists(arquivo_input):
        with open(arquivo_input, 'r', encoding='utf-8') as f:
            conteudo = f.read().strip()
        if conteudo and conteudo != "Início do caderno de campo":
            with open(arquivo_input, 'w', encoding='utf-8') as f: f.write("")
            return conteudo
    return ""

# --- 5. O NOVO CÉREBRO (REVISOR ESTRATÉGICO) ---
def revisor_estrategico(vpd, chuva_sensor, texto_usuario, dias_campo):
    texto = texto_usuario.lower()
    conclusao = ""
    status_icon = "🟢"

    # CRITÉRIOS DE DECISÃO
    usuario_relatou_chuva = any(p in texto for p in ["chuva", "água", "molhou"])
    usuario_adubou = any(p in texto for p in ["adubo", "fertirrigação", "nitrato", "cálcio"])
    tem_praga = any(p in texto for p in FARMACIA_AGRO.keys())
    vpd_critico_baixo = vpd < 0.4
    vpd_critico_alto = vpd > 1.4
    solo_saturado = chuva_sensor > 5.0 or usuario_relatou_chuva

    # --- LÓGICA DE CRUZAMENTO DE DADOS ---

    # CENÁRIO 1: O "Desperdício" (Adubou + Solo Saturado ou VPD Baixo)
    if usuario_adubou:
        if solo_saturado:
            status_icon = "🔴"
            conclusao = "⚠️ **ERRO ESTRATÉGICO DETECTADO:** Você realizou fertirrigação em condições de solo saturado (chuva). \n"
            conclusao += "   • **Diagnóstico:** Ocorre lixiviação (perda) de nutrientes e anoxia radicular.\n"
            conclusao += "   • **Ação:** Não irrigue amanhã. Monitore sinais de deficiência nos próximos 3 dias."
        elif vpd_critico_baixo:
            status_icon = "🟡"
            conclusao = "⚠️ **ALERTA DE INEFICIÊNCIA:** Você nutriu a planta, mas o VPD está muito baixo (<0.4). \n"
            conclusao += "   • **Diagnóstico:** Sem transpiração, o Cálcio aplicado não subirá para o fruto. O produto ficará acumulado no solo.\n"
            conclusao += "   • **Ação:** Em dias nublados assim, prefira adubação foliar, não via solo."
        else:
            status_icon = "✅"
            conclusao = "✅ **MANEJO ASSERTIVO:** A adubação foi feita em janela fisiológica favorável. A planta absorverá o máximo do produto."

    # CENÁRIO 2: O "Perigo Silencioso" (Não fez nada, mas o clima está perigoso)
    elif not usuario_adubou and not tem_praga:
        if vpd_critico_baixo:
            status_icon = "⛔"
            conclusao = "🛑 **DIRETRIZ DE BLOQUEIO:** O ar está saturado (VPD Baixo). A planta desligou o metabolismo.\n"
            conclusao += "   • **Ordem do Dia:** NÃO IRRIGUE hoje. A planta não tem capacidade de puxar água. Risco de afogamento da raiz."
        elif vpd_critico_alto:
            status_icon = "🔥"
            conclusao = "🔥 **ALERTA TÉRMICO:** Ar extremamente seco. A planta fechou estômatos para defesa.\n"
            conclusao += "   • **Ordem do Dia:** Irrigação pulsada (curta e frequente) apenas para resfriar a lavoura (Climatização)."
        elif solo_saturado:
             status_icon = "🌧️"
             conclusao = "🌧️ **MODO DRENAGEM:** O solo recebeu muita água. A prioridade hoje é oxigenar a raiz. Mantenha os canais de drenagem limpos."
        else:
            conclusao = "✅ **OPERAÇÃO PADRÃO:** Condições climáticas estáveis. Siga o cronograma de manejo preventivo."

    # CENÁRIO 3: Sanidade (Pragas relatadas)
    if tem_praga:
        status_icon = "🍄"
        conclusao = "🛡️ **ALERTA FITOSSANITÁRIO:** Detecção de praga no relato. \n"
        for p, t in FARMACIA_AGRO.items():
            if p in texto: conclusao += f"   • {t}\n"
        conclusao += "   • **Atenção:** Verifique o Delta T antes de aplicar."

    return f"{status_icon} {conclusao}"

# --- 6. GERAÇÃO DO RELATÓRIO ---
def gerar_relatorio_final(previsoes, anotacao_usuario):
    hoje = previsoes[0]
    dias_campo = (datetime.now(FUSO_BRASIL).date() - DATA_PLANTIO.date()).days
    
    # --- AQUI ACONTECE A MÁGICA DA SÍNTESE ---
    sintese_cruzada = revisor_estrategico(hoje['vpd'], hoje['chuva'], anotacao_usuario, dias_campo)
    
    # Dados complementares
    gda_total = dias_campo * 14.8 
    horas_molhamento = sum(1 for p in previsoes if p['umidade'] > 88)
    
    # --- MONTAGEM DO E-MAIL ---
    parecer = f"🔎 **ANÁLISE ESTRATÉGICA CRUZADA (Conclusão Final):**\n"
    parecer += f"{sintese_cruzada}\n\n"
    
    parecer += f"📊 **DADOS TÉCNICOS DO DIA:**\n"
    parecer += f"• VPD: {hoje['vpd']} kPa | Delta T: {hoje['delta_t']}°C\n"
    parecer += f"• Diário de Campo: \"{anotacao_usuario if anotacao_usuario else 'Sem registros'}\"\n\n"

    # Ajuste de Fases (Corrigido para 45 dias)
    parecer += f"🧬 **ESTÁGIO FISIOLÓGICO ({dias_campo} dias):**\n"
    if dias_campo < 45:
        fase = "ENRAIZAMENTO"
        foco = "Fósforo (P) + Cálcio (Ca)"
        ciencia = "Energia (ATP) para raízes novas."
    elif dias_campo < 130:
        fase = "CRESCIMENTO VEGETATIVO"
        foco = "Nitrogênio (N) + Magnésio (Mg)"
        ciencia = "Expansão foliar e fotossíntese."
    else:
        fase = "FRUTIFICAÇÃO"
        foco = "Potássio (K) + Boro (B)"
        ciencia = "Enchimento de fruto e translocação."
        
    parecer += f"• Fase Atual: {fase}\n"
    parecer += f"• Nutrição Prioritária: **{foco}**\n"
    parecer += f"💡 *Por que?* {ciencia}\n\n"
    
    parecer += f"🍄 **RISCO SANITÁRIO:**\n"
    parecer += f"• {horas_molhamento} janelas de orvalho previstas. (Risco {'ALTO' if horas_molhamento > 2 else 'BAIXO'}).\n"
    
    return parecer

# --- 7. EXECUÇÃO ---
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
        previsoes.append({'data': datetime.fromtimestamp(item['dt']).strftime('%d/%m'), 'temp': t, 'umidade': u, 'vpd': vpd, 'delta_t': dt, 'chuva': round(chuva, 1), 'et0': round(et0, 2)})
    return previsoes

def enviar_email(conteudo):
    msg = EmailMessage()
    msg.set_content(conteudo)
    msg['Subject'] = f"💎 RELATÓRIO DE DECISÃO: {datetime.now(FUSO_BRASIL).strftime('%d/%m')}"
    msg['From'] = EMAIL_DESTINO
    msg['To'] = EMAIL_DESTINO
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(EMAIL_DESTINO, GMAIL_PASSWORD)
            smtp.send_message(msg)
            smtp.quit()
    except: pass

def registrar_log_master(previsoes, anotacao, parecer):
    arquivo = 'caderno_de_campo_master.csv'
    data_br = datetime.now(FUSO_BRASIL).strftime('%d/%m/%Y')
    try:
        with open(arquivo, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            if not os.path.isfile(arquivo): writer.writerow(['Data', 'Manejo', 'Decisao_Sistema'])
            writer.writerow([data_br, anotacao, parecer.split('\n')[1]]) # Salva a conclusão principal
    except: pass

if __name__ == "__main__":
    previsoes = get_agro_data_ultimate()
    if previsoes:
        anotacao = ler_atividades_usuario()
        corpo_email = gerar_relatorio_final(previsoes, anotacao)
        
        cabecalho = f"💎 CONSULTORIA AGRO-INTEL PREMIUM\n📅 {datetime.now(FUSO_BRASIL).strftime('%d/%m/%Y')}\n"
        cabecalho += "-"*60 + "\n"
        for p in previsoes:
            cabecalho += f"{p['data']} | {p['temp']}°C | 🌧️ {p['chuva']}mm | 💧 Consumo: {round(p['et0']*KC_ATUAL, 2)}mm\n"
        
        enviar_email(cabecalho + "\n" + corpo_email)
        registrar_log_master(previsoes, anotacao, corpo_email)
