import requests
import os
import smtplib
import math
import csv
import random
import google.generativeai as genai
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage

# --- 1. CONFIGURAÇÕES E INICIALIZAÇÃO ---
DATA_PLANTIO = datetime(2025, 11, 25) 
T_BASE_BERRIES = 10.0 
GDA_ALVO_COLHEITA = 1200 
KC_ATUAL = 0.75
FUSO_BRASIL = timezone(timedelta(hours=-3))
CIDADE = "Ibicoara, BR"

# Segredos
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_KEY")
GMAIL_PASSWORD = os.getenv("GMAIL_PASSWORD")
EMAIL_DESTINO = "vitormartins1337@gmail.com"
GEMINI_KEY = os.getenv("GEMINI_KEY")

# Configuração da IA
if GEMINI_KEY:
    genai.configure(api_key=GEMINI_KEY)
    model = genai.GenerativeModel('gemini-2.0-flash')

# --- 2. CÁLCULOS FÍSICOS ---
def calcular_delta_t_e_vpd(temp, umidade):
    es = 0.61078 * math.exp((17.27 * temp) / (temp + 237.3))
    ea = es * (umidade / 100)
    vpd = round(es - ea, 2)
    tw = temp * math.atan(0.151977 * (umidade + 8.313659)**0.5) + \
         math.atan(temp + umidade) - math.atan(umidade - 1.676331) + \
         0.00391838 * (umidade)**1.5 * math.atan(0.023101 * umidade) - 4.686035
    delta_t = round(temp - tw, 1)
    return delta_t, vpd

# --- 3. LEITURA DE ARQUIVO ---
def ler_atividades_usuario():
    arquivo_input = 'input_atividades.txt'
    if os.path.exists(arquivo_input):
        with open(arquivo_input, 'r', encoding='utf-8') as f:
            conteudo = f.read().strip()
        if conteudo and conteudo != "Início do caderno de campo":
            with open(arquivo_input, 'w', encoding='utf-8') as f: f.write("")
            return conteudo
    return "Nenhum manejo registrado hoje."

# --- 4. CÉREBRO DA IA (CONSULTORIA GENERATIVA) ---
def consultar_ia_agronomica(previsoes, anotacao_usuario, dias_campo):
    """
    Envia os dados climáticos e a nota do usuário para a IA.
    Retorna uma análise agronômica personalizada.
    """
    hoje = previsoes[0]
    
    # Prompt: As instruções que damos ao "Consultor Virtual"
    prompt = f"""
    Aja como um Engenheiro Agrônomo Sênior especialista em Berries (Mirtilo, Framboesa, Amora) na Chapada Diamantina/BA.
    
    DADOS DO DIA:
    - Data: {datetime.now(FUSO_BRASIL).strftime('%d/%m/%Y')}
    - Idade da Planta: {dias_campo} dias.
    - Previsão Hoje: {hoje['temp']}°C, Umidade {hoje['umidade']}%, Chuva Prevista: {hoje['chuva']}mm.
    - Indicadores Técnicos: VPD {hoje['vpd']} kPa, Delta T {hoje['delta_t']}°C.
    
    RELATO DO PRODUTOR (CAMPO):
    "{anotacao_usuario}"
    
    TAREFA:
    1. Analise o relato do produtor cruzando com os dados climáticos (ex: se ele aplicou algo, o VPD ajudou? Se choveu, há risco?).
    2. Se ele citou pragas/doenças, sugira Ingredientes Ativos (Farmácia) e manejo cultural.
    3. Se ele não citou nada, analise o VPD e Delta T e dê uma recomendação de manejo preventivo.
    4. Seja técnico mas didático. Use termos como "Lixiviação", "Translocação", "Sistêmico".
    5. Máximo de 6 linhas.
    """
    
    try:
        if not GEMINI_KEY: raise Exception("Sem chave IA")
        resposta = model.generate_content(prompt)
        return resposta.text
    except Exception as e:
        print(f"Erro na IA (usando backup): {e}")
        # BACKUP: Se a IA falhar, usamos a lógica antiga de palavras-chave
        return processar_gatilhos_backup(anotacao_usuario)

def processar_gatilhos_backup(texto):
    """Lógica antiga (Backup) caso a IA esteja fora do ar."""
    analise = ""
    texto = texto.lower()
    if any(p in texto for p in ["chuva", "água"]): analise += "⚠️ Alerta Hídrico: Risco de lixiviação e anoxia.\n"
    if any(p in texto for p in ["adubo", "nitrato"]): analise += "🧪 Nutrição: Monitore VPD para eficiência.\n"
    if not analise: analise = "✅ Operação nominal (Modo Offline)."
    return analise

