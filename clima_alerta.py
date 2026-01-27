import requests
import os
import smtplib
import math
from datetime import datetime
from email.message import EmailMessage

# --- CONFIGURAÇÕES DE PLANTIO ---
DATA_PLANTIO = datetime(2025, 11, 25) 
T_BASE_BERRIES = 10.0 

# CONFIGURAÇÕES DE API E EMAIL
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_KEY")
GMAIL_PASSWORD = os.getenv("GMAIL_PASSWORD")
EMAIL_DESTINO = "vitormartins1337@gmail.com"
CIDADE = "Ibicoara, BR"

def calcular_gda(temp_media):
    gda = temp_media - T_BASE_BERRIES
    return max(gda, 0)

def calcular_delta_t_e_vpd(temp, umidade):
    es = 0.61078 * math.exp((17.27 * temp) / (temp + 237.3))
    ea = es * (umidade / 100)
    vpd = round(es - ea, 2)
    tw = temp * math.atan(0.151977 * (umidade + 8.313659)**0.5) + \
         math.atan(temp + umidade) - math.atan(umidade - 1.676331) + \
         0.00391838 * (umidade)**1.5 * math.atan(0.023101 * umidade) - 4.686035
    delta_t = round(temp - tw, 1)
    return delta_t, vpd

def analisar_premium_explicativo(previsoes):
    hoje = previsoes[0]
    total_chuva = sum(p['chuva'] for p in previsoes)
    total_perda = sum(p['et0'] for p in previsoes)
    balanco = total_chuva - total_perda
    
    # 1. Dashboard Operacional
    status_pulv = "🟢 IDEAL" if 2 <= hoje['delta_t'] <= 8 else ("🟡 ALERTA" if hoje['delta_t'] < 2 else "🔴 CRÍTICO")
    status_hidr = "🟢 EQUILIBRADO" if -5 < balanco < 5 else ("🔴 CRÍTICO" if balanco < -15 else "🟡 REVISAR")
    
    parecer = f"🚦 DASHBOARD OPERACIONAL:\n"
    parecer += f"• Eficiência de Pulverização (Delta T): {status_pulv}\n"
    parecer += f"• Balanço de Irrigação (Semanal): {status_hidr}\n\n"
    
    # 2. Fisiologia
    dias_campo = (datetime.now() - DATA_PLANTIO).days
    gda_hoje = calcular_gda(hoje['temp'])
    parecer += f"🧬 DESENVOLVIMENTO DA PLANTA (Ciclo Fisiológico):\n"
    parecer += f"• Idade da Cultura: {dias_campo} dias no campo.\n"
    parecer += f"• Energia Térmica Diária: {gda_hoje:.1f} Graus-Dia (Calor útil acumulado hoje).\n"
    parecer += f"• Fase Atual Estimada: Estabelecimento Radicular / Crescimento Vegetativo.\n"
    parecer += f"💡 CONSULTORIA: Foco em nutrição fosfatada para expansão das raízes das Berries.\n\n"
    
    # 3. Conforto Planta (VPD)
    parecer += f"🌿 CONFORTO TÉRMICO E TRANSPIRAÇÃO:\n"
    parecer += f"• Déficit de Pressão de Vapor (VPD): {hoje['vpd']} kPa\n"
    if 0.45 <= hoje['vpd'] <= 1.25:
        parecer += "💡 ANÁLISE: Conforto ideal. A planta está 'trabalhando' e absorvendo nutrientes com eficiência máxima.\n"
    else:
        parecer += "💡 ANÁLISE: Estresse detectado. A planta está fechando os poros (estômatos) para evitar perda excessiva de água.\n"

    # 4. Logística de Colheita
    parecer += f"\n🧺 LOGÍSTICA DE COLHEITA:\n"
    if previsoes[1]['chuva'] > 2:
        parecer += f"⚠️ PREVENÇÃO: Chuva de {previsoes[1]['chuva']}mm prevista para amanhã. Colha os frutos maduros hoje.\n"
    else:
        parecer += "✅ QUALIDADE: Janela favorável para firmeza e doçura dos frutos (Brix).\n"

    return parecer

def get_agro_data_clear():
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
    
    analise = analisar_premium_explicativo(previsoes_diarias)
    corpo = f"💎 INTELIGÊNCIA AGRO-FISIOLÓGICA: IBICOARA/BA\n"
    corpo += f"📅 Relatório gerado em: {datetime.now().strftime('%d/%m %H:%M')}\n"
    corpo += "------------------------------------------------------------\n"
    corpo += "📈 RESUMO DIÁRIO (Próximos 5 dias):\n"
    corpo += "DATA  | TEMP | CHUVA | UMIDADE | PERDA DE ÁGUA (ET0)\n"
    for p in previsoes_diarias:
        corpo += f"{p['data']} | {p['temp']}°C | {p['chuva']}mm | {p['umidade']}% | {p['et0']}mm/dia\n"
    
    corpo += f"\n{analise}"
    return corpo

def enviar_email(conteudo):
    msg = EmailMessage()
    msg.set_content(conteudo)
    msg['Subject'] = f"🚀 DASHBOARD FISIOLÓGICO: {datetime.now().strftime('%d/%m')}"
    msg['From'] = EMAIL_DESTINO
    msg['To'] = EMAIL_DESTINO
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(EMAIL_DESTINO, os.getenv("GMAIL_PASSWORD"))
        smtp.send_message(msg)

if __name__ == "__main__":
    relatorio = get_agro_data_clear()
    enviar_email(relatorio)
    print("✅ Sistema com nomenclatura clara ativado!")
