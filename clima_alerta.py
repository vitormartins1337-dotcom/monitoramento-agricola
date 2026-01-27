import requests
import os
import smtplib
from datetime import datetime
from email.message import EmailMessage

# CONFIGURAÇÕES
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_KEY")
GMAIL_PASSWORD = os.getenv("GMAIL_PASSWORD")
EMAIL_DESTINO = "vitormartins1337@gmail.com"
CIDADE = "Ibicoara, BR"

def analisar_agronomica(previsoes):
    """Analisa os dados de 5 dias e gera um parecer técnico."""
    total_chuva = sum(p['chuva'] for p in previsoes)
    media_et0 = sum(p['et0'] for p in previsoes) / len(previsoes)
    temp_max = max(p['temp'] for p in previsoes)
    
    parecer = f"📋 PLANO DE AÇÃO SEMANAL (Tendência 5 Dias):\n"
    
    # Análise de Chuva e Irrigação
    if total_chuva > 25:
        parecer += f"• 🌧️ ALERTA: Chuva acumulada alta ({total_chuva:.1f}mm). Risco de encharcamento. Reduza a fertirrigação.\n"
    elif total_chuva < 5 and media_et0 > 4.5:
        parecer += f"• ⚠️ DÉFICIT HÍDRICO: Semana seca com alta perda por evapotranspiração ({media_et0:.2f} mm/dia). Reforce as lâminas.\n"
    else:
        parecer += "• ✅ BALANÇO: Condições hídricas equilibradas para a semana.\n"
        
    # Análise de Fitossanidade (Vento e Umidade)
    melhor_dia = min(previsoes, key=lambda x: x['vento'])
    parecer += f"• 🌬️ PULVERIZAÇÃO: Melhor janela prevista para {melhor_dia['data']} (Ventos de {melhor_dia['vento']:.1f} km/h).\n"
    
    if any(p['umidade'] > 85 for p in previsoes):
        parecer += "• 🍄 RISCO FÚNGICO: Umidade acima de 85% prevista. Monitore sinais de doenças foliares."
        
    return parecer

def get_agro_data_5days():
    url = f"https://api.openweathermap.org/data/2.5/forecast?q={CIDADE}&appid={OPENWEATHER_API_KEY}&units=metric&lang=pt_br"
    data = requests.get(url).json()
    
    previsoes_diarias = []
    # O OpenWeather retorna dados a cada 3 horas. Pegamos 1 ponto por dia (8 * 3h = 24h)
    for i in range(0, 40, 8):
        item = data['list'][i]
        temp = item['main']['temp']
        dados_dia = {
            'data': datetime.fromtimestamp(item['dt']).strftime('%d/%m'),
            'temp': temp,
            'umidade': item['main']['humidity'],
            'vento': item['wind']['speed'] * 3.6,
            'chuva': sum([p.get('rain', {}).get('3h', 0) for p in data['list'][i:i+8]]),
            'et0': round(0.0023 * (temp + 17.8) * (temp ** 0.5) * 0.408, 2)
        }
        previsoes_diarias.append(dados_dia)
    
    # Montagem do Texto
    analise = analisar_agronomica(previsoes_diarias)
    
    corpo = f"📊 RELATÓRIO ESTRATÉGICO - IBICOARA/BA\n📅 Gerado em: {datetime.now().strftime('%d/%m %H:%M')}\n\n"
    corpo += "PREVISÃO RESUMIDA:\n"
    for p in previsoes_diarias:
        corpo += f"{p['data']}: {p['temp']}°C | Chuva: {p['chuva']:.1f}mm | ET0: {p['et0']}mm\n"
    
    corpo += f"\n{analise}"
    return corpo

def enviar_email(conteudo):
    msg = EmailMessage()
    msg.set_content(conteudo)
    msg['Subject'] = f"💎 CONSULTORIA AGRO: Planejamento 5 Dias"
    msg['From'] = EMAIL_DESTINO
    msg['To'] = EMAIL_DESTINO
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(EMAIL_DESTINO, GMAIL_PASSWORD)
        smtp.send_message(msg)

if __name__ == "__main__":
    relatorio = get_agro_data_5days()
    enviar_email(relatorio)
    print("✅ Relatório de 5 dias enviado!")
