import requests
import os
import smtplib
import math
import csv
import random
import google.generativeai as genai
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage

# --- 1. CONFIGURAÇÕES ---
DATA_PLANTIO = datetime(2025, 11, 25) 
KC_ATUAL = 0.75
FUSO_BRASIL = timezone(timedelta(hours=-3))
CIDADE = "Ibicoara, BR"

# Segredos
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_KEY")
GMAIL_PASSWORD = os.getenv("GMAIL_PASSWORD")
EMAIL_DESTINO = "vitormartins1337@gmail.com"
GEMINI_KEY = os.getenv("GEMINI_KEY")

# Configuração IA (Usando versão estável 1.5-flash)
MODELO_IA = None
if GEMINI_KEY:
    try:
        genai.configure(api_key=GEMINI_KEY)
        MODELO_IA = genai.GenerativeModel('gemini-1.5-flash')
    except:
        print("Erro ao configurar IA.")

# --- 2. MOTOR DE BACKUP (GATILHOS CLÁSSICOS) ---
# Se a IA falhar, usamos isso aqui para não ficar "fraco"
def backup_inteligencia_classica(texto):
    texto = texto.lower()
    analise = "⚠️ **ANÁLISE DE BACKUP (IA OFFLINE):**\n"
    
    if any(p in texto for p in ["chuva", "água", "molhou"]):
        analise += "• Você relatou chuva não prevista. Isso anula o dado do sensor. Risco Imediato: Lixiviação de Nitrogênio/Potássio e Anoxia (falta de ar na raiz).\n"
    
    if any(p in texto for p in ["adubo", "fertirrigação", "cálcio"]):
        analise += "• Sobre a nutrição: Se choveu muito após a aplicação, considere que parte foi perdida (lavada). Monitore sinais de deficiência nos próximos 3 dias.\n"
        
    if "não" in texto and "fertirrigação" in texto:
        analise += "• Decisão correta de suspender a fertirrigação. Com o solo encharcado, a planta não absorveria e apenas salinizaria o solo.\n"

    if analise == "⚠️ **ANÁLISE DE BACKUP (IA OFFLINE):**\n":
        return "Operação nominal. Acompanhe o VPD."
    return analise

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
    return "Nenhum manejo registrado hoje."

# --- 5. INTELIGÊNCIA HÍBRIDA ---
def consultar_ia_agronomica(previsoes, anotacao_usuario, dias_campo):
    hoje = previsoes[0]
    
    # Prompt agressivo para confiar no usuário
    prompt = f"""
    Você é um Engenheiro Agrônomo Sênior.
    
    CONFLITO DE DADOS (IMPORTANTE):
    - O sensor diz: Chuva {hoje['chuva']}mm.
    - O produtor diz: "{anotacao_usuario}"
    
    ORDEM: Se o produtor disse que choveu, IGNORE o sensor e considere CHUVA FORTE.
    
    TAREFA:
    Analise a situação. Se choveu e ele não fertirrigou, parabenize a decisão técnica (evitou lixiviação).
    Se ele aplicou algo e choveu, avise do prejuízo.
    Explique tecnicamente (lixiviação, anoxia, VPD).
    Seja curto e direto.
    """
    
    try:
        if not MODELO_IA: raise Exception("IA não configurada")
        resposta = MODELO_IA.generate_content(prompt)
        return resposta.text
    except Exception as e:
        print(f"⚠️ FALHA NA IA: {e} -> Usando Backup Clássico.")
        # AQUI ESTÁ A CORREÇÃO: Chama o backup inteligente em vez da frase vazia
        return backup_inteligencia_classica(anotacao_usuario)

