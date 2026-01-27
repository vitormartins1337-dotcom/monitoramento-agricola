import requests
import os
import smtplib
import math
import csv
from datetime import datetime
from email.message import EmailMessage

# --- CONFIGURAÇÕES DE CAMPO ---
DATA_PLANTIO = datetime(2025, 11, 25) 
T_BASE_BERRIES = 10.0 
GDA_ALVO_COLHEITA = 1200 
KC_ATUAL = 0.75          

# CONFIGURAÇÕES DE API E EMAIL
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_KEY")
GMAIL_PASSWORD = os.getenv("GMAIL_PASSWORD")
EMAIL_DESTINO = "vitormartins1337@gmail.com"
CIDADE = "Ibicoara, BR"

def calcular_delta_t_e_vpd(temp, umidade):
    es = 0.61078 * math.exp((17.27 * temp) / (temp + 237.3))
    ea = es * (umidade / 100)
    vpd = round(es - ea, 2)
    tw = temp * math.atan(0.151977 * (umidade + 8.313659)**0.5) + \
         math.atan(temp + umidade) - math.atan(umidade - 1.676331) + \
         0.00391838 * (umidade)**1.5 * math.atan(0.023101 * umidade) - 4.686035
    delta_t = round(temp - tw, 1)
    return delta_t, vpd

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
    """Analisa o texto do usuário e gera recomendações agronômicas baseadas em gatilhos"""
    analise_extra = ""
    texto = texto.lower()
    
    # Gatilho 1: Chuva (Lixiviação e Fungos)
    if "chuva" in texto or "chovendo" in texto or "volume" in texto:
        analise_extra += "⚠️ ALERTA DE LIXIVIAÇÃO: Chuvas volumosas podem lavar o Nitrogênio e Potássio da zona radicular. Monitore a condutividade elétrica (CE) do solo.\n"
        analise_extra += "⚠️ RISCO FITOSSANITÁRIO: O molhamento foliar real sobrepõe a previsão. Risco imediato para Botrytis e Antracnose nas Berries.\n"
    
    # Gatilho 2: Pragas/Doenças
    if any(palavra in texto for palavra in ["praga", "inseto", "mancha", "lagarta", "ácaro", "fungo"]):
        analise_extra += "🔍 MANEJO INTEGRADO (MIP): Identificada pressão biológica. Priorize aplicações com o Delta T em zona verde (2-8) para máxima penetração na calda.\n"
    
    # Gatilho 3: Fertirrigação
    if any(palavra in texto for palavra in ["fertilizante", "adubo", "fertirrigação", "nutriente", "map", "nitrato"]):
        analise_extra += "🧪 EFICIÊNCIA NUTRICIONAL: Nutrientes aplicados hoje. O aproveitamento dependerá do VPD e da umidade do solo. Evite saturação após a chuva.\n"

    return analise_extra if analise_extra else "✅ O manejo relatado está alinhado com a fase fisiológica atual."

def analisar_expert_educativo(previsoes, anotacao_usuario):
    hoje = previsoes[0]
    total_chuva = sum(p['chuva'] for p in previsoes)
    total_etc = sum(p['et0'] * KC_ATUAL for p in previsoes)
    balanco = total_chuva - total_etc
    
    # Executa a lógica de gatilhos sobre a anotação
    analise_gatilho = processar_gatilhos_inteligentes(anotacao_usuario)
    
    # Mantendo a estrutura anterior rigorosamente
    status_pulv = "🟢 IDEAL" if 2 <= hoje['delta_t'] <= 8 else ("🔴 CRÍTICO" if hoje['delta_t'] > 8 else "🟡 ALERTA")
    status_hidr = "🟢 OK" if -5 < balanco < 5 else ("🔴 DÉFICIT" if balanco < -10 else "🟡 REVISAR")
    
    parecer = f"🚦 DASHBOARD OPERACIONAL:\n"
    parecer += f"• Pulverização (Delta T): {status_pulv} | Irrigação: {status_hidr}\n"
    parecer += f"💡 EXPLICAÇÃO: Delta T ideal (2-8) garante que o defensivo não evapore nem escorra.\n\n"
    
    parecer += f"📝 SEU REGISTRO DE CAMPO (ANÁLISE DE GATILHOS):\n"
    parecer += f"• Sua nota: \"{anotacao_usuario}\"\n"
    parecer += f"📢 CONSULTORIA DINÂMICA:\n{analise_gatilho}\n\n"

    horas_molhamento = sum(1 for p in previsoes if p['umidade'] > 88 and p['vento'] < 6)
    parecer += f"🍄 MONITORAMENTO DE SANIDADE:\n• Índice de Molhamento Foliar: {'ALTO' if horas_molhamento > 2 else 'BAIXO'}\n"
    parecer += f"💡 EXPLICAÇÃO: Fungos precisam de umidade. Com o seu relato de chuva, a atenção deve ser redobrada.\n\n"

    dias_campo = (datetime.now() - DATA_PLANTIO).days
    gda_total = dias_campo * 14.8 
    progresso = min(round((gda_total / GDA_ALVO_COLHEITA) * 100, 1), 100)
    
    parecer += f"🧬 DESENVOLVIMENTO FISIOLÓGICO:\n"
    parecer += f"• Idade: {dias_campo} dias | Progresso: {progresso}%\n"
    parecer += f"💡 EXPLICAÇÃO: Planta acumulando energia térmica necessária para completar o ciclo.\n\n"
    
    parecer += f"🛒 SUGESTÃO DE FERTILIZAÇÃO MINERAL:\n"
    if dias_campo < 90: parecer += "• FASE: Estabelecimento. FOCO: Fósforo (P) e Cálcio (Ca).\n"
    elif dias_campo < 180: parecer += "• FASE: Crescimento. FOCO: Nitrogênio (N) e Magnésio (Mg).\n"
    else: parecer += "• FASE: Produção. FOCO: Potássio (K) e Boro (B).\n"
    parecer += "💡 EXPLICAÇÃO: Baseada na demanda nutricional da idade atual.\n\n"

    parecer += f"🌿 CONFORTO TÉRMICO (VPD):\n• Déficit de Pressão de Vapor: {hoje['vpd']} kPa.\n"
    parecer += f"💡 EXPLICAÇÃO: VPD em zona de conforto garante transporte de nutrientes via xilema.\n\n"

    parecer += f"💧 MANEJO HÍDRICO (Necessidade Real):\n• Consumo das Berries (ETc) para a semana: {total_etc:.1f} mm.\n"
    parecer += f"💡 EXPLICAÇÃO: ETc é a sede real da cultura ajustada pelo Kc.\n"

    return parecer

