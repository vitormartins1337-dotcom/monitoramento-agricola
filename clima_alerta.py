import requests
import os
import smtplib
import math
from datetime import datetime
from email.message import EmailMessage

# CONFIGURAÇÕES
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

def analisar_premium_expert(previsoes):
    hoje = previsoes[0]
    total_chuva = sum(p['chuva'] for p in previsoes)
    total_et0 = sum(p['et0'] for p in previsoes)
    balanco = total_chuva - total_et0
    
    # --- 1. DASHBOARD DE OPERAÇÃO ---
    status_pulv = "🟢 IDEAL" if 2 <= hoje['delta_t'] <= 8 else ("🟡 ALERTA" if hoje['delta_t'] < 2 else "🔴 CRÍTICO")
    status_hidr = "🟢 EQUILIBRADO" if -5 < balanco < 5 else ("🔴 CRÍTICO" if balanco < -15 else "🟡 REVISAR")
    
    parecer = f"🚦 DASHBOARD DE OPERAÇÃO:\n"
    parecer += f"• Pulverização: {status_pulv} | Irrigação: {status_hidr}\n"
    
    # Notas Técnicas do Dashboard
    parecer += f"📝 NOTA (PULV.): O status reflete a eficácia da gota. Delta T ideal (2-8) garante que a gota não evapore nem escorra.\n"
    
    if status_hidr != "🟢 EQUILIBRADO":
        msg_hidr = "DÉFICIT" if balanco < 0 else "EXCESSO"
        parecer += f"📝 NOTA (IRRIG.): Status {status_hidr} devido ao {msg_hidr} hídrico acumulado de {abs(balanco):.1f}mm previsto para a semana. Ajuste o turno de rega para evitar estresse ou lixiviação de nutrientes.\n\n"
    else:
        parecer += "📝 NOTA (IRRIG.): Balanço hídrico semanal estável. Mantenha o cronograma padrão.\n\n"
    
    # --- 2. VPD ---
    parecer += f"🌿 CONFORTO DA PLANTA (VPD):\n"
    parecer += f"• VPD Atual: {hoje['vpd']} kPa\n"
    if 0.45 <= hoje['vpd'] <= 1.25:
        parecer += "💡 ANÁLISE: Conforto Ideal. Máxima eficiência fotossintética e transporte de Cálcio e Boro.\n"
    elif hoje['vpd'] < 0.45:
        parecer += "💡 ANÁLISE: VPD Baixo. Planta 'travada' por excesso de umidade. Risco de Botrytis e deficiência induzida por falta de transpiração.\n"
    else:
        parecer += "💡 ANÁLISE: VPD Alto (Estresse). Planta fechando estômatos. Recomenda-se irrigação pulsada para baixar a temperatura do dossel.\n"

    # --- 3. LOGÍSTICA DE COLHEITA ---
    parecer += f"\n🧺 LOGÍSTICA DE COLHEITA (Berries):\n"
    chuva_amanha = previsoes[1]['chuva']
    if chuva_amanha > 2:
        parecer += f"⚠️ ATENÇÃO: Chuva de {chuva_amanha}mm amanhã. Antecipe colheita hoje para preservar o 'shelf-life' das frutas.\n"
    else:
        parecer += "✅ QUALIDADE: Janela seca favorável. Frutos com boa firmeza e concentração de açúcares (Brix).\n"

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
    
    analise = analisar_premium_expert(previsoes_diarias)
    corpo = f"💎 CONSULTORIA AGRO-INTEL PREMIUM: IBICOARA/BA\n"
    corpo += f"📅 Gerado em: {datetime.now().strftime('%d/%m %H:%M')}\n\n"
    
    corpo += "📈 RESUMO DIÁRIO (PRÓXIMOS 5 DIAS):\n"
    corpo += "DATA  | TEMP  | CHUVA  | UR% | ET0 (Perda)\n"
    corpo += "------------------------------------------\n"
    for p in previsoes_diarias:
        corpo += f"{p['data']} | {p['temp']}°C | {p['chuva']}mm | {p['umidade']}% | {p['et0']}mm/dia\n"
    
    corpo += f"\n{analise}"
    return corpo

def enviar_email(conteudo):
    msg = EmailMessage()
    msg.set_content(conteudo)
    msg['Subject'] = f"🚀 DASHBOARD OPERACIONAL: {datetime.now().strftime('%d/%m')}"
    msg['From'] = EMAIL_DESTINO
    msg['To'] = EMAIL_DESTINO
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(EMAIL_DESTINO, GMAIL_PASSWORD)
        smtp.send_message(msg)

if __name__ == "__main__":
    relatorio = get_agro_data_ultimate()
    enviar_email(relatorio)
    print("✅ Sistema Expert Atualizado!")
