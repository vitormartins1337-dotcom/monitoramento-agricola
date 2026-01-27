import requests
import os
import smtplib
import math
from datetime import datetime
from email.message import EmailMessage

# --- CONFIGURAÇÕES DE PLANTIO (AJUSTE SE NECESSÁRIO) ---
DATA_PLANTIO = datetime(2025, 11, 25) # Final de Novembro
T_BASE_BERRIES = 10.0 # Temperatura base para crescimento

# CONFIGURAÇÕES DE API E EMAIL
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_KEY")
GMAIL_PASSWORD = os.getenv("GMAIL_PASSWORD")
EMAIL_DESTINO = "vitormartins1337@gmail.com"
CIDADE = "Ibicoara, BR"

def calcular_gda(temp_media):
    """Calcula Graus-Dia Acumulados do dia."""
    gda = temp_media - T_BASE_BERRIES
    return max(gda, 0)

def analisar_fisiologia(temp_hoje):
    dias_campo = (datetime.now() - DATA_PLANTIO).days
    gda_hoje = calcular_gda(temp_hoje)
    
    parecer = f"🧬 ANÁLISE FISIOLÓGICA (Ciclo de Vida):\n"
    parecer += f"• Idade da Cultura: {dias_campo} dias desde o plantio.\n"
    
    if dias_campo < 90:
        fase = "Estabelecimento Radicular / Crescimento Vegetativo Inicial"
        dica = "Foco em fósforo e manutenção de umidade constante para expansão de raízes."
    elif dias_campo < 180:
        fase = "Desenvolvimento de Ramos e Dossel Foliar"
        dica = "Atenção ao nitrogênio e controle de pragas foliares."
    else:
        fase = "Maturação / Indução Reprodutiva"
        dica = "Equilíbrio de Potássio e monitoramento de pragas de fruto."

    parecer += f"• Fase Estimada: {fase}\n"
    parecer += f"• Energia Térmica (GDA de hoje): {gda_hoje:.1f} unidades de calor.\n"
    parecer += f"💡 CONSULTORIA: {dica}\n\n"
    return parecer

def calcular_delta_t_e_vpd(temp, umidade):
    es = 0.61078 * math.exp((17.27 * temp) / (temp + 237.3))
    ea = es * (umidade / 100)
    vpd = round(es - ea, 2)
    tw = temp * math.atan(0.151977 * (umidade + 8.313659)**0.5) + \
         math.atan(temp + umidade) - math.atan(umidade - 1.676331) + \
         0.00391838 * (umidade)**1.5 * math.atan(0.023101 * umidade) - 4.686035
    delta_t = round(temp - tw, 1)
    return delta_t, vpd

def analisar_premium_fisiologico(previsoes):
    hoje = previsoes[0]
    total_chuva = sum(p['chuva'] for p in previsoes)
    total_et0 = sum(p['et0'] for p in previsoes)
    balanco = total_chuva - total_et0
    
    # 1. Dashboard Operacional
    status_pulv = "🟢 IDEAL" if 2 <= hoje['delta_t'] <= 8 else ("🟡 ALERTA" if hoje['delta_t'] < 2 else "🔴 CRÍTICO")
    status_hidr = "🟢 OK" if -5 < balanco < 5 else ("🔴 CRÍTICO" if balanco < -15 else "🟡 REVISAR")
    
    parecer = f"🚦 DASHBOARD OPERACIONAL:\n"
    parecer += f"• Pulverização: {status_pulv} | Irrigação: {status_hidr}\n\n"
    
    # 2. Fisiologia e Tempo de Campo
    parecer += analisar_fisiologia(hoje['temp'])
    
    # 3. Conforto Planta (VPD)
    parecer += f"🌿 CONFORTO TÉRMICO (VPD):\n"
    parecer += f"• VPD Atual: {hoje['vpd']} kPa\n"
    if 0.45 <= hoje['vpd'] <= 1.25:
        parecer += "💡 ANÁLISE: Conforto ideal. Planta em plena atividade metabólica.\n"
    else:
        parecer += "💡 ANÁLISE: Estresse detectado. Planta priorizando sobrevivência em vez de crescimento.\n"

    # 4. Logística de Colheita
    parecer += f"\n🧺 LOGÍSTICA DE COLHEITA:\n"
    if previsoes[1]['chuva'] > 2:
        parecer += f"⚠️ PREVENÇÃO: Chuva prevista para amanhã. Proteja a qualidade do fruto hoje.\n"
    else:
        parecer += "✅ QUALIDADE: Janela favorável para firmeza e brix.\n"

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
    
    analise = analisar_premium_fisiologico(previsoes_diarias)
    corpo = f"💎 INTELIGÊNCIA AGRO-FISIOLÓGICA: IBICOARA/BA\n"
    corpo += f"📅 {datetime.now().strftime('%d/%m %H:%M')}\n"
    corpo += "------------------------------------------\n"
    corpo += "📈 RESUMO DIÁRIO:\n"
    corpo += "DATA  | TEMP  | CHUVA  | UR% | ET0\n"
    for p in previsoes_diarias:
        corpo += f"{p['data']} | {p['temp']}°C | {p['chuva']}mm | {p['umidade']}% | {p['et0']}mm\n"
    
    corpo += f"\n{analise}"
    return corpo

def enviar_email(conteudo):
    msg = EmailMessage()
    msg.set_content(conteudo)
    msg['Subject'] = f"🚀 DASHBOARD FISIOLÓGICO: {datetime.now().strftime('%d/%m')}"
    msg['From'] = EMAIL_DESTINO
    msg['To'] = EMAIL_DESTINO
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(EMAIL_DESTINO, GMAIL_PASSWORD)
        smtp.send_message(msg)

if __name__ == "__main__":
    relatorio = get_agro_data_ultimate()
    enviar_email(relatorio)
    print("✅ Sistema Fisiológico Premium Ativado!")
