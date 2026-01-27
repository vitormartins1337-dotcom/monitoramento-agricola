import requests
import os
import smtplib
import math
from datetime import datetime
from email.message import EmailMessage

# CONFIGURAÇÕES PROFISSIONAIS
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_KEY")
GMAIL_PASSWORD = os.getenv("GMAIL_PASSWORD")
EMAIL_DESTINO = "vitormartins1337@gmail.com"
CIDADE = "Ibicoara, BR"

def calcular_delta_t(temp, umidade):
    tw = temp * math.atan(0.151977 * (umidade + 8.313659)**0.5) + \
         math.atan(temp + umidade) - math.atan(umidade - 1.676331) + \
         0.00391838 * (umidade)**1.5 * math.atan(0.023101 * umidade) - 4.686035
    return round(temp - tw, 1)

def analisar_berries(previsoes):
    """Análise específica para Amora, Framboesa e Mirtilo."""
    hoje = previsoes[0]
    total_chuva_semana = sum(p['chuva'] for p in previsoes)
    delta_t = calcular_delta_t(hoje['temp'], hoje['umidade'])
    
    parecer = f"🍓 ESTRATÉGIA PARA FRUTAS VERMELHAS (Berries):\n"
    
    # 1. Alerta de Doenças (Botrytis e Antracnose)
    risco_fungo = any(p['umidade'] > 85 and 15 <= p['temp'] <= 24 for p in previsoes)
    if risco_fungo:
        parecer += "• 🍄 RISCO ALTO DE MOFO CINZENTO/ANTRACNOSE: Clima úmido e ameno detectado. Reforce o preventivo em Amoras e Framboesas.\n"
    
    # 2. Manejo de Irrigação para Mirtilo (Sensível a estresse)
    if total_chuva_semana < 5 and hoje['et0'] > 4.8:
        parecer += "• 💧 ALERTA MIRTILO: Baixa umidade e ET0 alta. Mirtilos têm raízes superficiais; não deixe o solo secar hoje.\n"

    # 3. Qualidade do Fruto (Radiação/Calor)
    if hoje['temp'] > 28 and hoje['umidade'] < 40:
        parecer += "• ☀️ QUALIDADE: Risco de escaldadura nos frutos. Considere o uso de telas se disponível.\n"

    # 4. Pulverização (Delta T)
    parecer += f"• 🌬️ PULVERIZAÇÃO: Delta T atual em {delta_t}. "
    if 2 <= delta_t <= 8:
        parecer += "Ideal para aplicação.\n"
    else:
        parecer += "Evite aplicação (Risco de baixa eficiência).\n"
        
    return parecer

def get_agro_data_berries():
    url = f"https://api.openweathermap.org/data/2.5/forecast?q={CIDADE}&appid={OPENWEATHER_API_KEY}&units=metric&lang=pt_br"
    data = requests.get(url).json()
    
    previsoes_diarias = []
    for i in range(0, 40, 8):
        item = data['list'][i]
        temp = item['main']['temp']
        previsoes_diarias.append({
            'data': datetime.fromtimestamp(item['dt']).strftime('%d/%m'),
            'temp': temp,
            'umidade': item['main']['humidity'],
            'chuva': sum([p.get('rain', {}).get('3h', 0) for p in data['list'][i:i+8]]),
            'et0': round(0.0023 * (temp + 17.8) * (temp ** 0.5) * 0.408, 2)
        })
    
    analise = analisar_berries(previsoes_diarias)
    
    corpo = f"📊 CONSULTORIA PREMIUM: FRUTAS VERMELHAS - IBICOARA\n"
    corpo += f"📅 Gerado: {datetime.now().strftime('%d/%m %H:%M')}\n\n"
    corpo += "📈 TENDÊNCIA 5 DIAS:\n"
    for p in previsoes_diarias:
        corpo += f"{p['data']}: {p['temp']}°C | Chuva: {p['chuva']:.1f}mm | UR: {p['umidade']}%\n"
    
    corpo += f"\n{analise}"
    return corpo

def enviar_email(conteudo):
    msg = EmailMessage()
    msg.set_content(conteudo)
    msg['Subject'] = f"💎 CONSULTORIA BERRIES: {datetime.now().strftime('%d/%m')}"
    msg['From'] = EMAIL_DESTINO
    msg['To'] = EMAIL_DESTINO
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(EMAIL_DESTINO, GMAIL_PASSWORD)
        smtp.send_message(msg)

if __name__ == "__main__":
    relatorio = get_agro_data_berries()
    enviar_email(relatorio)
    print("✅ Relatório especializado em Berries enviado!")
