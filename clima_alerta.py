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

def analisar_premium_com_explicacao(previsoes):
    hoje = previsoes[0]
    total_chuva = sum(p['chuva'] for p in previsoes)
    total_et0 = sum(p['et0'] for p in previsoes)
    
    # --- 1. DASHBOARD ---
    status_pulv = "🟢 IDEAL" if 2 <= hoje['delta_t'] <= 8 else ("🟡 ALERTA" if hoje['delta_t'] < 2 else "🔴 CRÍTICO")
    status_hidr = "🟢 OK" if -10 < (total_chuva - total_et0) < 10 else "🟡 REVISAR"
    
    parecer = f"🚦 DASHBOARD DE OPERAÇÃO:\n"
    parecer += f"• Pulverização: {status_pulv} | Irrigação: {status_hidr}\n"
    parecer += f"📝 NOTA: O status CRÍTICO em pulverização indica que o defensivo vai evaporar antes de agir (Delta T alto) ou escorrer (Delta T baixo).\n\n"
    
    # --- 2. VPD ---
    parecer += f"🌿 CONFORTO DA PLANTA (VPD):\n"
    parecer += f"• VPD Atual: {hoje['vpd']} kPa\n"
    if 0.45 <= hoje['vpd'] <= 1.25:
        parecer += "💡 ANÁLISE: Conforto ideal. A planta está com os estômatos abertos, transpirando e absorvendo nutrientes (cálcio/boro) via xilema.\n"
    elif hoje['vpd'] < 0.45:
        parecer += "💡 ANÁLISE: Ambiente muito saturado. A planta não consegue transpirar, o que reduz o transporte de nutrientes e favorece fungos foliares.\n"
    else:
        parecer += "💡 ANÁLISE: Estresse Hídrico Atmosférico. A planta fecha os estômatos para economizar água, parando a fotossíntese. Irrigar agora ajuda no resfriamento térmico.\n"

    # --- 3. LOGÍSTICA ---
    parecer += f"\n🧺 LOGÍSTICA DE COLHEITA (Berries):\n"
    chuva_amanha = previsoes[1]['chuva']
    if chuva_amanha > 2:
        parecer += f"⚠️ RISCO: Chuva prevista ({chuva_amanha}mm). A umidade no fruto durante a colheita reduz o 'shelf-life' (vida de prateleira) e favorece o mofo cinzento.\n"
    else:
        parecer += "✅ QUALIDADE: Janela seca. Ideal para manter a firmeza da casca e brix do fruto.\n"

    # --- 4. PLANO SEMANAL ---
    parecer += f"\n📅 PLANO DE AÇÃO SEMANAL (Tendência):\n"
    melhor_dia = min(previsoes, key=lambda x: x['vento'])
    parecer += f"• Operacional: Melhor dia para defensivos é {melhor_dia['data']} devido à estabilidade do vento.\n"
    parecer += f"• Hídrico: Perda total estimada (ET0) de {total_et0:.1f}mm contra {total_chuva:.1f}mm de chuva. "
    if total_et0 > total_chuva:
        parecer += "Planeje o bombeamento para repor o déficit acumulado."

    return parecer

def get_agro_data_educational():
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
            'chuva': sum([p.get('rain', {}).get('3h', 0) for p in data['list'][i:i+8]]),
            'et0': round(0.0023 * (t + 17.8) * (t ** 0.5) * 0.408, 2)
        })
    
    analise = analisar_premium_com_explicacao(previsoes_diarias)
    corpo = f"💎 CONSULTORIA AGRO-INTEL: IBICOARA/BA\n"
    corpo += f"📅 Gerado em: {datetime.now().strftime('%d/%m %H:%M')}\n\n"
    corpo += "📈 RESUMO 5 DIAS:\n"
    for p in previsoes_diarias:
        corpo += f"{p['data']}: {p['temp']}°C | Chuva: {p['chuva']:.1f}mm | UR: {p['umidade']}%\n"
    
    corpo += f"\n{analise}"
    return corpo

def enviar_email(conteudo):
    msg = EmailMessage()
    msg.set_content(conteudo)
    msg['Subject'] = f"🚀 DASHBOARD EDUCATIVO: {datetime.now().strftime('%d/%m')}"
    msg['From'] = EMAIL_DESTINO
    msg['To'] = EMAIL_DESTINO
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(EMAIL_DESTINO, GMAIL_PASSWORD)
        smtp.send_message(msg)

if __name__ == "__main__":
    relatorio = get_agro_data_educational()
    enviar_email(relatorio)
    print("✅ Sistema Educativo Enviado!")