# --- 6. RELATÓRIO ---
def analisar_expert_educativo(previsoes, anotacao_usuario):
    hoje = previsoes[0]
    total_etc = sum(p['et0'] * KC_ATUAL for p in previsoes)
    dias_campo = (datetime.now(FUSO_BRASIL).date() - DATA_PLANTIO.date()).days
    
    parecer_dinamico = consultar_ia_agronomica(previsoes, anotacao_usuario, dias_campo)
    
    # Frases VPD Fixas
    if hoje['vpd'] > 1.3: txt_vpd = "⚠️ **ANÁLISE FÍSICA (VPD ALTO):** Ar seco. Fechamento estomático. Risco de Tip Burn (falta de Ca)."
    elif hoje['vpd'] < 0.4: txt_vpd = "⚠️ **ANÁLISE FÍSICA (VPD BAIXO):** Ar saturado. Planta não transpira. Nutriente não sobe. Risco de doenças."
    else: txt_vpd = "✅ **ANÁLISE FÍSICA (VPD IDEAL):** Máxima eficiência fotossintética e nutricional."

    gda_total = dias_campo * 14.8 
    horas_molhamento = sum(1 for p in previsoes if p['umidade'] > 88 and p['vento'] < 6)
    risco_sanidade = 'ALTO' if horas_molhamento > 2 else 'BAIXO'

    parecer = f"🚦 **DASHBOARD OPERACIONAL:**\n"
    parecer += f"• Delta T: {hoje['delta_t']}°C | VPD: {hoje['vpd']} kPa\n"
    parecer += f"{txt_vpd}\n\n"
    
    parecer += f"📝 **REGISTRO DE CAMPO & ANÁLISE:**\n"
    parecer += f"• Relato: \"{anotacao_usuario}\"\n"
    parecer += f"👨‍🔬 **PARECER TÉCNICO:**\n{parecer_dinamico}\n\n"
    
    parecer += f"🍄 **SANIDADE (Risco {risco_sanidade}):**\n"
    parecer += f"• {horas_molhamento} janelas de orvalho previstas. Esporos de *Botrytis* precisam de água livre.\n\n"

    parecer += f"🛒 **NUTRIÇÃO (Idade: {dias_campo} dias):**\n"
    if dias_campo < 90: parecer += "• Foco: **P + Ca** (Raiz e Parede Celular)."
    elif dias_campo < 180: parecer += "• Foco: **N + Mg** (Vegetação)."
    else: parecer += "• Foco: **K + B** (Fruto)."
    parecer += "\n\n"

    parecer += f"💧 **HÍDRICO:** Reposição de {total_etc:.1f} mm/semana (ETc).\n"
    
    return parecer, parecer_dinamico

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
        previsoes.append({'data': datetime.fromtimestamp(item['dt']).strftime('%d/%m'), 'temp': t, 'umidade': u, 'vpd': vpd, 'delta_t': dt, 'vento': item['wind']['speed']*3.6, 'chuva': round(chuva, 1), 'et0': round(et0, 2)})
    return previsoes

def registrar_log_master(previsoes, anotacao, parecer):
    arquivo = 'caderno_de_campo_master.csv'
    data_br = datetime.now(FUSO_BRASIL).strftime('%d/%m/%Y')
    try:
        with open(arquivo, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            if not os.path.isfile(arquivo): writer.writerow(['Data', 'Temp', 'VPD', 'Manejo', 'Parecer'])
            writer.writerow([data_br, previsoes[0]['temp'], previsoes[0]['vpd'], anotacao, parecer.replace("\n", " | ")])
    except: pass

def enviar_email(conteudo):
    msg = EmailMessage()
    msg.set_content(conteudo)
    msg['Subject'] = f"💎 RELATÓRIO TÉCNICO: {datetime.now(FUSO_BRASIL).strftime('%d/%m')}"
    msg['From'] = EMAIL_DESTINO
    msg['To'] = EMAIL_DESTINO
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(EMAIL_DESTINO, GMAIL_PASSWORD)
            smtp.send_message(msg)
            smtp.quit()
    except Exception as e: print(f"Erro Email: {e}")

if __name__ == "__main__":
    previsoes = get_agro_data_ultimate()
    if previsoes:
        anotacao = ler_atividades_usuario()
        analise, parecer = analisar_expert_educativo(previsoes, anotacao)
        
        corpo = f"💎 CONSULTORIA AGRO-INTEL PREMIUM: IBICOARA/BA\n📅 {datetime.now(FUSO_BRASIL).strftime('%d/%m/%Y %H:%M')}\n"
        corpo += "-"*60 + "\n📈 PREVISÃO (OPENWEATHER):\n"
        for p in previsoes: corpo += f"{p['data']} | {p['temp']}°C | Chuva: {p['chuva']}mm\n"
        corpo += f"\n{analise}"
        
        enviar_email(corpo)
        registrar_log_master(previsoes, anotacao, parecer)
