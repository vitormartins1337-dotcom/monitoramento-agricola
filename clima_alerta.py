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

def analisar_plano_semanal(previsoes):
    total_chuva = sum(p['chuva'] for p in previsoes)
    total_et0 = sum(p['et0'] for p in previsoes)
    balanco = total_chuva - total_et0
    
    parecer = f"📋 PLANO DE AÇÃO SEMANAL (Tendência 5 Dias):\n"
    
    # 1. Manejo Hídrico Estratégico
    if balanco > 10:
        parecer += f"• 🌧️ ALERTA: Chuva acumulada alta ({total_chuva:.1f}mm). Risco de encharcamento e lixiviação. Reduza a fertirrigação.\n"
    elif balanco < -15:
        parecer += f"• ⚠️ DÉFICIT: Solo perderá {abs(balanco):.1f}mm a mais do que receberá. Reforce o turno de rega dos mirtilos.\n"
    else:
        parecer += f"• ✅ BALANÇO: Chuva ({total_chuva:.1f}mm) vs Perda ({total_et0:.1f}mm) equilibrados.\n"
        
    # 2. Janela de Operação (Pulverização)
    melhor_dia = min(previsoes, key=lambda x: x['vento'])
    parecer += f"• 🌬️ PULVERIZAÇÃO: Melhor janela para {melhor_dia['data']} (Vento: {melhor_dia['vento']:.1f}km/h | Delta T: {melhor_dia['delta_t']}).\n"
    
    # 3. Sanidade de Frutas (Amora, Framboesa, Mirtilo)
    risco_fungo = any(p['umidade'] > 85 and 15 <= p['temp'] <= 24 for p in previsoes)
    if risco_fungo:
        parecer += "• 🍄 FITOSSANIDADE: Alta probabilidade de molhamento foliar prolongado. Risco de Botrytis nas Berries.\n"
    
    # 4. Qualidade de Colheita
    if any(p['chuva'] > 5 for p in previsoes):
        parecer += "• 🧺 COLHEITA: Evite colher amoras/framboesas nos dias chuvosos para evitar perdas pós-colheita."

    return parecer

def get_agro_data_completo():
    url = f"https://api.openweathermap.org/data/2.5/forecast?q={CIDADE}&appid={OPENWEATHER_API_KEY}&units=metric&lang=pt_br"
    data = requests.get(url).json()
    
    previsoes_diarias = []
    for i in range(0, 40, 8):
        item = data['list'][i]
        temp = item['main']['temp']
        umidade = item['main']['humidity']
        previsoes_diarias.append({
            'data': datetime.fromtimestamp(item['dt']).strftime('%d/%m'),
            'temp': temp,
            'umidade': umidade,
            'vento': item['wind']['speed'] * 3.6,
            'chuva': sum([p.get('rain', {}).get('3h', 0) for p in data['list'][i:i+8]]),
            'et0': round(0.0023 * (temp + 17.8) * (temp ** 0.5) * 0.408, 2),
            'delta_t': calcular_delta_t(temp, umidade)
        })
    
    plano_acao = analisar_plano_semanal(previsoes_diarias)
    
    corpo = f"📊 CONSULTORIA AGRO PREMIUM - IBICOARA/BA\n"
    corpo += f"📅 Gerado em: {datetime.now().strftime('%d/%m %H:%M')}\n\n"
    corpo += "📈 TENDÊNCIA 5 DIAS:\n"
    for p in previsoes_diarias:
        corpo += f"{p['data']}: {p['temp']}°C | Chuva: {p['chuva']:.1f}mm | UR: {p['umidade']}%\n"
    
    corpo += f"\n{plano_acao}"
    return corpo

def enviar_email(conteudo):
    msg = EmailMessage()
    msg.set_content(conteudo)
    msg['Subject'] = f"💎 PLANO DE AÇÃO AGRO: {datetime.now().strftime('%d/%m')}"
    msg['From'] = EMAIL_DESTINO
    msg['To'] = EMAIL_DESTINO
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(EMAIL_DESTINO, GMAIL_PASSWORD)
        smtp.send_message(msg)

if __name__ == "__main__":
    relatorio = get_agro_data_completo()
    enviar_email(relatorio)
    print("✅ Sistema Premium atualizado e enviado!")