def get_agro_data_ultimate():
    url = f"https://api.openweathermap.org/data/2.5/forecast?q={CIDADE}&appid={OPENWEATHER_API_KEY}&units=metric&lang=pt_br"
    data = requests.get(url).json()
    previsoes_diarias = []
    for i in range(0, 40, 8):
        item = data['list'][i]
        t, u = item['main']['temp'], item['main']['humidity']
        dt, vpd = calcular_delta_t_e_vpd(t, u)
        previsoes_diarias.append({
            'data': datetime.fromtimestamp(item['dt']).strftime('%d/%m'),
            'temp': t, 'umidade': u, 'vpd': vpd, 'delta_t': dt,
            'vento': item['wind']['speed'] * 3.6,
            'chuva': round(sum([p.get('rain', {}).get('3h', 0) for p in data['list'][i:i+8]]), 1),
            'et0': round(0.0023 * (t + 17.8) * (t ** 0.5) * 0.408, 2)
        })
    return previsoes_diarias

def registrar_log_master(previsoes, anotacao):
    arquivo = 'caderno_de_campo_master.csv'
    existe = os.path.isfile(arquivo)
    with open(arquivo, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if not existe:
            writer.writerow(['Data', 'Temp_Med', 'VPD', 'Delta_T', 'Manejo_Realizado'])
        writer.writerow([datetime.now().strftime('%d/%m/%Y'), previsoes[0]['temp'], previsoes[0]['vpd'], previsoes[0]['delta_t'], anotacao])

def enviar_email(conteudo):
    msg = EmailMessage()
    msg.set_content(conteudo)
    msg['Subject'] = f"🚀 DASHBOARD INTELIGENTE: {datetime.now().strftime('%d/%m')}"
    msg['From'] = EMAIL_DESTINO
    msg['To'] = EMAIL_DESTINO
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(EMAIL_DESTINO, os.getenv("GMAIL_PASSWORD"))
        smtp.send_message(msg)

if __name__ == "__main__":
    previsoes = get_agro_data_ultimate()
    anotacao = ler_atividades_usuario()
    analise = analisar_expert_educativo(previsoes, anotacao)
    
    corpo = f"💎 CONSULTORIA AGRO-INTEL PREMIUM: IBICOARA/BA\n📅 Gerado: {datetime.now().strftime('%d/%m %H:%M')}\n"
    corpo += "------------------------------------------------------------\n"
    corpo += "📈 RESUMO 5 DIAS (TEMPO | CHUVA | CONSUMO PLANTA):\n"
    for p in previsoes:
        etc = round(p['et0'] * KC_ATUAL, 2)
        corpo += f"{p['data']} | {p['temp']}°C | {p['chuva']}mm | Consumo: {etc}mm/dia\n"
    corpo += f"\n{analise}"
    
    enviar_email(corpo)
    registrar_log_master(previsoes, anotacao)
    print("✅ Sistema rodou com Gatilhos Inteligentes!")