# --- 5. GERAÇÃO DO RELATÓRIO ---
def analisar_expert_educativo(previsoes, anotacao_usuario):
    hoje = previsoes[0]
    total_etc = sum(p['et0'] * KC_ATUAL for p in previsoes)
    dias_campo = (datetime.now(FUSO_BRASIL).date() - DATA_PLANTIO.date()).days
    
    # *** AQUI ESTÁ A MÁGICA: CHAMAMOS A IA ***
    consultoria_ia = consultar_ia_agronomica(previsoes, anotacao_usuario, dias_campo)
    
    # Textos Científicos Fixos (Mantendo o que você gostou)
    txt_vpd = ""
    if hoje['vpd'] > 1.3: txt_vpd = "⚠️ **ANÁLISE FÍSICA:** O ar seco força o fechamento estomático. A planta economiza água, mas para de absorver CO2 e Cálcio (Risco de Tip Burn)."
    elif hoje['vpd'] < 0.4: txt_vpd = "⚠️ **ANÁLISE FÍSICA:** Ar saturado impede a transpiração. A 'bomba de sucção' do xilema desliga. Nutrientes móveis não sobem."
    else: txt_vpd = "✅ **ANÁLISE FÍSICA:** Condição termodinâmica ideal. Máxima eficiência na conversão de luz e nutrientes em biomassa."

    gda_total = dias_campo * 14.8 
    progresso = min(round((gda_total / GDA_ALVO_COLHEITA) * 100, 1), 100)

    # Montagem do E-mail
    parecer = f"🚦 **DASHBOARD TÉCNICO:**\n"
    parecer += f"• Delta T: {hoje['delta_t']}°C | VPD: {hoje['vpd']} kPa\n"
    parecer += f"{txt_vpd}\n\n"
    
    parecer += f"🤖 **CONSULTORIA IA (GEMINI):**\n"
    parecer += f"• **Sua Nota:** \"{anotacao_usuario}\"\n"
    parecer += f"• **Análise Inteligente:**\n{consultoria_ia}\n"
    
    parecer += f"🧬 **FISIOLOGIA (Relógio Térmico):**\n"
    parecer += f"• Idade: {dias_campo} dias | GDA Acumulado: {gda_total:.0f}\n"
    parecer += f"💡 **FUNDAMENTAÇÃO:** Monitoramos a soma térmica para prever os estádios fenológicos. A planta está convertendo {progresso}% do tempo em estrutura produtiva.\n\n"

    parecer += f"🛒 **NUTRIÇÃO MINERAL:**\n"
    if dias_campo < 90: parecer += "• Foco: **P + Ca** (ATP e Parede Celular)."
    elif dias_campo < 180: parecer += "• Foco: **N + Mg** (Proteína e Clorofila)."
    else: parecer += "• Foco: **K + B** (Translocação e Polinização)."
    parecer += "\n\n"

    parecer += f"💧 **HÍDRICO (ETc):** Repor {total_etc:.1f} mm esta semana.\n"
    
    return parecer, consultoria_ia

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

def registrar_log_master(previsoes, anotacao, conclusao_ia):
    arquivo = 'caderno_de_campo_master.csv'
    data_br = datetime.now(FUSO_BRASIL).strftime('%d/%m/%Y')
    try:
        with open(arquivo, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            if not os.path.isfile(arquivo): writer.writerow(['Data', 'Temp', 'VPD', 'Manejo_Usuario', 'Parecer_IA'])
            # Limpa quebras de linha da IA para salvar numa linha só do Excel
            parecer_limpo = conclusao_ia.replace("\n", " | ")
            writer.writerow([data_br, previsoes[0]['temp'], previsoes[0]['vpd'], anotacao, parecer_limpo])
    except: pass

def enviar_email(conteudo):
    msg = EmailMessage()
    msg.set_content(conteudo)
    msg['Subject'] = f"🤖 RELATÓRIO IA AGRO: {datetime.now(FUSO_BRASIL).strftime('%d/%m')}"
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
        analise, conclusao_ia = analisar_expert_educativo(previsoes, anotacao)
        
        corpo = f"💎 CONSULTORIA AGRO-INTEL + IA (GEMINI): IBICOARA/BA\n📅 {datetime.now(FUSO_BRASIL).strftime('%d/%m/%Y %H:%M')}\n"
        corpo += "-"*60 + "\n📈 PREVISÃO 5 DIAS:\n"
        for p in previsoes: corpo += f"{p['data']} | {p['temp']}°C | Chuva: {p['chuva']}mm | ETc: {round(p['et0']*KC_ATUAL,2)}mm\n"
        corpo += f"\n{analise}"
        
        enviar_email(corpo)
        registrar_log_master(previsoes, anotacao, conclusao_ia)
