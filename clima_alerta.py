import requests
import os
import smtplib
import math
import csv
import random
import google.generativeai as genai
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage

# --- 1. CONFIGURAÇÕES E FUSO HORÁRIO ---
DATA_PLANTIO = datetime(2025, 11, 25) 
T_BASE_BERRIES = 10.0 
GDA_ALVO_COLHEITA = 1200 
KC_ATUAL = 0.75
FUSO_BRASIL = timezone(timedelta(hours=-3))
CIDADE = "Ibicoara, BR"

# Segredos
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_KEY")
GMAIL_PASSWORD = os.getenv("GMAIL_PASSWORD")
EMAIL_DESTINO = "vitormartins1337.com"
GEMINI_KEY = os.getenv("GEMINI_KEY")

# Configuração da IA (Blindada contra erros de ferramenta)
if GEMINI_KEY:
    genai.configure(api_key=GEMINI_KEY)
    model = genai.GenerativeModel('gemini-2.0-flash')

# --- 2. BANCO DE CONHECIMENTO CIENTÍFICO (FIXO) ---
FRASES_VPD = {
    'alto': "⚠️ **ANÁLISE FÍSICA (VPD ALTO):** A atmosfera está drenando água excessivamente. Para evitar cavitação no xilema, a planta fechou os estômatos. Consequência: Interrupção imediata da fotossíntese e travamento da absorção de Cálcio (risco de Tip Burn).",
    'baixo': "⚠️ **ANÁLISE FÍSICA (VPD BAIXO):** O ar saturado desligou a 'bomba hidráulica' da planta. Sem transpiração, não há fluxo de massa, ou seja, os nutrientes do solo não sobem para as folhas. Risco elevado de gutação e doenças.",
    'ideal': "✅ **ANÁLISE FÍSICA (VPD IDEAL):** Termodinâmica perfeita. A planta opera com máxima condutância estomática, transpirando e fixando carbono simultaneamente. É o momento de maior eficiência no uso da água e fertilizantes."
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

# --- 4. LEITURA E INTELIGÊNCIA ---
def ler_atividades_usuario():
    arquivo_input = 'input_atividades.txt'
    if os.path.exists(arquivo_input):
        with open(arquivo_input, 'r', encoding='utf-8') as f:
            conteudo = f.read().strip()
        if conteudo and conteudo != "Início do caderno de campo":
            with open(arquivo_input, 'w', encoding='utf-8') as f: f.write("")
            return conteudo
    return "Nenhum manejo registrado hoje."

def consultar_ia_agronomica(previsoes, anotacao_usuario, dias_campo):
    """
    Gera o parecer técnico usando a lógica da IA, 
    mas sem ferramentas externas para evitar erros de API.
    """
    hoje = previsoes[0]
    
    prompt = f"""
    Aja como um Engenheiro Agrônomo Sênior especialista em Frutas Vermelhas na Chapada Diamantina.
    Analise os dados abaixo e forneça um parecer técnico de um parágrafo.
    
    DADOS TÉCNICOS:
    - VPD: {hoje['vpd']} kPa (Otimize a recomendação baseada nisso)
    - Delta T: {hoje['delta_t']}°C
    - Chuva Prevista: {hoje['chuva']}mm
    - Idade da Planta: {dias_campo} dias
    
    NOTA DO PRODUTOR: "{anotacao_usuario}"
    
    DIRETRIZES:
    1. Cruze a nota do produtor com o VPD/Chuva. (Ex: Se aplicou adubo e choveu, alerte sobre lixiviação).
    2. Se não houver nota, dê uma recomendação de manejo baseada no VPD atual.
    3. Seja formal, técnico e não mencione que você é uma IA. Assine como uma análise técnica.
    """
    
    try:
        if not GEMINI_KEY: raise Exception("Offline")
        # Removido o tools='google_search' para garantir estabilidade total
        resposta = model.generate_content(prompt)
        return resposta.text
    except Exception as e:
        return "Operação nominal. Siga o manejo preventivo padrão baseado nos indicadores climáticos."

# --- 5. GERAÇÃO DO RELATÓRIO PROFISSIONAL ---
def analisar_expert_educativo(previsoes, anotacao_usuario):
    hoje = previsoes[0]
    total_etc = sum(p['et0'] * KC_ATUAL for p in previsoes)
    dias_campo = (datetime.now(FUSO_BRASIL).date() - DATA_PLANTIO.date()).days
    
    # Chama a IA (Modo Raciocínio Puro)
    parecer_dinamico = consultar_ia_agronomica(previsoes, anotacao_usuario, dias_campo)
    
    # Lógica Científica Fixa (VPD)
    if hoje['vpd'] > 1.3: txt_vpd = FRASES_VPD['alto']
    elif hoje['vpd'] < 0.4: txt_vpd = FRASES_VPD['baixo']
    else: txt_vpd = FRASES_VPD['ideal']

    gda_total = dias_campo * 14.8 
    gda_hoje = max(hoje['temp'] - T_BASE_BERRIES, 0)

    # Monitoramento de Orvalho
    horas_molhamento = sum(1 for p in previsoes if p['umidade'] > 88 and p['vento'] < 6)
    risco_sanidade = 'ALTO' if horas_molhamento > 2 else 'BAIXO'

    # --- MONTAGEM DO E-MAIL (Layout Premium) ---
    parecer = f"🚦 **DASHBOARD OPERACIONAL:**\n"
    parecer += f"• Delta T (Aplicação): {hoje['delta_t']}°C | VPD (Transpiração): {hoje['vpd']} kPa\n"
    parecer += f"{txt_vpd}\n\n"
    
    parecer += f"📝 **REGISTRO DE CAMPO & ANÁLISE:**\n"
    parecer += f"• Seu Relato: \"{anotacao_usuario}\"\n"
    parecer += f"👨‍🔬 **PARECER TÉCNICO DO ENGENHEIRO:**\n{parecer_dinamico}\n\n"
    
    parecer += f"🍄 **MONITORAMENTO FITOSSANITÁRIO:**\n"
    parecer += f"• Risco Fúngico: {risco_sanidade} ({horas_molhamento} janelas de orvalho previstas)\n"
    parecer += f"💡 **FUNDAMENTAÇÃO:** Esporos de *Botrytis* e *Antracnose* dependem de água livre. O monitoramento de molhamento foliar é mais crítico que a chuva total, pois define o tempo de infecção.\n\n"

    parecer += f"🧬 **FISIOLOGIA (Relógio Térmico):**\n"
    parecer += f"• Idade Real: {dias_campo} dias | GDA Acumulado: {gda_total:.0f} (+{gda_hoje:.1f} hoje)\n"
    parecer += f"💡 **FUNDAMENTAÇÃO:** Fenologia baseada em Soma Térmica. Estamos monitorando a eficiência enzimática da planta em converter radiação e temperatura em biomassa produtiva.\n\n"

    parecer += f"🛒 **SUGESTÃO DE NUTRIÇÃO MINERAL:**\n"
    if dias_campo < 90:
        parecer += "• FASE: Estabelecimento Radicular.\n"
        parecer += "• FOCO: **Fósforo (P)** e **Cálcio (Ca)**.\n"
        parecer += "💡 **CIÊNCIA DO SOLO:** O Fósforo é o gerador de ATP (energia celular) vital para o enraizamento. O Cálcio forma os pectatos da lamela média, a 'cola' que dá firmeza às células e resistência a patógenos."
    elif dias_campo < 180:
        parecer += "• FASE: Crescimento Vegetativo.\n"
        parecer += "• FOCO: **Nitrogênio (N)** e **Magnésio (Mg)**.\n"
        parecer += "💡 **CIÊNCIA DO SOLO:** O Nitrogênio é o bloco construtor de aminoácidos e proteínas. O Magnésio é o átomo central da molécula de clorofila; sem ele, não há conversão de luz em energia."
    else:
        parecer += "• FASE: Enchimento e Maturação.\n"
        parecer += "• FOCO: **Potássio (K)** e **Boro (B)**.\n"
        parecer += "💡 **CIÊNCIA DO SOLO:** O Potássio atua como regulador osmótico e transportador de fotoassimilados (açúcar) da folha para o dreno (fruto). O Boro é crucial para a viabilidade do tubo polínico."
    parecer += "\n\n"

    parecer += f"💧 **MANEJO HÍDRICO DE PRECISÃO:**\n"
    parecer += f"• Reposição Real (ETc): {total_etc:.1f} mm para a semana.\n"
    parecer += f"💡 **EXPLICAÇÃO:** Este valor considera a evaporação do ambiente cruzada com o coeficiente biológico (Kc) da sua cultura na fase atual.\n"
    
    return parecer, parecer_dinamico

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

def registrar_log_master(previsoes, anotacao, parecer_dinamico):
    arquivo = 'caderno_de_campo_master.csv'
    data_br = datetime.now(FUSO_BRASIL).strftime('%d/%m/%Y')
    try:
        with open(arquivo, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            if not os.path.isfile(arquivo): writer.writerow(['Data', 'Temp', 'VPD', 'Manejo_Usuario', 'Parecer_Tecnico'])
            parecer_limpo = parecer_dinamico.replace("\n", " | ")
            writer.writerow([data_br, previsoes[0]['temp'], previsoes[0]['vpd'], anotacao, parecer_limpo])
    except: pass

def enviar_email(conteudo):
    msg = EmailMessage()
    msg.set_content(conteudo)
    msg['Subject'] = f"💎 RELATÓRIO TÉCNICO DIÁRIO: {datetime.now(FUSO_BRASIL).strftime('%d/%m')}"
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
        analise, parecer_ia = analisar_expert_educativo(previsoes, anotacao)
        
        corpo = f"💎 CONSULTORIA AGRO-INTEL PREMIUM: IBICOARA/BA\n📅 {datetime.now(FUSO_BRASIL).strftime('%d/%m/%Y %H:%M')}\n"
        corpo += "-"*60 + "\n📈 PREVISÃO 5 DIAS (OPENWEATHER):\n"
        for p in previsoes: corpo += f"{p['data']} | {p['temp']}°C | Chuva: {p['chuva']}mm | ETc: {round(p['et0']*KC_ATUAL,2)}mm\n"
        corpo += f"\n{analise}"
        
        enviar_email(corpo)
        registrar_log_master(previsoes, anotacao, parecer_ia)
